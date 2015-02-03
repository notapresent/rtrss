import datetime

from . import RTRSSDataBaseTestCase
from rtrss import config
from rtrss.models import *
from rtrss.webapp import app
from rtrss import torrentfile
from rtrss.filestorage import make_storage


class WebAppTestCase(RTRSSDataBaseTestCase):
    def setUp(self):
        super(WebAppTestCase, self).setUp()
        self.app = app.test_client()

    def _populate_test_db(self):
        c = Category(id=0, title='Test category', tracker_id=0)
        t = Topic(id=1, title='Test topic',
                  updated_at=datetime.datetime.utcnow(), category_id=0)
        t.torrent = Torrent(infohash='testhash', size=1, tfsize=1)
        self.db.add(c)
        self.db.add(t)
        self.db.commit()

    def test_index_returns_200(self):
        rv = self.app.get('/')
        self.assertEqual(rv.status_code, 200)

    def test_feed_returns_links_with_passkey(self):
        passkey = 'somerandompasskey'
        self._populate_test_db()
        rv = self.app.get('/feed/?pk={}'.format(passkey))
        self.assertIn(passkey, rv.data)

    def test_torrent_passkey_embedding(self):
        torrent_id = 1
        tf = torrentfile.TorrentFile({'some key': 'some value'})
        storage_key = config.TORRENT_PATH_PATTERN.format(torrent_id)
        storage = make_storage(config)
        storage.put(storage_key, tf.encoded)

        passkey = 'somerandompasskey'
        self._populate_test_db()
        rv = self.app.get('/torrent/{}?pk={}'.format(torrent_id, passkey))
        tf = torrentfile.TorrentFile(rv.data)

        self.assertIn('announce', tf.decoded)
        self.assertIn(passkey, tf.decoded['announce'])

