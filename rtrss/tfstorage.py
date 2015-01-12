'''
Torrent file storage using Google Cloud Storage
'''
import logging
import httplib2
import io
import json
import time
from oauth2client import service_account
from googleapiclient import discovery, http
from googleapiclient.errors import HttpError

_logger = logging.getLogger(__name__)

API_VERSION = 'v1'

# chunk size for file downloads and uploads
CHUNKSIZE = 1024*1024

SCOPES = [
    'https://www.googleapis.com/auth/devstorage.read_write',
]

# Number of retries in case of API errors
NUM_RETRIES = 3

# Delay between retry attempts, seconds
RETRY_DELAY = 1

# credentials object is global
_credentials = None


def _init_credentials(config_json):
    global _credentials
    client_credentials = json.loads(config_json)
    _credentials = service_account._ServiceAccountCredentials(
        service_account_id=client_credentials['client_id'],
        service_account_email=client_credentials['client_email'],
        private_key_id=client_credentials['private_key_id'],
        private_key_pkcs8_text=client_credentials['private_key'],
        scopes=SCOPES)
    _logger.info('GCS storage credentials initialized')


def retry_on_http_error(tries=NUM_RETRIES, delay=RETRY_DELAY):
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            mtries = tries
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except HttpError as err:
                    # Reraise if non-retryable error
                    if err.resp.status not in [403, 500, 503]:
                        raise

                    _logger.warn("Retrying in %.2f seconds ...", delay)
                    time.sleep(delay)
                    mtries -= 1

            # Only one last try left
            return f(*args, **kwargs)
        return wrapped_f
    return wrap


class FileStorage(object):
    def __init__(self, config):
        self._client = None
        self.config = config
        self.bucket_name = config.STORAGE_SETTINGS['BUCKET_NAME']

        if _credentials is None:
            _init_credentials(config.STORAGE_SETTINGS['CLIENT_CREDENTIALS'])

    @property
    def client(self):
        if self._client:
            return self._client
        else:
            httpc = _credentials.authorize(httplib2.Http())
            self._client = discovery.build('storage', API_VERSION, http=httpc)
            return self._client

    @retry_on_http_error()
    def ensure_bucket(self, bucket_name):
        '''Ensure storage bucket exists'''
        self.client.buckets().get(bucket=bucket_name).execute()

    @retry_on_http_error()
    def get(self, key):
        '''
        Get file from storage. Returns file contents of None if file not exists
        '''
        # Get Payload Data
        req = self.client.objects()\
            .get_media(bucket=self.bucket_name, object=key)

        # The BytesIO object may be replaced with any io.Base instance.
        fh = io.BytesIO()
        downloader = http.MediaIoBaseDownload(fh, req, chunksize=CHUNKSIZE)
        done = False
        try:
            while not done:
                status, done = downloader.next_chunk()
        except HttpError as err:
            # Return None if object not found
            if err.resp.status == 404:
                content = None
                _logger.warn('Object not found: %s', err)
            else:       # Some other error
                raise
        else:
            content = fh.getvalue()     # TODO return bytes, not str?
        return content

    @retry_on_http_error()
    def put(self, key, contents):
        '''Put file into storage'''
        # The BytesIO object may be replaced with any io.Base instance.
        media = http.MediaIoBaseUpload(
            io.BytesIO(contents),
            mimetype='application/octet-stream',
            chunksize=CHUNKSIZE
        )
        req = self.client.objects().\
            insert(bucket=self.bucket_name, name=key, media_body=media)
        req.execute()

    @retry_on_http_error()
    def delete(self, key):
        '''Delete file from storage'''
        self.client.objects().\
            delete(bucket=self.bucket_name, object=key).\
            execute()
