import subprocess
import tempfile
import os
from typing import List, Set
from cyberhunter_3d.common.log import get_rich_logger

logger = get_rich_logger(__name__)

def get_hostnames_for_ips(ips: List[str]) -> Set[str]:
    """
    Uses dnsx to find hostnames for a given list of IP addresses.

    :param ips: A list of IP address strings.
    :return: A set of unique hostnames found.
    """
    if not ips:
        return set()

    logger.info(f"Starting reverse DNS lookup for {len(ips)} IP addresses...")
    hostnames = set()

    # Create a temporary file to store the list of IPs
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        tmp_filename = tmp_file.name
        tmp_file.write('\n'.join(ips))

    try:
        # dnsx -l <ip_list_file> -ptr -resp-only
        command = ['dnsx', '-l', tmp_filename, '-ptr', '-resp-only']
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        output = result.stdout
        if output:
            # dnsx returns one hostname per line
            for line in output.strip().splitlines():
                # The output might have a trailing dot, remove it
                hostnames.add(line.strip().rstrip('.'))

        logger.info(f"Found {len(hostnames)} hostnames from {len(ips)} IPs.")

    except FileNotFoundError:
        logger.error("'dnsx' command not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running dnsx for reverse DNS: {e}")
        logger.error(f"Stderr: {e.stderr}")
    finally:
        # Clean up the temporary file
        os.remove(tmp_filename)

    return hostnames

if __name__ == '__main__':
    # For direct testing of this module
    test_ips = ["8.8.8.8", "1.1.1.1"]
    found_hostnames = get_hostnames_for_ips(test_ips)

    if found_hostnames:
        print(f"\n--- Hostnames Found ---")
        for h in sorted(list(found_hostnames)):
            print(h)
