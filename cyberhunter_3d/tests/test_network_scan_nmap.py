import unittest
from unittest.mock import patch, MagicMock
import textwrap
from cyberhunter_3d.core.plugins.impl.network_scan_nmap import NmapScanPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestNmapScanPlugin(unittest.TestCase):

    @patch('subprocess.run')
    def test_run_nmap_scan(self, mock_subprocess_run):
        # Mock the subprocess.run call
        mock_result = MagicMock()
        mock_result.stdout = textwrap.dedent("""\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE nmaprun>
        <nmaprun scanner="nmap" args="nmap -sV -oX - -iL /tmp/tmp_nmap_targets" start="1628582400" version="7.91" xmloutputversion="1.05">
            <host>
                <address addr="127.0.0.1" addrtype="ipv4"/>
                <hostnames>
                    <hostname name="localhost" type="user"/>
                </hostnames>
                <ports>
                    <port protocol="tcp" portid="80">
                        <state state="open" reason="syn-ack" reason_ttl="0"/>
                        <service name="http" product="Apache httpd" version="2.4.41" extrainfo="(Ubuntu)" method="probed" conf="10"/>
                    </port>
                    <port protocol="tcp" portid="443">
                        <state state="open" reason="syn-ack" reason_ttl="0"/>
                        <service name="https" product="Apache httpd" version="2.4.41" extrainfo="(Ubuntu)" method="probed" conf="10"/>
                    </port>
                </ports>
            </host>
        </nmaprun>
        """)
        mock_result.stderr = ""
        mock_result.check_returncode.return_value = None
        mock_subprocess_run.return_value = mock_result

        # Setup the plugin and context
        plugin = NmapScanPlugin()
        context = ScanContext(target_domain="example.com", scan_id=1, results_dir="/tmp")
        context.set("validated_subdomains", {"localhost"})

        # Run the plugin
        plugin.run(context)

        # Assert the results
        open_ports = context.get("open_ports")
        services = context.get("services")

        self.assertIn("localhost", open_ports)
        self.assertEqual(open_ports["localhost"], [80, 443])

        self.assertIn("localhost", services)
        self.assertEqual(len(services["localhost"]), 2)
        self.assertEqual(services["localhost"][0]["port"], 80)
        self.assertEqual(services["localhost"][0]["name"], "http")
        self.assertEqual(services["localhost"][1]["port"], 443)
        self.assertEqual(services["localhost"][1]["name"], "https")

if __name__ == '__main__':
    unittest.main()
