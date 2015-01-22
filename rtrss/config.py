import os
import logging

# Database connection settings
_devdb = 'postgresql://postgres:postgres@localhost/rtrss_dev'
SQLALCHEMY_DATABASE_URI = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL', _devdb)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# directory to store runtime data, write access required
DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR', os.path.join(ROOT_DIR, 'data'))

TRACKER_HOST = 'rutracker.org'

# Timeone for the tracker times
TZNAME = 'Europe/Moscow'

DEBUG = bool(os.environ.get('DEBUG', False))

LOGLEVEL = logging.INFO

SECRET_KEY = os.environ.get('RTRSS_SECRET_KEY', 'development key')

# Settings for torrent file storage
_default_fsurl = 'file://{}'.format(DATA_DIR)
FILESTORAGE_URL = os.environ.get('RTRSS_FILESTORAGE_URL', _default_fsurl)
GCS_PRIVATEKEY_URL = os.environ.get('RTRSS_GCS_PRIVATEKEY_URL')

if 'OPENSHIFT_APP_DNS' in os.environ:       # production
    SERVER_NAME = os.environ.get('OPENSHIFT_APP_DNS')
    PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT', 8080))
    IP = os.environ.get('OPENSHIFT_PYTHON_IP', '0.0.0.0')

elif 'C9_HOSTNAME' in os.environ:       # Cloud9 dev environment
    SERVER_NAME = os.environ.get('C9_HOSTNAME')
    PORT = int(os.environ.get('C9_PORT', 8080))
    IP = os.environ.get('C9_IP', '0.0.0.0')

else:       # Local dev environment
    SERVER_NAME = 'localhost:8080'
    PORT = 8080
    IP = '0.0.0.0'
