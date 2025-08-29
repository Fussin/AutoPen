from collections import defaultdict
from typing import Dict, List

def correlate_tech_stack(tech_results: Dict[str, Dict]) -> Dict[str, List[str]]:
    """
    Correlates hosts by their technology stack.
    Returns a dictionary where keys are string representations of tech stacks
    and values are lists of hosts with that stack.
    """
    tech_clusters = defaultdict(list)
    for host, data in tech_results.items():
        # Create a canonical representation of the tech stack (sorted tuple of technologies)
        tech_stack = tuple(sorted(data.get('technologies', [])))
        if tech_stack:
            # The key must be a string
            tech_clusters[str(tech_stack)].append(host)

    # Filter out clusters with only one host, as they are not "clusters".
    return {stack: hosts for stack, hosts in tech_clusters.items() if len(hosts) > 1}
