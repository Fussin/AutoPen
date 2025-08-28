import subprocess
import tempfile
import os
import json
from typing import List, Dict, Set
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config

logger = setup_logger('ASNEngine', 'asn.log')
config = load_config()

def get_asn_for_ips(ips: Set[str]) -> Dict[str, Dict]:
    """
    Uses dnsx to find ASN information for a given set of IP addresses.
    """
    if not ips:
        return {}

    logger.info(f"Starting ASN lookup for {len(ips)} IP addresses...")
    asn_details = {}

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as ip_file:
        ip_filename = ip_file.name
        for ip in ips:
            ip_file.write(f"{ip}\n")

    try:
        dnsx_path = config['tools']['dnsx']
        # Use the -json flag for structured output
        command = [dnsx_path, '-l', ip_filename, '-asn', '-json', '-silent']
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                ip = data.get('host')
                if ip and 'asn' in data:
                    asn_details[ip] = {
                        'asn': data['asn'].get('asn'),
                        'name': data['asn'].get('name'),
                        'country': data['asn'].get('country'),
                        'registrar': data['asn'].get('registrar'),
                    }
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Could not parse dnsx ASN output line: {line}. Error: {e}")

    except FileNotFoundError:
        logger.error(f"Error: '{dnsx_path}' not found. Skipping ASN lookup.")
    except Exception as e:
        logger.error(f"An error occurred during ASN lookup with dnsx: {e}")
    finally:
        os.remove(ip_filename)

    logger.info(f"Found ASN details for {len(asn_details)} IPs.")
    return asn_details


def get_cidrs_for_asn(asn: str) -> List[Dict[str, str]]:
    """
    Uses amass to find all CIDR ranges for a given ASN.
    (Note: This function is currently unused by the main pipeline)
    """
    logger.info(f"Starting CIDR lookup for AS{asn} using amass...")
    assets = []
    try:
        amass_path = config['tools']['amass']
        command = [amass_path, 'intel', '-asn', asn]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        if not output:
            logger.warning(f"Amass produced no output for AS{asn}")
            return assets

        for line in output.strip().splitlines():
            if '/' in line and '.' in line:
                assets.append({'type': 'cidr', 'value': line.strip()})

        logger.info(f"Found {len(assets)} CIDRs for AS{asn}.")

    except FileNotFoundError:
        logger.error(f"Error: '{amass_path}' command not found.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running amass for AS{asn}: {e}\nStderr: {e.stderr}")

    return assets
