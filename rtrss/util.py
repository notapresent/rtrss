import logging
import os
import pytz
from datetime import datetime
from tzlocal import get_localzone
from . import config

_logger = logging.getLogger(__name__)


def make_localtime(str_time, tzname, fmt='%H:%M'):
    '''
    Make local timezone-aware time from time and timezone strings
    '''
    today = datetime.now().date()
    dt = datetime.combine(today, datetime.strptime(str_time, fmt).time())
    return pytz.timezone(tzname).localize(dt).astimezone(get_localzone())


def import_categories():    # TODO
    '''
    Import all existing categories from tracker. This function should be used
    only once, after initial deployment
    '''
    pass

def save_debug_file(filename, contents):
    ts_prefix = datetime.now().strftime('%d-%m-%Y_%H_%M_%S')
    filename = "{}_{}".format(ts_prefix, filename)
    filename = os.path.join(config.DATA_DIR, filename)
    with open(filename,'w') as f:
        f.write(contents)
