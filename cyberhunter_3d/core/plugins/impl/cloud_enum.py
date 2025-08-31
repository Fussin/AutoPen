import logging
import tempfile
import os
import json
import subprocess
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config, run_command

log = logging.getLogger(__name__)

class CloudEnumPlugin(Plugin):
    """
    Plugin for discovering cloud assets like S3 buckets.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "Cloud Enumeration"

    @property
    def description(self) -> str:
        return "Finds cloud assets (e.g., S3 buckets, Azure blobs) based on subdomains."

    @property
    def requires(self) -> List[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["cloud_assets"]

    def run(self, context: ScanContext):
        log.info("Running cloud enumeration plugin...")
        subdomains = context.get("validated_subdomains")
        if not subdomains:
            log.info("No validated subdomains found, skipping cloud enumeration.")
            context.set("cloud_assets", [])
            return

        cloud_assets = []

        # --- S3 Bucket Scan ---
        s3_names = self._generate_s3_bucket_names(subdomains)
        s3_scan_command = self.config.get("tool_commands", {}).get("s3_scan")
        if s3_scan_command:
            self._run_cloud_scan(s3_scan_command, s3_names, "s3_bucket", "S3", cloud_assets)

        # --- Azure Blob Scan ---
        azure_names = self._generate_azure_blob_names(subdomains)
        blobhunter_command = self.config.get("tool_commands", {}).get("blobhunter_scan")
        if blobhunter_command:
            self._run_cloud_scan(blobhunter_command, azure_names, "azure_blob", "Azure Blob", cloud_assets)

        context.set("cloud_assets", cloud_assets)
        log.info(f"Cloud enumeration finished. Found {len(cloud_assets)} total cloud assets.")

    def _run_cloud_scan(self, command_template: str, names: Set[str], asset_type: str, platform_name: str, results_list: List):
        log.info(f"Scanning for {platform_name} assets...")
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write('\n'.join(names))
            input_filename = tmp_file.name

        try:
            command = command_template.format(input_file=input_filename)
            output = self._run_command(command)

            if platform_name == "Azure Blob":
                for line in output.strip().split('\n'):
                    try:
                        data = json.loads(line)
                        if data.get("status") == "Public":
                            results_list.append({'type': asset_type, 'value': data.get('container')})
                    except json.JSONDecodeError:
                        continue
            else: # s3scanner
                for line in output.strip().split('\n'):
                    if "is readable" in line or "exists" in line:
                        results_list.append({'type': asset_type, 'value': line.split()[0]})

            log.info(f"Found {len(results_list)} potential {platform_name} assets so far.")

        except Exception as e:
            log.error(f"An error occurred during {platform_name} scanning: {e}")
        finally:
            os.remove(input_filename)

    def _run_command(self, command: str) -> str:
        """Wrapper for running external commands."""
        try:
            log.info(f"Running command: {command}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0 and stderr:
                log.warning(f"Command '{command}' exited with non-zero status. Stderr: {stderr}")
            return stdout
        except Exception as e:
            log.error(f"An exception occurred while running {command}: {e}")
            return ""

    def _generate_s3_bucket_names(self, subdomains: Set[str]) -> Set[str]:
        """Generates potential S3 bucket names from subdomains."""
        names = set()
        for sub in subdomains:
            names.add(sub)
            parts = sub.split('.')
            if len(parts) > 2:
                names.add(parts[0])
                names.add(parts[1])
                names.add(f"{parts[1]}-{parts[0]}")
        return names

    def _generate_azure_blob_names(self, subdomains: Set[str]) -> Set[str]:
        """Generates potential Azure storage account names from subdomains."""
        names = set()
        for sub in subdomains:
            # Azure storage account names are 3-24 alphanumeric characters, lowercase only.
            # We'll take the first part of the subdomain and sanitize it.
            name = sub.split('.')[0].lower().replace('-', '')
            if 3 <= len(name) <= 24 and name.isalnum():
                names.add(name)
        return names
