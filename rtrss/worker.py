"""Scheduler initialization and worker entry point"""
import sys
import os
import logging
from rtrss import config
from rtrss.scheduler import Scheduler
from rtrss.database import clear_db, init_db, session_scope, engine, Session
from rtrss.manager import Manager

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'

_logger = logging.getLogger(__name__)


def setup_logging():
    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)

    # set up primary handler...
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOGLEVEL)
    console_handler.setFormatter(formatter)
    rootlogger.addHandler(console_handler)

    # ... and debug handler if needed
    if config.DEBUG:
        filename = os.path.join(config.DATA_DIR, 'debug.log')
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        rootlogger.addHandler(file_handler)

    # Limit 3rd-party packages logging
    logging.getLogger('schedule').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    # logging.getLogger('oauth2client').setLevel(logging.WARNING)


def shutdown_logging():
    logging.shutdown()


def populate_categories():
    with session_scope(Session) as db:
        manager = Manager(config, db)
        manager.populate_categories()


def import_categories():
    with session_scope(Session) as db:
        manager = Manager(config, db)
        manager.import_categories()


def main():     # TODO argparse parameters
    setup_logging()
    retcode = 0
    if len(sys.argv) < 2 or sys.argv[1] == 'run':
        scheduler = Scheduler(config)
        retcode = scheduler.run()

    elif sys.argv[1] == 'import_categories':
        import_categories()

    elif sys.argv[1] == 'populate_categories':
        populate_categories()

    elif sys.argv[1] == 'initdb':
        init_db(engine)

    elif sys.argv[1] == 'cleardb':
        clear_db(engine)

    else:
        retcode = 1
        _logger.error("Invalid parameters: %s", sys.argv)

    shutdown_logging()
    return retcode

if __name__ == '__main__':
    sys.exit(main())
