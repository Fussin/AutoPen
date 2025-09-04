import requests
import json
from typing import List, Set

def get_subdomains_from_crtsh(domain: str) -> List[str]:
    """
    Fetches subdomains for a given domain from crt.sh.

    :param domain: The domain to query.
    :return: A list of unique subdomains.
    """
    subdomains: Set[str] = set()
    url = f"https://crt.sh/?q=%.{domain}&output=json"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        # crt.sh returns a single JSON array
        try:
            cert_data_list = response.json()
            for cert_data in cert_data_list:
                names = cert_data.get('name_value', '')
                for name in names.split('\n'):
                    cleaned_name = name.strip().lower()
                    if cleaned_name.startswith('*.'):
                        cleaned_name = cleaned_name[2:]
                    if cleaned_name.endswith(f".{domain}"):
                        subdomains.add(cleaned_name)
        except json.JSONDecodeError:
            print("Error decoding JSON from crt.sh")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from crt.sh: {e}")
        return []

    return list(subdomains)

if __name__ == '__main__':
    # For direct testing
    test_domain = "example.com"
    print(f"Fetching subdomains for: {test_domain}")
    results = get_subdomains_from_crtsh(test_domain)
    if results:
        print(f"Found {len(results)} unique subdomains.")
        for sub in sorted(results):
            print(f"  - {sub}")
    else:
        print("No subdomains found or an error occurred.")
