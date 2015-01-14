import unittest
from . import MockConfig
from rtrss import scraper 


class ScraperTestCase(unittest.TestCase):
# TODO Move this to a separate test suite    
#    def test_latest_topics(self):
#        cfg = MockConfig({'TRACKER_HOST': 'rutracker.org'})
#        s = scraper.Scraper(cfg)
#        self.assertIsInstance(s.get_latest_topics(), dict)
        
    def test_make_tree_returns_etree_element(self):
        from lxml import etree
        tree = scraper.make_tree('<xml></xml>')
        self.assertIsInstance(tree, etree._Element)
