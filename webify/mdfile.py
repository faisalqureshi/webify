import logging
import yaml
import codecs
import argparse
import pypandoc
import util
import os
import re
import mdfilters
import sys
import uuid


class PandocArguments:
    def __init__(self):
        self._pdoc_args = []

    def add_var(self, var, val):
        self._pdoc_args.append("-V %s:%s" % (var, val))
        
    def add_flag(self, options):
        if isinstance(options, list):
            for o in options:
                self._pdoc_args.append("--%s" % o)
        else:
            self._pdoc_args.append("--%s" % options)
        
    def add(self, option, vals):
        if isinstance(vals, list):
            for v in vals:
                self._pdoc_args.append("--%s=%s" % (option, v))
        else:
            self._pdoc_args.append("--%s=%s" % (option, vals))

    def get(self):
        return self._pdoc_args

class MDfile:
    """
    Class that implements MD file conversion to other formats.  
    'pandoc' is used to convert MD file to other formats.   
    Yaml front matter is used to control how an MD file is converted. 

    Example MD file:

    to: html* | pdf | beamer
    template: None* | path/to/pandoc-template-file
    render: None* | path/to/mustache-template-file
    bibliography: None | path/to/bibfile

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
    
    bibliography: None* | path/to/bib file

    csl: None* | path/to/csl file
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
    """
    def __init__(self, filepath, rootdir=None, dbglevel=logging.WARNING, extras=None, filters=None, mtime=None):
        self.logger = util.setup_logging('MDfile', dbglevel=dbglevel)

        self.filepath = filepath
        self.basepath, self.filename = os.path.split(self.filepath)
        if rootdir:
            self.rootdir = rootdir
        else:
            self.rootdir = self.basepath
        self.yaml = None
        self.buffer = None
        self.extras = extras
        self.filters = filters
        self.mtime = mtime
        
        self.logger.debug('%s -- initializing md file' % filepath)
        self.logger.debug('\tbasepath: %s' % self.basepath)
        self.logger.debug('\trootdir: %s' % self.rootdir)

        self.supported = [ 'html', 'beamer', 'pdf', 'latex' ]
        self.extensions = {'html': 'html', 'beamer': 'pdf', 'pdf': 'pdf', 'latex': 'tex'}

        self.rc = {'pushed': None, 'changes': {}, 'additions': []}

        self.files = {}
        
    def push_rc(self, rc):
        self.rc['pushed'] = uuid.uuid4()
        yaml_block = self.get_yaml()
        try:
            for k in yaml_block.keys():
                if k in rc.keys(): self.rc['changes'][k] = rc[k]
                else: self.rc['additions'].append(k)
                rc[k] = yaml_block[k]
        except:
            self.rc = {'pushed': None, 'changes': {}, 'additions': []}

        rc['this-path'] = self.basepath
        rc['this-file'] = self.filename
        rc['this-mtime'] = self.mtime
        
        return rc

    def pop_rc(self, rc):
        for k in self.rc['changes'].keys():
            rc[k] = self.rc['changes'][k]
        for k in self.rc['additions']:
            rc.pop(k)

        rc.pop('this-path')
        rc.pop('this-file')
        rc.pop('this-mtime')
            
        self.rc = {'pushed': None, 'changes': {}, 'additions': []}
        return rc
        
    def check_yaml(self):
        keys = ['to', 'template', 'render', 'bibliography', 'css', 'include-after-body', 'include-before-body', 'include-in-header', 'title', 'author', 'date', 'institute', 'titlegraphics', 'subtitle']
        for key in self.yaml.keys():
            if not key in keys:
                self.logger.debug('Key %s not supported' % key)

    def load(self):
        try:
            with codecs.open(self.filepath, 'r') as stream:
                self.buffer = stream.read().decode('utf-8')
            self.logger.debug('%s -- loaded MD file:' % self.filepath)
        except:
            self.logger.warning('%s -- error reading MD file' % self.filepath)
            self.buffer = ''
            return False

        try:
            yamlsections = yaml.load_all(self.buffer)

            for section in yamlsections:
                self.yaml = section
                self.logger.debug('%s -- YAML section found in md file' % self.filepath)
                break # Only the first yaml section is read in

            self.check_yaml()

        except:
            self.logger.debug('%s -- YAML section not found in md file' % self.filepath)

        if self.logger.getEffectiveLevel() == logging.DEBUG:
            #self.pprint()
            pass
        return True

    def pprint(self):
        print '---------------------------------------------'
        print 'MD file: ', self.filepath
        print 'Buffer:'
        print self.buffer
        print 'YAML:'
        print self.yaml
        print '---------------------------------------------'

    def apply_filters(self):
        try:    
            for f in self.filters['html']:
                self.buffer = f(self.filepath, self.rootdir, self.buffer)
        except:
            pass

    def get_rel_path(self, filepath):
        return util.make_rel_path(rootdir = self.rootdir, basepath = self.basepath, filepath = filepath)
        
    def get_abs_path(self, filepath):
        return util.make_abs_path(rootdir = self.rootdir, basepath = self.basepath, filepath = filepath)

    def compile(self, to, args, outputfile=None):

        if self.logger.getEffectiveLevel() == logging.DEBUG:
            print 'pandoc compilation:'
            print '\tto:', to
            print '\targs:', args
            print '\toutputfile:', outputfile

        cwd = os.getcwd()
        os.chdir(self.basepath)
        try:
            if to == 'html':
                html = pypandoc.convert_text(self.buffer, to=to, format='md', extra_args = args)
                retval = 'html', html
            else:
                pypandoc.convert_text(self.buffer, to=to, format='md', outputfile=outputfile, extra_args = args)
                retval = 'file', outputfile
        except:
            self.logger.error('%s -- pandoc conversion failed to %s' % (self.filename, to))
            print 'pandoc compilation:'
            print '  to:', to
            print '  args:', args
            print '  outputfile:', outputfile            
            retval = 'error', 'Error converting %s' % self.filepath
        os.chdir(cwd)
                
        return retval
    
    def convert(self, outputfile, use_cache=False):
        assert self.buffer

        to_format = self.get_output_format()
        if to_format in self.supported:
            self.logger.debug('%s -- Using Pandoc to convert MD to %s' % (self.filepath, to_format))
        else:
            self.logger.error('%s -- Unsupported conversion format: %s' % (self.filepath, to_format))
            return 'error', 'Error converting %s' % self.filepath 

        if not outputfile:
            outputfile = os.path.splitext(self.filepath)[0] + '.' + self.extensions[to_format]
        elif os.path.splitext(outputfile)[1] == '':
            outputfile = outputfile + '.' + self.extensions[to_format]
        else:
            pass
        self.logger.debug('%s -- MD convert, outputfile: %s' % (self.filepath, outputfile))

        pdoc_args = PandocArguments()

        render_file = self.get_renderfile()
        if render_file: pdoc_args.add_flag('standalone')
        
        template_file = self.get_template()
        pdoc_args.add('template', template_file)

        include_files = self.get_pandoc_include_files()
        pdoc_args.add('include-in-header', include_files['include-in-header'])
        pdoc_args.add('include-before-body', include_files['include-before-body'])
        pdoc_args.add('include-after-body', include_files['include-after-body'])

        bib_file = self.get_bibfile()
        pdoc_args.add('bibliography', bib_file)
        
        csl_file = self.get_cslfile()
        pdoc_args.add('csl', csl_file)
        
        if to_format == 'html':
            pdoc_args.add_flag('mathjax')
            pdoc_args.add('highlight-style','pygments')
            
            css_files = self.get_cssfiles()
            pdoc_args.add('css', css_files)

            self.apply_filters()

            return self.compile(to=to_format, args=pdoc_args.get())

        # if the desired output is a pdf or beamer file.
        elif to_format in ['pdf', 'beamer', 'latex']:

            if not self.needs_compilation(use_cache, outputfile):
                self.logger.info('%s - output already exists.  Nothing to do here.' % self.filepath)
                return 'file', outputfile

            if render_file:
                self.logger.warning('%s -- Render option in yaml frontmatter unsupported for %s format' % (self.filepath, to_format))

            pdoc_args.add('highlight-style','kate')
            pdoc_args.add_var('graphics','true')

            return self.compile(to=to_format, args=pdoc_args.get(), outputfile=outputfile)

        else:
            return 'error', 'Error converting %s' % self.filepath

    def needs_compilation(self, use_cache, outputfile):
        if not use_cache:
            return True

        if not util.is_valid_file(outputfile):
            return True

        srcs = []
        for k in ['template', 'csl', 'bibliography', 'template']:
            for f in self.files[k]:
                srcs.append(f)
        return util.srcs_newer_than_dest(srcs, outputfile)
        
    def get_yaml(self):
        assert(self.buffer)
        return self.yaml

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
        
    def add_e_to_list(self, e, l):
        if isinstance(e, list):
            l.extend(e)
        elif e:
            l.append(e)
        else:
            pass
        return l

    def get_files(self, key):
        assert(self.buffer)

        files = []

        try:
            files = self.add_e_to_list(self.yaml[key], files)
        except:
            pass

        try:
            files = self.add_e_to_list(self.extras[key], files)
        except:
            pass

        return files

    def make_rel_path(self, files, key=None):
        paths = []
        for f in files:
            paths.append(self.get_rel_path(f))
        return paths
            
    def make_abs_path(self, files, key):
        paths = []
        for f in files:
            p = self.get_abs_path(f)
            if not os.path.isfile(p):
                self.logger.warning('%s -- Cannot find "%s" file: %s' % (self.filepath, key, p))
            else:
                paths.append(p)
        return paths

    def pick_last(self, key, pathfunc):
        files = self.get_files(key)

        if len(files) == 0:
            self.files[key] = []
        else:
            self.files[key] = pathfunc([files[-1]], key)

        return self.files[key]

    def pick_all(self, key, pathfunc):
        files = self.get_files(key)
        self.files[key] = pathfunc(files, key)
        return self.files[key]
    
    def get_renderfile(self):
        assert(self.buffer)

        key = 'render'
        if key in self.files.keys():
            return self.files[key]
            
        files = self.make_abs_path(self.get_files(key), key)
        if len(files) > 0: self.files[key] = files[0]
        else: self.files[key] = None
            
        return self.files[key]

    def get_template(self):
        assert(self.buffer)

        key = 'template'
        if key in self.files.keys():
            return self.files[key]
        return self.pick_last(key, self.make_abs_path)
        
    def get_cssfiles(self):
        assert(self.buffer)

        key = 'css'
        if key in self.files.keys():
            return self.files[key]
        return self.pick_all(key, self.make_rel_path)
        
    def get_bibfile(self):
        assert(self.buffer)

        key = 'bibliography'
        if key in self.files.keys():
            return self.files[key]
        return self.pick_last(key, self.make_abs_path)
        
    def get_cslfile(self):
        assert(self.buffer)

        key = 'csl'
        if key in self.files.keys():
            return self.files[key]
        return self.pick_last(key, self.make_abs_path)
            
    def get_pandoc_include_files(self):
        assert(self.buffer)

        f = {'include-after-body': [], 'include-before-body':[], 'include-in-header': []}
        for i in f.keys():
            f[i] = self.make_abs_path(self.get_files(i), i)
        return f
    
    def get_copy_to_destination(self):
        assert(self.buffer)

        try:
            return self.yaml['copy-to-destination']
        except:
            return False
                
