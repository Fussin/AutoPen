import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List

# Assume tools are in the PATH. The installation script handles this.
# Sublist3r is a special case, we assume it's cloned in the project root.
SUBLIST3R_PATH = os.path.join(os.getcwd(), 'Sublist3r', 'sublist3r.py')


def run_command(command: List[str], domain: str) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    subdomains = set()
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Format the command with the domain and output file path
        formatted_command = [part.format(domain=domain, output_file=output_filename) for part in command]

        # assetfinder is a special case that only prints to stdout
        if 'assetfinder' in formatted_command[0]:
            with open(output_filename, 'w') as f_out:
                 subprocess.run(formatted_command, stdout=f_out, stderr=subprocess.DEVNULL)
        else:
            # Other tools take an output file argument
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


def enumerate_subdomains(domain: str) -> Set[str]:
    """
    Runs multiple subdomain enumeration tools in parallel and returns a unified set of results.
    """
    print(f"Starting subdomain enumeration for: {domain}")

    commands = [
        ['subfinder', '-d', '{domain}', '-o', '{output_file}', '-silent'],
        ['amass', 'enum', '-d', '{domain}', '-o', '{output_file}'],
        ['assetfinder', '--subs-only', '{domain}'], # This one prints to stdout
        ['python3', SUBLIST3R_PATH, '-d', '{domain}', '-o', '{output_file}'],
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        # Schedule each command to run
        future_to_command = {executor.submit(run_command, cmd, domain): cmd for cmd in commands}

        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                print(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                print(f"'{' '.join(command)}' generated an exception: {exc}")

    print(f"Total unique subdomains found: {len(all_subdomains)}")
    return all_subdomains

def save_results(subdomains: Set[str], output_filename: str):
    """Saves a set of subdomains to a file, sorted alphabetically."""
    print(f"Saving {len(subdomains)} unique subdomains to {output_filename}")
    with open(output_filename, 'w') as f:
        for subdomain in sorted(list(subdomains)):
            f.write(subdomain + '\n')
    print("Results saved.")


if __name__ == '__main__':
    # This is for testing the module directly
    target_domain = "example.com"
    results = enumerate_subdomains(target_domain)

    # The spec requires the output file to be name Subdomain.txt
    output_file = "Subdomain.txt"
    save_results(results, output_file)

    # For verification, print the contents of the created file
    print(f"\n--- Contents of {output_file} ---")
    if os.path.exists(output_file):
        with open(output_file, 'r') as f:
            print(f.read())
