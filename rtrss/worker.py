"""Worker management and helper commands"""
import os
import logging
import argparse

from rtrss import config, scheduler, database, manager, util


_logger = logging.getLogger(__name__)


def worker_init():
    _logger.debug('Initializing worker')
    util.set_signal_handlers()


def worker_teardown():
    _logger.debug('Tearing down worker')
    logging.shutdown()


def worker_action(action):
    util.init_newrelic_agent()
    util.setup_logentries_logging('LOGENTRIES_TOKEN_WORKER')

    worker_init()
    if action == 'run':
        sched = scheduler.Scheduler(config)
        result = sched.run()
    else:
        mgr = manager.Manager(config)
        result = mgr.run_task(action)
    worker_teardown()
    return result


def db_action(action):
    if action == 'clear':
        database.clear()
    elif action == 'init':
        database.init()
    elif action == 'import_users':
        csvfilename = os.path.join(config.ROOT_DIR, 'users.csv')
        database.import_users(csvfilename)


def make_argparser():
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='rtrssmgr',
        description='RTRSS worker command line interface'
    )
    subparsers = parser.add_subparsers(dest='subcommand')

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
    """Control script entry point"""
    args = make_argparser().parse_args()
    util.setup_logging(args.subcommand)

    args.func(args.action)

