#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -e

echo "[INFO] Starting CyberHunter 3D tool installation..."

# --- 1. Install System Dependencies ---
echo "[INFO] Installing system packages (git, golang, build-essential, etc.)..."
apt-get update
apt-get install -y golang-go build-essential git curl jq \
    libpcap-dev libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libcairo2 libffi-dev libgdk-pixbuf2.0-0 libpango-1.0-0 shared-mime-info

# --- 2. Setup Go Environment ---
echo "[INFO] Setting up Go environment variables..."
export GOPATH="${HOME}/go"
export GOBIN="${GOPATH}/bin"
mkdir -p "$GOBIN"
# Add to .bashrc to make it permanent for future sessions
echo 'export GOPATH="$HOME/go"' >> /root/.bashrc
echo 'export PATH="$PATH:$HOME/go/bin"' >> /root/.bashrc
export PATH="$PATH:$GOBIN"

# --- 3. Install Go-based Recon Tools ---
echo "[INFO] Installing Go-based reconnaissance tools..."
go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest
go install -v github.com/tomnomnom/assetfinder@latest
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
go install -v github.com/hakluke/hakrawler@latest
go install -v github.com/ffuf/ffuf/v2@latest
go install -v github.com/lc/gau/v2/cmd/gau@latest
go install -v github.com/tomnomnom/waybackurls@latest
go install -v github.com/hahwul/dalfox/v2@latest
go install -v github.com/OJ/gobuster/v3@latest

echo "[INFO] Verifying installation of key tools..."
which amass subfinder httpx nuclei

echo "[SUCCESS] Tool installation script finished."
