# Makefile for the security pipeline

# Variables to be passed from the command line
domain ?= example.com
vuln_targets ?= '{"urls": ["http://testphp.vulnweb.com/listproducts.php?cat=1"]}'
net_targets ?= "127.0.0.1"
osint_targets ?= '{"usernames": ["johndoe"]}'

# Default target
all:
	@echo "Running full pipeline for $(domain)..."
	@python -m src.main $(domain)

# Phase targets for individual debugging
recon:
	@echo "Running Reconnaissance Phase for $(domain)..."
	@python -m src.phases.recon $(domain)

urls:
	@echo "Running URL Discovery Phase for $(domain)..."
	@python -m src.phases.urls $(domain)

vuln:
	@echo "Running Vulnerability Discovery Phase..."
	@python -m src.phases.vuln '$(vuln_targets)'

network:
	@echo "Running Network Scanning Phase on $(net_targets)..."
	@python -m src.phases.network $(net_targets)

osint:
	@echo "Running OSINT Phase..."
	@python -m src.phases.osint '$(osint_targets)'

# Reporting target
report:
	@echo "Generating report from aggregated findings..."
	@python -c "from src.common.reporting import generate_html_report; import json; findings = []; \
	try: findings = json.load(open('outputs/findings_aggregated.json')); \
	except FileNotFoundError: print('findings_aggregated.json not found, generating empty report.'); \
	generate_html_report(findings, 'reports/final_report.html')"

# Clean target
clean:
	@echo "Cleaning up output files..."
	@rm -rf outputs/* artifacts/* reports/*
	@rm -f subdomains_*.txt way_kat.txt parameters_extracted.txt alive_domain.txt dead_domain.txt redirect_30x.txt takeover_findings.json

.PHONY: all recon urls vuln network osint report clean
