import subprocess
import tempfile
import os
import json
from typing import List, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config

class TakeoverPlugin(Plugin):
    """
    Plugin for detecting subdomain takeover vulnerabilities.
    """
    @property
    def name(self) -> str:
        return "Subdomain Takeover"

    @property
    def description(self) -> str:
        return "Checks for subdomain takeover vulnerabilities using Nuclei."

    @property
    def requires(self) -> List[str]:
        return ["live_hosts"]

    @property
    def provides(self) -> List[str]:
        return ["takeover_vulns"]

    def run(self, context: 'ScanContext'):
        logger = setup_logger('TakeoverPlugin', 'takeover_plugin.log')
        config = load_config()
        target = context.target

        live_hosts = context.get("live_hosts")
        if not live_hosts:
            logger.info("No live hosts provided for takeover scan.")
            return

        nuclei_path = config['tools'].get('nuclei')
        if not nuclei_path or not os.path.exists(nuclei_path):
            logger.error("Nuclei tool not found or path not configured. Skipping takeover scan.")
            return {}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
            for host in live_hosts:
                tmp_file.write(f"{host}\n")
            target_file = tmp_file.name

        logger.info(f"Starting subdomain takeover scan on {len(live_hosts)} hosts.")

        command = [nuclei_path, "-l", target_file, "-t", "takeovers", "-json", "-silent"]

        vulnerabilities = []
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
            for line in process.stdout:
                try:
                    if line.strip():
                        vulnerabilities.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON line from Nuclei output: {line.strip()}")

            stderr_output = process.communicate()[1]
            if process.returncode != 0:
                logger.error(f"Nuclei process finished with error code {process.returncode}. Stderr: {stderr_output}")

        except Exception as e:
            logger.error(f"An unexpected error occurred while running Nuclei: {e}")
        finally:
            os.remove(target_file)

        logger.info(f"Subdomain takeover scan complete. Found {len(vulnerabilities)} potential vulnerabilities.")
        context.set("takeover_vulns", vulnerabilities)
