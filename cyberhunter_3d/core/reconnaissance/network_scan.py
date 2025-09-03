import subprocess
import json
from typing import List, Dict, Any

def run_naabu(target: str) -> List[str]:
    """
    Runs a naabu scan on a single IP address or CIDR range.
    Returns a list of open ports.
    """
    print(f"Starting naabu scan for target: {target}")
    ports = []
    try:
        command = ['naabu', '-host', target, '-silent', '-json']
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            try:
                data = json.loads(line)
                ports.append(str(data['port']))
            except json.JSONDecodeError:
                continue # Ignore non-JSON lines

        print(f"naabu scan for {target} completed. Found ports: {ports}")
        return list(set(ports))

    except FileNotFoundError:
        print("Error: 'naabu' command not found. Please ensure it is installed and in your PATH.")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Error running naabu for {target}: {e}")
        print(f"Stderr: {e.stderr}")
        return []

def run_masscan(target: str) -> List[str]:
    """
    Runs a masscan scan on a single IP address or CIDR range.
    Returns a list of open ports.
    """
    print(f"Starting masscan scan for target: {target}")
    ports = []
    try:
        # Using --rate to avoid overwhelming the network
        command = ['masscan', target, '-p1-65535', '--rate', '1000', '--open', '--banners', '-oJ', '-']
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            if line.startswith('{') and line.endswith('}'):
                try:
                    data = json.loads(line)
                    for port_info in data.get('ports', []):
                        ports.append(str(port_info['port']))
                except json.JSONDecodeError:
                    continue # Ignore non-JSON lines

        # Handle cases where masscan finishes with a comma
        if result.stdout.strip().endswith(','):
            # It's not valid JSON, so we can't parse it directly.
            # We'll have to do some string manipulation to fix it.
            # For now, we'll just ignore the last comma.
            pass

        print(f"masscan scan for {target} completed. Found ports: {ports}")
        return list(set(ports))

    except FileNotFoundError:
        print("Error: 'masscan' command not found. Please ensure it is installed and in your PATH.")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Error running masscan for {target}: {e}")
        print(f"Stderr: {e.stderr}")
        return []

import xml.etree.ElementTree as ET

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

def run_nmap(target: str, ports: List[str]) -> List[Dict[str, Any]]:
    """
    Runs an nmap scan on a single IP address or CIDR range, focusing on specific ports.
    Returns a list of asset dictionaries.
    """
    if not ports:
        print("No ports to scan with nmap.")
        return []

    print(f"Starting nmap scan for target: {target} on ports: {','.join(ports)}")
    assets = []
    try:
        # -sV: Probe open ports to determine service/version info
        # -oX -: Output scan in XML format to stdout
        # -p: Specify ports to scan
        command = ['nmap', '-sV', '-oX', '-', '-p', ','.join(ports), target]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        xml_output = result.stdout
        if not xml_output:
            print(f"nmap produced no output for target: {target}")
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

        print(f"nmap scan for {target} completed.")
        return assets

    except FileNotFoundError:
        print("Error: 'nmap' command not found. Please ensure it is installed and in your PATH.")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Error running nmap for {target}: {e}")
        print(f"Stderr: {e.stderr}")
        return []

def scan_network(target: str, scanner: str = 'naabu') -> List[Dict[str, Any]]:
    """
    Orchestrates the network scan.
    - Runs a port scanner (naabu or masscan) to discover open ports.
    - Runs nmap on the discovered ports for service identification.
    """
    print(f"Starting network scan for {target} using {scanner}")

    open_ports = []
    if scanner == 'naabu':
        open_ports = run_naabu(target)
    elif scanner == 'masscan':
        open_ports = run_masscan(target)
    else:
        print(f"Error: Invalid scanner specified: {scanner}. Use 'naabu' or 'masscan'.")
        return []

    if not open_ports:
        print(f"No open ports found for {target} with {scanner}.")
        return []

    # Run nmap for service discovery on the found ports
    nmap_results = run_nmap(target, open_ports)

    print(f"Network scan for {target} completed.")
    return nmap_results
