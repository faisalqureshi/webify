import os
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, PatternMatchingEventHandler
from watchdog.events import FileModifiedEvent
import time
import datetime

# Acknowledgements: https://github.com/dloureiro/pandoc-watch/blob/master/pandocwatch.py

class Singleton:
    def __init__(self, decorated):
        self._decorated = decorated

    def Instance(self):
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `Instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

@Singleton
class Configuration:
    def __init__(self):
        pass

    def prn(self):
        print 'foo'

def get_now():
    return datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        
def which(program):
    """
    This function is taken from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python.
    """
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

class CheckFileChanges(PatternMatchingEventHandler):
    def __init__(self):
        super(CheckFileChanges, self).__init__(patterns=["*/webify.log","*/yamlfile.py"])
    
    def on_modified(self, event):
        print event
        

if __name__ == '__main__':
    print which("ls")


    c = Configuration.Instance()
    c.prn()
    print get_now()

    event_handler = CheckFileChanges()
    observer = Observer()
    observer.schedule(event_handler, os.getcwd(), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt as err:
        print str(err)
        observer.stop()
        

