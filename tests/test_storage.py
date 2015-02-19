import unittest

from testfixtures import TempDirectory
from mock import patch

from rtrss import storage


class FileStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = TempDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def test_makestorage_returns_localdirstorage(self):
        settings = {'URL': 'file:///random directory name'}
        s = storage.make_storage(settings, self.dir.path)
        self.assertIsInstance(s, storage.localdirectory.LocalDirectoryStorage)

    @patch('rtrss.storage.download_and_save_keyfile')
    def test_makestorage_returns_GCSStorage(self, _):
        settings = {
            'URL': 'gs:///random bucket name',
            'PRIVATEKEY_URL': 'random url',
            'CLIENT_EMAIL': 'random email'
        }
        s = storage.make_storage(settings, self.dir.path)
        self.assertIsInstance(s, storage.gcs.GCSStorage)
