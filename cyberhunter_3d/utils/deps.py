# cyberhunter_3d/utils/deps.py
import shutil, subprocess, os

TOOLS = {
    'amass': 'go install github.com/owasp-amass/amass/v3/...@latest',
    'subfinder': 'go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest',
    'hakrawler': 'go install github.com/hakluke/hakrawler@latest',
    'httpx': 'go install github.com/projectdiscovery/httpx/cmd/httpx@latest',
    'nuclei': 'go install github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest'
}

def which(tool):
    return shutil.which(tool)

def check_all(auto_install=False):
    missing=[]
    for t, cmd in TOOLS.items():
        if not which(t):
            missing.append((t, cmd))
    if not missing:
        print("[+] All tools found")
        return True
    print("[!] Missing:", ', '.join(t for t,_ in missing))
    for t, cmd in missing:
        print(f"Install {t}: {cmd}")
        if auto_install:
            subprocess.check_call(cmd, shell=True, env=os.environ)
    return False
