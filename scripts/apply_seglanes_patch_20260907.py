# -*- coding: utf-8 -*-
"""세그먼트별 본선 차로(및 세그먼트 파라미터 훅) 패치 (2026-09-07).

config `freeway.segment_lanes: "mapping"` 이면 control_mapping 의 freeway_model_links[*].segment_lanes 를 읽어
cfg.network.freeway_segment_lanes = {model_link: [lanes...]} 로 싣고, VISSIM 세그먼트 파서가 밀도를 count/(length·lanes_i) 로
다시 계산하며 state.freeway_effective_lanes 에 세그먼트별 차로를 넣는다(METANET·팔로워·리더가 그 배열을 쓴다).
`freeway_model_links[*].segment_params` 가 있으면 cfg.network.freeway_segment_params 로 그대로 싣는다(향후 합류 세그먼트 파라미터용).
키가 없으면 비트 동일. 사용: python apply_seglanes_patch_20260907.py <adapter_path>
(스필백 패치가 먼저 적용돼 있으면 그 설치 줄 뒤에, 아니면 _plant_ramp_observation_into 줄 뒤에 설치 호출을 넣는다.)"""
import io, re, sys

P = sys.argv[1]
s = io.open(P, encoding="utf-8").read()
if "def install_freeway_segment_lanes(" in s:
    print("already patched:", P)
    sys.exit(0)

# (1) 설치기
old = "def _plant_gate_peeloff_into(cfg, tuning) -> None:"
new = '''def install_freeway_segment_lanes(cfg, tuning, mapping) -> dict[str, float]:
    """config `freeway.segment_lanes: "mapping"` → control_mapping 의 세그먼트별 차로를 cfg.network 에 싣는다 (2026-09-07).

    Ver2 망은 본선이 한 모형 링크 안에서 차로가 바뀐다(FW_W: 26 3차로 → 120 4차로, FW_E: 2 4차로 → 119/24 3차로).
    종전엔 모형 링크당 단일값(RW_FW_*_LANES)이라 그 세그먼트들의 밀도·용량이 4/3 배 틀렸다. 값이라 컨트롤러와 함께 피클되어
    가격 워커까지 간다. `segment_params` 가 있으면 함께 실어 둔다(합류 세그먼트별 파라미터 실험용 훅; 지금은 소비처 없음)."""
    section = _mapping(_mapping(tuning).get("freeway"))
    mode = str(section.get("segment_lanes", "") or "").strip().lower()
    if mode != "mapping":
        return {"freeway_segment_lanes_enabled": 0.0}
    links = _mapping(_mapping(mapping).get("freeway_model_links"))
    lanes_by: dict[str, list[float]] = {}
    params_by: dict[str, Any] = {}
    for model, spec in links.items():
        spec = _mapping(spec)
        arr = [float(v) for v in (spec.get("segment_lanes") or []) if _as_float(v, 0.0) > 0.0]
        if not arr:
            segs = [s for s in (_mapping(mapping).get("segments") or []) if isinstance(s, Mapping) and str(s.get("model_link")) == str(model)]
            segs.sort(key=lambda s: int(_as_float(s.get("model_segment_index"), 0)))
            arr = [float(_as_float(s.get("lanes"), 0.0)) for s in segs if _as_float(s.get("lanes"), 0.0) > 0.0]
        if arr:
            lanes_by[str(model)] = arr
        if isinstance(spec.get("segment_params"), Mapping):
            params_by[str(model)] = dict(spec.get("segment_params"))
    setattr(cfg.network, "freeway_segment_lanes", lanes_by)
    setattr(cfg.network, "freeway_segment_params", params_by)
    out = {"freeway_segment_lanes_enabled": 1.0 if lanes_by else 0.0, "freeway_segment_lanes_links": float(len(lanes_by))}
    for model, arr in lanes_by.items():
        out["freeway_segment_lanes_min_%s" % model] = float(min(arr))
        out["freeway_segment_lanes_max_%s" % model] = float(max(arr))
    return out


def _plant_gate_peeloff_into(cfg, tuning) -> None:'''
assert s.count(old) == 1, ("anchor1", s.count(old))
s = s.replace(old, new)

# 설치 호출: main() 의 되접기 설치 줄 앞(mapping 은 11357 에서 로드됨, 상태 조립 traffic_state_from_vissim 보다 앞)
old_call = "    runtime_patch_metadata.update(install_leg_ramp_split_fold(cfg, tuning))\n"
assert s.count(old_call) == 1, ("call anchor", s.count(old_call))
s = s.replace(old_call, "    runtime_patch_metadata.update(install_freeway_segment_lanes(cfg, tuning, mapping))\n" + old_call)

# (2) 파서: 세그먼트별 차로로 밀도 재계산
old2 = '''            lanes = max(1.0, float(row.get("lanes", cfg.network.freeway_lanes)))
            speed = speed_sum / count if count > 1.0e-9 else float(cfg.network.v_free)
            density = count / (length_km * lanes)'''
new2 = '''            lanes = max(1.0, float(row.get("lanes", cfg.network.freeway_lanes)))
            # 2026-09-07 세그먼트별 차로(freeway.segment_lanes=mapping): VBS 의 모형 링크 단일값 대신 매핑의 세그먼트 차로로
            #   밀도를 count/(length·lanes_i) 로 다시 잰다. state.freeway_effective_lanes 에도 그대로 실린다.
            _seg_lanes = _mapping(getattr(cfg.network, "freeway_segment_lanes", None) or {}).get(str(link))
            if isinstance(_seg_lanes, list) and i < len(_seg_lanes) and _as_float(_seg_lanes[i], 0.0) > 0.0:
                lanes = max(1.0, float(_seg_lanes[i]))
            speed = speed_sum / count if count > 1.0e-9 else float(cfg.network.v_free)
            density = count / (length_km * lanes)'''
assert s.count(old2) == 1, ("anchor2", s.count(old2))
s = s.replace(old2, new2)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("seglanes patch applied to", P)
