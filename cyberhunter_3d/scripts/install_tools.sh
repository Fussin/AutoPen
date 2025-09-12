#!/usr/bin/env bash
# CyberHunter 3D - Mega Installer (100+ tools)
set -euo pipefail

# --- Dynamic Path Setup ---
# Get the directory of the currently executing script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Assume the project root is one level up from the scripts directory
PROJECT_ROOT="$( dirname "$SCRIPT_DIR" )"
AGENTS_DIR="${PROJECT_ROOT}/agents"


DEFAULT_HOME="${HOME}"
if [ "$(id -u)" -eq 0 ]; then
  DEFAULT_HOME="/root"
fi
GOPATH="${GOPATH:-$DEFAULT_HOME/go}"
GOBIN="$GOPATH/bin"
RESULTS_DIR="${DEFAULT_HOME}/.autopen"
PATH_UPDATED=false

info(){ echo -e "\033[1;34m[INFO]\033[0m $*"; }
ok(){ echo -e "\033[1;32m[OK]\033[0m $*"; }
warn(){ echo -e "\033[1;33m[WARN]\033[0m $*"; }

command_exists(){ command -v "$1" >/dev/null 2>&1; }

apt_install_if_missing(){
  for pkg in "$@"; do
    if dpkg -s "$pkg" >/dev/null 2>&1; then
      ok "APT: $pkg already installed"
    else
      info "APT: Installing $pkg"
      apt-get install -y "$pkg"
    fi
  done
}

go_install(){
  local pkg="$1"; local binname="$2"
  if command_exists "$binname"; then
    ok "Go: $binname already installed"
    return 0
  fi
  info "Go: Installing $binname from $pkg"
  mkdir -p "$GOPATH"
  GO111MODULE=on GOBIN="$GOBIN" go install "${pkg}@latest"
  if command_exists "$binname"; then
    ok "Go: installed $binname -> $(command -v $binname)"
  else
    warn "Go: $binname not found after install"
  fi
}

pipx_install(){
  local pkg="$1"; local binname="${2:-$1}"
  if command_exists "$binname"; then
    ok "pipx: $binname already installed"
    return 0
  fi
  info "pipx: Installing $pkg"
  pipx install --system-site-packages "$pkg" || pipx install "$pkg"
}

git_clone_if_missing(){
  local repo="$1"; local dest="$2"
  if [ -d "$dest" ]; then
    ok "Git: $dest already exists"
  else
    info "Git: Cloning $repo -> $dest"
    git clone --depth 1 "$repo" "$dest"
  fi
}

# -----------------------------------
# 🔍 Network Recon & Scanning
# -----------------------------------
info "Installing Network Recon Tools..."
apt_install_if_missing nmap masscan arp-scan nbtscan smbmap rpcbind
go_install "github.com/RustScan/RustScan" rustscan
go_install "github.com/owasp-amass/amass/v3/..." amass
go_install "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" subfinder
git_clone_if_missing "https://github.com/Tib3rius/AutoRecon.git" "${RESULTS_DIR}/AutoRecon"
git_clone_if_missing "https://github.com/fwaeytens/dnsenum.git" "${RESULTS_DIR}/dnsenum"
git_clone_if_missing "https://github.com/lgandx/Responder.git" "${RESULTS_DIR}/Responder"
git_clone_if_missing "https://github.com/cddmp/enum4linux-ng.git" "${RESULTS_DIR}/enum4linux-ng"

# -----------------------------------
# 🌐 Web Application Security
# -----------------------------------
info "Installing Web Application Security Tools..."
go_install "github.com/OJ/gobuster/v3" gobuster
pipx_install "dirsearch" "dirsearch"
# cargo install feroxbuster || true
go_install "github.com/ffuf/ffuf" ffuf
apt_install_if_missing dirb nikto
go_install "github.com/projectdiscovery/httpx/cmd/httpx" httpx
go_install "github.com/projectdiscovery/katana/cmd/katana" katana
go_install "github.com/hakluke/hakrawler" hakrawler
go_install "github.com/tomnomnom/gau/v2/cmd/gau" gau
go_install "github.com/tomnomnom/waybackurls" waybackurls
go_install "github.com/projectdiscovery/nuclei/v2/cmd/nuclei" nuclei
pipx_install "sqlmap-dev" "sqlmap"
# gem install wpscan || true
pipx_install "arjun" "arjun"
pipx_install "paramspider" "paramspider"
go_install "github.com/hahwul/dalfox/v2" dalfox
pipx_install "wafw00f" "wafw00f"
apt_install_if_missing whatweb
pipx_install "wfuzz" "wfuzz"
pipx_install "commix" "commix"
pipx_install "nosqlmap" "nosqlmap"
pipx_install "tplmap" "tplmap"
# SSL/TLS tools
apt_install_if_missing testssl.sh sslscan
pipx_install "sslyze" "sslyze"
# Helpers
go_install "github.com/tomnomnom/anew" anew
go_install "github.com/tomnomnom/qsreplace" qsreplace
pipx_install "uro" "uro"

