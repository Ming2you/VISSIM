# -*- coding: utf-8 -*-
"""스필백 관측(urban.ramp.spillback_obs) + 미터 스필백 가드(actuation.real_world_ramp_metering.spillback_guard) 패치.
사용: python apply_spill_patch.py <adapter_path>   (스크래치 사본에 먼저, 검증 뒤 정본에)"""
import io, sys, re

P = sys.argv[1]
s = io.open(P, encoding="utf-8").read()

# (1) 설치기
old = "def _plant_gate_peeloff_into(cfg, tuning) -> None:"
new = '''def _plant_ramp_spillback_into(cfg, tuning) -> None:
    """tuning `urban.ramp.spillback_obs` 를 cfg 로 나른다 (2026-09-07).

    켜면 build_local_observation_summary 가 검지 매핑 `ramp_spillback_links`(램프 커넥터별 전용 상류 링크)의
    **정지 차량**(queue_lanes, conn_pos_m 이하)을 램프 저수지 큐에 더한다. 커넥터 위 차량만 세던 저수지(상한 153)가
    링크 32/69 위 1 km 역류(진짜 큐 262 vs 모형 140, fzp 진단 2026-09-07)를 못 보던 실명 수정. 없으면 비트 동일."""
    section = _mapping(_mapping(_mapping(tuning).get("urban")).get("ramp"))
    setattr(cfg.network, "ramp_spillback_obs", bool(_is_enabled_value(section.get("spillback_obs", False))))


def _plant_gate_peeloff_into(cfg, tuning) -> None:'''
assert s.count(old) == 1, ("anchor1", s.count(old))
s = s.replace(old, new)

calls = [m.start() for m in re.finditer(r'^\s*_plant_ramp_observation_into\(cfg, tuning\)\s*$', s, re.M)]
assert len(calls) == 1, ("calls", len(calls))
line_end = s.index("\n", calls[0])
indent = re.match(r'\s*', s[calls[0]:]).group(0)
s = s[:line_end + 1] + indent + "_plant_ramp_spillback_into(cfg, tuning)\n" + s[line_end + 1:]

# (2) 관측 요약
old2 = '''    ramp_queue = {ramp: 0.0 for ramp in cfg.network.ramps}
    for link, ramps in detector_mapping.get("ramp_link_to_queues", {}).items():
        count = link_counts.get(str(link), 0.0)
        if count <= 0.0:
            continue
        for ramp_key, weight in _ramp_queue_shares(ramps):
            if ramp_key in ramp_queue:
                ramp_queue[ramp_key] += count * weight
'''
new2 = old2 + '''
    # 2026-09-07 램프 스필백 관측: 커넥터 상류 전용 검지 링크(ramp_spillback_links)의 정지 차량을 저수지 큐에 더한다.
    #   램프행은 lnChgDist 1000 으로 커넥터 1 km 상류부터 L1 에 붙어 서므로 정지·큐 차로(queue_lanes)·conn_pos_m 이하로 판정.
    #   링크 전체 재차를 넣지 않는다(09-03 rampconn 과대 사고). 스위치 urban.ramp.spillback_obs (없으면 비트 동일).
    ramp_spillback: dict[str, float] = {}
    if bool(getattr(cfg.network, "ramp_spillback_obs", False)):
        _spill_spec = _mapping(detector_mapping.get("ramp_spillback_links"))
        _recs = _mapping(state_json.get("vehicle_records")).get("records") or []
        _by_link: dict[str, list] = {}
        for _r in _recs:
            if isinstance(_r, Mapping):
                _by_link.setdefault(str(_r.get("link_no")), []).append(_r)
        for _ramp_key, _entries in _spill_spec.items():
            if _ramp_key not in ramp_queue or not isinstance(_entries, list):
                continue
            _spill = 0.0
            for _e in _entries:
                _e = _mapping(_e)
                _link = str(_e.get("link", ""))
                _lanes = {int(x) for x in (_e.get("queue_lanes") or [])}
                _pos_max = _as_float(_e.get("conn_pos_m"), -1.0)
                if _recs:
                    _rows = _by_link.get(_link) or []
                    _spill += float(sum(1 for _r in _rows if bool(_r.get("stopped"))
                                        and (not _lanes or int(_as_float(_r.get("lane_no"), 0)) in _lanes)
                                        and (_pos_max < 0.0 or _as_float(_r.get("position_m"), 0.0) <= _pos_max)))
                else:
                    _st = float(link_stopped_counts.get(_link, 0.0))
                    _nl = max(1, int(_as_float(_e.get("lanes"), 1)))
                    _spill += _st * ((len(_lanes) / _nl) if _lanes else 1.0)
            ramp_spillback[_ramp_key] = float(_spill)
            ramp_queue[_ramp_key] += float(_spill)
'''
assert s.count(old2) == 1, ("anchor2", s.count(old2))
s = s.replace(old2, new2)

