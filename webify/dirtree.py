import util2 as util
#import logging
import os

class DirTree:
    class DirNode:
        def __init__(self, root, path, name):
            self.logger = util.WebifyLogger.get('db')
            self.files = {'yaml': [], 'html': [], 'misc': [], 'md': [], 'ipynb': []}
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
            elif ext.lower() in ['.ipynb']:
                self.files['ipynb'].append(name)
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
        self.logger = util.WebifyLogger.get('db')
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
        if enter_func: 
            enter_func(dir)
        if proc_func: 
            skip_dirs, availability, ignore_info = proc_func(dir)
        for i in dir.children:
            if i.get_fullpath() not in skip_dirs:
                self.__traverse__(i, enter_func, proc_func, leave_func)
            else:
                
                if util.WebifyLogger.is_info(util.WebifyLogger.get('main')):
                    util.WebifyLogger.get('main').info('x-: %s' % i.get_fullpath())
                else:
                    util.WebifyLogger.get('ignored').info('Ignored:\n   %s' % i.get_fullpath() )
        if leave_func: 
            leave_func(dir, availability, ignore_info)
        self.logger.debug('Leaving %s' % dir.get_fullpath())
        
    def traverse(self, enter_func=None, proc_func=None, leave_func=None):
        rootdir = self.rootdir
        self.__traverse__(rootdir, enter_func, proc_func, leave_func)