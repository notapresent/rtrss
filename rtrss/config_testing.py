import os


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/rtrss_test'

# This should be set by tests
DATA_DIR = None

TESTING = True

SECRET_KEY = 'development key'

# This should be set by tests
FILESTORAGE_URL = None
