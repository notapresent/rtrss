from . import RTRSSDataBaseTestCase

from rtrss import manager


class ManagerTestCase(RTRSSDataBaseTestCase):
    def test_load_topics_returns_empty_(self):
        self.assertEqual(manager.load_topics([-1]), dict())
