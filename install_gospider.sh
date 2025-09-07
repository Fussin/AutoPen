#!/bin/bash
set -e
set -x
export PATH=$PATH:/home/jules/go/bin
go install -v github.com/jaeles-project/gospider@latest
