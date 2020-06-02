from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import sys
from pynput.keyboard import Key, Listener, KeyCode
import pynput
import datetime

class KeyboardListener(pynput.keyboard.Listener):
    def __init__(self, observer, event_handler):
        super().__init__(on_press=self.on_press, on_release=self.on_release)
        self.observer = observer
        self.alive = True
        self.event_handler = event_handler

    def on_press(self, key):
        print('{0} pressed'.format(key))

    def on_release(self, key):
        print('{0} release'.format(key))
        if key == Key.esc:
            self.observer.stop()
            self.alive = False
            return False
        elif key == KeyCode.from_char('a'):
            print('XX')
            return True
        else:
            return True

class RunWebify(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        #self.last_build = datetime.now().time()

    def on_moved(self, event):
        super(RunWebify, self).on_moved(event)
        what = 'directory' if event.is_directory else 'file'
        print("Moved %s: from %s to %s", what, event.src_path, event.dest_path)

    def on_created(self, event):
        super(RunWebify, self).on_created(event)
        what = 'directory' if event.is_directory else 'file'
        print("Created %s: %s", what, event.src_path)

    def on_deleted(self, event):
        super(RunWebify, self).on_deleted(event)
        what = 'directory' if event.is_directory else 'file'
        print("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event):
        # super(RunWebify, self).on_modified(event)
        what = 'directory' if event.is_directory else 'file'
        print("Modified %s: %s" % (what, event.src_path))

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = RunWebify()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    
    listener = KeyboardListener(observer, event_handler)
    listener.start()

    try:
        while listener.alive:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        listener.stop()
    observer.join()
    listener.join()