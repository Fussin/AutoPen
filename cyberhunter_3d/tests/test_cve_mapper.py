import pytest
from unittest.mock import patch
from cyberhunter_3d.core.plugins.impl.cve_mapper_plugin import CveMapperPlugin
from cyberhunter_3d.utils.logger import setup_logger

logger = setup_logger('test_cve_mapper.log')

@patch('cyberhunter_3d.core.plugins.impl.cve_mapper_plugin.CveMapperPlugin._query_nvd_for_cpe')
def test_map_tech_to_cves(mock_query_nvd):
    """
    Tests that _map_tech_to_cves correctly maps technologies to CVEs.
    """
    # 1. Setup
    plugin = CveMapperPlugin()

    # 2. Mock the NVD API response
    mock_nvd_response = [
        {"cve": {"id": "CVE-2021-1234"}},
        {"cve": {"id": "CVE-2021-5678"}},
    ]
    mock_query_nvd.return_value = mock_nvd_response

    # 3. Execute
    technologies = ["nginx", "apache"]
    cve_results = plugin._map_tech_to_cves(technologies)

    # 4. Assertions
    assert "nginx" in cve_results
    assert "apache" in cve_results
    assert cve_results["nginx"] == mock_nvd_response
    assert cve_results["apache"] == mock_nvd_response
    assert mock_query_nvd.call_count == 2
