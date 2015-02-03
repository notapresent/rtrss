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
        tf = torrentfile.TorrentFile(None)
        tf.decoded = testdata
        self.assertEqual(encoded_testdata, tf.encoded)

    def test_torrentfile_raises_valueerror_on_invalid_data(self):
        tf = torrentfile.TorrentFile('invalid data')
        with self.assertRaises(ValueError):
            _ = tf.decoded

    def test_remove_announcers_with_passkeys_removes(self):
        pass  # TODO

    def test_add_anouncer_adds_anouncer(self):
        tf = torrentfile.TorrentFile(encoded_testdata)
        test_announcer = 'some random announcer string'
        tf.add_announcer(test_announcer)

        self.assertEqual(tf._decoded['announce'], test_announcer)
        self.assertIn([test_announcer], tf._decoded['announce-list'])

