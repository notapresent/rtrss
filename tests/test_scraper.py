import unittest
from . import MockConfig
from rtrss.scraper import Scraper


class ScraperTestCase(unittest.TestCase):
    def test_latest_topics(self):
        cfg = MockConfig({'TRACKER_HOST': 'rutracker.org'})
        s = Scraper(cfg)
        self.assertIsInstance(s.get_latest_topics(), dict)
