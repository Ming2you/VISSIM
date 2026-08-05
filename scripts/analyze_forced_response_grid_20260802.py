# 강제응답 그리드 산출물 분석기 - 인가 검증 + METANET tau/nu/kappa/delta_merge 식별가능성 판정.
#
# 세 가지를 낸다.
#  1) 인가 검증: 각 arm 의 action CSV 에서 VSL 지령/readback 과 램프 rate/green 이
#     의도한 값으로 실제로 걸렸는지. 기준선에서 배운 교훈 - 인가 확인 없이 결과를 쓰지 않는다.
#  2) 여기(excitation) 요약: 세그먼트 밀도/속도 분포, 임계 초과 비율, 공간 밀도 구배.
#  3) 항별 식별가능성 판정: kappa(자유류), nu(구배), tau(계단 응답), delta_merge(합류 세그먼트 대비).

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RHO_CRIT = 16.354
V_FREE = 119.505

# 램프가 합류하는 모델 세그먼트 (calibration ramp_meter_connectors 의 to_model_*)
MERGE_SEGMENTS = {"RW_FW_W_S2", "RW_FW_W_S4", "RW_FW_W_S5", "RW_FW_E_S3", "RW_FW_E_S5"}

# arm 별 의도한 인가값. None 이면 그 레버는 강제하지 않는다.
ARM_INTENT = {
    "nc": {"vsl_kph": 120.0, "ramp_group_vph": 1800.0, "family": "no-control"},
    "fixed57": {"vsl_kph": 120.0, "ramp_group_vph": 1800.0, "family": "fixed57"},
    "vsl100": {"vsl_kph": 100.0, "ramp_group_vph": 1800.0, "family": "fixed57"},
    "vsl80": {"vsl_kph": 80.0, "ramp_group_vph": 1800.0, "family": "fixed57"},
    "rm735": {"vsl_kph": 120.0, "ramp_group_vph": 735.0, "family": "fixed57"},
    "rm360": {"vsl_kph": 120.0, "ramp_group_vph": 360.0, "family": "fixed57"},
    "incf57": {"vsl_kph": 120.0, "ramp_group_vph": 1800.0, "family": "fixed57+incident"},
}

NAME_RE = re.compile(r"^(?P<dem>fw\d+)_(?P<arm>[a-z0-9]+)_seed(?P<seed>\d+)$")


def parse_name(stem: str, prefix: str) -> dict | None:
    m = NAME_RE.match(stem[len(prefix):])
    return m.groupdict() if m else None


def verify_actuation(action_csv: Path, arm: str, control_start: int) -> dict:
    d = pd.read_csv(action_csv)
    intent = ARM_INTENT[arm]
    out: dict = {"action_rows": int(len(d)), "kinds": {k: int(v) for k, v in d["kind"].value_counts().items()}}

    vsl = d[d["kind"] == "vsl"]
    post = vsl[vsl["sim_sec"] >= control_start]
    src = post if len(post) else vsl
    out["vsl_applied_at_sec"] = sorted(int(x) for x in src["sim_sec"].unique())[:5]
    out["vsl_commanded_uniques"] = sorted(float(x) for x in src["speed_kph"].dropna().unique())
    rb = src["readback"].astype(str)
    out["vsl_readback_uniques"] = sorted(rb.unique().tolist())[:6]
    # readback 형식 "class10|class70" - 둘 다 지령과 같아야 한다.
    ok = True
    for v in rb.unique():
        parts = str(v).split("|")
        if len(parts) != 2:
            ok = False
            continue
        try:
            ok &= all(abs(float(p) - intent["vsl_kph"]) < 1e-6 for p in parts)
        except ValueError:
            ok = False
    out["vsl_dsd_count"] = int(src["dsd_no"].nunique())
    out["vsl_ok"] = bool(ok and len(src) > 0 and
                         all(abs(x - intent["vsl_kph"]) < 1e-6 for x in out["vsl_commanded_uniques"]))

    rm = d[d["kind"] == "ramp_meter"]
    rmp = rm[rm["sim_sec"] >= control_start]
    rsrc = rmp if len(rmp) else rm
    out["ramp_applied_at_sec"] = sorted(int(x) for x in rsrc["sim_sec"].unique())[:5]
    out["ramp_rate_vph_uniques"] = sorted(float(x) for x in rsrc["rate_vph"].dropna().unique())
    out["ramp_green_sec_uniques"] = sorted(float(x) for x in rsrc["green_sec"].dropna().unique())
    out["ramp_connectors"] = int(rsrc["id"].nunique())
    grp = []
    for m in rsrc["metadata"].astype(str):
        mm = re.search(r"group_rate_vph=([0-9.]+)", m)
        if mm:
            grp.append(float(mm.group(1)))
    out["ramp_group_rate_uniques"] = sorted(set(grp))
    # 커넥터 rate 는 모델 램프 그룹 rate 의 절반 (램프당 커넥터 2개)
    expect_conn = intent["ramp_group_vph"] / 2.0
    out["ramp_expected_connector_vph"] = expect_conn
    # 어댑터가 green = round(cycle * rate / 900) 로 정수 초 양자화하므로 실제
    # 방류율은 지령과 다르다. 인가 검증은 실현 green 기준으로도 봐야 한다.
    out["ramp_realized_group_vph"] = sorted(
        {round(g / 10.0 * 900.0 * 2.0, 3) for g in out["ramp_green_sec_uniques"]}
    )
    out["ramp_ok"] = bool(
        len(out["ramp_rate_vph_uniques"]) > 0
        and all(abs(x - expect_conn) < 1e-3 for x in out["ramp_rate_vph_uniques"])
    )
    return out


