import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

def parse_nmap_xml(xml_output: str) -> List[Dict[str, Any]]:
    """
    Parses the XML output from nmap and extracts host and port information.
    """
    results = []
    try:
        # Strip leading/trailing whitespace before parsing
        root = ET.fromstring(xml_output.strip())
        for host in root.findall('host'):
            ip_address = host.find('address').get('addr')
            host_info = {'ip': ip_address, 'ports': []}

            ports = host.find('ports')
            if ports is not None:
                for port in ports.findall('port'):
                    port_info = {
                        'portid': port.get('portid'),
                        'protocol': port.get('protocol'),
                        'state': port.find('state').get('state'),
                        'service_name': port.find('service').get('name') if port.find('service') is not None else 'unknown',
                        'service_product': port.find('service').get('product') if port.find('service') is not None else '',
                        'service_version': port.find('service').get('version') if port.find('service') is not None else '',
                    }
                    host_info['ports'].append(port_info)
            results.append(host_info)
    except ET.ParseError as e:
        print(f"Error parsing nmap XML output: {e}")

    return results

def format_scan_results(parsed_data: List[Dict[str, Any]]) -> str:
    """
    Formats the parsed nmap data into a human-readable string.
    """
    report_lines = []
    for host in parsed_data:
        report_lines.append(f"Host: {host['ip']}")
        if not host['ports']:
            report_lines.append("  No open ports found.")
        else:
            for port in host['ports']:
                # Handle cases where product or version might be None
                service_product = port.get('service_product') or ''
                service_version = port.get('service_version') or ''
                service_info = f"{service_product} {service_version}".strip()

                report_lines.append(
                    f"  - Port {port['portid']}/{port['protocol']} ({port['state']}): "
                    f"{port['service_name']}"
                    f"{f' ({service_info})' if service_info else ''}"
                )
        report_lines.append("") # Add a blank line for spacing
    return "\n".join(report_lines)


def scan_ip_target(target: str) -> str:
    """
    Runs an nmap scan on a single IP address or CIDR range.
    Returns a formatted string of the results.
    """
    print(f"Starting nmap scan for target: {target}")
    try:
        # -sV: Probe open ports to determine service/version info
        # -oX -: Output scan in XML format to stdout
        # We assume nmap is in the system's PATH
        command = ['nmap', '-sV', '-oX', '-', target]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        xml_output = result.stdout
        if not xml_output:
            print(f"nmap produced no output for target: {target}")
            return ""

        parsed_data = parse_nmap_xml(xml_output)
        formatted_results = format_scan_results(parsed_data)

        print(f"nmap scan for {target} completed.")
        return formatted_results

    except FileNotFoundError:
        print("Error: 'nmap' command not found. Please ensure it is installed and in your PATH.")
        return "Error: nmap not found."
    except subprocess.CalledProcessError as e:
        print(f"Error running nmap for {target}: {e}")
        print(f"Stderr: {e.stderr}")
        return f"Error scanning {target}."

if __name__ == '__main__':
    # For direct testing of this module
    test_target = "127.0.0.1" # or a test machine IP
    scan_results = scan_ip_target(test_target)
    print("\n--- Scan Report ---")
    print(scan_results)
