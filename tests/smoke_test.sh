#!/bin/bash

# Smoke test for the security pipeline

# Exit on error
set -e

# Setup
echo "Setting up test environment..."
mkdir -p outputs artifacts reports

# Run pipeline
echo "Running pipeline smoke test..."
make all domain=example.com

# Check for report
echo "Checking for report..."
if [ -f "reports/final_report.html" ]; then
    echo "Smoke test passed!"
else
    echo "Smoke test failed: final_report.html not found."
    exit 1
fi

# Cleanup
echo "Cleaning up..."
make clean
