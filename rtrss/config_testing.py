import os
import tempfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/rtrss_test'

# directory to store runtime data, write access required
DATA_DIR = tempfile.mkdtemp(dir=ROOT_DIR)

TESTING = True

SECRET_KEY = 'development key'

FILESTORAGE_URL = 'file://{}'.format(DATA_DIR)
