from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from pynput.keyboard import Key, Listener, KeyCode
import util2 as util
import sys
import time
from webify2 import Webify
import threading

lock = threading.Lock()

# class KeyboardListener(Listener):
#     def __init__(self, dir_observer, webify):
#         super().__init__(on_press=self.on_press, on_release=self.on_release)
#         self.logger = util.WebifyLogger.get('keyboard')
#         self.dir_observer = dir_observer
#         self.webify = webify
#         self.alive = True

#     def on_press(self, key):
#         self.logger.debug('{0} pressed'.format(key))

#     def on_release(self, key):
#         self.logger.debug('{0} released'.format(key))
#         if key == Key.esc or key == KeyCode.from_char('q') or key == KeyCode.from_char('Q'):
#             self.dir_observer.stop()
#             self.alive = False
#             return False
#         elif key == KeyCode.from_char('h') or key == KeyCode.from_char('H'):
#             return self.press_h()
#         elif key == KeyCode.from_char('r') or key == KeyCode.from_char('R'):
#             return self.press_r()
#         elif key == KeyCode.from_char('i') or key == KeyCode.from_char('I'):
#             return self.press_i()
#         elif key == KeyCode.from_char('c') or key == KeyCode.from_char('C'):
#             return self.press_c()
#         elif key == KeyCode.from_char('a') or key == KeyCode.from_char('A'):
#             return self.press_a()
#         else:
#             return True

#     def press_r(self):
#         self.logger.critical('Recompiling')
#         self.webify.meta_data['__ignore_times__'] = False
#         self.webify.meta_data['__force_copy__'] = False
#         self.webify.traverse()
#         return True

#     def press_i(self):
#         self.logger.critical('Recompiling (ignoring times)')
#         self.webify.meta_data['__ignore_times__'] = True
#         self.webify.meta_data['__force_copy__'] = False
#         self.webify.traverse()
#         return True

#     def press_a(self):
#         self.logger.critical('Recompiling (ignoring times)')
#         self.webify.meta_data['__ignore_times__'] = True
#         self.webify.meta_data['__force_copy__'] = True
#         self.webify.traverse()
#         return True

#     def press_h(self):
#         print('Keyboard shortcuts:')
#         print("- 'h': print this message")
#         print("- 'r': run webify")
#         print("- 'esc': quit")
#         print("- 'q': quit")
#         print("- 'c': webify (force file copying)")
#         print("- 'i': webify (force compilation)")
#         print("- 'a': webify (force compilation and file copying)")
#         return True

class KeyboardListener:
    def __init__(self, dir_observer, webify):
        self.logger = util.WebifyLogger.get('keyboard')
        self.dir_observer = dir_observer
        self.webify = webify
        self.alive = True

    def handler(self):
        while self.alive:
            time.sleep(0.2)
            ch = input('')
            if ch.upper() == 'Q':
                self.quit()
            elif ch.upper() == 'R':
                self.press_r()
            elif ch.upper() == 'I':
                self.press_i()
            elif ch.upper() == 'A':
                self.press_a()
            elif ch.upper() == 'C':
                self.press_c()
            elif ch.upper() == 'H':
                self.help()
            else:
                self.logger.critical("Unrecognized command.  Enter 'h' to see list of available commands.")

    def quit(self):
        self.alive = False
        self.dir_observer.stop()
        return False

    def press_r(self):
        with lock:
            self.logger.critical('Recompiling')
            self.webify.meta_data['__ignore_times__'] = False
            self.webify.meta_data['__force_copy__'] = False
            self.webify.traverse()
        return True

    def press_i(self):
        with lock:
            self.logger.critical('Recompiling (ignoring times)')
            self.webify.meta_data['__ignore_times__'] = True
            self.webify.meta_data['__force_copy__'] = False
            self.webify.traverse()
        return True

    def press_c(self):
        with lock:
            self.logger.critical('Recompiling (copying misc files)')
            self.webify.meta_data['__ignore_times__'] = False
            self.webify.meta_data['__force_copy__'] = True
            self.webify.traverse()
        return True

    def press_a(self):
        with lock:
            self.logger.critical('Recompiling (ignoring times & copying misc files)')
            self.webify.meta_data['__ignore_times__'] = True
            self.webify.meta_data['__force_copy__'] = True
            self.webify.traverse()
        return True

    def help(self):
        print('Keyboard shortcuts:')
        print("- 'h': print this message")
        print("- 'q': quit")
        print("- 'r': run webify")
        print("- 'c': webify (force file copying)")
        print("- 'i': webify (force compilation)")
        print("- 'a': webify (force compilation and file copying)")
        return True

class DirChangeHandler(FileSystemEventHandler):
    def __init__(self, webify):
        super().__init__()
        self.logger = util.WebifyLogger.get('watchdir')
        self.webify = webify
        self.last_time = time.time()
        self.time_resolution = 1 # second

    def on_moved(self, event):
        super(DirChangeHandler, self).on_moved(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Moved %s: from %s to %s' % (what, event.src_path,
                     event.dest_path))

    def on_created(self, event):
        super(DirChangeHandler, self).on_created(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Created %s: %s' % (what, event.src_path))

    def on_deleted(self, event):
        super(DirChangeHandler, self).on_deleted(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Deleted %s: %s' % (what, event.src_path))

    def on_modified(self, event):
        super(DirChangeHandler, self).on_modified(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Modified %s: %s' % (what, event.src_path))

        with lock:
            if time.time() - self.last_time > self.time_resolution:
                self.logger.critical('Recompiling')
                self.webify.meta_data['__ignore_times__'] = False
                self.webify.meta_data['__force_copy__'] = False
                self.webify.traverse()
                self.last_time = time.time()

def go(webify):
    path = webify.srcdir if webify else '.'

    dir_changes_event_handler = DirChangeHandler(webify=webify)

    dir_observer = Observer()
    dir_observer.schedule(dir_changes_event_handler, path, recursive=True)
    dir_observer.start()

    # keyboard_listener = KeyboardListener(dir_observer, webify=webify)
    # keyboard_listener.start()

    kl = KeyboardListener(dir_observer, webify=webify)
    kl_thread = threading.Thread(target=kl.handler)
    kl_thread.start()

    try:
        while kl.alive:
            time.sleep(1)
    except KeyboardInterrupt:
        dir_observer.stop()
        kl_thread.stop()
    dir_observer.join()
    kl_thread.join()

if __name__ == '__main__':
    go(None)