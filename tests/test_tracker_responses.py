import os
import unittest
from tests import AttrDict
from rtrss import scraper


@unittest.skipIf(not os.environ.get('TEST_TRACKER_RESPOPNSES'), 
                 'Skipping tracker response tests by default')
class TrackerResponseTestCase(unittest.TestCase):
    def test_latest_topics(self):
        cfg = AttrDict({'TRACKER_HOST': 'rutracker.org'})
        s = scraper.Scraper(cfg)
        self.assertIsInstance(s.get_latest_topics(), dict)
