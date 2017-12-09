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
            with codecs.open(self.filepath, 'r') as stream:
                self.buffer = stream.read().decode('utf-8')
            self.logger.debug('Loaded html file: %s' % self.filepath)
        except:
            self.logger.error('Error loading file: %s' % self.filepath)
            self.buffer = ''

    def get_buffer(self):
        assert self.buffer
        return self.buffer
