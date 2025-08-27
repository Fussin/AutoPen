import subprocess
import tempfile
import os
from typing import Set, List, Tuple

def run_visual_recon(subdomains: Set[str]) -> Tuple[Set[str], List[str]]:
    """
    Performs live host detection and visual reconnaissance.
    """
    print(f"Starting visual reconnaissance for {len(subdomains)} subdomains...")
    go_path = os.path.join(os.path.expanduser("~"), "go", "bin")

    if not subdomains:
        print("No subdomains to perform visual recon on.")
        return set(), []

    # Step 1: Find live hosts with httpx
    live_hosts = set()
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        input_filename = tmp_file.name
        for sub in subdomains:
            tmp_file.write(f"{sub}\n")

    try:
        httpx_command = [
            os.path.join(go_path, 'httpx'), '-l', input_filename, '-p', '80,443,8080,8000', '--silent'
        ]
        result = subprocess.run(httpx_command, capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if line:
                live_hosts.add(line)
    except FileNotFoundError:
        print("Error: 'httpx' not found.")
    except subprocess.CalledProcessError as e:
        print(f"Error running httpx for visual recon: {e}\nOutput: {e.stderr}")
    finally:
        os.remove(input_filename)

    if not live_hosts:
        print("No live hosts found for visual recon.")
        return set(), []

    print(f"Found {len(live_hosts)} live hosts. Now taking screenshots...")

    # Step 2: Take screenshots with gowitness and aquatone
    screenshots = []
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as live_hosts_file:
        live_hosts_filename = live_hosts_file.name
        for host in live_hosts:
            live_hosts_file.write(f"{host}\n")

    try:
        # gowitness
        gowitness_command = [os.path.join(go_path, 'gowitness'), 'file', '-f', live_hosts_filename, '-P', 'screenshots/gowitness']
        subprocess.run(gowitness_command)

        # aquatone
        aquatone_command = ['/usr/local/bin/aquatone', '-out', 'screenshots/aquatone']
        with open(live_hosts_filename, 'r') as f_in:
            subprocess.run(aquatone_command, stdin=f_in)

        # For now, just return the paths to the screenshot directories
        screenshots.append('screenshots/gowitness')
        screenshots.append('screenshots/aquatone')

    except FileNotFoundError as e:
        tool_name = str(e).split("'")[1]
        print(f"Error: Tool '{tool_name}' not found.")
    except Exception as e:
        print(f"An error occurred during visual recon: {e}")
    finally:
        os.remove(live_hosts_filename)

    return live_hosts, screenshots
