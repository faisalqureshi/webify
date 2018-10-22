import os
import logging
import inspect
import subprocess
import pprint as pp
import pystache

def get_gitinfo():
    try:
        webifydir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        __gitinfo__ = subprocess.check_output(["git", "describe"], cwd=webifydir).strip()
    except:
        __gitinfo__ = 'Not found'
    return __gitinfo__

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
        if WebifyLogger.is_debug(logger):
            print('Template:')
            print(template)
            print('Context:')
            pp.pprint(context)
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
