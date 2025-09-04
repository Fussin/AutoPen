# CyberHunter 3D - Reconnaissance Platform

## Vision
To create an advanced, automated reconnaissance platform that integrates a wide array of security tools to provide a comprehensive view of an organization's attack surface. This platform is designed to be highly modular, extensible, and easy to use.

## V3 Reconnaissance Pipeline
The V3 pipeline is a complete overhaul of the reconnaissance module, designed to be more powerful and flexible. It includes the following features:

- **Comprehensive Enumeration**: Combines passive, active, and permutation-based enumeration techniques to discover a wide range of subdomains.
- **Live Host Detection**: Uses `httpx` to identify live hosts from the list of discovered subdomains.
- **Visual Reconnaissance**: Takes screenshots of live hosts using `gowitness` for quick visual identification.
- **Technology Fingerprinting**: Identifies the technologies running on live hosts using `wappalyzer` and `naabu` for port scanning.
- **Subdomain Takeover Scans**: Checks for potential subdomain takeover vulnerabilities using `subzy`.
- **AI-Powered Enhancements (Placeholders)**:
    - **AI Wordlist Generator**: Enhances permutation scanning with AI-generated keywords.
    - **AI Noise Filter**: Filters out false-positive subdomains from the results.
    - **AI OCR Tagger**: Analyzes screenshots to generate descriptive tags (e.g., "login page", "404").
- **Cloudflare R2 Integration**: Optionally uploads the final results, including screenshots, to a Cloudflare R2 bucket for centralized storage.
- **Aggregated Results**: Consolidates all findings into a single, structured `final_recon_data.json` file.

## Usage
The recommended way to run CyberHunter 3D is via Docker, which ensures a consistent environment with all the necessary tools and dependencies.

### Prerequisites
- Docker: [https://www.docker.com/get-started](https://www.docker.com/get-started)
- Docker Compose: [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/)

### Running a Scan
1.  **Build the Docker image**:
    ```bash
    docker-compose build
    ```

2.  **Run the reconnaissance pipeline**:
    ```bash
    docker-compose run --rm cyberhunter -d example.com
    ```
    -   Replace `example.com` with your target domain.
    -   The results will be saved in the `recon_results` and `screenshots` directories on your host machine.

### Uploading to Cloudflare R2
To enable uploading to Cloudflare R2, you need to set the following environment variables on your host machine before running the scan:
- `CF_R2_ACCOUNT_ID`
- `CF_R2_ACCESS_KEY_ID`
- `CF_R2_SECRET_ACCESS_KEY`
- `CF_R2_BUCKET`

Then, run the scan with the `--upload-to-r2` flag:
```bash
docker-compose run --rm cyberhunter -d example.com --upload-to-r2
```

## `final_recon_data.json` Structure
The final output file has the following structure:
```json
{
  "domain": "example.com",
  "hosts": [
    {
      "host": "sub.example.com",
      "alive": true,
      "ips": ["1.2.3.4"],
      "asn_details": ["AS15169 - GOOGLE"],
      "open_ports": [80, 443],
      "technologies": ["nginx", "React"],
      "takeover_risk": false,
      "cloud_asset": false,
      "screenshot_tags": ["webpage", "screenshot"]
    }
  ]
}
```

This repository contains the source code for the CyberHunter 3D platform.

## Installation

This project relies on a number of external security tools. You need to install these tools and ensure they are in your system's PATH for the pipeline to work correctly.

A good starting point is the `cyberhunter_3d/scripts/install_tools.sh` script from the original codebase. You may need to adapt it to your system.

The Python dependencies are listed in `requirements.txt` and can be installed with:
```bash
pip install -r requirements.txt
```

## Usage

The main entry point for the pipeline is `src/main.py`. You can run the full pipeline with:
```bash
make all domain=yourtarget.com
```
