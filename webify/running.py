from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from pynput.keyboard import Key, Listener, KeyCode
import util2 as util
import sys
import time
from webify2 import Webify
import threading
import webbrowser
import browser
import upload

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
#             return self.`press_`h()
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
#         self.logger.critical('compiling')
#         self.webify.meta_data['__ignore_times__'] = False
#         self.webify.meta_data['__force_copy__'] = False
#         self.webify.traverse()
#         return True

#     def press_i(self):
#         self.logger.critical('compiling (ignoring times)')
#         self.webify.meta_data['__ignore_times__'] = True
#         self.webify.meta_data['__force_copy__'] = False
#         self.webify.traverse()
#         return True

#     def press_a(self):
#         self.logger.critical('compiling (ignoring times)')
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

# class UploadScript:
#     def __init__(self, shell_script):
#         self.logger = util.WebifyLogger.get('upload')
#         self.shell_script = shell_script

#     def run(self):
#         if self.shell_script == None:
#             self.logger.info('No upload shell script specified.')
#             return

#         try:
#             self.logger.info('Running upload shell script: %s' % self.shell_script)
#             x = subprocess.run([self.shell_script])
#             x.check_returncode()           
#         except subprocess.CalledProcessError as e:
#             self.logger.warning('Upload shell script failed: %s (%s)' % (self.shell_script, e))
#         except:
#             self.logger.warning('Upload shell script failed: %s' % (self.shell_script))

# class BrowserController:
#     def __init__(self, browser_name):
#         self.logger = util.WebifyLogger.get('browser')
        
#         self.browser_name = browser_name
#         self.browser = None
#         self.enabled = False
#         self.url = None

#         if self.browser_name == None:
#             self.logger.info('No live browser specified')
#             return

#         self.browser = self.check_if_available(self.browser_name, self.logger)
#         self.enabled = True if self.browser else False

#     @staticmethod
#     def check_if_available(browser_name, logger):
#         browser = None
#         try:
#             browser = webbrowser.get(browser_name)
#             logger.info('Using live browser: %s' % browser_name)
#             if not browser:
#                 raise ValueError
#         except webbrowser.Error as err:
#             logger.warning('Cannot create live browser: %s (%s)' % (browser_name, err))            
#         except ValueError as err:
#             logger.warning('Cannot create live browser: %s (%s)' % (browser_name, err))
#         return browser

#     def enable(self):
#         if not self.browser:
#             self.logger.warning('No live browser avaialable.  Cannot enable live viewing')
#             return
#         self.enabled = True

#     def disable(self):
#         self.enabled = False

#     def toggle(self):
#         if not self.browser:
#             self.logger.warning('No live browser avaialable.  Cannot enable live viewing')
#             return
#         self.enabled = not self.enabled
#         self.logger.critical('Browser referesh turned %s' % ('on' if self.enabled else 'off'))

#     def set_url(self, url):
#         if not self.browser:
#             self.logger.warning('No live browser avaialable.  Cannot enable live viewing')
#             return

#         self.url = url
#         self.logger.critical('Watching %s' % url)

#     def refresh(self):
#         if self.enabled and self.browser:
#             if self.url:
#                 try:
#                     self.browser.open(self.url, new=0, autoraise=False)
#                     self.logger.debug('Success opening url %s' % self.url)
#                 except:
#                     self.logger.warning('Cannot open url %s' % self.url)
#             else:
#                 self.logger.warning('Cannot refresh browser.  No url specified.')
#         else:
#             self.logger.debug('Live browser: enabled=%s, browser=%s' % (self.enabled, self.browser))

