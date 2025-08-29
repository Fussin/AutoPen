import unittest
from unittest.mock import patch, MagicMock
import requests
from cyberhunter_3d.core.scoring.cve_mapper import get_cves_for_technology

class TestCveMapper(unittest.TestCase):

    @patch('cyberhunter_3d.core.scoring.cve_mapper.requests.get')
    def test_get_cves_for_technology_success(self, mock_get):
        """
        Test successful fetching of CVEs for a technology.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "vulnerabilities": [
                {"cve": {"id": "CVE-2021-44228"}},
                {"cve": {"id": "CVE-2021-45046"}},
            ]
        }
        mock_get.return_value = mock_response

        cves = get_cves_for_technology("log4j", "2.15.0")

        self.assertEqual(len(cves), 2)
        self.assertEqual(cves[0]['cve']['id'], "CVE-2021-44228")
        mock_get.assert_called_once()
        # Check if the version was included in the search
        self.assertIn("2.15.0", mock_get.call_args.kwargs['params']['keywordSearch'])


    @patch('cyberhunter_3d.core.scoring.cve_mapper.requests.get')
    def test_get_cves_for_technology_api_error(self, mock_get):
        """
        Test handling of an API error (e.g., 500 server error).
        """
        mock_get.side_effect = requests.exceptions.RequestException("API is down")

        cves = get_cves_for_technology("some-tech")

        self.assertEqual(cves, [])
        mock_get.assert_called_once()

if __name__ == '__main__':
    unittest.main()
