import concurrent.futures
from typing import Set, List, Dict

from .utils import get_logger
from ...plugins.cloud.goblob import GoblobPlugin
from ...plugins.cloud.s3scanner import S3ScannerPlugin
from ...common.schema import Finding

logger = get_logger(__name__)

def find_cloud_assets(subdomains: Set[str]) -> List[Finding]:
    """
    Finds cloud assets by orchestrating cloud asset enumeration plugins.
    """
    logger.info(f"Starting cloud asset identification for {len(subdomains)} subdomains...")
    if not subdomains:
        logger.warning("No subdomains to check for cloud assets.")
        return []

    # Generate potential bucket names from subdomains
    potential_bucket_names = set()
    for sub in subdomains:
        potential_bucket_names.add(sub)
        if '.' in sub:
            potential_bucket_names.add(sub.split('.')[0])

    potential_names_list = list(potential_bucket_names)
    all_findings: List[Finding] = []

    goblob_plugin = GoblobPlugin()
    s3scanner_plugin = S3ScannerPlugin()

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Submit scanner tasks
        future_goblob = executor.submit(goblob_plugin.run, potential_names_list)
        future_s3_aws = executor.submit(s3scanner_plugin.run, potential_names_list, provider='aws')
        future_s3_gcp = executor.submit(s3scanner_plugin.run, potential_names_list, provider='gcp')

        # Process results as they complete
        for future in concurrent.futures.as_completed([future_goblob, future_s3_aws, future_s3_gcp]):
            try:
                all_findings.extend(future.result())
            except Exception as e:
                logger.error(f"A cloud asset plugin task generated an exception: {e}")

    logger.info(f"Found {len(all_findings)} potential cloud assets.")
    return all_findings
