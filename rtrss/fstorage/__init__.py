'''File storage for torrent files, with several backends'''
import urlparse
from rtrss.fstorage import gcsfs, dirfs


def make_storage(config):
    '''Return file storage based on url scheme'''
    uri = config.FILESTORAGE_URL
    parsed = urlparse.urlparse(uri)

    if parsed.scheme == 'gs':
        return gcsfs.GCSFileStorage(config)

    elif parsed.scheme == 'file':
        return dirfs.DirectoryFileStorage(config)

    else:
        raise ValueError('Invalid storage URL: {}'.format(uri))
