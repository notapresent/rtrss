import os

SQLALCHEMY_DATABASE_URI = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL')

# directory to store runtime data, write access required
DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR')

SECRET_KEY = os.environ.get('RTRSS_SECRET_KEY')

FILESTORAGE_URL = os.environ.get('RTRSS_FILESTORAGE_URL')
GCS_PRIVATEKEY_URL = os.environ.get('RTRSS_GCS_PRIVATEKEY_URL')

PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT'))
IP = os.environ.get('OPENSHIFT_PYTHON_IP')

DEBUG = False
