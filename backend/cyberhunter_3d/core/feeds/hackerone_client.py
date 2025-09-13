import requests
from typing import List, Dict, Any

H1_API_BASE = "https://api.hackerone.com/v1"

def get_hackerone_scopes(username: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Fetches all program scopes for a given HackerOne user.
    """
    all_scopes = []
    auth = (username, api_key)

    # Get all programs the user is a member of
    programs_url = f"{H1_API_BASE}/programs"
    try:
        response = requests.get(programs_url, auth=auth)
        response.raise_for_status()
        programs = response.json().get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching H1 programs: {e}")
        return []

    # For each program, get its detailed scope
    for program_summary in programs:
        handle = program_summary.get("attributes", {}).get("handle")
        if not handle:
            continue

        details_url = f"{H1_API_BASE}/programs/{handle}"
        try:
            response = requests.get(details_url, auth=auth)
            response.raise_for_status()
            program_details = response.json()
            parsed_scope = _parse_program_scope(program_details)
            if parsed_scope:
                all_scopes.append(parsed_scope)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching details for H1 program {handle}: {e}")

    return all_scopes

def _parse_program_scope(program_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses the structured scope data from a single H1 program.
    """
    attributes = program_data.get("data", {}).get("attributes", {})
    relationships = program_data.get("data", {}).get("relationships", {})

    handle = attributes.get("handle")
    if not handle:
        return {}

    scopes = relationships.get("structured_scopes", {}).get("data", [])

    targets = []
    in_scope_rules = []
    out_of_scope_rules = []

    for scope in scopes:
        scope_attrs = scope.get("attributes", {})
        asset_identifier = scope_attrs.get("asset_identifier")
        instruction = scope_attrs.get("instruction", "")
        eligible = scope_attrs.get("eligible_for_submission", False)

        if asset_identifier:
            targets.append(asset_identifier)
            rule = f"{asset_identifier} - {instruction}" if instruction else asset_identifier
            if eligible:
                in_scope_rules.append(rule)
            else:
                out_of_scope_rules.append(rule)

    if not targets:
        return {}

    return {
        "name": handle,
        "targets": targets,
        "in_scope_rules": in_scope_rules,
        "out_of_scope_rules": out_of_scope_rules
    }
