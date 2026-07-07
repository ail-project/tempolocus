"""Command line interface for tempolocus."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import DetectionError, detect, load_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tempolocus",
        description="Guess likely timezone or region from temporal JSON activity.",
    )
    parser.add_argument("input", type=Path, help="JSON file to analyse")
    parser.add_argument(
        "-k",
        "--kind",
        choices=("auto", "weekly", "yearly"),
        default="auto",
        help="Input kind. Defaults to auto-detection.",
    )
    parser.add_argument(
        "-n",
        "--top",
        type=int,
        default=5,
        help="Number of candidate results to print.",
    )
    parser.add_argument(
        "--holiday-profile",
        choices=("standard", "public-worker"),
        default="standard",
        help="Holiday reference set for yearly inputs. Use public-worker to add public-sector closure days.",
    )
    parser.add_argument(
        "--activity-signal",
        choices=("lack", "peak"),
        default="lack",
        help="Yearly activity signal to match against holidays. Defaults to lack of activity; use peak for high-activity holiday indicators.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format.",
    )
    return parser


def _print_text(result: dict, top: int) -> None:
    print(f"input_type: {result['input_type']}")
    print(f"confidence: {result['confidence']:.3f}")
    if result.get("assumptions"):
        print("assumptions:")
        for assumption in result["assumptions"]:
            print(f"  - {assumption}")
    print("results:")
    for item in result["results"][:top]:
        label = item.get("label") or item.get("id")
        probability = item["probability"]
        print(f"  {probability:0.3f}  {item['kind']}: {label}")
        if item.get("evidence"):
            evidence = "; ".join(f"{k}={v}" for k, v in item["evidence"].items())
            print(f"          {evidence}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        data = load_json(args.input)
        result = detect(
            data,
            kind=args.kind,
            top=args.top,
            holiday_profile=args.holiday_profile,
            activity_signal=args.activity_signal,
        )
    except (OSError, json.JSONDecodeError, DetectionError) as exc:
        print(f"tempolocus: {exc}", file=sys.stderr)
        return 2

    if args.format == "text":
        _print_text(result, args.top)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0
