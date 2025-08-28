import yaml
import os
import re
import subprocess
import tempfile
from typing import Set, List

def load_config():
    """
    Loads the reconnaissance configuration from the YAML file.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'recon_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def run_command(command: List[str], domain: str, logger, wordlist: str = None) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    results = set()
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Format the command with the domain and output file path
        formatted_command = [part.format(domain=domain, output_file=output_filename, wordlist=wordlist) for part in command]

        # If the command doesn't use a placeholder for an output file,
        # we assume it prints to stdout and redirect it to our temp file.
        if '{output_file}' not in ' '.join(command):
            with open(output_filename, 'w') as f_out:
                subprocess.run(formatted_command, stdout=f_out, stderr=subprocess.DEVNULL)
        else:
            # Other tools take an output file argument, so we run them as is.
            subprocess.run(formatted_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Read the output from the temporary file
        with open(output_filename, 'r') as f_in:
            for line in f_in:
                # Use a regex to extract valid subdomains
                match = re.search(r'([a-zA-Z0-9\-\.]+\.' + re.escape(domain) + ')', line)
                if match:
                    results.add(match.group(1))

    except FileNotFoundError as e:
        tool_name = command[0]
        logger.error(f"Error: Tool '{tool_name}' not found. Please ensure it is installed and in your PATH. Details: {e}")
    except subprocess.CalledProcessError as e:
        tool_name = command[0]
        logger.error(f"Error running tool '{tool_name}': {e}")
    finally:
        os.remove(output_filename)

    return results
