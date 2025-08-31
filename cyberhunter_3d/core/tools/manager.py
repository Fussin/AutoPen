import logging
import shutil
import subprocess
from ..reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class ToolManager:
    """
    Manages the verification and updating of external command-line tools.
    """
    def __init__(self):
        self.config = load_config()

    def verify_tools(self) -> bool:
        """
        Checks if all required tools from the config are installed and in the PATH.

        Returns:
            True if all tools are found, False otherwise.
        """
        log.info("Verifying required tools...")
        all_tools_found = True
        required_tools = self.config.get("tools", {})

        if not required_tools:
            log.warning("No tools listed in the configuration file.")
            return True

        for tool_name, tool_path in required_tools.items():
            if shutil.which(tool_path):
                log.info(f"[+] Found: {tool_name} (at {tool_path})")
            else:
                log.error(f"[-] Missing: {tool_name}. Please install it and ensure it's in your PATH.")
                all_tools_found = False

        if all_tools_found:
            log.info("All required tools verified successfully.")
        else:
            log.error("Some required tools are missing. Please install them before running a scan.")

        return all_tools_found

    def update_nuclei_templates(self):
        """
        Runs the command to update Nuclei's templates.
        """
        log.info("Checking for Nuclei template updates...")
        nuclei_path = self.config.get("tools", {}).get("nuclei")
        if not nuclei_path or not shutil.which(nuclei_path):
            log.warning("Nuclei tool not found, skipping template update.")
            return

        try:
            command = f"{nuclei_path} -update-templates"
            log.info(f"Running command: {command}")
            # We use a longer timeout as template downloads can be slow.
            process = subprocess.run(
                command,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                timeout=300 # 5 minutes
            )
            log.info("Nuclei templates updated successfully.")
            if process.stdout:
                log.info(process.stdout)
        except subprocess.TimeoutExpired:
            log.error("Timed out while trying to update Nuclei templates.")
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to update Nuclei templates: {e.stderr}")
