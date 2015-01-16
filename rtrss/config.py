import os
import logging

# Database connection settings
_devdb = 'postgresql://postgres:postgres@localhost/rtrss_dev'
SQLALCHEMY_DATABASE_URI = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL', _devdb)

# directory to store runtime data, write access required
_projdir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR', os.path.join(_projdir, 'data'))

TRACKER_HOST = 'rutracker.org'

# Timeone for the tracker times
TZNAME = 'Europe/Moscow'

DEBUG = bool(os.environ.get('DEBUG', False))

LOGLEVEL = logging.INFO

SECRET_KEY = os.environ.get('RTRSS_SECRET_KEY', 'development key')

# Settings for torrent file storage
_default_fsurl = 'file://{}'.format(os.path.join(DATA_DIR, 'torrents'))
FILESTORAGE_URL = os.environ.get('RTRSS_FILESTORAGE_URL', _default_fsurl)
GCS_PRIVATEKEY_URL = os.environ.get('RTRSS_GCS_PRIVATEKEY_URL')
