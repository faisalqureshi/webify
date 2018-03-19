import logging
import util
import pprint

class RenderingContext:
    """
    This class sets up and maintains rendering context for "template based rendering."  Currently
    this means that it maintains rendering context for mustache templates.

    Consider the following mustache template:

    This is an example mustache template.  It was written by
    {{author}}.

    Then in order to render this template, we need the rendering context.  This context
    takes the form a python dictionary.  Consider the following python dictionary:

    author: John

    Using this dictionary, the above mustache template will render into:

    This is an example mustache template.  It was written by
    John.
    
    Setting up and maintaining rendering context isn't as straightforward as first appears.  
    The rendering context is folder specific.  Consider the following folder hierarchy:

    a
    |-b
    |-c

    Now consider yaml files in folders a, b and c.  Say these yaml files are a.yaml,
    b.yaml and c.yaml.  Any md file in folder c, will have access to rendering context
    stored in files a.yaml and c.yaml.  An nd file in folder a will only have access 
    rendering context stored in files a.yaml.

    Rendering context is stored in the disk as a yaml file.
    """

    def __init__(self, rootdir, dbglevel, logfile):
        self.logger = util.setup_logger('RenderingContext', dbglevel=dbglevel, logfile=logfile)        
        self.rootdir = rootdir
        self.context = {}
        self.logger.info('Initializing rendering context with root %s' % self.rootdir)

    def add(self, path, rc):
        """
        path: folder path
        rc: rendering context stored a python dictionary
        """
        self.context[path] = rc
        self.logger.info('Adding path %s to rendering context' % path)

    def clear_cache(self, path):
        try:
            self.context[path]['__cache__'] = None
        except:
            pass

    def append(self, path, rc):
        """
        path: folder path
        rc: rendering context stored a python dictionary
        """        
        current_rc = self.get(path)
        for k in rc.keys():
            current_rc[k] = rc[k]
            
    def get(self, path):
        if self.logger.getEffectiveLevel() == logging.DEBUG:
            print '\nRenderingContext - get(): %s' % path

        try:
            if self.context[path]['__cache__'] != None:
                self.logger.debug('Using cached value')
                return self.context[path]['__cache__']
        except:
            pass

        parents = [ path ]
        parents[1:] = util.ancestors(path)
        rc = {}

        for i in reversed(parents):
            dir_rc = self.context[i]
            for f in dir_rc:
                file_rc = dir_rc[f]
                for k in file_rc:
                    rc[k] = file_rc[k]

        self.context[path]['__cache__'] = rc

        # if self.logger.getEffectiveLevel() == logging.DEBUG:
        # 	print rc

        return rc

    def pprint(self):
        for path in self.context:
            print '\npath: ', path
            pprint.pprint(self.context[path], indent=1)
