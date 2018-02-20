#!/Users/faisal/anaconda2/bin/python

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

    files:
        - include-before-body
        - include-in-header
        - include-after-body
    
    bibliography: None* | path/to/bib file

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
    def __init__(self, filepath, rootdir=None, dbglevel=logging.WARNING, extras=None, filters=None):
        self.logger = util.setup_logging('MDfile', dbglevel=dbglevel)

        self.filepath = filepath
        self.basepath = os.path.split(self.filepath)[0]
        if rootdir:
            self.rootdir = rootdir
        else:
            self.rootdir = self.basepath
        self.yaml = None
        self.buffer = None
        self.extras = extras
        self.filters = filters

        self.logger.debug('filepath: %s' % self.filepath)
        self.logger.debug('basepath: %s' % self.basepath)
        self.logger.debug('rootdir: %s' % self.rootdir)

        self.supported = [ 'html', 'beamer', 'pdf' ]

    def load(self):
        try:
            with codecs.open(self.filepath, 'r') as stream:
                self.buffer = stream.read().decode('utf-8')
            self.logger.debug('Loaded MD file: %s' % self.filepath)
        except:
            self.logger.warning('Error reading MD file: %s' % self.filepath)
            self.buffer = ''
            return False

        try:
            yamlsections = yaml.load_all(self.buffer)

            for section in yamlsections:
                self.yaml = section
                self.logger.debug('YAML section found in md file: %s' % self.filepath)
                break # Only the first yaml section is read in

        except:
            self.logger.debug('YAML section not found in md file: %s' % self.filepath)

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

    def convert(self, outputfile, use_cache=False):
        assert self.buffer

        to_format = self.get_output_format()

        if to_format in self.supported:
            self.logger.debug('Using Pandoc to convert MD to %s: %s', to_format, self.filepath)
        else:
            self.logger.error('Unsupported conversion format: %s', to_format)
            return 'error', 'Error converting %s' % self.filepath 

        if not outputfile:
            outputfile = os.path.splitext(self.filepath)[0]
        self.logger.debug('MD convert, outputfile: %s' % outputfile)

        pdoc_args = []

        if not self.get_renderfile():                   # If no render file (mustache) is specified
            self.logger.debug('Standlone html')         # then md is converted to a standalone file
            pdoc_args.append('--standalone')

        template_file = util.make_actual_path(rootdir = self.rootdir, basepath = self.basepath, filepath = self.get_template())
        self.logger.debug('Template file: %s' % template_file )
        if template_file:
            if os.path.isfile(template_file):
                pdoc_args.append('--template=%s' % template_file)
            else:
                self.logger.error('Template file %s not found.' % template_file)

        pandoc_include_files = self.get_pandoc_include_files()
        
        self.logger.debug('Pandoc include files:')
        if self.logger.getEffectiveLevel() == logging.DEBUG:
            for item in pandoc_include_files:
                print item

        for item in pandoc_include_files:
            if not item[0] in ['include-before-body', 'include-in-header', 'include-after-body']:
                self.logger.warning('Unrecognized pandoc include file option: %s', item[0])
                continue
            f = util.make_actual_path(rootdir = self.rootdir, basepath = self.basepath, filepath = item[1])
            if f and os.path.isfile(f):
                pdoc_args.append('--%s=%s' % (item[0],f))
            else:
                self.logger.error('%s file %s not found.' % (item[0],f))

        bibfile = self.get_bibfile()
        if bibfile:
            f = util.make_actual_path(rootdir = self.rootdir, basepath = self.basepath, filepath = bibfile)            
        pdoc_args.extend(['--filter=pandoc-citeproc'])
            
        # if the desired output is html
        if to_format == 'html':
            pdoc_args.extend(['--mathjax','--highlight-style=pygments'])

            css_files = self.get_css()
            for css_file in css_files:
                pdoc_args.extend(['--css=%s' % css_file])

            try:    
                for f in self.filters['html']:
                    self.buffer = f(self.filepath, self.rootdir, self.buffer)
            except:
                pass

            try:
                cwd = os.getcwd()
                os.chdir(self.basepath)
                html = pypandoc.convert_text(self.buffer, to=to_format, format='md', extra_args=pdoc_args)
                os.chdir(cwd)
                return 'html', html
            except:
                self.logger.warning('Error converting %s to html' % self.filepath)
                return 'error', 'Error converting %s' % self.filepath

        # if the desired output is a pdf or beamer file.
        elif to_format in ['pdf', 'beamer']:
            outputfile += '.pdf'

            if use_cache and os.path.isfile(outputfile) and not util.srcs_newer_than_dest([self.filepath, template_file], outputfile):
                self.logger.info('%s already exists.  Nothing to do.' % outputfile)
                return 'file', outputfile

            if self.get_renderfile():
                self.logger.warning('%s: "render" option in yaml frontmatter unsupported for %s format' % (self.filepath, to_format))

            pdoc_args.extend(['--highlight-style=kate','-V graphics:true'])

            if self.logger.getEffectiveLevel() == logging.DEBUG:
                print 'pdoc_args:', pdoc_args

            try:
                cwd = os.getcwd()
                os.chdir(self.basepath)
                pypandoc.convert_text(self.buffer, to=to_format, format='md', outputfile=outputfile, extra_args=pdoc_args)
                os.chdir(cwd)
                return 'file', outputfile
            except:
                self.logger.warning('Error converting %s to %s' % (self.filepath, to_format))
                return 'error', 'Error converting %s' % self.filepath

        else:
            return 'error', 'Error converting %s' % self.filepath

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

    def get_css(self):
        assert(self.buffer)

        css_files = []

        try:
            e = self.yaml['css']

            if isinstance(e, list):
                css_files.extend(e)
            elif e:
                css_files.append(e)
            else:
                pass
        except:
            pass

        try:
            e = self.extras['css']

            if isinstance(e, list):
                css_files.extend(e)
            elif e:
                css_files.append(e)
            else:
                pass
        except:
            pass

        return css_files

    def get_bibfile(self):
        assert(self.buffer)

        try:
            if self.extras['bib']:
                return self.extras['bib']
        except:
            pass

        try:
            return self.yaml['bibliography']
        except:
            return None

    def get_renderfile(self):
        assert(self.buffer)

        try:
            return self.yaml['render']
        except:
            return None

    def get_pandoc_include_files(self):
        assert(self.buffer)

        f = []
        try:
            l = self.yaml['files']
            for item in l:
                for key in item.keys():
                    f.append((key, item[key]))
            return f
        except:
            return []

    def get_copy_to_destination(self):
        assert(self.buffer)

        try:
            return self.yaml['copy-to-destination']
        except:
            return False

    def get_template(self):
        assert(self.buffer)

        try:
            if self.extras['template']:
                return self.extras['template']
        except:
            pass

        try:
            return self.yaml['template']
        except:
            return None

