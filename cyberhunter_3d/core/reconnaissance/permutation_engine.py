import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List

def run_command(command: List[str], domain: str, wordlist: str = None) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    subdomains = set()
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Format the command with the domain and output file path
        formatted_command = [part.format(domain=domain, output_file=output_filename, wordlist=wordlist) for part in command]

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

def run_permutation_enumeration(domain: str, known_subdomains: Set[str]) -> Set[str]:
    """
    Runs permutation-based subdomain enumeration tools in parallel.
    """
    print(f"Starting permutation enumeration for: {domain}")

    if not known_subdomains:
        print("No known subdomains to permute. Skipping permutation engine.")
        return set()

    # Create a temporary file with the known subdomains
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        subdomain_filename = tmp_file.name
        for sub in known_subdomains:
            tmp_file.write(f"{sub}\n")

    # For permutation, we also need a wordlist.
    wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt"

    commands = [
        ['dnsgen', subdomain_filename, '-w', wordlist, '-o', '{output_file}'],
        ['gotator', '-sub', subdomain_filename, '-perm', wordlist, '-depth', '2', '-mindup', '>', '{output_file}']
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain, wordlist): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                print(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                print(f"'{' '.join(command)}' generated an exception: {exc}")

    os.remove(subdomain_filename)
    print(f"Total unique permuted subdomains found: {len(all_subdomains)}")
    return all_subdomains
