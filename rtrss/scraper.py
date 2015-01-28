# -*- coding: utf-8 -*-
import logging
import datetime
import hashlib

import bencode
from dateutil import parser as dateparser
import pytz
from lxml import etree

from rtrss.exceptions import TopicException, ItemProcessingFailedException
from rtrss.webclient import WebClient
from rtrss.util import save_debug_file


_logger = logging.getLogger(__name__)

# Tracker time is 1 hour early for some reason
TRACKER_TIMEFIX = datetime.timedelta(hours=1)

# This string in topic title marks updated torrents
UPDATED_MARKER = u'[Обновлено]'

# Section with this title contains private forums, we don't need
PRIVATE_SECTION_TITLE = u'Приватные форумы'

TOPIC_STOPLIST = [
    u'Раздача ожидает проверки модератором',
    u'Раздача имеет статус: <b>не оформлено</b><br><br>Скачивание запрещено',
    u'Тема не найдена'
]


def make_tree(html, encoding='utf-8'):
    parser = etree.HTMLParser(encoding=encoding)
    tree = etree.fromstring(html, parser=parser)
    return tree


def jointext(elem):
    """Joins text from element and all its sub-elements"""
    return elem.text + ''.join(e.text for e in elem.iterdescendants())


class Scraper(object):
    def __init__(self, config):
        self.config = config

    def get_latest_topics(self):
        """Parses ATOM feed, returns topic_id:dict(topic)"""
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

        updated_raw = dateparser.parse(entry.find('updated').text)
        updated_at = updated_raw + TRACKER_TIMEFIX

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

        for msg in TOPIC_STOPLIST:
            if msg in html:
                raise TopicException('Skipping topic {} because of {}'.format(
                    tid, msg.encode('utf-8')))

        infohash, catlinks = self.parse_topic(html)

        if not catlinks:
            msg = 'Failed to parse categories for topic {}'.format(tid)
            raise TopicException(msg)

        categories = self.parse_categories(catlinks)
        if not categories:
            src = ''.join([etree.tostring(l) for l in catlinks])
            msg = 'Failed to parse categories in topic {}: {}'.format(tid, src)
            raise TopicException(msg)

        return dict({
            'infohash': infohash,
            'categories': categories
        })

    def parse_topic(self, html):
        tree = make_tree(html)
        hashspans = tree.xpath('//span[@id="tor-hash"]')
        infohash = hashspans[0].text if hashspans else None
        torrentlinks = tree.xpath('//a[@class="dl-stub dl-link"]')

        if not torrentlinks:
            infohash = None

        catlinks = tree.xpath('//*[@class="nav w100 pad_2"]/a')
        return infohash, catlinks

    def parse_categories(self, links):
        """Maked list of parsed categories from list of etree.Elements"""

        result = [self.parse_category(link) for link in links]
        return result

    def parse_category(self, c):
        href = c.get('href', '').strip('./')

        if href == 'index.php':     # Root category
            return dict({
                'tracker_id': 0,
                'title': u'Все разделы',
                'is_subforum': False,
            })

        if not href or '?' not in href or '=' not in href:
            msg = "Can't parse breadcrumb link {}".format(etree.tostring(c))
            raise TopicException(msg)

        param, tracker_id = href.split('?')[1].split('=')

        return dict({
            'tracker_id': int(tracker_id),
            'title': c.text,
            'is_subforum': param == 'f',
        })

    def get_torrent(self, tid, user):
        wc = WebClient(self.config, user)
        bindata = wc.get_torrent(tid)

        try:
            decoded = bencode.bdecode(bindata)

        except bencode.BTFailure as e:
            message = "Failed to decode torrent {}: {}".format(tid, str(e))
            _logger.error(message)
            if self.config.DEBUG:
                save_debug_file('{}-failed.torrent'.format(tid), bindata)
            raise TopicException(message)

        processed = process_torrent(decoded)
        torrent_dict = dict({
            'download_size': calculate_download_size(processed['info']),
            'infohash': calculate_infohash(processed['info']),
            'torrentfile': bencode.bencode(processed)
        })

        return torrent_dict

    def get_forum_ids(self, user):
        """Return list of ids for all forums found in tracker map"""
        wc = WebClient(self.config, user)
        html = wc.get_category_map()
        return self.parse_category_map(html)

    def parse_category_map(self, html):
        tree = make_tree(html)
        sections = tree.xpath('//*/ul[@class="tree-root"]')
        result = list()
        for section in sections:
            section_title = section.find('li/span/span').attrib.get('title')

            # Skip private forums
            if section_title == PRIVATE_SECTION_TITLE:
                continue

            hrefs = [a.attrib.get('href') for a in section.findall('.//a')]
            result.extend([int(h) for h in hrefs if h.isdigit()])

        return result

    def get_forum_page_navlinks(self, html):
        """Parse forum page and return list of links from breadcrumb"""
        tree = make_tree(html)
        links = tree.xpath('//*[@class="nav nav-top w100 pad_2"]/a')
        return links

    def get_forum_categories(self, forum_id, user):
        wc = WebClient(self.config, user)
        html = wc.get_forum_page(forum_id)
        links = self.get_forum_page_navlinks(html)

        if not links:
            msg = "Can't get categories for {}".format(forum_id)
            raise ItemProcessingFailedException(msg)

        if len(links) == 1:
            dump = etree.tostring(links[0])
            msg = "Can't get parents for forum {}: {}".format(forum_id, dump)
            raise ItemProcessingFailedException(msg)

        return self.parse_categories(links)

    def find_torrents(self, user, category_id=None):
        wc = WebClient(self.config, user)
        html = wc.find_torrents(category_id)
        return self.parse_search_results(html)

    def parse_search_results(self, html):
        tree = make_tree(html)
        row_xpath = '//*/table[@id="tor-tbl"]/tbody/tr[@class="tCenter hl-tr"]'
        rows = tree.xpath(row_xpath)
        if rows:
            return [self.parse_search_row(row) for row in rows]
        else:
            return []

    def parse_search_row(self, row):
        topic = row.find('td[4]/div/a[@data-topic_id]')

        if topic is None:
            html = etree.tostring(row)
            msg = 'Failed to parse search row: {}'.format(html)
            raise ItemProcessingFailedException(msg)

        topic_id = int(topic.attrib['href'].split('=')[1])
        title = jointext(topic)
        cat_id = row.find('td[3]/*/a').attrib['href'].split('=')[1]

        author_id = row.find('td[5]/*/a').attrib['href'].split('=')[1]
        author_name = row.find('td[5]/*/a').text

        size = row.find('td[6]/u').text
        updated_ts = int(row.find('td[10]/u').text)
        local_tz = pytz.timezone(self.config.TZNAME)
        updated_at = datetime.datetime.fromtimestamp(updated_ts, local_tz)
        updated_at = updated_at + TRACKER_TIMEFIX
        updated_at = updated_at.astimezone(pytz.utc).replace(tzinfo=None)

        tdict = dict({
            'id': topic_id,
            'category_id': int(cat_id),
            'title': title,

            'author_id': int(author_id),
            'author_name': author_name,

            'size': int(size),
            'updated_at': updated_at
        })

        return tdict


def calculate_infohash(info):
    """Calculates torrent infohash from decoded info section"""
    return hashlib.sha1(bencode.bencode(info)).hexdigest()


def calculate_download_size(info):
    """Calculates torrent size from decoded info section"""
    length = info.get('length', 0)
    if length:
        return length

    for entry in info['files']:
        length += entry['length']

    return length


def process_torrent(decoded):
    """Remove all announce urls with user passkey"""
    decoded.pop('announce', None)
    ann_list = decoded['announce-list']
    decoded['announce-list'] = filter(lambda a: '?uk=' not in a[0], ann_list)
    return decoded
