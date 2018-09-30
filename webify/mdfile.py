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
import pprint as pp
import mustachefile

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

    to: html* | pdf | beamer | latex (very useful during debugging)
    template: None* | path/to/pandoc-template-file
    render: None* | path/to/mustache-template-file

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

    bibliography: None* | path/to/bib file

    csl: None* | path/to/csl file

    preprocess-mustache: None* | true or false
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
    def __init__(self, filepath, rootdir=None, dbglevel=logging.WARNING, extras=None, mtime=None, logger=None, logfile=None):

        self.dbglevel = dbglevel
        self.logfile = logfile

        if not logger:
            self.logger = util.setup_logger('MDfile', dbglevel=dbglevel, logfile=logfile)
        else:
            self.logger = logger

        self.filepath = filepath
        self.basepath, self.filename = os.path.split(self.filepath)
        if rootdir:
            self.rootdir = rootdir
        else:
            self.rootdir = self.basepath
        self.yaml = None
        self.buffer = None
        self.extras = extras
        self.mtime = mtime

        self.logger.debug('Initializing md file\n\t - filename: %s' % self.filename)
        self.logger.debug('\t - basepath: %s' % self.basepath)
        self.logger.debug('\t - rootdir: %s' % self.rootdir)

        self.supported = [ 'html', 'beamer', 'pdf', 'latex' ]
        self.extensions = {'html': 'html', 'beamer': 'pdf', 'pdf': 'pdf', 'latex': 'tex'}

        self.supported_keys = ['to', 'template', 'render', 'bibliography', 'css', 'include-after-body', 'include-before-body', 'include-in-header', 'title', 'author', 'date', 'institute', 'titlegraphics', 'subtitle', 'preprocess-mustache']

        self.rc = {'pushed': None, 'changes': {}, 'additions': []}

        self.files = {}

    def log_msg(self, msg):
        pass

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
        #keys = ['to', 'template', 'render', 'bibliography', 'css', 'include-after-body', 'include-before-body', 'include-in-header', 'title', 'author', 'date', 'institute', 'titlegraphics', 'subtitle']
        for key in self.yaml.keys():
            if not key in self.supported_keys:
                self.logger.debug('Key %s not supported' % key)

    def load(self):
        try:
            with codecs.open(self.filepath, 'r', 'utf-8') as stream:
                self.buffer = stream.read()
                if not isinstance(self.buffer, unicode):
                    self.buffer = self.buffer.decode('utf-8')
            self.logger.info('Loaded file')
        except:
            self.logger.warning('Cannot read MD file\n\t - %s' % self.filepath)
            self.buffer = ''
            return False

        try:
            yamlsections = yaml.load_all(self.buffer)

            for section in yamlsections:
                self.yaml = section
                self.logger.info('YAML section found')
                if self.logger.getEffectiveLevel() == logging.DEBUG:
                    pp.pprint(self.yaml)
                break # Only the first yaml section is read in

            # self.check_yaml()

        except:
            self.logger.warning('YAML section not found in md file\n\t - filepath: %s' % self.filepath)

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

    def get_rel_path(self, filepath):
        return util.make_rel_path(rootdir = self.rootdir, basepath = self.basepath, filepath = filepath)

    def get_abs_path(self, filepath):
        return util.make_abs_path(rootdir = self.rootdir, basepath = self.basepath, filepath = filepath)

    def compile(self, to, args, outputfile=None):

        self.logger.debug('Pandoc conversion\n\t - filename: %s' % self.filepath)
        self.logger.debug('\t - to: %s' % to)
        self.logger.debug('\t - args: %s' % args)
        self.logger.debug('\t - outputfile: %s' % outputfile)

        cwd = os.getcwd()
        os.chdir(self.basepath)
        try:
            if to == 'html':
                html = pypandoc.convert_text(self.buffer, to=to, format='md', extra_args = args)
                retval = 'html', html
            else:
                pypandoc.convert_text(self.buffer, to=to, format='md', outputfile=outputfile, extra_args = args)
                retval = 'file', outputfile
                self.logger.info('Saved %s file: %s' % (to, outputfile))
        except:
            self.logger.error('Pandoc conversion failed\n\t - filename: %s' % self.filepath)
            self.logger.error('\t - to: %s' % to)
            self.logger.error('\t - args: %s' % args)
            self.logger.error('\t - outputfile: %s' % outputfile)
            retval = 'error', 'Error converting %s' % self.filepath
        os.chdir(cwd)

        return retval

    def make_output_filename(self, outputfile, to_format):
        #print outputfile, to_format, self

        if not outputfile:
            outputfile = os.path.splitext(outputfile)[0]

        oname, oextension = os.path.splitext(outputfile)
        if oextension == '':
            outputfile = oname + '.' + self.extensions[to_format]
        elif oextension[1:] != self.extensions[to_format]:
            self.logger.error('Incorrect outputfile extension %s for format %s\n\t - %s\n\t - outputfile: %s' % (oextension, to_format, self.filepath, outputfile))
            outputfile = None
        else:
            pass

        return outputfile

    def convert(self, outputfile, use_cache=False, rc=None):
        assert self.buffer

        to_format = self.get_output_format()
        self.logger.info('Converting to %s' % to_format)
        if not to_format in self.supported:
            self.logger.error('Unsupported conversion format %s\n\t - %s' % (to_format, self.filepath))
            return 'error', 'Error converting %s' % self.filepath

        outputfile = self.make_output_filename(outputfile, to_format)
        self.logger.debug('Output file: %s' % outputfile)
        if not outputfile:
            return 'error', 'Error creating outputfile %s' % self.filepath

        pdoc_args = PandocArguments()

        render_file = self.get_renderfile()
        if not render_file:
            pdoc_args.add_flag('standalone')
            self.logger.info('Standalone mode')

        template_file = self.get_template()
        pdoc_args.add('template', template_file)
        self.logger.debug('Template file: ' % template_file)

        include_files = self.get_pandoc_include_files()
        pdoc_args.add('include-in-header', include_files['include-in-header'])
        pdoc_args.add('include-before-body', include_files['include-before-body'])
        pdoc_args.add('include-after-body', include_files['include-after-body'])

        bib_file = self.get_bibfile()
        pdoc_args.add('bibliography', bib_file)

        csl_file = self.get_cslfile()
        pdoc_args.add('csl', csl_file)

        if self.get_preprocess_mustache():
            assert(rc)
            self.logger.debug('Preprocess mustache: %s' % self.filepath)
            self.buffer = mustachefile.mustache_render2(self.filepath, self.filepath, self.buffer, rc, self.logger)
        else:
            self.logger.debug('Do not preprocess mustache: %s' % self.filepath)

        if to_format == 'html':
            apply_hf, hf = self.get_html_filter()
            if apply_hf:
                for k in hf.keys():
                    if hf[k]:
                        self.files[k] = hf[k]

            if not self.needs_compilation(use_cache, outputfile):
                self.logger.warning('Output already exists.  Nothing to do here.\n\t - %s\n\t - %s' % (self.filepath, outputfile))
                return 'file', outputfile

            if apply_hf:
                f = mdfilters.HTML_Filter(hf, self.dbglevel, self.logfile)
                try:
                    self.buffer = f.apply(self.filepath, self.rootdir, self.buffer)
                except:
                    print self.buffer
                    print f.img_template
                    self.logger.warning('HTML filters failed. \n\t - %s' % self.filepath)

            pdoc_args.add_flag('mathjax')
            pdoc_args.add('highlight-style', self.get_highlighter())

            css_files = self.get_cssfiles()
            pdoc_args.add('css', css_files)

            return self.compile(to=to_format, args=pdoc_args.get())

        # if the desired output is a pdf or beamer file.
        elif to_format in ['pdf', 'beamer', 'latex']:

            if not outputfile:
                self.logger.error('No output file specified.  Conversion failed. \n\t - %s' % self.filepath)
                return 'error', 'No output file'

            if not self.needs_compilation(use_cache, outputfile):
                self.logger.warning('Output already exists.  Nothing to do here.\n\t - %s\n\t - %s' % (self.filepath, outputfile))
                return 'file', outputfile

            if render_file:
                self.logger.warning('Render option in yaml frontmatter unsupported for %s format\n\t - ' % (to_format, self.filepath))

            pdoc_args.add('highlight-style', self.get_highlighter())
            pdoc_args.add_var('graphics','true')

            return self.compile(to=to_format, args=pdoc_args.get(), outputfile=outputfile)

        else:
            return 'error', 'Error converting %s' % self.filepath

    def needs_compilation(self, use_cache, outputfile):
        if not use_cache:
            return True

        if not util.is_valid_file(outputfile):
            return True

        srcs = [ self.filepath ]
        for k in ['template', 'csl', 'bibliography', 'template']:
            for f in self.files[k]:
                srcs.append(f)
        return util.srcs_newer_than_dest(srcs, outputfile)

    def get_highlighter(self):
        try:
            if self.extras['highlighter']:
                return self.extras['highlighter']
        except:
            pass

        try:
            return self.yaml['highlighter']
        except:
            return 'pygments'

    def get_yaml(self):
        assert(self.buffer)
        return self.yaml

    def get_html_filter(self):
        assert(self.buffer)

        hf = {'html-img': None, 'html-imgs': None, 'html-vid': None, 'html-vids': None}

        try:
            hf['html-img'] = self.yaml['html-img']
            if hf['html-img'] != None:
                hf['html-img'] = self.get_abs_path(hf['html-img'])
        except:
            pass

        try:
            hf['html-imgs'] = self.yaml['html-imgs']
            if hf['html-imgs'] != None:
                hf['html-imgs'] = self.get_abs_path(hf['html-imgs'])
        except:
            pass

        try:
            hf['html-vid'] = self.yaml['html-vid']
            if hf['html-vid'] != None:
                hf['html-vid'] = self.get_abs_path(hf['html-vid'])
        except:
            pass

        try:
            hf['html-vids'] = self.yaml['html-vids']
            if hf['html-vids'] != None:
                hf['html-vids'] = self.get_abs_path(hf['html-vids'])
        except:
            pass

        use = not (hf['html-img']==None and hf['html-imgs']==None and hf['html-vid']==None and hf['html-vids']==None)
        return use, hf

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

    def get_preprocess_mustache(self):
        assert(self.buffer)

        try:
            if self.extras['preprocess-mustache']:
                return self.extras['preprocess-mustache']
        except:
            pass

        try:
            return self.yaml['preprocess-mustache']
        except:
            return False

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
                self.logger.warning('Cannot find\n\t - file: %s\n\t - key: %s\n\t - path: %s' % (self.filepath, key, p))
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

