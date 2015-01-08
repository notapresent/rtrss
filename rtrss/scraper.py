# -*- coding: utf-8 -*-
import logging
import datetime
import bencode
from lxml import etree
from dateutil import parser
from rtrss.webclient import WebClient
from . import TopicException
from .util import save_debug_file
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
            changed = True
        else:
            changed = False

        return dict({
            'title': title.strip(),
            'id': int(id),
            'updated_at': updated_at.replace(tzinfo=None),
            'changed': changed
        })

    def get_topic(self, tid, user):
        wc = WebClient(self.config, user)
        html = wc.get_topic(tid)
        return self.parse_topic(html)

    def parse_topic(self, html):
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.fromstring(html, parser=parser)

        hashspans = tree.xpath('//span[@id="tor-hash"]')
        # torrentlinks = tree.xpath('//a[@class="dl-stub dl-link"]')
        catlinks = tree.xpath('//*[@class="nav w100 pad_2"]/a')

        return dict({
            'infohash': hashspans[0].text if hashspans else None,
            'categories': self.parse_categories(catlinks)
            # 'has_torrent': bool(torrentlinks)
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

        if href == 'index.php':     # Root category
            return dict({
                'id': 0,
                'title': u'Все разделы',
                'is_subforum': False,
            })

        if '?' not in href or '=' not in href:
            return None

        param, id = href.split('?')[1].split('=')

        return dict({
            'id': int(id),
            'title': c.text,
            'is_subforum': param == 'f',
        })


    def get_torrent(self, id, user):
        wc = WebClient(self.config, user)
        bindata = wc.get_torrent(id)
        user.downloads_today += 1

        try:
            parsed = bencode.bdecode(bindata)
        except bencode.BTL.BTFailure as e:
            _logger.error("Failed to decode torrent %d: %s", id, str(e))
            if self.config.DEBUG:
                save_debug_file('{}-failed.torrent'.format(id), bindata)
            raise TopicException(str(e))

        return self.process_torrent(parsed)

    def process_torrent(self, parsed):
        '''remove announce urls with user passkey'''
        parsed.pop('announce', None)
        annlist = parsed['announce-list']
        parsed['announce-list'] = filter(lambda a: '?uk=' not in a[0], annlist)

        return bencode.bencode(parsed)

    def get_category_ids(self, user):
        wc = WebClient(self.config, user)
        html = wc.get_category_map()
        return self.parse_category_map(html)

    def parse_category_map(self, html):
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.fromstring(html, parser=parser)
        rootdiv = tree.xpath('//div[@id="f-map"]')

        links = rootdiv[0].xpath('//*/a')
        hrefs = [l.attrib.get('href') for l in links if l.attrib.get('href')]
        ids = [int(h) for h in hrefs if h.isdigit()]
        return ids

    def parse_forum_page(self, html):
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.fromstring(html, parser=parser)
        links = tree.xpath('//*[@class="nav nav-top w100 pad_2"]/a')
        return links

    def get_forum_categories(self, id, user):
        wc = WebClient(self.config, user)
        html = wc.get_forum_page(id)
        links = self.parse_forum_page(html)
        return self.parse_categories(links)
