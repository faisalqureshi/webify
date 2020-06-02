from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from webify2 import Webify

class RunWebify(FileSystemEventHandler):
    """Runs webify if anything changes."""

    def __init__(self, webify_func):
        self.webify_func = webify_func

    def on_moved(self, event):
        super(RunWebify, self).on_moved(event)

        what = 'directory' if event.is_directory else 'file'
        print("Moved %s: from %s to %s", what, event.src_path,
                     event.dest_path)

    def on_created(self, event):
        super(RunWebify, self).on_created(event)

        what = 'directory' if event.is_directory else 'file'
        print("Created %s: %s", what, event.src_path)

    def on_deleted(self, event):
        super(RunWebify, self).on_deleted(event)

        what = 'directory' if event.is_directory else 'file'
        print("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event):
        super(RunWebify, self).on_modified(event)

        what = 'directory' if event.is_directory else 'file'
        print("Modified %s: %s", what, event.src_path)
        print("Starting webification")
        self.webify_func.traverse()
        print("Ending webification")

def start(event_handler, srcdir):
    print(srcdir)
    observer = Observer()
    observer.schedule(event_handler, srcdir, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()    

if __name__ == "__main__":
    logging.basicConfig(level=print,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = RunWebify()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()