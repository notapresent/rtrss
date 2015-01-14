import unittest
from rtrss import scraper


class ScraperTestCase(unittest.TestCase):
    def test_make_tree_returns_etree_element(self):
        from lxml import etree
        tree = scraper.make_tree('<xml></xml>')
        self.assertIsInstance(tree, etree._Element)
