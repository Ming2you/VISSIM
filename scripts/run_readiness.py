#!/usr/bin/env python3
# 실 VISSIM 런 착수 준비도와 실행 순서를 판정하는 도구 (v3)
"""Judge whether the real VISSIM runs can start, and in what order.

v3 의 절반 이상이 실 런에 걸려 있다 — N4-6 · N4-7 · N6 · N8-1 · N8-4 · N1b · N9 · N10.
런 전 조건과 각 런이 무엇을 푸는지가 계획 여러 절에 흩어져 있어, 순서를 짜려면 문서를 다시
읽어야 한다. 그 판정을 여기서 한다.

## 두 가지 목적

**착수 전 차단.** 사슬(runtime_source / preflight / approval)이 PASS 가 아니거나 봉인된
명세가 없으면 시작하면 안 된다. 1,620 셀을 돌린 뒤에 아는 것은 되돌릴 수 없다.

**순서 제시.** 부모 런(N5)이 N6 캘리브레이션과 N9 의 `eps_J_vissim` 을 공급하므로 먼저다.
그 의존을 코드로 표현해 두면 순서를 기억에 의존하지 않는다.

미측정을 준비된 것으로 세지 않는다. 이 저장소의 다른 게이트와 같은 규칙이다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence


SCHEMA_VERSION = "run-readiness-v3"

# 런 전에 PASS 여야 하는 승인 사슬.
CHAIN_ARTIFACTS = (
    "runtime_source_v2_1.json",
    "preflight_manifest_v3.json",
    "topology_approval_v2_1.json",
)

# 사후 조정을 막으려면 런 전에 봉인돼 있어야 하는 명세.
SEALED_SPECS = (
    "parent_runs_v3.json",
    "experiment_matrix_v3.json",
)

# 참고용 산출물. 없으면 경고하되 차단하지는 않는다.
ADVISORY_ARTIFACTS = (
    "signal_group_timing_v3.json",
    "movement_signal_group_map_v3.json",
    "signal_group_actuation_plan_v3.json",
)

# 실행 순서. 앞이 뒤를 푼다.
STAGES: tuple[dict[str, Any], ...] = (
    {
        "name": "N5_parent_runs",
        "what": "개발용 부모 런 9개(demand 3 x seed 3) + 부모-anchor 당 base replay 20회",
        "command": (
            "powershell -File scripts/run_plant_fidelity_matrix.ps1 "
            "-Strict -RequireComplete -OutDir evaluation\\runs\\<new>"
        ),
        "produces": ["anchor 상태 900/1500/2100/2700", "eps_J_vissim"],
        "unblocks": ["N6_calibration", "N9_paired_matrix"],
        "note": "러너 기본값이 시드 13/29/47 x demand 0.75/1.0/1.25 라 부모 9개와 일치한다.",
    },
    {
        "name": "N4_6_signal_oracle",
        "what": "의도한 SG 타이밍이 VISSIM 에 실현됐는지 readback 으로 입증",
        "command": "scripts/verify_signal_timing_oracle.py (런 산출물 대상)",
        "produces": ["valid-interval 계약 입증"],
        "unblocks": ["N4_7_offset_promotion"],
        "note": "양자화 0.99s 가 게이트 0.5s 를 넘는 문제가 먼저 해결돼야 한다.",
    },
    {
        "name": "N6_calibration",
        "what": "jam density 재적합. 표본 >=200, 포화 lane-group >=30, CI 반폭 <=10%",
        "command": "scripts/validate_physical_stock_calibration.py --calibration <new>",
        "produces": ["physical_stock_calibration_v3.json"],
        "unblocks": ["N10_promotion"],
        "note": "현 자료는 표본 177 로 미달이고 CI 가 없다. 관측을 더 모아야 한다.",
    },
    {
        "name": "N8_1_fd_vs_spsa",
        "what": "endpoint 재현성 잡음 eps_J_endpoint 를 동일 control 20회 평가로 측정",
        "command": "(N7 endpoint 를 쓰는 자격심사 하네스)",
        "produces": ["eps_J_endpoint", "eps_g"],
        "unblocks": ["N10_promotion"],
        "note": "N5 의 eps_J_vissim 을 여기 쓰지 마라. 하한이 세 자리 다르다.",
    },
    {
        "name": "N8_4_runtime_contract",
        "what": "end-to-end p95 <=30s. stratum 별 50 attempt, 독립 런 5개",
        "command": "scripts/run_real_world_single_watchdog_distributed_core15n41.ps1",
        "produces": ["런타임 계약 증거"],
        "unblocks": ["N1b_mpc_capture", "N10_promotion"],
        "note": "결정당 solve 실측 중앙값 11.0s / p95 12.9s (런로그 217개).",
    },
    {
        "name": "N1b_mpc_capture",
        "what": "MPC 캡처 61회",
        "command": "(B1a 캡처 경로, N8-4 계약 충족 후)",
        "produces": ["MPC 초기상태 투영 증거"],
        "unblocks": ["N10_promotion"],
        "note": "",
    },
    {
        "name": "N4_7_offset_promotion",
        "what": "offset 승격 잠금 해제 판정",
        "command": "evaluation/controllers/offset_promotion.py 판정",
        "produces": ["offset writer 승격 여부"],
        "unblocks": ["N9_paired_matrix (offset 레버 540셀)"],
        "note": "D-core PASS + N9 효과/순위 + N8-4 런타임이 모두 PASS 해야 열린다.",
    },
    {
        "name": "N9_paired_matrix",
        "what": "짝지은 검증 1,620셀 (offset BLOCKED 540 제외)",
        "command": "(행렬 봉인 d397fa07d1c05692 기준 순차 실행)",
        "produces": ["ΔJ, 효과/순위, spillback"],
        "unblocks": ["N10_promotion"],
        "note": "solve 182h + VISSIM 시뮬 994h(30~60배속 17~33h) = 8~9일 규모.",
    },
    {
        "name": "N10_promotion",
        "what": "세 demand 의 holdout 시드에서 필수 게이트 PASS 여야 승격",
        "command": "scripts/audit_plant_fidelity.py",
        "produces": ["승격 판정"],
        "unblocks": [],
        "note": "저수요라고 spillback 외 지표를 면제하지 않는다.",
    },
)


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def evaluate(repo: Path) -> dict[str, Any]:
    outputs = Path(repo) / "outputs"
    blocking: list[str] = []
    advisory: list[str] = []
    checked: dict[str, Any] = {}

    for name in CHAIN_ARTIFACTS:
        payload = _load(outputs / name)
        if payload is None:
            blocking.append(f"{name}: 없음")
            continue
        status = payload.get("status")
        checked[name] = status
        if status != "PASS":
            blocking.append(f"{name}: status={status!r}")

    for name in SEALED_SPECS:
        payload = _load(outputs / name)
        if payload is None:
            blocking.append(f"{name}: 없음")
            continue
        seal = payload.get("seal_sha256")
        checked[name] = seal
        if not seal:
            # 봉인이 없으면 사후 조정을 막을 수 없다.
            blocking.append(f"{name}: seal_sha256 없음")

    for name in ADVISORY_ARTIFACTS:
        if not (outputs / name).is_file():
            advisory.append(f"{name}: 없음")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED" if blocking else "READY",
        "blocking": blocking,
        "advisory": advisory,
        "checked": checked,
        "stages": list(STAGES),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Judge real-run readiness and order")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    report = evaluate(args.repo)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    print("status=%s" % report["status"])
    for reason in report["blocking"]:
        print("  BLOCKING:", reason)
    for reason in report["advisory"]:
        print("  advisory:", reason)
    print()
    print("실행 순서")
    for index, stage in enumerate(report["stages"], 1):
        print("  %d. %-24s %s" % (index, stage["name"], stage["what"]))
        if stage["unblocks"]:
            print("     푸는 것: %s" % ", ".join(stage["unblocks"]))
        if stage["note"]:
            print("     주의: %s" % stage["note"])
    return 0 if report["status"] == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
