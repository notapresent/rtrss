import logging
import unittest
import random
import string

from testfixtures import TempDirectory

from rtrss import database


logging.disable(logging.ERROR)


class AttrDict(dict):
    """Class to make mock objects"""
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        super(TempDirTestCase, self).setUp()
        self.dir = TempDirectory()

    def tearDown(self):
        self.dir.cleanup()
        super(TempDirTestCase, self).tearDown()


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        super(DatabaseTestCase, self).setUp()
        database.clear()
        database.init()
        self.db = database.Session()

    def tearDown(self):
        self.db.close()
        database.clear()
        super(DatabaseTestCase, self).tearDown()


def random_key(length=32, allowed=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(allowed) for _ in range(length))

