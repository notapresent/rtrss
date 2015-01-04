# -*- coding: utf-8 -*-
import logging
import datetime
import pytz
from lxml import etree
from dateutil import parser
from rtrss.webclient import WebClient

_logger = logging.getLogger(__name__)

# Timestamps in ATOM feed are 1 hour early for some reason
FIX_ATOM_TIMES = datetime.timedelta(hours=1)

# This string in topic title marks updated torrents
UPDATED_MARKER = u'[Обновлено]'


class Scraper(object):
    def __init__(self, config):
        self.config = config

    def get_latest_topics(self):
        '''Parses ATOM feed, returns topic_id:dict(topic)'''
        wc = WebClient(self.config)
        feed = wc.get_feed()

        # remove stupid namespace
        feed = feed.replace('xmlns="http://www.w3.org/2005/Atom"', '')
        result = dict()
        entries = etree.fromstring(feed).findall('entry')

        for e in entries:
            entry = self.parse_feed_entry(e)
            result[entry['id']] = entry

        return result

    def parse_feed_entry(self, entry):
        title = entry.find('title').text
        id = entry.find('link').attrib['href'].split('=')[1]

        updated_raw = parser.parse(entry.find('updated').text)
        updated_at = updated_raw + FIX_ATOM_TIMES

        if title[0:len(UPDATED_MARKER)] == UPDATED_MARKER:
            title = title[len(UPDATED_MARKER):]
            torrent_updated = True
        else:
            torrent_updated = False

        return dict({
            'title': title.strip(),
            'id': int(id),
            'updated_at': updated_at.replace(tzinfo=pytz.utc),
            'torrent_updated': torrent_updated
        })

    def load_topic(self, tid):
        pass

    def parse_topic(self, html):
        pass
