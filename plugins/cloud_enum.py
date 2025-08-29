import subprocess
import tempfile
import os
from typing import Set, List, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.core.reconnaissance.utils import load_config

class CloudEnumPlugin(Plugin):
    """
    Plugin for discovering cloud assets.
    """
    @property
    def name(self) -> str:
        return "Cloud Enumeration"

    @property
    def description(self) -> str:
        return "Finds cloud assets (S3 buckets, Azure blobs, GCP buckets)."

    def run(self, target: str, **kwargs) -> Dict[str, Any]:
        logger = setup_logger('CloudEnumPlugin', 'cloud_enum_plugin.log')
        config = load_config()

        subdomains = kwargs.get('subdomains')
        if not subdomains:
            logger.info("No subdomains provided for cloud asset enumeration.")
            return {}

        cloud_assets = []
        potential_bucket_names = set()
        for sub in subdomains:
            potential_bucket_names.add(sub)
            if '.' in sub:
                potential_bucket_names.add(sub.split('.')[0])

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            bucket_filename = tmp_file.name
            for name in potential_bucket_names:
                tmp_file.write(f"{name}\n")

        try:
            # Azure Blobs
            goblob_command = [config['tools']['goblob'], '-accounts', bucket_filename, '-silent']
            result = subprocess.run(goblob_command, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if line:
                    cloud_assets.append({'type': 'azure_blob', 'value': line})

            # S3 Buckets
            s3_command = [config['tools']['s3scanner'], '-provider', 'aws', '-bucket-file', bucket_filename]
            result = subprocess.run(s3_command, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if "is readable" in line or "exists" in line:
                    cloud_assets.append({'type': 's3_bucket', 'value': line.split()[0]})

            # GCP Buckets
            gcp_command = [config['tools']['s3scanner'], '-provider', 'gcp', '-bucket-file', bucket_filename]
            result = subprocess.run(gcp_command, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if "is readable" in line or "exists" in line:
                    cloud_assets.append({'type': 'gcp_bucket', 'value': line.split()[0]})

        except Exception as e:
            logger.error(f"An error occurred during cloud asset identification: {e}")
        finally:
            os.remove(bucket_filename)

        return {"cloud_assets": cloud_assets}
