import unittest

from sqlalchemy import create_engine

from . import DB_URL
import rtrss.database as database
from rtrss import manager


engine = create_engine(DB_URL, echo=False, client_encoding='utf8')

# Reconfigure session factory to use our test schema
database.Session.configure(bind=engine)


class DBTestCase(unittest.TestCase):
    def setUp(self):
        with database.session_scope(database.Session):
            database.clear(engine)
            database.init(engine)

    def tearDown(self):
        with database.session_scope(database.Session):
            database.clear(engine)


class ManagerTestCase(DBTestCase):
    def test_load_topics_returns_empty_(self):
        self.assertEqual(manager.load_topics([-1]), dict())
