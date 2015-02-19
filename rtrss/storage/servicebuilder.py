import time
import json
import os
import datetime
import logging

from googleapiclient.discovery import DISCOVERY_URI
from googleapiclient.discovery import build_from_document
from googleapiclient.errors import HttpError
from googleapiclient.errors import InvalidJsonError
import httplib2
import uritemplate

from rtrss.storage.util import locked_open, M_WRITE


DISCOVERY_DOC_MAX_AGE = datetime.timedelta(hours=24)

_logger = logging.getLogger(__name__)


def retrieve_discovery_doc(service_name, version, http=None,
                           discovery_service_url=DISCOVERY_URI):
    params = {'api': service_name, 'apiVersion': version}
    requested_url = uritemplate.expand(discovery_service_url, params)
    http = http or httplib2.Http()

    resp, content = http.request(requested_url)

    if resp.status >= 400:
        raise HttpError(resp, content, uri=requested_url)

    try:
        _ = json.loads(content)
    except ValueError:
        raise InvalidJsonError(
            'Bad JSON: %s from %s.' % (content, requested_url))

    return content


class CachedServiceBuilder(object):
    def __init__(self, filename, service_name, version, **kwargs):
        self.filepath = filename
        self.service_name = service_name
        self.version = version
        self.build_params = kwargs

    def expired(self):
        now = time.time()
        updated = os.path.getmtime(self.filepath)
        return now - updated > DISCOVERY_DOC_MAX_AGE.total_seconds()

    @property
    def document(self):
        try:
            with locked_open(self.filepath) as f:
                document = f.read()
        except OSError as e:
            if e.errno == 2:  # no such file
                document = None
            else:
                raise

        if document is None or self.expired():
            document = self.retrieve_document()
            with locked_open(self.filepath, M_WRITE) as f:
                f.write(document)

        return document

    def retrieve_document(self):
        discovery_service_url = self.build_params.get(
            'discovery_service_url', DISCOVERY_URI)

        document = retrieve_discovery_doc(
            self.service_name,
            self.version,
            http=self.build_params.get('http'),
            discovery_service_url=discovery_service_url
        )
        _logger.debug('Discovery doc for {} {} retrieved'.format(
            self.service_name, self.version))
        return document

    def build_service(self):
        return build_from_document(self.document, **self.build_params)
