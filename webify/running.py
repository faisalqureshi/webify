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
import datetime
import os

lock = threading.Lock()

class KeyboardListener:
    def __init__(self, dir_observer, run_webify, browser_controller, uploader, url_prefix):
        self.logger = util.WebifyLogger.get('keyboard')
        self.logger.debug('Setting up keyboard handler')

        self.dir_observer = dir_observer
        self.run_webify = run_webify
        self.browser_controller = browser_controller
        self.uploader = uploader
        self.url_prefix = url_prefix

        self.alive = True

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
        self.run_webify.stop()
        return False

    def press_u(self):
        self.logger.debug('running uploader script, waiting for lock')
        with lock:
            self.uploader.run()
        self.logger.debug('finished running uploader script, released lock')

    def press_w(self):
        self.logger.debug('getting url from user, waiting for lock')
        with lock:
            prefix = self.url_prefix if self.url_prefix != None else ''
            url = input('Enter URL to watch: %s' % prefix)
            self.browser_controller.set_url(prefix+url)
        self.logger.debug('finished getting url from user, released lock')
        return True

    def press_r(self):
        self.logger.debug('compiling, waiting for lock')
        self.run_webify.run(when='now', ignore_times=False, force_copy=False)
        self.logger.debug('finished compiling, released lock')
        return True

    def press_i(self):
        self.logger.debug('compiling ignoring times, waiting for lock')
        self.run_webify.run(when='now', ignore_times=True, force_copy=False)
        self.logger.debug('finished compiling, released lock')
        return True

    def press_c(self):
        self.logger.debug('compiling with force copy, waiting for lock')
        self.run_webify.run(when='now', ignore_times=False, force_copy=True)
        self.logger.debug('finished compiling, released lock')
        return True

    def press_a(self):
        self.logger.debug('compiling all, waiting for lock')
        self.run_webify.run(when='now', ignore_times=True, force_copy=True)
        self.logger.debug('finished compiling, released lock')
        return True

    def press_b(self):
        self.logger.debug('toggling browser live view, waiting for lock')
        with lock:
            self.browser_controller.toggle()
        self.logger.debug('finished toggling browser live view, released lock')

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
    def __init__(self, watched_dir, run_webify):
        super().__init__()
        self.logger = util.WebifyLogger.get('watchdir')
        self.logger.info('Setting up directory watch for %s' % watched_dir)
        self.watched_dir = watched_dir
        self.run_webify = run_webify

        self.last_time = time.time()
        self.time_resolution = 5 # second

    def on_moved(self, event):
        super(DirChangeHandler, self).on_moved(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Moved %s: from %s to %s' % (what, event.src_path, event.dest_path))

    def on_created(self, event):
        super(DirChangeHandler, self).on_created(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Created %s: %s' % (what, event.src_path))
        if os.stat(event.src_path).st_size > 0:
            ignore_times = self.run_webify.webify.meta_data['__ignore_times__']
            self.run_webify.run(when='after', ignore_times=ignore_times, force_copy=False, time_or_duration=5)

    def on_deleted(self, event):
        super(DirChangeHandler, self).on_deleted(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Deleted %s: %s' % (what, event.src_path))

    def on_modified(self, event):
        super(DirChangeHandler, self).on_modified(event)
        what = 'directory' if event.is_directory else 'file'
        self.logger.debug('Modified %s: %s' % (what, event.src_path))
        
        if not event.is_directory:
            if os.path.splitext(event.src_path)[1] in ['.md', '.html', '.yaml', '.css', '.mustache', '.jinja']:
                ignore_times = self.run_webify.webify.meta_data['__ignore_times__']
                self.run_webify.run(when='after', ignore_times=ignore_times, force_copy=False, time_or_duration=5)

class RunWebify:
    def __init__(self, webify, browser_controller):
        self.webify = webify
        self.browser_controller = browser_controller

        self.logger = util.WebifyLogger.get('run-webify')
        self.timer_thread = None
        self.time_for_next_run = None

        self.time_padding = datetime.timedelta(seconds=1)

    def stop(self):
        with lock:
            if self.timer_thread:
                self.logger.warning('Canceling a scheduled run at %s' % self.time_for_next_run)
                self.timer_thread.cancel()

    def run(self, when, ignore_times, force_copy, time_or_duration=None):
        with lock:
            self.logger.debug('RunWebify signal: %s, tm_or_dur: %s' % (when, time_or_duration))

            cur_time = datetime.datetime.now()
            if when == 'now':
                requested_time = cur_time
            elif when == 'after':
                requested_time = cur_time + datetime.timedelta(seconds=time_or_duration)
            elif when == 'at':
                requested_time = time_or_duration
            else:
                self.logger.warning('RunWebify signal: unknown %s' % time_or_duration)
                requested_time = cur_time

            self.logger.debug('current time: %s', cur_time)
            self.logger.debug('requested time: %s', requested_time)

            if self.timer_thread:
                self.logger.debug('A run is already scheduled at %s' % self.time_for_next_run)
                if self.time_for_next_run > requested_time:
                    self.logger.debug('The requested run time is earlier then scheduled run.  Cancelling the scheduled run.')
                    self.timer_thread.cancel()
                    self.time_for_next_run = None
                else:
                    self.logger.debug('The requested run time is after the scheduled run.  Keeping the scheduled run.')
                    return

            if requested_time == cur_time:
                self.logger.info('Running webify "now" as requested')
                self.run_(ignore_times, force_copy)
                self.schedule_next_run(ignore_times, force_copy)
            else:
                self.time_for_next_run = requested_time
                self.logger.info('Scheduling a run at %s' % self.time_for_next_run)
                delay = ((self.time_for_next_run - cur_time) + self.time_padding).total_seconds()
                self.timer_thread = threading.Timer(delay, self.run_with_lock_, [ignore_times, force_copy])
                self.timer_thread.start()
                print('Enter choice: ', )

    def run_with_lock_(self, ignore_times, force_copy):
        with lock:
            self.logger.info('Running webify at %s as scheduled' % self.time_for_next_run)
            self.run_(ignore_times, force_copy)
            self.schedule_next_run(ignore_times, force_copy)
            print('Enter choice: ', )

    def schedule_next_run(self, ignore_times, force_copy):
        nrt = self.webify.next_run_time
        if nrt == None:
            if self.time_for_next_run == None and self.timer_thread:
                self.timer_thread.cancel()
                self.timer_thread = None
            self.logger.info('No run is scheduled')
            return
        if self.time_for_next_run != None and nrt > self.time_for_next_run:
            self.logger.info('Next run is scheduled at {}'.format(self.time_for_next_run))
            return
        if self.timer_thread:
            self.timer_thread.cancel()
            self.timer_thread = None

        cur_time = datetime.datetime.now()
        self.time_for_next_run = nrt 
        delay = ((self.time_for_next_run - cur_time) + self.time_padding).total_seconds()
        self.logger.info('Scheduling next run at %s' % self.time_for_next_run)
        self.timer_thread = threading.Timer(delay, self.run_with_lock_, [ignore_times, force_copy])
        self.timer_thread.start()
        self.logger.info('Next run is scheduled at {}'.format(self.time_for_next_run))

    def run_(self, ignore_times, force_copy):
        self.logger.debug('Executing webify.traverse()')
        cur_time = datetime.datetime.now()
        self.webify.meta_data['__ignore_times__'] = ignore_times
        self.webify.meta_data['__force_copy__'] = force_copy
        self.webify.meta_data['__last_updated__'] = cur_time.strftime('%Y-%m-%d %H:%M')
        self.webify.meta_data['__time__'] = cur_time
        self.webify.traverse()
        self.browser_controller.refresh()
        self.time_for_next_run = None

class WebifyLive:
    def __init__(self, webify, url_prefix, upload_shell_script):

        browser_controller = browser.BrowserController()
        uploader = upload.UploadScript(shell_script=upload_shell_script)

        self.run_webify = RunWebify(webify=webify, browser_controller=browser_controller)
        ignore_times = self.run_webify.webify.meta_data['__ignore_times__']
        self.run_webify.run(when='now', ignore_times=ignore_times, force_copy=False)

        watched_dir = webify.get_src()
        dir_observer = Observer()
        dir_observer.schedule(DirChangeHandler(watched_dir=watched_dir, run_webify=self.run_webify), watched_dir, recursive=True)
        dir_observer.start()

        kl = KeyboardListener(dir_observer, run_webify=self.run_webify, browser_controller=browser_controller, uploader=uploader, url_prefix=url_prefix)
        kl_thread = threading.Thread(target=kl.handler)
        kl_thread.start()

        try:
            while kl.alive:
                time.sleep(1)
        except KeyboardInterrupt:
            dir_observer.stop()

        dir_observer.join()
        kl_thread.join()
        if self.run_webify.timer_thread:
            self.run_webify.timer_thread.join()

if __name__ == '__main__':
    pass