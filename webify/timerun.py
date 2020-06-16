import sched
import time

if __name__ == '__main__':
    scheduler = sched.scheduler(time.time, time.sleep)

    def print_event(name):
        print('EVENT: %s, %s' % (time.time(), name))

    print('START: %s' % time.time())
    scheduler.enter(30, 1, print_event, ('second',))
    scheduler.enter(15, 1, print_event, ('first',))

    scheduler.run()