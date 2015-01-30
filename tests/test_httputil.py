import unittest

import mock
import requests
import httplib2
import googleapiclient.errors

from rtrss.filestorage import httputil


class HttpUtilTestCase(unittest.TestCase):
    def test_is_retryable_returns_false_on_random_exception(self):
        exc = Exception
        self.assertFalse(httputil.is_retryable(exc))

    def test_is_retryable_returns_false_on_requests_404(self):
        resp = requests.Response()
        resp.status_code = 404
        exc = requests.RequestException(response=resp)
        self.assertFalse(httputil.is_retryable(exc))

    def test_is_retryable_returns_true_on_requests_500(self):
        resp = requests.Response()
        resp.status_code = 500
        exc = requests.RequestException(response=resp)
        self.assertTrue(httputil.is_retryable(exc))

    def test_is_retryable_returns_false_on_httplib2_404(self):
        resp = httplib2.Response({'status': 404})
        exc = googleapiclient.errors.HttpError(resp, '')
        self.assertFalse(httputil.is_retryable(exc))

    def test_is_retryable_returns_true_on_httplib2_500(self):
        resp = httplib2.Response({'status': 500})
        exc = googleapiclient.errors.HttpError(resp, '')
        self.assertTrue(httputil.is_retryable(exc))

    def test_retry_on_exception_retries(self):
        exc = Exception('Boo!')
        func = mock.Mock(side_effect=exc)
        retry_count = 3

        decorated = httputil.retry_on_exception(
            retryable=lambda e: True,
            tries=retry_count,
            delay=0.01)(func)

        try:
            decorated()
        except type(exc):
            pass
        expected = [mock.call() for i in range(retry_count)]
        self.assertEqual(func.call_args_list, expected)