def setup_mdfile_logger(dbglevel, logfile):
    logger = logging.getLogger('mdfile')
    if logger.handlers:
        return logger

    logger.setLevel(dbglevel)

    fmtstr = '%(message)s'
    formatter = logging.Formatter(fmtstr)
    console_log = logging.StreamHandler()
    console_log.setLevel(dbglevel)
    console_log.setFormatter(formatter)
    logger.addHandler(console_log)

    if logfile:
        fmtstr = '%(name)-8s \t %(levelname)-8s \t [%(asctime)s] \t %(message)s'
        formatter = logging.Formatter(fmtstr)
        file_log = logging.FileHandler(logfile)
        file_log.setLevel(dbglevel)
        file_log.setFormatter(formatter)
        logger.addHandler(file_log)

    return logger

if __name__ == '__main__':

    from webify import __version__

    global prog_name, prog_dir
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)

    parser = argparse.ArgumentParser()
    parser.add_argument('mdfile', help='MD file.  Options specified on commandline override those specified in the file yaml block.')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    parser.add_argument('-o','--output', action='store', default=None, help='Output path.  A file or dir name can be specified.')
    parser.add_argument('-v','--verbose', action='store_true', default=False, help='Turn verbose on.')
    parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages.')
    parser.add_argument('-f','--format', action='store', default=None, help='Output format: html, pdf, beamer, latex.')
    parser.add_argument('-t','--template', action='store', default=None, help='Path to pandoc template file.')
    parser.add_argument('-b','--bibliography', action='store', default=None, help='Path to bibliography file.')
    parser.add_argument('-s','--css', nargs='*', action='append', help='Space separated list of css files.')
    parser.add_argument('-c','--csl', action='store', default=None, help='csl file, only used when a bibfile is specified either via commandline or via yaml frontmatter')