class KeyboardListener:
    def __init__(self, dir_observer, webify, browser_controller, uploader):
        self.logger = util.WebifyLogger.get('keyboard')
        self.dir_observer = dir_observer
        self.webify = webify
        self.alive = True
        self.browser_controller = browser_controller
        self.uploader = uploader

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
            elif ch.upper() == 'W':
                self.press_w()
            elif ch.upper() == 'B':
                self.press_b()
            elif ch.upper() == 'U':
                self.press_u()
            else:
                self.logger.critical("Unrecognized command.  Enter 'h' to see list of available commands.")

    def quit(self):
        self.alive = False
        self.dir_observer.stop()
        return False

    def press_u(self):
        self.logger.debug('running uploader script, waiting for lock')
        with lock:
            self.uploader.run()
        self.logger.debug('finished running uploader script, released lock')

    def press_w(self):
        self.logger.debug('getting url from user, waiting for lock')
        with lock:
            url = input('Enter URL to watch: http://')
            self.browser_controller.set_url('http://'+url)
        self.logger.debug('finished getting url from user, released lock')
        return True

    def press_r(self):
        self.logger.debug('compiling, waiting for lock')
        with lock:
            self.logger.critical('compiling')
            self.webify.meta_data['__ignore_times__'] = False
            self.webify.meta_data['__force_copy__'] = False
            self.webify.traverse()
        self.logger.debug('finished compiling, released lock')
        return True

    def press_i(self):
        self.logger.debug('compiling ignoring times, waiting for lock')
        with lock:
            self.logger.critical('compiling (ignoring times)')
            self.webify.meta_data['__ignore_times__'] = True
            self.webify.meta_data['__force_copy__'] = False
            self.webify.traverse()
        self.logger.debug('finished compiling, released lock')
        return True

    def press_c(self):
        self.logger.debug('compiling with force copy, waiting for lock')
        with lock:
            self.logger.critical('compiling (copying misc files)')
            self.webify.meta_data['__ignore_times__'] = False
            self.webify.meta_data['__force_copy__'] = True
            self.webify.traverse()
        self.logger.debug('finished compiling, released lock')
        return True

    def press_b(self):
        self.logger.debug('toggling browser live view, waiting for lock')
        with lock:
            self.browser_controller.toggle()
        self.logger.debug('finished toggling browser live view, released lock')

    def press_a(self):
        self.logger.debug('compiling all, waiting for lock')
        with lock:
            self.logger.critical('compiling (ignoring times & copying misc files)')
            self.webify.meta_data['__ignore_times__'] = True
            self.webify.meta_data['__force_copy__'] = True
            self.webify.traverse()
        self.logger.debug('finished compiling, released lock')
        return True

    def help(self):
        print('Keyboard shortcuts:')
        print("- 'h': print this message")
        print("- 'q': quit")
        print("- 'r': run webify")
        print("- 'c': webify (force file copying)")
        print("- 'i': webify (force compilation)")
        print("- 'a': webify (force compilation and file copying)")
        print("- 'w': enter url to watch (useful for live updates)")
        print("- 'b': toggle browser refresh")
        print("- 'u': run upload shell script")
        return True

class DirChangeHandler(FileSystemEventHandler):
    def __init__(self, webify, browser_controller, uploader):
        super().__init__()
        self.logger = util.WebifyLogger.get('watchdir')
        self.webify = webify
        self.last_time = time.time()
        self.time_resolution = 5 # second
        self.browser_controller = browser_controller
        self.uploader = uploader

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

        if time.time() - self.last_time > self.time_resolution:
            self.logger.debug('starting reompiling, waiting for lock')
            with lock:
                self.logger.critical('Compiling')
                self.webify.meta_data['__ignore_times__'] = False
                self.webify.meta_data['__force_copy__'] = False
                self.webify.traverse()
                self.last_time = time.time()
                self.browser_controller.refresh()
            self.logger.debug('finished compiling, released lock')

def go(webify, upload_shell_script):
    util.WebifyLogger.get('browser').debug('Setting live view browser')
    browser_controller = browser.BrowserController()

    util.WebifyLogger.get('upload').debug('Setting upload shell script')
    uploader = upload.UploadScript(shell_script=upload_shell_script)

    util.WebifyLogger.get('watchdir').debug('Setting directory watch')
    dir_changes_event_handler = DirChangeHandler(webify=webify, browser_controller=browser_controller, uploader=uploader)

    dir_observer = Observer()
    dir_observer.schedule(dir_changes_event_handler, webify.get_src(), recursive=True)
    dir_observer.start()

    # keyboard_listener = KeyboardListener(dir_observer, webify=webify)
    # keyboard_listener.start()

    util.WebifyLogger.get('keyboard').debug('Setting up keyboard handler')
    kl = KeyboardListener(dir_observer, webify=webify, browser_controller=browser_controller, uploader=uploader)
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
    pass