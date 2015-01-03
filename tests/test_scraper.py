import unittest
from . import MockConfig
from rtrss.scraper import Scraper


class ScraperTestCase(unittest.TestCase):
    def testLatestTopics(self):
        s = Scraper(MockConfig(
            {'FEED_URL': 'http://feed.rutracker.org/atom/f/0.atom'}))
        self.assertIsInstance(s.get_latest_topics(), list)
