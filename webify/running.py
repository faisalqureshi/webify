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
            ch = input('Enter choice: ')
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
        print('X')
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

class WebifyLive:
    def __init__(self, webify, upload_shell_script):
        self.logger = util.WebifyLogger.get('webify-live')

        self.webify = webify        

        if webify.get_next_run_offset() > 0:
            self.next_run = threading.Timer(webify.get_next_run_offset()+60, self.run_webify)
            self.next_run.start()
        else:
            self.next_run = None

        util.WebifyLogger.get('browser').debug('Setting live view browser')
        browser_controller = browser.BrowserController()

        util.WebifyLogger.get('upload').debug('Setting upload shell script')
        uploader = upload.UploadScript(shell_script=upload_shell_script)

        util.WebifyLogger.get('watchdir').debug('Setting directory watch')
        dir_changes_event_handler = DirChangeHandler(webify=webify, browser_controller=browser_controller, uploader=uploader)

        dir_observer = Observer()
        dir_observer.schedule(dir_changes_event_handler, webify.get_src(), recursive=True)
        dir_observer.start()

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

        if self.next_run: 
            self.next_run.cancel()
        dir_observer.join()
        kl_thread.join()

    def run_webify(self):
        print('foo')
        with lock:
            self.logger.critical('Timed auto compilation')
            self.webify.meta_data['__ignore_times__'] = False
            self.webify.meta_data['__force_copy__'] = False
            self.webify.traverse()

if __name__ == '__main__':
    pass