import unittest
import os

from testfixtures import TempDirectory
from mock import MagicMock, patch, call
import requests
import httplib2
import googleapiclient.errors

from tests import AttrDict
from rtrss.storage import util


class HttpUtilTestCase(unittest.TestCase):
    def test_is_retryable_returns_false_on_random_exception(self):
        exc = Exception
        self.assertFalse(util.is_retryable(exc))

    def test_is_retryable_returns_false_on_requests_404(self):
        resp = requests.Response()
        resp.status_code = 404
        exc = requests.RequestException(response=resp)
        self.assertFalse(util.is_retryable(exc))

    def test_is_retryable_returns_true_on_requests_500(self):
        resp = requests.Response()
        resp.status_code = 500
        exc = requests.RequestException(response=resp)
        self.assertTrue(util.is_retryable(exc))

    def test_is_retryable_returns_false_on_httplib2_404(self):
        resp = httplib2.Response({'status': 404})
        exc = googleapiclient.errors.HttpError(resp, '')
        self.assertFalse(util.is_retryable(exc))

    def test_is_retryable_returns_true_on_httplib2_500(self):
        resp = httplib2.Response({'status': 500})
        exc = googleapiclient.errors.HttpError(resp, '')
        self.assertTrue(util.is_retryable(exc))

    def test_retry_on_exception_retries(self):
        exc = Exception('Boo!')
        func = MagicMock(side_effect=exc)
        retry_count = 3

        decorated = util.retry_on_exception(
            retryable=lambda e: True,
            tries=retry_count,
            delay=0.01)(func)

        try:
            decorated()
        except type(exc):
            pass
        expected = [call() for _ in range(retry_count)]
        self.assertEqual(func.call_args_list, expected)


class LockedOpenTestCase(unittest.TestCase):
    filename = 'testfile.txt'
    test_data = 'random text'

    def setUp(self):
        self.tempdir = TempDirectory()
        self.filepath = os.path.join(self.tempdir.path, self.filename)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_returns_file_object(self):
        with util.locked_open(self.filepath, util.M_WRITE) as f:
            self.assertIsInstance(f, file)

    def test_concurrent_read(self):
        self.tempdir.write(self.filename, self.test_data)
        with util.locked_open(self.filepath, util.M_READ) as f1:
            with util.locked_open(self.filepath, util.M_READ) as f2:
                self.assertEqual(self.test_data, f1.read())
                self.assertEqual(self.test_data, f2.read())

    def test_non_blocking_read_during_write_raises(self):
        with util.locked_open(self.filepath, util.M_WRITE):
            with self.assertRaises(IOError):
                util.locked_open(self.filepath,
                                 util.M_READ,
                                 blocking=False).__enter__()

    def test_non_blocking_write_during_read_raises(self):
        self.tempdir.write(self.filename, self.test_data)
        with util.locked_open(self.filepath, util.M_READ):
            with self.assertRaises(IOError):
                util.locked_open(self.filepath,
                                 util.M_WRITE,
                                 blocking=False).__enter__()

    def test_read(self):
        self.tempdir.write(self.filename, self.test_data)
        with util.locked_open(self.filepath, util.M_READ) as f:
            self.assertEqual(self.test_data, f.read())

    def test_write(self):
        with util.locked_open(self.filepath, util.M_WRITE) as f:
            f.write(self.test_data)
        self.assertEqual(self.test_data, self.tempdir.read(self.filename))


class DownloadAndSaveKeyFileTestCase(unittest.TestCase):
    filename = 'testfile.txt'
    test_data = 'random text'
    url = 'test url'

    def setUp(self):
        self.dir = TempDirectory()
        self.filepath = os.path.join(self.dir.path, self.filename)

    def tearDown(self):
        self.dir.cleanup()

    @patch('rtrss.storage.util.requests.get')
    def test_calls_requests_get(self, mocked_get):
        mocked_get.return_value = AttrDict({'content': self.test_data})
        util.download_and_save_keyfile(self.url, self.filepath)
        mocked_get.assert_called_once_with(self.url)

    @patch('rtrss.storage.util.requests.get')
    def test_store_result(self, mocked_get):
        mocked_get.return_value = AttrDict({'content': self.test_data})
        util.download_and_save_keyfile(self.url, self.filepath)
        self.assertEqual(self.test_data, self.dir.read(self.filename))

