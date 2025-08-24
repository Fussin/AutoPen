#!/bin/bash

# Exit on any error
set -e

echo "Starting installation of CyberHunter 3D reconnaissance tools..."

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

# Install subfinder
echo "Installing subfinder..."
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest

# Install amass
echo "Installing amass..."
go install -v github.com/OWASP/Amass/v3/cmd/amass@latest

# Install assetfinder
echo "Installing assetfinder..."
go install -v github.com/tomnomnom/assetfinder@latest

echo "Go-based tools installed successfully."

# --- Python tools installation ---
echo "Checking for Python and pip installation..."
if ! [ -x "$(command -v python3)" ] || ! [ -x "$(command -v pip3)" ]; then
  echo "Error: python3 and/or pip3 are not installed. Please install them and try again." >&2
  exit 1
fi

echo "Python and pip are installed."

# Install Sublist3r
echo "Installing Sublist3r..."
if [ -d "Sublist3r" ]; then
  echo "Sublist3r directory already exists. Skipping clone."
else
  git clone https://github.com/aboul3la/Sublist3r.git
fi
pip3 install -r Sublist3r/requirements.txt

echo "Sublist3r installed successfully."

echo "All reconnaissance tools have been installed."
echo "Make sure to add '$(go env GOPATH)/bin' to your system's PATH environment variable."
