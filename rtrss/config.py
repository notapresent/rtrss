import os
import logging

# Feed update interval, minutes
UPDATE_INTERVAL = 5

# Database cleanup interval, minutes
CLEANUP_INTERVAL = 60

# Perform daily mainenance at this time
DAILY_MAINTENANCE_TIME = '00:15'

# Timeone for the DAILY_MAINTENANCE_TIME
TZNAME = 'Europe/Moscow'

# Database connection settings
_devdb = 'postgresql://postgres:postgres@localhost/rtrss_dev'
SQLALCHEMY_DATABASE_URI = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL', _devdb)

FEED_URL = 'http://feed.rutracker.org/atom/f/0.atom'

LOGLEVEL = logging.DEBUG

SECRET_KEY = os.environ.get('SECRET_KEY', 'development key')

DEBUG = bool(os.environ.get('RTRSS_DEBUG', False))
