# Stage 1: Builder
FROM golang:1.19-bullseye as builder

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    wget \
    unzip \
    nmap \
    gobuster \
    libpcap-dev \
    firefox \
    sqlmap \
    tesseract-ocr \
    wkhtmltopdf \
    build-essential \
    seclists \
    && rm -rf /var/lib/apt/lists/*

# Set up Go environment
ENV GOPATH /go
ENV PATH $GOPATH/bin:/usr/local/go/bin:$PATH

# Copy and run the tool installation script
COPY cyberhunter_3d/scripts/install_tools.sh /install_tools.sh
RUN chmod +x /install_tools.sh && /install_tools.sh

# Stage 2: Final Image
FROM python:3.9-slim-bullseye

# Set up non-root user
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Copy tools from the builder stage
COPY --from=builder /go/bin/amass /go/bin/
COPY --from=builder /go/bin/subfinder /go/bin/
COPY --from=builder /go/bin/assetfinder /go/bin/
COPY --from=builder /go/bin/hakrawler /go/bin/
COPY --from=builder /go/bin/httpx /go/bin/
COPY --from=builder /go/bin/nuclei /go/bin/
COPY --from=builder /go/bin/puredns /go/bin/
COPY --from=builder /go/bin/gotator /go/bin/
COPY --from=builder /go/bin/gowitness /go/bin/
COPY --from=builder /go/bin/naabu /go/bin/
COPY --from=builder /go/bin/goblob /go/bin/
COPY --from=builder /go/bin/s3scanner /go/bin/
COPY --from=builder /go/bin/subzy /go/bin/
COPY --from=builder /go/bin/dnsx /go/bin/
COPY --from=builder /go/bin/gospider /go/bin/
COPY --from=builder /go/bin/gau /go/bin/
COPY --from=builder /usr/local/bin/massdns /usr/local/bin/
COPY --from=builder /usr/local/bin/aquatone /usr/local/bin/
COPY --from=builder /usr/local/bin/geckodriver /usr/local/bin/
COPY --from=builder /usr/bin/nmap /usr/bin/
COPY --from=builder /usr/bin/gobuster /usr/bin/
COPY --from=builder /usr/bin/sqlmap /usr/bin/
COPY --from=builder /usr/bin/sublist3r /usr/bin/
COPY --from=builder /root/.local/bin/wappalyzer /root/.local/bin/

# Set environment variables
ENV PATH /go/bin:/usr/local/bin:/usr/bin:/root/.local/bin:$PATH
ENV GOPATH /go

# Copy application code
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Change ownership to non-root user
RUN chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Expose the web interface port
EXPOSE 5000

# Entrypoint
ENTRYPOINT ["python3", "cyberhunter_3d/main.py"]
