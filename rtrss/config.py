import os
import logging

# Database connection settings
_devdb = 'postgresql://postgres:postgres@localhost/rtrss_dev'
SQLALCHEMY_DATABASE_URI = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL', _devdb)

# directory to store runtime data, write access required
_dev_datadir = os.path.join(os.environ.get('HOME'), 'data')
DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR', _dev_datadir)

TRACKER_HOST = 'rutracker.org'

# Timeone for the tracker times
TZNAME = 'Europe/Moscow'

DEBUG = bool(os.environ.get('RTRSS_DEBUG', False))

LOGLEVEL = logging.DEBUG

SECRET_KEY = os.environ.get('RTRSS_SECRET_KEY', 'development key')

# Settings for torrent file storage
STORAGE_SETTINGS = {
    'BUCKET_NAME': os.environ.get('RTRSS_GCS_BUCKET_NAME',
                                  'rtrss-development-bucket'),
    'CLIENT_CREDENTIALS': os.environ.get('RTRSS_GCS_CLIENT_CREDENTIALS'),
}
