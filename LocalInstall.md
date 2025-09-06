# CyberHunter 3D: Local Installation Guide

This document provides step-by-step instructions for setting up and running the CyberHunter 3D reconnaissance platform on your local machine without using Docker.

## 1. Prerequisites

Before you begin, ensure you have the following software installed on your system:

*   **Git:** For cloning the repository.
*   **Python 3:** (Version 3.8 or higher) with `pip`.
*   **Go:** (Version 1.18 or higher) for installing various security tools.
*   **A C compiler and related build tools** (like `build-essential` on Debian/Ubuntu) for compiling certain dependencies.
*   **Tesseract OCR Engine:** For the AI-powered screenshot analysis feature. On Debian/Ubuntu, you can install it with `sudo apt-get install tesseract-ocr`.

## 2. Installation

The installation process involves cloning the repository, installing numerous command-line tools, and setting up the Python environment.

### Step 2.1: Clone the Repository

First, clone the CyberHunter 3D repository from GitHub:

```bash
git clone https://github.com/user/repo.git
cd repo
```
*(Replace `https://github.com/user/repo.git` with the actual URL of the repository and `repo` with the repository name)*

### Step 2.2: Install System & Go-based Tools

The platform relies on a wide range of external security tools.

**For Debian-based Linux (e.g., Ubuntu, Kali):**

The repository includes a convenience script to automate the installation of most required tools.

```bash
sudo bash cyberhunter_3d/scripts/install_tools.sh
```

**For other Operating Systems (or Manual Installation):**

If you are not using a Debian-based distribution, you will need to install the tools manually. Below is a list of the key tools. Please refer to their official installation guides for instructions specific to your OS.

*   **Go tools:** Ensure your `GOPATH` is set up correctly (e.g., `export PATH=$PATH:$(go env GOPATH)/bin` in your `.bashrc` or `.zshrc`).
    *   `subfinder`: `go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest`
    *   `amass`: `go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest`
    *   `httpx`: `go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest`
    *   `naabu`: `go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest`
    *   `nuclei`: `go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest`
    *   `gowitness`: `go install -v github.com/sensepost/gowitness@latest`
    *   `subzy`: `go install -v github.com/PentestPad/subzy@latest`
    *   ...and others listed in `cyberhunter_3d/scripts/install_tools.sh`.

*   **Other tools:**
    *   `nmap`, `gobuster`, `sqlmap`, etc., can typically be installed via your system's package manager (e.g., `brew install nmap` on macOS).

### Step 2.3: Install Python Dependencies

Install all the required Python packages using `pip`:

```bash
pip3 install -r requirements.txt
```

## 3. Configuration

After installing all dependencies, you need to configure the tool by providing necessary wordlists.

### Step 3.1: Download Wordlists

The tool requires several wordlists for enumeration and bruteforcing. The default configuration expects them to be in a `/wordlists/` directory, but you can place them anywhere and update the config file.

Create a directory for your wordlists:
```bash
mkdir -p wordlists
cd wordlists
```

Download the following common wordlists:

*   **Subdomain Bruteforcing:**
    ```bash
    wget https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt
    ```
*   **Directory Bruteforcing:**
    ```bash
    wget https://raw.githubusercontent.com/v0re/dirb/master/wordlists/common.txt -O directory-list-2.3-medium.txt
    ```
*   **DNS Resolvers:**
    ```bash
    wget https://raw.githubusercontent.com/janmasarik/resolvers/master/resolvers.txt
    ```
`cd ..` to return to the project root directory.

### Step 3.2: Update the Configuration File

Open the `recon_config.yaml` file and update the paths to the wordlists you just downloaded.

**File:** `cyberhunter_3d/config/recon_config.yaml`

Update the `wordlists` section to point to the absolute paths of the downloaded files on your system. For example:

```yaml
wordlists:
  dns_bruteforce: /path/to/your/cyberhunter-3d/wordlists/subdomains-top1million-5000.txt
  dir_bruteforce: /path/to/your/cyberhunter-3d/wordlists/directory-list-2.3-medium.txt
  resolvers: /path/to/your/cyberhunter-3d/wordlists/resolvers.txt
  github_dorks: /path/to/your/cyberhunter-3d/gh-dork/dorks.txt # This should be correct if you cloned the repo
```
*(Replace `/path/to/your/cyberhunter-3d/` with the actual absolute path to the project directory).*

## 4. Database Setup

The platform uses a SQLite database to store scan information. Before running a scan for the first time, you must initialize the database.

Run the `init_db.py` script from the root of the project directory:

```bash
python3 init_db.py
```

You should see a confirmation message: `Database initialized successfully.`

## 5. Usage

You can now run reconnaissance scans from the command line or use the web interface.

### Running a Scan (CLI)

To run a scan on a target domain, use the `main.py` script.

**Basic Scan:**
```bash
python3 cyberhunter_3d/main.py -d example.com
```

**Verbose Scan (more detailed output):**
```bash
python3 cyberhunter_3d/main.py -d example.com -v
```

**URL Discovery and Vulnerability Scan:**
```bash
python3 cyberhunter_3d/main.py -d example.com --url-discovery
```

Results will be saved in the `recon_results/` and `screenshots/` directories.

### Running the Web Interface

To use the web-based dashboard, run the `run_web.py` script:

```bash
python3 run_web.py
```

The web server will start (by default on port 5001). Open your web browser and navigate to `http://127.0.0.1:5001`. You will need to register a new user and set up two-factor authentication (2FA) on your first visit.

## 6. New Features

This version of CyberHunter 3D includes several new features that enhance its reconnaissance and vulnerability scanning capabilities.

### AI-Powered Enhancements

*   **OCR Tagging:** The tool can now perform Optical Character Recognition (OCR) on screenshots to identify interesting keywords (e.g., "login", "admin", "debug"). This requires the Tesseract OCR engine to be installed on your system.
*   **Noise Filtering:** A rule-based noise filter helps to remove common false-positive subdomains from the results.
*   **Intelligent Wordlists:** The tool can generate intelligent wordlists for permutation scanning based on keywords extracted from discovered subdomains.

### New Vulnerability Scanners

The platform now includes several new vulnerability scanners. While many are still under development (placeholders), the framework is in place. The new scanning capabilities include:

*   **CORS Misconfiguration:** Scans for Cross-Origin Resource Sharing (CORS) misconfigurations. This feature requires the `corscanner` Python package.
*   **LFI (Local File Inclusion):** Placeholder for LFI scanning.
*   **SQLi (SQL Injection):** Placeholder for SQLi scanning.
*   **SSRF/XXE:** Placeholders for Server-Side Request Forgery and XML External Entity scanning.
*   **Sensitive Data Exposure:** Placeholders for detecting exposed `.git` directories, API keys, and backup files.
*   **XSS (Cross-Site Scripting):** Uses `dalfox` to scan for XSS vulnerabilities.
