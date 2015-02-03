import logging
import unittest
import os

from sqlalchemy import create_engine

from rtrss import config, database


logging.disable(logging.ERROR)

engine = create_engine(config.SQLALCHEMY_DATABASE_URI,
                       echo=False,
                       client_encoding='utf8')
# Reconfigure session factory to use our test schema
database.Session.configure(bind=engine)


class AttrDict(dict):
    """Class to make mock objects"""
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class RTRSSTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.isdir(config.DATA_DIR):
            os.rmdir(config.DATA_DIR)
        os.makedirs(config.DATA_DIR)

    @classmethod
    def tearDownClass(cls):
        os.rmdir(config.DATA_DIR)


class RTRSSDataBaseTestCase(RTRSSTestCase):
    def setUp(self):
        database.clear(engine)
        database.init(engine)
        self.db = database.Session()

    def tearDown(self):
        database.clear(engine)
        self.db.close()


