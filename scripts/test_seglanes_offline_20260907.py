# -*- coding: utf-8 -*-
"""세그먼트별 차로 패치 오프라인 검증: install_freeway_segment_lanes 로 cfg 에 차로 배열을 싣고 상태를 다시 조립해
state.freeway_effective_lanes·밀도가 세그먼트별로 바뀌는지 본다(비활성 config 는 비트 동일이어야 한다).
사용: python test_seglanes_offline_20260907.py <adapter_path> <config_name> <mapping_json> <run_name> <T>"""
import sys, io, json, importlib.util
from pathlib import Path


def main():
    R = Path("C:/Users/TRLAB/Desktop/찐찐막/VISSIM")
    sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine")); sys.path.insert(0, str(R / "scripts"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ADAPTER, CFGN, MAPJ, RUN, T = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    sp = importlib.util.spec_from_file_location("qb", R / ADAPTER); qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
                                              str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    print("기본 조립: effective_lanes", {k: v for k, v in st.freeway_effective_lanes.items()})
    print("           density FW_W", [round(x, 1) for x in st.freeway_density.get("FW_W", [])])
    mapping = json.load(io.open(R / MAPJ, encoding="utf-8"))
    out = qb.install_freeway_segment_lanes(cfg, tun, mapping)
    print("설치기 →", out, "· cfg.network.freeway_segment_lanes =", getattr(cfg.network, "freeway_segment_lanes", None))
    st2 = qb.traffic_state_from_vissim(sj, cfg, TrafficState, dm, cal, physical_projection_input=None)
    print("재조립: effective_lanes", {k: v for k, v in st2.freeway_effective_lanes.items()})
    print("        density FW_W", [round(x, 1) for x in st2.freeway_density.get("FW_W", [])])
    print("        density FW_E", [round(x, 1) for x in st2.freeway_density.get("FW_E", [])])
    cnt1 = st.freeway_vehicle_count_by_link(cfg.network); cnt2 = st2.freeway_vehicle_count_by_link(cfg.network)
    print("        veh count FW_W 기본 %s → 재조립 %s (합 %.0f → %.0f, 차량 보존이어야 함)" % (
        [round(x) for x in cnt1.get("FW_W", [])], [round(x) for x in cnt2.get("FW_W", [])], sum(cnt1.get("FW_W", [])), sum(cnt2.get("FW_W", []))))


if __name__ == "__main__":
    main()
