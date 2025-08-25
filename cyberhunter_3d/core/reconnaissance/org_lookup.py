import subprocess
from typing import List, Dict

# Import the parser from the sibling module to help classify the output
from ..target_parser import parse_single_target

def get_assets_for_org(org_name: str) -> List[Dict[str, str]]:
    """
    Uses amass to find all assets (domains, CIDRs) for a given organization.

    :param org_name: The name of the organization (e.g., "Google LLC").
    :return: A list of asset dictionaries, e.g., [{'type': 'domain', 'value': '...'}]
    """
    print(f"Starting organization lookup for '{org_name}' using amass...")
    assets = []
    # Use a set to avoid duplicate assets before returning as a list
    found_assets = set()
    try:
        # amass intel -org '<name>'
        command = ['amass', 'intel', '-org', org_name]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        if not output:
            print(f"Amass produced no output for organization '{org_name}'")
            return assets

        for line in output.strip().splitlines():
            clean_line = line.split('[')[0].strip()
            if clean_line:
                value, asset_type = parse_single_target(clean_line)
                if asset_type not in ['unknown', 'empty']:
                    found_assets.add((value, asset_type))

        print(f"Found {len(found_assets)} unique assets for organization '{org_name}'.")

        # Convert set of tuples to list of dictionaries
        assets = [{'type': asset_type, 'value': value} for value, asset_type in found_assets]

    except FileNotFoundError:
        print("Error: 'amass' command not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error running amass for organization '{org_name}': {e}")
        print(f"Stderr: {e.stderr}")

    return assets