#    parser.add_argument('-n','--no-cache', action='store_true', default=False, help='Forces to generated a new pdf file even if md files in not changed.')
    parser.add_argument('-l','--log', action='store_true', default=False, help='Writes out a log file.')
    parser.add_argument('-k','--highlighter', action='store', default=None, help='Specify a highlighter.  See pandoc --list-highlight-styles.')
    parser.add_argument('-y', '--yaml', nargs='*', action='append', help='Space separated list of extra yaml files to process.')
    parser.add_argument('-p', '--preprocess-mustache', action='store_true', default=False, help='Pre-processes md file using mustache before converting via pandoc.')
    parser.add_argument('-i', '--ignore-times', action='store_true', default=False, help='Forces the generation of the output file even if the source file has not changed')

    args = parser.parse_args()

    log_level = logging.NOTSET
    if args.debug:
        log_level = logging.DEBUG
    elif args.verbose:
        log_level = logging.INFO

    logfile = None
    if args.log:
        logfile = 'mdfile.log'

    logger = setup_mdfile_logger(log_level, logfile)

    css_files = []
    if args.css:
        css_files = args.css[0]

    if logger.getEffectiveLevel() == logging.DEBUG:
        print 'prog_name', prog_name
        print 'prog_dir', prog_dir
        print 'Commandline arguments:'
        print '\tformat', args.format
        print '\ttemplate', args.template
        print '\tbibliography', args.bibliography
        print '\tcss', css_files
        print '\tcsl', args.csl
        print '\thighlighter', args.highlighter
        print '\tpreprocess-mustache', args.preprocess_mustache
        print '\tignore-times', args.ignore_times
        print '\toutput', args.output, '\n'

    extras = { 'format': args.format,
               'template': args.template,
               'bibliography': args.bibliography,
               'css': css_files,
               'csl': args.csl,
               'highlighter': args.highlighter,
               'ignore-times': args.ignore_times,
               'preprocess-mustache': args.preprocess_mustache }

    cwd = os.getcwd()
    filepath = os.path.normpath(os.path.join(cwd, args.mdfile))
    logger.info('Processing: %s' % filepath)

    m = MDfile(filepath=filepath, rootdir='/', dbglevel=None, extras=extras, logger=logger)
    if not m.load():
        logger.error('Error creating mdfile object.  Nothing to be done here.')
        exit(-1)

    outputfile = os.path.splitext(filepath)[0]
    if args.output:
        if util.is_valid_dir(args.output):
            outputfile = os.path.normpath(os.path.join(args.output, os.path.splitext(args.mdfile)[0]))
        else:
            outputfile = os.path.normpath(args.output)

    fmt, data = m.convert(outputfile=outputfile, use_cache=not args.ignore_times, rc=m.get_yaml())
    logger.debug('Mdfile convert return fmt: %s' % fmt)

    if fmt == 'error':
        logger.error('Failed')
        exit(-1)

    if fmt == 'html':
        util.save_to_html(data, util.make_extension(outputfile, 'html'), logger=m.logger)
    else:
        pass # the file is already written at destination

    exit(0)

    # yamlfiles = []
    # if args.yaml:
    #     yamlfiles.extend(args.yaml[0])

    # if not len(yamlfiles) > 0:
    #     exit(0)

    # import yamlfile, renderingcontext
    # rc = renderingcontext.RenderingContext()
    # for f in yamlfiles:
    #     y = yamlfile.YAMLfile(f)
    #     rc.add_yamlfile(y)
    # rc.add_key_val('body', m.get_body())

    # import mustachefile
    # template_file = util.make_actual_path(rootdir = '/', basepath = m.basepath, template_file = m.get_renderfile())
    # m1 = mustachefile.Mustachefile(template_file)
    # m1.load()
    # data = m1.render(rc)
    # if fmt == 'html':
    #     util.save_to_html(data, util.make_different_extension(args.mdfile, '.html'), logger=None)
