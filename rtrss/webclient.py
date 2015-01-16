# -*- coding: utf-8 -*-
import logging
import time
import requests
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
from rtrss.util import save_debug_file
from rtrss.exceptions import (OperationInterruptedException, 
                              CaptchaRequiredException)

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
SEARCH_DELAY = 1.5

DL_LIMIT_MSG = u'Вы уже исчерпали суточный лимит скачиваний торрент-файлов'

CAPTCHA_STR = u'<img src="http://static.{host}/captcha/'

MAINTENANCE_MSG = u'Форум временно отключен на профилактические работы'

_logger = logging.getLogger(__name__)


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
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.warn('Request failed: %s', e)
            raise OperationInterruptedException(str(e))

        contenttype = response.headers.get('content-type')
        if 'text' in contenttype and MAINTENANCE_MSG in response.text:
            raise OperationInterruptedException('Tracker maintenance')

        return response

    def authorized_request(self, url, method='get', **kwargs):
        response = self.request(url, method, **kwargs)

        contenttype = response.headers.get('content-type')
        if 'text' in contenttype and not self.is_signed_in(response.text):
            self.sign_in(self.user)
            time.sleep(PAGE_DOWNLOAD_DELAY)
            response = self.request(url, method, **kwargs)

        return response

    def get_topic(self, id):
        url = TOPIC_URL.format(host=self.config.TRACKER_HOST, topic_id=id)
        time.sleep(PAGE_DOWNLOAD_DELAY)
        return self.authorized_request(url).text

    def get_torrent(self, id):
        '''Download torrent file or raise an exception'''
        url = TORRENT_URL.format(host=self.config.TRACKER_HOST, topic_id=id)
        cookies = {'bb_dl': str(id)}
        response = self.authorized_request(url, 'post', cookies=cookies)

        if 'application/x-bittorrent' in response.headers['content-type']:
            time.sleep(TORRENT_DOWNLOAD_DELAY)
            return response.content

        # Something went wrong
        if DL_LIMIT_MSG in response.text:
            _logger.error('User %s exceeded download quota', self.user)
            raise CaptchaRequiredException

        _logger.error('Failed to download torrent %s (User:%s)', id, self.user)
        raise OperationInterruptedException('Failed to download torrent')

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
        postdata = {'login_username': user.username,
                    'login_password': user.password,
                    'login': '%C2%F5%EE%E4'}

        time.sleep(PAGE_DOWNLOAD_DELAY)
        html = self.request(login_url, 'post', data=postdata).text

        if self.is_signed_in(html):
            _logger.info('User %s signed in', self.user)
            user.cookies = dict_from_cookiejar(self.session.cookies)

        elif CAPTCHA_STR.format(host=self.config.TRACKER_HOST) in html:
            _logger.error('Captcha request during user %s sign in', self.user)
            raise CaptchaRequiredException

        else:
            message = "User {} failed to sign in".format(self.user)

            if self.config.DEBUG:
                filename = 'user-signin-{}.html'.format(user.id)
                save_debug_file(filename, html.encode('windows-1251'))

            raise OperationInterruptedException(message)

    def get_category_map(self):
        url = MAP_URL.format(host=self.config.TRACKER_HOST)
        time.sleep(PAGE_DOWNLOAD_DELAY)
        return self.authorized_request(url).text

    def get_forum_page(self, id):
        url = SUBFORUM_URL.format(host=self.config.TRACKER_HOST, id=id)
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
