"""
Scheduler controls tasks execution
"""
import time
import logging
from datetime import datetime, date, timedelta
import schedule
import pytz
import tzlocal
from rtrss import OperationInterruptedException
from rtrss.manager import Manager
from rtrss.database import session_scope

# Feed update interval, minutes
UPDATE_INTERVAL = 10

# Database cleanup interval, minutes
CLEANUP_INTERVAL = 60

# Perform daily mainenance at this time
DAILY_MAINTENANCE_TIME = '00:01'

# Do not run update when current time is that close to midnight, minutes
SAFETY_WINDOW_SIZE = 15

ONEDAY = timedelta(days=1)

_logger = logging.getLogger(__name__)


def make_localtime(str_time, tzname, fmt='%H:%M'):
    '''
    Make local timezone-aware time from time and timezone strings
    '''
    today = date.today()
    dt = datetime.combine(today, datetime.strptime(str_time, fmt).time())
    tracker_tz = pytz.timezone(tzname)
    return tracker_tz.localize(dt).astimezone(tzlocal.get_localzone())


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


class Scheduler(object):
    def __init__(self, config):
        self.config = config
        self._sched = schedule.Scheduler()
        self.setup_schedule()

    def setup_schedule(self):
        self._sched.every(UPDATE_INTERVAL).minutes\
            .do(self.run_task, 'update')

        self._sched.every(CLEANUP_INTERVAL).minutes\
            .do(self.run_task, 'cleanup')

        localtime = make_localtime(DAILY_MAINTENANCE_TIME, self.config.TZNAME)
        self._sched.every().day.at(localtime.strftime('%H:%M'))\
            .do(self.run_task, 'daily_reset')

    def run_task(self, task_name):
        if task_name == 'update' and self.is_safety_window():
            _logger.debug('Safety window, skipping update')
            return

        with session_scope() as session:
            manager = Manager(self.config, session)
            try:
                getattr(manager, task_name)()
            except OperationInterruptedException:
                pass

    def is_safety_window(self):
        win = timedelta(minutes=SAFETY_WINDOW_SIZE)
        time_to_midnight = time_to_closest_midnight(self.config.TZNAME)
        return time_to_midnight < win

    def run(self):
        _logger.info('Scheduler started')

        try:
            while True:
                self._sched.run_pending()
                delay = self._sched.idle_seconds
                if delay < 0:
                    delay = 0

                time.sleep(delay)

        except (KeyboardInterrupt, SystemExit):
            _logger.info('Caught interrupt signal, exiting')
            return 0
