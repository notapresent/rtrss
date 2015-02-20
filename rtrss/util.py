import sys
import signal
import logging
import os
import datetime

import newrelic.agent

from rtrss import config


_logger = logging.getLogger(__name__)


def save_debug_file(filename, contents):
    ts_prefix = datetime.datetime.now().strftime('%d-%m-%Y_%H_%M_%S')
    filename = "{}_{}".format(ts_prefix, filename)
    filename = os.path.join(config.DATA_DIR, filename)
    with open(filename, 'w') as f:
        f.write(contents)


def init_newrelic_agent():
    if 'NEW_RELIC_LICENSE_KEY' in os.environ:
        newrelic.agent.initialize()
        _logger.debug('Newrelic agent initialized')


def get_newreilc_app(name, timeout):
    if 'NEW_RELIC_LICENSE_KEY' in os.environ:
        return newrelic.agent.register_application(name=name, timeout=timeout)
    else:
        return None


def setup_logentries_logging(varname):
    pass

def setup_logging(component_name):
    """Initialize logging and add handlers"""
    rootlogger = logging.getLogger()
    rootlogger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(config.LOG_FORMAT_BRIEF)

    # logging to stdout with maximum verbosity
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    rootlogger.addHandler(console_handler)
    _logger.debug('Logging to stdout initialized')

    # Limit 3rd-party packages logging
    loggers = ['schedule', 'requests', 'googleapiclient', 'oauth2client',
               'newrelic', 'sqlalchemy']
    for logger_name in loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logfile_abspath(name):
    log_dir = os.environ.get('OPENSHIFT_LOG_DIR') or config.DATA_DIR
    return os.path.join(log_dir, '{}.log'.format(name))


def _make_signal_names_map():
    return dict((k, v) for v, k in signal.__dict__.items()
                if v.startswith('SIG') and not v.startswith('SIG_'))

# Mapping signal number => signal name
_SIGNAL_NAMES = _make_signal_names_map()


def signal_handler(signum, frame):
    msg = 'Caught {} ({}), exiting'.format(_SIGNAL_NAMES[signum], signum)
    _logger.info(msg)
    sys.exit(0)


def set_signal_handlers():
    exits = [signal.SIGHUP, signal.SIGTERM, signal.SIGQUIT, signal.SIGINT]
    for s in exits:
        signal.signal(s, signal_handler)
