import codecs
import util
import logging

class HTMLfile:

    def __init__(self, filepath, dbglevel=logging.INFO):
        self.logger = util.setup_logging('HTMLfile', dbglevel=dbglevel)
        self.filepath = filepath
        self.buffer = None

    def load(self):
        try:
            with codecs.open(self.filepath, 'r', 'utf-8') as stream:
                self.buffer = stream.read()
                if not isinstance(self.buffer, unicode):
                    self.buffer = self.buffer.decode('utf-8')
            self.logger.debug('Loaded html file:\n\t - %s' % self.filepath)
        except:
            self.logger.error('Error loading file:\n\t - %s' % self.filepath)
            self.buffer = ''

    def get_buffer(self):
#       print self.filepath
#       I need to fix this a bug here.  The following assertion failes if an empty html file is read
        assert self.buffer
        return self.buffer
