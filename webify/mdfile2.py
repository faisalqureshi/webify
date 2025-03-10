import logging
import yaml
import yamlfile
import codecs
import argparse
import pypandoc
import os
import sys
import pprint as pp
import util2 as util
import pystache
import markupsafe
from mdfilters import HTML_Filter
import datetime
import rc as RenderingContext
import dateutil.parser
import time_util as tm

from globals import __version__
__logfile__ = 'mdfile.log'


class PandocArguments:
    '''
    Helper class to setup arguments for pypandoc.
    '''
    def __init__(self, pandoc_var, pandoc_meta):
        self.pdoc_args = []

        for v in pandoc_var:
            self.add_var(v)

        for v in pandoc_meta:
            self.add_meta(v)

    def add_var(self, v):
        self.pdoc_args.extend(["-V", "%s" % v])

    def add_meta(self, v):
        self.pdoc_args.extend(["-M", "%s" % v])

    # def add_var(self, var, val):
    #     self.pdoc_args.append("-V %s=%s" % (var, val))

    def add_filter(self, name):
        self.pdoc_args.append("--filter %s" % name)
        
    def add_flag(self, options):
        if isinstance(options, list):
            for o in options:
                self.pdoc_args.append("--%s" % o)
        else:
            self.pdoc_args.append("--%s" % options)

    def add_flag_shortform(self, options):
        if isinstance(options, list):
            for o in options:
                self.pdoc_args.append("-%s" % o)
        else:
            self.pdoc_args.append("-%s" % options)

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
    This class implements markdown conversion to other formats.
    'pandoc' is used to convert the markdown file to other formats.
    Yaml front matter is used to control how an MD file is converted.

    # Highlights

    By default a markdown file is converted to a standalone html file.

    The `to` key can be specified to specify other conversion modes: 
    pdf article, beamer slides, or plain LaTeX (useful for debugging).

    The `template` key is used to specify the pandoc template during conversion:

    - default pandoc template is used if `template` key is not provided.  Use 
    `pandoc -D <html|latex|beamer>` to get default pandoc template for the format that
    you are interested in.
    - `template` key is only used if `render` key doesn't specify a mustache or 
    jinja2 template file.  

    The `render` key is used to specify a mustache or jinja2 template file:

    - `render` key is only used if document is converted to html.
    - when `render` key is specified, markdown is converted to plain html (without)
    using pandoc template, i.e., `template` key is ignored.
    - when `render` key is specified html contents is available as the 
    `body` tag during mustache or jinja2 rendering.
    - A value for `render` key indicates that the generated html will
    be consumed within a mustache or jinja template file.

    # Yaml frontmatter

    [PANDOC & INTERNAL]
    to: html* | pdf | beamer | latex (very useful during debugging)
    
    [PANDOC]
    template: None* | path/to/pandoc-template-file
    When None, default pandoc template is used.
    
    [INTERNAL]
    render: None* | path/to/mustache-or-jinja-template-file (see below about how to use it)

    [INTERNAL]
    renderer: jinja2* | mustache*

    [PANDOC]
    css: None* | path/to/css-file (used only when converting to html)

    or

    css:
        - path/to/css-file-1
        - path/to/css-file-2
        - path/to/css-file-3
        ...

    [PANDOC]
    include-before-body: None* | path/to/file
        - path/to/file-1
        - path/to/file-2
        - path/to/file-3
        ...

    [PANDOC]
    include-in-header: None* | path/to/file
        - path/to/file-1
        - path/to/file-2
        - path/to/file-3
        ...

    [PANDOC]
    include-after-body: None* | path/to/file
        - path/to/file-1
        - path/to/file-2
        - path/to/file-3
        ...

    [INTERNAL]
    html-img: None* | file
    html-imgs: None* | file
    html-vid: None* | file
    html-vids: None* | file

    Check out mdfilters.py and ./filter/* to see how these tags are used.  These use the following 
    markdown syntax: "![](file)" or "![](file1|file2)".  Note that the second form isn't understood by 
    markdown.

    [PANDOC]
    bibliography: None* | path/to/bib file

    [PANDOC]
    csl: None* | path/to/csl file

    [INTERNAL]
    preprocess-frontmatter: None | *True or False
    preprocess-buffer: None | True or False (True for conversion to html, False otherwise) 

    These two flags can be used preprocess yaml frontmatter or buffer
    using mustache rendering using the current rendering context.

    [PANDOC]
    pdf-engine: *None | lualatex or tetex.  This info will be passed onto pandoc convertor.

    [INTERNAL]
    copy-source: None | *False, True
    
    Copy source markdwon file to destination.
    """
    def __init__(self, filepath, args):

        # Initialize the md object
        self.logger = util.WebifyLogger.get('main')
        self.filepath = filepath
        self.rootdir = os.path.split(filepath)[0]
        self.args = args
        self.output_format = None

        self.logger.debug('Processing: %s' % self.filepath)
        self.logger.debug('rootdir:    %s' % self.rootdir)
        self.logger.debug(pp.pformat(self.args, indent=2))
        
        # if util.WebifyLogger.is_debug(self.logger):
        #     print('args:')
        #     pp.pprint(self.args, indent=2)

        self.formats = { 'html':   {'ext': '.html', 'fn': self.to_html},
                         'beamer': {'ext': '.pdf',  'fn': self.latexify},
                         'pdf':    {'ext': '.pdf',  'fn': self.latexify},
                         'latex':  {'ext': '.tex',  'fn': self.latexify} }

        self.defaults = { 'to': 'html',
                          'renderer': 'jinja2',
                          'highlight-style': 'pygments',
                          'pdf-engine': None,
                          'preprocess-frontmatter': True,
                          'preprocess-buffer': None,
                          'slide-level': 1,
                          'toc': False,
                          'copy-source': False,
                          'create-output-file': True,
                          'standalone-html': False,
                          'ignore': False,
                          'ignore-times': False,
                          'availability': None }

    def get_filename(self):
        return os.path.basename(self.filepath)

    def get_filepath(self):
        return self.filepath

    def get_defaults(self):
        return self.defaults

    def set_default(self, key, value):
        self.defaults[key] = value
        
    def load(self, rc={}):
        self.yaml = {}

        logger_file = util.WebifyLogger.get('md-file')
        logger_buffer = util.WebifyLogger.get('md-buffer')

        # Read the file in to a buffer
        try:
            with codecs.open(self.filepath, 'r', 'utf-8') as stream:
                self.buffer = stream.read()
            logger_file.info('Loaded markdown file: %s' % self.filepath)
            logger_buffer.debug(pp.pformat(self.buffer))
        except:
            self.logger.warning('Cannot load: %s' % self.filepath)
            self.buffer = None
            return False

        # Try to get the first yaml section from the file
        try:
            yamlsections = yaml.safe_load_all(self.buffer)
            for section in yamlsections:
                self.yaml = section
                logger_file.info('YAML section found')
                logger_file.debug(pp.pformat(self.yaml))
                break # Only the first yaml section is read in
        except:
            self.logger.warning('YAML loader problems: %s' % self.filepath)
            
        # If yaml section found, good.  If not create a {} yaml section.
        if not isinstance(self.yaml, dict):
            self.logger.warning('YAML section not found in md file: %s' % self.filepath)
            self.yaml = {}
        elif len(self.get_yaml().keys()) == 0:
            self.logger.warning('Loaded an empty YAML section (check for missing "" around yaml values or other syntax errors): %s' % self.filepath)
        else:
            pass

        # logger_rc = util.WebifyLogger.get('rc')
        # logger_rc.debug(pp.pformat(rc.print()))

        # If we want to preprocess the file using mustache renderer then do it
        # here.  This allows us to change the yaml frontmatter based upon the
        # larger rendering context.  Cool, eh. 
        if self.get_preprocess_frontmatter():
            logger_file.info('Preprocessing YAML front matter via mustache')
            try:
                yaml_str = yaml.dump(self.get_yaml())
                s = util.mustache_renderer(template=yaml_str, render_filepath=self.filepath, context=rc.data(), src_filepath=self.filepath)
                self.set_yaml(yaml.safe_load(s))
            except:
                self.logger.warning('Failed: preprocessing YAML front matter via mustache')
            logger_file.debug('YAML frontmatter after preprocessing')
            logger_file.debug(pp.pformat(self.get_yaml()))

        return True

    def convert(self, rc={}):
        if not self.buffer:
            return 'error', 'Load error', self.filepath

        # This allow load and convert to be separated by 
        # modification to rendering context.
        # E.g.,
        # rc.push()
        # f = MDfile(filepath, args, rc)
        # f.load()
        # rc.pop()
        # rc.push()
        # changes to rc
        # rc.pop()
        # rc.push()
        # f.convert(rc) -- convert has the same rc as passed during construction
        # rc.pop()
        rc.add(self.get_yaml())
        util.WebifyLogger.get('md-rc').debug('rendering context for %s' % self.filepath)
        util.WebifyLogger.get('md-rc').debug(pp.pformat(rc.data()))

        output_format = self.get_output_format()

        if not output_format in self.formats.keys():
            self.logger.error('Unsupported conversion format "%s": %s' % (output_format, self.filepath))
            return 'error', 'Unrecognized output format "%s"' % output_format,  self.filepath

        if self.get_create_output_file():
            output_fileext = self.get_output_fileext()
            format_ext = self.formats[output_format]['ext']
            if output_fileext and format_ext != output_fileext:
                self.logger.error('Output format "%s" doesnot match output file extension "%s": %s' % (output_format, output_fileext, self.filepath) )
                return 'error', 'Bad output file extension', self.filepath
        elif not self.is_output_format('html'):
            self.logger.error('Invalid option "do not create output file" for format "html": %s' % self.filepath)
            return 'error', 'Bad option "do not create output file"', self.filepath
        else:
            util.WebifyLogger.get('md-file').info('Output format: "%s":' % output_format)
        
        convertor = self.formats[output_format]['fn']
        return convertor(rc)

    def latexify(self, rc):
        files = [self.filepath]
        pdoc_args = PandocArguments(self.args['pandoc-var'], self.args['pandoc-meta'])

        logger_file = util.WebifyLogger.get('md-file')

        render_file = self.get_renderfile()
        if render_file:
            self.logger.warning('Ignoring render file "%s" (only supported for "html" conversion): %s' % (render_file, self.filepath))
            render_file = None            

        template_file = self.get_template()
        if template_file:
            logger_file.info('Using pandoc template file: %s' % template_file)
            pdoc_args.add('template', template_file)
            files.append(template_file)        
        else:
            logger_file.info('Using default pandoc template for "%s" format' % self.get_output_format())

        if self.get_standalone_html():
            # The default is False, so if it is true, it means that someone is messing with this flag.
            self.logger.warning('Standlone html flag is ignored when render file is specified: %s' % self.filepath)

        pdoc_args.add_flag('standalone')

        # Lets get the bib and csl files
        bib_files = self.get_bibfiles()
        self.logger.debug('Bibliography:', bib_files)
        if len(bib_files) > 0:
            files.extend(bib_files)
            pdoc_args.add('bibliography', bib_files)
            pdoc_args.add_flag('citeproc')

        csl_file = self.get_cslfile()
        self.logger.debug('CSL file: %s' % csl_file)
        if csl_file:
            files.append(csl_file)
            pdoc_args.add('csl', csl_file)
            #pdoc_args.add_var('csl-refs', True)

        # Get pandoc include files
        include_files = self.get_pandoc_include_files()
        pdoc_args.add('include-in-header',   include_files['include-in-header'])
        pdoc_args.add('include-before-body', include_files['include-before-body'])
        pdoc_args.add('include-after-body',  include_files['include-after-body'])
        logger_file.debug('Pandoc include files:')
        logger_file.debug(pp.pformat(include_files, indent=2))
        # if util.WebifyLogger.is_debug(self.logger):
        #     print('Pandoc include files:')
        #     pp.pprint(include_files, indent=2)
        files.extend(include_files['include-in-header'])
        files.extend(include_files['include-before-body'])
        files.extend(include_files['include-after-body'])

        output_filepath = self.make_output_filepath()
        logger_file.debug('Output file: %s' % output_filepath)

        if self.needs_compilation(files, output_filepath):
            logger_file.debug('Needs compilation YES')
        else:
            logger_file.debug('Needs compilation NO')
            logger_file.warning('Did not compile, file already up-to-date: %s' % output_filepath)
            return 'exists', output_filepath, self.filepath

        logger_file.info('Compiling')

        hf, hf_file_list = self.get_html_filters()
        if len(hf_file_list) > 0:
            self.logger.warning('HTML medial filters are only available when converting to html: %s' % self.filepath)

        if self.get_preprocess_buffer(): 
            self.logger.warning('Markdown mustache preprocessing is only available when converting to html: %s' % self.filepath)

        pdoc_args.add('highlight-style', self.get_highlight_style())
        pdoc_args.add_var('graphics=true')
        pdf_engine = self.get_pdf_engine()
        if pdf_engine:
            pdoc_args.add('pdf-engine', pdf_engine)

        if self.is_output_format('beamer'):
            slide_level = self.get_slide_level()
            pdoc_args.add('slide-level', slide_level)

            toc = self.get_toc()
            pdoc_args.add_flag('toc')
            
        logger_file.info('Writing to: %s' % output_filepath)
        pdoc_args.get()
        return self.compile(output_format=self.get_output_format(), pandoc_args=pdoc_args.get(), output_filepath=output_filepath)

    def to_html(self, rc):
        logger_file = util.WebifyLogger.get('md-file')

        files = [self.filepath]
        pdoc_args = PandocArguments(self.args['pandoc-var'], self.args['pandoc-meta'])

        template_file = self.get_template()
        if template_file:
            logger_file.info('Using pandoc template file: %s' % template_file)
            pdoc_args.add('template', template_file)
            pdoc_args.add_flag('standalone')
            files.append(template_file)
        elif self.get_standalone_html():
            logger_file.info('Using default pandoc template for "html" format')
            pdoc_args.add_flag('standalone')
        else:
            logger_file.info('Not using any pandoc template for "html" format')

        render_file = self.get_renderfile()
        if render_file:
            logger_file.info('Using render file: %s' % render_file)
            files.append(render_file)
        else:
            logger_file.info('Not using a render file: %s' % render_file)

        include_files = self.get_pandoc_include_files()
        pdoc_args.add('include-in-header',   include_files['include-in-header'])
        pdoc_args.add('include-before-body', include_files['include-before-body'])
        pdoc_args.add('include-after-body',  include_files['include-after-body'])
        logger_file.debug('Pandoc include files:')
        logger_file.debug(pp.pformat(include_files, indent=2))
        files.extend(include_files['include-in-header'])
        files.extend(include_files['include-before-body'])
        files.extend(include_files['include-after-body'])

        hf, hf_file_list = self.get_html_filters()
        if len(hf_file_list) > 0:
            files.extend(hf_file_list)

        if self.get_create_output_file():        
            output_filepath = self.make_output_filepath()
            logger_file.debug('Output file: %s' % output_filepath)
        else:
            output_filepath = None
            logger_file.info('Not creating output file: %s' % self.filepath)

        if self.needs_compilation(files, output_filepath):
            logger_file.debug('Needs compilation YES')
        else:
            logger_file.debug('Needs compilation NO')
            logger_file.warning('Did not compile, file already up-to-date: %s' % output_filepath)
            return 'exists', output_filepath, self.filepath

        logger_file.info('Compiling')

        if len(hf_file_list) > 0:
            logger_file.info('Applying HTML filter')
            f = HTML_Filter(hf)
            self.buffer = f.apply(self.buffer, self.filepath)                    

        if self.get_preprocess_buffer(): 
            logger_file.info('Preprocessing markdown buffer using mustache')
            self.buffer = util.mustache_renderer(template=self.buffer, render_filepath=self.filepath, context=rc.data(), src_filepath=self.filepath)
        
        pdoc_args.add('highlight-style', self.get_highlight_style())
        pdoc_args.add_flag('mathjax')
        pdoc_args.add('css', self.get_cssfiles())

        # Case 1
        if output_filepath and not render_file:
            logger_file.info('Writing to: %s' % output_filepath)
            return self.compile(output_format=self.get_output_format(), pandoc_args=pdoc_args.get(), output_filepath=output_filepath)

        # Case 2
        r = self.compile(output_format=self.get_output_format(), pandoc_args=pdoc_args.get())

        if render_file:
            rc.add({'body': markupsafe.Markup(r[1])})
            renderer_name, render_engine = self.get_renderer()
            logger_file.info('Using renderer: %s' % renderer_name)
            buffer = util.render(render_engine, render_file, rc.data(), self.filepath)
        else:
            buffer = markupsafe.Markup(r[1])

        if output_filepath:
            logger_file.info('Writing to: %s' % output_filepath)
            if util.save_to_file(output_filepath, buffer):
                return 'file', output_filepath, self.filepath
            else:
                logger_file.warning('Error saving to output file: %s' % output_filepath)
                return 'error', output_filepath, self.filepath

        logger_file.debug('Buffer created.')        
        return 'buffer', buffer, self.filepath

    def compile(self, output_format, pandoc_args, output_filepath=None):
        
        ret_type = 'file' if output_filepath else 'buffer'
        # ret_val = output_filepath

        cwd = os.getcwd()
        os.chdir(self.rootdir)
    
        logger_pandoc = util.WebifyLogger.get('pandoc')
        logger_pandoc.debug("output format: %s" % output_format)
        logger_pandoc.debug("pandoc args:")
        logger_pandoc.debug(pp.pformat(pandoc_args))

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
            ret = 'error', '', self.filepath

        os.chdir(cwd)

        return ret

    def make_output_filepath(self):
        output_format = self.get_output_format()
        output_filepath = self.get_output_filepath()
        assert(output_filepath)
        return output_filepath + self.formats[output_format]['ext']

    def make_output_fileext(self):
        output_format = self.get_output_format()
        return self.formats[output_format]['ext']

    def needs_compilation(self, files, output_filepath):
        logger_timestamps = util.WebifyLogger.get('md-timestamps')
        logger_timestamps.debug('Checking timestamps.')

        if not output_filepath:
            logger_timestamps.debug('\tOutput filepath not specified.')
            logger_timestamps.debug('\tCompilation needed.')
            return True

        if self.get_ignore_times():
            logger_timestamps.debug('\tIgnore times flag is True')
            logger_timestamps.debug('\tCompilation needed.')
            return True
        
        if output_filepath and not os.path.isfile(output_filepath): 
            logger_timestamps.debug('\tOutput filepath is not a file %s' % output_filepath)
            logger_timestamps.debug('\tCompilation needed.')
            return True

        # output_filepath is a file
        output_filepath_mtime =  os.path.getmtime(output_filepath)
        logger_timestamps.debug('\tOutput filepath: %s [%s]' % (output_filepath, str(output_filepath_mtime)))
        for f in files:
            if os.path.isfile(f):
                f_mtime = os.path.getmtime(f)
                logger_timestamps.debug('\tCheck: %s [%s]' % (f, str(f_mtime)))
                if f_mtime > output_filepath_mtime:
                    logger_timestamps.debug('\tCompilation needed.')
                    return True
            else:
                logger_timestamps.debug('\tIgnoring %s.  Not a file.' % f)

        logger_timestamps.debug('\tCompilation not needed.')
        return False

    def get_availability(self):
        x = self.get_value('availability')
        return tm.read_time('start', x), tm.read_time('end', x)

    def get_value(self, name):
        if name in self.args.keys() and self.args[name] != None:
            return self.args[name]

        if name in self.yaml.keys():
            return self.yaml[name]

        return self.defaults[name]

    def get_standalone_html(self):
        value = self.get_value('standalone-html')
        util.WebifyLogger.get('file').debug('standalone-html: %s' % str(value))
        return value

    def get_create_output_file(self):
        value = self.get_value('create-output-file')
        util.WebifyLogger.get('file').debug('Create output file: %s' % str(value))
        return value

    def get_highlight_style(self):
        value = self.get_value('highlight-style')
        util.WebifyLogger.get('file').debug('Highlight style: %s' % value)
        return value

    def get_ignore_times(self):
        value = self.get_value('ignore-times')
        util.WebifyLogger.get('file').debug('Ignore compilation times: %s' % value)
        return value

    def get_yaml(self):
        try:
            return self.yaml
        except:
            self.logger.error('get_yaml called before loading file %s' % self.filepath)
            return {}

    def set_yaml(self, data):
        self.yaml = data

    def get_html_filters(self):
        file_list = []
        hf = {'html-img': None, 'html-imgs': None, 'html-vid': None, 'html-vids': None}

        for key in hf.keys():
            if key in self.yaml.keys():
                if isinstance(self.yaml[key], str):
                    f = os.path.normpath(os.path.join(self.rootdir, self.yaml[key]))
                    if os.path.isfile(f):
                        hf[key] = f
                        file_list.append(f)
                        util.WebifyLogger.get('file').info('Found HTML filter file: %s found in %s' % (f, self.filepath))
                    else:
                        self.logger.warning('Ignoring HTML filter file: %s found in %s' % (f, self.filepath))
                else:
                    self.logger.warning('Ignoring HTML filter key: %s' % (self.filepath))
        return hf, file_list

    def get_output_format(self):
        # assert(self.buffer)

        if self.output_format:
            return self.output_format

        self.output_format = self.get_value('to')
        return self.output_format

    def get_pdf_engine(self):
        # assert(self.buffer)
        return self.get_value('pdf-engine')

    def get_preprocess_frontmatter(self):
        # assert(self.buffer)
        value = self.get_value('preprocess-frontmatter')
        util.WebifyLogger.get('file').debug('Preprocess frontmatter: %s' % str(value))
        return value

    def get_preprocess_buffer(self):
        # assert(self.buffer)
        value = self.get_value('preprocess-buffer')
        if value == None:
            if self.is_output_format('html'):
                return True
            else:
                return False
        util.WebifyLogger.get('file').debug('Preprocess buffer: %s' % str(value))
        return value

    def get_files(self, key):
        try:
            f1 = self.yaml[key] if isinstance(self.yaml[key], list) else [self.yaml[key]]
            f1 = [x for x in f1 if x is not None]
        except:
            f1 = []
        try:
            f2 = self.args[key] if isinstance(self.args[key], list) else [self.args[key]]
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

    def get_output_filepath(self):
        if 'output-filepath' in self.args.keys():
            return self.args['output-filepath']
        return None

    def get_output_fileext(self):
        if 'output-fileext' in self.args.keys():
            return self.args['output-fileext']
        return None

    def is_output_format(self, output_format_str):
        return output_format_str == self.get_output_format()

    def get_renderfile(self):
        file = self.pick_last_file('render')
        file = os.path.normpath(os.path.join(self.rootdir, os.path.expandvars(file))) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find render file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    def get_template(self):
        file = self.pick_last_file('template')
        file = os.path.normpath(os.path.join(self.rootdir, os.path.expandvars(file))) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find template file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    def get_cssfiles(self):
        return self.pick_all_files('css', relpath=True)

    # def get_bibfile(self):
    #     file = self.pick_last_file('bibliography')
    #     file = os.path.normpath(os.path.join(self.rootdir, os.path.expandvars(file))) if file else None
    #     if file and not os.path.isfile(file):
    #         self.logger.warning('Cannot find bibliography file:\n\t- %s\n\t- %s' % (self.filepath, file))
    #         return None
    #     return file

    def get_bibfiles(self):
        files = []
        for file in self.pick_all_files('bibliography'):
            file = os.path.normpath(os.path.join(self.rootdir, os.path.expandvars(file)))
            if not os.path.isfile(file):
                self.logger.warning('Cannot find bibliography file:\n\t- %s\n\t- %s' % (self.filepath, file))
            else:
                files.append(file)
        return files

    def get_cslfile(self):
        file = self.pick_last_file('csl')
        file = os.path.normpath(os.path.join(self.rootdir, os.path.expandvars(file))) if file else None
        if file and not os.path.isfile(file):
            self.logger.warning('Cannot find csl file:\n\t- %s\n\t- %s' % (self.filepath, file))
            return None
        return file

    # def get_cslfiles(self):
    #     files = []
    #     for file in self.pick_all_files('csl'):
    #         file = os.path.normpath(os.path.join(self.rootdir, os.path.expandvars(file)))
    #         if not os.path.isfile(file):
    #             self.logger.warning('Cannot find csl file:\n\t- %s\n\t- %s' % (self.filepath, file))
    #         else:
    #             files.append(file)
    #     return files

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
        # assert(self.buffer)
        value = self.get_value('slide-level')
        util.WebifyLogger.get('file').debug('slide-level: %s' % str(value))
        return value

    def get_toc(self):
        value = self.get_value('toc')
        util.WebifyLogger.get('file').debug('TOC: %s' % value)
        return value

    def get_renderer(self):
        # assert(self.buffer)
        value = self.get_value('renderer')
        if not value in ['mustache', 'jinja2']:
            self.logger.warning('Invalid template engine "%s" found in %s.  Valid values are "mustache" or "jinja"' % (renderer, self.filepath))
            value = self.defaults['renderer']
        if value == 'jinja2':
            return 'jinja2', util.jinja2_renderer
        return 'mustache', util.mustache_renderer

# def version_info():
#     str =  '  Mdfile2:    %s\n' % __version__
#     str += '  logfile:    %s\n' % __logfile__ 
#     str += '  Git info:   %s\n' % util.get_gitinfo()
#     str += '  Python:     %s.%s\n' % (sys.version_info[0],sys.version_info[1])
#     str += '  Pypandoc:   %s\n' % pypandoc.__version__
#     str += '  Pyyaml:     %s, and \n' % yaml.__version__
#     str += '  Pystache:   %s.' % pystache.__version__
#     return str

def version_info():
    return __version__

if __name__ == '__main__':

    terminal = util.Terminal()
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)
    cur_dir = os.getcwd()

    # Command line arguments
    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('mdfile', help='Markdown file.  Options specified on commandline override those in the frontmatter.')
    cmdline_parser.add_argument('-o','--output', action='store', default=None, help='Output path.  A file or a directory name.')
    cmdline_parser.add_argument('-f','--format', action='store', default=None, help='Output format: html, pdf, beamer, latex.')
    cmdline_parser.add_argument('-i', '--ignore-times', action='store_true', default=False, help='Forces the generation of the output file even if the source file has not changed')
    
    cmdline_parser.add_argument('--standalone-html', action='store_true', default=False, help='Use this option if you want to use default pandoc html5 template.')
    cmdline_parser.add_argument('--do-not-create-output-file', action='store_true', default=False, help='Do not create an output file.  This is only available when converting to html.  This option is really only useful when using mdfile2 within webify.')

    cmdline_parser.add_argument('--version', action='version', version=version_info())
    cmdline_parser.add_argument('-v','--verbose', action='store_true', default=False, help='Turn verbose on.')
    cmdline_parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages.')
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Writes out a log file.')

    cmdline_parser.add_argument('--debug-buffer', action='store_true', default=False, help='Show file buffer contents.')
    cmdline_parser.add_argument('--debug-file', action='store_true', default=False, help='Debug messages regarding file loading.')
    cmdline_parser.add_argument('--debug-render', action='store_true', default=False, help='Debug messages regarding template rendering.')
    cmdline_parser.add_argument('--debug-timestamps', action='store_true', default=False, help='Debug messages regarding file timestamps.')
    cmdline_parser.add_argument('--debug-rc', action='store_true', default=False, help='Debug messages regarding yaml front matter and rendering context.')
    cmdline_parser.add_argument('--debug-pandoc', action='store_true', default=False, help='Debug messages regarding pandoc.')
    
    cmdline_parser.add_argument('--render-file', action='store', default=None, help='Path to render file (used for html only).  The generated html contents are available as the body key to be consumed within the specified render file.')
    cmdline_parser.add_argument('--template-file', action='store', default=None, help='Path to pandoc template file.')
    cmdline_parser.add_argument('--include-in-header', nargs='*', action='append', default=None, help='Path to file that will be included in the header.  Typically LaTeX preambles.')
    cmdline_parser.add_argument('--bibliography', nargs='*', action='append', default=None, help='Space separated list of bibliography files.')
    cmdline_parser.add_argument('--css', nargs='*', action='append', default=None, help='Space separated list of css files.')
    cmdline_parser.add_argument('--csl', action='store', default=None, help='csl file, only used when a bibfile is specified either via commandline or via yaml frontmatter')
    cmdline_parser.add_argument('--highlight-style', action='store', default=None, help='Specify a highlight-style.  See pandoc --list-highlight-styles.')
    cmdline_parser.add_argument('--yaml', nargs='*', default=[], action='append', help='Space separated list of extra yaml files to process.')

    cmdline_parser.add_argument('--do-not-preprocess-frontmatter', action='store_true', default=False, help='Turns off mustache preprocessing for yaml frontmatter.')
    cmdline_parser.add_argument('--do-not-preprocess-buffer', action='store_true', default=False, help='Turns off mustache preprocessing for buffer.  Buffer mustache preprocessing is only available for conversion to html.')

    cmdline_parser.add_argument('--slide-level', action='store', default=None, help='Slide level argument for pandoc (for beamer documents)')

    cmdline_parser.add_argument('--pdf-engine', action='store', default=None, help='PDF engine used to generate pdf. The default is vanilla LaTeX.  Possible options are lualatex or tetex.')
    cmdline_parser.add_argument('--renderer', action='store', default=None, help='Specify whether to use "mustache" or "jinja2" engine.  "jinja2" is the default choice.')
    
    cmdline_parser.add_argument('--pandoc-var', action='append', default=[], help='A mechanism for providing -V Name:Val for pandoc.')
    cmdline_parser.add_argument('--pandoc-meta', action='append', default=[], help='A mechanism for providing -M Name:Val for pandoc.')

    cmdline_args = cmdline_parser.parse_args()
  
    css_files = cmdline_args.css[0] if cmdline_args.css else []
    include_in_header = [os.path.join(cur_dir, f) for f in (cmdline_args.include_in_header[0] if cmdline_args.include_in_header else [])]
    bibliography = os.path.join(cur_dir, cmdline_args.bibliography) if cmdline_args.bibliography else None
    csl = os.path.join(cur_dir, cmdline_args.csl) if cmdline_args.csl else None
    template = os.path.join(cur_dir, cmdline_args.template_file) if cmdline_args.template_file else None
    render = os.path.join(cur_dir, cmdline_args.render_file) if cmdline_args.render_file else None
    
    # Setting up logging
    logfile = None if not cmdline_args.log else __logfile__
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug   else loglevel
    logger = util.WebifyLogger.make(name='main', loglevel=loglevel, logfile=logfile)

    util.WebifyLogger.make(name='render',     loglevel=logging.DEBUG if cmdline_args.debug_render else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='md-rc',         loglevel=logging.DEBUG if cmdline_args.debug_rc else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='md-file',       loglevel=logging.DEBUG if cmdline_args.debug_file else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='md-timestamps', loglevel=logging.DEBUG if cmdline_args.debug_timestamps else loglevel, logfile=logfile)
    util.WebifyLogger.make(name='md-buffer',     loglevel=logging.DEBUG if cmdline_args.debug_buffer else logging.WARNING, logfile=logfile)
    util.WebifyLogger.make(name='pandoc',     loglevel=logging.DEBUG if cmdline_args.debug_pandoc else loglevel, logfile=logfile)
    
    # Go
    logger.info('mdfile version %s' % version_info())
    logger.debug('Prog name:    %s' % prog_name)
    logger.debug('Prog dir:     %s' % prog_dir)
    logger.debug('Current dir:  %s' % cur_dir)
    logger.debug(pp.pformat(cmdline_args))


    # if util.WebifyLogger.is_debug(logger):
    #     print('Commandline arguments:')
    #     print('  --output:                       ', cmdline_args.output)
    #     print('  --format:                       ', cmdline_args.format)
    #     print('  --template-file:                ', template)
    #     print('  --render-file                   ', render)
    #     print('  --include-in-header:            ', include_in_header)
    #     print('  --bibliography:                 ', bibliography)
    #     print('  --css:                          ', css_files)
    #     print('  --csl:                          ', csl)
    #     print('  --highlight-style:              ', cmdline_args.highlight_style)
    #     print('  --do-not-preprocess-frontmatter:', cmdline_args.do_not_preprocess_frontmatter)
    #     print('  --do-not-preprocess-buffer:     ', cmdline_args.do_not_preprocess_buffer)
    #     print('  --ignore-times:                 ', cmdline_args.ignore_times)
    #     print('  --output:                       ', cmdline_args.output)
    #     print('  --slide-level:                  ', cmdline_args.slide_level)
    #     print('  --pdf-engine:                   ', cmdline_args.pdf_engine)
    #     print('  --verbose:                      ', cmdline_args.verbose)
    #     print('  --renderer:                     ', cmdline_args.renderer)
    #     print('  --do-not-create-output-file:    ', cmdline_args.do_not_create_output_file)
    #     print('  --standalone-html:              ', cmdline_args.standalone_html)

    # Input file
    filepath = os.path.normpath(os.path.join(cur_dir, cmdline_args.mdfile))
    filename = os.path.basename(filepath)
    filedir = os.path.split(filepath)[0]

    # Output file
    if cmdline_args.output == None:
        output_filename, _ = os.path.splitext(filename)
        output_fileext = ''
        output_dir = cur_dir
    else:
        d, f = os.path.dirname(cmdline_args.output), os.path.basename(cmdline_args.output)
        if not d:
            output_dir = cur_dir
        elif not os.path.isdir(d):
            logger.error('Output directory not found: %s' % d)
            exit(-1)
        else:
            output_dir = d

        if not f:
            output_filename, _ = os.path.splitext(filename)
            output_fileext = ''
        else:
            output_filename, output_fileext = os.path.splitext(f)
    output_filepath = os.path.normpath(os.path.join(output_dir, output_filename))

    logger.debug('File names:')
    logger.debug('  filepath:        %s' % filepath)
    logger.debug('  filename:        %s' % filename)
    logger.debug('  filedir:        %s' % filedir)
    logger.debug('  output_filename: %s' % output_filename)
    logger.debug('  output_fileext:  %s' % output_fileext)
    logger.debug('  output_dir:      %s' % output_dir)
    logger.debug('  output_filepath: %s' % output_filepath)

    args = { 'to': cmdline_args.format,
               'template': template,
               'render': render,
               'bibliography': bibliography,
               'css': css_files,
               'csl': csl,
               'highlight-style': cmdline_args.highlight_style,
               'ignore-times': cmdline_args.ignore_times,
               'preprocess-frontmatter': False if cmdline_args.do_not_preprocess_frontmatter else None,
               'preprocess-buffer': False if cmdline_args.do_not_preprocess_buffer else None,
               'include-in-header': include_in_header,
               'slide-level': cmdline_args.slide_level,
               'pdf-engine': cmdline_args.pdf_engine,
               'verbose': cmdline_args.verbose,
               'renderer': cmdline_args.renderer,
               'output-fileext': output_fileext,
               'output-filepath': output_filepath,
               'create-output-file': False if cmdline_args.do_not_create_output_file else None,
               'standalone-html': None if not cmdline_args.standalone_html else cmdline_args.standalone_html,
               'pandoc-var': cmdline_args.pandoc_var,
               'pandoc-meta': cmdline_args.pandoc_meta}

    logger.debug('args:')
    logger.debug(pp.pformat(args))    

    meta_data = {
        '__version__': __version__,
        '__filepath__': filepath.replace('\\','/'),
        '__root__': filedir.replace('\\','/'),
        '__time__': datetime.datetime.now()
    }

    rc = RenderingContext.RenderingContext()
    rc.push()
    rc.add(meta_data)

    for yaml_filepath in cmdline_args.yaml:
        logger.debug('Loading yaml file: %s', yaml_filepath[0])
        yaml_file = yamlfile.YAMLfile(yaml_filepath[0])
        yaml_file.load()
        rc.add(yaml_file.data)

    m = MDfile(filepath=filepath, args=args)
    m.load(rc=rc)
    ret_type, ret_val, _ = m.convert(rc=rc)
    logger.debug('Status:  %s' % ret_type)
    logger.debug('Message: %s' % ret_val)
    if ret_type == 'file':
        logger.debug('Success: %s' % ret_val)
    elif ret_type == 'error':
        logger.error('Failure: %s' % ret_val)
    elif ret_type == 'exists':
        pass
    elif ret_type == 'buffer':
        print('Status: %s' % ret_type)
        print('Buffer:\n%s' % ret_val)
    else:
        logger.error('Unknown error: (%s, %s...)' % (ret_type, ret_val[:100]))

    exit(0)
