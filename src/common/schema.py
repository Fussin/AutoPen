from typing import TypedDict, List, Optional

class Evidence(TypedDict, total=False):
    path: Optional[str]
    snippet: Optional[str]
    poc: Optional[str]

class Vulnerability(TypedDict, total=False):
    id: Optional[str]
    name: str
    severity: str # info, low, medium, high, critical

class Fingerprints(TypedDict, total=False):
    tech: List[str]
    services: List[str]
    ports: List[int]

class Finding(TypedDict):
    target: str
    phase: str # recon, url, vuln, network, osint
    tool: str
    timestamp: str
    evidence: Evidence
    vuln: Vulnerability
    tags: List[str]
    fingerprints: Fingerprints
