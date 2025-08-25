import subprocess
from typing import List, Dict

def get_cidrs_for_asn(asn: str) -> List[Dict[str, str]]:
    """
    Uses amass to find all CIDR ranges for a given ASN.

    :param asn: The Autonomous System Number (as a string, e.g., "15169").
    :return: A list of asset dictionaries, e.g., [{'type': 'cidr', 'value': '...'}].
    """
    print(f"Starting ASN lookup for AS{asn} using amass...")
    assets = []
    try:
        # amass intel -asn <number>
        command = ['amass', 'intel', '-asn', asn]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        if not output:
            print(f"Amass produced no output for AS{asn}")
            return assets

        # Amass output for this command is one CIDR per line
        for line in output.strip().splitlines():
            # Basic validation that it looks like a CIDR
            if '/' in line and '.' in line:
                assets.append({'type': 'cidr', 'value': line.strip()})

        print(f"Found {len(assets)} CIDRs for AS{asn}.")

    except FileNotFoundError:
        print("Error: 'amass' command not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error running amass for AS{asn}: {e}")
        print(f"Stderr: {e.stderr}")

    return assets
