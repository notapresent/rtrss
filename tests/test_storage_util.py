import unittest
import os

from testfixtures import TempDirectory
import mock
import requests
import httplib2
import googleapiclient.errors

from rtrss.storage.util import locked_open, M_READ, M_WRITE
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
        func = mock.Mock(side_effect=exc)
        retry_count = 3

        decorated = util.retry_on_exception(
            retryable=lambda e: True,
            tries=retry_count,
            delay=0.01)(func)

        try:
            decorated()
        except type(exc):
            pass
        expected = [mock.call() for i in range(retry_count)]
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
        with locked_open(self.filepath, M_WRITE) as f:
            self.assertIsInstance(f, file)

    def test_concurrent_read(self):
        self.tempdir.write(self.filename, self.test_data)
        with locked_open(self.filepath, M_READ) as f1:
            with locked_open(self.filepath, M_READ) as f2:
                self.assertEqual(self.test_data, f1.read())
                self.assertEqual(self.test_data, f2.read())

    def test_non_blocking_read_during_write_raises(self):
        with locked_open(self.filepath, M_WRITE):
            with self.assertRaises(IOError):
                locked_open(self.filepath, M_READ, blocking=False).__enter__()

    def test_non_blocking_write_during_read_raises(self):
        self.tempdir.write(self.filename, self.test_data)
        with locked_open(self.filepath, M_READ):
            with self.assertRaises(IOError):
                locked_open(self.filepath, M_WRITE, blocking=False).__enter__()

    def test_read(self):
        self.tempdir.write(self.filename, self.test_data)
        with locked_open(self.filepath, M_READ) as f:
            self.assertEqual(self.test_data, f.read())

    def test_write(self):
        with locked_open(self.filepath, M_WRITE) as f:
            f.write(self.test_data)
        self.assertEqual(self.test_data, self.tempdir.read(self.filename))

