import argparse
import pprint as pp
import sys
import logging
import os
from util2 import get_gitinfo, make_directory, mustache_renderer, jinja2_renderer, WebifyLogger, Terminal, RenderingContext, YAMLfile, HTMLfile, IgnoreList, save_to_file, process_file
from mdfile2 import MDfile
import pypandoc
import pystache
import yaml
import pathspec
import datetime
import markupsafe
import json

from globals import __version__
logfile = 'webify2.log'
ignorefile = '.webifyignore'
ignore_times = False

class DirTree:
    class DirNode:
        def __init__(self, root, path, name):
            self.logger = WebifyLogger.get('db')
            self.files = {'yaml': [], 'html': [], 'misc': [], 'md': []}
            self.children = []
            self.partials = None
            self.name = name
            self.path = path
            self.root = root
    
        def add_file(self, name):
            _, ext = os.path.splitext(name)
            if ext.lower() == '.yaml':
                self.files['yaml'].append(name)
            elif ext.lower() in ['.html', '.htm']:
                self.files['html'].append(name)
            elif ext.lower() in ['.md', '.markdown']:
                self.files['md'].append(name)
            else:
                self.files['misc'].append(name)

        def add_child(self, dir_node):
            if dir_node.name == '_partials':
                self.partials = dir_node
            else:
                self.children.append(dir_node)

        def get_fullpath(self):
            return os.path.normpath(os.path.join(self.root, self.path, self.name))
                
        def get_path(self):
            return os.path.normpath(os.path.join(self.path, self.name))

        def __repr__(self):
            s = "Path: " + self.path + ", Name: " + self.name
            return s
            
    def __init__(self):
        self.logger = WebifyLogger.get('db')
        self.rootdir = None
        
    def collect(self, rootdir, ignore=None):
        self.ignore = ignore
        self.rootdir = self.DirNode(root=rootdir, path='.', name='.')

        dirs = [self.rootdir]
        while len(dirs) > 0:
            cur_dir_node = dirs.pop()

            self.logger.debug('Collecting directory %s' % cur_dir_node.get_fullpath())
            for entry in os.scandir(cur_dir_node.get_fullpath()):
                self.logger.debug('Found entry %s %s' % (cur_dir_node.get_fullpath(), entry.name))

                if ignore and ignore.ignore(cur_dir_node.get_fullpath(), entry.name, entry.is_dir()):
                    self.logger.debug('Ignoring          : %s' % entry.name)
                    continue
                
                if entry.is_dir():
                    sub_dir_node = self.DirNode(root=cur_dir_node.root, path=cur_dir_node.get_path(), name=entry.name)
                    cur_dir_node.add_child(sub_dir_node)
                    dirs.append(sub_dir_node)
                    self.logger.debug('Added subdirectory: %s, %s, %s' % (cur_dir_node.root, cur_dir_node.get_path(), entry.name))
                else:
                    self.logger.debug('Added file        : %s' % entry.name)
                    cur_dir_node.add_file(name=entry.name)

    def __traverse__(self, dir, enter_func, proc_func, leave_func):
        self.logger.debug('Entering %s' % dir.get_fullpath())
        if enter_func: enter_func(dir)
        if proc_func: proc_func(dir)
        for i in dir.children:
            self.__traverse__(i, enter_func, proc_func, leave_func)
        if leave_func: leave_func(dir)
        self.logger.debug('Leaving %s' % dir.get_fullpath())
        
    def traverse(self, enter_func=None, proc_func=None, leave_func=None):
        rootdir = self.rootdir
        #self.__traverse__(rootdir, None, None, None)
        self.__traverse__(rootdir, enter_func, proc_func, leave_func)

