import logging
import requests
from . import OperationInterruptedException

_logger = logging.getLogger(__name__)


class WebClient(object):
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()

    def get_feed(self):
        return self.request('get', self.config.FEED_URL).content

    def request(self, method, url, **kwargs):
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.warn('Request failed: %s', e)
            raise OperationInterruptedException(e)
        else:
            return response
