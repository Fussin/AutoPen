import requests
from typing import List, Dict, Any

H1_API_BASE_URL = "https://api.hackerone.com/v1"

def get_hackerone_scopes(api_user: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Fetches all program scopes for a given HackerOne user.

    :param api_user: The HackerOne API username.
    :param api_key: The HackerOne API key.
    :return: A list of dictionaries, where each dictionary represents a program
             and contains its targets and scope rules.
    """
    programs = []
    print("Fetching programs from HackerOne...")

    try:
        # First, get the list of programs the user is associated with
        response = requests.get(
            f"{H1_API_BASE_URL}/hackers/programs",
            auth=(api_user, api_key),
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()

        program_data = response.json().get('data', [])
        print(f"Found {len(program_data)} programs.")

        for program in program_data:
            handle = program.get('attributes', {}).get('handle')
            if not handle:
                continue

            # For each program, get its detailed scope
            print(f"Fetching scope for program: {handle}")
            scope_response = requests.get(
                f"{H1_API_BASE_URL}/programs/{handle}",
                auth=(api_user, api_key),
                headers={'Accept': 'application/json'}
            )
            scope_response.raise_for_status()

            structured_scope = _parse_program_scope(scope_response.json())
            if structured_scope:
                programs.append(structured_scope)

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with HackerOne API: {e}")
        return []

    return programs

def _parse_program_scope(program_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parses the detailed program JSON to extract targets and scope rules.
    """
    attributes = program_details.get('data', {}).get('attributes', {})
    relationships = program_details.get('data', {}).get('relationships', {})

    program_name = attributes.get('handle', 'unknown-program')

    targets = []
    in_scope = []
    out_of_scope = []

    # Extract structured scopes (assets)
    structured_scopes = relationships.get('structured_scopes', {}).get('data', [])
    for scope in structured_scopes:
        scope_attr = scope.get('attributes', {})
        asset_identifier = scope_attr.get('asset_identifier')
        asset_type = scope_attr.get('asset_type')

        if asset_identifier:
            # We can map H1 asset types to our internal types if needed
            # For now, we'll just pass them through to our parser
            targets.append(asset_identifier)

            if scope_attr.get('eligible_for_submission', False):
                in_scope.append(f"{asset_identifier} - {scope_attr.get('instruction', '')}")
            else:
                out_of_scope.append(f"{asset_identifier} - {scope_attr.get('instruction', '')}")

    if not targets:
        return {}

    return {
        'name': program_name,
        'targets': targets,
        'in_scope_rules': "\n".join(in_scope),
        'out_of_scope_rules': "\n".join(out_of_scope),
    }

if __name__ == '__main__':
    # For direct testing, requires H1_USER and H1_KEY environment variables
    import os
    h1_user = os.environ.get("H1_USER")
    h1_key = os.environ.get("H1_KEY")
    if h1_user and h1_key:
        scopes = get_hackerone_scopes(h1_user, h1_key)
        if scopes:
            print("\n--- Fetched Scopes ---")
            for scope in scopes:
                print(f"\nProgram: {scope['name']}")
                print(f"  Targets: {len(scope['targets'])}")
    else:
        print("Set H1_USER and H1_KEY environment variables to run this test.")
