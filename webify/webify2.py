import argparse
import pprint as pp
import sys
import logging
import os
from util2 import get_gitinfo, make_directory, mustache_render, WebifyLogger, Terminal, RenderingContext, YAMLfile, HTMLfile, IgnoreList
from mdfile2 import MDfile

from globals import __version__
logfile = 'webify2.log'
ignorefile = '.webifyignore'

class DirTree:
    class DirNode:
        def __init__(self, path, name):
            self.logger = WebifyLogger.get('db')
            self.files = {'yaml': [], 'html': [], 'misc': [], 'md': []}
            self.name = name
            self.path = path
            self.children = []
            self.partials = None
    
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

        def get_path(self):
            return os.path.join(self.path, self.name)

        def __repr__(self):
            s = "Path: " + self.path + ", Name: " + self.name
            return s
            
    def __init__(self):
        self.logger = WebifyLogger.get('db')
        self.rootdir = None
        
    def collect(self, rootdir, ignore=None):
        self.ignore = ignore
        self.rootdir = self.DirNode(path='', name=rootdir)

        dirs = [self.rootdir]
        while len(dirs) > 0:
            cur_dir_node = dirs.pop()

            self.logger.debug('Collecting directory %s' % cur_dir_node.get_path())
            for entry in os.scandir(cur_dir_node.get_path()):
                if ignore and ignore.ignore(entry.name):
                    self.logger.debug('Ignoring          : %s' % entry.name)
                    continue
                
                if entry.is_dir():
                    sub_dir_node = self.DirNode(path=cur_dir_node.get_path(), name=entry.name)
                    cur_dir_node.add_child(sub_dir_node)
                    dirs.append(sub_dir_node)
                    self.logger.debug('Added subdirectory: %s' % entry.name)
                else:
                    self.logger.debug('Added file        : %s' % entry.name)
                    cur_dir_node.add_file(name=entry.name)

    def __traverse__(self, dir, enter_func, proc_func, leave_func):
        if enter_func: enter_func(dir)
        if proc_func: proc_func(dir)
        for i in dir.children:
            self.__traverse__(i, enter_func, proc_func, leave_func)
        if leave_func: leave_func(dir)
            
    def traverse(self, enter_func=None, proc_func=None, leave_func=None):
        rootdir = self.rootdir
        self.__traverse__(rootdir, enter_func, proc_func, leave_func)

class Webify:
    def __init__(self):
        self.logger = WebifyLogger.get('webify')
        self.rc = RenderingContext()
        self.ignore = IgnoreList()
        self.dir_tree = DirTree()

    def set_src(self, srcdir):
        self.srcdir = os.path.abspath(srcdir)
        if not os.path.isdir(self.srcdir):
            self.logger.critical('Source folder not found: %s' % srcdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error source folder')
        else:
            self.logger.info('Source folder found: %s' % srcdir)
            self.ignore.read_ignore_file(os.path.join(srcdir, ignorefile))

    def set_dest(self, destdir):
        self.destdir = os.path.abspath(destdir)
        r = make_directory(destdir)
        if not r:
            self.logger.critical('Cannot create destination folder: %s' % destdir)
            self.logger.critical('Nothing to do here.')
            raise ValueError('Error destination folder')
        else:
            self.logger.info('Destination directory %s: %s' % (r, destdir))

    def enter_dir(self, dir):
        self.logger.info('+ Processing folder %s' % dir.get_path())

        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.info('-'*terminal.c())
            logger_rc.debug('Rendering context (enter: %s)' % dir.name)
            self.rc.print()
        
        self.rc.push()

    def proc_dir(self, dir):
        for i in dir.files['yaml']:
            yaml_file = YAMLfile(filepath=os.path.join(dir.get_path(), i))
            yaml_file.load()
            self.rc.add(yaml_file.data)

        data = {}    
        if dir.partials:
            self.logger.info('+ Processing: %s' % dir.partials.get_path())
            self.rc.push()
            for i in dir.partials.files['yaml']:
                yaml_file = YAMLfile(filepath=os.path.join(dir.partials.get_path(), i))
                yaml_file.load()
                self.rc.add(yaml_file.data)
            
            for i in dir.partials.files['html']:
                html_file = HTMLfile(filepath=os.path.join(dir.partials.get_path(), i))
                buffer = html_file.load().get_buffer()
                rendered_buf = mustache_render(template=buffer, context=self.rc.data())
                data[i] = rendered_buf

            extras = { 'output-file': None, 'ignore-times': True, 'standalone': False, 'preprocess-mustache': True }
            for i in dir.partials.files['md']:
                self.rc.push()
                filepath = os.path.join(dir.partials.get_path(), i)
                md_file = MDfile(filepath=filepath, rootdir=dir.partials.get_path(), extras=extras, rc=self.rc)
                ret_type, buffer, _ = md_file.load().get_buffer()
                self.rc.pop()
                if not ret_type == 'buffer':
                    self.logger.warning('Ignoring _partials file: %s' % filepath)
                else:
                    rendered_buf = mustache_render(template=buffer, context=self.rc.data())
                    data[i] = rendered_buf
            self.logger.info('> Done processing: %s' % dir.partials.get_path())
            self.rc.pop()            
            self.rc.add(data)

        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.debug('\nRendering context (inside: %s)' % dir.name)
            self.rc.print()
            
    def leave_dir(self, dir):
        self.rc.pop()
        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.debug('\nRendering context (leave: %s)' % dir.name)
            self.rc.print()
            logger_rc.info('-'*terminal.c())
        self.logger.info('> Done processing folder %s' % dir.get_path())
            
    def traverse(self):
        self.dir_tree.collect(rootdir=self.srcdir, ignore=self.ignore)
#        self.dir_tree.traverse(enter_func=self.enter_dir, proc_func=self.proc_dir, leave_func=self.leave_dir)

if __name__ == '__main__':

    if '--version' in sys.argv:
        print('Webify2 version: %s' % __version__)
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
    cmdline_args = cmdline_parser.parse_args()

    ######################################################################
    # Setting up logging
    logfile = None if cmdline_args.log == None else logfile
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
    l = logging.DEBUG if cmdline_args.debug_render else loglevel    
    WebifyLogger.make(name='render', loglevel=l, logfile=logfile)
    l = logging.DEBUG if cmdline_args.debug_md else loglevel    
    WebifyLogger.make(name='mdfile', loglevel=l, logfile=logfile)
    ######################################################################
    
    terminal = Terminal()
    
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)
    cur_dir = os.getcwd()
    logger.info('='*terminal.c())
    logger.info('Prog name:   %s' % prog_name)
    logger.info('Prog dir:    %s' % prog_dir)
    logger.info('Current dir: %s' % cur_dir)
    logger.info('-'*terminal.c())

        
    webify = Webify()
    #try:
    webify.set_src(cmdline_args.srcdir)
    webify.set_dest(cmdline_args.destdir)
    webify.traverse()
    #except Exception as error:
    #    print('Oops: ' + repr(error))
        
    logger.info('='*terminal.c())
    
    
