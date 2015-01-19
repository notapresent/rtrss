import os
import os.path as path
import errno
import logging
import urlparse
import string
import filelock

_logger = logging.getLogger(__name__)


def slugify(key):
    """Make a valid filename from arbitrary string"""
    valid_chars = set(string.letters + string.digits + '-_.()')
    return ''.join(c for c in key if c in valid_chars)


def parse_fsurl(url):
    """Parse file storage URL and return directory name"""
    parsed = urlparse.urlparse(url)
    if parsed.netloc:       # Relative path
        modpath = path.abspath(path.dirname(__file__))
        projpath = path.abspath(path.join(modpath, os.pardir, os.pardir))
        relpath = path.join(parsed.netloc, parsed.path.strip(os.sep))
        return path.join(projpath, relpath)
    else:
        return parsed.path.rstrip(os.sep)


def mkdir_p(path):
    """Make directory with all subdirectories
    :param path: directory to create
    """
    try:
        os.makedirs(path)
    except OSError as exc:      # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def ensure_dir(dirname):
    """Check if file directory exists, create if it doesn't"""
    if not path.exists(dirname):
        mkdir_p(dirname)


class DirectoryFileStorage(object):
    def __init__(self, config):
        self._dir = parse_fsurl(config.FILESTORAGE_URL)
        mkdir_p(self._dir)
        if not os.access(self._dir, os.W_OK):
            raise IOError('Directory {} is not writeable'.format(self._dir))

        _logger.info('Directory storage initialized in {}'.format(self._dir))

    def full_path(self, key):
        return path.join(self._dir, slugify(key))

    def lockfilename(self, filename):
        return filename + '.lock'

    def get(self, key):
        filename = self.full_path(key)
        lockfilename = self.lockfilename(filename)
        _logger.debug('Getting {} from {}'.format(key, filename))
        with filelock.FileLock(lockfilename):
            with open(filename) as file:
                return file.read()

    def put(self, key, content, mimetype=None):     # noqa
        filename = self.full_path(key)
        lockfilename = self.lockfilename(filename)
        ensure_dir(path.dirname(filename))
        _logger.debug('Saving {} to {}'.format(key, filename))
        with filelock.FileLock(lockfilename):
            with open(filename, 'w') as file:
                file.write(content)

    def delete(self, key):
        filename = self.full_path(key)
        lockfilename = self.lockfilename(filename)
        _logger.debug('Deleting {}'.format(filename))
        with filelock.FileLock(lockfilename):
            try:
                os.unlink(filename)
            except OSError:
                pass

    def __repr__(self):
        return "<DirectoryFileStorage dir='{}'>".format(self._dir)
