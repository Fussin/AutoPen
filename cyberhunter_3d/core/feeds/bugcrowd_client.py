import requests
from typing import List, Dict, Any

BUGCROWD_API_BASE_URL = "https://api.bugcrowd.com"

def get_bugcrowd_programs(api_user: str, api_key: str) -> List[Dict[str, Any]]:
    """
    Fetches all program scopes from Bugcrowd.
    """
    programs = []
    headers = {
        'Accept': 'application/vnd.bugcrowd.v4+json',
        'Authorization': f'Token {api_user}:{api_key}'
    }

    params = {
        'include': 'target_groups.targets',
        'fields[program]': 'name,target_groups',
        'fields[target_group]': 'name,targets',
        'fields[target]': 'name,category',
    }

    url = f"{BUGCROWD_API_BASE_URL}/programs"

    while url:
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            included_data = { (item['type'], item['id']): item for item in data.get('included', []) }

            for program_data in data.get('data', []):
                attributes = program_data.get('attributes', {})
                program_name = attributes.get('name', 'unknown-program')

                targets = []
                in_scope_rules = []

                target_group_refs = program_data.get('relationships', {}).get('target_groups', {}).get('data', [])
                for tg_ref in target_group_refs:
                    tg_id = (tg_ref['type'], tg_ref['id'])
                    target_group = included_data.get(tg_id)
                    if not target_group:
                        continue

                    target_refs = target_group.get('relationships', {}).get('targets', {}).get('data', [])
                    for t_ref in target_refs:
                        t_id = (t_ref['type'], t_ref['id'])
                        target = included_data.get(t_id)
                        if target:
                            target_name = target.get('attributes', {}).get('name')
                            if target_name:
                                targets.append(target_name)
                                in_scope_rules.append(target_name)

                programs.append({
                    'name': program_name,
                    'targets': targets,
                    'in_scope_rules': "\n".join(in_scope_rules),
                    'out_of_scope_rules': '', # Not provided in this view
                })

            # Handle pagination
            url = data.get('links', {}).get('next')
            params = {} # The next URL from the API includes all the params.

        except requests.exceptions.RequestException as e:
            print(f"Error communicating with Bugcrowd API: {e}")
            return []

    return programs

if __name__ == '__main__':
    # For direct testing, requires BUGCROWD_USER and BUGCROWD_KEY environment variables
    import os
    bc_user = os.environ.get("BUGCROWD_USER")
    bc_key = os.environ.get("BUGCROWD_KEY")
    if bc_user and bc_key:
        programs = get_bugcrowd_programs(bc_user, bc_key)
        if programs:
            print("\n--- Fetched Programs ---")
            for program in programs:
                print(f"\nProgram: {program.get('name')}")
                print(f"  Targets: {len(program.get('targets', []))}")
    else:
        print("Set BUGCROWD_USER and BUGCROWD_KEY environment variables to run this test.")
