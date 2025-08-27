import subprocess
import tempfile
import os
import json
from typing import Set, List, Dict

def run_tech_fingerprinting(live_hosts: Set[str]) -> Dict[str, Dict]:
    """
    Performs technology fingerprinting and port scanning.
    """
    print(f"Starting technology fingerprinting for {len(live_hosts)} live hosts...")
    go_path = os.path.join(os.path.expanduser("~"), "go", "bin")

    if not live_hosts:
        print("No live hosts to fingerprint.")
        return {}

    tech_results = {}

    # Step 1: Technology fingerprinting with Wappalyzer
    # Wappalyzer can be used as a library, which is better than shelling out.
    # For simplicity in this script, I'll use the command line, but a real implementation
    # would use the Python library.
    try:
        from wappalyzer import analyze
        for host in live_hosts:
            tech = analyze(host)
            tech_results[host] = {'technologies': tech}
    except ImportError:
        print("Wappalyzer library not found. Skipping technology fingerprinting.")
    except Exception as e:
        print(f"An error occurred during Wappalyzer analysis: {e}")


    # Step 2: Port scanning with Naabu and Nmap
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as live_hosts_file:
        live_hosts_filename = live_hosts_file.name
        for host in live_hosts:
            live_hosts_file.write(f"{host}\n")

    try:
        # Naabu
        naabu_command = [os.path.join(go_path, 'naabu'), '-list', live_hosts_filename, '-top-ports', '1000', '-json', '-o', 'naabu_results.json']
        subprocess.run(naabu_command)

        # Nmap on discovered ports
        with open('naabu_results.json', 'r') as f_in:
            for line in f_in:
                try:
                    data = json.loads(line)
                    host = data['host']
                    port = data['port']
                    if host not in tech_results:
                        tech_results[host] = {}
                    if 'ports' not in tech_results[host]:
                        tech_results[host]['ports'] = []

                    nmap_command = ['nmap', '-sV', '-p', str(port), host, '-oN', f'nmap_{host}_{port}.txt']
                    subprocess.run(nmap_command)

                    with open(f'nmap_{host}_{port}.txt', 'r') as f_nmap:
                        nmap_output = f_nmap.read()
                        tech_results[host]['ports'].append({'port': port, 'service': nmap_output})

                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Could not parse naabu output line: {line}. Error: {e}")

    except FileNotFoundError as e:
        tool_name = str(e).split("'")[1]
        print(f"Error: Tool '{tool_name}' not found.")
    except Exception as e:
        print(f"An error occurred during port scanning: {e}")
    finally:
        os.remove(live_hosts_filename)
        if os.path.exists('naabu_results.json'):
            os.remove('naabu_results.json')

    return tech_results
