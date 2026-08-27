# -*- coding: utf-8 -*-
"""정본 파라미터가 실제로 실효값이 됐는지 검사한다. 런 전에 돌린다.

왜 필요한가. 2026-08-27 감사에서 확인된 것 — `evaluation/parameters.json` 이 값의
단일 출처라고 선언해 놓고, 그것이 실효값이 됐는지 대조하는 장치가 하나도 살아 있지
않았다. `parameters.audit_against()` 는 정의만 있고 호출자가 0이었다. 그래서
parameters.json 을 고치고 런을 발사한 뒤, 결과를 다 뽑고 나서야 값이 안 들어갔음을
알게 되는 구조였다. 실제로 그 유형의 사고가 셋 있었다(FD 폴백, perimeter 스위치,
rollout_far 미계산).

검사 넷.
  1. parameters.json 의 키가 실효 cfg 와 일치하는가.
  2. 일치하지 않는다면, 그것이 config 에 **선언된 의도적 override** 인가.
     선언 없이 어긋나면 FAIL — 이것이 '조용히 옛 값으로 돌아갔다' 의 신호다.
  3. config 가 parameters 와 **값까지 같은 키**를 중복 보유하는가.
     중복은 tuning 이 parameters 를 이기므로 parameters.json 편집을 무력화한다. FAIL.
  4. 파생량(리더 깊이·녹색 예산·FD 함의 용량)이 저장값과 정합하는가.

사용:  python scripts/verify_parameters.py evaluation/configs/canon_plantfix_20260827.json
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(tuning_path: Path, state_json: Path | None = None) -> list[tuple[str, str]]:
    """(판정, 메시지) 목록. 판정은 OK / FAIL / WARN."""
    sys.path.insert(0, str(R))
    P = _load("canon_parameters", R / "evaluation/parameters.py")
    qb = _load("canon_adapter", R / "evaluation/controllers/vissim_stackelberg_adapter.py")

    tun = qb.load_optional_json(str(tuning_path))
    if not tun:
        return [("FAIL", "tuning 을 읽지 못했다(빈 dict). 경로 오타면 런이 무설정으로 정상 종료한다: %s" % tuning_path)]
    cal = qb.load_optional_json(str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link", cal, tun,
                          local_observation=True, flagship=True)
    qb._plant_rollout_far_into(cfg, tun)
    P.apply_runtime(cfg)

    out: list[tuple[str, str]] = []

    # --- 1·2. 실효값 대조 + 선언된 override 인지 ---
    declared = qb.tuning_to_config_overrides(tun)
    bad = P.audit_against(cfg)
    undeclared = []
    for line in bad:
        key = line.split(":")[0].strip()          # "network.v_free"
        sec, _, k = key.partition(".")
        if k in (declared.get(sec) or {}):
            out.append(("OK", "선언된 override — %s" % line))
        else:
            undeclared.append(line)
    if undeclared:
        for line in undeclared:
            out.append(("FAIL", "선언 없이 어긋남 — %s" % line))
    elif not bad:
        out.append(("OK", "parameters.json 의 모든 키가 실효값과 일치"))

    # --- 3. 순수 중복 ---
    doc = P.load()
    dups = []
    co = tun.get("config_overrides") or {}
    for sec in ("network", "mpc", "leader"):
        pk = {k: v for k, v in (doc.get(sec) or {}).items() if not str(k).startswith("_")}
        for k, v in pk.items():
            for blk, where in ((co.get(sec) or {}, "config_overrides"), (tun.get(sec) or {}, "최상위 %s" % sec)):
                if k in blk and blk[k] == v:
                    dups.append("%s.%s (%s)" % (sec, k, where))
    if dups:
        out.append(("FAIL", "parameters 와 값까지 같은 중복 키 %d개 — tuning 이 이겨서 "
                            "parameters.json 편집이 무시된다: %s" % (len(dups), ", ".join(sorted(set(dups))))))
    else:
        out.append(("OK", "순수 중복 키 없음 — parameters.json 편집이 실효한다"))

    # --- 4. 파생량 정합 ---
    n, m = cfg.network, cfg.mpc
    ld, fd_ = P.leader_rollout_depth(cfg), P.follower_rollout_depth(cfg)
    out.append(("OK" if ld == fd_ else "WARN",
                "리더 롤아웃 깊이 %d · follower %d%s" % (ld, fd_, "" if ld == fd_ else "  ← 둘이 다르다")))
    budget = P.effective_green_total(cfg)
    out.append(("OK", "녹색 예산 %.1f = cycle %.1f - lost %.1f" % (budget, n.cycle_length, n.lost_time)))
    # 나머지 파생 헬퍼도 여기서 실제로 부른다. 호출자가 0인 헬퍼는 조용히 썩는다 —
    # `effective_green_total` 만 고치고 실제 계산 경로(state.py·urban_queue_model.py)는
    # 안 바뀌는 상황이 2026-08-27 감사에서 지적된 그 함정이다. vendor 쪽 호출부를
    # 바꿀 수는 없으므로(수정 금지), 최소한 값이 어긋나면 여기서 잡는다.
    nph = int(getattr(n, "num_phases", 4) or 4)
    dpg = P.default_phase_green(cfg, nph)
    stored_dpg = float(getattr(n, "default_phase_green", dpg))
    out.append((("OK" if abs(dpg - stored_dpg) <= 1e-6 else "FAIL"),
                "기본 현시녹색 파생 %.2f 대 저장 %.2f (현시 %d개)" % (dpg, stored_dpg, nph)))
    gmax = P.phase_green_max(budget, nph)
    stored_gmax = float(getattr(n, "green_max", gmax))
    out.append((("OK" if abs(gmax - stored_gmax) <= 1e-6 else "WARN"),
                "현시 상한 파생 %.1f = 예산 %.1f - (현시 %d-1)x green_min %.0f · 저장 %.1f"
                % (gmax, budget, nph, n.green_min, stored_gmax)))

    lanes = float(getattr(n, "freeway_lanes", 0) or 0)
    stored = float(getattr(n, "freeway_capacity_veh_h", 0) or 0)
    if lanes > 0 and stored > 0:
        implied = n.rho_crit * n.v_free * math.exp(-1.0 / n.metanet_a_m) * lanes
        ratio = implied / stored
        out.append((("OK" if abs(ratio - 1.0) <= 0.05 else "WARN"),
                    "FD 함의 용량 %.0f 대 저장 %.0f (비 %.2f) — 용량은 rho_crit·v_free·a·차로수의 "
                    "파생값이라 어긋나면 둘 중 하나가 틀렸다" % (implied, stored, ratio)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tuning", help="검사할 config (예: evaluation/configs/canon_plantfix_20260827.json)")
    ap.add_argument("--quiet", action="store_true", help="FAIL 만 출력")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = Path(args.tuning)
    if not p.is_absolute():
        p = R / args.tuning
    rows = check(p)
    nfail = sum(1 for t, _ in rows if t == "FAIL")
    for t, msg in rows:
        if args.quiet and t != "FAIL":
            continue
        print("  %-4s %s" % (t, msg))
    print("파라미터 검사 %s — %s" % ("FAIL" if nfail else "PASS", p.name))
    return 1 if nfail else 0


if __name__ == "__main__":
    raise SystemExit(main())
