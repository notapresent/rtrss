import unittest
import os
import time

from testfixtures import TempDirectory
from mock import MagicMock, patch

from rtrss.storage.servicebuilder import (
    CachedServiceBuilder, retrieve_discovery_doc, DISCOVERY_DOC_MAX_AGE
)


class RetrieveDiscoveryDocTestCase(unittest.TestCase):
    service_name = 'test-service-name'
    version = 'v1'
    discovery_url = 'https://exampe.com/{api}/{apiVersion}/'

    @patch('rtrss.storage.servicebuilder.json')
    def test_builds_right_url(self, _):
        expected_url = self.discovery_url.format(
            api=self.service_name, apiVersion=self.version)

        http = MagicMock(
            request=MagicMock(
                return_value=(MagicMock(status=200), MagicMock())
            )
        )
        _ = retrieve_discovery_doc(
            self.service_name,
            self.version,
            discovery_service_url=self.discovery_url,
            http=http
        )

        http.request.assert_called_once_with(expected_url)

    def test_raises_on_status_400(self):
        from rtrss.storage.servicebuilder import HttpError

        http = MagicMock(
            request=MagicMock(
                return_value=(MagicMock(status=400), MagicMock())
            )
        )

        with self.assertRaises(HttpError):
            _ = retrieve_discovery_doc(
                self.service_name,
                self.version,
                discovery_service_url=self.discovery_url,
                http=http
            )

    @patch('rtrss.storage.servicebuilder.json')
    def test_calls_json_loads(self, json):
        content = MagicMock()
        http = MagicMock(
            request=MagicMock(
                return_value=(MagicMock(status=200), content)
            )
        )

        _ = retrieve_discovery_doc(
            self.service_name,
            self.version,
            discovery_service_url=self.discovery_url,
            http=http
        )

        json.loads.assert_called_once_with(content)

    @patch('rtrss.storage.servicebuilder.json')
    def test_returns_content(self, json):
        content = 'some random string'
        http = MagicMock(
            request=MagicMock(
                return_value=(MagicMock(status=200), content)
            )
        )

        result = retrieve_discovery_doc(
            self.service_name,
            self.version,
            discovery_service_url=self.discovery_url,
            http=http
        )

        self.assertEqual(content, result)

    def test_raises_on_invalid_json(self):
        from rtrss.storage.servicebuilder import InvalidJsonError

        content = 'some invalid json'
        http = MagicMock(
            request=MagicMock(
                return_value=(MagicMock(status=200), content)
            )
        )

        with self.assertRaises(InvalidJsonError):
            retrieve_discovery_doc(
                self.service_name,
                self.version,
                discovery_service_url=self.discovery_url,
                http=http
            )


class CachedServiceBuilderTestCase(unittest.TestCase):
    service_name = 'test-service-name'
    version = 'v1'
    filename = 'test-file.json'

    def setUp(self):
        self.dir = TempDirectory()
        self.dirpath = self.dir.path
        self.filepath = os.path.join(self.dirpath, self.filename)
        self.builder = CachedServiceBuilder(self.filepath, self.service_name,
                                            self.version)

    def tearDown(self):
        self.dir.cleanup()

    def test_expired_returns_false(self):
        self.dir.write(self.filename, 'content')
        self.assertFalse(self.builder.expired())

    def test_expired_returns_true(self):
        path = self.dir.write(self.filename, 'test content')
        past = int(time.time() - DISCOVERY_DOC_MAX_AGE.total_seconds() - 10)
        os.utime(path, (past, past))
        self.assertTrue(self.builder.expired())

    @patch('rtrss.storage.servicebuilder.build_from_document')
    @patch('rtrss.storage.servicebuilder.CachedServiceBuilder.document')
    def test_build_calls_build_from_document(self, document, bfd):
        _ = self.builder.build_service()
        bfd.assert_called_once_with(document)

    @patch('rtrss.storage.servicebuilder.DISCOVERY_URI')
    @patch('rtrss.storage.servicebuilder.retrieve_discovery_doc')
    def test_retrieve_document_calls_retrieve(self, rtd, discovery_url):
        _ = self.builder.retrieve_document()
        rtd.assert_called_once_with(self.service_name, self.version, http=None,
                                    discovery_service_url=discovery_url)

    def test_document_returns_file_contents(self):
        test_data = 'random test'
        self.dir.write(self.filename, test_data)
        self.assertEqual(test_data, self.builder.document)

    @patch('rtrss.storage.servicebuilder.retrieve_discovery_doc')
    def test_document_calls_retrieve_if_no_file(self, rtd):
        rtd.return_value = ''
        _ = self.builder.document
        rtd.assert_called_once()

    @patch('rtrss.storage.servicebuilder.retrieve_discovery_doc')
    def test_document_calls_retrieve_if_expired(self, rtd):
        rtd.return_value = ''
        path = self.dir.write(self.filename, 'test content')
        past = int(time.time() - DISCOVERY_DOC_MAX_AGE.total_seconds() - 10)
        os.utime(path, (past, past))
        _ = self.builder.document
        rtd.assert_called_once()

    @patch('rtrss.storage.servicebuilder.retrieve_discovery_doc')
    def test_document_saves_content_to_file(self, rtd):
        test_content = rtd.return_value = 'test content'
        _ = self.builder.document
        self.assertEqual(test_content, self.dir.read(self.filename))
