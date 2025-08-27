import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List, Tuple, Dict
import json

# Assume tools are in the PATH. The installation script handles this.


def run_command(command: List[str], domain: str) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    subdomains = set()
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Format the command with the domain and output file path
        formatted_command = [part.format(domain=domain, output_file=output_filename) for part in command]

        # assetfinder is a special case that only prints to stdout
        if 'assetfinder' in formatted_command[0]:
            with open(output_filename, 'w') as f_out:
                 subprocess.run(formatted_command, stdout=f_out, stderr=subprocess.DEVNULL)
        else:
            # Other tools take an output file argument
            subprocess.run(formatted_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Read the output from the temporary file
        with open(output_filename, 'r') as f_in:
            for line in f_in:
                # Basic cleaning
                line = line.strip()
                if line and '.' in line and domain in line:
                    # More robust parsing can be added here if needed
                    subdomains.add(line)

    except FileNotFoundError as e:
        tool_name = command[0]
        print(f"Error: Tool '{tool_name}' not found. Please ensure it is installed and in your PATH. Details: {e}")
    except subprocess.CalledProcessError as e:
        tool_name = command[0]
        print(f"Error running tool '{tool_name}': {e}")
    finally:
        os.remove(output_filename)

    return subdomains


def detect_live_hosts(subdomains: Set[str]) -> Tuple[Set[str], Set[str]]:
    """
    Uses httpx to find live hosts from a set of subdomains.
    Returns two sets: one with live hosts and one with dead hosts.
    """
    print(f"Detecting live hosts from {len(subdomains)} subdomains...")
    live_hosts = set()

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        input_filename = tmp_file.name
        for subdomain in subdomains:
            tmp_file.write(f"{subdomain}\n")

    try:
        # Run httpx, asking it to probe ports and output JSON
        httpx_command = [
            'httpx',
            '-l', input_filename,
            '-p', '80,443,8080,8000', # As per the diagram
            '-json', # Output in JSON format for easier parsing
            '-silent'
        ]
        result = subprocess.run(httpx_command, capture_output=True, text=True, check=True)

        # Parse the JSON output from httpx
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                # httpx outputs a stream of JSON objects, one per line
                scan_result = json.loads(line)
                # We consider any host that gives a successful probe on any port to be "live"
                # We will extract the URL, which includes the port
                if 'url' in scan_result:
                    live_hosts.add(scan_result['url'])
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON line from httpx output: {line}")

    except FileNotFoundError:
        print("Error: 'httpx' not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error running httpx: {e}\nOutput: {e.stderr}")
    finally:
        os.remove(input_filename)

    # Determine dead hosts by finding the difference
    # We need to be careful here because live_hosts contains URLs (e.g., http://test.com:80)
    # and subdomains is just hostnames (e.g., test.com)
    live_hostnames = {url.split('//')[1].split(':')[0] for url in live_hosts}
    dead_hosts = subdomains - live_hostnames

    print(f"Found {len(live_hosts)} live URLs and {len(dead_hosts)} dead hosts.")
    return live_hosts, dead_hosts


def check_subdomain_takeover(live_hosts: Set[str]) -> Dict[str, str]:
    """
    Checks for subdomain takeover vulnerabilities on a list of live hosts.
    Uses subzy and nuclei.
    Returns a dictionary mapping vulnerable hosts to the identified vulnerability.
    """
    if not live_hosts:
        return {}

    print(f"Checking {len(live_hosts)} live hosts for subdomain takeover...")
    vulnerabilities = {}

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        input_filename = tmp_file.name
        for host in live_hosts:
            tmp_file.write(f"{host}\n")

    try:
        # --- Run subzy ---
        print("Running subzy...")
        subzy_command = ['subzy', 'run', '--targets', input_filename]
        # subzy has colorful output, so we capture it as text
        result = subprocess.run(subzy_command, capture_output=True, text=True)
        # Simple parsing for subzy: look for lines containing "VULNERABLE"
        for line in result.stdout.strip().split('\n'):
            if "VULNERABLE" in line:
                # Attempt to extract the vulnerable host
                parts = line.split()
                if len(parts) > 0:
                    # The vulnerable host is usually part of the line, let's find it
                    for part in parts:
                        if part in live_hosts:
                            vulnerabilities[part] = "Subdomain Takeover (subzy)"
                            break

        # --- Run nuclei ---
        print("Running nuclei for takeover checks...")
        # We use nuclei's takeover templates.
        nuclei_command = [
            'nuclei',
            '-l', input_filename,
            '-t', 'subdomain-takeover', # Use the built-in takeover templates
            '-silent' # Only output findings
        ]
        result = subprocess.run(nuclei_command, capture_output=True, text=True)
        # Simple parsing for nuclei: each line is a finding
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            # Example output: [subdomain-takeover] [http-vuln] [high] http://some.host
            parts = line.split()
            if len(parts) > 1:
                # The last part is usually the URL
                vulnerable_host = parts[-1]
                vulnerabilities[vulnerable_host] = f"Subdomain Takeover ({parts[0]})"

    except FileNotFoundError as e:
        tool_name = str(e).split("'")[1]
        print(f"Error: Tool '{tool_name}' not found. Please ensure it is installed.")
    except Exception as e:
        print(f"An error occurred during takeover scan: {e}")
    finally:
        os.remove(input_filename)

    print(f"Found {len(vulnerabilities)} potential subdomain takeover vulnerabilities.")
    return vulnerabilities


from typing import Dict

def enumerate_subdomains(domain: str) -> List[Dict[str, str]]:
    """
    Runs multiple subdomain enumeration tools in parallel and returns a unified
    set of results as a list of asset dictionaries.
    """
    print(f"Starting subdomain enumeration for: {domain}")

    commands = [
        ['subfinder', '-d', '{domain}', '-o', '{output_file}', '-silent'],
        ['amass', 'enum', '-d', '{domain}', '-o', '{output_file}'],
        ['assetfinder', '--subs-only', '{domain}'], # This one prints to stdout
        ['sublist3r', '-d', '{domain}', '-o', '{output_file}'],
    ]

    all_subdomains_str = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                print(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains_str.update(subdomains)
            except Exception as exc:
                print(f"'{' '.join(command)}' generated an exception: {exc}")

    print(f"Total unique subdomains found: {len(all_subdomains_str)}")

    # Step 2: Detect which subdomains are live
    live_urls, dead_hosts = detect_live_hosts(all_subdomains_str)

    # Step 3: Check for subdomain takeover on live hosts
    takeover_vulns = check_subdomain_takeover(live_urls)

    # Step 4: Consolidate all information into a list of asset dictionaries
    assets = []
    live_host_to_url = {url.split('//')[1].split(':')[0]: url for url in live_urls}

    for sub in all_subdomains_str:
        asset_info = {'type': 'subdomain', 'value': sub}
        if sub in dead_hosts:
            asset_info['status'] = 'dead'
        else:
            asset_info['status'] = 'live'
            # Find the corresponding URL (could be multiple if multiple ports are open)
            # For simplicity, we take the first one we find.
            matching_urls = [u for u in live_urls if sub in u]
            if matching_urls:
                url = matching_urls[0]
                asset_info['url'] = url
                if url in takeover_vulns:
                    asset_info['takeover_vulnerability'] = takeover_vulns[url]
        assets.append(asset_info)

    # Optionally, save to files as per the diagram
    with open('subdomains_alive.txt', 'w') as f_alive, open('subdomains_dead.txt', 'w') as f_dead:
        for url in live_urls:
            f_alive.write(f"{url}\n")
        for host in dead_hosts:
            f_dead.write(f"{host}\n")
    print("Saved live and dead subdomains to 'subdomains_alive.txt' and 'subdomains_dead.txt'")

    return assets
