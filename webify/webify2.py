import argparse
import logging
import os
import codecs
import datetime
import sys
import pathspec
import pprint as pp
import yaml
import copy
import pystache
#from mdfile2 import MDfile

from globals import __version__
logfile = 'foo.log'
ignorefile = '.webifyignore'

def make_directory(dirpath):
    try:
        os.makedirs(dirpath)
    except OSError:
        if os.path.isdir(dirpath):
            return 'Found'
        else:
            return None
    return 'Created'

def mustache_render(template, context):
    logger = WebifyLogger.get('render')

    try:
        logger.debug('Success pystache render')        
        rendered_buf = pystache.render(template, context)
    except:
        logger.warning('Error pystache render')
        rendered_buf = template

    return rendered_buf

class WebifyLogger:
    @staticmethod
    def make(name, loglevel=logging.WARNING, logfile=None):
        logger = logging.getLogger(name)
        if logger.handlers:
            return logger

        logger.setLevel(logging.DEBUG)
        
        # Console
        fmtstr = '%(message)s'
        formatter = logging.Formatter(fmtstr)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
        # Logfile
        if logfile:
            fmtstr = '%(name)-8s \t %(levelname)-8s \t [%(asctime)s] \t %(message)s'
            formatter = logging.Formatter(fmtstr)
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return WebifyLogger.set_level(logger, loglevel)

    @staticmethod
    def get(name):
        return logging.getLogger(name)
    
    @staticmethod 
    def set_level(logger, level):
        assert level in [logging.INFO, logging.WARNING, logging.DEBUG]
        
        if level == logging.WARNING:
            h1 = logging.WARNING
            h2 = logging.INFO
        else:
            h1 = level
            h2 = level

        logger.handlers[0].setLevel(h1)
        if len(logger.handlers) > 1: logger.handlers[1].setLevel(h2)
        return logger

    @staticmethod
    def is_debug(logger):
        return logger.handlers[0].level <= logging.DEBUG

class DirTree:
    class DirNode:
        def __init__(self, path, name):
            self.logger = WebifyLogger.get('db')
            self.files = {'yaml': [], 'html': [], 'misc': []}
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


class Terminal:
    def __init__(self):
        try:
            self.rows, self.cols = os.popen('stty size', 'r').read().split()
        except:
            self.rows, self.cols = 24, 16

    def r(self):
        return int(self.rows)
        
    def c(self):
        return int(self.cols)-1

class RenderingContext:
    def __init__(self):
        self.logger = WebifyLogger.get('rc')
        self.rc = {}
        self.diff_stack = []

    def data(self):
        return self.rc
        
    def diff(self):
        return {'a': [], 'm': []}
        
    def push(self):
        self.diff_stack.append(self.diff())

    def add(self, data):
        diff = self.diff_stack[-1]

        for k in data.keys():
            if k in self.rc.keys():
                diff['m'].append({k: copy.deepcopy(self.rc[k])})
                self.rc[k] = data[k]
            else:
                kv = {k: data[k]}
                diff['a'].append({k: data[k]})
                self.rc.update(kv)
                
    def pop(self):
        diff = self.diff_stack.pop()
        for i in diff['a']:
            for k in i.keys():
                del self.rc[k]
        for i in diff['m']:
            for k in i.keys():
                self.rc[k] = i[k]

    def get(self):
        return self.rc

    def print(self):
        pp.pprint(self.rc)

class YAMLfile:
    """
    Yaml files play a central role in webify.  These store all rendering context.
    Each yaml files should only contain on yaml block.

    """
    def __init__(self, filepath):
        self.logger = WebifyLogger.get('yaml')
        self.filepath = filepath
        self.data = None

    def load(self):
        try:
            with codecs.open(self.filepath, 'r') as stream:
                self.data = yaml.load(stream)
            self.logger.info('Loaded YAML file: %s' % self.filepath)
        except:
            self.logger.warning('Error loading YAML file: %s' % self.filepath)
            self.data = {}

        if WebifyLogger.is_debug(self.logger):
            self.logger.debug('Yaml file contents')
            pp.pprint(self.data)

class HTMLfile:

    def __init__(self, filepath):
        self.logger = WebifyLogger.get('html')
        self.filepath = filepath
        self.buffer = None

    def load(self):
        try:
            with codecs.open(self.filepath, 'r', 'utf-8') as stream:
                self.buffer = stream.read()
            self.logger.info('Loaded html file: %s' % self.filepath)
        except:
            self.logger.warning('Error loading file: %s' % self.filepath)
            self.buffer = ''
        return self

    def get_buffer(self):
        assert self.buffer
        return self.buffer
            
class IgnoreList:
    def __init__(self):
        self.logger = WebifyLogger.get('db')
        self.ignorelist = []

    def read_ignore_file(self, ignorefile):
        self.logger.info('Reading ignore file: %s' % ignorefile)
        try:
            with codecs.open(ignorefile, 'r') as stream:
                self.spec = pathspec.PathSpec.from_lines('gitignore', stream)
        except:
            self.spec = None
            self.logger.warning('Cannot read ignorefile: %s' % ignorefile)

    def ignore(self, filepath):
        if self.spec:
            return self.spec.match_file(filepath)
        return False
    
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
            self.ignore.read_ignore_file(os.path.join(srcdir, __ignore_file__))

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
        self.logger.info('Processing folder %s' % dir.get_path())
        self.rc.push()

    def proc_dir(self, dir):
        for i in dir.files['yaml']:
            yaml_file = YAMLfile(filepath=os.path.join(dir.get_path(), i))
            yaml_file.load()
            self.rc.add(yaml_file.data)

        data = {}
        if dir.partials:
            self.logger.debug('Processing _partials')
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
            for i in dir.partials.files['md']:
                md_file = MDfile(filepath=os.path.join(dir.partials.get_path(), i))
                self.rc.push()
                buffer = md_file.load().convert(self.rc.data())
                self.rc.pop()
            self.rc.pop()            
            self.rc.add(data)

        logger_rc =  WebifyLogger.get('rc')
        if WebifyLogger.is_debug(logger_rc):
            logger_rc.debug('Current rendering context')
            self.rc.print()

            
    def leave_dir(self, dir):
        self.rc.pop()
            
    def traverse(self):
        self.dir_tree.collect(rootdir=self.srcdir, ignore=self.ignore)
        self.dir_tree.traverse(enter_func=self.enter_dir, proc_func=self.proc_dir, leave_func=self.leave_dir)

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
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Use log file.')
    cmdline_args = cmdline_parser.parse_args()

    ######################################################################
    # Setting up logging
    logfile = None if cmdline_args.log == None else __logfile__
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
    ######################################################################
    
    terminal = Terminal()
    
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)
    cur_dir = os.getcwd()
    logger.info('='*terminal.c())
    logger.info('Prog name: %s  ' % prog_name)
    logger.info('Prog dir: %s   ' % prog_dir)
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
    
    
