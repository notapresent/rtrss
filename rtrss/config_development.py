import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/rtrss_dev'

# directory to store runtime data, write access required
DATA_DIR = os.path.join(ROOT_DIR, 'data')

DEBUG = True

SECRET_KEY = 'development key'

FILESTORAGE_URL = 'file://{}'.format(DATA_DIR)

SERVER_NAME = os.environ.get('C9_HOSTNAME', 'localhost:8080')
PORT = int(os.environ.get('C9_PORT', 8080))
IP = os.environ.get('C9_IP', '0.0.0.0')