if __name__ == '__main__':

    global prog_name, prog_dir
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)

    parser = argparse.ArgumentParser()
    parser.add_argument('mdfile', help='MD file.  Options specified on commandline override those specified in the file yaml block.')
    parser.add_argument('-y', '--yaml', nargs='*', action='append', help='Space separated list of extra yaml files to process')
    parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages')
    parser.add_argument('-f','--format', action='store', default=None, help='Output format: html, pdf, beamer')
    parser.add_argument('-t','--template', action='store', default=None, help='Path to pandoc template file')
    parser.add_argument('-b','--bib', action='store', default=None, help='Path to bibliography file')
    parser.add_argument('-c','--css', action='store', default=None, help='Path to css file')
    parser.add_argument('--media-filters', action='store_true', default=False, help='Media filters (see documentation)')

    args = parser.parse_args()

    dbglevel = logging.INFO
    if args.debug:
      dbglevel = logging.DEBUG

    if dbglevel == logging.DEBUG:
        print 'format', args.format
        print 'template', args.template
        print 'bib', args.bib
        print 'css', args.css

    extras = { 'format': args.format, 'template': args.template, 'bib': args.bib, 'css': args.css }

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

    fmt, data = m.convert(outputfile=None, use_cache=True)
    if m.logger.getEffectiveLevel() == logging.DEBUG:
        print 'Format:', fmt
        print 'Data:', data

    if fmt == 'html':
        util.save_to_html(data, util.make_different_extension(args.mdfile, '.html'), logger=None)

    if m.logger.getEffectiveLevel() == logging.DEBUG:
        print 'Copy to destination:', m.get_copy_to_destination()
        print 'Pandoc include files', m.get_pandoc_include_files()

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

