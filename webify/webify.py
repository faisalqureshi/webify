import argparse
import logging
import filedb as db
from yamlfile import YAMLfile
from renderingcontext import RenderingContext
import mustachefile
from mdfile import MDfile
from htmlfile import HTMLfile
import util
import os
import codecs
import datetime
import copy
import sys

global __version__
__version__ = '1.8.2'

class Webify:
    def __init__(self, rootdir, destdir, debug_levels, use_cache, logfile):

        self.debug_levels = debug_levels
        self.logfile = logfile
        self.logger = util.setup_logger('Webify', dbglevel=self.debug_levels['main'], logfile=logfile)

        self.time_now = datetime.datetime.now()
        self.rootdir = rootdir
        self.destdir = destdir
        self.debug_levels = debug_levels
        self.ok = True
        self.use_cache = use_cache

    def collect_files(self):
        self.logger.info('\n*** Collecting files/folder ***\n')

        self.filedb = db.Filedb(rootdir, dbglevel=self.debug_levels['db'], logfile=logfile)
        self.filedb.collect()
        return self.filedb.get_size()

    def setup_rendering_context(self):
        self.rendering_context = RenderingContext(rootdir, self.debug_levels['rc'], logfile=logfile)

    def load_yamlfiles(self):
        self.logger.info('\n*** Loading YAML files ***\n')

        for d, _, r in db.get_directories(self.filedb):
            self.logger.debug('Directory: %s' % d)

            rc = {}
            for f, p in db.get_files(self.filedb, dirpath=r, fileext='.yaml'):
                self.logger.debug('Yaml file found: %s' % p)
                y = YAMLfile(p, dbglevel=self.debug_levels['yaml'], logfile=self.logfile)
                y.load()
                rc[p] = y.get_data()
                f['handler'] = y

            # Adding webify internal context to the root
            if r == '.':
                rc['__webify_internal__'] = {'auto-last-updated': self.time_now.strftime('%Y-%m-%d %H:%M')}

            self.rendering_context.add(r, rc)

        if self.debug_levels['main'] == logging.DEBUG:
            print '---------------------------------------'
            print 'Rendering context after loading yaml files:'
            self.rendering_context.pprint()
            print '---------------------------------------'

    def load_templates(self):
        self.logger.info('\n*** Loading templates ***\n')

        for f, p in db.get_files(self.filedb, fileext='.mustache'):
            self.logger.debug('Mustache file found: %s' % p)
            m = mustachefile.Mustachefile(p, dbglevel=debug_levels['mustache'], logfile=self.logfile)
            m.load()
            f['handler'] = m

    def render_html(self, htmlfile, buffer, rc):
        '''
        htmlfile: filedb object containing the (current) html file
        buffer: contents of the html file
        rc: rendering context

        Returns: html + rc is rendered using mustache.
        '''
        htmlfile = db.filepath(htmlfile)
        return mustachefile.mustache_render2(htmlfile, htmlfile, buffer, rc, util.setup_logging('Mustachefile', dbglevel=debug_levels['mustache']))

    def render_md(self, mdfile, html, templatefile, rc):
        '''
        mdfile: filedb object containing the current mdfile
        html: rendered html, we use pandoc to render md to html
        templatefile: templatefile that will be used as mustache template.  html will be available
                      during mustache rendering as 'body' key.  we use the "render" key within
                      the mdfile yaml frontmatter to specify this template file.
        rc: rendering context.  Yaml frontmatter in this mdfile is also available during mustache rendering.

        Returns: This function returns html that is ready to be written to the disk
        '''

        mdfile_name = db.filepath(mdfile)

        if not templatefile:
            return html

        # Getting template file that will be used for rendering
        filepath, filename = os.path.split(templatefile)
        filename, fileext = os.path.splitext(filename)
        filepath = filepath.replace(self.rootdir,'.')
        if len(filepath) > 1:
            filepath = filepath[2:]

        if not fileext == '.mustache':
            self.logger.warning('Cannot load template "%s" when rendering %s', templatefile, mdfile_name)
            return html

        # Lets get the entry for this specific md file within the filedb structure
        tf, p = db.search(self.filedb, filename=filename, dirpath=filepath, fileext=fileext)
        if tf:
            mustache_file = tf['handler']

            if not isinstance(html, unicode):
                rc['body'] = html.decode('utf-8')
            else:
                rc['body'] = html

            rendered_md = mustachefile.mustache_render2(mdfile_name, templatefile, mustache_file.get_template(), rc, util.setup_logging('Mustachefile', dbglevel=debug_levels['mustache']))
            rc['body'] = None

            return rendered_md
        else:
            self.logger.warning('Cannot load template "%s" when rendering %s', templatefile, os.path.join(mdfile['path'], mdfile['name']+mdfile['ext']))

        # It seems something didn't work as expected.
        # Perhaps the mustache template was not available.
        # We simply return the html that was passed as argument to this function.
        return html

    def compute_partials(self):
        self.logger.info('\n*** Computing partials ***\n')
        try:
            rc = self.rendering_context.get('_partials')
            self.logger.info('Rendering context for _partials set')
        except:
            self.logger.info('No _partials found.')
            return

        for f, p in db.get_files(self.filedb, dirpath='_partials', fileext='.html'):
            self.logger.info('HTML file found in _partials %s' % p)
            h = HTMLfile(p)
            h.load()
            rc[f['name']+'_html'] = self.render_html(f, h.get_buffer(), rc)
            f['handler'] = h

        for f, p in db.get_files(self.filedb, dirpath='_partials', fileext='.md'):
            self.logger.info('MD file found in _partials %s' % p)
            md = MDfile(p, self.rootdir, dbglevel=self.debug_levels['md'], mtime=f['mtime'])
            md.load()
            format, buffer = md.convert(outputfile=None, use_cache=self.use_cache)
            if not format == 'html':
                self.logger.warning('Error converting file %s in _partials' % f)
                continue

            rc = md.push_rc(rc)
            rc[f['name'] + '_md'] = self.render_md(f, buffer, md.get_renderfile(), rc)
            rc = md.pop_rc(rc)

            #f['handler'] = md
            f['copy-to-destination'] = False # Because files in _partial are never copied over

        self.rendering_context.append('.', rc)

        if self.logger.getEffectiveLevel() == logging.DEBUG:
            util.debug_rendering_context(self.rendering_context.context)

    def render_all_files(self):
        self.logger.info('\n*** Rendering all files ***')

        num_rendered = 0
        for d, _, r in db.get_directories(self.filedb):
            a = [r]
            a[1:] = util.ancestors(r)
            c = [i for i in a if i in ['_partials', '_templates']]
            if len(c) > 0:
                continue

            # rc = self.rendering_context.get(r)

            # if self.debug_levels['rc'] == logging.DEBUG:
            #     print '\n-------------------------------------------------'
            #     print 'render_all_files()'
            #     print 'Directory: ', d, r
            #     util.debug_rendering_context(rc)
            #     print '\n-------------------------------------------------'

            for f, p in db.get_files(self.filedb, dirpath=r, fileext=['.md', '.html']):
                num_rendered += 1
                self.logger.info('\n>>> Rendering file: %s' % p)

                rc = self.rendering_context.get(r)
                if self.debug_levels['rc'] == logging.DEBUG:
                    print '\nFolder specific rc: %s' % r
                    print rc

                if f['ext'] == '.html':
                    h = HTMLfile(p)
                    h.load()
                    f['__rendered__'] = self.render_html(f, h.get_buffer(), rc)
                    continue

                if f['ext'] == '.md':
                    outputfile = os.path.normpath(os.path.join(self.destdir, f['path'], f['name']))
                    md = MDfile(filepath=p, rootdir=self.rootdir, dbglevel=self.debug_levels['md'], mtime=f['mtime'], logfile=self.logfile)
                    md.load()

                    rc = md.push_rc(rc)
                    if self.debug_levels['rc'] == logging.DEBUG:
                        print '\nFile specific rc: %s%s' % (f['name'], f['ext'])
                        print rc
                        print '\nrc_changes:'
                        print md.rc['changes']
                        print '\nrc_additions:'
                        print md.rc['additions']

                    format, buffer = md.convert(outputfile=outputfile, use_cache=self.use_cache, rc=rc)
                    if format == 'html':
                        f['__rendered__'] = self.render_md(f, buffer, md.get_renderfile(), rc)
                    elif format == 'file':
                        f['__generated_file__'] = buffer
                    else:
                        self.logger.warning('Pandoc conversion failed: %s' % p)

                    rc = md.pop_rc(rc)
                    if self.debug_levels['rc'] == logging.DEBUG:
                        print '\nFolder specific rc (after file processing if finished): %s' % r
                        print rc
                        print '-------------------------------------------------'

                    f['copy-to-destination'] = md.get_copy_to_destination()

        self.logger.info('\n>>> Rendered %s files\n' % num_rendered)


    def create_destination_folder(self):
        dd = os.path.abspath(self.destdir)
        self.logger.info('Creating destination folder: %s' % dd)

        dir_creation = util.make_directory(dd)
        if not dir_creation:
            self.logger.error('Cannot make destination directory.  Nothing more to do.  Aborting.')
            exit(-1)
        else:
            self.logger.debug('%s %s' % (dd, dir_creation))

        for d, _, r in db.get_directories(self.filedb):
            a = [r]
            a[1:] = util.ancestors(r)
            c = [i for i in a if i in ['_partials', '_templates']]
            if len(c) > 0:
                continue

            dirpath = os.path.normpath(os.path.join(dd,r))
            self.logger.debug('Creating directory %s' % dirpath)
            dir_creation = util.make_directory(dirpath)
            if not dir_creation:
                self.logger.error('Error creating directory: %s.  Ignoring its contents.' % dirpath)
                continue
            else:
                self.logger.debug('%s %s' % (dirpath, dir_creation))

    def write(self, force_save):
        dd = os.path.abspath(self.destdir)
        self.logger.info('*** Writing to destination: %s ***\n' % dd)

        # If we don't have a desitnation directory, we are in trouble
        # Since we create the destination folder structure right in the beginning
        assert os.path.isdir(dd)

        for d, _, r in db.get_directories(self.filedb):
            a = [r]
            a[1:] = util.ancestors(r)
            c = [i for i in a if i in ['_partials', '_templates']]     # Folders _partials and _templates and their
            if len(c) > 0:                                             # children are not copied over to destination folder
                continue

            dirpath = os.path.normpath(os.path.join(dd,r))

            # If we don't have a desitnation directory, we are in trouble
            # Since we create the destination folder structure right in the beginning
            assert os.path.isdir(dirpath)

            for f, p in db.get_files(self.filedb, dirpath=r):
                if f['ext'] in ['.yaml', '.mustache']:                  # YAML and Mustache files are not copied over to
                    continue                                            # the destination folder

                if self.logger.getEffectiveLevel() == logging.DEBUG:
                    print 'File path', p
                    print '-------------------------------'
                    print f
                    print '-------------------------------'

                if f['ext'] in ['.md', '.html']:

                    if '__rendered__' in f.keys():
                        filepath = os.path.join(dirpath, f['name'] + '.html')

                        try:
                            self.logger.info('Saving rendered content to html file: %s' % filepath)
                            with codecs.open(filepath, 'w', encoding='utf-8') as stream:
                                stream.write(f['__rendered__'])
                        except:
                            self.logger.warning('Failed saving rendered content to html file: %s' % filepath)

                    elif '__generated_file__' in f.keys():
                        pass

                    else:
                        assert True

                    if 'copy-to-destination' in f.keys() and f['copy-to-destination']:
                        filepath = os.path.join(dirpath, f['name']+f['ext'])
                        file_copy = util.copy_file(p, filepath, force_save)
                        if file_copy == 1:
                            self.logger.info('Saving %s at destination' % filepath)
                        elif file_copy == 2:
                            self.logger.info('Skipped saving %s at destination.  Already exists' % filepath)
                        else:
                            self.logger.warning('Failed saving %s at destination' % filepath)

                else:
                    filepath = os.path.join(dirpath, f['name']+f['ext'])
                    file_copy = util.copy_file(p, filepath, force_save)
                    if file_copy == 1:
                        self.logger.info('Saving %s at destination' % filepath)
                    elif file_copy == 2:
                        self.logger.info('Skipped saving %s at destination.  Already exists' % filepath)
                    else:
                        self.logger.warning('Failed saving %s at destination' % filepath)


