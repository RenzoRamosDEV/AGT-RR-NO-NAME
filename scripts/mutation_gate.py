"""Falla si la puntuación de mutación queda por debajo del umbral.

Uso: python scripts/mutation_gate.py <mutmut-cicd-stats.json> --min 85

Puntuación = mutantes muertos / (muertos + supervivientes + timeouts + sin tests).
Los mutantes "suspicious"/omitidos no cuentan a favor ni en contra.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def score(stats: dict[str, int]) -> tuple[int, int]:
    killed = stats.get("killed", 0) + stats.get("timeout", 0)
    alive = stats.get("survived", 0) + stats.get("no_tests", 0)
    return killed, killed + alive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stats_file", type=Path)
    parser.add_argument("--min", type=float, required=True, dest="minimum")
    args = parser.parse_args()

    stats = json.loads(args.stats_file.read_text())
    killed, total = score(stats)
    if total == 0:
        print("mutation-gate: no se generó ningún mutante", file=sys.stderr)
        return 1

    percentage = 100 * killed / total
    print(f"mutation-gate: {killed}/{total} mutantes muertos = {percentage:.1f}% (mínimo {args.minimum}%)")
    if percentage < args.minimum:
        print("mutation-gate: FALLA - puntuación por debajo del umbral", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
