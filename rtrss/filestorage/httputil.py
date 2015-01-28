import logging
import time

import requests
from googleapiclient.errors import HttpError


# Number of retries in case of API errors
NUM_RETRIES = 3

# Delay between retry attempts, seconds
RETRY_DELAY = 1

_logger = logging.getLogger(__name__)


def is_retryable(exc):
    retryable_codes = [500, 502, 503, 504]
    """Returns True if exception is "retryable", eg. HTTP 503"""
    if issubclass(exc, requests.exceptions.RequestException):
        code = exc.response.status_code
    elif issubclass(exc, HttpError):
        code = exc.resp.status
    else:
        return False
    return code in retryable_codes


def retry_on_exception(
        exceptions=(HttpError, requests.exceptions.RequestException),
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
                except exceptions as err:
                    # Reraise if non-retryable error
                    if not retryable(err):
                        raise

                    _logger.warn("Retrying in %.2f seconds ...", delay)
                    time.sleep(delay)
                    mtries -= 1

            # Only one last try left
            return f(*args, **kwargs)
        return wrapped_f
    return wrap
