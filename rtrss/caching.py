import os
from UserDict import DictMixin
from contextlib import contextmanager
from tempfile import NamedTemporaryFile


@contextmanager
def open_for_atomic_write(name):
    dirpath, filename = os.path.split(name)
    # use the same dir for os.rename() to work
    with NamedTemporaryFile(dir=dirpath, prefix=filename, suffix='.tmp') as f:
        yield f
        f.flush()  # libc -> OS
        os.fsync(f)  # OS -> disc (note: on OSX it is not enough)
        f.delete = False  # don't delete tmp file if `replace()` fails
        f.close()
        os.rename(f.name, name)


class DiskCache(DictMixin):
    def __init__(self, directory):
        self._dir = directory

    def full_path(self, key):
        if os.sep in key or os.pathsep in key:
            raise IndexError
        return os.path.join(self._dir, key)

    def __getitem__(self, key):
        try:
            with open(self.full_path(key)) as f:
                return f.read()
        except IOError:
            raise KeyError

    def __setitem__(self, key, value):
        if not os.path.isdir(self._dir):
            os.makedirs(self._dir)

        with open_for_atomic_write(self.full_path(key)) as f:
            f.write(value)

    def __delitem__(self, key):
        os.remove(self.full_path(key))

    def __contains__(self, key):
        return os.path.isfile(self.full_path(key))

        # keys() __iter__(), and iteritems().
