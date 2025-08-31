import json
import os
import click

@click.command()
@click.option('--template-id', required=True, help='The Nuclei template ID of the finding.')
@click.option('--host', required=True, help='The host where the finding occurred.')
def mark_as_false_positive(template_id, host):
    """
    Marks a specific finding as a false positive by adding it to the database.
    """
    config_dir = os.path.dirname(os.path.join(os.path.dirname(__file__), '..', 'config', 'recon_config.yaml'))
    fp_db_path = os.path.join(config_dir, 'false_positives.json')

    # Load existing false positives
    if os.path.exists(fp_db_path):
        with open(fp_db_path, 'r') as f:
            try:
                fp_list = json.load(f)
            except json.JSONDecodeError:
                fp_list = []
    else:
        fp_list = []

    # Create the new entry
    new_fp = {
        "template-id": template_id,
        "host": host
    }

    # Add if not already present
    if new_fp not in fp_list:
        fp_list.append(new_fp)
        with open(fp_db_path, 'w') as f:
            json.dump(fp_list, f, indent=4)
        print(f"Successfully marked finding on '{host}' from template '{template_id}' as a false positive.")
    else:
        print("This finding is already marked as a false positive.")

if __name__ == '__main__':
    mark_as_false_positive()