if __name__ == '__main__':

    global prog_name, prog_dir
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)

    parser = argparse.ArgumentParser()
    parser.add_argument('mdfile', help='MD file.  Options specified on commandline override those specified in the file yaml block.')
    parser.add_argument('-y', '--yaml', nargs='*', action='append', help='Space separated list of extra yaml files to process')
    parser.add_argument('-s','--css', nargs='*', action='append', help='Space separated list of css files')
    parser.add_argument('-c','--csl', action='store', default=None, help='csl file, only used when a bibfile is specified either via commandline or via yaml frontmatter')
    parser.add_argument('-v','--verbose', action='store_true', default=False, help='Turn verbose on')
    parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages')
    parser.add_argument('-f','--format', action='store', default=None, help='Output format: html, pdf, beamer, latex')
    parser.add_argument('-t','--template', action='store', default=None, help='Path to pandoc template file')
    parser.add_argument('-b','--bibliography', action='store', default=None, help='Path to bibliography file')
    parser.add_argument('--no-cache', action='store_true', default=False, help='Forces to generated a new pdf file even if md files in not changed.')
    parser.add_argument('--media-filters', action='store_true', default=False, help='Sets media filters flag to true.  Check source code.')

    args = parser.parse_args()

    dbglevel = logging.INFO
    if args.debug:
        dbglevel = logging.DEBUG
    elif args.verbose:
        dbglevel = logging.INFO
      
    css_files = []
    if args.css:
        css_files = args.css[0]
      
    if dbglevel == logging.DEBUG:
        print 'Commandline arguments:'
        print '\tformat', args.format
        print '\ttemplate', args.template
        print '\tbibliography', args.bibliography
        print '\tcss', css_files
        print '\tcsl', args.csl

    extras = { 'format': args.format, 'template': args.template, 'bibliography': args.bibliography, 'css': css_files, 'csl': args.csl }

    cwd = os.getcwd()
    filepath = os.path.normpath(os.path.join(cwd, args.mdfile))
    if dbglevel == logging.DEBUG:
        print 'cwd:', cwd
        print 'filepath', filepath

    filters = None
    if args.media_filters:
        html_media = mdfilters.HTML_Media(filterdir=os.path.join(prog_dir,'filters'))
        filters = {'html': [html_media.apply]}

    m = MDfile(filepath=filepath, rootdir='/', dbglevel=dbglevel, extras=extras, filters=filters)
    if not m.load():
        print 'Exiting.  Nothing to be done here.'
        exit(0)

    fmt, data = m.convert(outputfile=None, use_cache=not args.no_cache)
    if m.logger.getEffectiveLevel() == logging.DEBUG:
        print 'Format:', fmt
        print 'Data:', data

    if fmt == 'html':
        util.save_to_html(data, util.make_different_extension(args.mdfile, '.html'), logger=None)

    yamlfiles = []
    if args.yaml:
        yamlfiles.extend(args.yaml[0])

    if not len(yamlfiles) > 0:
        exit(0)

    import yamlfile, renderingcontext
    rc = renderingcontext.RenderingContext()
    for f in yamlfiles:
        y = yamlfile.YAMLfile(f)
        rc.add_yamlfile(y)
    rc.add_key_val('body', m.get_body())

    import mustachefile
    template_file = util.make_actual_path(rootdir = '/', basepath = m.basepath, template_file = m.get_renderfile())    
    m1 = mustachefile.Mustachefile(template_file)
    m1.load()
    data = m1.render(rc)
    if fmt == 'html':
        util.save_to_html(data, util.make_different_extension(args.mdfile, '.html'), logger=None)

