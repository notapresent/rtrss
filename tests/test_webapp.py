import datetime

from testfixtures import TempDirectory

from mock import patch

from tests import DatabaseTestCase
from rtrss import config
from rtrss.models import *
from rtrss.webapp import make_app
from rtrss import torrentfile


# FIXME this test suite needs refactoring
class WebAppTestCase(DatabaseTestCase):
    def setUp(self):
        super(WebAppTestCase, self).setUp()
        self.dir = TempDirectory()
        config.DATA_DIR = self.dir.path
        config.FILESTORAGE_SETTINGS = {
            'URL': 'file://{}'.format(self.dir.path)
        }
        self.app = make_app(config).test_client()

    def tearDown(self):
        self.dir.cleanup()
        super(WebAppTestCase, self).tearDown()

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

    @patch('rtrss.views.storage')
    def test_torrent_passkey_embedding(self, mock_storage):
        torrent_id = 1

        tf = torrentfile.TorrentFile({'some key': 'some value'})
        mock_storage.get.return_value = tf.encoded
        passkey = 'somerandompasskey'
        self._populate_test_db()
        rv = self.app.get('/torrent/{}?pk={}'.format(torrent_id, passkey))
        tf = torrentfile.TorrentFile(rv.data)

        self.assertIn('announce', tf.decoded)
        self.assertIn(passkey, tf.decoded['announce'])

