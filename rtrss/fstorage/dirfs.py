import os
from os.path import dirname, abspath, join
import errno
import logging
import urlparse
import string
import portalocker      # TODO change this to filelock

_logger = logging.getLogger(__name__)


def slugify(key):
    '''Make a valud filename from arbitrary string'''
    valid_chars = set(string.letters + string.digits + '-_.()')
    return ''.join(c for c in key if c in valid_chars)


def parse_fsurl(url):
    '''Parse filestorage URL and return directory name'''
    parsed = urlparse.urlparse(url)
    if parsed.netloc:       # Relative path
        modpath = abspath(dirname(__file__))
        projpath = abspath(join(modpath, os.pardir, os.pardir))
        relpath = join(parsed.netloc, parsed.path.strip(os.sep))
        return join(projpath, relpath)
    else:
        return parsed.path.rstrip(os.sep)


def mkdir_p(path):
    '''Make directory with all subdirectories'''
    try:
        os.makedirs(path)
    except OSError as exc:      # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class DirectoryFileStorage(object):
    def __init__(self, config):
        self._dir = parse_fsurl(config.FILESTORAGE_URL)
        mkdir_p(self._dir)
        if not os.access(self._dir, os.W_OK):
            raise IOError('Directory {} is not writeable'.format(self._dir))

        _logger.info('Directory storage initialized in {}'.format(self._dir))

    def full_path(self, key):
        return join(self._dir, slugify(key))

    def get(self, key):
        with portalocker.Lock(self.full_path(key)) as fh:
            content = fh.read()
        return content

    def put(self, key, content):
        with portalocker.Lock(self.full_path(key)) as fh:
            fh.write(content)

    def delete(self, key):
        filename = self.full_path(key)
        with portalocker.Lock(filename):
            try:
                os.unlink(filename)
            except OSError:
                pass

    def __repr__(self):
        return "<DirectoryFileStorage dir='{}'>".format(self._dir)
