'''
Torrent file storage using Google Cloud Storage
'''
import os
import logging
import httplib2
import io
import requests
from oauth2client.client import GoogleCredentials
from googleapiclient import discovery, http
from googleapiclient.errors import HttpError
from rtrss.httputil import retry_on_exception

_logger = logging.getLogger(__name__)

API_VERSION = 'v1'

# chunk size for file downloads and uploads
CHUNKSIZE = 1024*1024

SCOPES = [
    'https://www.googleapis.com/auth/devstorage.read_write',
]

# credentials object is global
_credentials = None


@retry_on_exception()
def download_and_save_keyfile(keyfile_url, keyfile_path):
    '''Download private key file and store it or raise an exception'''
    json = requests.get(keyfile_url).text
    with open(keyfile_path, 'w') as fh:
        fh.write(json)


def _init_credentials(keyfile_url, keyfile_path):
    global _credentials
    download_and_save_keyfile(keyfile_url, keyfile_path)
    _credentials = GoogleCredentials.from_stream(keyfile_path)\
        .create_scoped(SCOPES)
    _logger.info('GCS storage credentials creatd')


class FileStorage(object):
    def __init__(self, config):
        self._client = None
        self.config = config
        self.bucket_name = config.STORAGE_SETTINGS['BUCKET_NAME']

        if _credentials is None:
            _init_credentials(config.STORAGE_SETTINGS['APIKEY_URL'],
                              os.path.join(config.DATA_DIR, 'privatekey.json'))

    @property
    def client(self):
        if self._client:
            return self._client
        else:
            httpclient = _credentials.authorize(httplib2.Http())
            _logger.info('Service authorization completed')
            self._client = discovery.build(
                'storage',
                API_VERSION,
                http=httpclient
            )
            _logger.info('API servive client created')
            return self._client

    @retry_on_exception()
    def ensure_bucket(self, bucket_name):
        '''Ensure storage bucket exists'''
        self.client.buckets().get(bucket=bucket_name).execute()

    @retry_on_exception()
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

    @retry_on_exception()
    def put(self, key, contents):
        '''Put file into storage, possibly overwriting it'''
        # The BytesIO object may be replaced with any io.Base instance.
        media = http.MediaIoBaseUpload(
            io.BytesIO(contents),
            mimetype='application/octet-stream',
            chunksize=CHUNKSIZE
        )
        self.client.objects()\
            .insert(bucket=self.bucket_name, name=key, media_body=media)\
            .execute()

    @retry_on_exception()
    def delete(self, key):
        '''Delete file from storage'''
        self.client.objects()\
            .delete(bucket=self.bucket_name, object=key)\
            .execute()
