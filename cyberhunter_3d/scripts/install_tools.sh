#!/usr/bin/env bash
set -e

export GOPATH="${HOME}/go"
export PATH="$PATH:$GOPATH/bin"

# --- Check for root privileges ---
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo, as this script needs to install packages."
  exit 1
fi

apt update
apt install -y git golang-go python3-venv python3-pip build-essential tesseract-ocr wkhtmltopdf nmap gobuster libpcap-dev firefox wget unzip sqlmap seclists

go_install() {
  pkg="$1"
  binname="$2"
  if ! command -v "$binname" >/dev/null 2>&1; then
    echo "[*] Installing $binname (go: $pkg)"
    GO111MODULE=on go install "$pkg@latest"
  else
    echo "[+] $binname already present"
  fi
}

go_install "github.com/owasp-amass/amass/v3/..." amass
go_install "github.com/projectdiscovery/subfinder/v2/cmd/subfinder" subfinder
go_install "github.com/tomnomnom/assetfinder" assetfinder
go_install "github.com/hakluke/hakrawler" hakrawler
go_install "github.com/projectdiscovery/httpx/cmd/httpx" httpx
go_install "github.com/projectdiscovery/nuclei/v2/cmd/nuclei" nuclei
go_install "github.com/d3mondev/puredns/v2" puredns
go_install "github.com/Josue87/gotator" gotator
go_install "github.com/sensepost/gowitness" gowitness
go_install "github.com/projectdiscovery/naabu/v2/cmd/naabu" naabu
go_install "github.com/Macmod/goblob" goblob
go_install "github.com/sa7mon/s3scanner" s3scanner
go_install "github.com/PentestPad/subzy" subzy
go_install "github.com/projectdiscovery/dnsx/cmd/dnsx" dnsx
go_install "github.com/jaeles-project/gospider" gospider
go_install "github.com/lc/gau/v2/cmd/gau" gau

# massdns is a dependency for puredns
if ! command -v "massdns" >/dev/null 2>&1; then
    echo "Installing massdns..."
    git clone https://github.com/blechschmidt/massdns.git
    cd massdns
    make
    make install
    cd ..
    rm -rf massdns
    echo "massdns installed successfully."
else
    echo "[+] massdns already present"
fi

# Aquatone
if ! command -v "aquatone" >/dev/null 2>&1; then
    echo "Installing Aquatone..."
    AQUATONE_VERSION="1.7.0"
    wget "https://github.com/michenriksen/aquatone/releases/download/v${AQUATONE_VERSION}/aquatone_linux_amd64_${AQUATONE_VERSION}.zip"
    unzip "aquatone_linux_amd64_${AQUATONE_VERSION}.zip"
    mv aquatone /usr/local/bin/
    rm "aquatone_linux_amd64_${AQUATONE_VERSION}.zip"
    echo "Aquatone installed successfully."
else
    echo "[+] aquatone already present"
fi


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
if ! command -v "linkfinder" >/dev/null 2>&1; then
    echo "Installing LinkFinder..."
    git clone https://github.com/GerbenJavado/LinkFinder.git
    cd LinkFinder
    pip3 install -r requirements.txt
    python3 setup.py install
    cd ..
    rm -rf LinkFinder
    echo "LinkFinder installed successfully."
else
    echo "[+] LinkFinder already present"
fi

# Technology Fingerprinting
if ! command -v "wappalyzer" >/dev/null 2>&1; then
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
else
    echo "[+] wappalyzer already present"
fi

# GitHub Dorking
if ! command -v "gh-dork" >/dev/null 2>&1; then
    echo "Installing gh-dork..."
    git clone https://github.com/molly/gh-dork.git
    cd gh-dork
    pip3 install -r requirements.txt
    ln -s "$(pwd)/gh-dork" /usr/local/bin/gh-dork
    cd ..
    echo "gh-dork installed successfully."
else
    echo "[+] gh-dork already present"
fi

# Other tools from previous version
apt-get install -y sublist3r

echo "Python tools installed successfully."

echo "All V2 reconnaissance tools have been installed."
echo "Make sure to add '$(go env GOPATH)/bin' to your system's PATH environment variable."
