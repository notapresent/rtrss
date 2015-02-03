import os
import logging
import importlib

# All configuration defaults are set in this module

TRACKER_HOST = 'rutracker.org'

# Timeone for the tracker times
TZNAME = 'Europe/Moscow'

ANNOUNCE_URLS = [
    'http://bt.{host}/ann'.format(host=TRACKER_HOST),
    'http://bt2.{host}/ann'.format(host=TRACKER_HOST),
    'http://bt3.{host}/ann'.format(host=TRACKER_HOST),
    'http://bt4.{host}/ann'.format(host=TRACKER_HOST)
]

LOGLEVEL = logging.INFO

LOG_FORMAT_LOGENTRIES = '%(levelname)s %(name)s %(message)s'
LOG_FORMAT_BRIEF = '%(asctime)s %(levelname)s %(name)s %(message)s'

ADMIN_LOGIN = os.environ.get('ADMIN_LOGIN', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@localhost')

# path to save torrent files
TORRENT_PATH_PATTERN = 'torrents/{}.torrent'

APP_ENVIRONMENT = os.environ.get('RTRSS_ENVIRONMENT')

if not APP_ENVIRONMENT:
    raise EnvironmentError('RTRSS_ENVIRONMENT must be set')

IP = '0.0.0.0'
PORT = 8080

_mod = importlib.import_module('rtrss.config_{}'.format(APP_ENVIRONMENT))
_envconf = {k: v for k, v in _mod.__dict__.items() if k == k.upper()}
globals().update(_envconf)
