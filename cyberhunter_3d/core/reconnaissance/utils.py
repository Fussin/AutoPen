import yaml
import os
import re
import subprocess
import tempfile
from typing import Set, List

def load_config():
    """
    Loads the reconnaissance configuration from the YAML file.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'recon_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def run_command(command: List[str], domain: str, logger, wordlist: str = None) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    results = set()
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Format the command with the domain and output file path
        formatted_command = [part.format(domain=domain, output_file=output_filename, wordlist=wordlist) for part in command]

        # If the command doesn't use a placeholder for an output file,
        # we assume it prints to stdout and redirect it to our temp file.
        if '{output_file}' not in ' '.join(command):
            with open(output_filename, 'w') as f_out:
                subprocess.run(formatted_command, stdout=f_out, stderr=subprocess.DEVNULL)
        else:
            # Other tools take an output file argument, so we run them as is.
            subprocess.run(formatted_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Read the output from the temporary file
        with open(output_filename, 'r') as f_in:
            for line in f_in:
                # Use a regex to extract valid subdomains
                match = re.search(r'([a-zA-Z0-9\-\.]+\.' + re.escape(domain) + ')', line)
                if match:
                    results.add(match.group(1))

    except FileNotFoundError as e:
        tool_name = command[0]
        logger.error(f"Error: Tool '{tool_name}' not found. Please ensure it is installed and in your PATH. Details: {e}")
    except subprocess.CalledProcessError as e:
        tool_name = command[0]
        logger.error(f"Error running tool '{tool_name}': {e}")
    finally:
        os.remove(output_filename)

    return results

import uuid
import json

def detect_wildcard_ips(domain: str, logger, num_tests: int = 5) -> Set[str]:
    """
    Detects if a domain has a wildcard DNS record by resolving random subdomains.
    Returns a set of IP addresses that the wildcard record resolves to.
    """
    logger.info(f"Starting wildcard detection for {domain}...")
    wildcard_ips = set()

    config = load_config()
    dnsx_path = config['tools'].get('dnsx')
    if not dnsx_path:
        logger.error("dnsx tool not configured. Skipping wildcard detection.")
        return wildcard_ips

    # Generate a list of random, non-existent subdomains
    random_subdomains = [
        f"{uuid.uuid4().hex[:12]}.{domain}" for _ in range(num_tests)
    ]

    try:
        # Use dnsx to resolve these domains
        # The '-resp' flag includes the IP in the output, e.g., "random.domain.com [1.2.3.4]"
        process = subprocess.run(
            [dnsx_path, '-resp', '-silent'],
            input="\n".join(random_subdomains),
            capture_output=True,
            text=True,
            check=True
        )

        # Regex to extract the IP address from the output
        ip_regex = re.compile(r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]')

        for line in process.stdout.strip().split('\n'):
            if not line:
                continue
            match = ip_regex.search(line)
            if match:
                wildcard_ips.add(match.group(1))

    except FileNotFoundError:
        logger.error(f"Error: '{dnsx_path}' not found. Skipping wildcard detection.")
    except subprocess.CalledProcessError as e:
        logger.error(f"dnsx failed during wildcard check: {e}")

    if wildcard_ips:
        logger.warning(f"Wildcard DNS detected for {domain}. IPs: {wildcard_ips}")
    else:
        logger.info(f"No wildcard DNS detected for {domain}.")

    return wildcard_ips

from typing import Dict

def resolve_subdomains_to_ips(subdomains: Set[str], logger) -> Dict[str, List[str]]:
    """
    Resolves a set of subdomains to their corresponding IP addresses.
    """
    if not subdomains:
        return {}

    logger.info(f"Resolving {len(subdomains)} subdomains to IP addresses...")
    ip_mapping = {}

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as subs_file:
        subs_filename = subs_file.name
        for sub in subdomains:
            subs_file.write(f"{sub}\n")

    try:
        config = load_config()
        dnsx_path = config['tools']['dnsx']
        command = [dnsx_path, '-l', subs_filename, '-a', '-json', '-silent']
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                host = data.get('host')
                if host and 'a' in data:
                    ip_mapping[host] = data['a']
            except (json.JSONDecodeError, KeyError):
                logger.warning(f"Could not parse dnsx A record output line: {line}")

    except FileNotFoundError:
        logger.error(f"Error: '{dnsx_path}' not found. Skipping subdomain to IP resolution.")
    except Exception as e:
        logger.error(f"An error occurred during subdomain to IP resolution with dnsx: {e}")
    finally:
        os.remove(subs_filename)

    logger.info(f"Successfully resolved {len(ip_mapping)} subdomains to IPs.")
    return ip_mapping

def save_to_json(data: any, filename: str, logger, deduplication_key: str = None) -> str:
    """
    Saves a Python object to a JSON file, with deduplication.
    """
    config = load_config()
    output_dir = config.get('recon_output_dir', 'recon_results')
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, filename)

    # Deduplication logic
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                existing_data = json.load(f)

            if isinstance(existing_data, list) and isinstance(data, list):
                if deduplication_key:
                    existing_items = {item[deduplication_key]: item for item in existing_data}
                    for item in data:
                        existing_items[item[deduplication_key]] = item
                    data = list(existing_items.values())
                else:
                    data = list(set(existing_data + data))
            elif isinstance(existing_data, dict) and isinstance(data, dict):
                data = {**existing_data, **data}

    except (json.JSONDecodeError, IOError):
        logger.warning(f"Could not read existing data from {file_path}. Overwriting.")

    try:
        with open(file_path, 'w') as f:
            def set_default(obj):
                if isinstance(obj, set):
                    return list(obj)
                raise TypeError
            json.dump(data, f, indent=4, default=set_default)
        logger.info(f"Successfully saved data to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save data to {file_path}: {e}")
        return None
