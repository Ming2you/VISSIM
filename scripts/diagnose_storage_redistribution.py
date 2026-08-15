#!/usr/bin/env python3
"""저류 오차가 투영 탓인지 동역학 탓인지 가른다 (양쪽에 **같은 투영**을 쓴다).

v1 의 잘못: VISSIM 링크 대수를 소유권 지도로 통에 모아 "관측 저류" 로 삼았다. 그런데
모델의 저류 점유는 어댑터가 전혀 다른 규칙으로 만든다.

    storage_count = count * storage_fraction   (나머지는 movement queue 로)
    한 링크가 _storage_links_for_observed_origin 으로 여러 통에 균등 분배
    assigned = min(share, capacity - current)  용량에서 잘린다

audit_rollout_spatial_accuracy.py 는 소유권 지도로 관측을 모으는데 그것은 모델의 규칙이
아니다. 그래서 그 도구의 숫자에는 투영 불일치가 섞여 있다.

여기서는 관측 시각의 링크 대수를 어댑터의 `build_local_observation_summary` 에 그대로
통과시켜 "관측 저류 점유" 를 만든다. 모델 쪽과 같은 함수·같은 분율·같은 용량 클리핑을
거치므로 남는 차이는 **예측 오차뿐**이다.

## 실측 결과 (2026-08-15, 부모런 3셀 x anchor 3 x 3스텝)

    스텝 0(초기상태)   0.0%    <- 투영은 정확하다
    스텝 1(60초)      54.8%
    스텝 2(120초)     54.4%
    스텝 3(180초)     50.6%

**한 스텝 만에 생기고 그 뒤로는 거의 안 변한다.** 점진적 이탈이 아니라 즉각적인
재배치다. 총량은 보존된다(부호 있는 중앙값 +0.0%) - 질량이 사라지는 게 아니라
엉뚱한 통으로 간다. SC15_NE_out / SC15_SW_out / SC108_to_SC7 은 정확히 -100% 로,
모델이 60초 만에 통째로 비운다.
"""
import csv, json, io, sys, statistics as st
from collections import defaultdict
from pathlib import Path

REPO = Path(r"C:\Users\TRLAB\Desktop\찐찐막\VISSIM")
sys.path.insert(0, str(REPO / "scripts"))
from audit_rollout_prediction_accuracy import _load_adapter, rollout_from_anchor  # noqa: E402
from audit_rollout_spatial_accuracy import model_storage_occupancy  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

run_dir = REPO / "evaluation" / "runs" / "n5_parent_20260814"
TUNING = REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json"
CALIB = REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"
DETMAP = REPO / "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_pedovrx_20260814.json"
paths = {"tuning": TUNING, "calibration": CALIB, "detector_mapping": DETMAP}

ad = _load_adapter()
detector_mapping = ad.load_optional_json(str(DETMAP))
calibration = ad.load_optional_json(str(CALIB))
tuning = ad.load_optional_json(str(TUNING))
ov = tuning.get("calibration_override", {})
if isinstance(ov, dict):
    calibration = ad.deep_update(dict(calibration), ov)


def observed_link_counts(path: Path, want: set[float]):
    """sim_sec -> {link: count} (그리고 속도/정지수도 같이)"""
    out = defaultdict(lambda: {"link_counts": {}, "link_speeds_kph": {}, "link_stopped_counts": {}})
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                sec = float(row["sim_sec"])
            except (KeyError, TypeError, ValueError):
                continue
            if sec not in want:
                continue
            link = str(row["link"])
            out[sec]["link_counts"][link] = float(row["count"])
            out[sec]["link_speeds_kph"][link] = float(row["mean_speed_kph"])
            out[sec]["link_stopped_counts"][link] = float(row["stopped_count"])
    return out


CELLS = [
    "n5parent_20260814_training_d075_s13",
    "n5parent_20260814_training_d100_s13",
    "n5parent_20260814_congested_d125_s13",
]
ANCHORS = [900, 1500, 2100]
H = 3

by_step = defaultdict(list)
signed = []
worst = defaultdict(list)
n_units = set()

for cell in CELLS:
    want = {float(a + 60 * k) for a in ANCHORS for k in range(1, H + 1)}
    want |= {float(a) for a in ANCHORS}
    obs_raw = observed_link_counts(run_dir / f"bottleneck_links_{cell}.csv", want)
    for anchor in ANCHORS:
        ap = run_dir / f"decisions_{cell}" / f"anchor_{anchor:06d}.json"
        if not ap.is_file():
            continue
        aj = json.loads(ap.read_text(encoding="utf-8"))
        steps, _iv, cfg = rollout_from_anchor(ad, aj, H, paths)
        # 스텝 0 = 초기 상태 자체. anchor 시각의 관측과 비교하면 투영이 맞는지 바로 보인다.
        init_state = ad.traffic_state_from_vissim(
            aj, cfg, type(steps[0]["state"]), detector_mapping, calibration
        )
        steps = [{"step": 0, "sim_sec": float(anchor), "state": init_state, "summary": {}}] + list(steps)
        for stp in steps:
            sec = float(stp["sim_sec"])
            raw = obs_raw.get(sec)
            if not raw:
                continue
            # 관측 링크 대수를 **어댑터의 같은 함수**에 통과시킨다.
            synthetic = dict(aj)
            synthetic["local_observation"] = {
                **(aj.get("local_observation") or {}),
                **raw,
            }
            osum = ad.build_local_observation_summary(synthetic, cfg, detector_mapping, calibration)
            oocc = osum.get("urban_link_storage_occupancy") or {}
            mocc = model_storage_occupancy(stp["state"], cfg)
            for name, mval in mocc.items():
                oval = oocc.get(name)
                if oval is None or oval < 5.0:
                    continue
                n_units.add(name)
                pe = 100.0 * (mval - oval) / oval
                by_step[stp["step"]].append(abs(pe))
                signed.append(pe)
                worst[name].append(pe)

print(f"비교 단위 {len(n_units)}통, 표본 {len(signed)}")
print("\n== 스텝별 절대 APE 중앙값 ==")
for k in sorted(by_step):
    v = by_step[k]
    print(f"  스텝 {k}  n={len(v):5d}  중앙값 {st.median(v):6.1f}%")
if signed:
    print(f"\n부호 있는 중앙값 {st.median(signed):+.1f}%   과소예측 {100*sum(1 for x in signed if x<0)/len(signed):.0f}%")
rank = sorted(((k, st.median(v), len(v)) for k, v in worst.items() if len(v) >= 5), key=lambda x: -abs(x[1]))
print("\n== 최악 통 8개 ==")
for k, m, n in rank[:8]:
    print(f"  {k:26s} {m:+8.1f}%  n={n:3d}")
