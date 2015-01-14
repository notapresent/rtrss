import unittest
from . import AttrDict, DB_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rtrss.manager import Manager
from rtrss.database import session_scope, init_db, clear_db


engine = create_engine(DB_URL, echo=False, client_encoding='utf8')
Session = sessionmaker(bind=engine)


class DBTestCase(unittest.TestCase):
    def setUp(self):
        with session_scope(Session):
            clear_db(engine)
            init_db(engine)

    def tearDown(self):
        with session_scope(Session):
            clear_db(engine)


class ManagerTestCase(DBTestCase):
    def test_load_topics_returns_empty_(self):
        cfg = AttrDict({'SQLALCHEMY_DATABASE_URI': DB_URL})
        with session_scope(Session) as session:
            manager = Manager(cfg, session)
            self.assertEqual(manager.load_topics([-1]), dict())
