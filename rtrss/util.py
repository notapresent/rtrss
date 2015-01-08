import logging
import os
import pytz
from datetime import datetime, date, timedelta
from tzlocal import get_localzone
from . import config

ONEDAY = timedelta(days=1)

_logger = logging.getLogger(__name__)


def make_localtime(str_time, tzname, fmt='%H:%M'):
    '''
    Make local timezone-aware time from time and timezone strings
    '''
    today = date.today()
    dt = datetime.combine(today, datetime.strptime(str_time, fmt).time())
    tracker_tz = pytz.timezone(tzname)
    return tracker_tz.localize(dt).astimezone(get_localzone())


def time_to_closest_midnight(tzname):
    tz = pytz.timezone(tzname)
    utcnow = pytz.utc.localize(datetime.utcnow())
    localnow = utcnow.astimezone(tz)
    localmidnight = localnow.replace(hour=0, minute=0, second=0)
    delta = localnow - localmidnight

    if delta < ONEDAY / 2:
        return delta
    else:
        return ONEDAY - delta

def save_debug_file(filename, contents):
    ts_prefix = datetime.now().strftime('%d-%m-%Y_%H_%M_%S')
    filename = "{}_{}".format(ts_prefix, filename)
    filename = os.path.join(config.DATA_DIR, filename)
    with open(filename, 'w') as f:
        f.write(contents)
