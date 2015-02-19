import os


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/rtrss_test'

DATA_DIR = os.path.join(ROOT_DIR, 'data')

TESTING = True

SECRET_KEY = 'development key'

FILESTORAGE_SETTINGS = {
    'URL': 'file:///non-existent-directory/',
}
