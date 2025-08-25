import subprocess
from typing import Set

def get_cidrs_for_asn(asn: str) -> Set[str]:
    """
    Uses amass to find all CIDR ranges for a given ASN.

    :param asn: The Autonomous System Number (as a string, e.g., "15169").
    :return: A set of CIDR strings.
    """
    print(f"Starting ASN lookup for AS{asn} using amass...")
    cidrs = set()
    try:
        # amass intel -asn <number>
        # We assume amass is in the system's PATH
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
            return cidrs

        # Amass output for this command is one CIDR per line
        for line in output.strip().splitlines():
            # Basic validation that it looks like a CIDR
            if '/' in line and '.' in line:
                cidrs.add(line.strip())

        print(f"Found {len(cidrs)} CIDRs for AS{asn}.")

    except FileNotFoundError:
        print("Error: 'amass' command not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error running amass for AS{asn}: {e}")
        print(f"Stderr: {e.stderr}")

    return cidrs

if __name__ == '__main__':
    # For direct testing of this module
    # Note: This requires amass to be installed and will perform a live lookup.
    test_asn = "15169" # Google's ASN
    found_cidrs = get_cidrs_for_asn(test_asn)

    if found_cidrs:
        print(f"\n--- CIDRs for AS{test_asn} ---")
        for cidr in sorted(list(found_cidrs)):
            print(cidr)
