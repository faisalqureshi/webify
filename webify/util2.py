import os
import logging
import inspect
import subprocess
import pprint as pp
import pystache
import sys
import pathspec
import codecs
import copy
import shutil
import filecmp
import pypandoc
import jinja2
import fnmatch 
import file_processor 


def filter_pandoc(str):
    logger = WebifyLogger.get('mdfile')
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
        logger.warning('Error applying pandoc filter on key %s' % str[7:])
    return str

def filter_dict(filter, data):
    if not data:
        return None
    if isinstance(data, dict):
        for key, value in data.items():
            retval = filter_dict(filter, value)
            if retval:
                data[key] = retval
        return data
    if isinstance(data, list):
        for i in range(len(data)):
            retval = filter_dict(filter, data[i])
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

def copy_file(src, dest, force_copy):
    if not force_copy:
        try:
            if filecmp.cmp(src, dest):
                return True, 'Exists'
        except:
            pass

    try:
        shutil.copy2(src, dest)
        return True, 'Copied'
    except:
        pass
    return False, 'Copy failed'

def save_to_file(filepath, buffer):
    try:
        with codecs.open(filepath, 'w', 'utf-8') as stream:
            stream.write(buffer)
        return True
    except:
        return False

def remove_file(filepath):
    if not os.path.exists(filepath):
        return True, 'Nothing to delete'

    try:
        os.remove(filepath)
        return True, 'Deleted'
    except:
        pass

    return False, 'Deletion failed'

def render(filepath, context, renderer):
    logger = WebifyLogger.get('render')
    try:
        with codecs.open(filepath, 'r', 'utf-8') as stream:
            template = stream.read()
            logger.debug('Loaded render file: %s' % filepath)
    except:
        logger.warning('Cannot load render file: %s' % filepath)
        return ''

    return renderer(template, context, filepath)

def jinja2_renderer(template, context, file_info):
    logger = WebifyLogger.get('render')

    # if WebifyLogger.is_debug(logger):
    #     print('Template:')  
    #     print(template)
    #     print('Context:')
    #     pp.pprint(context)

    #rendered_buf = Template(template).render(context)

    try:
        rendered_buf = jinja2.Template(template).render(context)
        logger.debug('Success jinja2 render: %s' % file_info)
    except jinja2.exceptions.TemplateSyntaxError as e:
        logger.warning('Error jinja2 render: %s\n%s' % (file_info, e))
        if WebifyLogger.is_debug(logger) or True:
            print('Template:')
            print(template)
            #print('Context:')
            #pp.pprint(context)
        rendered_buf = template

    # if WebifyLogger.is_debug(logger):
    #     print('Rendered Buf')
    #     print(rendered_buf)

    return rendered_buf

def mustache_renderer(template, context, file_info):
    logger = WebifyLogger.get('render')

    # if WebifyLogger.is_debug(logger):
    #     print('Template:')  
    #     print(template)
    #     print('Context:')
    #     pp.pprint(context)

    try:
        rendered_buf = pystache.render(template, context)
        logger.debug('Success pystache render: %s' % file_info)        
    except:
        logger.warning('Error pystache render: %s' % file_info)
        if WebifyLogger.is_debug(logger):
            print('Template:')
            print(template)
            # print('Context:')
            # pp.pprint(context)
        rendered_buf = template

    # if WebifyLogger.is_debug(logger):
    #     print('Rendered Buf')
    #     print(rendered_buf)

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
        assert level in [logging.INFO, logging.WARNING, logging.DEBUG, logging.ERROR]
        
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
    def is_debug_name(name):
        try:
            logger = WebifyLogger.get(name)
            return logger.handlers[0].level <= logging.DEBUG
        except:
            return False

    @staticmethod
    def is_info(logger):
        try:
            return logger.handlers[0].level <= logging.INFO
        except:
            return False

    @staticmethod
    def is_info_name(name):
        try:
            logger = WebifyLogger.get(name)
            return logger.handlers[0].level <= logging.INFO
        except:
            return False

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

# class YAMLfile:
#     """
#     Yaml files play a central role in webify.  These store all rendering context.
#     Each yaml files should only contain on yaml block.

#     """
#     def __init__(self, filepath):
#         self.logger = WebifyLogger.get('yaml')
#         self.filepath = filepath
#         self.data = None

#     def load(self):
#         try:
#             with codecs.open(self.filepath, 'r') as stream:
#                 self.data = yaml.safe_load(stream)
#             self.logger.info('Loaded YAML file: %s' % self.filepath)
# #            pp.pprint(self.data)
#             self.data = apply_filter(md_filter, self.data)
# #            pp.pprint(self.data)
            
