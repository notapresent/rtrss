'''File storage for torrent files, with several backends'''
import urlparse
from rtrss.filestorage import googlecloudstorage, localdirectorystorage


def make_storage(config):
    '''Return file storage based on url scheme'''
    uri = config.FILESTORAGE_URL
    parsed = urlparse.urlparse(uri)

    if parsed.scheme == 'gs':
        return googlecloudstorage.GCSFileStorage(config)

    elif parsed.scheme == 'file':
        return localdirectorystorage.DirectoryFileStorage(config)

    else:
        raise ValueError('Invalid storage URL: {}'.format(uri))
