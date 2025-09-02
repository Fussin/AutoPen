import json
from typing import List, Dict, Any

def format_subdomains(hosts: List[Dict[str, Any]]) -> List[str]:
    """Extracts subdomains from a list of host dictionaries."""
    return [host['host'] for host in hosts]

def format_alive_domains(hosts: List[Dict[str, Any]]) -> List[str]:
    """Extracts alive domains from a list of host dictionaries."""
    return [host['host'] for host in hosts if host.get('alive')]

def format_dead_domains(hosts: List[Dict[str, Any]]) -> List[str]:
    """Extracts dead domains from a list of host dictionaries."""
    return [host['host'] for host in hosts if not host.get('alive')]
