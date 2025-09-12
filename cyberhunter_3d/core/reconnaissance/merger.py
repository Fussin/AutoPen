import re
import asyncio
import httpx
from typing import Set, List, Tuple, Optional, Dict, Any

from ...common.log import get_rich_logger as get_logger

logger = get_logger(__name__)

# A robust regex to extract domain names, including subdomains.
# It handles various formats and avoids matching invalid characters.
# It also handles domains with ports and paths.
DOMAIN_RE = re.compile(r'([a-zA-Z0-9\.\-\_]+\.[a-zA-Z]{2,})')

def extract_domains_from_text(text: str) -> Set[str]:
    """
    Extracts domain names from a block of text.

    Args:
        text: The text to parse.

    Returns:
        A set of unique domain names found in the text.
    """
    # This regex is an attempt to be more specific than the user's suggestion.
    # The user's regex `([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)` is good, but this one
    # is a bit more specific to FQDNs.
    domain_re = re.compile(r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}')

    # Find all matches and normalize them
    matches = set(m.group(0).lower().strip('.') for m in domain_re.finditer(text))
    return matches

def merge_and_dedupe(source_files: List[str]) -> Set[str]:
    """
    Merges multiple source files, extracts domain names, and deduplicates them.

    Args:
        source_files: A list of paths to the source files.

    Returns:
        A sorted set of unique domain names.
    """
    all_domains: Set[str] = set()
    logger.info(f"Merging and deduplicating {len(source_files)} source files.")

    for file_path in source_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                domains = extract_domains_from_text(text)
                logger.info(f"Extracted {len(domains)} domains from {file_path}")
                all_domains.update(domains)
        except FileNotFoundError:
            logger.warning(f"File not found: {file_path}. Skipping.")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")

    logger.info(f"Total unique domains found: {len(all_domains)}")
    return all_domains

async def check_url(url: str, sem: asyncio.Semaphore, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """
    Checks a single URL for liveness and returns its details.
    """
    protocols = ["https://", "http://"]
    for protocol in protocols:
        full_url = f"{protocol}{url}"
        async with sem:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
                try:
                    r = await client.get(full_url)
                    # A simple check to see if the response is valid
                    if r.status_code < 600:
                        title_match = re.search(r'<title>(.*?)</title>', r.text, re.IGNORECASE)
                        title = title_match.group(1).strip() if title_match else ""
                        return {
                            "url": full_url,
                            "status_code": r.status_code,
                            "server": r.headers.get('server'),
                            "content_length": len(r.content),
                            "title": title
                        }
                except (httpx.RequestError, httpx.TimeoutException) as e:
                    logger.debug(f"Error checking {full_url}: {e}")
                except Exception as e:
                    logger.error(f"An unexpected error occurred while checking {full_url}: {e}")
    return None


async def bulk_check_liveness(urls: Set[str], concurrency: int = 100) -> List[Dict[str, Any]]:
    """
    Checks a list of URLs for liveness concurrently.
    """
    sem = asyncio.Semaphore(concurrency)
    tasks = [check_url(u, sem) for u in urls]
    results = await asyncio.gather(*tasks)
    live_hosts = [res for res in results if res is not None]
    logger.info(f"Found {len(live_hosts)} live hosts out of {len(urls)}.")
    return live_hosts