# class EventHandler(pyinotify.ProcessEvent):
#     def process_IN_CREATE(self, event):
#         print "Creating:", event.pathname
#
#     def process_IN_DELETE(self, event):
#         print "Removing:", event.pathname


# from watchdog.events import FileSystemEventHandler
# class FileChanges(FileSystemEventHandler):
#     def __init__(self):
#         pass

#     def on_any_event(self, event):
#         print event

def handle_commandline_arguments():
    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('rootdir', help='Root directory')
    cmdline_parser.add_argument('destdir', help='Destination directory')
    cmdline_parser.add_argument('--monitor', action='store_true', default=False, help='Monitor root folder for changes')
    cmdline_parser.add_argument('-w','--force-save', action='store_true', default=False, help='Force saving to destination')
    cmdline_parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
    cmdline_parser.add_argument('-s','--status', action='store_true', default=False, help='Prints helpful information about the folder that you plan to webify')
    cmdline_parser.add_argument('-i','--no-cache', action='store_true', default=False, help='Turn off cache usage')

    # Logging and verbosity
    cmdline_parser.add_argument('--debug', action='store_true', default=False, help='Log debugging messages (global, use with caution)')
    cmdline_parser.add_argument('-v','--verbose', action='store_true', default=False, help='More verbose')
    cmdline_parser.add_argument('--debug-md', action='store_true', default=False, help='Debug logger for MD files.')
    cmdline_parser.add_argument('--debug-yaml', action='store_true', default=False, help='Debug logger for Yaml files.')
    cmdline_parser.add_argument('--debug-rc', action='store_true', default=False, help='Debug logger for RC files.')
    cmdline_parser.add_argument('--debug-db', action='store_true', default=False, help='Debug logger for Filedb files.')
    cmdline_parser.add_argument('--debug-mustache', action='store_true', default=False, help='Debug logger for Mustachefile files.')
    cmdline_parser.add_argument('-l','--log', action='store_true', default=False, help='Use log file.')

    # Parsing commandline arguments
    cmdline_args = cmdline_parser.parse_args()

    return cmdline_args

