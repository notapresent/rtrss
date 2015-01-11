'''
File storage
'''
import logging
import datetime
import argparse
import httplib2
import os
import io
import sys
import json
from oauth2client import service_account
from googleapiclient import discovery, http
from googleapiclient.errors import HttpError

_logger = logging.getLogger(__name__)

API_VERSION = 'v1'

CHUNKSIZE = 1024*1024

SCOPES = [
    'https://www.googleapis.com/auth/devstorage.full_control',     # TODO check if needed
    'https://www.googleapis.com/auth/devstorage.read_only',
    'https://www.googleapis.com/auth/devstorage.read_write',
]

# credentials object is shared between all instances
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


class FileStorage(object):
    def __init__(self, config):
        self.config = config
        self.bucket_name = config.STORAGE_SETTINGS['BUCKET_NAME']

        if _credentials is None:
            _init_credentials(config.STORAGE_SETTINGS['CLIENT_CREDENTIALS'])


        httpclient = _credentials.authorize(httplib2.Http())

        # Construct the service object for the interacting with the Cloud Storage API. 
        # TODO make this lazy
        self.client = discovery.build('storage', API_VERSION, http=httpclient)
        # try to get our bucket
        self.client.buckets().get(bucket=self.bucket_name).execute()
            
    def get(self, key):
        '''
        Get file from storage. Returns file contents of None if file not exists
        '''
        # Get Payload Data
        req = self.client.objects().get_media(bucket=self.bucket_name, object=key)
        # The BytesIO object may be replaced with any io.Base instance.
        fh = io.BytesIO()
        downloader = http.MediaIoBaseDownload(fh, req, chunksize=CHUNKSIZE)
        done = False

        try:
            while not done:
                status, done = downloader.next_chunk()
        except HttpError:
            content = None
        else:
            content = fh.getvalue()     # TODO return bytes, not str?
        return content

    def put(self, key, contents):
        '''Put file into storage'''
        # The BytesIO object may be replaced with any io.Base instance.
        media = http.MediaIoBaseUpload(io.BytesIO(contents), 'application/octet-stream')
        req = self.client.objects().insert(bucket=self.bucket_name, name=key, media_body=media)
        resp = req.execute()

    def delete(self, key):
        '''Delete file from storage'''
        self.client.objects().delete(bucket=self.bucket_name, object=key).execute()
