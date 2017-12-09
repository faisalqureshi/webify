import os
import argparse
import logging
import codecs
import fnmatch
import time
import util


def filepath(fileitem):
    print os.path.join(fileitem['path'],fileitem['name'] + fileitem['ext'])

    return os.path.join(fileitem['path'],fileitem['name'] + fileitem['ext'])

def get_directories(filedb, dirpath=None):
    filter = None
    if dirpath:
        filter = {'path': dirpath}

    for i in filedb.files:
        if Filedb.match_diritem(i, filter=filter):
            yield i, filedb.get_full_dirpath(i), Filedb.get_rel_dirpath(i)


def get_files(filedb, dirpath=None, filename=None, fileext=None):
    if fileext and not isinstance(fileext, list):
        fileext = [ fileext ]

    filter = None
    if dirpath or filename or fileext:
        filter = {'path': dirpath, 'name': filename, 'ext': fileext}

    for i in filedb.files:
        if Filedb.match_fileitem(i, filter=filter):
            yield i, filedb.get_full_filepath(i)


def search(filedb, dirpath=None, filename=None, fileext=None, isfile=True):
    if isfile:
        for f, p in get_files(filedb, dirpath, filename, fileext):
            return f, p
        return None, None

    assert not fileext
    for d in get_directories(filedb, dirpath):
        return d
    return None


