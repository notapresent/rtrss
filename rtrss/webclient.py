# -*- coding: utf-8 -*-
import logging
import requests
import time
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
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
        return self.request('get', url).content

    def request(self, method, url, **kwargs):
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.warn('Request failed: %s', e)
            raise OperationInterruptedException(e)
        else:
            return response
        # TODO tracker maintenance should be handled here

    def get_page(self, url, auth_required=True):
        html = self.request('get', url).text
        time.sleep(PAGE_DOWNLOAD_DELAY)

        if auth_required and not self.is_signed_in(html):
            self.sign_in(self.user)
            html = self.request('get', url).text
            time.sleep(PAGE_DOWNLOAD_DELAY)

        return html

    def get_topic(self, id):
        url = TOPIC_URL.format(host=self.config.TRACKER_HOST, topic_id=id)
        return self.get_page(url)

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
        post_data = {'login_username': user.username,
                     'login_password': user.password,
                     'login': '%C2%F5%EE%E4'}

        html = self.request('post', login_url, data=post_data).text

        if self.is_signed_in(html):
            _logger.info('User %s signed in', self.user)
        else:
            message = "User {} failed to sign in".format(self.user)
            raise OperationInterruptedException(message)

# def download_torrentfile(self, tid, *args, **kwargs):
#     tfile = self.request('GET', self.torrentfile_url % tid, **kwargs)
#     if tfile:
#         self.user.downloads_today += 1
#     return tfile
