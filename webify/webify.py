import argparse
import logging
import filedb as db
#from filedb import Filedb, get_files, get_directories, search, filepath
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

version = '1.7'

class Webify:
    def __init__(self, rootdir, destdir, debug_lvls, use_cache):
        self.time_now = datetime.datetime.now()
        self.rootdir = rootdir
        self.debug_lvls = debug_lvls
        self.ok = True
        self.use_cache = use_cache
        self.destdir = destdir
        #self.cachedb = None

        # Setting up main logger
        self.logger = util.setup_logging('Webify', dbglevel=self.debug_lvls['main'])
        self.logger.info('Webifying (version: %s) folder %s' % (version, self.rootdir))        
        if self.use_cache:
            self.logger.info('Using cache')        
        else:
            self.logger.info('Not using cache')

        # Collecting files
        self.filedb = db.Filedb(rootdir, dbglevel=debug_lvls['db'])
        self.filedb.collect()
        if self.filedb.get_size() == 0:
            self.ok = False
        
        # Setting up rendering context
        self.rendering_context = RenderingContext(rootdir, debug_lvls['rc'])

    def load_yamlfiles(self):
        self.logger.info('Loading YAML files')

        for d, _, r in db.get_directories(self.filedb):
            self.logger.debug('Directory: %s' % d)

            rc = {}
            for f, p in db.get_files(self.filedb, dirpath=r, fileext='.yaml'):
                self.logger.debug('Yaml file found: %s' % p)
                y = YAMLfile(p, dbglevel=self.debug_lvls['yaml'])
                y.load()
                rc[p] = y.get_data()
                f['handler'] = y

            # Adding webify internal context to the root    
            if r == '.':
                rc['__webify_internal__'] = {'auto-last-updated': self.time_now.strftime('%Y-%m-%d %H:%M')}
                
            self.rendering_context.add(r, rc)

        if self.debug_lvls['main'] == logging.DEBUG:
            print '---------------------------------------'
            print 'Rendering context after loading yaml files:'
            self.rendering_context.pprint()
            print '---------------------------------------'

    def load_templates(self):
        self.logger.info('Loading templates')

        for f, p in db.get_files(self.filedb, fileext='.mustache'):
            self.logger.debug('Mustache file found: %s' % p)
            m = mustachefile.Mustachefile(p, dbglevel=debug_lvls['mustache'])
            m.load()
            f['handler'] = m

    def render_html(self, buffer, rc):
        return mustachefile.mustache_render(buffer, rc, util.setup_logging('Mustachefile', dbglevel=debug_lvls['mustache']))

    def render_md(self, mdfile, html, templatefile, rc):
        if not templatefile:
            return html

        # print 'mdfile: ', mdfile
        # print 'templatefile: ', templatefile
        # print 'dirpath', mdfile['path']
        # print 'rootdir', self.rootdir
        filepath, filename = os.path.split(templatefile)

        if not filepath:
            filepath = mdfile['path']
        elif filepath[0] == '/':
            if len(filepath) == 1:
                filepath = '.'
            else:
                filepath = filepath[1:]
        else:
            os.path.join(mdfile['path'], filepath)
        #print 'filepath', filepath
        filename, fileext = os.path.splitext(filename)
        #print 'filename', filename
        #print 'fileext', fileext

        if not fileext == '.mustache':
            self.logger.warning('Cannot load template "%s" when rendering %s', templatefile, os.path.join(mdfile['path'], mdfile['name']+mdfile['ext']))
            return html 

        tf, p = db.search(self.filedb, filename=filename, dirpath=filepath, fileext=fileext)
        if tf:
            mustache_file = tf['handler']
            rc['body'] = html
            rendered_md = mustachefile.mustache_render(mustache_file.get_template(), rc, util.setup_logging('Mustachefile', dbglevel=debug_lvls['mustache']))
            rc['body'] = None
            return rendered_md
        else:
            self.logger.warning('Cannot load template "%s" when rendering %s', templatefile, os.path.join(mdfile['path'], mdfile['name']+mdfile['ext']))

        return html

    def compute_partials(self):
        self.logger.info('Computing partials')
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
            rc[f['name']+'_html'] = self.render_html(h.get_buffer(), rc)
            f['handler'] = h

        for f, p in db.get_files(self.filedb, dirpath='_partials', fileext='.md'):
            self.logger.info('MD file found in _partials %s' % p)
            md = MDfile(p, self.rootdir, dbglevel=self.debug_lvls['md'])
            md.load()
            format, buffer = md.convert(outputfile=None, use_cache=self.use_cache)
            if not format == 'html':
                self.logger.warning('Error converting file %s in _partials' % f)
                continue

            rc_changes = {}
            yaml_block = md.get_yaml()
            try:
                for k in yaml_block.keys():
                    if k in rc.keys():
                        rc_changes[k] = rc[k]
                    rc[k] = yaml_block[k]
            except:
                    pass
            rc[f['name'] + '_md'] = self.render_md(f, buffer, md.get_renderfile(), rc)
            
            for k in rc_changes.keys():
                rc[k] = rc_changes[k]

            #f['handler'] = md
            f['copy-to-destination'] = False # Because files in _partial are never copied over

        self.rendering_context.append('.', rc)

        if self.logger.getEffectiveLevel() == logging.DEBUG:
            util.debug_rendering_context(self.rendering_context.context)

    def render_all_files(self):
        self.logger.info('Rendering all files')

        for d, _, r in db.get_directories(self.filedb):
            a = [r]
            a[1:] = util.ancestors(r)
            c = [i for i in a if i in ['_partials', '_templates']]
            if len(c) > 0:
                continue

            # rc = self.rendering_context.get(r)

            # if self.debug_lvls['rc'] == logging.DEBUG:
            #     print '\n-------------------------------------------------'
            #     print 'render_all_files()'
            #     print 'Directory: ', d, r
            #     util.debug_rendering_context(rc)
            #     print '\n-------------------------------------------------'

            for f, p in db.get_files(self.filedb, dirpath=r, fileext=['.md', '.html']):
                self.logger.info('Rendering file: %s' % p)

                if self.debug_lvls['rc'] == logging.DEBUG:
                    print '\n-------------------------------------------------'
                    print 'f', f
                    print 'p', p
                    print 'r', r
                rc = self.rendering_context.get(r)
                if self.debug_lvls['rc'] == logging.DEBUG:
                    print '\nFolder specific rc:'
                    print rc

                if f['ext'] == '.html':
                    h = HTMLfile(p)
                    h.load()
                    f['__rendered__'] = self.render_html(h.get_buffer(), rc)
                    continue

                outputfile = os.path.normpath(os.path.join(self.destdir, f['path'], f['name']))

                if f['ext'] == '.md':
                    md = MDfile(filepath=p, rootdir=self.rootdir, dbglevel=self.debug_lvls['md'])
                    md.load()
                    format, buffer = md.convert(outputfile=outputfile, use_cache=self.use_cache)

                    rc_changes = {}
                    if format == 'html':
                        yaml_block = md.get_yaml()
                        try:
                            for k in yaml_block.keys():
                                if k in rc.keys():
                                    rc_changes[k] = rc[k]
                                rc[k] = yaml_block[k]
                        except:
                            pass

                        if self.debug_lvls['rc'] == logging.DEBUG:
                            print '\nFile specific rc:'
                            print rc
                            print '-------------------------------------------------'

                        f['__rendered__'] = self.render_md(f, buffer, md.get_renderfile(), rc)

                        for k in rc_changes.keys():
                            rc[k] = rc_changes[k]

                    elif format == 'file':
                        f['__generated_file__'] = buffer
                    else:
                        self.logger.warning('Pandoc conversion failed: %s' % p)
                    f['copy-to-destination'] = md.get_copy_to_destination()

    def create_destination_folder(self):
        dd = os.path.abspath(self.destdir)
        self.logger.info('Creating destination: %s' % dd)

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
            self.logger.debug('Creating directory: %s' % dirpath)
            dir_creation = util.make_directory(dirpath)
            if not dir_creation:
                self.logger.error('Error creating directory: %s.  Ignoring its contents.' % dirpath)
                continue
            else:
                self.logger.debug('%s %s' % (dirpath, dir_creation))            

    # def setup_cache(self):
    #     if self.use_cache:
    #         self.logger.info('Setting up cache')
    #         self.cachedb = db.Filedb(self.destdir, dbglevel=debug_lvls['db'])
    #         self.cachedb.collect()


    def write(self, force_save):
        dd = os.path.abspath(self.destdir)
        self.logger.info('Writing to destination: %s' % dd)

        # If we don't have a desitnation directory, we are in trouble
        # Since we create the destination folder structure right in the beginning
        assert os.path.isdir(dd)

        # dir_creation = util.make_directory(dd)
        # if not dir_creation:
        #     self.logger.error('Cannot make destination directory.  Nothing more to do.  Aborting.')
        #     exit(-1)
        # else:
        #     self.logger.debug('%s %s' % (dd, dir_creation))

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

            # self.logger.info('Directory: %s' % dirpath)
            # dir_creation = util.make_directory(dirpath)
            # if not dir_creation:
            #     self.logger.error('Error creating directory: %s.  Ignoring its contents.' % dirpath)
            #     continue
            # else:
            #     self.logger.debug('%s %s' % (dirpath, dir_creation))            

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
                            with codecs.open(filepath, 'w') as stream:
                                stream.write(f['__rendered__'].encode('utf-8'))
                        except:
                            self.logger.warning('Failed saving rendered content to html file: %s' % filepath)

                    elif '__generated_file__' in f.keys():
                        # The generated file is already copied to the destination
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

        self.logger.info('Webifying completed.')


