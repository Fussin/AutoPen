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
    go_path = os.path.join(os.path.expanduser("~"), "go", "bin")
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Prepend the path to the Go tools if it's a go tool
        if command[0] in ['gobuster', 'puredns']:
            command[0] = os.path.join(go_path, command[0])

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

def run_active_enumeration(domain: str) -> Set[str]:
    """
    Runs active subdomain enumeration tools in parallel.
    """
    print(f"Starting active enumeration for: {domain}")

    # For bruteforcing, we need a wordlist. I'll assume a common one exists.
    # In a real application, this would be configurable.
    wordlist = "/usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt"

    commands = [
        ['gobuster', 'dns', '-d', '{domain}', '-w', wordlist, '-o', '{output_file}', '-q'],
        ['puredns', 'bruteforce', wordlist, '{domain}', '-r', '/usr/share/seclists/Discovery/DNS/resolvers.txt', '-w', '{output_file}'],
        ['nmap', '--script', 'dns-zone-transfer', '-p', '53', '{domain}', '-oN', '{output_file}']
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

    print(f"Total unique active subdomains found: {len(all_subdomains)}")
    return all_subdomains
