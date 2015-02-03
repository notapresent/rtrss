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
