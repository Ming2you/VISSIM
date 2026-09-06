# -*- coding: utf-8 -*-
"""게이트 0 — VISSIM 없이: 관측 저류가 지평(450 s) 안에서 movement 큐가 되는가.

실런 상태 JSON 을 싣고, movement 큐를 0 으로 비우고, 수요를 0 으로 둔 뒤 90 substep
(30 substep x T_u 5 s = 150 s, horizon 3 = 450 s)을 굴린다.

  시더 OFF  -> movement_queue 가 정확히 0.00 이어야 한다 (현행 결함의 재현)
  시더 ON   -> > 0 이어야 한다 (2단계가 실제로 배달한다는 증거)

여기서 ON 이 0 이면 VISSIM 런을 쏘지 마라.
"""
import io,sys,json,importlib.util,pathlib,os
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
R = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sp = importlib.util.spec_from_file_location("qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
from src.models.state import TrafficState
from src.models.demand import DemandStep
from src.models.urban_queue_model import urban_substep, _urban_step_index
from src.models.state import ControlAction

TUN = "evaluation/configs/canon_default_20260905.json"
CAL = "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"
DET = "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_core17legs4f_20260903_blindfix20260905b.json"
STATE = "evaluation/runs/arm_qsplit_x18_20260904/decisions_arm_qsplit_x18_20260904/state_002700.json"

def run(seed_on: bool):
    tun = qb.load_optional_json(str(R / TUN))
    # 스위치 주입: 2단계만 켠다(1단계는 러너가 queue_bins 를 실어야 의미가 있다)
    tun = json.loads(json.dumps(tun))
    tun.setdefault("urban", {}).setdefault("arrival", {})["seed_from_residual"] = bool(seed_on)
    tun["urban"].setdefault("tau", {})["storage_lanes_fzp"] = bool(seed_on)   # 4단계 동시 확인
    cal = qb.load_optional_json(str(R / CAL))
    cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link",
                          cal, tun, local_observation=True, flagship=True)
    det = qb.load_optional_json(str(R / DET))
    sj = json.load(io.open(R / STATE, encoding="utf-8"))
    state = qb.traffic_state_from_vissim(dict(sj), cfg, TrafficState, det, cal)
    summary = qb.build_local_observation_summary(sj, cfg, det, cal)
    occ = sum(float(v) for v in (summary.get("urban_link_storage_occupancy") or {}).values())
    # traffic_state_from_vissim 이 이미 시딩했다 - 여기서 또 부르면 이중계상이다.
    stats = dict((summary.get('urban_arrival_seed') or {}))
    for k in ('links','moving_veh','stopped_veh','dropped_veh'): stats.setdefault(k, 0.0)
    buf = getattr(state, "urban_arrival_buffer", {}) or {}
    entries = sum(len(v) for v in buf.values() if isinstance(v, dict))
    booked = sum(sum(v.values()) for v in buf.values() if isinstance(v, dict))
    # movement 큐 비우고 수요 0 으로 90 substep
    for k in list(state.urban_movement_queue): state.urban_movement_queue[k] = 0.0
    ctrl = ControlAction.fixed(cfg)
    zero = DemandStep(freeway_mainline={l: 0.0 for l in cfg.network.freeway_links},
                      urban_boundary={}, ramp_arrival={r: 0.0 for r in cfg.network.ramps})
    trace = []
    base = _urban_step_index(state, cfg)   # 롤아웃은 **절대** substep 인덱스를 쓴다
    for i in range(90):
        urban_substep(state, ctrl, zero, cfg, urban_step_index=base + i)
        if i in (0, 1, 5, 15, 30, 60, 89):
            trace.append((i + 1, sum(state.urban_movement_queue.values())))
    return occ, stats, entries, booked, trace

print("상태 JSON: %s\n"%STATE)
for on in (False, True):
    occ, st, entries, booked, tr = run(on)
    print("=== 시더 %s ==="%("ON " if on else "OFF"))
    print("   저류 점유 %.1f veh · 예약 항목 %d · 예약 대수 %.1f"%(occ, entries, booked))
    print("   시더 통계: 링크 %.0f · 이동 %.1f · 정지 %.1f · 버림 %.1f"%(
        st["links"], st["moving_veh"], st["stopped_veh"], st["dropped_veh"]))
    print("   movement_queue: " + "  ".join("s%d=%.2f"%(a, b) for a, b in tr))
    print()
