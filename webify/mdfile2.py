import logging
import yaml
import codecs
import argparse
import pypandoc
import os
import sys
import pprint as pp
from util2 import WebifyLogger, Terminal, mustache_renderer, jinja2_renderer, RenderingContext, render, save_to_file, get_gitinfo
import pystache
import markupsafe
from mdfilters import HTML_Filter

from globals import __version__
__logfile__ = 'mdfile.log'

class PandocArguments:
    def __init__(self):
        self.pdoc_args = []

    def add_var(self, var, val):
        self.pdoc_args.append("-V %s:%s" % (var, val))

    def add_filter(self, name):
        self.pdoc_args.append("--filter %s" % name)
        
    def add_flag(self, options):
        if isinstance(options, list):
            for o in options:
                self.pdoc_args.append("--%s" % o)
        else:
            self.pdoc_args.append("--%s" % options)

    def add(self, option, vals):
        if isinstance(vals, list):
            for v in vals:
                self.pdoc_args.append("--%s=%s" % (option, v))
        else:
            self.pdoc_args.append("--%s=%s" % (option, vals))

    def get(self):
        return self.pdoc_args

class MDfile:
    """
    Class that implements MD file conversion to other formats.
    'pandoc' is used to convert MD file to other formats.
    Yaml front matter is used to control how an MD file is converted.

    Example MD file:

    to: html* | pdf | beamer | latex (very useful during debugging)
    template: None* | path/to/pandoc-template-file
    render: None* | path/to/mustache-or-jinja-template-file

    standalone-alone: None | false* or true

    if standalone is false and render is None then standalon is true

    css: None* | path/to/css-file (used only when converting to html)

    or

    css:
        - path/to/css-file-1
        - path/to/css-file-2
        - path/to/css-file-3
        ...

    include-before-body: None* | path/to/file
        - path/to/file-1
        - path/to/file-2
        - path/to/file-3
        ...

    include-in-header: None* | path/to/file
        - path/to/file-1
        - path/to/file-2
        - path/to/file-3
        ...

    include-after-body: None* | path/to/file
        - path/to/file-1
        - path/to/file-2
        - path/to/file-3
        ...

    html-img: None* | file
    html-imgs: None* | file
    html-vid: None* | file
    html-vids: None* | file

    Check out mdfilters.py and ./filter/* to see how these tags are used.  These use the following 
    markdown syntax: "![](file)" or "![](file1|file2)".  Note that the second form isn't understood by 
    markdown.

    renderer: jinja | mustache*

    bibliography: None* | path/to/bib file

    csl: None* | path/to/csl file

    preprocess-mustache: None | *True or False

    pdf-engine: *None | lualatex or tetex.  This info will be passed onto pandoc convertor.
    ___

    Contents of the MD file.

    Default mode is to convert an MD file to a standalone html.  Otherwise 'to' key
    can be used to specify other conversion modes, e.g., pdf or beamer slides.
    'template' key is used to specify the pandoc template used during the conversion.
    If no 'template' key is specified the default pandoc template is used.
    Check out the 'pandoc -D html ...' command to see the default template.
    'render' key is used to specify the mustache template.  'render' key is only used if
    html is generated from the MD file.  'body' tag in the mustache template is replaced
    by the html generated from this MD file.  Note that when converting MD file to html,
    template is only used if 'render' key is None.  A value for 'render' key
    indicates that the generated html will be consumed within a mustache file.

    It is possible to pass the contents of the mdfile through mustache before the
    mdfile is passed on to pandoc for conversion.  If this behavior is desired
    set preprocess-mustache to true.  The default is false.
    """
    def __init__(self, filepath, rootdir, extras, rc):

        # Initialize the md object
        self.logger = WebifyLogger.get('mdfile')
        self.filepath = filepath
        self.rootdir = rootdir
        self.extras = extras
        self.rc = rc

        self.logger.debug('Processing: %s' % self.filepath)
        self.logger.debug('rootdir:    %s' % self.rootdir)
        if WebifyLogger.is_debug(self.logger):
            print('Extras:')
            pp.pprint(self.extras)
            print('Rendering context:')
            pp.pprint(self.rc.get())

        # We only support the following conversions
        self.supported_output_formats = [ 'html',
                                          'beamer',
                                          'pdf',
                                          'latex' ]
        self.extensions = { 'html':   'html',
                            'beamer': 'pdf',
                            'pdf':    'pdf',
                            'latex':  'tex' }

        # This is an incomplete list of keys that can be found in a yaml frontmatter
        self.supported_keys = [ 'standalone',
                                'to',
                                'template',
                                'render',
                                'bibliography',
                                'css',
                                'include-after-body',
                                'include-before-body',
                                'include-in-header',
                                'title',
                                'author',
                                'date',
                                'institute',
                                'titlegraphics',
                                'subtitle',
                                'preprocess-mustache' ]

    def load(self):
        logger = WebifyLogger.get('file-debug')
        self.yaml = {}

        # Read the file in to a buffer
        try:
            with codecs.open(self.filepath, 'r', 'utf-8') as stream:
                self.buffer = stream.read()
            self.logger.info('Loaded MD file: %s' % self.filepath)
        except:
            self.logger.warning('Cannot load: %s' % self.filepath)
            self.buffer = None
            return self

        # Try to get the first yaml section from the file
        try:
            yamlsections = yaml.load_all(self.buffer)
            for section in yamlsections:
                self.yaml = section
                logger.info('YAML section found')
                if WebifyLogger.is_debug(logger):
                    print('Buffer:')
                    pp.pprint(self.buffer)
                    print('YAML frontmatter:')
                    pp.pprint(self.yaml)
                break # Only the first yaml section is read in
        except:
            pass

        # If yaml section found, good.  If not create a {} yaml section.
        if not isinstance(self.yaml, dict):
            logger.warning('YAML section not found in md file: %s' % self.filepath)
            self.yaml = {}

        # If we want to preprocess the file using mustache renderer then do it
        # here.  This allows us to change the yaml frontmatter based upon the
        # larger rendering context.  Cool, eh. 
        if self.get_preprocess_mustache():
            self.logger.info('Preprocessing Yaml front matter via mustache')
            try:
                yaml_str = yaml.dump(self.get_yaml())
                s = mustache_renderer(yaml_str, self.rc.data())
                self.set_yaml(yaml.load(s))
            except:
                self.logger.warning('Failed: preprocessing Yaml front matter via mustache')
                if WebifyLogger.is_debug(self.logger):
                    pp.pprint(self.rc.data())
                    pp.pprint(yaml.dump(self.get_yaml()))

            if WebifyLogger.is_debug(logger):
                print('YAML frontmatter after pre-processing:')
                pp.pprint(self.yaml)

        # Update the rendering context for this file
        self.rc.add(self.get_yaml())
        return self

    def get_buffer(self):
        if not self.buffer:
            return 'error', 'Load error', self.filepath

        output_format = self.get_output_format()
        if not output_format in self.supported_output_formats:
            self.logger.error('Unsupported conversion format "%s": %s' % (output_format, self.filepath))
            return 'error', 'Unrecognized output format "%s"' % output_format,  self.filepath

        self.logger.info('Converting to "%s"' % output_format)
        return self.convert()

    def compile(self, output_format, pandoc_args, output_filepath=None):
        ret_type = 'file' if output_filepath else 'buffer'
        ret_val = output_filepath

        cwd = os.getcwd()
        os.chdir(self.rootdir)
    
        try:
            ret_val = pypandoc.convert_text(self.buffer, to=output_format, format='md', outputfile=output_filepath, extra_args=pandoc_args)
            ret_val = output_filepath if output_filepath else ret_val
            self.logger.debug('Converted to "%s": %s' % (output_format, output_filepath))
            ret = ret_type, ret_val, self.filepath
        except Exception as e:
            self.logger.error('Pandoc conversion failed\n\t - filename: %s' % self.filepath)
            self.logger.error('\t - output format: %s' % output_format)
            self.logger.error('\t - args:          %s' % pandoc_args)
            self.logger.error('\t - outputfile:    %s' % output_filepath)
            self.logger.error('\t - rootdir:       %s' % self.rootdir)
            self.logger.error('--- Pandoc says ---\n\n%s\n---' % e)
            
            ret = 'error', 'Conversion', self.filepath
        os.chdir(cwd)

        return ret

    def make_output_filepath(self):
        output_file = self.extras['output-file']
        assert(output_file)
        output_format = self.get_output_format()

        oname, oextension = os.path.splitext(output_file)
        if oextension == '':
            output_file = oname + '.' + self.extensions[output_format]
        elif oextension[1:] != self.extensions[output_format]:
            if oextension != '._mdfile_tmp':
                self.logger.warning('Illegal file extension\n\t - filename: %s\n\t - output:   %s' % (self.filepath, output_file))
                self.logger.warning('Correct extension is: %s' % self.extensions[output_format])
                return None
            else:
                output_file = oname + '.' + self.extensions[output_format]
        else:
            pass
        self.logger.debug('Output file: %s' % output_file)

        return output_file

    def is_create_outputfile(self):
        try:
            return not self.extras['no-output-file']
        except:
            return True

    def convert(self):
        files = [self.filepath]
        pdoc_args = PandocArguments()
        using_renderfile = False

        render_file = self.get_renderfile()
        template_file = self.get_template()

        # The plan is to create an output file
        if self.is_create_outputfile():
            self.logger.info('Create output file YES')
            output_filepath = self.make_output_filepath()
            if not output_filepath:
                return 'error', 'Illegal output filename', self.filepath
            
            if render_file:
                self.logger.info('Renderfile found: %s' % render_file)
                if template_file: self.logger.warning('Ignoring pandoc template file: %s' % template)
                using_renderfile = True
                files.append(render_file)
                self.logger.debug('Pandoc standalone mode OFF')
            else:
                self.logger.debug('Pandoc standalone mode ON')
                pdoc_args.add_flag('standalone')
                if template_file:
                    self.logger.info('Using pandoc template file: %s' % template_file)
                    pdoc_args.add('template', template_file)
                    files.append(template_file)
        # We don't plan to create an output file
        else:
            self.logger.info('Create output file NO')
            output_filepath = None
            if render_file: self.logger.warning('Ignoring renderfile file: %s' % render_file)
            if template_file: self.logger.warning('Ignoring pandoc template file: %s' % template_file)

        # Lets get the bib and csl files
        bib_file = self.get_bibfile()
        self.logger.debug('Bibliography: %s' % bib_file)
        if bib_file:
            files.append(bib_file)
            pdoc_args.add('bibliography', bib_file)
            #pdoc_args.add_filter('pandoc-citeproc')

        csl_file = self.get_cslfile()
        self.logger.debug('CSL file: %s' % csl_file)
        if csl_file:
            files.append(csl_file)
            pdoc_args.add('csl', csl_file)

        # Get pandoc include files
        include_files = self.get_pandoc_include_files()
        pdoc_args.add('include-in-header',   include_files['include-in-header'])
        pdoc_args.add('include-before-body', include_files['include-before-body'])
        pdoc_args.add('include-after-body',  include_files['include-after-body'])
        if WebifyLogger.is_debug(self.logger):
            print('Pandoc include files:')
            pp.pprint(include_files)
        files.extend(include_files['include-in-header'])
        files.extend(include_files['include-before-body'])
        files.extend(include_files['include-after-body'])

        hf, hf_file_list = self.get_html_filters()
        if len(hf_file_list) > 0:
            files.extend(hf_file_list)
        
        # See if any of the sources are newer than the output,
        # if output exists
        if self.needs_compilation(files, output_filepath):
            self.logger.debug('Needs compilation YES')
        else:
            self.logger.debug('Needs compilation NO')
            self.logger.warning('Doesn\'t need to do anything.  Output already exists: %s' % output_filepath)
            return 'exists', output_filepath, self.filepath

        # So it seems that we will have to do the real work
        pdoc_args.add('highlight-style', self.get_highlight_style())
