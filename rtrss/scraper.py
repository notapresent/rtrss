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

    def load_topic(self, tid, user):
        wc = WebClient(self.config, user)
        html = wc.get_topic(tid)
        return self.parse_topic(html)

    def parse_topic(self, html):
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.fromstring(html, parser=parser)

        hashspans = tree.xpath('//span[@id="tor-hash"]')
        torrentlinks = tree.xpath('//a[@class="dl-stub dl-link"]')

        if not hashspans or not torrentlinks:
            return None

        catlinks = tree.xpath('//*[@class="nav w100 pad_2"]/a')
        categories = self.parse_categories(catlinks)

        return dict({
            'infohash': hashspans[0].text,
            'categories': categories
        })

    def parse_categories(self, links):
        result = list()
        parent_id = None

        for link in links:
            parsed = self.parse_category(link)
            if parsed:
                parsed['parent_id'] = parent_id
                parent_id = parsed['id']
                result.append(parsed)
        return result

    def parse_category(self, c):
        href = c.get('href').strip('./')

        if href == 'index.php': # Root category
            return dict({
                'id': 0,
                'title': 'Root',
                'is_toplevel': True,
                'has_torrents': True
            })

        if '?' not in href or '=' not in href:
            return None

        param, id = href.split('?')[1].split('=')

        return dict({
            'id': int(id),
            'title': c.text,
            'is_toplevel': param == 'c',
            'has_torrents': True
        })

