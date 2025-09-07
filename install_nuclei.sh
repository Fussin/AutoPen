#!/bin/bash
set -e
echo "Installing Go..."
sudo apt-get update
sudo apt-get install -y golang-go
echo "Go installed successfully."
echo "Installing Nuclei..."
export PATH=$PATH:$(go env GOPATH)/bin
go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
echo "Nuclei installed successfully."
