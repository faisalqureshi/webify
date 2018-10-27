import argparse
import pprint as pp
import sys
import logging
import os
from util2 import get_gitinfo, make_directory, mustache_render, WebifyLogger, Terminal, RenderingContext, YAMLfile, HTMLfile, IgnoreList, save_to_file, copy_file
from mdfile2 import MDfile
import pypandoc
import pystache
import yaml
import json
import pathspec

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
                #print('nn')
                if ignore and ignore.ignore(entry.name):
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
        self.ignore = IgnoreList()
        self.dir_tree = DirTree()

    def set_src(self, srcdir, meta_data):
        self.srcdir = os.path.abspath(srcdir)
        if not os.path.isdir(self.srcdir):
            self.logger.critical('Source folder not found: %s' % srcdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error source folder')
        else:
            self.logger.info('Source folder found: %s' % srcdir)
            self.ignore.read_ignore_file(os.path.join(srcdir, ignorefile))

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
                rendered_buf = mustache_render(template=buffer, context=self.rc.data())
                data[i.replace('.','-')] = rendered_buf

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
                    rendered_buf = mustache_render(template=buffer, context=self.rc.data())
                    data[i.replace('.','-')] = rendered_buf
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

    def proc_html(self, dir):
        if len(dir.files['html']) > 0:
            self.logger.info('Processing  HTML files...')
        else:
            self.logger.info('No HTML files found')
                
        for i in dir.files['html']:
            dest_file = os.path.normpath(os.path.join(self.destdir, dir.path, dir.name, i))
            html_file = HTMLfile(filepath=os.path.join(dir.get_fullpath(), i))
            buffer = html_file.load().get_buffer()
            rendered_buf = mustache_render(template=buffer, context=self.rc.data())
            self.logger.info('Saving %s' % dest_file)
            save_to_file(dest_file, rendered_buf)

    def proc_md(self, dir):
        if len(dir.files['md']) > 0:
            self.logger.info('Processing MD files...')
        else:
            self.logger.info('No MD files found')

        extras = { 'ignore-times': ignore_times }
        for i in dir.files['md']:
            self.rc.push()
            filepath =  os.path.join(dir.get_fullpath(), i)
            dest_filepath = os.path.normpath(os.path.join(self.destdir, dir.path, dir.name, i))
            extras['output-file'] = os.path.splitext(dest_filepath)[0]
            self.logger.info('Processing MD file: %s' % filepath)
            md_file = MDfile(filepath=filepath, rootdir=dir.get_fullpath(), extras=extras, rc=self.rc)
            self.logger.debug('Saving %s' % extras['output-file'])
            ret_type, saved_file, _ = md_file.load().get_buffer()
            if ret_type == 'file':
                self.logger.info('Saved %s' % saved_file)
            elif ret_type == 'exists':
                self.logger.info('Already exists %s' % filepath)
            else:
                self.logger.warning('Error processing %s' % filepath)
            self.rc.pop()

    def proc_misc(self, dir):
        if len(dir.files['misc']) > 0:
            self.logger.info('Processing all other files...')
        else:
            self.logger.info('No other files found')

        for i in dir.files['misc']:
            filepath =  os.path.join(dir.get_fullpath(), i)
            dest_filepath = os.path.normpath(os.path.join(self.destdir, dir.path, dir.name, i))
            r = copy_file(filepath, dest_filepath, ignore_times)
            if r == 'Failed':
                self.logger.warning('%s %s' % (r, dest_filepath))
            else:
                self.logger.info('%s %s' % (r, dest_filepath))
            
    def proc_dir(self, dir):
        self.proc_yaml(dir)
        self.proc_partials(dir)

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

if __name__ == '__main__':

    if '--version' in sys.argv:
        print('Webify2:    %s' % __version__)
        print('logfile:    %s' % logfile)
        print('ignorefile: %s' % ignorefile)
        print('Git info:   %s' % get_gitinfo())
        print('Python:     %s.%s' % (sys.version_info[0],sys.version_info[1]))
        print('Pypandoc:   %s' % pypandoc.__version__)
        print('Pyyaml:     %s' % yaml.__version__)
        print('Pystache:   %s' % pystache.__version__)
        print('Json:       %s' % json.__version__)
        print('Pathspec:   %s' % pathspec.__version__)
        exit(0)

    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('srcdir', help='Source directory')
    cmdline_parser.add_argument('destdir', help='Destination directory')
    cmdline_parser.add_argument('--version', action='version', version='Webify2: {version}'.format(version=__version__))
    cmdline_parser.add_argument('-v','--verbose',action='store_true',default=False,help='Prints helpful messages')
    cmdline_parser.add_argument('-d','--debug',action='store_true',default=False,help='Turns on (global) debug messages')
    cmdline_parser.add_argument('--debug-rc',action='store_true',default=False,help='Turns on rendering context debug messages')
    cmdline_parser.add_argument('--debug-db',action='store_true',default=False,help='Turns on file database debug messages')
    cmdline_parser.add_argument('--debug-yaml',action='store_true',default=False,help='Turns on yaml debug messages')
    cmdline_parser.add_argument('--debug-render',action='store_true',default=False,help='Turns on render debug messages')
    cmdline_parser.add_argument('--debug-md',action='store_true',default=False,help='Turns on mdfile debug messages')
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Use log file.')
    cmdline_parser.add_argument('-i', '--ignore-times', action='store_true', default=False, help='Forces the generation of the output file even if the source file has not changed')
    cmdline_args = cmdline_parser.parse_args()

    ######################################################################
    # Setting up logging
    logfile = None if not cmdline_args.log else logfile
    loglevel = logging.INFO  if cmdline_args.verbose else logging.WARNING
    loglevel = logging.DEBUG if cmdline_args.debug   else loglevel
    logger = WebifyLogger.make(name='webify', loglevel=loglevel, logfile=logfile)

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

    ignore_times = cmdline_args.ignore_times
    ######################################################################
    
    terminal = Terminal()
    
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    logger.info('Prog name:   %s' % prog_name)
    prog_dir = os.path.dirname(prog_name)
    logger.info('Prog dir:    %s' % prog_dir)
    cur_dir = os.getcwd()
    logger.info('Current dir: %s' % cur_dir)

    logger.info('Version:    %s' % __version__)
    logger.info('logfile:    %s' % logfile)
    logger.info('Git info:   %s' % get_gitinfo())
    logger.info('Python:     %s.%s' % (sys.version_info[0],sys.version_info[1]))
    logger.info('Pypandoc:   %s' % pypandoc.__version__)
    logger.info('Pyyaml:     %s' % yaml.__version__)
    logger.info('Pystache:   %s' % pystache.__version__)
    
    meta_data = {
        'prog-name': prog_name,
        'prog-dir': prog_dir,
        'cur-dir': cur_dir,
        'src-dir': cmdline_args.srcdir,
        'dest-dir': cmdline_args.destdir,
        '__version__': __version__,
        'root': os.path.abspath(cmdline_args.srcdir)
    }
    
    webify = Webify()
    webify.set_src(cmdline_args.srcdir, meta_data)
    webify.set_dest(cmdline_args.destdir)
    webify.traverse()
        
    
    