#        pdoc_args.add_flag('listings')

        if self.get_output_format() == 'beamer':
            slide_level = self.get_slide_level()
            pdoc_args.add('slide-level', slide_level)

        # See if we need to preprocess the mdfile using mustache templating
        # If we have to then lets get on with it.        
        if self.get_preprocess_mustache():
            if self.get_output_format() == 'html':
                self.logger.info('Preprocess mustache YES')

                if len(hf_file_list) > 0:
                    self.logger.info('Applying HTML filter')
                    f = HTML_Filter(hf)
                    self.buffer = f.apply(self.buffer)
                
                self.buffer = mustache_renderer(self.buffer, self.rc.data())
            else:
                self.logger.warning('Preprocess mustache is only allowed for md to html conversion.')
        else:
            self.logger.info('Preprocess mustache NO')
            if len(hf_file_list) > 0:
                self.logger.warning('HTML Filters are only applied when preprocess mustache is ON.')

        # Now we need to use pandoc to transform the "preprocessed"
        # md file to one of three output formats: 1) html,
        # 2) latex, or 3) beamer
        # We set the options accordingly
        if self.get_output_format() == 'html':
            pdoc_args.add_flag('mathjax')
            pdoc_args.add('css', self.get_cssfiles())
        elif self.get_output_format() in ['pdf', 'beamer', 'latex']:
            pdoc_args.add_var('graphics','true')
            pdf_engine = self.get_pdf_engine()
            if pdf_engine:
                pdoc_args.add('pdf-engine', pdf_engine)

        # If we were supposed to create an output file
        # and no renderfile is specified.  This case is rather
        # straightforward.  Pandoc can create the output file
        # for us.  
        if self.is_create_outputfile() and not using_renderfile:
            return self.compile(output_format=self.get_output_format(), pandoc_args=pdoc_args.get(), output_filepath=output_filepath)
        
        # We are left with the following choices.  We are not
        # supposed to create an output file.  Or we are 
        # supposed to create an output file using the
        # render file.  In the later case the html contents from 
        # the md file will replace the {{body}} tag of the template.

        # First, lets ensure that the output format is html
        assert(self.get_output_format() == 'html')

        # Next lets use pandoc to get md to html
        r = self.compile(output_format=self.get_output_format(), pandoc_args=pdoc_args.get())

        # Case 1: If a render file is not specified.  It means that the intention is not
        # to create a output file.  Return the buffer. 
        if not using_renderfile:
            self.logger.info('Using render file NO')
            return r

        # Case 2: A render file is specified.  We need will use the 
        # render file to create the output file.
        self.logger.info('Using render file YES')
        self.rc.add({'body': markupsafe.Markup(r[1])})

        # Lets find the renderer that we plan to use.  We have
        # two options: mustache or jinja2
        if self.get_renderer() == 'mustache':
            render_engine = mustache_renderer
            self.logger.info('Using renderer: mustache')
        else:
            render_engine = jinja2_renderer
            self.logger.info('Using renderer: jinja2')

        # Render and save to the output file
        buffer = render(render_file, self.rc.data(), render_engine)
        self.logger.debug('Saving to output file: %s' % output_filepath)
        if save_to_file(output_filepath, buffer):
            return 'file', output_filepath, self.filepath
        else:
            self.logger.warning('Error saving to output file: %s' % output_filepath)
            return 'error', output_filepath, self.filepath

    def needs_compilation(self, files, output_filepath):
        if not output_filepath or self.extras['ignore-times']: return True
        if output_filepath and not os.path.isfile(output_filepath): return True

        for f in files:
            if os.path.isfile(f) and os.path.getmtime(f) > os.path.getmtime(output_filepath):
                return True
        if output_filepath and os.path.isfile(output_filepath) and os.path.getmtime(output_filepath) < os.path.getmtime(self.filepath):
            return True

        return False

    def get_highlight_style(self):
        try:
            if self.extras['highlight-style']:
                return self.extras['highlight-style']
        except:
            pass

        try:
            return self.yaml['highlight-style']
        except:
            return 'pygments'

    def get_yaml(self):
        return self.yaml

    def set_yaml(self, data):
        #print(data)
        self.yaml = data

    def get_html_filters(self):
        file_list = []
        hf = {'html-img': None, 'html-imgs': None, 'html-vid': None, 'html-vids': None}

        for key in hf.keys():
            if key in self.yaml.keys():
                f = os.path.normpath(os.path.join(self.rootdir, self.yaml[key]))
                if os.path.isfile(f):
                    hf[key] = f
                    file_list.append(f)
                    self.logger.info('Found HTML filter file: %s found in %s' % (f, self.filepath))
                else:
                    self.logger.warning('Ignoring HTML filter file: %s found in %s' % (f, self.filepath))
        return hf, file_list

    def get_output_format(self):
        assert(self.buffer)

        try:
            if self.extras['format']:
                return self.extras['format']
        except:
            pass

        try:
            return self.yaml['to']
        except:
            return 'html'

    def get_pdf_engine(self):
        assert(self.buffer)

        try:
            if self.extras['pdf-engine']:
                return self.extras['pdf-engine']
        except:
            pass

        try:
            return self.yaml['pdf-engine']
        except:
            return None

    def get_preprocess_mustache(self):
        assert(self.buffer)

        try:
            if not self.extras['preprocess-mustache'] is None:
                return self.extras['preprocess-mustache']
        except:
            pass

        try:
            return self.yaml['preprocess-mustache']
        except:
            return True

    def get_files(self, key):
        try:
            f1 = self.yaml[key] if isinstance(self.yaml[key], list) else [self.yaml[key]]
            f1 = [x for x in f1 if x is not None]
        except:
            f1 = []
        try:
            f2 = self.extras[key] if isinstance(self.extras[key], list) else [self.extras[key]]
            f2 = [x for x in f2 if x is not None]
        except:
            f2 = []
        files = f1 + f2
        return files

    def pick_last_file(self, key):
        files = self.get_files(key)
        if len(files) > 0: return files[-1]
        return None

    def pick_all_files(self, key, relpath=False):
        return self.get_files(key)

    def get_renderfile(self):
        file = self.pick_last_file('render')
        file = os.path.join(self.rootdir, os.path.expandvars(file)) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find render file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    def get_template(self):
        file = self.pick_last_file('template')
        file = os.path.join(self.rootdir, os.path.expandvars(file)) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find template file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    def get_cssfiles(self):
        return self.pick_all_files('css', relpath=True)

    def get_bibfile(self):
        file = self.pick_last_file('bibliography')
        file = os.path.join(self.rootdir, os.path.expandvars(file)) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find bibliography file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    def get_cslfile(self):
        file = self.pick_last_file('csl')
        file = os.path.join(self.rootdir, os.path.expandvars(file)) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find csl file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    def get_pandoc_include_files(self):
        f = {'include-after-body': [], 'include-before-body':[], 'include-in-header': []}
        for i in f.keys():
            for x in self.pick_all_files(i):
                file = os.path.join(self.rootdir, os.path.expandvars(x))
                if not os.path.isfile(file):
                    self.logger.warning('Cannot find %s file:\n\t- %s\n\t- %s' % (i, self.filepath, file))
                else:
                    f[i].append(file)
        return f

    def get_slide_level(self):
        assert(self.buffer)

        try:
            if self.extras['slide-level']:
                return self.extras['slide-level']
        except:
            pass

        try:
            return self.yaml['slide-level']
        except:
            return 1        
    
    def get_renderer(self):
        assert(self.buffer)

        try:
            value = self.yaml['renderer']
            if not value in ['mustache', 'jinja2']:
                self.logger.warning('Invalid template engine "%s" found in %s.  Valid values are "mustache" or "jinja"' % (value, self.filepath))
                return 'mustache'
            return value
        except:
            return 'mustache'

    def get_copy_to_destination(self):
        assert(self.buffer)

        try:
            return self.yaml['copy-to-destination']
        except:
            return False

