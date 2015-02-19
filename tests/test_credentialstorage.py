import unittest
import os

from testfixtures import TempDirectory
from mock import Mock, patch

from rtrss.storage.credentialstorage import Storage


class CredentialStorageTestCase(unittest.TestCase):
    filename = 'teststorage.txt'
    test_data = 'some random test data'

    def setUp(self):
        self.dir = TempDirectory()
        self.filepath = os.path.join(self.dir.path, self.filename)
        self.storage = Storage(self.filepath)

    def tearDown(self):
        self.dir.cleanup()

    def test_release_unacquired_lock_raises(self):
        with self.assertRaises(RuntimeError):
            self.storage.release_lock()

    def test_locked_put_stores_data(self):
        mock_credentials = Mock()
        mock_credentials.to_json.return_value = self.test_data
        self.storage.acquire_lock()
        self.storage.locked_put(mock_credentials)
        self.storage.release_lock()  # release lock to read saved data
        self.assertEqual(self.test_data, self.dir.read(self.filename))

    def test_locked_delete_deletes(self):
        self.dir.write(self.filename, self.test_data)
        self.storage.acquire_lock()
        self.storage.locked_delete()
        self.storage.release_lock()
        self.assertFalse(os.path.exists(self.filepath))

    def test_locked_get_returns_none_for_empty_storage(self):
        self.storage.acquire_lock()
        self.assertIsNone(self.storage.locked_get())
        self.storage.release_lock()

    @patch('rtrss.storage.credentialstorage.Credentials')
    def test_locked_get_calls_new_from_json_with_stored_data(self, mocked):
        self.dir.write(self.filename, self.test_data)
        self.storage.acquire_lock()
        _ = self.storage.locked_get()
        self.storage.release_lock()
        mocked.new_from_json.assert_called_once_with(self.test_data)

    @patch('rtrss.storage.credentialstorage.Credentials')
    def test_locked_get_calls_set_store(self, mocked):
        self.dir.write(self.filename, self.test_data)
        self.storage.acquire_lock()
        result = self.storage.locked_get()
        self.storage.release_lock()
        result.set_store.assert_called_once_with(self.storage)

    def test_put_doesnt_append(self):
        mock_credentials = Mock()
        mock_credentials.to_json.return_value = self.test_data
        self.storage.acquire_lock()
        self.storage.locked_put(mock_credentials)
        self.storage.locked_put(mock_credentials)
        self.storage.release_lock()
        self.assertEqual(self.test_data, self.dir.read(self.filename))
