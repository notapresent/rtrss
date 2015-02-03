import os
import tempfile

from . import RTRSSTestCase
from rtrss import caching, config


class CachingTestCase(RTRSSTestCase):
    def setUp(self):
        fh, self.filename = tempfile.mkstemp(dir=config.DATA_DIR)
        os.close(fh)

    def tearDown(self):
        os.remove(self.filename)

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
