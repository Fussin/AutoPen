# CyberHunter 3D: Installation Guide

This document provides step-by-step instructions for setting up and running the CyberHunter 3D reconnaissance platform on your local machine.

## Installation Options

You can set up CyberHunter 3D in two ways:

1.  **Local Installation:** Installing the platform and all its dependencies directly on your machine. This provides maximum control and is ideal for development.
2.  **Docker Installation:** (Coming Soon) A containerized setup that simplifies dependency management and provides a consistent environment.

---

## 1. Local Installation

This section guides you through setting up the platform on a local machine.

### 1.1. Prerequisites

Before you begin, ensure your system meets the following requirements.

#### System Requirements
*   **Operating System:** A Debian-based Linux distribution (e.g., Ubuntu, Kali Linux) is recommended, as the `install_tools.sh` script is tailored for it.
*   **Git:** For cloning the repository.
*   **Python:** Version 3.8 or higher, with `pip`.
*   **Go:** Version 1.18 or higher.
*   **C Compiler:** Build tools like `build-essential` are needed for some dependencies.
*   **Tesseract OCR:** Required for the screenshot analysis feature (`tesseract-ocr`).
*   **wkhtmltopdf:** For converting HTML reports to PDF.

#### External Security Tools
The platform integrates a wide array of external security tools. The provided `install_tools.sh` script automates the installation of these tools on Debian-based systems.

*   **Recon & Enumeration:** `Nmap`, `Gobuster`, `Subfinder`, `Amass`, `Assetfinder`, `MassDNS`, `puredns`, `Gotator`, `Sublist3r`, `Gospider`, `gau`.
*   **Web & Vulnerability:** `HTTPX`, `Nuclei`, `Naabu`, `SQLMap`, `gowitness`, `Aquatone`, `Subzy`, `DNSX`.
*   **Cloud & Code Analysis:** `Goblob`, `S3Scanner`, `LinkFinder`, `gh-dork`.
*   **Utilities:** `Wappalyzer`, `dnsgen`, `pipx`.

#### Python Dependencies
The core platform and its web interface rely on several Python packages. These are listed in `requirements.txt` and will be installed in a later step. Key packages include:
*   `Flask` (for the web interface)
*   `Flask-SQLAlchemy` (for database interaction)
*   `boto3` (for AWS integration)
*   `playwright` (for browser automation)
*   `shodan`, `censys-platform`, `fofa-py`, `greynoise` (for API integrations)
*   `pytesseract`, `Pillow` (for OCR)
*   `pandas`, `scikit-learn`, `lightgbm` (for data analysis and AI features)

### 1.2. Installation Steps

The installation is a three-step process:

#### Step 1: Clone the Repository
First, clone the CyberHunter 3D repository from GitHub:
```bash
git clone https://github.com/user/repo.git
cd repo
```
*(Replace `https://github.com/user/repo.git` and `repo` with the actual repository details)*

#### Step 2: Install External Tools
The platform relies on numerous external security tools.

**Option A: Automated Installation (Recommended for Debian-based systems)**
The repository includes a script to automate the installation of most required tools. Run it with `sudo`:
```bash
sudo bash cyberhunter_3d/scripts/install_tools.sh
```
**Note:** This script is designed for Debian-based distributions like Ubuntu and Kali Linux.

**Option B: Manual Installation**
If you are not using a Debian-based OS, you must install the tools manually. Please refer to the official documentation for each tool for OS-specific instructions. You can find the full list of tools in the `cyberhunter_3d/scripts/install_tools.sh` script.

#### Step 3: Install Python Dependencies and Application
Finally, install the CyberHunter 3D application and its Python dependencies. This command uses `pip` to install the packages listed in `setup.py` and `requirements.txt`.

From the root of the project directory, run:
```bash
pip3 install .
```
For development purposes, you might prefer to install in editable mode:
```bash
pip3 install -e .
```
This will install the application and allow you to modify the source code without reinstalling.

### 1.3. Configuration

After installation, you need to configure the platform. The main configuration file is `cyberhunter_3d/config/recon_config.yaml`.

#### Tool Paths
The `recon_config.yaml` file contains paths to the external tools. If you used the `install_tools.sh` script, it likely installed Go-based tools in `/root/go/bin/`. If you installed the tools manually or are not running as root, you **must** update these paths.

**Example:**
```yaml
tools:
  subfinder: /home/your_user/go/bin/subfinder
  # ... other tools
```
**Tip:** If a tool is in your system's `PATH`, you can just use the tool's name (e.g., `subfinder:`). You can check if a tool is in your path by running `which <tool_name>`.

#### Wordlists
The configuration file also points to wordlists for DNS and directory bruteforcing. The default paths point to `/usr/share/seclists/`, which is standard on Kali Linux. If you are on a different OS or stored your wordlists elsewhere, you must update these paths.

**Example:**
```yaml
wordlists:
  dns_bruteforce: /path/to/your/wordlists/subdomains.txt
  resolvers: /path/to/your/wordlists/resolvers.txt
```
You can find links to download common wordlists in the old `LocalInstall.md` or use your own preferred lists.

#### API Keys (Optional)
Some tools integrated into CyberHunter 3D can use API keys for better results (e.g., Shodan, Censys). While the platform does not yet have a centralized API key management system, individual tools may require them to be configured in their own configuration files (e.g., `~/.config/shodan/api_key`). Please refer to the documentation of each tool for details.

### 1.4. Database Setup

The platform uses a SQLite database to store scan information. Before running the web interface for the first time, you must initialize the database.

From the root of the project directory, run:
```bash
python3 init_db.py
```
You should see a confirmation message: `Database initialized successfully.`

### 1.5. Usage

You can run reconnaissance scans from the command line or use the web interface.

#### Command-Line Interface (CLI)
Thanks to the `setup.py` entry point, you can use the `cyberhunter` command directly.

**Basic Scan:**
```bash
cyberhunter example.com
```
This will run a passive enumeration scan on the specified domain and print the results to the console.

#### Web Interface
To use the web-based dashboard, run the `run_web.py` script:
```bash
python3 run_web.py
```
The web server will start (by default on port 5001). Open your web browser and navigate to `http://127.0.0.1:5001`. You will need to register a new user and set up two-factor authentication (2FA) on your first visit.

---

## 2. Docker Installation (Coming Soon)

A Docker-based setup for CyberHunter 3D is not yet available. A containerized environment would offer several advantages:

*   **Simplified Setup:** No need to manually install tools or manage dependencies.
*   **Consistency:** The platform runs in the same environment, regardless of your host OS.
*   **Isolation:** The platform and its dependencies are isolated from your host system.

We are considering developing a Docker setup for the project. If this is a feature you would find valuable, please let us know by opening an issue on our GitHub repository.

---

## 3. New Features

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
