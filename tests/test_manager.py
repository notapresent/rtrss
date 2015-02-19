from tests import DatabaseTestCase

from rtrss import manager


class ManagerTestCase(DatabaseTestCase):
    def test_load_topics_returns_empty_(self):
        self.assertEqual(manager.load_topics([-1]), dict())
