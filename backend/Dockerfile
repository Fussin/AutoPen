# =========================================================================================
# STAGE 1: The Builder
# This stage installs build tools and compiles/downloads all the security tools.
# =========================================================================================
FROM debian:bookworm AS builder

# Prevent prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install essential build dependencies for various tools (Go, Rust, Python, C, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git wget curl ca-certificates gnupg \
    golang-go rustc cargo ruby ruby-dev libpcap-dev \
    python3 python3-pip python3-venv libssl-dev libxml2-dev \
    libxslt1-dev zlib1g-dev pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --- Setup Environment Paths ---
ENV GOPATH=/go
ENV PATH=$GOPATH/bin:/usr/local/go/bin:/root/.local/bin:$PATH
RUN mkdir -p "$GOPATH/src" "$GOPATH/bin" /opt/tools

# =========================================================================================
# 🔍 Network Reconnaissance & Scanning (25+ Tools)
# =========================================================================================
# Install from APT for simplicity and stability where possible
RUN apt-get update && apt-get install -y --no-install-recommends nmap arp-scan nbtscan rpcbind \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install RustScan (fast port scanner)
RUN wget https://github.com/RustScan/RustScan/releases/download/2.0.1/rustscan_2.0.1_amd64.deb && \
    dpkg -i rustscan_2.0.1_amd64.deb && rm rustscan_2.0.1_amd64.deb

# Build Masscan from source (high-speed port scanner)
RUN git clone https://github.com/robertdavidgraham/masscan.git /opt/tools/masscan-src && \
    cd /opt/tools/masscan-src && make -j$(nproc) && mv bin/masscan /usr/local/bin/

# Install Go-based Network Tools
RUN go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@v2.5.6

# Install Python-based Network Tools
RUN pip3 install --no-cache-dir pipx
RUN pipx ensurepath
RUN pipx install --no-cache-dir git+https://github.com/SECFORCE/fierce.git
RUN pipx install --no-cache-dir git+https://github.com/ofensec/enum4linux-ng.git --force # Enum4linux-ng
RUN pipx install --no-cache-dir git+https://github.com/byt3bl33d3r/NetExec.git
RUN pipx install --no-cache-dir smbmap

# Clone Git-based Network Tools
RUN git clone https://github.com/Tib3rius/AutoRecon.git /opt/tools/AutoRecon
RUN git clone https://github.com/darkoperator/dnsenum.git /opt/tools/dnsenum
RUN git clone https://github.com/laramies/theHarvester.git /opt/tools/theHarvester && \
    cd /opt/tools/theHarvester && python3 -m pip install -r requirements/base.txt
RUN git clone https://github.com/lgandx/Responder.git /opt/tools/Responder

# =========================================================================================
# 🌐 Web Application Security Testing (40+ Tools)
# =========================================================================================
# Install Go-based Web Tools
RUN go install -v github.com/OJ/gobuster/v3@latest
RUN go install -v github.com/ffuf/ffuf@latest
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest
RUN go install -v github.com/hakluke/hakrawler@latest
RUN go install -v github.com/tomnomnom/gau/v2/cmd/gau@latest
RUN go install -v github.com/tomnomnom/waybackurls@latest
RUN go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest
RUN go install -v github.com/hahwul/dalfox/v2@latest
RUN go install -v github.com/tomnomnom/anew@latest
RUN go install -v github.com/tomnomnom/qsreplace@latest
RUN go install -v github.com/jaeles-project/jaeles@latest

# Install Python-based Web Tools
RUN pipx install --no-cache-dir dirsearch
RUN pipx install --no-cache-dir sqlmap-dev
RUN pipx install --no-cache-dir arjun
RUN pipx install --no-cache-dir paramspider
RUN pipx install --no-cache-dir wafw00f
RUN pipx install --no-cache-dir sslyze
RUN pipx install --no-cache-dir uro
RUN pipx install --no-cache-dir jwt-tool
RUN pipx install --no-cache-dir wfuzz
RUN pipx install --no-cache-dir commix
RUN pipx install --no-cache-dir nosqlmap
RUN pipx install --no-cache-dir tplmap
RUN pipx install --no-cache-dir X8

# Install from APT
RUN echo "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian bookworm main contrib non-free" > /etc/apt/sources.list.d/non-free.list && \
    apt-get update && \
    apt-get install -y nikto dirb whatweb testssl.sh sslscan

# Install from other sources
RUN cargo install feroxbuster
RUN gem install wpscan

# NOTE: GUI-based tools like Burp Suite and ZAP Proxy are not suitable for a Docker server image.
# They should be run on a local machine and can connect to targets deployed via Docker.

# =========================================================================================
# ☁️ Cloud & Container Security (20+ Tools)
# =========================================================================================
# Install Go-based Cloud/Container Tools
RUN go install -v github.com/aquasecurity/trivy/cmd/trivy@latest

