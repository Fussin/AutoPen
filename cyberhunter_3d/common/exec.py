import subprocess
from typing import List
from .exceptions import ToolExecutionError

def run_command(command: List[str]):
    """
    Runs an external command and returns the output.
    Raises ToolExecutionError on failure.
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
        raise ToolExecutionError(f"Command not found: {e.filename}") from e
    except subprocess.CalledProcessError as e:
        raise ToolExecutionError(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.\nStderr: {e.stderr}") from e
