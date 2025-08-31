#!/bin/bash

# Exit on any error
set -e

# --- Check for root privileges ---
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo, as this script needs to install packages."
  exit 1
fi

echo "Starting installation of CyberHunter 3D V2 reconnaissance tools..."

# --- System package installation (apt) ---
echo "Installing system packages..."
apt-get update
apt-get install -y nmap gobuster libpcap-dev firefox git wget unzip seclists wkhtmltopdf
echo "System packages installed successfully."

# --- Go tools installation ---
echo "Checking for Go installation..."
if ! [ -x "$(command -v go)" ]; then
  echo "Error: Go is not installed. Please install Go and try again." >&2
  exit 1
fi

echo "Go is installed. Version: $(go version)"
echo "Installing Go-based tools... This may take a few minutes."

# Add go bin to path for this session
export PATH=$PATH:$(go env GOPATH)/bin

# Passive Engine
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest
go install -v github.com/tomnomnom/assetfinder@latest

# Active Engine
# massdns is a dependency for puredns
echo "Installing massdns..."
git clone https://github.com/blechschmidt/massdns.git
cd massdns
make
make install
cd ..
rm -rf massdns
echo "massdns installed successfully."
go install -v github.com/d3mondev/puredns/v2@latest

# Permutation Engine
go install -v github.com/Josue87/gotator@latest

# JS/Code Analysis Engine
go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest

# Live Host Detection / Visual Recon
go install -v github.com/sensepost/gowitness@latest
echo "Installing Aquatone..."
AQUATONE_VERSION="1.7.0"
wget "https://github.com/michenriksen/aquatone/releases/download/v${AQUATONE_VERSION}/aquatone_linux_amd64_${AQUATONE_VERSION}.zip"
unzip "aquatone_linux_amd64_${AQUATONE_VERSION}.zip"
mv aquatone /usr/local/bin/
rm "aquatone_linux_amd64_${AQUATONE_VERSION}.zip"
echo "Aquatone installed successfully."

# Technology Fingerprinting & Port Scanning
go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest

# Cloud Asset Identification
go install -v github.com/Macmod/goblob@latest
go install -v github.com/sa7mon/s3scanner@latest

# Other tools from previous version
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/PentestPad/subzy@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install -v github.com/jaeles-project/gospider@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
go install -v github.com/tomnomnom/waybackurls@latest
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install -v github.com/hakluke/hakrawler@latest
go install -v github.com/tomnomnom/unfurl@latest


echo "Go-based tools installed successfully."

# --- Python tools installation ---
echo "Checking for Python and pip installation..."
if ! [ -x "$(command -v python3)" ] || ! [ -x "$(command -v pip3)" ]; then
  echo "Error: python3 and/or pip3 are not installed. Please install them and try again." >&2
  exit 1
fi

echo "Python and pip are installed."

# Permutation Engine
pip3 install dnsgen

# JS/Code Analysis
echo "Installing LinkFinder..."
git clone https://github.com/GerbenJavado/LinkFinder.git
cd LinkFinder
pip3 install -r requirements.txt
python3 setup.py install
cd ..
rm -rf LinkFinder
echo "LinkFinder installed successfully."

# Technology Fingerprinting
echo "Installing Wappalyzer dependencies..."
# geckodriver installation
GECKODRIVER_VERSION="v0.34.0" # Check for latest version
wget "https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz"
tar -xvzf "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz"
chmod +x geckodriver
mv geckodriver /usr/local/bin/
rm "geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz"
pip3 install pipx
pipx install wappalyzer

# GitHub Dorking
echo "Installing gh-dork..."
git clone https://github.com/molly/gh-dork.git
cd gh-dork
pip3 install -r requirements.txt
cd ..
# We will leave the gh-dork directory in the root for now
echo "gh-dork installed successfully."

# Other tools from previous version
apt-get install -y sublist3r

echo "Python tools installed successfully."

echo "All V2 reconnaissance tools have been installed."
echo "Make sure to add '$(go env GOPATH)/bin' to your system's PATH environment variable."
