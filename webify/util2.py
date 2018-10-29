import os
import logging
import inspect
import subprocess
import pprint as pp
import pystache
import sys
import pathspec
import codecs
import yaml
import copy
import shutil
import filecmp
import pypandoc
from jinja2 import Template

def md_filter(str):
    try:
        s = str.strip(' ')
        if s[0:8] == '_pandoc_':
            pdoc_args = ['--mathjax','--highlight-style=pygments']
            s = pypandoc.convert_text(s[8:], to='html', format='md', extra_args=pdoc_args)
            s = s.replace('<p>', '', 1)                
            s = ''.join(s.rsplit('</p>', 1))
            return s
        else:
            pass
    except:
        pass
        #self.logger.warning('Error applying pandoc filter on key %s' % str[7:])
    return str

def apply_filter(filter, data):
    if not data:
        return None
    if isinstance(data, dict):
        for key, value in data.items():
            retval = apply_filter(filter, value)
            if retval:
                data[key] = retval
        return data
    if isinstance(data, list):
        for i in range(len(data)):
            retval = apply_filter(filter, data[i])
            if retval:
                data[i] = retval
        return data
    if isinstance(data, str):
        return filter(data)
    return data

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

def copy_file(src, dest, force_save):
    """
    Copy src to dest

    Returns status:
        - None: failed
        - 1: copied
        - 2: skipped
    """
    if not force_save and os.path.exists(dest):
        if filecmp.cmp(src, dest):
            return 'Skipped'

    try:
        shutil.copy2(src, dest)
        return 'Copied'
    except:
        pass
    return 'Failed'

def save_to_file(filepath, buffer):
    try:
        with codecs.open(filepath, 'w', 'utf-8') as stream:
            stream.write(buffer)
        return True
    except:
        return False

def render(filepath, context, renderer):
    logger = WebifyLogger.get('render')
    try:
        with codecs.open(filepath, 'r', 'utf-8') as stream:
            template = stream.read()
            logger.info('Loaded render file: %s' % filepath)
    except:
        logger.warning('Cannot load render file: %s' % filepath)
        return ''

    return renderer(template, context)

def jinja2_renderer(template, context):
    logger = WebifyLogger.get('render')

    if WebifyLogger.is_debug(logger):
        print('Template:')  
        print(template)
        print('Context:')
        pp.pprint(context)

    try:
        rendered_buf = Template(template).render(context)
        logger.debug('Success jinja2 render')
    except:
        logger.warning('Error jinja2 render')
        if WebifyLogger.is_debug(logger):
            print('Template:')
            print(template)
            print('Context:')
            pp.pprint(context)
        rendered_buf = template

    if WebifyLogger.is_debug(logger):
        print('Rendered Buf')
        print(rendered_buf)

    return rendered_buf

def mustache_renderer(template, context):
    logger = WebifyLogger.get('render')

    if WebifyLogger.is_debug(logger):
        print('Template:')  
        print(template)
        print('Context:')
        pp.pprint(context)

    try:
        rendered_buf = pystache.render(template, context)
        logger.debug('Success pystache render')        
    except:
        logger.warning('Error pystache render')
        if WebifyLogger.is_debug(logger):
            print('Template:')
            print(template)
            print('Context:')
            pp.pprint(context)
        rendered_buf = template

    if WebifyLogger.is_debug(logger):
        print('Rendered Buf')
        print(rendered_buf)

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
        try:
            return logger.handlers[0].level <= logging.DEBUG
        except:
            return False

class Terminal:
    def __init__(self):
        try:
        	if sys.platform in ['linux', 'linux2', 'darwin']:
	            self.rows, self.cols = os.popen('stty size', 'r').read().split()
	        else:
	        	self.rows, self.cols = 24, 16
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
#            pp.pprint(self.data)
            self.data = apply_filter(md_filter, self.data)
#            pp.pprint(self.data)
            
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

    def save(self, filepath):
        pass
    

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
