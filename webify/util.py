import logging
import codecs
import pprint
import os
import shutil

def copy_file(src, dest, force_save):
    """
    Copy src to dest

    Returns status:
        - None: failed
        - 1: copied
        - 2: skipped
    """
    if not force_save and os.path.exists(dest):
        s = os.stat(src)
        d = os.stat(dest)
        if s.st_size == d.st_size and s.st_mtime == d.st_mtime:
            return 2 # Skipped

    try:
        shutil.copy2(src, dest)
        return 1 # Copied
    except:
        pass
    return None # Failed

def move_file(src, dest, force_save):
    """
    Moves src to dest

    Returns status:
        - None: failed
        - 1: moved
        - 2: skipped
    """
    if not force_save and os._exists(dest):
        s = os.stat(src)
        d = os.stat(dest)
        if s.st_size == d.st_size and s.st_mtime == d.st_m_time:
            return 2 # Skipped

    try:
        shutil.move(src, dest)
        return 1 # Moved
    except:
        pass
    return None # Failed

def make_directory(dirpath):
    try:
        os.makedirs(dirpath)
    except OSError:
        if os.path.isdir(dirpath):
            return 'Found'
        else:
            return None
    return 'Created'

def debug_rendering_context(rc):
    print '\n>>>>>>>>>>> Rendering context'
    for p in rc.keys():
        print '\nKey:', p
        pprint.pprint(rc[p], indent=1)
    print '\n<<<<<<<<<<< rendering context.\n'


def get_logging_levels(dbglevel):
    if dbglevel == logging.WARNING:
        dbgfile = logging.INFO
        dbgconsole = logging.WARNING
    elif dbglevel == logging.INFO:
        dbgfile = logging.INFO
        dbgconsole = logging.INFO
    elif dbglevel == logging.DEBUG:
        dbgfile = logging.DEBUG
        dbgconsole = logging.DEBUG
    else:
        dbgfile = dbgconsole = dbglevel
    
    return dbgfile, dbgconsole    

def setup_logging(name,
                  dbglevel,
                  logfile='webify.log',
                  formatstr='[%(asctime)s] \t [%(name)s] \t [%(levelname)s] \t %(message)s'):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    dbgfile, dbgconsole = get_logging_levels(dbglevel)
    logger.setLevel(dbgfile)
    # print dbgfile, dbgconsole

    if dbgfile:
        formatter = logging.Formatter('[%(asctime)s] \t [%(name)s] \t [%(levelname)s] \t %(message)s')
        fh = logging.FileHandler(logfile)
        fh.setLevel(dbgfile)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    formatstr = '[%(levelname)s] - %(message)s'
    if dbgconsole <= logging.DEBUG:
        formatstr = '[%(name)s] - [%(levelname)s] - %(message)s'

    formatter = logging.Formatter(formatstr)
    ch = logging.StreamHandler()
    ch.setLevel(dbgconsole)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

def save_to_html(buffer, filepath, logger=None):
    try:
        with codecs.open(filepath, 'w') as stream:
            stream.write(buffer.encode('utf-8'))
        if logger:
            logger.info('Saved html file: %s' % filepath)
        else:
            print 'Saved html file:', filepath
    except:
        if logger:
            logger.error('Error saving file: %s' % filepath)
        else:
            print 'Error saving file:', filepath

def make_different_extension(filepath, new_extension):
    if new_extension[0] == '.':
        dot = ''
    else:
        dot = '.'
    return os.path.splitext(filepath)[0] + dot + new_extension

def srcs_newer_than_dest(srclist, dst):
    try:
        d = os.stat(dst)
        for src in srclist:
            if not is_valid_file(src):
                continue
            s = os.stat(src)
            if s.st_mtime > d.st_mtime: # Source was modified after destination
                return True
        return False
    except:
        pass
    return False

def is_valid_file(filepath):
    if not filepath:
        return False
    else:
        return os.path.isfile(filepath)

def make_rel_path(rootdir, basepath, filepath):
    """
    Typically used for file path processing for files specified within the yaml frontmatter
    in markdown files:

    Case 1:
    /paths/starting/with/a/slash are seen as absolute paths and are not changed.
    
    Case 2:
    {{root}}/paths/start/at/the/rootdir

    Case 3:
    paths/that/donot/start/with/a/slash start at the basepath

    In all three cases the returned path is relative to the basepath.  This routine
    is used to compute relative paths for css files.
    """    
    if not filepath:
        return filepath

    filepath = os.path.expandvars(filepath)

    if filepath[0] == '/':
        fp = filepath
    elif filepath[0:8] == '{{root}}':
        fp = filepath.replace('{{root}}', rootdir, 1)
        if fp[0:2] == '//': fp = fp[1:]
    else:
        fp = os.path.join(basepath, filepath)

    return os.path.relpath(fp, basepath)

def make_abs_path(rootdir, basepath, filepath):    
    """
    Typically used for file path processing for files specified within the yaml frontmatter
    in markdown files:

    Case 1:
    /paths/starting/with/a/slash are seen as absolute paths and are not changed.
    
    Case 2:
    {{root}}/paths/start/at/the/rootdir

    Case 3:
    paths/that/donot/start/with/a/slash start at the basepath

    In all three cases the returned path is the absolute path, which
    makes it easy to check for file existence, etc.
    """
    if not filepath:
        return filepath

    filepath = os.path.expandvars(filepath)
    
    if filepath[0] == '/':
        fp = filepath                                   
    elif filepath[0:8] == '{{root}}':
        fp = filepath.replace('{{root}}', rootdir, 1)
        if fp[0:2] == '//': fp = fp[1:]
    else:
        fp = os.path.join(basepath, filepath)
       
    return os.path.normpath(fp)

def ancestors(path):
    import os
    while True:
        if path == '.':
            break

        try:
            path = os.path.split(path)[0]
        except:
            break
        if path == '':
            path = '.'
        yield path
