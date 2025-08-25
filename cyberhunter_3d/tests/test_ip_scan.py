import unittest
from unittest.mock import patch
import sys
import os
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.reconnaissance.ip_scan import parse_nmap_xml, scan_ip_target

# Sample nmap XML output for testing
SAMPLE_NMAP_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE nmaprun>
<nmaprun scanner="nmap" start="1678886400" version="7.91">
  <host starttime="1678886401" endtime="1678886405">
    <status state="up" reason="user-set"/>
    <address addr="127.0.0.1" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open" reason="syn-ack"/>
        <service name="ssh" product="OpenSSH" version="8.2p1" method="probed" conf="10"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open" reason="syn-ack"/>
        <service name="http" product="Apache httpd" version="2.4.41" method="probed" conf="10"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="closed" reason="reset"/>
        <service name="https" method="table" conf="3"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""

class TestIpScan(unittest.TestCase):

    def test_parse_nmap_xml(self):
        parsed_data = parse_nmap_xml(SAMPLE_NMAP_XML.strip())
        self.assertEqual(len(parsed_data), 1)
        host = parsed_data[0]
        self.assertEqual(host['ip'], '127.0.0.1')
        self.assertEqual(len(host['ports']), 3)

        # Check port 22
        port1 = host['ports'][0]
        self.assertEqual(port1['portid'], '22')
        self.assertEqual(port1['state'], 'open')
        self.assertEqual(port1['service_product'], 'OpenSSH')
        self.assertEqual(port1['service_version'], '8.2p1')

        # Check port 80
        port2 = host['ports'][1]
        self.assertEqual(port2['portid'], '80')
        self.assertEqual(port2['state'], 'open')
        self.assertEqual(port2['service_product'], 'Apache httpd')

        # Check port 443
        port3 = host['ports'][2]
        self.assertEqual(port3['portid'], '443')
        self.assertEqual(port3['state'], 'closed')

    @patch('cyberhunter_3d.core.reconnaissance.ip_scan.subprocess.run')
    def test_scan_ip_target_success(self, mock_subprocess_run):
        # Mock the subprocess call to return the sample XML
        mock_subprocess_run.return_value.stdout = SAMPLE_NMAP_XML
        mock_subprocess_run.return_value.stderr = ""

        assets = scan_ip_target("127.0.0.1")

        # Check that nmap was called correctly
        mock_subprocess_run.assert_called_once_with(
            ['nmap', '-sV', '-oX', '-', '127.0.0.1'],
            capture_output=True, text=True, check=True
        )

        # Check that the output is parsed into the correct structure
        self.assertEqual(len(assets), 1)
        asset = assets[0]
        self.assertEqual(asset['type'], 'host_with_open_ports')
        self.assertEqual(asset['value'], '127.0.0.1')
        self.assertIn('ports', asset['details'])
        # Only open ports should be included
        self.assertEqual(len(asset['details']['ports']), 2)
        self.assertEqual(asset['details']['ports'][0]['portid'], '22')

    @patch('cyberhunter_3d.core.reconnaissance.ip_scan.subprocess.run')
    def test_scan_ip_target_nmap_error(self, mock_subprocess_run):
        # Mock a failed subprocess call
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "nmap", stderr="Some nmap error")

        assets = scan_ip_target("127.0.0.1")
        self.assertEqual(assets, [])

if __name__ == '__main__':
    unittest.main()