if __name__ == '__main__':

    global prog_name, prog_dir
    prog_name = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
    prog_dir = os.path.dirname(prog_name)

    if '--ver' in sys.argv:
        print('Webify version %s' % version)
        exit(0)

    cmdline_args = handle_commandline_arguments()

    dbg_level = logging.WARNING
    if cmdline_args.verbose:
        dbg_level = logging.INFO
    if cmdline_args.debug:
        dbg_level = logging.DEBUG

    # Logging and verbosity
    debug_levels = { 'main': dbg_level,
                   'md': dbg_level,
                   'yaml': dbg_level,
                   'rc': dbg_level,
                   'db': dbg_level,
                   'mustache': dbg_level }

    # And now selective logging
    if cmdline_args.debug_md:
        debug_levels['md'] = logging.DEBUG
    if cmdline_args.debug_yaml:
        debug_levels['yaml'] = logging.DEBUG
    if cmdline_args.debug_rc:
        debug_levels['rc'] = logging.DEBUG
    if cmdline_args.debug_db:
        debug_levels['db'] = logging.DEBUG
    if cmdline_args.debug_mustache:
        debug_levels['mustache'] = logging.DEBUG

    logfile = None
    if cmdline_args.log:
        logfile = 'webify.log'

    # The following is not yet implemented
    if cmdline_args.monitor:
        print('Feature not yet implemented.')
        exit(-1)
        # import time
        # from watchdog.observers import Observer

        # event_handler = FileChanges()
        # observer = Observer()
        # observer.schedule(event_handler, cmdline_args.rootdir, recursive=True)
        # observer.start()

        # try:
        #     while True:
        #         time.sleep(1)
        # except KeyboardInterrupt:
        #     observer.stop()
        # observer.join()

        # import pynotify
        # wm = pyinotify.WatchManager()
        # mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE  # watched events
        #
        # handler = EventHandler()
        # notifier = pyinotify.Notifier(wm, handler)
        # wdd = wm.add_watch(cmdline_args.rootdir, mask, rec=True)
        # notifier.loop()
    else:
        rootdir = os.path.realpath(cmdline_args.rootdir)
        destdir = os.path.realpath(cmdline_args.destdir)

        webify = Webify(rootdir=rootdir, destdir=destdir, debug_levels=debug_levels, use_cache=not cmdline_args.no_cache, logfile=logfile)
        print('Webify version %s' % __version__)
        webify.logger.info('Webify version %s' % __version__)
        print('Webifying %s' % rootdir)
        webify.logger.info('Webifying %s' % rootdir)

        num_items_found = webify.collect_files()
        webify.logger.info('Collected %s files/folders' % num_items_found)

        if num_items_found == 0:
            webify.logger.error('Cannot webify.  Webification failed.')
            exit(-1)

        if not cmdline_args.status:
            print('Saving to %s' % destdir)
            #webify.logger.info('Saving to %s' % destdir)
        else:
            _, ignorelist, files = webify.filedb.get_stats()
            print('Ignorelist:')
            for (i,j) in ignorelist:
                print('\t (%s, %s)' % (i,j))
            print('Files:')
            for i in files.keys():
                print('\t %s: %s' % (i, files[i]))

        webify.setup_rendering_context()

        if cmdline_args.status:
            exit(0)

        webify.create_destination_folder()
        #webify.setup_cache()

        webify.load_yamlfiles()
        webify.load_templates()
        webify.compute_partials()
        webify.render_all_files()
        webify.write(force_save=cmdline_args.force_save)

        webify.logger.info('\nWebifying done.')
        exit(0)