# -----------------------------------
# ☁️ Cloud & Container Security
# -----------------------------------
info "Installing Cloud & Container Tools..."
pipx_install "prowler" "prowler"
git_clone_if_missing "https://github.com/nccgroup/ScoutSuite.git" "${RESULTS_DIR}/ScoutSuite"
git_clone_if_missing "https://github.com/duo-labs/cloudmapper.git" "${RESULTS_DIR}/cloudmapper"
git_clone_if_missing "https://github.com/RhinoSecurityLabs/pacu.git" "${RESULTS_DIR}/pacu"
go_install "github.com/aquasecurity/trivy/cmd/trivy" trivy
git_clone_if_missing "https://github.com/quay/clair.git" "${RESULTS_DIR}/clair"
pipx_install "kube-hunter" "kube-hunter"
pipx_install "kube-bench" "kube-bench"
git_clone_if_missing "https://github.com/docker/docker-bench-security.git" "${RESULTS_DIR}/docker-bench-security"
git_clone_if_missing "https://github.com/falcosecurity/falco.git" "${RESULTS_DIR}/falco"
pipx_install "checkov" "checkov"
pipx_install "terrascan" "terrascan"
git_clone_if_missing "https://github.com/aquasecurity/cloudsploit.git" "${RESULTS_DIR}/cloudsploit"

# CLIs
apt_install_if_missing awscli azure-cli google-cloud-sdk kubectl helm

# -----------------------------------
# 🔥 Bug Bounty & OSINT
# -----------------------------------
info "Installing Bug Bounty & OSINT Tools..."
git_clone_if_missing "https://github.com/michenriksen/aquatone.git" "${RESULTS_DIR}/aquatone"
go_install "github.com/haccer/subjack" subjack
pipx_install "sherlock" "sherlock"
git_clone_if_missing "https://github.com/qeeqbox/social-analyzer.git" "${RESULTS_DIR}/social-analyzer"
git_clone_if_missing "https://github.com/lanmaster53/recon-ng.git" "${RESULTS_DIR}/recon-ng"
warn "Maltego: manual download needed from https://www.maltego.com/"
git_clone_if_missing "https://github.com/smicallef/spiderfoot.git" "${RESULTS_DIR}/spiderfoot"
pipx_install "shodan-cli" "shodan"
pipx_install "censys-cli" "censys"
pipx_install "trufflehog" "trufflehog"

# -----------------------------------
# 🤖 AI Agents (placeholders)
# -----------------------------------
info "Adding AI Agent stubs..."
mkdir -p "$AGENTS_DIR"
for agent in IntelligentDecisionEngine BugBountyWorkflowManager CTFWorkflowManager CVEIntelligenceManager \
             AIExploitGenerator VulnerabilityCorrelator TechnologyDetector RateLimitDetector \
             FailureRecoverySystem PerformanceMonitor ParameterOptimizer GracefulDegradation; do
  echo "#!/usr/bin/env bash" > "$AGENTS_DIR/${agent}.sh"
  echo "echo '[AI Agent] ${agent} - Placeholder Script'" >> "$AGENTS_DIR/${agent}.sh"
  chmod +x "$AGENTS_DIR/${agent}.sh"
done

# -----------------------------------
# Wrap-up
# -----------------------------------
ok "Mega Installer Finished!"
echo "All tools cloned/installed into: ${RESULTS_DIR}"
warn "Some tools like Maltego, Ghidra, or GUI-based tools (Aquatone, SpiderFoot) may require manual setup."
warn "Please add GOBIN to your shell's rc file (e.g., ~/.bashrc, ~/.zshrc): export PATH=\$PATH:$GOBIN"
