import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.cve_mapper_plugin import CveMapperPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestCveMapperPlugin(unittest.TestCase):

    @patch('cyberhunter_3d.core.plugins.impl.cve_mapper_plugin.CveMapperPlugin._query_nvd_for_cpe')
    def test_run_cve_mapper(self, mock_query_nvd):
        """
        Tests the main run method of the CveMapperPlugin.
        """
        # 1. Setup
        plugin = CveMapperPlugin()
        context = ScanContext(target_domain="example.com")
        context.set("tech_fingerprints", {
            "host1": ["nginx", "react"],
            "host2": ["apache"]
        })

        # 2. Mock the NVD API response
        mock_query_nvd.return_value = [{"cve": {"id": "CVE-2021-1234"}}]

        # 3. Execute
        plugin.run(context)

        # 4. Assertions
        cve_results = context.get("cve_results")
        self.assertIn("host1", cve_results)
        self.assertIn("host2", cve_results)
        self.assertIn("nginx", cve_results["host1"])
        self.assertEqual(mock_query_nvd.call_count, 2) # Nginx and Apache have CPEs

if __name__ == '__main__':
    unittest.main()
