import logging
import time
import os
import fcntl
from contextlib import contextmanager

import requests
from googleapiclient.errors import HttpError








# Number of retries in case of API errors
NUM_RETRIES = 3

# Delay between retry attempts, seconds
RETRY_DELAY = 1

# Open modes for locked_open
M_READ, M_WRITE = range(2)

# Flags and settings for open modes
_MODES = (
    (os.O_RDONLY, fcntl.LOCK_SH, 'rb'),  # read
    (os.O_WRONLY | os.O_CREAT | os.O_TRUNC, fcntl.LOCK_EX, 'wb')  # write
)

# Blocking flags for flock() call
_BLOCKING_FLAGS = (fcntl.LOCK_NB, 0)

_logger = logging.getLogger(__name__)


def is_retryable(exc):
    retryable_codes = [500, 502, 503, 504]
    """Returns True if exception is "retryable", eg. HTTP 503"""
    if isinstance(exc, requests.exceptions.RequestException):
        code = exc.response.status_code
    elif isinstance(exc, HttpError):
        code = exc.resp.status
    else:
        return False
    return code in retryable_codes


def retry_on_exception(
        retryable=is_retryable,
        tries=NUM_RETRIES,
        delay=RETRY_DELAY):
    """Retry call if function raises retryable exception"""

    def wrap(f):
        def wrapped_f(*args, **kwargs):
            mtries = tries
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except Exception as err:
                    # Re-raise if non-retryable error
                    if not retryable(err):
                        raise

                    _logger.warn("Retrying in %.2f seconds ...", delay)
                    time.sleep(delay)
                    mtries -= 1

            # Only one last try left
            return f(*args, **kwargs)

        return wrapped_f

    return wrap


@contextmanager
def locked_open(filename, mode=M_READ, blocking=True):
    open_mode, flock_flags, mode_str = _MODES[mode]
    flock_flags = flock_flags | _BLOCKING_FLAGS[blocking]

    fileobj = None
    fd = os.open(filename, open_mode)
    try:
        fcntl.flock(fd, flock_flags)
        fileobj = os.fdopen(fd, mode_str)

        try:
            yield fileobj
        finally:
            fileobj.flush()
            os.fdatasync(fd)
    finally:
        if fileobj is not None:
            fileobj.close()


@retry_on_exception()
def download_and_save_keyfile(keyfile_url, keyfile_path):
    """Download private key file and store it"""
    content = requests.get(keyfile_url).content
    with open(keyfile_path, 'w') as fh:
        fh.write(content)
    _logger.info('Keyfile saved to {}'.format(keyfile_path))
