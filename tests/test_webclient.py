import unittest

from rtrss import webclient
from . import AttrDict


class WebClientTestCase(unittest.TestCase):
    def test_is_text_response_returns_true(self):
        response = AttrDict({'headers': {'content-type': 'text/plain'}})
        self.assertTrue(webclient.is_text_response(response))

    def test_is_text_response_returns_false(self):
        response = AttrDict({'headers': {'content-type': 'image/png'}})
        self.assertFalse(webclient.is_text_response(response))

    def test_detect_cp1251_encoding_returns_encoding(self):
        response = AttrDict({
            'headers': {'content-type': 'text/plain'},
            'content': '',
            'encoding': 'utf-8'
        })

        self.assertEqual(webclient.detect_cp1251_encoding(response), 'utf-8')

    def test_detect_cp1251_encoding_returns_1251(self):
        response = AttrDict({
            'headers': {'content-type': 'text/plain'},
            'content': '<meta charset="windows-1251">'
        })
        encoding = webclient.detect_cp1251_encoding(response)
        self.assertEqual(encoding, 'windows-1251')
