"""Entry-point script for the DME document classifier.

Usage:
    python -m src.classify --input documents/ --output output/

Orchestrates extraction → classification → completeness check → storage.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argument namespace with input_dir and output_dir.
    """
    raise NotImplementedError


def run(input_dir: Path, output_dir: Path) -> None:
    """Run the full classification pipeline.

    1. Discover all PDF files in input_dir.
    2. Extract text from each PDF (dual-path).
    3. Classify each document.
    4. Check per-patient completeness.
    5. Save results to output_dir.

    Args:
        input_dir: Directory containing PDF documents.
        output_dir: Directory to write output files into.
    """
    raise NotImplementedError


if __name__ == "__main__":
    args = parse_args()
    run(args.input_dir, args.output_dir)