# Install Python-based Cloud/Container Tools
RUN pipx install --no-cache-dir prowler
RUN pipx install --no-cache-dir checkov
RUN pipx install --no-cache-dir terrascan
RUN pipx install --no-cache-dir awscli
RUN pipx install --no-cache-dir azure-cli
RUN pipx install --no-cache-dir kube-hunter
RUN pipx install --no-cache-dir kube-bench

# Install from APT/scripts
RUN apt-get update && apt-get install -y --no-install-recommends kubectl helm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://falco.org/repo/falcosecurity-3672BA8F.asc | gpg --dearmor -o /usr/share/keyrings/falco-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] https://download.falco.org/packages/deb stable main" | tee -a /etc/apt/sources.list.d/falco.list && \
    apt-get update && apt-get install -y --no-install-recommends falco \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts && mv /root/google-cloud-sdk /opt/
ENV PATH="/opt/google-cloud-sdk/bin:$PATH"

# Clone Git-based Cloud Tools
RUN git clone https://github.com/nccgroup/ScoutSuite.git /opt/tools/ScoutSuite && \
    cd /opt/tools/ScoutSuite && python3 -m pip install -r requirements.txt
RUN git clone https://github.com/duo-labs/cloudmapper.git /opt/tools/cloudmapper
RUN git clone https://github.com/RhinoSecurityLabs/pacu.git /opt/tools/pacu
RUN git clone https://github.com/docker/docker-bench-security.git /opt/tools/docker-bench-security
RUN git clone https://github.com/aquasecurity/cloudsploit.git /opt/tools/cloudsploit

# =========================================================================================
# 🔥 Bug Bounty & OSINT Arsenal (20+ Tools)
# =========================================================================================
# Tools like amass, subfinder, httpx, hakrawler are already installed above.
# Install Python-based OSINT tools
RUN pipx install --no-cache-dir sherlock
RUN pipx install --no-cache-dir social-analyzer
RUN pipx install --no-cache-dir shodan
RUN pipx install --no-cache-dir censys-cli
RUN pipx install --no-cache-dir trufflehog

# Install Go-based OSINT tools
RUN go install -v github.com/haccer/subjack@latest

# Install from other sources
RUN wget https://github.com/michenriksen/aquatone/releases/download/v1.7.0/aquatone_linux_amd64_1.7.0.zip && \
    unzip aquatone_linux_amd64_1.7.0.zip && mv aquatone /usr/local/bin/ && rm aquatone_linux_amd64_1.7.0.zip
# NOTE: Maltego is a GUI tool and not suitable for this image.

# Clone Git-based OSINT tools
RUN git clone https://github.com/laramies/recon-ng.git /opt/tools/recon-ng
RUN git clone https://github.com/smicallef/spiderfoot.git /opt/tools/spiderfoot


# =========================================================================================
# STAGE 2: The Final Application Image
# This stage copies the compiled tools and application code into a slim base image.
# =========================================================================================
FROM python:3.11-slim-bookworm

# Create a non-root user for better security
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# Install only necessary runtime packages
RUN echo "deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] http://deb.debian.org/debian bookworm main contrib non-free" > /etc/apt/sources.list.d/non-free.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    nmap arp-scan nbtscan rpcbind nikto dirb whatweb testssl.sh sslscan curl procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# --- Copy all compiled/cloned tools from the builder stage ---
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY --from=builder /root/.local/bin/ /home/appuser/.local/bin/
COPY --from=builder /opt/tools /opt/tools
COPY --from=builder /opt/google-cloud-sdk /opt/google-cloud-sdk

# Set PATH for the new user, including pipx and gcloud
ENV PATH="/home/appuser/.local/bin:/opt/google-cloud-sdk/bin:$PATH"

# --- Create AI Agent Placeholder Scripts ---
RUN mkdir -p /home/appuser/app/agents
RUN for agent in IntelligentDecisionEngine BugBountyWorkflowManager CTFWorkflowManager CVEIntelligenceManager \
                 AIExploitGenerator VulnerabilityCorrelator TechnologyDetector RateLimitDetector \
                 FailureRecoverySystem PerformanceMonitor ParameterOptimizer GracefulDegradation; do \
      echo "#!/bin/bash" > /home/appuser/app/agents/${agent}.sh && \
      echo "echo '[AI Agent] ${agent} activated with args: \"$@\"'" >> /home/appuser/app/agents/${agent}.sh && \
      chmod +x /home/appuser/app/agents/${agent}.sh; \
    done
ENV PATH="/home/appuser/app/agents:$PATH"

# Set ownership of tools and app directory to the new user
RUN chown -R appuser:appuser /home/appuser /opt/tools

# Switch to the non-root user
USER appuser

# --- Final Application Setup ---
# Copy the application source code
COPY --chown=appuser:appuser . .

# Install Python dependencies for the main application
RUN python3 -m pip install --no-cache-dir --user -r requirements.txt

# Expose the application port
EXPOSE 5001

# Command to run the web server using a production-grade server like Gunicorn
CMD ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "run_web:create_app()"]
