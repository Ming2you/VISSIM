#!/usr/bin/env python3
"""N5 부모런 9개의 증거를 커밋 가능한 한 파일로 봉인한다.

## 왜 필요한가

`evaluation/runs/` 는 `.gitignore` 에 들어 있다(:6). 큰 산출물을 커밋하지 않는다는
저장소 정책은 맞지만, 부모런은 재생성에 7~10시간이 드는 데다 VISSIM 시드 재현성에
의존한다. 그래서 **해시가 정본**이라는 같은 원칙을 부모런에도 적용한다 - 산출물은
디스크에 두고, 그 정체성(해시·행수·anchor 목록)만 여기 봉인해 커밋한다.

## 무엇을 검사하는가

계획 N5 의 PASS 기준을 그대로 옮겼다.

    부모 9/9              9개 셀이 전부 있고 exit=0
    anchor 완비           셀마다 anchor_000900/001500/002100/002700.json 4개
    누락/중복 0           (demand, seed) 조합이 정확히 1회씩
    training/holdout 시드 중복 0

수요 배율이 실제로 먹었는지도 런로그에서 확인한다 - `DEMAND=SCALED_IN_MEMORY` 가 아니라
`DEMAND=ORIGINAL_INPX_UNCHANGED` 이면 그 셀은 배율이 안 들어간 것이고, 눈으로는 구분이
안 간다. 게이트맵도 같이 본다(`unmapped_inputs=0` 이 아니면 조용히 오염된 런이다).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "n5-parent-run-evidence-v1"
ANCHORS_SEC = (900, 1500, 2100, 2700)
EXPECTED_CELLS = (
    ("training", 0.75, 13),
    ("training", 0.75, 29),
    ("training", 1.00, 13),
    ("training", 1.00, 29),
    ("congested", 1.25, 13),
    ("congested", 1.25, 29),
    ("holdout", 0.75, 47),
    ("holdout", 1.00, 47),
    ("holdout", 1.25, 47),
)

_DEMAND_RE = re.compile(r"^DEMAND=(\S+)(?:\s+scale=([0-9.]+))?")
_GATE_RE = re.compile(r"^URBAN_GATE_ANCHOR_LOADED\s+mapped_inputs=(\d+)\s+internal_inputs=(\d+)\s+unmapped_inputs=(\d+)")
_SCALE_RE = re.compile(r"^DEMAND_SCALE_APPLIED scale=([0-9.]+) vehicle_inputs=(\d+)")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_runlog_facts(path: Path) -> dict[str, Any]:
    facts: dict[str, Any] = {
        "demand_mode": "",
        "demand_scale_logged": None,
        "scaled_vehicle_inputs": None,
        "gate_mapped_inputs": None,
        "gate_unmapped_inputs": None,
        "decisions_failed": None,
        "run_mode": "",
    }
    if not path.is_file():
        return facts
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        m = _DEMAND_RE.match(line)
        if m:
            facts["demand_mode"] = m.group(1)
            if m.group(2):
                facts["demand_scale_logged"] = float(m.group(2))
            continue
        m = _SCALE_RE.match(line)
        if m:
            facts["demand_scale_logged"] = float(m.group(1))
            facts["scaled_vehicle_inputs"] = int(m.group(2))
            continue
        m = _GATE_RE.match(line)
        if m:
            facts["gate_mapped_inputs"] = int(m.group(1))
            facts["gate_unmapped_inputs"] = int(m.group(3))
            continue
        if line.startswith("DECISIONS_FAILED="):
            facts["decisions_failed"] = int(line.split("=", 1)[1])
        elif line.startswith("RUN_MODE="):
            facts["run_mode"] = line.split("=", 1)[1]
    return facts


def count_csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        return max(0, sum(1 for _ in fh) - 1)


def read_ledger(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {row["name"]: row for row in csv.DictReader(fh) if row.get("name")}


def cell_name(tag: str, role: str, demand: float, seed: int) -> str:
    return f"{tag}_{role}_d{int(round(demand * 100)):03d}_s{seed}"


def collect(run_dir: Path, tag: str) -> dict[str, Any]:
    ledger = read_ledger(run_dir / "n5_parent_ledger.csv")
    reasons: list[str] = []
    cells: list[dict[str, Any]] = []

    for role, demand, seed in EXPECTED_CELLS:
        name = cell_name(tag, role, demand, seed)
        decision_dir = run_dir / f"decisions_{name}"
        state_csv = run_dir / f"state_{name}.csv"
        runlog = run_dir / f"runlog_{name}.txt"
        provenance = run_dir / f"run_provenance_{name}.json"

        anchors: dict[str, Any] = {}
        for sec in ANCHORS_SEC:
            anchor = decision_dir / f"anchor_{sec:06d}.json"
            if anchor.is_file():
                anchors[str(sec)] = {
                    "path": anchor.relative_to(run_dir.parent.parent.parent).as_posix()
                    if anchor.is_absolute()
                    else str(anchor),
                    "sha256": file_sha256(anchor),
                    "size_bytes": anchor.stat().st_size,
                }
            else:
                reasons.append(f"{name}: anchor {sec} 없음")

        facts = read_runlog_facts(runlog)
        row = ledger.get(name, {})
        exit_code = row.get("exit_code", "")

        if not state_csv.is_file():
            reasons.append(f"{name}: 상태 CSV 없음")
        if not provenance.is_file():
            reasons.append(f"{name}: provenance 없음")
        if exit_code not in {"0", ""} or (exit_code == "" and state_csv.is_file() is False):
            reasons.append(f"{name}: exit_code={exit_code!r}")
        # 수요 배율이 실제로 먹었는가. 1.0 이면 스케일링을 건너뛰는 것이 정상이다.
        if abs(demand - 1.0) > 1e-9:
            if facts["demand_mode"] != "SCALED_IN_MEMORY":
                reasons.append(f"{name}: 수요 배율 미적용 (DEMAND={facts['demand_mode']!r})")
            elif facts["demand_scale_logged"] is None or abs(facts["demand_scale_logged"] - demand) > 1e-6:
                reasons.append(
                    f"{name}: 로그 배율 {facts['demand_scale_logged']} != 요청 {demand}"
                )
        # 게이트맵이 옛 판이면 mapped 가 19 로 떨어진다. 그 런은 조용히 오염된 것이다.
        if facts["gate_unmapped_inputs"] not in (0, None) or facts["gate_mapped_inputs"] is None:
            reasons.append(
                f"{name}: 게이트 매핑 이상 mapped={facts['gate_mapped_inputs']} "
                f"unmapped={facts['gate_unmapped_inputs']}"
            )
        if facts["decisions_failed"] not in (0, None):
            reasons.append(f"{name}: DECISIONS_FAILED={facts['decisions_failed']}")

        cells.append(
            {
                "name": name,
                "role": role,
                "demand": demand,
                "seed": seed,
                "exit_code": exit_code,
                "wall_min": row.get("wall_min", ""),
                "state_csv_sha256": file_sha256(state_csv) if state_csv.is_file() else "",
                "state_csv_rows": count_csv_rows(state_csv),
                "run_provenance_sha256": file_sha256(provenance) if provenance.is_file() else "",
                "runlog_facts": facts,
                "anchors": anchors,
                "anchor_count": len(anchors),
            }
        )

    identities = [(c["demand"], c["seed"]) for c in cells]
    if len(identities) != len(set(identities)):
        reasons.append("(demand, seed) 중복")
    training_seeds = {c["seed"] for c in cells if c["role"] != "holdout"}
    holdout_seeds = {c["seed"] for c in cells if c["role"] == "holdout"}
    overlap = sorted(training_seeds & holdout_seeds)
    if overlap:
        reasons.append(f"training/holdout 시드 중복: {overlap}")

    complete = [c for c in cells if c["anchor_count"] == len(ANCHORS_SEC) and c["exit_code"] == "0"]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not reasons else "FAIL",
        "reasons": sorted(set(reasons)),
        "run_dir": str(run_dir),
        "sample_dimensions": {
            "parents_expected": len(EXPECTED_CELLS),
            "parents_complete": len(complete),
            "anchors_per_parent": len(ANCHORS_SEC),
            "anchors_present": sum(c["anchor_count"] for c in cells),
            "anchors_expected": len(EXPECTED_CELLS) * len(ANCHORS_SEC),
        },
        "cells": cells,
    }
    payload["semantic_sha256"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in payload.items() if k != "run_dir"},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--tag", default="n5parent_20260814")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    payload = collect(args.run_dir.resolve(), args.tag)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    dims = payload["sample_dimensions"]
    print(
        "status=%s parents=%d/%d anchors=%d/%d hash=%s"
        % (
            payload["status"],
            dims["parents_complete"],
            dims["parents_expected"],
            dims["anchors_present"],
            dims["anchors_expected"],
            payload["semantic_sha256"][:16],
        )
    )
    for reason in payload["reasons"][:12]:
        print("  " + reason)
    return 2 if args.strict and payload["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