def version_info():
    str =  '  Mdfile2:    %s, ' % __version__
    str += '  logfile:    %s, ' % __logfile__ 
    str += '  Git info:   %s, ' % get_gitinfo()
    str += '  Python:     %s.%s, ' % (sys.version_info[0],sys.version_info[1])
    str += '  Pypandoc:   %s, ' % pypandoc.__version__
    str += '  Pyyaml:     %s, and' % yaml.__version__
    str += '  Pystache:   %s.' % pystache.__version__
    return str

if __name__ == '__main__':

    terminal = Terminal()
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)
    cur_dir = os.getcwd()

    # Command line arguments
    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('mdfile', help='MD file.  Options specified on commandline override those specified in the file yaml block.')
    cmdline_parser.add_argument('--version', action='version', version=version_info())
    cmdline_parser.add_argument('-o','--output', action='store', default=None, help='Output path.  A file or dir name can be specified.')
    cmdline_parser.add_argument('--no-output-file', action='store_true', default=False, help='Use this flag to turn off creating an output file.')
    cmdline_parser.add_argument('-v','--verbose', action='store_true', default=False, help='Turn verbose on.')
    cmdline_parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages.')
    cmdline_parser.add_argument('--debug-file', action='store_true', default=False, help='Debug messages regarding file loading.')
    cmdline_parser.add_argument('--debug-render', action='store_true', default=False, help='Debug messages regarding template rendering.')
    cmdline_parser.add_argument('-f','--format', action='store', default=None, help='Output format: html, pdf, beamer, latex.')
    cmdline_parser.add_argument('-T','--template', action='store', default=None, help='Path to pandoc template file.')
    cmdline_parser.add_argument('-H','--include-in-header', nargs='*', action='append', default=None, help='Path to file that will be included in the header.  Typically LaTeX preambles.')
    cmdline_parser.add_argument('-b','--bibliography', action='store', default=None, help='Path to bibliography file.')
    cmdline_parser.add_argument('--css', nargs='*', action='append', default=None, help='Space separated list of css files.')
    cmdline_parser.add_argument('--csl', action='store', default=None, help='csl file, only used when a bibfile is specified either via commandline or via yaml frontmatter')
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Writes out a log file.')
    cmdline_parser.add_argument('--highlight-style', action='store', default=None, help='Specify a highlight-style.  See pandoc --list-highlight-styles.')
    cmdline_parser.add_argument('-Y', '--yaml', nargs='*', action='append', help='Space separated list of extra yaml files to process.')
    cmdline_parser.add_argument('-p', '--do-not-preprocess-mustache', action='store_true', default=None, help='Turns off pre-processesing md file using mustache before converting via pandoc.')
    cmdline_parser.add_argument('-i', '--ignore-times', action='store_true', default=False, help='Forces the generation of the output file even if the source file has not changed')
    cmdline_parser.add_argument('--slide-level', action='store', default=None, help='Slide level argument for pandoc (for beamer documents)')
    cmdline_parser.add_argument('--pdf-engine', action='store', default=None, help='PDF engine used to generate pdf. The default is vanilla LaTeX.  Possible options are lualatex or tetex.')

    
    cmdline_args = cmdline_parser.parse_args()

    css_files = cmdline_args.css[0] if cmdline_args.css else []
    include_in_header = [os.path.join(cur_dir, f) for f in (cmdline_args.include_in_header[0] if cmdline_args.include_in_header else [])]
    bibliography = os.path.join(cur_dir, cmdline_args.bibliography) if cmdline_args.bibliography else None
    csl = os.path.join(cur_dir, cmdline_args.csl) if cmdline_args.csl else None
    template = os.path.join(cur_dir, cmdline_args.template) if cmdline_args.template else None

    # Setting up logging
    logfile = None if not cmdline_args.log else __logfile__
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug   else loglevel
    logger = WebifyLogger.make(name='mdfile', loglevel=loglevel, logfile=logfile)
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug_render   else loglevel
    WebifyLogger.make(name='render', loglevel=loglevel, logfile=logfile)
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug_file   else loglevel
    WebifyLogger.make(name='file-debug', loglevel=loglevel, logfile=logfile)
    
    # Go
    logger.debug('Prog name:    %s' % prog_name)
    logger.debug('Prog dir:     %s' % prog_dir)
    logger.debug('Current dir:  %s' % cur_dir)
    logger.debug('Info:')
    logger.debug(version_info())

    if WebifyLogger.is_debug(logger):
        print('Commandline arguments:')
        print('--format:                    ', cmdline_args.format)
        print('--template:                  ', template)
        print('--no-output-file:            ', cmdline_args.no_output_file)
        print('--include-in-header:         ', include_in_header)
        print('--bibliography:              ', bibliography)
        print('--css:                       ', css_files)
        print('--csl:                       ', csl)
        print('--highlight-style:           ', cmdline_args.highlight_style)
        print('--do-not-preprocess-mustache:', cmdline_args.do_not_preprocess_mustache)
        print('--ignore-times:              ', cmdline_args.ignore_times)
        print('--output:                    ', cmdline_args.output)
        print('--slide-level:               ', cmdline_args.slide_level)
        print('--pdf-engine:                ', cmdline_args.pdf_engine)
        

    filepath = os.path.normpath(os.path.join(cur_dir, cmdline_args.mdfile))
    filename = os.path.basename(filepath)
    file_dir = os.path.split(filepath)[0]
    temporary_output_filename = os.path.splitext(filename)[0]+'._mdfile_tmp'
    output_filename = cmdline_args.output if cmdline_args.output else temporary_output_filename 
    if os.path.isdir(output_filename):
        output_filepath = os.path.normpath(os.path.join(output_filename, temporary_output_filename))
    else:
        output_filepath = os.path.normpath(os.path.join(cur_dir, output_filename))

    if WebifyLogger.is_debug(logger):
        logger.debug('filepath:        %s' % filepath)
        logger.debug('filename:        %s' % filename)
        logger.debug('file_dir:        %s' % file_dir)
        logger.debug('output_filename: %s' % output_filename)
        logger.debug('output_filepath: %s' % output_filepath)

    extras = { 'format': cmdline_args.format,
               'template': template,
               'bibliography': bibliography,
               'css': css_files,
               'csl': csl,
               'highlight-style': cmdline_args.highlight_style,
               'ignore-times': cmdline_args.ignore_times,
               'preprocess-mustache': not cmdline_args.do_not_preprocess_mustache,
               'include-in-header': include_in_header,
               'ignore-times': cmdline_args.ignore_times,
               'output-file': output_filepath,
               'no-output-file': cmdline_args.no_output_file,
               'slide-level': cmdline_args.slide_level,
               'pdf-engine': cmdline_args.pdf_engine }

    meta_data = {
        '__version__': __version__,
        '__filepath__': filepath.replace('\\','\\\\'),
        '__rootdir__': file_dir.replace('\\','\\\\')
    }
    rc = RenderingContext()
    rc.push()
    rc.add(meta_data)

    m = MDfile(filepath=filepath, rootdir=file_dir, extras=extras, rc=rc)
    m.load()
    ret_type, ret_val, _ = m.get_buffer()
    logger.debug('Status:  %s' % ret_type)
    logger.debug('Message: %s' % ret_val)
    if ret_type == 'file':
        logger.info('Output file: %s' % ret_val)
    elif ret_type == 'error':
        logger.error('Failure: %s' % ret_val)
    elif ret_type == 'exists':
        pass
    elif ret_type == 'buffer':
        pass
    else:
        logger.error('Unknown error: (%s, %s...)' % (ret_type, ret_val[:100]))

    exit(0)
