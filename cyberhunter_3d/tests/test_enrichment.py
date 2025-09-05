import pytest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.enrichment.enrichment_engine import run_enrichment_engine

def create_mock_finding(target, tool, phase, status="success", evidence=None, error=None):
    return {"target": target, "phase": phase, "tool": tool, "status": status, "evidence": evidence, "error": error}

@patch('cyberhunter_3d.core.enrichment.enrichment_engine.NmapScanPlugin')
@patch('cyberhunter_3d.core.enrichment.enrichment_engine.NaabuPlugin')
@patch('cyberhunter_3d.core.enrichment.enrichment_engine.AquatonePlugin')
@patch('cyberhunter_3d.core.enrichment.enrichment_engine.GowitnessPlugin')
@patch('cyberhunter_3d.core.enrichment.enrichment_engine.HttpxPlugin')
def test_enrichment_engine_orchestration(mock_httpx, mock_gowitness, mock_aquatone, mock_naabu, mock_nmap):
    initial_subdomains = {"test.example.com"}

    mock_httpx.return_value.run.return_value = [
        create_mock_finding("http://test.example.com", "httpx", "enrichment-live-hosts", evidence={"live_url": "http://test.example.com"})
    ]
    mock_gowitness.return_value.run.return_value = [
        create_mock_finding("multiple", "gowitness", "enrichment-screenshot", evidence={"screenshot_dir": "/ss/gowitness"})
    ]
    mock_aquatone.return_value.run.return_value = []
    mock_naabu.return_value.run.return_value = [
        create_mock_finding("test.example.com", "naabu", "enrichment-portscan", evidence={"port": "80", "ip": "1.2.3.4"})
    ]
    mock_nmap.return_value.run.return_value = [
        create_mock_finding("test.example.com", "nmap-scan", "enrichment-service-scan", evidence={"port": "80", "service_info": "Apache"})
    ]

    all_findings = run_enrichment_engine(initial_subdomains)

    assert len(all_findings) == 4 # httpx, gowitness, naabu, nmap
    mock_httpx.return_value.run.assert_called_once_with(list(initial_subdomains))
    live_url_list = ["http://test.example.com"]
    mock_gowitness.return_value.run.assert_called_once_with(live_url_list)
    mock_naabu.return_value.run.assert_called_once_with(live_url_list)
    nmap_target = [{'host': 'test.example.com', 'port': '80'}]
    mock_nmap.return_value.run.assert_called_once_with(nmap_target)