# class EventHandler(pyinotify.ProcessEvent):
#     def process_IN_CREATE(self, event):
#         print "Creating:", event.pathname
#
#     def process_IN_DELETE(self, event):
#         print "Removing:", event.pathname


from watchdog.events import FileSystemEventHandler
class FileChanges(FileSystemEventHandler):
    def __init__(self):
        pass

    def on_any_event(self, event):
        print event

if __name__ == '__main__':
    cmdline_parser = argparse.ArgumentParser()
    cmdline_parser.add_argument('rootdir', help='Root directory')
    cmdline_parser.add_argument('destdir', help='Destination directory')
    cmdline_parser.add_argument('--monitor', action='store_true', default=False, help='Monitor root folder for changes')
    cmdline_parser.add_argument('--force-save', action='store_true', default=False, help='Force saving to destination')
    cmdline_parser.add_argument('--ver', action='store_true', default=False, help='Print version and exit')
    cmdline_parser.add_argument('--status', action='store_true', default=False, help='Prints helpful information about the folder that you plan to webify')
    cmdline_parser.add_argument('--no-cache', action='store_true', default=False, help='Turn off cache usage')

    # Logging and verbosity
    cmdline_parser.add_argument('--debug', action='store_true', default=False, help='Log debugging messages (global, use with caution)')
    cmdline_parser.add_argument('--verbose', action='store_true', default=False, help='More verbose')
    cmdline_parser.add_argument('--debug-md', action='store_true', default=False, help='Debug logger for MD files.')
    cmdline_parser.add_argument('--debug-yaml', action='store_true', default=False, help='Debug logger for Yaml files.')
    cmdline_parser.add_argument('--debug-rc', action='store_true', default=False, help='Debug logger for RC files.')
    cmdline_parser.add_argument('--debug-db', action='store_true', default=False, help='Debug logger for Filedb files.')
    cmdline_parser.add_argument('--debug-mustache', action='store_true', default=False, help='Debug logger for Mustachefile files.')

    # Parsing commandline arguments
    cmdline_args = cmdline_parser.parse_args()

    # Just checking version
    if cmdline_args.ver:
        print 'Webify version %s' % version
        exit(0)

    # Logging and verbosity
    debug_lvls = { 'main': logging.WARNING, 'md': logging.WARNING, 'yaml': logging.WARNING, 'rc': logging.WARNING, 'db': logging.WARNING, 'mustache': logging.WARNING }

    if cmdline_args.verbose:
        for k in debug_lvls.keys():
            debug_lvls[k] = logging.INFO

    if cmdline_args.debug:
        for k in debug_lvls.keys():
            debug_lvls[k] = logging.DEBUG

    # And now selective logging
    if cmdline_args.debug_md:
        debug_lvls['md'] = logging.DEBUG
    if cmdline_args.debug_yaml:
        debug_lvls['yaml'] = logging.DEBUG
    if cmdline_args.debug_rc:
        debug_lvls['rc'] = logging.DEBUG
    if cmdline_args.debug_db:
        debug_lvls['db'] = logging.DEBUG
    if cmdline_args.debug_mustache:
        debug_lvls['mustache'] = logging.DEBUG

    # The following is not yet implemented
    if cmdline_args.monitor:
        print 'Feature not implemented.'
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
        if cmdline_args.status:
            print('Webify version: %s' % version)
            print('Webifying %s' % cmdline_args.rootdir)

        rootdir = os.path.realpath(cmdline_args.rootdir)
        destdir = os.path.realpath(cmdline_args.destdir)

        webify = Webify(rootdir=rootdir, destdir=destdir, debug_lvls=debug_lvls, use_cache=not cmdline_args.no_cache)

        # Get some statistics from the webify folder
        if cmdline_args.status:
            _, ignorelist, files = webify.filedb.get_stats()
            print('Ignorelist:')
            for (i,j) in ignorelist:
                print('\t (%s, %s)' % (i,j)) 
            print('Files:')
            for i in files.keys():
                print('\t %s: %s' % (i, files[i]))

        # Exit if only checking status or if webify encountered
        # an error.  This error typically is the result of
        # specify an invalid (say non-existent) folder to webify.
        if not webify.ok or cmdline_args.status:
            print 'Error.  Cannot webify %s' % cmdline_args.rootdir
            exit(-1)

        webify.create_destination_folder()
        #webify.setup_cache()

        webify.load_yamlfiles()
        webify.load_templates()
        webify.compute_partials()
        webify.render_all_files()
        webify.write(force_save=cmdline_args.force_save)
        exit(0)
