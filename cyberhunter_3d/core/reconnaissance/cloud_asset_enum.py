import subprocess
import tempfile
import os
from typing import Set, List, Dict
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config

config = load_config()
logger = setup_logger('CloudAssetEngine', 'cloud_asset.log')

def find_cloud_assets(subdomains: Set[str]) -> List[Dict[str, str]]:
    """
    Finds cloud assets (S3 buckets, Azure blobs, GCP buckets) for a list of subdomains.
    """
    logger.info(f"Starting cloud asset identification for {len(subdomains)} subdomains...")

    if not subdomains:
        logger.warning("No subdomains to check for cloud assets.")
        return []

    cloud_assets = []

    # Generate potential bucket names from subdomains
    potential_bucket_names = set()
    for sub in subdomains:
        # A simple strategy: use the full subdomain and the first part of the subdomain
        potential_bucket_names.add(sub)
        if '.' in sub:
            potential_bucket_names.add(sub.split('.')[0])

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        bucket_filename = tmp_file.name
        for name in potential_bucket_names:
            tmp_file.write(f"{name}\n")

    try:
        # Azure Blobs with goblob
        logger.info("Checking for Azure blobs...")
        goblob_command = [config['tools']['goblob'], '-accounts', bucket_filename, '-silent']
        result = subprocess.run(goblob_command, capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if line:
                cloud_assets.append({'type': 'azure_blob', 'value': line})

        # S3 Buckets with S3Scanner
        logger.info("Checking for S3 buckets...")
        s3_command = [config['tools']['s3scanner'], '-provider', 'aws', '-bucket-file', bucket_filename]
        result = subprocess.run(s3_command, capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if "is readable" in line or "exists" in line:
                cloud_assets.append({'type': 's3_bucket', 'value': line.split()[0]})

        # GCP Buckets with S3Scanner
        logger.info("Checking for GCP buckets...")
        gcp_command = [config['tools']['s3scanner'], '-provider', 'gcp', '-bucket-file', bucket_filename]
        result = subprocess.run(gcp_command, capture_output=True, text=True)
        for line in result.stdout.strip().split('\n'):
            if "is readable" in line or "exists" in line:
                cloud_assets.append({'type': 'gcp_bucket', 'value': line.split()[0]})

    except FileNotFoundError as e:
        tool_name = str(e).split("'")[1]
        logger.error(f"Error: Tool '{tool_name}' not found.")
    except Exception as e:
        logger.error(f"An error occurred during cloud asset identification: {e}")
    finally:
        os.remove(bucket_filename)

    logger.info(f"Found {len(cloud_assets)} potential cloud assets.")
    return cloud_assets
