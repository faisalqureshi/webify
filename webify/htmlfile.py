import util2 as util
import codecs

class HTMLfile:

    def __init__(self, filepath):
        self.logger = util.WebifyLogger.get('html')
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

        if self.buffer == None:
            self.logger.warning('No readable information found in file: %s' % self.filepath) 
            self.buffer = ''       

        return self

    def get_buffer(self):
        return self.buffer