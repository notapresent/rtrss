"""
Torrent file storage using Google Cloud Storage
"""
import os
import logging
import io
import threading

import httplib2
from oauth2client.client import SignedJwtAssertionCredentials
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.http import BatchHttpRequest
from googleapiclient.errors import BatchError, HttpError

from rtrss.storage.util import retry_on_exception
from rtrss.storage.credentialstorage import Storage
from rtrss.storage.servicebuilder import CachedServiceBuilder


SERVICE_NAME = 'storage'

API_VERSION = 'v1'

SCOPE = 'https://www.googleapis.com/auth/devstorage.read_write'

# Maximum number of requests in batch request
MAX_BATCH_SIZE = 1000

_logger = logging.getLogger(__name__)

service = None
credentials_store = None


class GCSStorage(object):
    def __init__(self, bucket_name, prefix, keyfile_path, client_email):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.keyfile_path = keyfile_path
        self.client_email = client_email

    @property
    def client(self):
        if service:
            return service

        with threading.Lock():
            init_credentials_store(os.path.dirname(self.keyfile_path))
            init_service(self.keyfile_path, self.client_email)
            self.ensure_bucket()

        return service

    @retry_on_exception()
    def ensure_bucket(self):
        """Ensure storage bucket exists"""
        with threading.Lock():
            self.client.buckets().get(bucket=self.bucket_name).execute()

    @retry_on_exception()
    def get(self, key):
        """
        Get file from storage. Returns file contents of None if file not exists
        """
        with threading.Lock():
            # Get Payload Data
            req = self.client.objects().get_media(
                bucket=self.bucket_name,
                object=self.prefix + key
            )

            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, req)
            done = False
            try:
                while not done:
                    status, done = downloader.next_chunk(num_retries=2)

            except HttpError as err:
                # Return None if object not found
                if err.resp.status == 404:
                    content = None
                    message = 'Object not found: {}'.format(self.prefix + key)
                    _logger.warn(message)
                else:
                    raise
            else:
                content = fh.getvalue()
        return content

    @retry_on_exception()
    def put(self, key, contents, **kwargs):
        """Put file into storage, possibly overwriting it"""
        mimetype = kwargs.get('mimetype', 'application/octet-stream')

        with threading.Lock():
            media = MediaIoBaseUpload(io.BytesIO(contents), mimetype=mimetype)

            self.client.objects().insert(
                bucket=self.bucket_name,
                name=self.prefix + key,
                media_body=media
            ).execute()

    @retry_on_exception()
    def delete(self, key):
        """Delete file from storage"""
        with threading.Lock():
            try:
                self.client.objects().delete(
                    bucket=self.bucket_name,
                    object=self.prefix + key
                ).execute()
            except HttpError as e:
                if e.resp.status == 404:
                    pass
                else:
                    raise

    def bulk_delete(self, keys):
        with threading.Lock():
            objects = [self.prefix + key for key in keys]
            for seg in segment(MAX_BATCH_SIZE, objects):
                try:
                    batch_remove(seg, self.client, None, self.bucket_name)
                except BatchError as e:
                    _logger.warn('Batch error: %s', e)
                except httplib2.HttpLib2Error as e:
                    _logger.warn('Transport error: %s', e)


def segment(size, items):
    cuts = range(0, len(items), size)
    for start, end in zip(cuts, cuts[1:]):
        yield items[start:end]
    yield items[cuts[-1]:]


def batch_remove(objects, srv, http, bucket_name):
    def cb(req_id, response, exception):
        if exception:
            _logger.warn("Request %s failed:%s", req_id, exception)

    batch = BatchHttpRequest()
    for obj in objects:
        batch.add(
            srv.objects().delete(
                bucket=bucket_name,
                object=obj
            ), callback=cb
        )
    batch.execute(http=http)


def init_credentials_store(data_dir):
    global credentials_store
    cs_filename = os.path.join(data_dir, 'stored-credentials.json')
    credentials_store = Storage(cs_filename)


def init_service(keyfile_path, client_email):
    global service
    builder = make_service_builder(keyfile_path, client_email)
    service = builder.build_service()
    _logger.debug('Google Cloud Storage service created')


def make_service_builder(keyfile_path, client_email):
    data_dir = os.path.dirname(keyfile_path)
    cdd_filename = os.path.join(
        data_dir, 'cached-discovery-document-{}-{}.json'.format(
            SERVICE_NAME, API_VERSION)
    )
    credentials = make_credentials(keyfile_path, client_email)
    http_auth = credentials.authorize(httplib2.Http())
    return CachedServiceBuilder(cdd_filename, SERVICE_NAME, API_VERSION,
                                http=http_auth)


def make_credentials(keyfile_path, client_email, store=None):
    if store is None:
        store = credentials_store

    credentials = store.get()

    if credentials is None or credentials.invalid:
        with open(keyfile_path) as f:
            private_key = f.read()

        credentials = SignedJwtAssertionCredentials(
            client_email,
            private_key,
            SCOPE
        )
        credentials.set_store(store)
        _logger.debug('Created new credentials')

    return credentials
