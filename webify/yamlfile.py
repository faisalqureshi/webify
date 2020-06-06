import util2 as util
import pprint as pp
import yaml
import codecs
from util2 import apply_filter, filter_pandoc


class YAMLfile:
    """
    Yaml files play a central role in webify.  These store all rendering context.
    Each yaml files should only contain on yaml block.

    """
    def __init__(self, filepath):
        self.logger = util.WebifyLogger.get('yaml')
        self.filepath = filepath
        self.data = None

    def load(self):
        try:
            with codecs.open(self.filepath, 'r') as stream:
                self.data = yaml.safe_load(stream)
            self.logger.info('Loaded YAML file: %s' % self.filepath)

            self.logger.debug('YAML file contents (before filter application):')
            self.logger.debug(pp.pformat(self.data))
            self.data = apply_filter(filter_pandoc, self.data)
        except:
            self.logger.warning('Error loading YAML file: %s' % self.filepath)
            self.data = {}

        if self.data == None:
            self.logger.warning('No readable data in YAML file: %s' % self.filepath)
            self.data = {}

        self.logger.debug('YAML file contents:')
        self.logger.debug(pp.pformat(self.data))


    # def apply_filter(self, filter, data):
    #     if not data:
    #         return None
    #     if isinstance(data, dict):
    #         for key, value in data.items():
    #             retval = self.apply_filter(filter, value)
    #             if retval:
    #                 data[key] = retval
    #         return data
    #     if isinstance(data, list):
    #         for i in range(len(data)):
    #             retval = self.apply_filter(filter, data[i])
    #             if retval:
    #                 data[i] = retval
    #         return data
    #     if isinstance(data, str):
    #         return filter(data)
    #     return data

    # def filter_pandoc(self, str):
    #     try:
    #         s = str.strip(' ')
    #         if s[0:8] == '_pandoc_':
    #             pdoc_args = ['--mathjax','--highlight-style=pygments']
    #             s = pypandoc.convert_text(s[8:], to='html', format='md', extra_args=pdoc_args)
    #             s = s.replace('<p>', '', 1)                
    #             s = ''.join(s.rsplit('</p>', 1))
    #             return s
    #         else:
    #             pass
    #     except:
    #         self.logger.warning('Error applying pandoc filter on key %s' % str[7:])
    #     return str
    


