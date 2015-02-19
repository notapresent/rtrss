import unittest

from testfixtures import TempDirectory
from mock import patch, MagicMock

from tests import AttrDict
import rtrss.storage.gcs as gcs
from rtrss.storage.servicebuilder import CachedServiceBuilder


class GCSStorageTestCase(unittest.TestCase):
    bucket_name = 'test bucket'
    test_key = 'some random key'
    test_value = 'some random value'
    email = 'test email'
    prefix = 'test prefix'
    test_pk = 'test private key'

    def setUp(self):
        self.dir = TempDirectory()
        self.keyfile_path = self.dir.write('test key file', self.test_pk)
        # self.store = GCSStorage(
        # self.bucket_name,
        # self.prefix,
        #     self.keyfile_path,
        #     self.email
        # )

    def tearDown(self):
        self.dir.cleanup()

    def test_make_credentials_return_stored_credentials(self):
        storage = MagicMock()
        test_credentials = AttrDict({'invalid': False})
        storage.get.return_value = test_credentials
        result = gcs.make_credentials(self.keyfile_path, self.email, storage)
        self.assertEqual(test_credentials, result)

    @patch('rtrss.storage.gcs.SignedJwtAssertionCredentials')
    def test_make_credentials_creates_new_if_none(self, sjac):
        empty_storage = MagicMock()
        _ = gcs.make_credentials(self.keyfile_path, self.email, empty_storage)
        sjac.assert_called_once()

    @patch('rtrss.storage.gcs.SignedJwtAssertionCredentials')
    def test_make_credentials_creates_new_if_invalid(self, sjac):
        invalid_storage = MagicMock()
        invalid_storage.get.return_value = AttrDict({'invalid': True})
        _ = gcs.make_credentials(
            self.keyfile_path,
            self.email,
            invalid_storage
        )
        sjac.assert_called_once()

    @patch('rtrss.storage.gcs.SignedJwtAssertionCredentials')
    def test_make_credentials_sets_store(self, sjac):
        mock_credentials = sjac.return_value = MagicMock()
        mock_store = MagicMock()
        _ = gcs.make_credentials(self.keyfile_path, self.email, mock_store)
        mock_credentials.set_store.assert_called_once_with(mock_store)

    @patch('rtrss.storage.gcs.SignedJwtAssertionCredentials')
    def test_make_credentials_reads_private_key_from_file(self, sjac):
        empty_storage = MagicMock()
        _ = gcs.make_credentials(self.keyfile_path, self.email, empty_storage)
        sjac.assert_called_once_with(self.email, self.test_pk, gcs.SCOPE)

    @patch('rtrss.storage.gcs.SignedJwtAssertionCredentials')
    def test_make_credentials_returns_created_credentials(self, sjac):
        mock_credentials = sjac.return_value = MagicMock()
        result = gcs.make_credentials(
            self.keyfile_path,
            self.email,
            MagicMock()
        )
        self.assertIs(mock_credentials, result)

    @patch('rtrss.storage.gcs.Storage')
    def test_init_credentials_store_sets_store(self, mock_storage):
        mock_storage.return_value = mocked = MagicMock()
        gcs.init_credentials_store(self.dir.path)
        self.assertIs(mocked, gcs.credentials_store)

    @patch('rtrss.storage.gcs.Storage')
    def test_init_credentials_store_creates_store(self, mock_storage):
        gcs.init_credentials_store(self.dir.path)
        mock_storage.assert_called_once()

    @patch('rtrss.storage.gcs.make_service_builder')
    def test_init_service_sets_service(self, mock_make_service_builder):
        mock_builder = MagicMock()
        mock_builder.build_service.return_value = mock_service = MagicMock()
        mock_make_service_builder.return_value = mock_builder
        gcs.init_service('', '')
        self.assertIs(mock_service, gcs.service)

    def test_make_service_builder_returns_csb(self):
        result = gcs.make_service_builder(self.keyfile_path, self.email)
        self.assertIsInstance(result, CachedServiceBuilder)

    @patch('rtrss.storage.gcs.make_credentials')
    def test_make_service_builder_calls_make_credentials(self, mmc):
        _ = gcs.make_service_builder(self.keyfile_path, self.email)
        mmc.assert_called_once_with(self.keyfile_path, self.email)

    @patch('rtrss.storage.gcs.make_credentials')
    @patch('rtrss.storage.gcs.httplib2')
    def test_make_service_builder_calls_authorize(self, httplib2, mmc):
        mmc.return_value = mock_credentials = MagicMock()
        _ = gcs.make_service_builder(self.keyfile_path, self.email)
        mock_credentials.authorize.assert_called_once_with(httplib2.Http())
