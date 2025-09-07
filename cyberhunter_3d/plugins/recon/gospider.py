import subprocess
from typing import List

def run_gospider_scan(target_site: str) -> List[str]:
    """
    Runs a gospider scan on a single site to discover URLs.

    :param target_site: The base URL of the site to scan (e.g., https://example.com).
    :return: A list of discovered URLs.
    """
    print(f"Running gospider scan on {target_site}...")
    urls = []

    # Construct the gospider command
    # -s: site to crawl
    # -q: quiet mode (suppress banners)
    # -d: depth of crawl (e.g., 2)
    # --other-source: find URLs from other sources (archives, etc.)
    command = [
        "gospider",
        "-s", target_site,
        "-q",
        "-d", "2",
        "--other-source"
    ]

    try:
        # Run the command
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=300) # 5 minute timeout

        # gospider outputs URLs to stdout, one per line
        output_lines = result.stdout.strip().split('\n')

        for line in output_lines:
            # The output format is typically "[source] - url"
            if " - " in line:
                parts = line.split(" - ")
                if len(parts) > 1 and parts[1].startswith("http"):
                    urls.append(parts[1])

        print(f"gospider scan for {target_site} complete. Found {len(urls)} URLs.")

    except FileNotFoundError:
        print("Error: 'gospider' command not found. Please ensure it is installed and in your PATH.")
        return []
    except subprocess.TimeoutExpired:
        print(f"Error: gospider scan for {target_site} timed out.")
        return []
    except subprocess.CalledProcessError as e:
        print(f"Error running gospider on {target_site}: {e}")
        print(f"Stderr: {e.stderr}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during gospider scan for {target_site}: {e}")
        return []

    return urls
