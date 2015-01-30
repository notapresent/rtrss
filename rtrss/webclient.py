# -*- coding: utf-8 -*-
import logging
import time

import requests
from requests.utils import cookiejar_from_dict, dict_from_cookiejar

from rtrss.util import save_debug_file
from rtrss.exceptions import (OperationInterruptedException,
                              CaptchaRequiredException, TorrentFileException,
                              DownloadLimitException)


FEED_URL = 'http://feed.{host}/atom/f/{category_id}.atom'
TOPIC_URL = 'http://{host}/forum/viewtopic.php?t={topic_id}'
TORRENT_URL = 'http://dl.{host}/forum/dl.php?t={topic_id}'
LOGIN_URL = 'http://login.{host}/forum/login.php'
MAP_URL = 'http://{host}/forum/index.php?map=1'
SUBFORUM_URL = 'http://{host}/forum/viewforum.php?f={id}'
SEARCH_URL = 'http://{host}/forum/tracker.php?f={cid}'


# if this string is in server response then user is logged in
LOGGED_IN_STR = u'Вы зашли как: &nbsp;<a href="./profile.php?mode='\
    u'viewprofile&amp;u={user_id}"><b class="med">{username}'

# Time between page download requests (seconds)
PAGE_DOWNLOAD_DELAY = 0.5

# Time between torrent file download requests (seconds)
TORRENT_DOWNLOAD_DELAY = 5

# Time between search requests (seconds)
SEARCH_DELAY = 1.8

DL_LIMIT_MSG = u'Вы уже исчерпали суточный лимит скачиваний торрент-файлов'

CAPTCHA_STR = u'<img src="http://static.{host}/captcha/'

MAINTENANCE_MSG = u'Форум временно отключен на профилактические работы'

REQUEST_TIMEOUT = 15

_logger = logging.getLogger(__name__)


def is_text_response(response):
    return 'text' in response.headers.get('content-type', '')


def detect_cp1251_encoding(response):
    cp1251_marker = '<meta charset="windows-1251">'
    if is_text_response(response) and cp1251_marker in response.content:
        return 'windows-1251'
    else:
        return response.encoding


class WebClient(object):
    def __init__(self, config, user=None):
        self.config = config
        self.session = requests.Session()
        self.user = user

        if user:
            self.set_user(user)

    def get_feed(self, cid=0):
        url = FEED_URL.format(host=self.config.TRACKER_HOST, category_id=cid)
        return self.request(url).content

    def request(self, url, method='get', **kwargs):
        if 'timeout' not in kwargs:
            kwargs['timeout'] = REQUEST_TIMEOUT
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.warn('url:%s Request failed  %s', url, e)
            raise OperationInterruptedException(str(e))

        response.is_text = is_text_response(response)

        # Detect windows-1251 encoding
        if response.is_text:
            response.encoding = detect_cp1251_encoding(response)

        if response.is_text and MAINTENANCE_MSG in response.text:
            raise OperationInterruptedException('Tracker maintenance')

        return response

    def authorized_request(self, url, method='get', **kwargs):
        response = self.request(url, method, **kwargs)

        if response.is_text and not self.is_signed_in(response.text):
            msg = '{} not signed in while requesting {}, retrying'.format(
                self.user, url)
            _logger.debug(msg)

            if self.config.DEBUG:
                filename = '{}-signin-retry.html'.format(self.user.id)
                save_debug_file(filename, response.content)

            self.sign_in(self.user)
            time.sleep(PAGE_DOWNLOAD_DELAY)
            response = self.request(url, method, **kwargs)

        return response

    def get_topic(self, tid):
        url = TOPIC_URL.format(host=self.config.TRACKER_HOST, topic_id=tid)
        time.sleep(PAGE_DOWNLOAD_DELAY)
        return self.authorized_request(url).text

    def get_torrent(self, torrent_id):
        """Download torrent file or raise an exception"""
        url = TORRENT_URL.format(host=self.config.TRACKER_HOST,
                                 topic_id=torrent_id)

        cookies = {'bb_dl': str(torrent_id)}
        response = self.authorized_request(url, 'post', cookies=cookies)

        if 'application/x-bittorrent' in response.headers['content-type']:
            time.sleep(TORRENT_DOWNLOAD_DELAY)
            return response.content

        # Something went wrong
        if DL_LIMIT_MSG in response.text:
            msg = '{} exceeded download quota'.format(self.user)
            _logger.error(msg)

            if self.config.DEBUG:
                filename = '{}-quota-exceeded-{}.html'.format(
                    self.user.id, torrent_id)
                save_debug_file(filename, response.content)

            raise DownloadLimitException(msg)

        msg = '{} failed to download torrent {} @ {}'.format(
            self.user, torrent_id, url)
        _logger.error(msg)

        if self.config.DEBUG:
            filename = 'failed-torrent-{}.html'.format(torrent_id)
            save_debug_file(filename, response.content)

        raise TorrentFileException(msg)

    def is_signed_in(self, html):
        search_str = LOGGED_IN_STR.format(user_id=self.user.id,
                                          username=self.user.username)
        return search_str in html

    def set_user(self, user):
        if user.cookies:
            self.session.cookies = cookiejar_from_dict(user.cookies)
        else:
            self.sign_in(user)

    def sign_in(self, user):
        login_url = LOGIN_URL.format(host=self.config.TRACKER_HOST)
        post_data = {'login_username': user.username,
                     'login_password': user.password,
                     'login': '%C2%F5%EE%E4'}

        time.sleep(PAGE_DOWNLOAD_DELAY)
        response = self.request(login_url, 'post', data=post_data)
        html = response.text

        if self.is_signed_in(html):
            _logger.debug('User %s signed in', self.user)
            user.cookies = dict_from_cookiejar(self.session.cookies)

        elif CAPTCHA_STR.format(host=self.config.TRACKER_HOST) in html:
            _logger.error('Captcha request during %s sign in', self.user)
            raise CaptchaRequiredException

        else:
            message = "User {} failed to sign in".format(self.user)

            if self.config.DEBUG:
                filename = 'user-signin-{}.html'.format(user.id)
                save_debug_file(filename, response.content)

            raise OperationInterruptedException(message)

    def get_category_map(self):
        url = MAP_URL.format(host=self.config.TRACKER_HOST)
        time.sleep(PAGE_DOWNLOAD_DELAY)
        return self.authorized_request(url).text

    def get_forum_page(self, fid):
        url = SUBFORUM_URL.format(host=self.config.TRACKER_HOST, id=fid)
        time.sleep(PAGE_DOWNLOAD_DELAY)
        return self.authorized_request(url).text

    def find_torrents(self, cid=None):
        form_data = {
            'prev_my': 0,
            'prev_new': 0,
            'prev_oop': 0,
            'f[]': cid or -1,  # category id
            'o': 1,         # sort field
            's': 2,         # sort order ascending/descending
            'tm': -1,       # timespan
            'pn': '',       # author name
            'nm': '',       # title
            'oop': 1        # only open
        }
        url = SEARCH_URL.format(host=self.config.TRACKER_HOST, cid=cid or '')
        time.sleep(SEARCH_DELAY)
        return self.authorized_request(url, 'post', data=form_data).text
