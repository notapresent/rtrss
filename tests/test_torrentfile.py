import unittest

import bencode

from rtrss import torrentfile


testdata = dict({'some key': 'some value'})
encoded_testdata = bencode.bencode(testdata)


class TorrentFileTestCase(unittest.TestCase):
    def test_torrentfile_decoded_equals_encoded(self):
        tf = torrentfile.TorrentFile(encoded_testdata)
        self.assertEqual(testdata, tf.decoded)

    def test_torrentfile_encoded_equals_decoded(self):
        tf = torrentfile.TorrentFile(testdata)
        self.assertEqual(encoded_testdata, tf.encoded)

    def test_torrentfile_raises_valueerror_on_invalid_data(self):
        tf = torrentfile.TorrentFile('invalid data')
        with self.assertRaises(ValueError):
            _ = tf.decoded

    def test_remove_announcers_with_passkeys_removes(self):
        test_announcer = 'this announce url has passkey: ?uk=test'
        testdata_with_passkeys = dict({
            'announce': test_announcer,
            'announce-list': [
                [test_announcer],
                ['some other announcer']
            ]
        })
        tf = torrentfile.TorrentFile(testdata_with_passkeys)
        tf.remove_announcers_with_passkeys()
        self.assertNotIn('announce', tf.decoded)
        self.assertNotIn([test_announcer], tf.decoded['announce-list'])

    def test_add_anouncer_adds_anouncer(self):
        tf = torrentfile.TorrentFile(encoded_testdata)
        test_announcer = 'some random announcer string'
        tf.add_announcer(test_announcer)
        self.assertEqual(tf.decoded['announce'], test_announcer)
        self.assertIn([test_announcer], tf.decoded['announce-list'])

    def test_add_announce_reflected_in_encoded(self):
        tf = torrentfile.TorrentFile(testdata)
        test_announcer = 'test announcer'
        tf.add_announcer(test_announcer)
        decoded = bencode.bdecode(tf.encoded)
        self.assertIn('announce', decoded)
        self.assertEqual(test_announcer, decoded['announce'])

    def test_init_raises_valueerror(self):
        with self.assertRaises(ValueError):
            _ = torrentfile.TorrentFile(None)