#         except:
#             self.logger.warning('Error loading YAML file: %s' % self.filepath)
#             self.data = {}

#         if WebifyLogger.is_debug(self.logger):
#             self.logger.debug('Yaml file contents')
#             pp.pprint(self.data)

# class HTMLfile:

#     def __init__(self, filepath):
#         self.logger = WebifyLogger.get('html')
#         self.filepath = filepath
#         self.buffer = None

#     def load(self):
#         try:
#             with codecs.open(self.filepath, 'r', 'utf-8') as stream:
#                 self.buffer = stream.read()
#             self.logger.info('Loaded html file: %s' % self.filepath)
#         except:
#             self.logger.warning('Error loading file: %s' % self.filepath)
#             self.buffer = ''
#         return self

#     def get_buffer(self):
#         assert self.buffer
#         return self.buffer

#     def save(self, filepath):
#         pass
    

class IgnoreList:
    def __init__(self, srcdir):
        self.logger = WebifyLogger.get('db-ignore')
        self.ignorelist = []
        self.srcdir = srcdir

    def read_ignore_file(self, ignorefile):
        self.logger.info('Reading ignore file: %s' % ignorefile)
        try:
            with codecs.open(ignorefile, 'r', 'utf-8') as stream:
                for line in stream:
                    p, f = os.path.split(line.strip())
                    self.logger.debug('%s %s' % (p, f))
                    self.ignorelist.append((p, f))
        except:
            self.spec = None
            self.logger.warning('Cannot read ignorefile: %s' % ignorefile)

    def match(self, path, name, is_dir, p, f):

        # if WebifyLogger.is_debug(self.logger):
        #     print('srcdir: %s' % self.srcdir)
        #     print('path:   %s' % path)
        #     print('name:   %s' % name)
        #     print('p:      %s' % p)
        #     print('f:      %s' % f)

        if p == '' and f == '':
            self.warning('Illegal empty pattern found in ignore file')
        
        if p == '':
            r = fnmatch.fnmatch(name, f)
        elif p[0] == '/':
            if f == '':
                r = fnmatch.fnmatch(os.path.join(path, name), p) if is_dir else False
            else:
                r = fnmatch.fnmatch(path, p) and fnmatch.fnmatch(name, f)
        else: 
            if f == '':
                r = fnmatch.fnmatch(name, p) if is_dir else False
            else:
                r = fnmatch.fnmatch(path, p) and fnmatch.fnmatch(name, f)

        self.logger.debug('Ignore: %s - %s %s == %s %s' % (r, path, name, p, f))
        return r
            
    def ignore(self, path, name, is_dir):
        self.logger.debug('Checking %s %s' % (path, name))

        path = '/' if path == self.srcdir else path.replace(self.srcdir, '')

        should_ignore = False        
        for (p, f) in self.ignorelist:
            should_ignore = self.match(path, name, is_dir, p, f)
            if should_ignore:
                self.logger.debug('Ignore file')
                return True
        self.logger.debug('Do not ignore file')
        return False

def process_file(filepath, dest_filepath, force_copy):
    _, ext = os.path.splitext(filepath)

    processor = make_file_processor(ext)
    return processor(filepath, dest_filepath, force_copy)
    
def make_file_processor(ext):
    if ext == '.ipynb':
        return file_processor.JupyterNotebook
    else:
        return copy_file

def get_values(k, d, d2=None):
    """
    k = key
    d = dictionary
    d2 = extra dictionary - check out get_files() in mdfile2.py to see how one might use an extra dictionary

    Example 1:
    d[k] = v
    get_values(d, k) -> v

    Example 2:
    d[k] = [v1, v2, v3]
    get_values(d, k) -> [v1, v2, v3]

    Useful for processing yaml files of the form

    Case 1:
    file: file1

    Case 2:
    file:
        - file1
        - file2

    Here the first case refers to example 1, and the second case refers to example 2.
    """
    try:
        f1 = d[key] if isinstance(d[key], list) else [d[key]]
        f1 = [x for x in f1 if x is not None]
    except:
        f1 = []
    try:
        f2 = d2[key] if isinstance(d2[key], list) else [d2[key]]
        f2 = [x for x in f2 if x is not None]
    except:
        f2 = []
    files = f1 + f2
    return files

def pick_last_value(k, d, d2=None):
    v = get_values(k, d, d2)
    if len(v) > 0: return v[-1]
    return None

def pick_all_values(k, d, d2=None):
    return get_values(k, d, d2)    
        
