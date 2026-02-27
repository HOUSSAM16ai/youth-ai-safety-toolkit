#!/usr/bin/env python3
"""
Measures the 'Copy-Coupling' overlap between the monolithic Overmind service
and the Microservices Orchestrator service.

It calculates:
1. File Overlap: Number of files with identical names.
2. Content Similarity (Hash): Number of files with identical content.
3. Content Similarity (Fuzzy): (Optional/Future) Line-by-line comparison.

Usage:
    python3 scripts/measure_copy_coupling.py
"""

import hashlib
import os
from pathlib import Path

# Paths to compare
MONOLITH_PATH = Path("app/services/overmind")
MICROSERVICE_PATH = Path("microservices/orchestrator_service/src")

def get_file_map(root_path: Path) -> dict[str, Path]:
    """Recursively find all files and map filename -> full path."""
    file_map = {}
    if not root_path.exists():
        return file_map

    for root, _, files in os.walk(root_path):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                # We use the relative path from the service root as the key
                # to detect structural mirroring
                rel_path = Path(root).relative_to(root_path) / file
                file_map[str(rel_path)] = Path(root) / file
    return file_map

def calculate_file_hash(filepath: Path) -> str:
    """Calculate MD5 hash of file content."""
    return hashlib.md5(filepath.read_bytes()).hexdigest()

def main():
    print(f"🔍 Measuring Copy-Coupling between:\n  A: {MONOLITH_PATH}\n  B: {MICROSERVICE_PATH}\n")

    monolith_files = get_file_map(MONOLITH_PATH)
    microservice_files = get_file_map(MICROSERVICE_PATH)

    common_files = set(monolith_files.keys()) & set(microservice_files.keys())

    identical_content_count = 0

    print(f"{'File':<60} | {'Status':<15}")
    print("-" * 80)

    for filename in sorted(common_files):
        path_a = monolith_files[filename]
        path_b = microservice_files[filename]

        hash_a = calculate_file_hash(path_a)
        hash_b = calculate_file_hash(path_b)

        if hash_a == hash_b:
            status = "IDENTICAL"
            identical_content_count += 1
        else:
            status = "DIVERGED"

        print(f"{filename:<60} | {status:<15}")

    print("-" * 80)
    print(f"Total Monolith Files: {len(monolith_files)}")
    print(f"Total Microservice Files: {len(microservice_files)}")
    print(f"Overlapping Filenames: {len(common_files)}")
    print(f"Identical Content: {identical_content_count}")

    overlap_ratio = 0
    if len(monolith_files) > 0:
        overlap_ratio = (len(common_files) / len(monolith_files)) * 100

    print(f"\nCopy-Coupling Score: {overlap_ratio:.1f}% (files with same relative path)")

    # Check if we are below a certain threshold (soft check for now)
    if identical_content_count > 0:
        print("\n⚠️  WARNING: Identical files detected. This indicates direct copy-paste without decoupling.")

if __name__ == "__main__":
    main()
