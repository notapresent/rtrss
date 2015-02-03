import os
import tempfile
from . import RTRSSTestCase
from rtrss import caching


class CachingTestCase(RTRSSTestCase):
    def test_open_for_atomic_write_writes(self):
        test_data = 'test'
        fh, fn = tempfile.mkstemp()
        os.close(fh)
        with caching.open_for_atomic_write(fn) as f:
            f.write(test_data)

        with open(fn) as f:
            data = f.read()

        self.assertEqual(test_data, data)
        os.remove(fn)
