import logging
import tempfile
import os
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
        return "Finds cloud assets (e.g., S3 buckets) based on subdomains."

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

        potential_bucket_names = self._generate_bucket_names(subdomains)

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write('\n'.join(potential_bucket_names))
            bucket_filename = tmp_file.name

        cloud_assets = []
        try:
            s3scanner_path = self.config['tools']['s3scanner']
            s3_command = [s3scanner_path, "scan", "-f", bucket_filename]
            result = run_command(s3_command, "", log)
            for line in result.strip().split('\n'):
                if "is readable" in line or "exists" in line:
                    cloud_assets.append({'type': 's3_bucket', 'value': line.split()[0]})
            log.info(f"Found {len(cloud_assets)} potential S3 buckets.")
        except Exception as e:
            log.error(f"An error occurred during S3 scanning: {e}")
        finally:
            os.remove(bucket_filename)

        context.set("cloud_assets", cloud_assets)

    def _generate_bucket_names(self, subdomains: Set[str]) -> Set[str]:
        """Generates potential bucket names from subdomains."""
        names = set()
        for sub in subdomains:
            names.add(sub)
            parts = sub.split('.')
            if len(parts) > 2:
                names.add(parts[0])
                names.add(parts[1])
                names.add(f"{parts[1]}-{parts[0]}")
        return names
