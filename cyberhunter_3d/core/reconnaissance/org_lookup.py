import subprocess
from typing import Set, Tuple

# Import the parser from the sibling module to help classify the output
from ..target_parser import parse_single_target

def get_assets_for_org(org_name: str) -> Set[Tuple[str, str]]:
    """
    Uses amass to find all assets (domains, CIDRs) for a given organization.

    :param org_name: The name of the organization (e.g., "Google LLC").
    :return: A set of tuples, where each tuple is (value, type).
    """
    print(f"Starting organization lookup for '{org_name}' using amass...")
    assets = set()
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

        # The output can be mixed (domains, IPs, CIDRs).
        # We can reuse our own parser to classify the results.
        for line in output.strip().splitlines():
            # The output of 'amass intel' sometimes includes the source in brackets, e.g. "example.com [source]"
            # We should strip that off before parsing.
            clean_line = line.split('[')[0].strip()

            if clean_line:
                value, asset_type = parse_single_target(clean_line)
                if asset_type not in ['unknown', 'empty']:
                    assets.add((value, asset_type))

        print(f"Found {len(assets)} assets for organization '{org_name}'.")

    except FileNotFoundError:
        print("Error: 'amass' command not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error running amass for organization '{org_name}': {e}")
        print(f"Stderr: {e.stderr}")

    return assets

if __name__ == '__main__':
    # For direct testing of this module
    test_org = "AS15169" # Using an ASN here as a proxy for an org name that amass can find
    found_assets = get_assets_for_org(test_org)

    if found_assets:
        print(f"\n--- Assets for {test_org} ---")
        for value, asset_type in sorted(list(found_assets)):
            print(f"- {value} ({asset_type})")
