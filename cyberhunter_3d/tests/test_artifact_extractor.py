import unittest
import codecs
import mmh3
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.artifact_extractor import ArtifactExtractorPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestArtifactExtractorPlugin(unittest.TestCase):

    def setUp(self):
        self.context = ScanContext("example.com", 1, "results")

    @patch('cyberhunter_3d.core.plugins.impl.artifact_extractor.requests.get')
    def test_extracts_ga_id_and_favicon_hash(self, mock_requests_get):
        """
        Tests that the plugin can correctly extract a Google Analytics ID and
        a favicon hash from a web page.
        """
        main_page_html = """
        <html><head>
            <link rel="icon" href="/favicon.png">
            <script>
                gtag('config', 'UA-12345678-1');
            </script>
        </head></html>
        """
        favicon_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90\wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xb3\x17\x00\x00\x00\x00IEND\xaeB`\x82'
        expected_hash = mmh3.hash(codecs.encode(favicon_content, 'base64'))

        def side_effect(url, **kwargs):
            mock_response = MagicMock()
            if "favicon.png" in url:
                mock_response.content = favicon_content
            else:
                mock_response.text = main_page_html
            mock_response.raise_for_status = MagicMock()
            return mock_response

        mock_requests_get.side_effect = side_effect

        self.context.set("live_urls_2xx", ["http://example.com"])
        plugin = ArtifactExtractorPlugin()
        plugin.run(self.context)

        artifacts = self.context.get("discovered_artifacts")
        self.assertIsNotNone(artifacts)
        self.assertIn("UA-12345678-1", artifacts["google_analytics_ids"])
        self.assertIn(str(expected_hash), artifacts["favicon_hashes"])

if __name__ == '__main__':
    unittest.main()
