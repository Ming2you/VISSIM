#!/usr/bin/env python3
# 짝지은 VISSIM 검증의 실험 행렬을 런 전에 전개하고 봉인하는 생산자 (v3 N9-1/N9-2)
"""Expand and seal the paired-VISSIM experiment matrix before any run starts.

The plan requires the amplitudes to be pre-registered:

    값을 사후 조정하지 않고 요청 매니페스트에 정확한 값을 먼저 봉인한다.

That is the whole point of this module. If the lever amplitudes can be edited after
seeing a run, pre-registration is theatre. So expansion is a pure function of a spec,
the spec is hashed, and the manifest carries the hash.

It also counts the matrix before anyone spends VISSIM wall-clock on it. A design error
found after 700 runs cannot be undone; found here it costs nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.controllers import offset_promotion  # noqa: E402


SCHEMA_VERSION = "experiment-matrix-v3"

# v2.1 은 21필드였다. v3 는 run-level provenance 를 덜어내고 13필드로 줄였다.
# 순서가 키의 일부다 - 바꾸면 과거 런 키와 대조가 안 된다.
RUN_KEY_FIELDS = (
    "experiment_id",
    "inpx_hash",
    "topology_sha256",
    "calibration_version",
    "controller_version",
    "demand",
    "seed",
    "anchor_sec",
    "H",
    "channel",
    "lever_id",
    "action_payload_hash",
    "replicate",
)

# 실행 키 중 **설계가 아니라 신원** 인 필드. spec 에는 없고 런 전에 외부에서 주입된다.
# 봉인이 이것을 빼면 매트릭스는 어떤 위상에도 묶이지 않는다 - 격자를 바꿔도 봉인이 그대로라
# 사후에 "같은 위상에서 돌린 결과" 라고 주장할 근거가 없다. 실제로 그랬다: `--topology-sha256`
# 을 서로 다르게 줘도 봉인이 d397fa07d1c05692 로 같았다.
IDENTITY_FIELDS = (
    "inpx_hash",
    "topology_sha256",
    "calibration_version",
    "controller_version",
)

# 신원이 아직 안 정해졌다는 표시. 이 값으로 봉인된 매트릭스는 위상에 묶이지 않은 것이고,
# 그 사실이 산출물의 `identity` 에 그대로 남는다.
IDENTITY_PENDING = "PENDING"

# 위상 해시는 sha256 이거나 PENDING 이다. 짧은/오타난 값을 받아 봉인하면 묶인 것처럼
# 보이는데 묶인 것이 없다. 형식은 canonical topology 의 `topology_hash` 와 같다.
_SHA256_RE = re.compile(r"[0-9a-f]{64}")

# 사전등록 진폭. base 대비 (low, base, high).
LEVER_AMPLITUDES: dict[str, tuple[float, float, float]] = {
    "green": (-10.0, 0.0, 10.0),          # 초. 정본 tangent 기저
    "vsl": (-10.0, 0.0, 10.0),            # km/h
    "ramp_meter": (-150.0, 0.0, 150.0),   # veh/h
    "offset": (-10.0, 0.0, 10.0),         # 초. native cycle modulo
}

LEVER_UNITS = {
    "green": "sec",
    "vsl": "kph",
    "ramp_meter": "veh_h",
    "offset": "sec",
}

# offset 은 production writer 와 분리된 test-only writer 가 적용한다. 실현 readback 이
# valid-interval 계약을 입증하기 전까지(N4-6 D-core PASS) BLOCKED 다.
#
# 이 두 값은 **손으로 적지 않는다.** N4-7 삼중 잠금 판정(evaluation/controllers/
# offset_promotion.py)에서 유도한다. 여기에 "PLANNED"/"production" 을 직접 적을 수
# 있으면 행렬과 실제 writer 동작이 조용히 어긋나고, 그 어긋남은 런을 다 돌린 뒤에야
# 드러난다. 승격 증거가 갖춰지면 이 파일을 고치지 않아도 두 값이 함께 열린다.
_OFFSET_VERDICT = offset_promotion.evaluate()

LEVER_WRITER = {
    "green": "production",
    "vsl": "production",
    "ramp_meter": "production",
    "offset": offset_promotion.matrix_lever_writer(_OFFSET_VERDICT),
}
LEVER_STATUS = {
    "green": "PLANNED",
    "vsl": "PLANNED",
    "ramp_meter": "PLANNED",
    "offset": offset_promotion.matrix_lever_status(_OFFSET_VERDICT),
}

# 레버가 어느 채널에 작용하는가. 집계와 게이트가 채널별로 갈리므로 셀에 새긴다.
LEVER_CHANNEL = {
    "green": "urban_signal",
    "vsl": "freeway_vsl",
    "ramp_meter": "ramp_metering",
    "offset": "urban_signal",
}

LEVEL_NAMES = ("low", "base", "high")


class MatrixError(RuntimeError):
    """Raised when a cell or spec would silently corrupt the run identity."""


def default_spec() -> dict[str, Any]:
    """The pre-registered v3 N9-2 matrix."""
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": "n9_paired_single_lever_v3",
        "demand": (0.75, 1.0, 1.25),
        "anchor_sec": (900, 1500, 2100, 2700),
        "H": (1, 3, 5, 10, 15),
        "sim_period_sec": 3600,
        "warmup_sec": 900,
        "control_interval_sec": 60,
        # development 진단은 13/29 만 쓴다. 승격 판정은 holdout 시드만 쓴다.
        #
        # holdout 은 N5 가 정한 **단일 시드 47** 이다. v2.1 의 인증 wave 3시드(47/59/71)를
        # 대신하는 값이라 여기서 임의로 늘리면 N5 부모 런 9개(demand 3 x seed 3)와 어긋나
        # 부모 런이 없는 셀이 생긴다. 그 어긋남은 런을 다 돌린 뒤에야 드러난다.
        "development_seeds": (13, 29),
        "holdout_seeds": (47,),
        "replicates": 1,
        "levers": tuple(LEVER_AMPLITUDES),
        "lever_amplitudes": dict(LEVER_AMPLITUDES),
    }


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def seal_hash(spec: Mapping[str, Any], identity: Mapping[str, Any]) -> str:
    """Hash the spec **and the run identity** so both are covered by one seal.

    Tuples and lists collapse to the same canonical form on purpose - the seal is about
    the values, not the Python container they arrived in.

    `identity` is mandatory and must be exactly `IDENTITY_FIELDS`. Defaulting a missing
    field to "" (or leaving it out of the hash, which is what v3 did until now) makes two
    genuinely different topologies produce one seal - the same failure mode `run_key`
    already refuses, one level up.
    """
    supplied = set(identity)
    missing = sorted(set(IDENTITY_FIELDS) - supplied)
    if missing:
        raise MatrixError(f"seal identity is missing fields: {missing}")
    extra = sorted(supplied - set(IDENTITY_FIELDS))
    if extra:
        raise MatrixError(f"seal identity has unknown fields: {extra}")
    encoded = json.dumps(
        {"spec": _canonical(spec), "identity": _canonical(identity)},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_key(cell: Mapping[str, Any]) -> str:
    """Canonical run key over exactly the 13 planned fields.

    Missing fields are an error, not an empty string. Filling a gap with "" makes two
    genuinely different cells share one key, and the collision only surfaces when the
    results disagree - long after the wall-clock is spent.
    """
    supplied = {key for key in cell if key in RUN_KEY_FIELDS}
    missing = sorted(set(RUN_KEY_FIELDS) - supplied)
    if missing:
        raise MatrixError(f"run key is missing fields: {missing}")
    extra = sorted(set(cell) - set(RUN_KEY_FIELDS) - _CELL_ANNOTATIONS)
    if extra:
        raise MatrixError(f"run key has unknown fields: {extra}")
    return "|".join(f"{name}={cell[name]}" for name in RUN_KEY_FIELDS)


# 런 키에는 안 들어가지만 셀에 붙여 두는 주석 필드. 실행/집계가 참조한다.
_CELL_ANNOTATIONS = {
    "level",
    "amplitude",
    "unit",
    "writer",
    "status",
    "seed_role",
    "horizon_end_sec",
}


def _action_payload_hash(lever: str, level: str, amplitude: float) -> str:
    encoded = json.dumps(
        {"lever": lever, "level": level, "amplitude": amplitude},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def expand(
    spec: Mapping[str, Any],
    *,
    inpx_hash: str = "PENDING",
    topology_sha256: str = "PENDING",
    calibration_version: str = "PENDING",
    controller_version: str = "PENDING",
) -> list[dict[str, Any]]:
    """Expand the spec into one cell per (demand, seed, anchor, H, lever, level, replicate).

    Identity placeholders default to "PENDING" so the matrix can be sealed before the
    network and calibration are pinned. The seal covers the identity too, so a matrix
    sealed with "PENDING" is on the record as *not bound to a topology* - re-sealing with
    the real values is what binds it, and that changes the seal.
    """
    interval = int(spec["control_interval_sec"])
    period = int(spec["sim_period_sec"])
    amplitudes: Mapping[str, Iterable[float]] = spec["lever_amplitudes"]

    seed_roles = [(seed, "development") for seed in spec["development_seeds"]]
    seed_roles += [(seed, "holdout") for seed in spec["holdout_seeds"]]

    cells: list[dict[str, Any]] = []
    for demand in spec["demand"]:
        for seed, seed_role in seed_roles:
            for anchor in spec["anchor_sec"]:
                for horizon in spec["H"]:
                    end = anchor + horizon * interval
                    if end > period:
                        # anchor 2700 + H15 = 3600 이 상한이다. 넘는 조합은 잘린 셀이라
                        # 비교 대상이 못 된다. 조용히 자르지 않고 아예 만들지 않는다.
                        continue
                    for lever in spec["levers"]:
                        for level, amplitude in zip(LEVEL_NAMES, amplitudes[lever]):
                            for replicate in range(1, int(spec["replicates"]) + 1):
                                cells.append(
                                    {
                                        "experiment_id": spec["experiment_id"],
                                        "inpx_hash": inpx_hash,
                                        "topology_sha256": topology_sha256,
                                        "calibration_version": calibration_version,
                                        "controller_version": controller_version,
                                        "demand": demand,
                                        "seed": seed,
                                        "anchor_sec": anchor,
                                        "H": horizon,
                                        "channel": LEVER_CHANNEL[lever],
                                        "lever_id": lever,
                                        "action_payload_hash": _action_payload_hash(
                                            lever, level, float(amplitude)
                                        ),
                                        "replicate": replicate,
                                        "level": level,
                                        "amplitude": float(amplitude),
                                        "unit": LEVER_UNITS[lever],
                                        "writer": LEVER_WRITER[lever],
                                        "status": LEVER_STATUS[lever],
                                        "seed_role": seed_role,
                                        "horizon_end_sec": end,
                                    }
                                )
    return cells


def material_comparison_counts(spec: Mapping[str, Any]) -> dict[str, int]:
    """Count non-base cells per (demand, H, channel).

    계획은 레버 효과에 demand x H x 채널마다 재료 비교 16개 이상을 요구한다. BLOCKED 레버는
    실제로 돌지 않으므로 세지 않는다 - 세면 통과한 것처럼 보이는데 자료가 없다.
    """
    counts: dict[str, int] = {}
    for cell in expand(spec):
        if cell["level"] == "base" or cell["status"] == "BLOCKED":
            continue
        key = f"demand={cell['demand']}|H={cell['H']}|channel={cell['channel']}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expand and seal the N9 experiment matrix")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--inpx-hash", default=IDENTITY_PENDING)
    parser.add_argument("--topology-sha256", default=IDENTITY_PENDING)
    parser.add_argument("--calibration-version", default=IDENTITY_PENDING)
    parser.add_argument("--controller-version", default=IDENTITY_PENDING)
    args = parser.parse_args(argv)

    spec = default_spec()
    # 셀과 봉인이 **같은 하나의 신원** 을 읽는다. 둘을 따로 채우면 조용히 어긋난다.
    identity = {
        "inpx_hash": args.inpx_hash,
        "topology_sha256": args.topology_sha256,
        "calibration_version": args.calibration_version,
        "controller_version": args.controller_version,
    }
    try:
        topology = identity["topology_sha256"]
        if topology != IDENTITY_PENDING and not _SHA256_RE.fullmatch(topology):
            raise MatrixError(
                f"topology_sha256 must be 64 lowercase hex or {IDENTITY_PENDING!r}, "
                f"got {topology!r}"
            )
        cells = expand(spec, **identity)
        keys = [run_key(cell) for cell in cells]
        if len(keys) != len(set(keys)):
            raise MatrixError("run keys collide - the matrix identity is not unique")
        shortfall = {k: v for k, v in material_comparison_counts(spec).items() if v < 16}
        if shortfall:
            raise MatrixError(f"material comparisons below 16: {shortfall}")
    except (MatrixError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    blocked = sum(1 for cell in cells if cell["status"] == "BLOCKED")
    # 런 전에 규모를 드러낸다. 각 branch 는 계획(N9-1)대로 t=0 부터 재실행하므로 비용은
    # horizon_end 까지의 시뮬 초다. BLOCKED 는 돌지 않으므로 빼야 예산이 맞는다.
    runnable = [cell for cell in cells if cell["status"] != "BLOCKED"]
    total_sec = sum(cell["horizon_end_sec"] for cell in runnable)
    decisions = sum(
        cell["horizon_end_sec"] // int(spec["control_interval_sec"]) for cell in runnable
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "seal_sha256": seal_hash(spec, identity),
        "run_key_fields": list(RUN_KEY_FIELDS),
        # 봉인 입력을 산출물에 그대로 싣는다. 없으면 제3자가 봉인을 재계산할 수 없다.
        "identity": _canonical(identity),
        "spec": _canonical(spec),
        "sample_dimensions": {
            "cells": len(cells),
            "runnable_cells": len(cells) - blocked,
            "blocked_cells": blocked,
            "material_comparison_groups": len(material_comparison_counts(spec)),
            "total_simulated_sec": total_sec,
            "control_decisions": decisions,
        },
        "cells": cells,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "status=PASS cells=%d runnable=%d blocked=%d topology=%s seal=%s"
        % (
            len(cells),
            len(cells) - blocked,
            blocked,
            identity["topology_sha256"][:16],
            payload["seal_sha256"][:16],
        )
    )
    print(
        "cost: %.0f simulated hours over %d control decisions"
        % (total_sec / 3600.0, decisions)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
