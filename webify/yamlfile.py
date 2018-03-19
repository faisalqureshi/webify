import yaml
import codecs
import logging
import argparse
import util
import pprint
import pypandoc

class YAMLfile:
    """
    Yaml files play a central role in webify.  These store all rendering context.
    Each yaml files should only contain on yaml block.

    """

    def __init__(self, filepath, dbglevel, logfile):
        self.logger = util.setup_logger('YAMLfile', dbglevel=dbglevel, logfile=logfile)
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
        
        self.apply_filters(self.pandoc_filter, self.data)

    def pandoc_filter(self, str):
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
            self.logger.warning('Error applying pandoc filter on key %s' % str[7:])
        return str

    def apply_filters(self, filter, data):
        self.logger.debug('Apply filters')

        if not data:
            return None
        if isinstance(data, bool) or isinstance(data, int) or isinstance(data, float):
            return None
        if isinstance(data, dict):
            for key, value in data.iteritems():
                retval = self.apply_filters(filter, value)
                if retval:
                    data[key] = retval
            return None
        if isinstance(data, list):
            for i in range(len(data)):
                retval = self.apply_filters(filter, data[i])
                if retval:
                    data[i] = retval
            return None

        return filter(data)

    def get_data(self):
        assert self.data
        return self.data

    def pprint(self):
        print '---------------------------------------------'
        print 'YAML file: ', self.filepath
        print 'Data:'
        pprint.pprint(self.data, indent=1)
        print '---------------------------------------------'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('yamlfile', help='YAML file.')
    parser.add_argument('-y','--yaml', nargs='*', action='append', help='Space separated list of extra yaml files to process')
    parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages')
    args = parser.parse_args()

    yamlfiles = [args.yamlfile]
    if args.yaml:
        yamlfiles.extend(args.yaml[0])

    dbglevel = logging.INFO
    if args.debug:
      dbglevel = logging.DEBUG

    print 'YAML file'
    for f in yamlfiles:
        y = YAMLfile(f, dbglevel=dbglevel)
        y.load()
        y.pprint()
        y.apply_filters(y.pandoc_filter, y.get_data())
        y.pprint()



