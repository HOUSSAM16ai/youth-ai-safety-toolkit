"""
Deep Indexer for Overmind Planning.
-----------------------------------
This module provides functionality to build a deep structural index of the codebase
and summarize it for LLM consumption. It restores missing functionality required by
MissionComplexHandler and DeepAnalysisHandler.
"""

import logging
from pathlib import Path

from microservices.orchestrator_service.src.services.overmind.code_intelligence.core import (
    StructuralCodeIntelligence,
)
from microservices.orchestrator_service.src.services.overmind.code_intelligence.models import (
    ProjectAnalysis,
)

logger = logging.getLogger(__name__)


def build_index(root: str = ".") -> ProjectAnalysis:
    """
    Build a structural index of the project.

    Args:
        root (str): The root directory of the project. Defaults to ".".

    Returns:
        ProjectAnalysis: The analysis result containing metrics and hotspots.
    """
    repo_path = Path(root).resolve()

    # Auto-detect target paths
    candidates = ["app", "src", "microservices", "scripts", "lib", "frontend"]
    target_paths = []

    for candidate in candidates:
        if (repo_path / candidate).exists():
            target_paths.append(candidate)

    # If no standard directories found, fall back to analyzing the root (excluding hidden/ignored by default)
    if not target_paths:
        target_paths = ["."]

    logger.info(f"Building deep index for: {repo_path} (Targets: {target_paths})")

    sci = StructuralCodeIntelligence(repo_path, target_paths)
    return sci.analyze_project()


def summarize_for_prompt(index: ProjectAnalysis, max_len: int = 3000) -> str:
    """
    Summarize the project analysis for use in an LLM prompt.

    Args:
        index (ProjectAnalysis): The analysis object.
        max_len (int): Maximum length of the summary string.

    Returns:
        str: A formatted summary string.
    """
    if not index:
        return "No project analysis available."

    lines = []
    lines.append(f"📊 **Project Analysis Report** (Generated: {index.timestamp})")
    lines.append("-" * 40)
    lines.append(f"• Total Files: {index.total_files}")
    lines.append(f"• Total Lines: {index.total_lines} (Code: {index.total_code_lines})")
    lines.append(
        f"• Complexity: Avg {index.avg_file_complexity:.2f} (Max {index.max_file_complexity})"
    )
    lines.append(
        f"• Architecture: {index.total_classes} Classes, {index.total_functions} Functions"
    )

    if index.critical_hotspots:
        lines.append("\n🔥 **Critical Hotspots (Refactor Priority):**")
        for hotspot in index.critical_hotspots[:5]:  # Top 5
            lines.append(f"  - {hotspot}")

    if index.high_hotspots:
        lines.append("\n⚠️ **High Maintenance Targets:**")
        for hotspot in index.high_hotspots[:5]:
            lines.append(f"  - {hotspot}")

    # File highlights (Top complex files)
    sorted_files = sorted(index.files, key=lambda x: x.file_complexity, reverse=True)
    if sorted_files:
        lines.append("\n🧠 **Most Complex Modules:**")
        for f in sorted_files[:5]:
            lines.append(f"  - {f.relative_path} (C: {f.file_complexity}, Lines: {f.total_lines})")

    summary = "\n".join(lines)

    if len(summary) > max_len:
        return summary[:max_len] + "\n...(truncated)"

    return summary
