"""Scheduler initialization and worker entry point"""
import sys
import time
import logging
from schedule import Scheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from . import config
from . import OperationInterruptedException
from .manager import Manager
from .util import make_localtime
from .dbutil import session_scope

_logger = logging.getLogger(__name__)

engine = create_engine(config.SQLALCHEMY_DATABASE_URI, client_encoding='utf8')
Session = sessionmaker(bind=engine)


class Worker(object):
    def __init__(self, config):
        self.config = config
        self.scheduler = Scheduler()
        self.setup_schedule()

    def setup_schedule(self):
        self.scheduler.every(self.config.UPDATE_INTERVAL).minutes.\
            do(self.run_task, 'update')

        self.scheduler.every(self.config.CLEANUP_INTERVAL).minutes.\
            do(self.run_task, 'cleanup')

        localtime = make_localtime(
            self.config.DAILY_MAINTENANCE_TIME,
            self.config.TZNAME)
        self.scheduler.every().day.at(localtime.strftime('%H:%M')).\
            do(self.run_task, 'daily_reset')

    def run_task(self, task_name):
        with session_scope(Session) as session:
            manager = Manager(self.config, session)
            try:
                getattr(manager, task_name)()
            except OperationInterruptedException:
                pass

    def run(self):
        _logger.info('Worker started')

        try:
            while True:
                self.scheduler.run_pending()
                time.sleep(self.scheduler.idle_seconds)

        except (KeyboardInterrupt, SystemExit):
            _logger.info('Worker caught interrupt signal, exiting')
            return 0


def main():
    logging.basicConfig(
        level=config.LOGLEVEL, stream=sys.stdout,
        format='%(asctime)s %(levelname)s %(name)s %(message)s')

    # Limit 3rd-party packages logging
    logging.getLogger('schedule').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    worker = Worker(config)
    return worker.run()

if __name__ == '__main__':
    sys.exit(main())
