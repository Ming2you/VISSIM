# 구성 그리드(FD x 토폴로지 x capacity drop)가 의도한 cfg 값으로 실체화되는지 확인하는 사전 검증기.
"""각 채점 구성이 실제로 무엇을 바꾸는지 cfg 수준에서 찍어 본다.

측정 전에 이걸 먼저 돌린다. 구성 파일이 의도한 값을 만들지 못하면 이후 지표는 전부
무의미하다. `assert` 로 고정하지 않고 표로 찍는 이유는, 어떤 값이 어디서 오는지를
보고서에 그대로 옮기기 위해서다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import episode as ep  # noqa: E402  (g6 디렉터리를 sys.path 에 넣어 준다)
import g6_core as core  # noqa: E402

CONFIG_DIR = core.VISSIM_ROOT / "evaluation" / "configs" / "gates_scoring"
PROBE_STATE = (core.VISSIM_ROOT / "evaluation/runs/new_baseline_ab_20260801"
               / "decisions_pstack_flagship_scale135_warm900_eval3600_seed13/state_000900.json")

CONFIGS = {
    "a_FDA_pre":     CONFIG_DIR / "gates_cfgA_pre.json",
    "b_FDA_post":    CONFIG_DIR / "gates_cfgB_post.json",
    "c_FDC_post":    CONFIG_DIR / "gates_cfgC_fdc_post.json",
    "d_FDA_post_cd": CONFIG_DIR / "gates_cfgD_fda_post_cd.json",
    "e_FDC_post_cd": CONFIG_DIR / "gates_cfgE_fdc_post_cd.json",
}


def main() -> int:
    state_json = json.loads(PROBE_STATE.read_text(encoding="utf-8"))
    rows = []
    for name, path in CONFIGS.items():
        rt = core.build_runtime(state_json, tuning_json=path)
        net = rt.cfg.network
        profile = getattr(net, "freeway_segment_length_profile_km", {}) or {}
        rows.append({
            "config": name,
            "tuning": path.name,
            "v_free": float(net.v_free),
            "rho_crit": float(net.rho_crit),
            "a_m": float(getattr(net, "metanet_a_m", float("nan"))),
            "q_cap_veh_h": float(net.freeway_capacity_veh_h),
            "seg_len_scalar_km": float(net.freeway_segment_length_km),
            "profile_FW_E_km": (profile.get("FW_E") or [None])[0],
            "profile_FW_W_km": (profile.get("FW_W") or [None])[0],
            "phi_cd": float(getattr(net, "capacity_drop_discharge_phi", 1.0) or 1.0),
            "control_interval_sec": float(rt.cfg.simulation.control_interval),
        })
    width = {k: max(len(k), *(len(f"{r[k]}") for r in rows)) for k in rows[0]}
    print(" | ".join(k.ljust(width[k]) for k in rows[0]))
    for row in rows:
        print(" | ".join(f"{row[k]}".ljust(width[k]) for k in row))

    # 기하 정정 전/후가 실제로 다른 격자인지 한 번 더 못박는다.
    pre = next(r for r in rows if r["config"] == "a_FDA_pre")
    post = next(r for r in rows if r["config"] == "b_FDA_post")
    assert pre["profile_FW_E_km"] != post["profile_FW_E_km"], "토폴로지 정정이 반영되지 않았다"
    assert abs(pre["seg_len_scalar_km"] - 0.795059) < 1e-6
    assert abs(post["seg_len_scalar_km"] - 1.346925) < 1e-6
    fdc = next(r for r in rows if r["config"] == "c_FDC_post")
    assert abs(fdc["rho_crit"] - 21.419) < 1e-6 and abs(post["rho_crit"] - 16.354) < 1e-6
    cd = next(r for r in rows if r["config"] == "d_FDA_post_cd")
    assert abs(cd["phi_cd"] - 0.6) < 1e-9 and abs(post["phi_cd"] - 1.0) < 1e-9
    print("\nOK: 5개 구성이 전부 의도한 값으로 실체화된다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
