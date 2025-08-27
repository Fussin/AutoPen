import yaml
import os
import logging

def get_logger(name: str):
    """
    Returns a logger instance.
    Configuration is handled by the application's entry point.
    """
    return logging.getLogger(name)

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

def run_command(command: List[str], domain: str, wordlist: str = None) -> Set[str]:
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
                # Use a regex to extract valid subdomains
                match = re.search(r'([a-zA-Z0-9\-\.]+\.' + re.escape(domain) + ')', line)
                if match:
                    results.add(match.group(1))

    except FileNotFoundError as e:
        tool_name = command[0]
        # Assuming get_logger is available in this scope
        get_logger(__name__).error(f"Error: Tool '{tool_name}' not found. Please ensure it is installed and in your PATH. Details: {e}")
    except subprocess.CalledProcessError as e:
        tool_name = command[0]
        get_logger(__name__).error(f"Error running tool '{tool_name}': {e}")
    finally:
        os.remove(output_filename)

    return results
