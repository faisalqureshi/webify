import datetime
import dateutil

def parse(t):
    if t == 'big-bang':
        return -2
    if t == 'ragnarok':
        return -1
    return dateutil.parser.parse(t)

def check_valid_start_and_end(ts, te):

    # Start at big-bang and end at ragnarok
    if ts == -2 and te == -1:
        return True

    # Can't start at ragnarok or finish at big-bang
    if ts == -1 or te == -2:
        return False

    # Can't both start and end at big-bang
    if ts == -2 and te == -2:
        return False

    # Can't both start and end at ragnarok
    if ts == -1 and te == -1:
        return False

    if ts == -2:
        return True

    if te == -1:
        return True

    if ts < te:
        return True

    return False

def check_for_time_in_range(ts, te, c):
    # 'big-bang' -> -2
    # 'ragnarok' -> -1

    if not check_valid_start_and_end(ts, te):
        return 'error'

    sf = ef = False
    
    try:
        if ts == -2 or ts <= c:
            sf = True
        if te == -1 or te >= c:
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

# def check_for_time_in_range(s, e, c):
#     sf = ef = False
    
#     try:
#         if s == 'big-bang' or dateutil.parser.parse(s) <= c:
#             sf = True
#         if e == 'ragnarok' or dateutil.parser.parse(e) >= c:
#             ef = True
#     except:
#         return 'error'

#     if sf and ef:
#         return True
#     elif sf and not ef:
#         return False
#     elif not sf and ef:
#         return False
#     elif not sf and not ef:
#         return 'error'
