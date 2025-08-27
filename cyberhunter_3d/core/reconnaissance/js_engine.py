import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List

def run_command(command: List[str], domain: str) -> Set[str]:
    """
    Runs a command, captures its output, and returns a set of subdomains.
    """
    results = set()
    go_path = os.path.join(os.path.expanduser("~"), "go", "bin")
    # Create a temporary file to store the output of the command
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        output_filename = tmp_file.name

    try:
        # Prepend the path to the Go tools if it's a go tool
        if command[0] in ['nuclei']:
            command[0] = os.path.join(go_path, command[0])

        # Format the command with the domain and output file path
        formatted_command = [part.format(domain=domain, output_file=output_filename) for part in command]

        subprocess.run(formatted_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Read the output from the temporary file
        with open(output_filename, 'r') as f_in:
            for line in f_in:
                # Basic cleaning
                line = line.strip()
                if line:
                    results.add(line)

    except FileNotFoundError as e:
        tool_name = command[0]
        print(f"Error: Tool '{tool_name}' not found. Please ensure it is installed and in your PATH. Details: {e}")
    except subprocess.CalledProcessError as e:
        tool_name = command[0]
        print(f"Error running tool '{tool_name}': {e}")
    finally:
        os.remove(output_filename)

    return results

def run_js_enumeration(live_hosts: Set[str]) -> Set[str]:
    """
    Runs JS/Code analysis tools in parallel.
    """
    print(f"Starting JS/Code analysis for {len(live_hosts)} live hosts...")

    if not live_hosts:
        print("No live hosts to analyze. Skipping JS/Code analysis engine.")
        return set()

    all_results = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # LinkFinder
        for host in live_hosts:
            command = ['python3', 'linkfinder.py', '-i', host, '-o', 'cli']
            future = executor.submit(run_command, command, host)
            try:
                results = future.result()
                if results:
                    print(f"Found {len(results)} endpoints in JS files for {host}")
                    all_results.update(results)
            except Exception as exc:
                print(f"LinkFinder generated an exception for {host}: {exc}")

        # Nuclei - js-secrets
        # Create a temporary file with the live hosts
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            host_filename = tmp_file.name
            for host in live_hosts:
                tmp_file.write(f"{host}\n")

        command = ['nuclei', '-l', host_filename, '-t', 'technologies/javascript/js-secrets.yaml', '-o', '{output_file}', '-silent']
        future = executor.submit(run_command, command, "") # domain is not used here
        try:
            results = future.result()
            if results:
                print(f"Found {len(results)} secrets in JS files.")
                all_results.update(results)
        except Exception as exc:
            print(f"Nuclei js-secrets generated an exception: {exc}")
        finally:
            os.remove(host_filename)


    print(f"Total unique findings from JS/Code analysis: {len(all_results)}")
    return all_results

def run_github_dorking(subdomains: Set[str]) -> List[str]:
    """
    Performs GitHub dorking to find sensitive information.
    """
    print(f"Starting GitHub dorking for {len(subdomains)} subdomains...")

    if not subdomains:
        print("No subdomains to dork. Skipping GitHub dorking.")
        return []

    # We need a file with dorks. I'll assume a common one exists.
    dorks_file = "gh-dork/dorks.txt"
    if not os.path.exists(dorks_file):
        print(f"Dorks file not found at {dorks_file}. Skipping GitHub dorking.")
        return []

    # Create a temporary file with the subdomains to use as orgs
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        orgs_filename = tmp_file.name
        for sub in subdomains:
            # We can treat each subdomain as a potential organization name
            if '.' in sub:
                org = sub.split('.')[-2] # a.b.c -> b
                tmp_file.write(f"{org}\n")

    findings = []
    try:
        gh_dork_command = [
            'python3', 'gh-dork/gh-dork.py',
            '-d', dorks_file,
            '-of', orgs_filename,
            '-o', 'gh_dork_results'
        ]
        subprocess.run(gh_dork_command)

        # The results are saved to files in the 'gh_dork_results' directory.
        # We can parse these files to get the findings.
        if os.path.exists('gh_dork_results'):
            for filename in os.listdir('gh_dork_results'):
                with open(os.path.join('gh_dork_results', filename), 'r') as f:
                    findings.extend(f.readlines())

    except FileNotFoundError:
        print("Error: 'gh-dork.py' not found. Please ensure it is installed.")
    except Exception as e:
        print(f"An error occurred during GitHub dorking: {e}")
    finally:
        os.remove(orgs_filename)
        if os.path.exists('gh_dork_results'):
            import shutil
            shutil.rmtree('gh_dork_results')

    print(f"Found {len(findings)} potential findings from GitHub dorking.")
    return findings
