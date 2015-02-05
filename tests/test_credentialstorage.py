import os

import filelock
from mock import Mock, patch

from tests import TempDirTestCase
from rtrss.filestorage.credentialstorage import Storage


class CredentialStorageTestCase(TempDirTestCase):
    def setUp(self):
        super(CredentialStorageTestCase, self).setUp()
        self.filename = 'teststorage.txt'
        self.filepath = os.path.join(self.dir.path, self.filename)
        self.storage = Storage(self.filepath)
        self.test_data = 'some random test data'

    def test_acquire_lock_not_reentrant(self):
        self.storage.acquire_lock()
        with self.assertRaises(filelock.Timeout):
            self.storage.acquire_lock(timeout=0.01)

    def test_release_unacquired_lock_raises(self):
        with self.assertRaises(RuntimeError):
            self.storage.release_lock()

    def test_locked_put_stores_data(self):
        mock_credentials = Mock()
        mock_credentials.to_json.return_value = self.test_data

        self.storage.locked_put(mock_credentials)
        self.assertEqual(self.dir.read(self.filename), self.test_data)

    def test_locked_delete_deletes(self):
        self.dir.write(self.filename, self.test_data)
        self.storage.locked_delete()
        self.assertIsNone(self.storage.locked_get())

    def test_locked_get_returns_none_for_empty_storage(self):
        self.assertIsNone(self.storage.locked_get())

    @patch('rtrss.filestorage.credentialstorage.Credentials')
    def test_locked_get_calls_new_from_json(self, mocked):
        self.dir.write(self.filename, self.test_data)
        _ = self.storage.locked_get()
        mocked.new_from_json.assert_called_once_with(self.test_data)

    @patch('rtrss.filestorage.credentialstorage.Credentials')
    def test_locked_get_calls_set_store(self, mocked):
        self.dir.write(self.filename, self.test_data)
        result = self.storage.locked_get()
        result.set_store.assert_called_once_with(self.storage)

        # def test_release_lock(self):
        # self.fail()
        #
