import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from ...common.log import get_rich_logger

logger = get_rich_logger(__name__)

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
        logger.error(f"Error parsing nmap XML output: {e}")

    return results

def scan_ip_target(target: str) -> List[Dict[str, Any]]:
    """
    Runs an nmap scan on a single IP address or CIDR range.
    Returns a list of asset dictionaries.
    """
    logger.info(f"Starting nmap scan for target: {target}")
    assets = []
    try:
        # -sV: Probe open ports to determine service/version info
        # -oX -: Output scan in XML format to stdout
        command = ['nmap', '-sV', '-oX', '-', target]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        xml_output = result.stdout
        if not xml_output:
            logger.warning(f"nmap produced no output for target: {target}")
            return assets

        parsed_data = parse_nmap_xml(xml_output)

        # Transform the parsed data into our asset structure
        for host_info in parsed_data:
            # We only care about hosts with open ports for now
            open_ports = [p for p in host_info.get('ports', []) if p.get('state') == 'open']
            if open_ports:
                assets.append({
                    'type': 'host_with_open_ports',
                    'value': host_info['ip'],
                    'details': {'ports': open_ports}
                })

        logger.info(f"nmap scan for {target} completed.")
        return assets

    except FileNotFoundError:
        logger.error("'nmap' command not found. Please ensure it is installed and in your PATH.")
        return []
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running nmap for {target}: {e}")
        logger.error(f"Stderr: {e.stderr}")
        return []
