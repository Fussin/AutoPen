import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List

def run_command(command: List[str], domain: str) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    subdomains = set()
    go_path = os.path.join(os.path.expanduser("~"), "go", "bin")
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Prepend the path to the Go tools
        command[0] = os.path.join(go_path, command[0])
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

def run_passive_enumeration(domain: str) -> Set[str]:
    """
    Runs passive subdomain enumeration tools in parallel.
    """
    print(f"Starting passive enumeration for: {domain}")

    commands = [
        ['subfinder', '-d', '{domain}', '-o', '{output_file}', '-silent'],
        ['amass', 'enum', '-passive', '-d', '{domain}', '-o', '{output_file}'], # Using passive mode for amass
        ['assetfinder', '--subs-only', '{domain}'], # This one prints to stdout
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                print(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                print(f"'{' '.join(command)}' generated an exception: {exc}")

    print(f"Total unique passive subdomains found: {len(all_subdomains)}")
    return all_subdomains
