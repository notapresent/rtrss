import os
import time

from oauth2client.client import Credentials
from oauth2client.client import Storage as BaseStorage
import filelock





# Default timeout for locking operations
TIMEOUT = 5

# Default poll interval for locking operations
POLL_INTERVAL = 0.05


class Storage(BaseStorage):
    """Store and retrieve a single credential to and from a file."""

    def __init__(self, filename):
        self._filename = filename
        self._lock = filelock.FileLock(filename + '.lock')

    def acquire_lock(self, timeout=TIMEOUT, poll_interval=POLL_INTERVAL):
        """Acquires any lock necessary to access this Storage.

        This lock is not reentrant."""
        self._wait_for_the_lock(timeout, poll_interval)
        self._lock.acquire(timeout=timeout, poll_intervall=poll_interval)

    def release_lock(self):
        """Release the Storage lock.

        Trying to release a lock that isn't held will result in a
        RuntimeError.
        """
        if not self._lock.is_locked():
            raise RuntimeError('Trying to release unacquired lock')

        self._lock.release()

    def locked_get(self):
        """Retrieve Credential from file.

        Returns:
          oauth2client.client.Credentials

        """
        credentials = None
        try:
            with open(self._filename, 'rb') as f:
                content = f.read()
        except IOError:
            return credentials

        try:
            credentials = Credentials.new_from_json(content)
            credentials.set_store(self)
        except ValueError:
            pass

        return credentials

    def locked_put(self, credentials):
        """Write Credentials to file.

        Args:
          credentials: Credentials, the credentials to store.

        """
        with open(self._filename, 'w') as f:
            f.write(credentials.to_json())

    def locked_delete(self, timeout=TIMEOUT, poll_interval=POLL_INTERVAL):
        """Delete Credentials file.

        Args:
          credentials: Credentials, the credentials to store.
        """
        self._wait_for_the_lock(timeout=timeout, poll_interval=poll_interval)
        os.unlink(self._filename)

    def _wait_for_the_lock(self, timeout=TIMEOUT, poll_interval=POLL_INTERVAL):
        """Wait for internal lock to become unlocked

        :raises filelock.Timeout
        """
        start_time = time.time()
        while self._lock.is_locked():
            if timeout is not None and time.time() - start_time > timeout:
                raise filelock.Timeout(self._filename)
            else:
                time.sleep(poll_interval)