class Webify:
    def __init__(self):
        self.logger = WebifyLogger.get('webify')
        self.rc = RenderingContext()
        self.ignore = None
        self.dir_tree = DirTree()

    def set_templating_engine(self):
        if self.meta_data['templating-engine'] == 'jinja2':
            self.render = jinja2_renderer
        else:
            self.render = mustache_renderer
        
    def set_src(self, srcdir, meta_data):
        self.meta_data = meta_data
        self.srcdir = os.path.abspath(srcdir)
        if not os.path.isdir(self.srcdir):
            self.logger.critical('Source folder not found: %s' % srcdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error source folder')
        else:
            self.logger.info('Source folder found: %s' % srcdir)
            self.ignore = IgnoreList(srcdir=self.srcdir)
            self.ignore.read_ignore_file(os.path.abspath(os.path.join(srcdir, ignorefile)))

        self.set_templating_engine()            
        self.rc.push()
        self.rc.add(meta_data)

    def set_dest(self, destdir):
        self.destdir = os.path.abspath(destdir)
        r = make_directory(destdir)
        if not r:
            self.logger.critical('Cannot create destination folder: %s' % destdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error destination folder')
        else:
            self.logger.info('Destination directory %s: %s' % (r, destdir))

    def proc_partials(self, dir):
        data = {}
        if dir.partials:
            self.logger.info('Processing _partials ...')
            self.logger.info('Processing: %s' % dir.partials.get_fullpath())
            self.rc.push()

            if len(dir.partials.files['yaml']) > 0:
                self.logger.info('Processing  YAML files...')
            else:
                self.logger.info('No YAML files found')
            for i in dir.partials.files['yaml']:
                yaml_file = YAMLfile(filepath=os.path.join(dir.partials.get_fullpath(), i))
                yaml_file.load()
                self.rc.add(yaml_file.data)

            if len(dir.partials.files['html']) > 0:
                self.logger.info('Processing  HTML files...')
            else:
                self.logger.info('No HTML files found')
            for i in dir.partials.files['html']:
                html_file = HTMLfile(filepath=os.path.join(dir.partials.get_fullpath(), i))
                buffer = html_file.load().get_buffer()
                rendered_buf = self.render(template=buffer, context=self.rc.data())
                data[i.replace('.','_')] = markupsafe.Markup(rendered_buf)

            if len(dir.partials.files['md']) > 0:
                self.logger.info('Processing  MD files...')
            else:
                self.logger.info('No MD files found')
            extras = { 'no-output-file': True, 'ignore-times': ignore_times }
            for i in dir.partials.files['md']:
                self.rc.push()
                filepath = os.path.join(dir.partials.get_fullpath(), i)
                md_file = MDfile(filepath=filepath, rootdir=dir.partials.get_fullpath(), extras=extras, rc=self.rc)
                self.logger.info('Processing MD file: %s' % filepath)
                ret_type, buffer, _ = md_file.load().get_buffer()
                self.rc.pop()
                if not ret_type == 'buffer':
                    self.logger.warning('Ignoring _partials file: %s' % filepath)
                else:
                    data[i.replace('.','_')] = markupsafe.Markup(buffer)
            self.logger.info('Done processing folder %s' % dir.partials.get_fullpath())
            self.rc.pop()            
            self.rc.add(data)
        else:
            self.logger.info('No _partials found')

    def proc_yaml(self, dir):
        if len(dir.files['yaml']) > 0:
            self.logger.info('Processing  YAML files...')
        else:
            self.logger.info('No YAML files found')
        
        for i in dir.files['yaml']:
            yaml_file = YAMLfile(filepath=os.path.join(dir.get_fullpath(), i))
            yaml_file.load()
            self.rc.add(yaml_file.data)
            
    def enter_dir(self, dir):
        self.logger.info('Processing folder %s...' % dir.get_fullpath())

        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.info('>'*terminal.c())
            logger_rc.debug('Rendering context (enter: %s)' % dir.name)
            self.rc.print()

        self.rc.push()
        self.rc.add({'__root__': os.path.relpath(self.srcdir, dir.get_fullpath())})

    def proc_html(self, dir):
        if len(dir.files['html']) > 0:
            self.logger.info('Processing  HTML files...')
        else:
            self.logger.info('No HTML files found')
                
        for filename in dir.files['html']:
            filepath, dest_filepath = self.get_src_and_dest(dir, filename)
            html_file = HTMLfile(filepath)
            buffer = html_file.load().get_buffer()
            rendered_buf = self.render(template=buffer, context=self.rc.data())
            self.logger.info('Saving %s' % dest_filepath)
            save_to_file(dest_filepath, rendered_buf)

    def proc_md(self, dir):
        if len(dir.files['md']) > 0:
            self.logger.info('Processing MD files...')
        else:
            self.logger.info('No MD files found')

        # Lets check if this directory contains a blog
        is_blog = self.rc.value('blog')
        if is_blog: 
            if not self.rc.value('blog_root_dir'):
                blog_root_dir = self.get_src(dir, '')
                blog_dest_dir = self.get_dest(dir, '') 

                blog_index_file = self.rc.value('blog_index')
                if not blog_index_file:
                    self.logger.warning('Blog index file not found %s' % blog_root_dir)
                    blog_index_filepath = None
                    blog_index_destpath_noext = None
                else:
                    blog_index_filepath = self.get_src(dir, blog_index_file)
                    blog_index_destpath = self.get_dest(dir, blog_index_file)
                    blog_index_destpath_noext = os.path.splitext(blog_index_destpath)[0]

                blog_posts = []
                self.rc.add( {'blog_root_dir': blog_root_dir,
                              'blog_dest_dir': blog_dest_dir,
                              'blog_posts': blog_posts,
                              'blog_index_filepath': blog_index_filepath,
                              'blog_index_destpath_noext': blog_index_destpath_noext} )
            else:
                blog_dest_dir = self.rc.value('blog_dest_dir')
                blog_posts = self.rc.value('blog_posts')
                blog_index_filepath = self.rc.value('blog_index_filepath')
        else:
            blog_posts = None
            blog_dest_dir = None 

        print('\n\n\n\n')
        print(dir)
        self.rc.print()

        extras = { 'ignore-times': ignore_times }
        for filename in dir.files['md']:
            filepath = self.get_src(dir, filename)
            if is_blog and filepath == blog_index_filepath: continue

            filepath_dir = self.get_src(dir, '')
            destpath = self.get_dest(dir, filename)
            destpath_noext = os.path.splitext(destpath)[0]
            
            extras['output-file'] = destpath_noext
            self.proc_md_file(filename, filepath, filepath_dir, extras, blog_posts, blog_dest_dir)

            # self.logger.info('Processing MD file: %s' % filepath)
            # self.rc.push() 
            # md_file = MDfile(filepath=filepath, rootdir=dir.get_fullpath(), extras=extras, rc=self.rc)
            # #self.rc.pop()
            # self.logger.debug('Saving %s' % extras['output-file'])

            # ret_type, saved_file, _ = md_file.load().get_buffer()
            # if ret_type == 'file':
            #     self.logger.info('Saved %s' % saved_file)
            # elif ret_type == 'exists':
            #     self.logger.info('Already exists %s' % saved_file)
            # else:
            #     self.logger.warning('Error processing %s' % filepath)
            #     self.rc.pop()
            #     continue

            # if is_blog:
            #     blog_posts.append(
            #         self.collect_blog_info(filename, saved_file, blog_root_dir, md_file)
            #         )
            # self.rc.pop()
    
    def proc_md_file(self, filename, filepath, filepath_dir, extras, blog_posts, blog_dest_dir):
        self.rc.push() 
        
        md_file = MDfile(filepath=filepath, rootdir=filepath_dir, extras=extras, rc=self.rc)
        self.logger.debug('Saving %s' % extras['output-file'])

        ret_type, saved_file, _ = md_file.load().get_buffer()
        if ret_type == 'file':
            self.logger.info('Saved %s' % saved_file)
        elif ret_type == 'exists':
            self.logger.info('Already exists %s' % saved_file)
        else:
            self.logger.warning('Error processing %s' % filepath)

        if blog_posts != None:
            blog_posts.append(
                self.collect_blog_info(filename, saved_file, blog_dest_dir, md_file)
                )

        self.rc.pop()

    def collect_blog_info(self, filename, saved_file, blog_index_dir, md_file):
        entry = {
            'filename': filename,
            'link': os.path.relpath(saved_file, blog_index_dir)
        }

        y = md_file.get_yaml()
        try:
            entry['title'] = y['title']
        except:
            entry['title'] = entry['link']
        
        try:
            entry['author'] = y['author']
        except:
            entry['author'] = ''

        try:
            entry['date'] = y['date']
        except:
            entry['date'] = 'Today'

        return entry

    def get_src(self, dir, filename):
        filepath =  os.path.join(dir.get_fullpath(), filename)
        return os.path.normpath(filepath)

    def get_dest(self, dir, filename):
        dest_rel_filepath = os.path.join(dir.path, dir.name, filename)
        dest_filepath = os.path.join(self.destdir, dest_rel_filepath)
        return os.path.normpath(dest_filepath)

    def get_src_and_dest(self, dir, filename):
        return self.get_src(dir, filename), self.get_dest(dir, filename)
                
    def proc_misc(self, dir):
        if len(dir.files['misc']) > 0:
            self.logger.info('Processing all other files...')
        else:
            self.logger.info('No other files found')

        for filename in dir.files['misc']:
            filepath, dest_filepath = self.get_src_and_dest(dir, filename)
            self.logger.info('Processing %s' % filepath)
            r = process_file(filepath, dest_filepath, self.meta_data['force_copy'])

    def proc_dir(self, dir):
        self.proc_yaml(dir)
        self.proc_partials(dir)

        # print(self.rc.data()['header-bootstrap4_html'])
        # print(self.rc.data()['nav_html'])

        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.debug('\nRendering context (inside: %s)' % dir.name)
            self.rc.print()

        destdir = os.path.normpath(os.path.join(self.destdir, dir.path, dir.name))
        if os.path.isdir(destdir):
            self.logger.info('Destination directory exists: %s' % destdir)
        else:
            self.logger.info('Making destination directory: %s' % destdir)
            make_directory(destdir)
            
        self.proc_html(dir)
        self.proc_md(dir)
        self.proc_misc(dir)
            
    def leave_dir(self, dir):
        is_blog = self.rc.value('blog')
        if is_blog and self.rc.value('blog_root_dir') == self.get_src(dir, ''):

            extras = { 'ignore-times': ignore_times,
                       'output-file': self.rc.value('blog_index_destpath_noext') }

            blog_index_filename = self.rc.value('blog_index')
            blog_index_filepath = self.rc.value('blog_index_filepath')
            blog_index_filepath_dir = self.rc.value('blog_root_dir')
            blog_posts = None
            blog_dest_dir = self.rc.value('blog_dest_dir')

            print('XXXX', blog_index_filename)
            self.proc_md_file(blog_index_filename, 
                              blog_index_filepath, 
                              blog_index_filepath_dir, 
                              extras, 
                              blog_posts, 
                              blog_dest_dir)

        self.rc.pop()

        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.debug('\nRendering context (leave: %s)' % dir.name)
            self.rc.print()
            logger_rc.info('-'*terminal.c())
        self.logger.info('...  Done processing folder %s' % dir.get_fullpath())
        
    def traverse(self):
        self.dir_tree.collect(rootdir=self.srcdir, ignore=self.ignore)
        self.dir_tree.traverse(enter_func=self.enter_dir, proc_func=self.proc_dir, leave_func=self.leave_dir)

def version_info():
    str =  '  Webify2:    %s,\n' % __version__
    str += '  logfile:    %s,\n' % logfile 
    str += '  ignorefile: %s,\n' % ignorefile
    str += '  Git info:   %s,\n' % get_gitinfo()
    str += '  Python:     %s.%s,\n' % (sys.version_info[0],sys.version_info[1])
    str += '  Pypandoc:   %s,\n' % pypandoc.__version__
    str += '  Pyyaml:     %s,\n' % yaml.__version__
    str += '  Pystache:   %s,\n' % pystache.__version__
    str += '  Json:       %s, and\n' % json.__version__
    str += '  Pathspec:   %s.' % pathspec.__version__
    return str

if __name__ == '__main__':

    terminal = Terminal()
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)
    cur_dir = os.getcwd()

    # Command line arguments
    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('srcdir', help='Source directory')
    cmdline_parser.add_argument('destdir', help='Destination directory')
    cmdline_parser.add_argument('--version', action='version', version=version_info())
    cmdline_parser.add_argument('-v','--verbose',action='store_true',default=False,help='Prints helpful messages')
    cmdline_parser.add_argument('-d','--debug',action='store_true',default=False,help='Turns on (global) debug messages')
    cmdline_parser.add_argument('--debug-rc',action='store_true',default=False,help='Turns on rendering context debug messages')
    cmdline_parser.add_argument('--debug-db',action='store_true',default=False,help='Turns on file database debug messages')
    cmdline_parser.add_argument('--debug-db-ignore',action='store_true',default=False,help='Turns on .webifyignore debug messages')
    cmdline_parser.add_argument('--debug-yaml',action='store_true',default=False,help='Turns on yaml debug messages')
    cmdline_parser.add_argument('--debug-render',action='store_true',default=False,help='Turns on render debug messages')
    cmdline_parser.add_argument('--debug-md',action='store_true',default=False,help='Turns on mdfile debug messages')
    cmdline_parser.add_argument('--debug-webify',action='store_true',default=False,help='Turns on webify debug messages')
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Use log file.')
    cmdline_parser.add_argument('-i', '--ignore-times', action='store_true', default=False, help='Forces the generation of the output file even if the source file has not changed')
    cmdline_parser.add_argument('--force-copy', action='store_true', default=False, help='Force file copy.')    
    cmdline_parser.add_argument('-t', '--templating-engine', action='store', default='jinja2', help='Specify whether to use mustache or jinja2 engine.  Jinja2 is the default choice.')
    
    cmdline_args = cmdline_parser.parse_args()
    ignore_times = cmdline_args.ignore_times
    
    # Setting up logging
    logfile = None if not cmdline_args.log else logfile
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug   else loglevel
#    logger = WebifyLogger.make(name='webify', loglevel=loglevel, logfile=logfile)

    l = logging.DEBUG if cmdline_args.debug_rc else loglevel
    WebifyLogger.make(name='rc', loglevel=l, logfile=logfile)
    l = logging.DEBUG if cmdline_args.debug_db else loglevel
    WebifyLogger.make(name='db', loglevel=l, logfile=logfile)
    l = logging.DEBUG if cmdline_args.debug_yaml else loglevel    
    WebifyLogger.make(name='yaml', loglevel=l, logfile=logfile)
    WebifyLogger.make(name='html', loglevel=loglevel, logfile=logfile)    
    l = logging.DEBUG if cmdline_args.debug_render else logging.WARNING    
    WebifyLogger.make(name='render', loglevel=l, logfile=logfile)
    l = logging.DEBUG if cmdline_args.debug_md else logging.WARNING  
    WebifyLogger.make(name='mdfile', loglevel=l, logfile=logfile)
    l = logging.DEBUG if cmdline_args.debug_db_ignore else loglevel
    WebifyLogger.make(name='db-ignore', loglevel=l, logfile=logfile)
    l = logging.DEBUG if cmdline_args.debug_webify else loglevel
    WebifyLogger.make(name='webify', loglevel=l, logfile=logfile)

    
    logger = WebifyLogger.get('webify')

    # Check
    if not cmdline_args.templating_engine in ['mustache', 'jinja2']:
        logger.error('Invalid templating engine %s.  See help' % cmdline_args.templateing_engine)
        exit(-4)
        
    # Go        
    logger.info('Prog name:    %s' % prog_name)
    logger.info('Prog dir:     %s' % prog_dir)
    logger.info('Current dir:  %s' % cur_dir)
    logger.info('Info:')
    logger.info(version_info())
    logger.info('Using "%s" templating engine' % cmdline_args.templating_engine)

    srcdir = os.path.normpath(cmdline_args.srcdir)
    destdir = os.path.normpath(cmdline_args.destdir)
    
    meta_data = {
        'prog_name': prog_name,
        'prog_dir': prog_dir.replace('\\','\\\\'), # We need to do it for windows.
        'cur_dir': cur_dir.replace('\\','\\\\'),   # It is a bit wierd, I agree.
        'src_dir': srcdir.replace('\\','\\\\'),    # But it seems mustache templating engine
        'dest_dir': destdir.replace('\\','\\\\'),  # can't deal with \.  Will look into it more.
        '__version__': __version__,
        '__root__': os.path.abspath(cmdline_args.srcdir).replace('\\','\\\\'),
        'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'templating-engine': cmdline_args.templating_engine,
        'force_copy': cmdline_args.force_copy,
        'blog': False
    }
    
    if WebifyLogger.is_debug(logger):
        print('Meta data:')
        pp.pprint(meta_data)

    webify = Webify()
    try:
        webify.set_src(srcdir, meta_data)
    except ValueError as e:
        print(e)
        exit(-1)
    try:           
        webify.set_dest(destdir)
    except ValueError as e:
        print(e)
        exit(-2)
    
    webify.traverse()
    exit(0)
