import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from . import AttrDict, DB_URL
from rtrss.manager import Manager
import rtrss.database as database


engine = create_engine(DB_URL, echo=False, client_encoding='utf8')
Session = sessionmaker(bind=engine)


class DBTestCase(unittest.TestCase):
    def setUp(self):
        with database.session_scope(Session):
            database.clear(engine)
            database.init(engine)

    def tearDown(self):
        with database.session_scope(Session):
            database.clear(engine)


class ManagerTestCase(DBTestCase):
    def test_load_topics_returns_empty_(self):
        cfg = AttrDict({'SQLALCHEMY_DATABASE_URI': DB_URL})
        with database.session_scope(Session) as session:
            manager = Manager(cfg, session)
            self.assertEqual(manager.load_topics([-1]), dict())
