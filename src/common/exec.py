import subprocess
from typing import List

def run_command(command: List[str]):
    """
    Runs an external command and returns the output.
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except FileNotFoundError as e:
        print(f"Error: Command not found: {e}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}\nOutput: {e.stderr}")
        return None
