"""프리웨이-도시부 램프 결합이 모형에 실제로 연결돼 있는지 본다.

2026-08-17 에 이걸로 잡은 것: 생산 config(pedovrx)의 `off_ramp_to_movement` 와
`on_ramp_to_movement` 가 **둘 다 빈 dict** 다. 그래서

  - `_drain_offramp_storage`(vendor/.../urban_queue_model.py:514)가 순회할 movement 가 없어
    off-ramp 저류가 한 대도 못 빠진다. 용량 60 veh 를 향해 단조로 찬다:
        OR_D_W_storage  18.28 -> 35.09 -> 50.98   (스텝 1/2/3)
    네 개 합 66.4 -> 131.2 -> 190.7 veh, 전체 모형 질량의 2.9% -> 6.7%.
  - 도시부->온램프 연결이 없어 ramp metering 이 모형 안에서 조일 대상을 잃는다
    (2026-08-04 에 core15 selector 에서 같은 증상이 기록돼 있다:
     scripts/generate_real_world_distributed_players.py:1393-1397).

원인은 selector 이름이다. 생산 config 의 `urban_signal_selector` 가 "core15" 이고
생성기의 `--sc1-coupling auto` 규칙이 **core15 만 결합 off** 다. SC1 이 통제 집합에 들어
있어도 이름 때문에 꺼진다.

VISSIM 을 띄우지 않는다. 앵커 하나에서 rollout 만 굴린다.
"""

import json
import sys
from pathlib import Path

REPO = Path(r"C:\Users\TRLAB\Desktop\찐찐막\VISSIM")
sys.path.insert(0, str(REPO / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from audit_rollout_prediction_accuracy import _load_adapter, rollout_from_anchor  # noqa: E402

ad = _load_adapter()
P = {
    "tuning": REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json",
    "calibration": REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json",
    "detector_mapping": REPO / "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_pedovrx_20260814.json",
}
run = REPO / "evaluation/runs/n5_parent_20260814"
aj = json.loads((run / "decisions_n5parent_20260814_training_d100_s13" / "anchor_001500.json").read_text(encoding="utf-8"))
steps, _iv, cfg = rollout_from_anchor(ad, aj, 3, P)
net = cfg.network

print("off_ramps:", list(getattr(net, "off_ramps", []) or []))
o2m = getattr(net, "off_ramp_to_movement", {}) or {}
specs = net.urban_movements or {}
print()
for r in (getattr(net, "off_ramps", []) or []):
    sl = (getattr(net, "off_ramp_storage_link", {}) or {}).get(r, "")
    movs = list(o2m.get(r, []) or [])
    in_specs = [m for m in movs if m in specs]
    print(f"{r}  -> storage {sl!r}")
    print(f"   off_ramp_to_movement: {len(movs)}개 {movs}")
    print(f"   그중 urban_movements 에 있는 것: {len(in_specs)}개")
    for m in in_specs:
        s = specs[m]
        print(f"      {m}  beta={s.get('beta')}  receiving_link={s.get('receiving_link')!r}"
              f"  origin={s.get('origin')!r}")
    if movs and not in_specs:
        print("   *** 배수 불가: movement 이름이 urban_movements 에 없다 ***")
    if not movs:
        print("   *** 배수 불가: off_ramp_to_movement 가 비었다 ***")
    print()

# split ratio 와 유입
print("off_ramp_split_ratio:", dict(getattr(net, "off_ramp_split_ratio", {}) or {}))
occ0 = getattr(steps[0]["state"], "urban_link_storage", {}) or {}
for r in (getattr(net, "off_ramps", []) or []):
    sl = (getattr(net, "off_ramp_storage_link", {}) or {}).get(r, "")
    cap = float(net.urban_link_storage_veh.get(sl, 0.0))
    print(f"  {sl:18s} cap {cap:7.1f}  스텝별 점유:", end=" ")
    for stp in steps:
        st_ = getattr(stp["state"], "urban_link_storage", {}) or {}
        print(f"{max(0.0, cap - float(st_.get(sl, cap))):7.2f}", end="")
    print()
