import requests
import json
from typing import List, Dict, Any

DIODB_URL = "https://github.com/disclose/diodb/raw/master/program-list.json"

def get_diodb_programs() -> List[Dict[str, Any]]:
    """
    Fetches all program scopes from the disclose.io database.
    """
    programs = []
    try:
        response = requests.get(DIODB_URL)
        response.raise_for_status()
        data = response.json()

        for program_data in data:
            program_name = program_data.get('program_name')
            policy_url = program_data.get('policy_url')

            if program_name and policy_url:
                programs.append({
                    'name': program_name,
                    'targets': [policy_url],
                    'in_scope_rules': '', # Placeholder
                    'out_of_scope_rules': '', # Placeholder
                })

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with diodb: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from diodb: {e}")
        return []

    return programs

if __name__ == '__main__':
    programs = get_diodb_programs()
    if programs:
        print(f"Found {len(programs)} programs in diodb.")
        for program in programs[:5]: # Print first 5 for brevity
            print(f"  - {program.get('name')}: {program.get('targets')}")
