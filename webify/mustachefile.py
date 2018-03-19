import logging
import codecs
import pystache
import argparse
import util
import renderingcontext


def mustache_render(template, context, logger):
    import pystache
    try:
        logger.debug('Rendering mustache template using pystache')
        rendered_buf = pystache.render(template, context)
    except:
        logger.debug('Error rendering mustache template using pystache')
        rendered_buf = template
    return rendered_buf


class Mustachefile:

    def __init__(self, filepath, dbglevel, logfile):
        self.logger = util.setup_logger('Mustachefile', dbglevel=dbglevel, logfile=logfile)
        self.filepath = filepath
        self.template = None

    def load(self):
      try:
          with codecs.open(self.filepath, 'r') as stream:
              buf = stream.read().decode('utf-8')
              self.template = pystache.parse(buf)
          self.logger.info('Loaded mustache file: %s' % self.filepath)
      except:
          self.logger.error('Error loading mustache file: %s' % self.filepath)
          self.template = ''

    def get_template(self):
        if not self.template:
            self.load()
        return self.template

    def pprint(self):
        print '---------------------------------------------'
        print 'Mustache file:', self.filepath
        print 'Template:'
        print self.template
        print '---------------------------------------------'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mustachefile', help='Mustache file.')
    parser.add_argument('-y','--yaml', nargs='*', action='append', help='Space separated list of extra yaml files to process')
    parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages')
    args = parser.parse_args()

    dbglevel = logging.INFO
    if args.debug:
      dbglevel = logging.DEBUG

    yamlfiles = []
    if args.yaml:
        yamlfiles.extend(args.yaml[0])

    m = Mustachefile(args.mustachefile, dbglevel)
    m.load()
    m.pprint()

    if not len(yamlfiles) > 0:
        exit(0)

    for f in yamlfiles:
        print f
