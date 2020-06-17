import datetime
import dateutil
import time
from enum import Enum

class T(Enum):
    bigbang = -2
    ragnarok = -1

def parse(t):
    if t == 'big-bang':
        return T.bigbang
    if t == 'ragnarok':
        return T.ragnarok
    return dateutil.parser.parse(t)

def check_valid_start_and_end(ts, te):

    # Start at big-bang and end at ragnarok
    if ts == T.bigbang and te == T.ragnarok:
        return True

    # Can't start at ragnarok or finish at big-bang
    if ts == T.ragnarok or te == T.bigbang:
        return False

    # Start time must be before end time
    if ts == T.bigbang or te == T.ragnarok or ts < te:
        return True

    return False

def check_for_time_in_range(ts, te, c):
    sf = ef = False
    
    try:
        if ts == T.bigbang or ts <= c:
            sf = True
        if te == T.ragnarok or te >= c:
            ef = True
    except:
        return 'error'

    if sf and ef:
        return True
    elif sf and not ef:
        return False
    elif not sf and ef:
        return False
    elif not sf and not ef:
        return 'error'

def is_after(t, c):
    if t == T.bigbang:
        return False
    if t == T.ragnarok:
        return True
    return t > c

def find_next_time(ts, te, c):
    # We assume that s < e
    if is_after(ts, c):
        return ts
    if is_after(te, c):
        if te == T.ragnarok:
            return None
        else:
            return te
    return None

if __name__ == '__main__':
    from dateutil import parser

    t1 = parser.parse('14 Jun 10:23')
    t2 = parser.parse('15 Jun 9:43')
    t3 = parser.parse('12 Jun 2030 10:42')

    print('t1: ', t1)
    print('t2: ', t2)
    print('t3: ', t3)

    x = t2 - t1
    print('t2-t1', x)

    y = t3 - t1
    print('t3-t1', y)

    print('x is less than 0: ', x < datetime.timedelta(0))
    print('y is less than 0: ', y < datetime.timedelta(0))
    print('x is less than y: ', x < y)