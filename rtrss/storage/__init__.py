"""File storage for torrent files, with several backends"""

import urlparse
import os

from rtrss.storage import gcs, localdirectory
from rtrss.storage.util import download_and_save_keyfile


def make_storage(storage_settings, data_path):
    """Return file storage based on url scheme"""
    parsed = urlparse.urlparse(storage_settings['URL'])

    if parsed.scheme == 'gs':
        bucket = parsed.netloc
        prefix = parsed.path
        keyfile_url = storage_settings.pop('PRIVATEKEY_URL')
        keyfile_path = os.path.join(
            data_path,
            'google-storage-privatekey-{}.json'.format(hash(keyfile_url))
        )

        if not os.path.isfile(keyfile_path):
            download_and_save_keyfile(keyfile_url, keyfile_path)

        return gcs.GCSStorage(bucket, prefix, keyfile_path)

    elif parsed.scheme == 'file':
        dirname = parsed.path.rstrip('/')
        return localdirectory.LocalDirectoryStorage(dirname)

    else:
        raise ValueError('Invalid URL: {}'.format(storage_settings['URL']))



