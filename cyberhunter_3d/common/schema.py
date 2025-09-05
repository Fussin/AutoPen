from typing import TypedDict, List, Optional, Dict

class Finding(TypedDict):
    tool: str
    phase: str
    target: str
    evidence: Dict[str, str]
