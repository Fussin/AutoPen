from typing import TypedDict, List, Optional, Dict

class Finding(TypedDict):
    """
    A structured dictionary to hold the results of a plugin's execution.
    It can represent both successful findings and failures.
    """
    tool: str
    phase: str
    target: str
    status: str  # 'success' or 'failed'
    evidence: Optional[Dict[str, str]]
    error: Optional[str]  # Description of the error if status is 'failed'
