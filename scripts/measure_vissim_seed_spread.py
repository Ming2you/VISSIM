"""VISSIM 자신의 시드 간 실현 분산을 잰다 — 결정론 모형이 넘을 수 없는 바닥.

새 런이 필요 없다. 부모런이 수요 3 x 시드 3 이라 같은 수요의 세 시드가 곧 같은 조건의
독립 실현 3개다.

논리: 결정론 모형이 **앙상블 평균을 완벽히** 맞춘다 해도, 검증은 **한 시드**를 상대로
한다. 그러면 그 모형의 MdAPE 는 "한 시드가 앙상블 평균에서 벗어난 상대편차"의 중앙값과
같아진다. 그 값이 파라미터로 없앨 수 없는 바닥이다.

주의: 시드가 t=0 부터 갈라지므로 이건 "같은 앵커에서 갈라지는 미래"가 아니라 "완전히 다른
실현"의 분산이다. 따라서 진짜 바닥의 **상한**에 가깝다 — 앵커를 공유하면 분산이 더 작다.
그래도 자릿수 판단에는 충분하고 비용이 0이다.
"""
import statistics as st
import sys
from pathlib import Path

REPO = Path(r"C:\Users\TRLAB\Desktop\찐찐막\VISSIM")
sys.path.insert(0, str(REPO / "scripts"))
# TextIOWrapper 로 감싸면 안 된다 - 아래 모듈들이 import 시 stdout.reconfigure 를 부르고
# 그때 원래 버퍼가 닫혀 있어 터진다.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from audit_rollout_prediction_accuracy import _load_adapter  # noqa: E402
from audit_rollout_conserved_unit import (  # noqa: E402
    MIN_OBS_VEH,
    conserved_from_parts,
    observed_link_metrics,
)

RUN = REPO / "evaluation/runs/n5_parent_20260814"
PATHS = {
    "tuning": REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json",
    "calibration": REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json",
    "detector_mapping": REPO / "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_pedovrx_20260814.json",
}

# 수요별로 시드 셋. 부모런 이름 규칙이 셀 종류(training/holdout/congested)를 담고 있다.
CELLS = {
    0.75: ["n5parent_20260814_training_d075_s13", "n5parent_20260814_training_d075_s29", "n5parent_20260814_holdout_d075_s47"],
    1.00: ["n5parent_20260814_training_d100_s13", "n5parent_20260814_training_d100_s29", "n5parent_20260814_holdout_d100_s47"],
    1.25: ["n5parent_20260814_congested_d125_s13", "n5parent_20260814_congested_d125_s29", "n5parent_20260814_holdout_d125_s47"],
}
# 검증에서 쓴 앵커와 같은 시각대
TIMES = [float(a + 60 * k) for a in (1500, 2100) for k in range(1, 4)]

ad = _load_adapter()
det = ad.load_optional_json(str(PATHS["detector_mapping"]))
cal = ad.load_optional_json(str(PATHS["calibration"]))
tun = ad.load_optional_json(str(PATHS["tuning"]))
ov = tun.get("calibration_override", {})
if isinstance(ov, dict):
    cal = ad.deep_update(dict(cal), ov)

rr = Path(ad.DEFAULT_REPO_ROOT)
ad.repo_imports(rr)
cfg = ad.build_config(rr, 60.0, 3600.0, "local_observation", cal, tun, local_observation=True, flagship=False)


def conserved_by_time(cell: str) -> dict[float, dict[str, float]]:
    """셀 하나에서 시각별 보존단위(저류 점유 + 이동류 큐)를 뽑는다."""
    raw_by_time = observed_link_metrics(RUN / f"bottleneck_links_{cell}.csv", set(TIMES))
    out: dict[float, dict[str, float]] = {}
    for sec, raw in raw_by_time.items():
        synth = {"local_observation": raw, "sim_sec": sec}
        summary = ad.build_local_observation_summary(synth, cfg, det, cal)
        out[sec] = conserved_from_parts(
            cfg,
            summary.get("urban_link_storage_occupancy") or {},
            summary.get("urban_movement_queue") or {},
        )
    return out


print("VISSIM 시드 간 실현 분산 — 결정론 모형의 바닥")
print(f"보존단위 = 저류 점유 + 이동류 큐,  최소 관측 {MIN_OBS_VEH} veh 이상만,  시각 {len(TIMES)}개\n")

rows = []
for demand, cells in CELLS.items():
    per_cell = {}
    for cell in cells:
        if not (RUN / f"bottleneck_links_{cell}.csv").is_file():
            print(f"  (없음) {cell}")
            continue
        per_cell[cell] = conserved_by_time(cell)
    if len(per_cell) < 2:
        continue

    rel_dev = []       # 한 시드가 시드평균에서 벗어난 상대편차 (%)
    abs_dev = []       # 같은 것의 절대 대수 (veh)
    cv = []            # 시드 간 변동계수 (%)
    for sec in TIMES:
        keys = set()
        for cell in per_cell:
            keys |= set(per_cell[cell].get(sec, {}))
        for storage in keys:
            vals = [per_cell[c].get(sec, {}).get(storage) for c in per_cell]
            vals = [v for v in vals if v is not None]
            if len(vals) < 2:
                continue
            m = st.mean(vals)
            if m < MIN_OBS_VEH:
                continue
            for v in vals:
                rel_dev.append(100.0 * abs(v - m) / m)
                abs_dev.append(abs(v - m))
            if len(vals) >= 2:
                cv.append(100.0 * st.stdev(vals) / m)

    if not rel_dev:
        continue
    rel_dev.sort()
    abs_dev.sort()
    cv.sort()
    rows.append((demand, len(per_cell), len(rel_dev),
                 st.median(rel_dev), rel_dev[int(0.9 * len(rel_dev))],
                 st.median(abs_dev), st.median(cv)))

print(f"{'수요':>6s} {'시드':>4s} {'표본':>7s} {'중앙 상대편차':>13s} {'p90':>7s} {'중앙 절대':>10s} {'중앙 CV':>8s}")
print("-" * 62)
for d, ns, n, med, p90, mabs, mcv in rows:
    print(f"{d:6.2f} {ns:4d} {n:7d} {med:12.1f}% {p90:6.1f}% {mabs:8.2f}veh {mcv:7.1f}%")

if rows:
    overall = st.median([r[3] for r in rows])
    print(f"\n세 수요 중앙값: {overall:.1f}%")
    print("\n해석: 앙상블 평균을 완벽히 맞추는 결정론 모형이라도 한 시드를 상대로는")
    print(f"      약 {overall:.0f}% 의 MdAPE 를 낸다. 우리 스텝1 오차 41.6% 중 그만큼은")
    print("      파라미터로 없앨 수 없는 몫이다.")
    print("      단 시드가 t=0 부터 갈라지므로 이 값은 진짜 바닥의 상한에 가깝다.")
