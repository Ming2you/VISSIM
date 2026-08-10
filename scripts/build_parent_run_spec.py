#!/usr/bin/env python3
# 개발용 부모 런 9개와 두 가지 잡음 바닥을 런 전에 봉인하는 생산자 (v3 N5)
"""Seal the nine development parent runs and the two noise floors before any run.

## 잡음 바닥이 둘이라는 것이 이 모듈의 핵심이다

계획(N5)이 명시한다.

    이것은 VISSIM 런간 분산 척도이고 N9 의 ΔJ 재료성 판정 전용이다.
    플랜트 endpoint 의 재현성 잡음 eps_J_endpoint 는 별개이며 N8-1 에서 따로 측정한다.

하한이 세 자리 다르고(`1e-6 veh·h` 대 `1e-9`) 재는 대상이 다르다. v3 초판이 둘을 합쳐
VISSIM 척도를 endpoint 자리에 넣었는데, 그러면 `eps_g` 가 과대해져
`|intercept| <= median(eps_g)` 가 느슨해지고 재료 표본이 줄어 지지 요건이 무너진다.

그래서 두 함수는 이름도 하한도 분리하고, `eps_j_endpoint` 는 VISSIM 표본을 받으면 거부한다.
막을 수 있는 자리에서 막지 않으면 두 값이 섞였는지는 결과가 이상해진 뒤에야 알게 된다.

## 부모 런 9개

    training   demand 0.75, 1.0      seed 13, 29   4
    congested  demand 1.25           seed 13, 29   2
    holdout    demand 0.75/1.0/1.25  seed 47       3

SPSA 전용 seed 31 은 training 과 **공유**한다 — 별도 3개를 만들지 않는다.
시드 집합 {13, 29, 47} 은 N9 실험 행렬과 같아야 하며 테스트가 그것을 확인한다. 어긋나면
부모 런이 없는 셀이 생기고 그 사실은 런을 다 돌린 뒤에야 드러난다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "parent-run-spec-v3"

# 두 잡음 바닥. 이름을 붙여 분리한다.
EPS_J_VISSIM_FLOOR_VEH_H = 1.0e-6      # VISSIM 런간 분산. N9 의 ΔJ 재료성 판정 전용
EPS_J_ENDPOINT_FLOOR_VEH_H = 1.0e-9    # 플랜트 endpoint 재현성. N8-1 에서 따로 측정

# 부모-anchor 당 base replay 횟수. 계획이 "이 부분은 축소하지 않는다" 고 못박은 값이다.
BASE_REPLAYS_PER_PARENT_ANCHOR = 20

ANCHORS_SEC = (900, 1500, 2100, 2700)

VISSIM_SOURCE = "vissim_base_replay"
ENDPOINT_SOURCE = "plant_endpoint_repeat"


class ParentRunError(ValueError):
    """Raised when the two noise floors would be mixed or a parent set is malformed."""


def default_spec() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "anchor_sec": ANCHORS_SEC,
        "sim_period_sec": 3600,
        "warmup_sec": 900,
        "training": {"demand": (0.75, 1.0), "seeds": (13, 29)},
        "congested": {"demand": (1.25,), "seeds": (13, 29)},
        "holdout": {"demand": (0.75, 1.0, 1.25), "seeds": (47,)},
        # SPSA 는 training 시드를 공유한다. 별도 부모를 만들지 않는다.
        "spsa_seed": 13,
        "base_replays_per_parent_anchor": BASE_REPLAYS_PER_PARENT_ANCHOR,
    }


def expand(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for role in ("training", "congested", "holdout"):
        block = spec[role]
        for demand in block["demand"]:
            for seed in block["seeds"]:
                runs.append(
                    {
                        "role": role,
                        "demand": float(demand),
                        "seed": int(seed),
                        "anchor_sec": tuple(spec["anchor_sec"]),
                        "sim_period_sec": int(spec["sim_period_sec"]),
                        "warmup_sec": int(spec["warmup_sec"]),
                    }
                )
    keys = [(run["demand"], run["seed"]) for run in runs]
    if len(keys) != len(set(keys)):
        raise ParentRunError("duplicate parent identity (demand, seed)")
    return runs


def eps_j_vissim(
    base_objectives: Sequence[float], *, require_full_count: bool = False
) -> float:
    """eps_J_vissim = max(1e-6 veh·h, max_{i,j} |J_i − J_j|).

    독립 `t=0` base replay 들의 최대 격차다. 이후 모든 "효과가 실재하는가" 판정의 기준선이라
    계획이 축소를 금지했다. `require_full_count` 로 20 회를 강제할 수 있다.
    """
    values = [float(v) for v in base_objectives]
    if len(values) < 2:
        raise ParentRunError("need at least two base replays to measure spread")
    if require_full_count and len(values) < BASE_REPLAYS_PER_PARENT_ANCHOR:
        raise ParentRunError(
            f"need {BASE_REPLAYS_PER_PARENT_ANCHOR} base replays, got {len(values)}"
        )
    return max(EPS_J_VISSIM_FLOOR_VEH_H, max(values) - min(values))


def eps_j_endpoint(repeats: Sequence[float], *, source: str) -> float:
    """eps_J_endpoint = max(1e-9, 최대 격차). **VISSIM 표본을 받으면 거부한다.**

    둘을 섞으면 eps_g 가 과대해져 |intercept| <= median(eps_g) 가 느슨해지고 재료 표본이
    줄어 지지 요건이 무너진다. v3 초판이 실제로 그렇게 합쳤다.
    """
    if source != ENDPOINT_SOURCE:
        raise ParentRunError(
            f"eps_j_endpoint requires source={ENDPOINT_SOURCE!r}, got {source!r} "
            "(VISSIM 런간 분산은 eps_j_vissim 이다 - 두 값을 섞지 마라)"
        )
    values = [float(v) for v in repeats]
    if len(values) < 2:
        raise ParentRunError("need at least two endpoint repeats to measure spread")
    return max(EPS_J_ENDPOINT_FLOOR_VEH_H, max(values) - min(values))


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(value[k]) for k in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    return value


def seal_hash(spec: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _canonical(spec), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seal the N5 parent runs")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    spec = default_spec()
    try:
        runs = expand(spec)
        training = {r["seed"] for r in runs if r["role"] != "holdout"}
        holdout = {r["seed"] for r in runs if r["role"] == "holdout"}
        if training & holdout:
            raise ParentRunError(f"training/holdout seed overlap: {sorted(training & holdout)}")
    except ParentRunError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "seal_sha256": seal_hash(spec),
        "spec": _canonical(spec),
        "noise_floors": {
            "eps_j_vissim_floor_veh_h": EPS_J_VISSIM_FLOOR_VEH_H,
            "eps_j_vissim_scope": "VISSIM 런간 분산. N9 의 ΔJ 재료성 판정 전용",
            "eps_j_endpoint_floor_veh_h": EPS_J_ENDPOINT_FLOOR_VEH_H,
            "eps_j_endpoint_scope": "플랜트 endpoint 재현성. N8-1 에서 따로 측정",
            "never_mix": "두 값을 섞으면 eps_g 가 과대해져 지지 요건이 무너진다",
        },
        "sample_dimensions": {
            "parents": len(runs),
            "anchors_per_parent": len(spec["anchor_sec"]),
            "base_replays_per_parent_anchor": BASE_REPLAYS_PER_PARENT_ANCHOR,
            "base_replays_total": len(runs)
            * len(spec["anchor_sec"])
            * BASE_REPLAYS_PER_PARENT_ANCHOR,
        },
        "parent_runs": runs,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    dims = payload["sample_dimensions"]
    print(
        "status=PASS parents=%d base_replays=%d seal=%s"
        % (dims["parents"], dims["base_replays_total"], payload["seal_sha256"][:16])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
