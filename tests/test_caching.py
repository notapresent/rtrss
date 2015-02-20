import os
import tempfile

from tests import TempDirTestCase
from rtrss import caching


class CachingTestCase(TempDirTestCase):
    def setUp(self):
        super(CachingTestCase, self).setUp()
        fh, self.filename = tempfile.mkstemp(dir=self.dir.path)
        os.close(fh)

    def tearDown(self):
        os.remove(self.filename)
        super(CachingTestCase, self).tearDown()

    def test_open_for_atomic_write_writes(self):
        test_data = 'test'
        with caching.open_for_atomic_write(self.filename) as f:
            f.write(test_data)
        with open(self.filename) as f:
            data = f.read()
        self.assertEqual(test_data, data)

    def test_atomic_write_really_atomic(self):
        test_data = 'test'

        with caching.open_for_atomic_write(self.filename) as f:
            f.write(test_data)
            with open(self.filename, 'w') as f1:
                f1.write('this will be overwritten')

        with open(self.filename) as f:
            data = f.read()

        self.assertEqual(test_data, data)
