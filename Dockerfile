# Stage 1: Builder for Go tools and other binaries
FROM golang:1.19-bullseye AS builder

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libpcap-dev \
    nmap \
    gobuster \
    python3-pip \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set Go environment
ENV GOPATH=/go
ENV PATH=$GOPATH/bin:/usr/local/go/bin:$PATH

# Install Go tools
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
RUN go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
RUN go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
RUN go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
RUN go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest
RUN go install github.com/d3mondev/puredns/v2@latest
RUN go install github.com/Josue87/gotator@latest
RUN go install github.com/sensepost/gowitness@latest
RUN go install github.com/tomnomnom/assetfinder@latest
RUN go install github.com/tomnomnom/waybackurls@latest
RUN go install -v github.com/LukaSikic/subzy@latest
RUN go install github.com/jaeles-project/gospider@latest
RUN go install github.com/lc/gau/v2/cmd/gau@latest
RUN go install -v github.com/owasp-amass/amass/v4/...@master

# Install massdns from source
RUN git clone https://github.com/blechschmidt/massdns.git /tmp/massdns \
    && cd /tmp/massdns \
    && make \
    && cp bin/massdns /go/bin/

# Install Aquatone from binary release
RUN wget https://github.com/michenriksen/aquatone/releases/download/v1.7.0/aquatone_linux_amd64_1.7.0.zip -O /tmp/aquatone.zip \
    && unzip /tmp/aquatone.zip -d /tmp/ \
    && mv /tmp/aquatone /go/bin/

# Clone gh-dork for the script and dorks
RUN git clone https://github.com/KathanP19/gh-dork.git /gh-dork

# Stage 2: Final image
FROM python:3.10-slim-bullseye

# Install sudo and tesseract
RUN apt-get update && apt-get install -y sudo tesseract-ocr && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a non-root user and add to sudo group
RUN useradd -m appuser && usermod -aG sudo appuser
# Set passwordless sudo for the user
RUN echo 'appuser ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

USER appuser
WORKDIR /home/appuser/app

# Copy binaries from builder stage
COPY --from=builder /go/bin/* /usr/local/bin/
COPY --from=builder /usr/bin/nmap /usr/bin/nmap
COPY --from=builder /usr/bin/gobuster /usr/bin/gobuster

# Copy gh-dork script and make it executable
COPY --from=builder /gh-dork /home/appuser/app/gh-dork
RUN sudo chmod +x /home/appuser/app/gh-dork/gh-dork.py
# Create a symlink to gh-dork.py in /usr/local/bin
RUN sudo ln -s /home/appuser/app/gh-dork/gh-dork.py /usr/local/bin/gh-dork.py


# Copy application code
COPY --chown=appuser:appuser . .

# Download wordlists
RUN mkdir /wordlists && \
    wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt -O /wordlists/subdomains-top1million-5000.txt && \
    wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/resolvers.txt -O /wordlists/resolvers.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt
# Install python-based tools
RUN pip install --no-cache-dir --user dnsgen wappalyzer-cli s3scanner linkfinder

# Set environment to include user's local bin
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Set entrypoint
ENTRYPOINT ["python3", "cyberhunter_3d/main.py"]
