import os
import fcntl

from oauth2client.client import Credentials
from oauth2client.client import Storage as BaseStorage


class Storage(BaseStorage):
    def __init__(self, filename):
        self._filename = filename
        self._file = None
        self._fd = None

    def acquire_lock(self):
        self._fd = os.open(self._filename, os.O_RDWR | os.O_CREAT)
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        self._file = os.fdopen(self._fd, 'r+b')

    def release_lock(self):
        if self._fd is None or self._file is None:
            raise RuntimeError('Trying to release unacquired lock')

        self._file.flush()
        os.fdatasync(self._fd)
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        self._file.close()
        self._fd = self._file = None

    def locked_get(self):
        credentials = None
        try:
            content = self._file.read()
        except IOError as e:
            return credentials

        try:
            credentials = Credentials.new_from_json(content)
            credentials.set_store(self)
        except ValueError:
            pass

        return credentials

    def locked_put(self, credentials):
        self._file.write(credentials.to_json())

    def locked_delete(self):
        os.unlink(self._filename)
