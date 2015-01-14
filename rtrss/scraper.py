# -*- coding: utf-8 -*-
import logging
import datetime
import hashlib
import bencode
from dateutil import parser as dateparser
import pytz
from lxml import etree
from rtrss import TopicException
from rtrss.webclient import WebClient
from rtrss.util import save_debug_file

_logger = logging.getLogger(__name__)

# Tracker time is 1 hour early for some reason
TRACKER_TIMEFIX = datetime.timedelta(hours=1)

# This string in topic title marks updated torrents
UPDATED_MARKER = u'[Обновлено]'


def make_tree(html, encoding='utf-8'):
    parser = etree.HTMLParser(encoding=encoding)
    tree = etree.fromstring(html, parser=parser)
    return tree


def jointext(elem):
    '''Joins text from element and all its sub-elements'''
    return elem.text + ''.join(e.text for e in elem.iterdescendants())


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
        return self.parse_topic(html)

    def parse_topic(self, html):
        tree = make_tree(html)
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
        decoded = self.decode_torrent(bindata)
        decoded = self.process_torrent(decoded)
        return bencode.bencode(decoded)

    def decode_torrent(self, bindata):
        try:
            decoded = bencode.bdecode(bindata)
        except bencode.BTL.BTFailure as e:
            _logger.error("Failed to decode torrent %d: %s", id, str(e))
            if self.config.DEBUG:
                save_debug_file('{}-failed.torrent'.format(id), bindata)
            raise TopicException(str(e))

        return decoded

    def process_torrent(self, decoded):
        '''remove announce urls with user passkey'''
        decoded.pop('announce', None)
        annlst = decoded['announce-list']
        decoded['announce-list'] = filter(lambda a: '?uk=' not in a[0], annlst)
        return decoded

    def parse_torrent(self, bindata):
        decoded = self.decode_torrent(bindata)
        result = {
            'size': torrentsize(decoded['info']),
            'infohash': infohash(decoded['info'])
        }
        return result

    def get_category_ids(self, user):
        '''Return list of ids for all categories found in tracker map'''
        wc = WebClient(self.config, user)
        html = wc.get_category_map()
        return self.parse_category_map(html)

    def parse_category_map(self, html):
        tree = make_tree(html)
        rootdiv = tree.xpath('//div[@id="f-map"]')
        links = rootdiv[0].xpath('//*/a')
        hrefs = [l.attrib.get('href') for l in links if l.attrib.get('href')]
        ids = [int(h) for h in hrefs if h.isdigit()]
        return ids

    def parse_forum_page(self, html):
        tree = make_tree(html)
        links = tree.xpath('//*[@class="nav nav-top w100 pad_2"]/a')
        return links

    def get_forum_categories(self, id, user):
        wc = WebClient(self.config, user)
        html = wc.get_forum_page(id)
        links = self.parse_forum_page(html)
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
            print etree.tostring(row)
            raise Exception
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


def infohash(info):
    '''Calculates torrent infohash from decoded info section'''
    return hashlib.sha1(bencode.bencode(info)).hexdigest()


def torrentsize(info):
    '''Calculates torrent size from decoded info section'''
    length = info.get('length', 0)
    if length:
        return length

    for file in info['files']:
        length += file['length']

    return length
