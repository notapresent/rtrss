import logging
import datetime
import pytz
from lxml import etree
from dateutil import parser
from rtrss.webclient import WebClient

_logger = logging.getLogger(__name__)


class Scraper(object):
    def __init__(self, config):
        self.config = config

    def get_latest_topics(self):
        '''Parses ATOM feed, returns list of dicts'''
        wc = WebClient(self.config)
        feed = wc.get_feed()

        # remove stupid namespace
        feed = feed.replace('xmlns="http://www.w3.org/2005/Atom"', '')

        entries = etree.fromstring(feed).findall('entry')

        result = []

        for e in entries:
            result.append(self.parse_feed_entry(e))

        return result

    def parse_feed_entry(self, entry):
        title = entry.find('title').text
        id = entry.find('link').attrib['href'].split('=')[1]
        updated_raw = parser.parse(entry.find('updated').text)

        # Timestamps in ATOM feed are 1 hour early for some reason
        fix_datetime = datetime.timedelta(hours=1)
        updated = updated_raw + fix_datetime

        return dict({
            'title': title,
            'id': int(id),
            'updated': updated.replace(tzinfo=pytz.utc)
        })
