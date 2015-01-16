"""Worker management and helper commands"""
import sys
import os
import logging
import time
import datetime
import signal
import atexit
import argparse
from rtrss import config
from rtrss import scheduler
from rtrss import database
from rtrss import manager
from rtrss.daemon import make_daemon

_logger = logging.getLogger(__name__)

_signalnames = dict((k, v) for v, k in sorted(signal.__dict__.items())
     if v.startswith('SIG') and not v.startswith('SIG_'))

def _signal_handler(signum, frame):
    msg = 'Caught signal {} ({}), exiting'.format(_signalnames[signum], signum)
    _logger.info(msg)
    sys.exit(0)

def _set_signal_handlers():
    exits = [signal.SIGHUP, signal.SIGTERM, signal.SIGQUIT, signal.SIGINT]
    for s in exits:
        signal.signal(s, _signal_handler)


def _setup_logging():
    '''Initialize logging and add handlers'''
    LOG_FORMAT = '%(asctime)s %(process)d %(levelname)s %(name)s %(message)s'
    
    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(LOG_FORMAT)

    # logging to stderr with maximum verbosity 
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    rootlogger.addHandler(console_handler)
    _logger.info('Logging to stderr initialized')


    #  logging to file
    logdir = os.environ.get('OPENSHIFT_LOG_DIR') or config.DATA_DIR
    filename = os.path.join(logdir, 'worker.log')
    file_handler = logging.FileHandler(filename)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(config.LOGLEVEL)
    rootlogger.addHandler(file_handler)
    _logger.info('Logging to %s with loglevel %s initialized', 
                 filename, logging.getLevelName(config.LOGLEVEL))
    
    # TODO external logging service handler here
    # TODO warning & error notifications with SMTPHandler

    # Limit 3rd-party packages logging
    logging.getLogger('schedule').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('googleapiclient').setLevel(logging.WARNING)


def _shutdown_logging():
    '''Shutdown logging. Must be called immediately before exit'''
    _logger.info('Shutting down logging')
    logging.shutdown()
    
# "Public" functions below this line

def app_init():
    _setup_logging()
    _logger.info('Initializing worker')
    _set_signal_handlers()
    # atexit.register(app_teardown)


def app_teardown():
    _logger.info('Tearing down worker')
    # Session().commit()        # TODO    
    _shutdown_logging()


def get_status(daemon):
    '''Return daemon status string'''
    running = daemon.is_running()
    if running:
        with open(daemon.pidfile,'r') as f:
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
        with database.session_scope(database.Session) as db:
            mgr = manager.Manager(config, db)
            return getattr(mgr, action)()


def db_action(action):
    if action == 'clear':
        database.clear_db()
    elif action == 'init':
        database.init_db()

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
        choices=['run', 'update', 'import_categories', 
                 'populate_categories']
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
        choices=['init', 'clear']
    )
    dbp.set_defaults(func=db_action)
    
    return parser


def main():
    '''Worker entry point'''
    args = make_argparser().parse_args()
    app_init()
    args.func(args.action)
    app_teardown()
