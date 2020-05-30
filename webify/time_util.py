import datetime
import dateutil

def check_for_time_in_range(s, e, c):
    sf = ef = False
    
    try:
        if s == 'big-bang' or dateutil.parser.parse(s) <= c:
            sf = True
        if e == 'ragnarok' or dateutil.parser.parse(e) >= c:
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