def segment_stats(seg_csv: Path, lo: int, hi: int) -> dict:
    d = pd.read_csv(seg_csv)
    w = d[(d.sim_sec >= lo) & (d.sim_sec <= hi)].copy()
    rho = w["density_veh_km_lane"]
    v = w["mean_speed_kph"]
    # 공간 구배: 같은 시각 같은 방향에서 segment_index 순 차분
    w = w.sort_values(["sim_sec", "model_link", "segment_index"])
    w["drho"] = w.groupby(["sim_sec", "model_link"])["density_veh_km_lane"].diff()
    g = w["drho"].abs().dropna()
    merge = w[w.segment_id.isin(MERGE_SEGMENTS)]
    return {
        "n_samples": int(len(w)),
        "n_timesteps": int(w.sim_sec.nunique()),
        "rho_mean": float(rho.mean()),
        "rho_p50": float(rho.quantile(0.5)),
        "rho_p95": float(rho.quantile(0.95)),
        "rho_max": float(rho.max()),
        "frac_rho_gt_crit": float((rho > RHO_CRIT).mean()),
        "frac_rho_gt_20": float((rho > 20).mean()),
        "frac_rho_gt_30": float((rho > 30).mean()),
        "speed_mean": float(v.mean()),
        "speed_p05": float(v.quantile(0.05)),
        "speed_min": float(v.min()),
        "abs_drho_mean": float(g.mean()),
        "abs_drho_p95": float(g.quantile(0.95)),
        "frac_abs_drho_gt_5": float((g > 5).mean()),
        "merge_rho_mean": float(merge["density_veh_km_lane"].mean()) if len(merge) else float("nan"),
        "merge_speed_mean": float(merge["mean_speed_kph"].mean()) if len(merge) else float("nan"),
    }


def step_response(seg_csv: Path, control_start: int, window: int = 300) -> dict:
    """t=control_start 계단 직전/직후 본선 평균 속도 궤적. tau 관측 가능성 판정용."""
    d = pd.read_csv(seg_csv)
    ts = d.groupby("sim_sec")["mean_speed_kph"].mean()
    pre = ts[(ts.index >= control_start - window) & (ts.index < control_start)]
    post = ts[(ts.index >= control_start) & (ts.index <= control_start + window)]
    if len(pre) == 0 or len(post) < 3:
        return {"pre_mean": float("nan"), "post_samples": int(len(post))}
    v0 = float(pre.mean())
    vend = float(post.iloc[-max(1, len(post) // 5):].mean())
    drop = v0 - vend
    out = {
        "pre_mean_kph": v0,
        "post_settle_kph": vend,
        "step_drop_kph": drop,
        "post_samples": int(len(post)),
        "post_sample_dt_sec": float(np.median(np.diff(post.index.values))) if len(post) > 1 else float("nan"),
    }
    # 63% 도달 시점 -> 1차 완화 시정수의 조야한 추정
    if abs(drop) > 1.0:
        target = v0 - 0.632 * drop
        hit = post[(post - target) * np.sign(-drop) >= 0]
        out["tau_hat_sec"] = float(hit.index[0] - control_start) if len(hit) else float("nan")
    else:
        out["tau_hat_sec"] = float("nan")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    p.add_argument("--control-start-sec", type=int, default=900)
    p.add_argument("--eval-end-sec", type=int, default=4500)
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-csv", required=True)
    args = p.parse_args()

    run_dir = Path(args.run_dir)
    rows = []
    for seg in sorted(run_dir.glob("bottleneck_segments_*.csv")):
        meta = parse_name(seg.stem, "bottleneck_segments_")
        if not meta:
            continue
        name = seg.stem[len("bottleneck_segments_"):]
        act = run_dir / f"action_{name}.csv"
        rec = {"name": name, **meta}
        rec.update(segment_stats(seg, args.control_start_sec, args.eval_end_sec))
        rec.update({f"step_{k}": v for k, v in step_response(seg, args.control_start_sec).items()})
        if act.exists():
            try:
                rec.update({f"act_{k}": v for k, v in
                            verify_actuation(act, meta["arm"], args.control_start_sec).items()})
            except Exception as exc:  # noqa: BLE001
                rec["act_error"] = repr(exc)
        else:
            rec["act_error"] = "action_csv_missing"
        rows.append(rec)

    df = pd.DataFrame(rows)
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    flat = df.copy()
    for c in flat.columns:
        if flat[c].apply(lambda x: isinstance(x, (list, dict))).any():
            flat[c] = flat[c].apply(json.dumps)
    flat.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    Path(args.out_json).write_text(
        json.dumps({"rho_crit": RHO_CRIT, "v_free": V_FREE, "runs": rows}, indent=1, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    cols = ["name", "n_samples", "rho_mean", "rho_p95", "frac_rho_gt_crit", "frac_rho_gt_20",
            "abs_drho_p95", "speed_mean", "step_step_drop_kph", "step_tau_hat_sec",
            "act_vsl_ok", "act_ramp_ok", "act_vsl_commanded_uniques", "act_ramp_rate_vph_uniques"]
    cols = [c for c in cols if c in df.columns]
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
