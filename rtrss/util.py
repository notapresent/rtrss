import logging
import pytz
from datetime import datetime
from tzlocal import get_localzone

_logger = logging.getLogger(__name__)


def make_localtime(str_time, tzname, fmt='%H:%M'):
    '''
    Make local timezone-aware time from time and timezone strings
    '''
    today = datetime.now().date()
    dt = datetime.combine(today, datetime.strptime(str_time, fmt).time())
    return pytz.timezone(tzname).localize(dt).astimezone(get_localzone())
