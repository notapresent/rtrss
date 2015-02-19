import os

SQLALCHEMY_DATABASE_URI = os.environ.get('OPENSHIFT_POSTGRESQL_DB_URL')

# directory to store runtime data, write access required
DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR')

SECRET_KEY = os.environ.get('RTRSS_SECRET_KEY')

FILESTORAGE_SETTINGS = {
    'URL': os.environ.get('RTRSS_FILESTORAGE_URL'),
    'PRIVATEKEY_URL': os.environ.get('RTRSS_GCS_PRIVATEKEY_URL'),
    'CLIENT_EMAIL': os.environ.get('RTRSS_CLIENT_EMAIL')
}

PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT'))
IP = os.environ.get('OPENSHIFT_PYTHON_IP')

DEBUG = False