class Filedb:
    """
    Class that maintains files and folders that need to be processed by webify.

    Each file item is stored as a dictionary:
        [{'path': '.', 'idx': idx, 'type': 'dir', 'name': '.'}]

    Subsequent processing can 
    """


    def __init__(self, rootdir, dbglevel, ignorefile='.webifyignore'):
        self.logger = util.setup_logging('Filedb', dbglevel=dbglevel)
        self.rootdir = os.path.realpath(rootdir)
        # print 'rootdir', self.rootdir

        self.ignorelist = self.setup_ignore_list(ignorefile)

        if self.logger.getEffectiveLevel() <= logging.DEBUG:
            for i in self.ignorelist:
                self.logger.debug('%s, %s' % (i[0], i[1]))
        #self.ignorelist.append('.tmp') # default output folder
        self.files = []

    def get_stats(self):
        num_files = {'.mustache': 0, '.md': 0, '.html': 0, '.yaml': 0, 'other': 0, 'total': 0}

        for f, _ in get_files(self):
            num_files['total'] += 1
            if f['ext'] in ['.mustache', '.md', '.html', '.yaml']:
                num_files[f['ext']] += 1
            else:
                num_files['other'] += 1

        return self.rootdir, self.ignorelist, num_files

    def get_rootdir(self):
        return self.rootdir

    def get_full_dirpath(self, diritem):
        return os.path.normpath(os.path.join(self.rootdir, diritem['path'], diritem['name']))

    @staticmethod
    def get_rel_dirpath(diritem):
        return os.path.normpath(os.path.join(diritem['path'], diritem['name']))

    def get_full_filepath(self, fileitem):
        return os.path.normpath(os.path.join(self.rootdir, fileitem['path'], fileitem['name']+fileitem['ext']))

    @staticmethod
    def get_rel_filepath(filepath):
        return os.path.normpath(os.path.join(fileitem['path'], fileitem['name']+fileitem['ext']))

    @staticmethod
    def match_diritem(diritem, filter):
        if diritem['type'] != 'dir':
            return False

        if not filter:
            return True

        if filter['path'] and diritem['path'] != filter['path']:
            return False

        return True


    @staticmethod
    def match_fileitem(fileitem, filter):
        if fileitem['type'] != 'file':
            return False

        if not filter:
            return True

        if filter['path'] and filter['path'] != fileitem['path']:
            return False

        if filter['name'] and filter['name'] != fileitem['name']:
            return False

        if filter['ext'] and not fileitem['ext'] in filter['ext']:
            return False

        return True

    def setup_ignore_list(self, ignorefile):
        self.logger.debug('setup_ignore_list')
        try:
            ignorelist = [(''.decode('utf-8'),'.webify_cache'.decode('utf-8'))]
            with codecs.open(os.path.join(self.rootdir, ignorefile), 'r') as stream:
                tmp = stream.readlines()
                for i in range(len(tmp)):
                    tmp[i] = tmp[i].decode('utf-8').strip()
                    self.logger.debug('%d, %s' % (i, tmp[i]))
                    x, y = os.path.split(tmp[i])
                    self.logger.debug('%s, %s' % (x,y))
                    ignorelist.append((x, y))
            self.logger.info('Read ignorefile: %s' % ignorefile)
            return ignorelist
        except:
            self.logger.warning('Cannot read ignorefile: %s' % ignorefile)
            return ignorelist

    def in_ignore_list(self, path, file):
        for i in self.ignorelist:
            self.logger.debug('in_ignore_list() - %s,%s == %s,%s' % (i[0], i[1], path, file))

            if len(i[0]) == 0 and fnmatch.fnmatch(file, i[1]):
                self.logger.debug('in_ignore_list() - file matched')
                return True
            elif len(i[0]) > 0 and fnmatch.fnmatch(path, i[0]) and fnmatch.fnmatch(file, i[1]):
                self.logger.debug('in_ignore_list() - path and file matched')
                return True
            else:
                self.logger.debug('in_ignore_list() - pass')
                pass

        return False

    def get_size(self):
        return len(self.files)

    def collect(self):
        """
        A special directory '.webify_cache' is ignored.
        """
        if not os.path.isdir(self.rootdir):
            self.logger.error('Cannot find directory: %s', self.rootdir)
            return False

        self.logger.info('Collecting files in %s' % self.rootdir)
        ignore_paths = []

        idx = 0
        self.files = [{'path': '.', 'idx': idx, 'type': 'dir', 'name': '.'}]
        for path, directories, files in os.walk(self.rootdir):
            self.logger.debug('collect() - path: %s' % path)

            idx += 1
            relpath = os.path.relpath(path, self.rootdir)
            self.logger.debug('collect() - relpath: %s' % relpath)

            for file in files:
                self.logger.debug('collect(), file - %s, %s' % (relpath, file))
                filepath = os.path.join(relpath, file)

                if relpath in ignore_paths:
                    self.logger.debug('Found in ignore_paths.')
                    self.logger.info('Ignoring file: %s' % filepath)
                    continue

                if self.in_ignore_list(relpath, file):
                    self.logger.debug('Found in ignore list.')
                    self.logger.info('Ignoring file: %s' % filepath)
                    continue

                try:
                    mtime = None
                    mtime = time.ctime(os.path.getmtime(os.path.join(self.rootdir,filepath)))
                except:
                    self.logger.warning('Can not get modification time for %s' % filepath)

                name, ext = os.path.splitext(file)
                fileitem = {'idx': idx, 'type': 'file', 'path': relpath, 'name': name, 'ext': ext, 'mtime': mtime}
                self.files.append(fileitem)
                self.logger.debug('Adding file: %s' % filepath)

            for directory in directories:
                self.logger.debug('collect(), directory - %s, %s' % (relpath, directory))
                dirpath = os.path.join(relpath, directory)

                if relpath in ignore_paths or self.in_ignore_list(relpath, directory):
                    self.logger.info('Ignoring directory: %s' % dirpath)
                    self.logger.debug('Adding %s to ignore_paths' % os.path.normpath(dirpath))
                    ignore_paths.append(os.path.normpath(dirpath))
                    continue

                self.files.append({'idx': idx, 'path': relpath, 'type': 'dir', 'name': directory})
                self.logger.debug('Adding directory: %s' % dirpath)



                # if path in ignore_paths:
                #     self.logger.debug('Ignoring directory: %s' % dirpath)
                #     ignore_paths.append(os.path.join(self.rootdir, dirpath))
                #     continue
                #
                # if not self.in_ignore_list(dirpath, None):
                #     self.files.append({'idx': idx, 'path': dirpath, 'type': 'dir'})
                #     self.logger.debug('Adding directory: %s' % dirpath)
                # else:
                #     self.logger.debug('Ignoring directory: %s' % dirpath)
                #     ignore_paths.append(os.path.join(self.rootdir, dirpath))

        if self.logger.getEffectiveLevel() <= logging.DEBUG:
            print '[DEBUG] - files:'
            for i in self.files:
                print i

    def pprint(self):
        print 'Rootdir:', self.rootdir
        print '\nIgnore list:'
        for i in self.ignorelist:
            print i
        print '\nTotal:', len(self.files)
        for i in self.files:
            print i

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('rootdir', help='Root directory.')
    parser.add_argument('-d','--debug', action='store_true', default=False, help='Log debugging messages')
    args = parser.parse_args()

    dbglevel = logging.INFO
    if args.debug:
        dbglevel = logging.DEBUG

    filedb = Filedb(args.rootdir, dbglevel=dbglevel)
    filedb.collect()

    print '\nAll items:'
    for f, p in get_files(filedb):
        print f
        print p, '\n'

    print '\nAll directories'
    for d, p, r in get_directories(filedb):
        print d
        print r, '\n'
        print p, '\n'

    #
    # print '\nOnly yaml files in _partials:'
    # for fileitem in get_files(filedb, dirpath='_partials', fileext='.yaml'):
    #     print fileitem
    #
    # print '\nOnly _partials directory:'
    # for diritem in get_directories(filedb, dirpath='_partials'):
    #     print diritem
    #
    # print '\n-------------------------------------'
    # filedb.pprint()