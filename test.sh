#!/usr/bin/env bash

# What is broken?
echo "--- Root Cause Summary ---"
cat ROOT_CAUSE_DIAGNOSIS_MISSION_CATASTROPHE.md | head -n 25
cat MICROSERVICES_MIGRATION_FORENSICS_REPORT.md | grep -A 10 "Root Cause #1"
