# -*- coding: utf-8 -*-
import logging
import requests
import time
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
from .util import save_debug_file
from . import OperationInterruptedException

FEED_URL = 'http://feed.{host}/atom/f/{category_id}.atom'
TOPIC_URL = 'http://{host}/forum/viewtopic.php?t={topic_id}'
TORRENT_URL = 'http://dl.{host}/forum/dl.php?t={topic_id}'
LOGIN_URL = 'http://login.{host}/forum/login.php'

# if this string is in server response then user is logged in
LOGGED_IN_STR = u'Вы зашли как: &nbsp;<a href="./profile.php?mode='\
    u'viewprofile&amp;u={user_id}"><b class="med">{username}'

# Time between page download requests (seconds)
PAGE_DOWNLOAD_DELAY = 0.5

# Time between torrent file download requests (seconds)
TORRENT_DOWNLOAD_DELAY = 5

DL_LIMIT_MSG = u'Вы уже исчерпали суточный лимит скачиваний торрент-файлов'

CAPTCHA_STR = u'<img src="http://static.{ho}/captcha/'

_logger = logging.getLogger(__name__)


class WebClient(object):
    def __init__(self, config, user=None):
        self.config = config
        self.session = requests.Session()
        self.user = user

        if user:
            self.set_user(user)

    def get_feed(self):
        url = FEED_URL.format(host=self.config.TRACKER_HOST, category_id=0)
        return self.request(url, 'get').content

    def request(self, url, method, **kwargs):
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.warn('Request failed: %s', e)
            raise OperationInterruptedException(e)
        else:
            return response
        # TODO tracker maintenance should be handled here

    def html(self, url, method='get', auth_required=True, *args, **kwargs):
        html = self.request(url, method, *args, **kwargs).text
        time.sleep(PAGE_DOWNLOAD_DELAY)

        if auth_required and not self.is_signed_in(html):
            self.sign_in(self.user)
            html = self.request(url, 'get').text
            time.sleep(PAGE_DOWNLOAD_DELAY)

        return html

    def get_topic(self, id):
        url = TOPIC_URL.format(host=self.config.TRACKER_HOST, topic_id=id)
        return self.html(url)

    def load_torrentfile(self, id):
        pass    # TODO

    def is_signed_in(self, html):
        search_str = LOGGED_IN_STR.format(user_id=self.user.id,
                                          username=self.user.username)
        return search_str in html

    def set_user(self, user):
        if user.cookies:
            self.session.cookies = cookiejar_from_dict(user.cookies)
        else:
            self.sign_in(user)
            user.cookies = dict_from_cookiejar(self.session.cookies)

    def sign_in(self, user):
        login_url = LOGIN_URL.format(host=self.config.TRACKER_HOST)
        postdata = {'login_username': user.username,
                    'login_password': user.password,
                    'login': '%C2%F5%EE%E4'}

        html = self.html(login_url, 'post', data=postdata, auth_required=False)

        if self.is_signed_in(html):
            _logger.info('User %s signed in', self.user)
        else:
            message = "User {} failed to sign in".format(self.user)

            if self.config.DEBUG:
                filename = 'user-signin-{}.html'.format(user.id)
                save_debug_file(filename, html.encode('windows-1251'))

            raise OperationInterruptedException(message)

# def download_torrentfile(self, tid, *args, **kwargs):
#     tfile = self.request('GET', self.torrentfile_url % tid, **kwargs)
#     if tfile:
#         self.user.downloads_today += 1
#     return tfile
