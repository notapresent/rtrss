import unittest

from testfixtures import TempDirectory

from tests import random_key
from rtrss.storage.localdirectory import LocalDirectoryStorage, mkdir_p


class LocalDirectoryStorageTestCase(unittest.TestCase):
    test_key = 'some random key'
    test_value = 'some random value'

    def setUp(self):
        self.dir = TempDirectory()
        self.store = LocalDirectoryStorage(self.dir.path)

    def tearDown(self):
        self.dir.cleanup()

    def test_put_stores(self):
        self.store.put(self.test_key, self.test_value)
        self.assertEqual(self.test_value, self.dir.read(self.test_key))

    def test_get_retrieves(self):
        self.dir.write(self.test_key, self.test_value)
        self.assertEqual(self.test_value, self.store.get(self.test_key))

    def test_get_returns_none_for_nonexistent(self):
        self.assertIsNone(self.store.get('some random nonexistent key'))

    def test_delete_deletes(self):
        self.dir.write(self.test_key, self.test_value)
        self.store.delete(self.test_key)
        self.assertIsNone(self.store.get(self.test_key))

    def test_delete_nonexistent_not_raises(self):
        try:
            self.store.delete('some random nonexistent key')
        except OSError as e:
            self.fail('delete("nonexistent key") raised an exception: ' % e)

    def test_key_with_slashes_creates_directories(self):
        key = 'key/with/slash'
        self.store.put(key, self.test_value)
        subdir, filename = key.rsplit('/', 1)
        self.dir.check_dir(subdir, filename)

    def test_bulk_delete_deletes_multiple(self):
        keys = []
        for _ in xrange(10):
            key = random_key()
            keys.append(key)
            self.dir.write(key, self.test_value)

        self.store.bulk_delete(keys)

        self.dir.check()

    def test_mkdir_p_creates_dir(self):
        dirname = 'test directory 1/test directory 2/test directory 3'
        mkdir_p(self.dir.getpath(dirname))
        self.dir.check_dir(dirname)

