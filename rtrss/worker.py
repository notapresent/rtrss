"""Worker management and helper commands"""
import sys
import os
import logging
import signal
import argparse

from logentries import LogentriesHandler

from rtrss import config
from rtrss import scheduler
from rtrss import database
from rtrss import manager
from rtrss.daemon import make_daemon


_logger = logging.getLogger(__name__)


def _make_signal_names_map():
    return dict((k, v) for v, k in signal.__dict__.items()
                if v.startswith('SIG') and not v.startswith('SIG_'))

# Mapping signal number => signal name
_SIGNAL_NAMES = _make_signal_names_map()


def _signal_handler(signum, frame):
    msg = 'Caught {} ({}), exiting'.format(_SIGNAL_NAMES[signum], signum)
    _logger.info(msg)
    sys.exit(0)


def _set_signal_handlers():
    exits = [signal.SIGHUP, signal.SIGTERM, signal.SIGQUIT, signal.SIGINT]
    for s in exits:
        signal.signal(s, _signal_handler)


def _setup_logging():
    """Initialize logging and add handlers"""
    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(config.LOG_FORMAT_BRIEF)

    # logging to stderr with maximum verbosity
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    rootlogger.addHandler(console_handler)
    _logger.debug('Logging to stderr initialized')

    # logging to file
    log_dir = os.environ.get('OPENSHIFT_LOG_DIR') or config.DATA_DIR
    filename = os.path.join(log_dir, 'worker.log')
    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(config.LOGLEVEL)
    rootlogger.addHandler(file_handler)
    _logger.debug('Logging to %s with loglevel %s initialized',
                  filename, logging.getLevelName(config.LOGLEVEL))

    # Limit 3rd-party packages logging
    logging.getLogger('schedule').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)
    logging.getLogger('oauth2client').setLevel(logging.WARNING)


def setup_external_logging():
    rootlogger = logging.getLogger()
    if 'LOGENTRIES_TOKEN_WORKER' in os.environ:
        token = os.environ['LOGENTRIES_TOKEN_WORKER']
        fmt = '%(asctime)s : %(levelname)s %(name)s %(message)s'
        dtfmt = '%a %b %d %H:%M:%S %Z %Y'
        le_handler = LogentriesHandler(token)
        formatter = logging.Formatter(fmt, dtfmt)
        le_handler.setFormatter(formatter)
        rootlogger.addHandler(le_handler)
        rootlogger.debug('Logging to logentries initialized')


def app_init():
    _setup_logging()
    _logger.info('Initializing worker')
    _set_signal_handlers()


def app_teardown():
    _logger.info('Tearing down worker')
    # commit everything
    database.Session().commit()
    logging.shutdown()


def get_status(daemon):
    """Return daemon status string"""
    running = daemon.is_running()
    if running:
        with open(daemon.pidfile, 'r') as f:
            pid = f.read().strip()
        msg = "Daemon is running with pid {}".format(pid)
    else:
        msg = "Daemon is not running"
    return msg


def worker_action(action):
    if action == 'run':
        sched = scheduler.Scheduler(config)
        return sched.run()
    else:
        mgr = manager.Manager(config)
        mgr.run_task(action)


def db_action(action):
    if action == 'clear':
        database.clear()
    elif action == 'init':
        database.init()
    elif action == 'import_users':
        from rtrss.util import import_users

        csvfilename = os.path.join(config.ROOT_DIR, 'users.csv')
        import_users(csvfilename)


def daemon_action(action):
    daemon = make_daemon(config)
    if action == 'status':
        print get_status(daemon)
        return 0
    else:
        return getattr(daemon, action)()


def make_argparser():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='rtrssmgr',
        description='RTRSS worker command line interface'
    )
    subparsers = parser.add_subparsers()

    wp = subparsers.add_parser(
        'worker',
        help='Worker commands'
    )
    wp.add_argument(
        'action',
        help='Action to perform',
        choices=['run', 'update', 'sync_categories', 'populate_categories']
    )
    wp.set_defaults(func=worker_action)

    dp = subparsers.add_parser(
        'daemon',
        help='Daemon control'
    )
    dp.add_argument(
        'action',
        help='Control daemon process or view status',
        choices=['start', 'stop', 'restart', 'status']
    )
    dp.set_defaults(func=daemon_action)

    dbp = subparsers.add_parser(
        'db',
        help='Database managemant')
    dbp.add_argument(
        'action',
        help='Perform database initialization or clean-up',
        choices=['init', 'clear', 'import_users']
    )
    dbp.set_defaults(func=db_action)

    return parser


def main():
    """Worker entry point"""
    args = make_argparser().parse_args()
    app_init()
    args.func(args.action)
    app_teardown()
