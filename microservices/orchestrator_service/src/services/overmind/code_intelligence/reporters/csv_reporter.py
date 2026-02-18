import csv
from pathlib import Path

from app.core.logging import get_logger
from microservices.orchestrator_service.src.services.overmind.code_intelligence.models import (
    ProjectAnalysis,
)

logger = get_logger(__name__)


def save_csv_report(analysis: ProjectAnalysis, output_path: Path) -> None:
    """Save report as CSV"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        if not analysis.files:
            return

        fieldnames = [
            "relative_path",
            "code_lines",
            "num_classes",
            "num_functions",
            "file_complexity",
            "avg_function_complexity",
            "max_function_complexity",
            "commits_last_12months",
            "bugfix_commits",
            "is_god_class",
            "has_layer_mixing",
            "has_cross_layer_imports",
            "hotspot_score",
            "priority_tier",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    for file_metrics in analysis.files:
        row = {k: getattr(file_metrics, k) for k in fieldnames}
        writer.writerow(row)

    logger.info("💾 CSV report saved: %s", output_path)