old3 = '''        "ramp_queue": ramp_queue,
        "boundary_queue": boundary_queue,
        "projection_diagnostics": projection_diagnostics,'''
new3 = '''        "ramp_queue": ramp_queue,
        "ramp_spillback": ramp_spillback,
        "boundary_queue": boundary_queue,
        "projection_diagnostics": projection_diagnostics,'''
assert s.count(old3) == 1, ("anchor3", s.count(old3))
s = s.replace(old3, new3)

# (3) 가드
old4 = "def real_world_ramp_meter_write_back(control, cfg, actuation: Mapping[str, Any], mapping: Mapping[str, Any], metadata=None,"
new4 = '''def apply_ramp_spillback_guard(control, cfg, state, actuation: Mapping[str, Any], metadata=None) -> dict[str, float]:
    """램프 스필백 제약 (2026-09-07): 검지 링크 위 정지 큐(ramp_spillback)가 문턱을 넘으면 그 램프의 미터 rate 를 floor 로 강제
    개방한다 — 커넥터 + 전용 상류 검지 링크 이상으로 스필백을 쌓아두지 않는다(사용자 요구). 되쓰기(write-back) **앞**에 불러
    강제값이 green 배정으로 실현되게 한다. `actuation.real_world_ramp_metering.spillback_guard` 가 없으면 no-op = 비트 동일."""
    settings = _mapping(_mapping(actuation.get("real_world_ramp_metering")).get("spillback_guard"))
    if not _is_enabled_value(settings.get("enabled", False)):
        return {}
    thr = max(0.0, _as_float(settings.get("spill_threshold_veh"), 8.0))
    floor = max(0.0, _as_float(settings.get("floor_vph"), 1800.0))
    summ = _mapping(getattr(state, "local_observation_summary", None) or {})
    spill = _mapping(summ.get("ramp_spillback"))
    out: dict[str, float] = {}
    for ramp, sv in spill.items():
        sv = _as_float(sv, 0.0)
        cur = _as_float(control.ramp_metering.get(ramp), 0.0)
        forced = bool(sv > thr and cur < floor)
        if forced:
            control.ramp_metering[ramp] = float(floor)
        out[ramp] = 1.0 if forced else 0.0
        if isinstance(metadata, dict):
            metadata["rw_spill_%s_veh" % ramp] = float(sv)
            metadata["rw_spill_guard_%s" % ramp] = 1.0 if forced else 0.0
            if forced:
                metadata["rw_spill_guard_%s_from_vph" % ramp] = float(cur)
    if isinstance(metadata, dict):
        metadata["rw_spill_guard_threshold_veh"] = thr
        metadata["rw_spill_guard_forced_count"] = float(sum(out.values()))
    return out


def real_world_ramp_meter_write_back(control, cfg, actuation: Mapping[str, Any], mapping: Mapping[str, Any], metadata=None,'''
assert s.count(old4) == 1, ("anchor4", s.count(old4))
s = s.replace(old4, new4)

old5 = "    real_world_ramp_meter_write_back(control, cfg, actuation, mapping, metadata, state_json=state_json, previous=previous)"
new5 = ("    apply_ramp_spillback_guard(control, cfg, state, actuation, metadata)\n"
        "    real_world_ramp_meter_write_back(control, cfg, actuation, mapping, metadata, state_json=state_json, previous=previous)")
assert s.count(old5) == 1, ("anchor5", s.count(old5))
s = s.replace(old5, new5)

io.open(P, "w", encoding="utf-8", newline="").write(s)
print("spill patch applied to", P)
