import shutil
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

def parse_nmap_xml(xml_output: str) -> List[Dict[str, Any]]:
    """
    Parses the XML output from nmap and extracts host and port information.
    """
    if not xml_output:
        return []

    try:
        root = ET.fromstring(xml_output)
        hosts_data = []
        for host in root.findall('host'):
            ip_address = host.find('address').get('addr')
            ports = []
            for port in host.findall('.//port'):
                port_id = int(port.get('portid'))
                state = port.find('state').get('state')
                service_elem = port.find('service')
                service = service_elem.get('name') if service_elem is not None else 'unknown'
                product = service_elem.get('product') if service_elem is not None else ''
                version = service_elem.get('version') if service_elem is not None else ''
                ports.append({
                    'port': port_id,
                    'state': state,
                    'service': service,
                    'product': product,
                    'version': version
                })
            hosts_data.append({'ip': ip_address, 'ports': ports})
        return hosts_data
    except ET.ParseError as e:
        print(f"Error parsing nmap XML output: {e}")
        return []

class NmapPlugin(Plugin):
    """
    Nmap plugin for network scanning.
    """

    def name(self) -> str:
        return "nmap"

    def phase(self) -> str:
        return "network"

    def check_dependencies(self) -> bool:
        """
        Checks if nmap is installed.
        """
        return shutil.which("nmap") is not None

    def run(self, targets: List[str], args: List[str] = None) -> List[Dict]:
        """
        Runs nmap on a list of targets with a given set of arguments.
        """
        if not self.check_dependencies():
            print("Nmap is not installed. Please install it to use this plugin.")
            return []

        if args is None:
            # Default to a version scan with XML output
            args = ["-sV", "-oX", "-"]

        all_findings = []
        for target in targets:
            print(f"Running nmap on {target} with args: {' '.join(args)}")

            command = ["nmap"] + args + [target]

            raw_output = run_command(command)
            if raw_output:
                output_dir = f"artifacts/network/{self.name()}"
                os.makedirs(output_dir, exist_ok=True)
                safe_target_name = target.replace('/', '_').replace(':', '_')
                # Use a unique filename for each scan type
                args_str = "".join(filter(str.isalnum, "".join(args)))
                output_path = os.path.join(output_dir, f"{safe_target_name}_{args_str}.xml")
                with open(output_path, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the XML output of nmap.
        """
        findings = []
        parsed_data = parse_nmap_xml(raw_output)
        for host_data in parsed_data:
            finding: Finding = {
                "target": host_data["ip"],
                "phase": self.phase(),
                "tool": self.name(),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "evidence": {},
                "vuln": {
                    "name": "Network Service Discovered",
                    "severity": "info",
                },
                "tags": ["network", "fingerprint"],
                "fingerprints": {
                    "ports": [p["port"] for p in host_data["ports"]],
                    "services": [p for p in host_data["ports"]]
                }
            }
            findings.append(finding)
        return findings
