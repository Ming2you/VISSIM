#!/usr/bin/env python3
# canonical topology 를 실런 네트워크에서 재생성하고 낡음을 판정하는 빌드 도구 (v3 N4/N9)
"""Rebuild the canonical Phase-0 topology from the live run network.

The topology is a **build product**, not a stored artifact. It takes ~9 s to compile and
weighs ~24 MB, so the repository convention (`.gitignore:34-36`, which already ignores
`lane_route_graph`, `lane_route_proofs` and `physical_stock_topology`) applies: ignore it
and rebuild.

The reason this module exists is that the previous stored copy was stale in two ways at
once, and nothing detected it:

    evaluation/strict_plant_20260731/canonical_topology.json
        source.inpx   modi.inpx (12489a21..)   live run uses modi_eval_rw_control.inpx (f3ce390f..)
        compiler      1.0.0                    current is 1.1.1

Measured consequence - the signal layer is understated:

    signal_controllers  37 -> 50      signal_groups  392 -> 440
    signal_heads       475 -> 541     routes         278 -> 339

The observation operators (198 / 90 / 191) happened to be identical, so the measurement
join stayed valid. Nothing guaranteed that; it was luck. `staleness()` exists so the next
consumer is told rather than guessing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_INPX = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
DEFAULT_OUT = REPO / "outputs" / "canonical_topology_v3.json"

# 컴파일러가 산출물에 새기는 판번호. 판올림하면 여기도 올려야 낡음 판정이 살아 있다.
CURRENT_COMPILER_VERSION = "vissim-strict-phase0/1.1.1"

REMEDY = (
    "python scripts/build_canonical_topology.py "
    "--inpx network/real_world_gaepo_modi/modi_eval_rw_control.inpx "
    "--out outputs/canonical_topology_v3.json"
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def staleness(topology_path: Path, inpx_path: Path) -> dict[str, Any]:
    """Judge whether a stored topology still describes the given network.

    Two independent reasons, reported separately - a version bump and a network change
    need different follow-ups, and collapsing them into one boolean hides that.
    """
    payload = json.loads(Path(topology_path).read_text(encoding="utf-8"))
    reasons: list[str] = []

    recorded = str(payload.get("source", {}).get("inpx_sha256", ""))
    if recorded != sha256_file(inpx_path):
        reasons.append("source_inpx_sha256")
    if str(payload.get("compiler_version", "")) != CURRENT_COMPILER_VERSION:
        reasons.append("compiler_version")

    return {
        "stale": bool(reasons),
        "reasons": reasons,
        "topology": str(topology_path),
        "inpx": str(inpx_path),
        "recorded_inpx_sha256": recorded,
        "actual_inpx_sha256": sha256_file(inpx_path),
        "recorded_compiler_version": payload.get("compiler_version", ""),
        "expected_compiler_version": CURRENT_COMPILER_VERSION,
        "remedy": REMEDY,
    }


def build(inpx: Path, out: Path) -> None:
    """Run the Phase-0 compiler.

    It is invoked as a subprocess rather than imported because it lives under `plant/`
    with its own import root (`cwd=plant`, `PYTHONPATH=<repo>`); importing it from here
    would need that root grafted onto this process for the rest of the run.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    plant = REPO / "plant"
    environment = {"PYTHONPATH": str(REPO)}
    import os

    merged = dict(os.environ)
    merged.update(environment)
    result = subprocess.run(
        [sys.executable, "-m", "src.vissim_strict.compiler", str(inpx), "--output", str(out)],
        cwd=str(plant),
        env=merged,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "topology compiler failed (%d): %s"
            % (result.returncode, (result.stderr or result.stdout or "").strip())
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild the canonical Phase-0 topology")
    parser.add_argument("--inpx", type=Path, default=DEFAULT_INPX)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Report whether --out is stale for --inpx without rebuilding",
    )
    args = parser.parse_args(argv)

    try:
        if args.check_only:
            if not args.out.is_file():
                print(json.dumps({"status": "MISSING", "remedy": REMEDY}, ensure_ascii=False))
                return 1
            verdict = staleness(args.out, args.inpx)
            print(json.dumps(verdict, ensure_ascii=False))
            return 1 if verdict["stale"] else 0

        build(args.inpx, args.out)
        verdict = staleness(args.out, args.inpx)
        if verdict["stale"]:
            raise RuntimeError(f"freshly built topology reports stale: {verdict['reasons']}")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    payload = json.loads(args.out.read_text(encoding="utf-8"))
    print(
        "status=PASS out=%s compiler=%s inpx_sha256=%s"
        % (args.out, payload.get("compiler_version"), verdict["actual_inpx_sha256"][:16])
    )
    print(
        "signal_controllers=%d signal_groups=%d observation_operators=%d"
        % (
            len(payload.get("signal_controllers", [])),
            len(payload.get("signal_groups", [])),
            len(payload.get("observation_operators", [])),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
