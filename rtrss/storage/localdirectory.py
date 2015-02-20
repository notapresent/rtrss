import os
import errno
import logging

from rtrss.storage.util import locked_open, M_WRITE


_logger = logging.getLogger(__name__)


class LocalDirectoryStorage(object):
    def __init__(self, dir_path):
        self._dir = dir_path

    def _key_to_path(self, key):
        return os.path.join(self._dir, key)

    def put(self, key, value):
        filepath = self._key_to_path(key)
        dirpath = os.path.dirname(filepath)

        if not os.path.isdir(dirpath):
            mkdir_p(dirpath)

        with locked_open(filepath, M_WRITE) as f:
            f.write(value)

    def get(self, key):
        try:
            with locked_open(self._key_to_path(key)) as f:
                return f.read()
        except OSError as e:
            if e.errno == 2:  # No such file
                return None

    def delete(self, key):
        try:
            os.unlink(self._key_to_path(key))
        except OSError as e:
            if e.errno == 2:  # No such file
                pass

    def bulk_delete(self, keys):
        for k in keys:
            self.delete(k)

    def __repr__(self):
        return "<LocalDirectoryStorage dir='{}'>".format(self._dir)


def mkdir_p(path):
    """Make directory with all subdirectories
    :param path: directory to create
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
