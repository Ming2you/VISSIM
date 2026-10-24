def install_measured_movement_capacity(cfg, tuning, state_json, previous_path) -> dict[str, float]:
    """**직전 구간 실측 방류율**로 movement 용량을 갱신한다. `urban.capacity.measured` 없으면 no-op.

    왜. 지금 용량은 가정값이다 — 플랜트/GNE 가 `차로수 x 330`, 정련 채점기가
    `len(movements) x 1400`. 실측(무제어 .knr)은 정지선 차로군이 1,100~4,400 veh/h 라
    전자는 3~5배 과소, 후자는 신호 합이 4배 과대다. 리더가 녹색을 나눌 때 쓰는 게
    movement 간 **상대** 용량이라 이 왜곡이 그대로 배분 왜곡이 된다.

    무엇을 재나. 러너가 5초 스캔에서 차량별 (No, Link) 를 이미 읽으므로 연속 스캔을
    비교해 **정지선 링크를 떠난 대수**를 세고 `link_departures_window` 로 실어 보낸다
    (`RW_QUEUE_WINDOW=1`). 그 링크 차로군의 직전 구간 녹색초로 나누면 방류율이다.

        cap_obs[link] = departures[link] / green_sec[link] x 3600

    수요제약을 어떻게 거르나. 한산한 구간의 `departures/green` 은 용량이 아니라 수요다.
    오프라인 분위수로 거르려 했으나 실패했다(중앙값 기준 차로환산 0.52 — 1차로 미만).
    대신 **감쇠 러닝맥스**를 쓴다:

        cap_est = max(cap_obs, decay x cap_est_prev)

    증거가 나오면 즉시 올라가고 없으면 천천히 잊는다. 포화점이 안정 고정점이라
    아래에서 수렴한다 — 녹색이 줄면 큐가 덜 비어 `departures/green` 이 올라간다.
    어댑터는 결정마다 새 프로세스라 직전 추정치를 **직전 action JSON 진단**으로 나른다.

    씨앗. 첫 결정에는 직전값이 없다. 무제어 런에서 유도한
    `movement_saturation_measured_20260822.json` 의 차로군 값을 쓴다.

    차로군 -> movement 배분. 한 접근로의 직진·좌·우는 **같은 차로를 나눠 쓴다**.
    차로군 총량을 movement 마다 복제하면 그 접근로가 용량의 3배를 방류한다.
    모델 자신의 회전 분율 `beta` 로 나눈다 — 총량이 보존된다.
    """
    section = _mapping(_mapping(tuning.get("urban")).get("capacity"))
    if not _is_enabled_value(section.get("measured")):
        return {"measured_capacity_enabled": 0.0}
    decay = _as_float(section.get("decay"), 0.98)
    local = _mapping(state_json.get("local_observation"))
    departures = {str(k): _as_float(v, 0.0) for k, v in _mapping(local.get("link_departures_window")).items()}

    prev_est: dict[str, float] = {}
    try:
        prev_doc = json.loads(Path(previous_path).read_text(encoding="utf-8"))
        for holder in ("metadata", "diagnostics"):
            for key, value in _mapping(prev_doc.get(holder)).items():
                if key.startswith("sat_est_"):
                    prev_est[key[len("sat_est_"):]] = _as_float(value, 0.0)
    except (OSError, ValueError):
        pass

    groups: list[Mapping[str, Any]] = []
    if MEASURED_SATURATION_EVIDENCE_JSON.is_file():
        doc = json.loads(MEASURED_SATURATION_EVIDENCE_JSON.read_text(encoding="utf-8"))
        groups = [g for g in (doc.get("lane_groups") or []) if isinstance(g, Mapping)]
    # 씨앗. 기본은 **플랜트가 지금 믿는 값**(차로수 x equivalent_uniform, 통상 330)이다.
    #
    # 왜 기하값(차로수 x 1800)을 안 쓰나. `max(실측, 씨앗)` 에서 기하 씨앗은 실측보다
    # 3~8배 커서 사실상 늘 이긴다(실측: 60개 중 2개만 채택). 그러면 "직전 실측을 쓴다"가
    # 아니라 "1800/차로를 가정한다"가 되고, 이 망이 실제로 그 근처도 못 가므로 낙관적이다.
    # 플랜트 현재값에서 출발하면 대부분의 접근로에서 실측이 즉시 이겨 데이터가 지배한다
    # (예: SC6 1220021201 실측 7,912 vs 4차로x330 = 1,320).
    #
    # `seed: "geometric"` 으로 옛 거동(차로수 x 1800)을 되살릴 수 있다.
    seed_mode = str(section.get("seed", "plant")).strip().lower()
    base_caps = dict(getattr(cfg.network, "movement_capacity_by_movement_veh_h", {}) or {})
    seed: dict[str, float] = {}
    # 2026-09-06 차로군(정지선 링크, 현시) 씨앗. observed 모드와 lane_group 배분이 쓴다.
    seed_lg: dict[tuple[str, str], float] = {}
    _nema = {"NBT": "p1", "SBT": "p1", "NBL": "p2", "SBL": "p2", "EBT": "p3", "WBT": "p3", "EBL": "p4", "WBL": "p4"}
    if seed_mode == "observed":
        clip_lo, clip_hi = 0.2, 1.0
        _clip = section.get("observed_clip")
        if isinstance(_clip, (list, tuple)) and len(_clip) == 2:
            clip_lo, clip_hi = float(_clip[0]), float(_clip[1])
        missing_frac = clamp(_as_float(section.get("seed_missing_frac"), 0.5), 0.0, 1.0)
        # 큐가 서는 접근로만 관측 최대를 용량으로 믿는다. 무제어(h0)에서 큐가 안 서던 접근로의 관측 최대는
        # 수요이지 용량이 아니라(과소 → 유령 큐) 물리값(기하)을 쓴다. 분류표 = outputs/link_queue_class_*.json.
        queued: set[str] | None = None
        _qpath = str(section.get("queued_links_json", "") or "")
        if _qpath:
            try:
                _qdoc = json.loads((WORKSPACE_ROOT / _qpath).read_text(encoding="utf-8"))
                queued = {str(x) for x in (_qdoc.get("queued_links") or [])}
            except (OSError, ValueError):
                queued = None
        unqueued_frac = clamp(_as_float(section.get("unqueued_geometric_frac"), 1.0), 0.0, 1.0)
        for g in groups:
            link = str(g.get("stopline_link", ""))
            pid = _nema.get(str(g.get("sg_name", "")).upper())
            if not link or pid is None:
                continue
            geo = _as_float(g.get("geometric_veh_h"), 0.0)
            if geo <= 0.0:
                geo = max(1.0, _as_float(g.get("lanes_from_heads"), 1.0)) * 1800.0
            obs_top = _as_float(g.get("observed_top_veh_h"), 0.0)
            if queued is not None and link not in queued:
                val = geo * unqueued_frac
            else:
                val = clamp(obs_top, clip_lo * geo, clip_hi * geo) if obs_top > 0.0 else geo * missing_frac
            seed[link] = seed.get(link, 0.0) + val
            seed_lg[(link, pid)] = seed_lg.get((link, pid), 0.0) + val
    elif seed_mode == "sustained":
        # 2026-09-06 SAT v2: lcd1000 무제어 차량 레코드의 (정지선 링크, 현시) 지속 방류(큐 창 중앙). 상한 = 기하(차로×1800).
        # 큐가 안 서던 링크(queued_links_json)는 기하값. 지속 자료가 없는 차로군은 기하 × seed_missing_frac.
        _spath = str(section.get("sustained_json", "outputs/lane_group_sustained_h0_20260906.json") or "")
        _stat = str(section.get("sustained_stat", "free") or "free").strip().lower()
        _min_w = int(_as_float(section.get("sustained_min_windows"), 6.0))
        missing_frac = clamp(_as_float(section.get("seed_missing_frac"), 0.5), 0.0, 1.0)
        unqueued_frac = clamp(_as_float(section.get("unqueued_geometric_frac"), 1.0), 0.0, 1.0)
        queued = None
        _qpath = str(section.get("queued_links_json", "") or "")
        if _qpath:
            try:
                queued = {str(x) for x in (json.loads((WORKSPACE_ROOT / _qpath).read_text(encoding="utf-8")).get("queued_links") or [])}
            except (OSError, ValueError):
                queued = None
        sus: dict[tuple[str, str], float] = {}
        _SUS_SIGS.clear(); _SUS_LANES.clear()
        _LG_KINDS.clear(); _LG_KINDS.update({str(x) for x in (section.get("lane_group_kinds") or ["internal"])})
        _LTO.clear()
        try:
            _dmp = str(tuning.get("detector_mapping_json", "") or "")
            if _dmp:
                _LTO.update({str(k): list(v) for k, v in _mapping(json.loads((WORKSPACE_ROOT / _dmp).read_text(encoding="utf-8")).get("link_to_origins")).items()})
        except (OSError, ValueError, TypeError):
            pass
        try:
            _sdoc = json.loads((WORKSPACE_ROOT / _spath).read_text(encoding="utf-8"))
            for _lk, _e in _mapping(_sdoc.get("links")).items():
                _SUS_SIGS[str(_lk)] = str(_mapping(_e).get("signal", ""))
                for _pid, _g in _mapping(_mapping(_e).get("groups")).items():
                    _gm = _mapping(_g)
                    _SUS_LANES[(str(_lk), str(_pid))] = max(1, len(list(_gm.get("lanes") or [])))
                    # 우선순위: free(큐 있고 하류 자유, 창 >= min) → queued(창 >= min) → all(창 >= min). 하류가 막힌 창은 포화가 아니다.
                    _v = None
                    # "all"(전체 창 중앙)은 수요이지 용량이 아니라 씨앗으로 쓰지 않는다 — free/queued 만, 창 수 >= min.
                    for _key, _wkey in (("free", "windows_free"), ("queued", "windows_queued")):
                        if _stat == "queued" and _key == "free":
                            continue
                        _cand = _gm.get("sustained_%s_veh_h" % _key)
                        if _cand is not None and _as_float(_cand, 0.0) > 0.0 and int(_as_float(_gm.get(_wkey), 0.0)) >= _min_w:
                            _v = _as_float(_cand, 0.0)
                            break
                    if _v is not None:
                        sus[(str(_lk), str(_pid))] = _v
        except (OSError, ValueError):
            sus = {}
        for g in groups:
            link = str(g.get("stopline_link", ""))
            pid = _nema.get(str(g.get("sg_name", "")).upper())
            if not link or pid is None:
                continue
            geo = _as_float(g.get("geometric_veh_h"), 0.0)
            if geo <= 0.0:
                geo = max(1.0, _as_float(g.get("lanes_from_heads"), 1.0)) * 1800.0
            _floor = clamp(_as_float(section.get("sustained_floor_frac"), 0.15), 0.0, 1.0) * geo
            if queued is not None and link not in queued:
                val = geo * unqueued_frac
            elif (link, pid) in sus:
                val = clamp(sus[(link, pid)], _floor, geo)
            else:
                val = geo * missing_frac
            seed[link] = seed.get(link, 0.0) + val
            seed_lg[(link, pid)] = seed_lg.get((link, pid), 0.0) + val
        # SAT v3: 증거(08-22) 차로군 목록에 없는 (링크, 현시) 도 지속 산출물에서 씨앗을 만든다. config 게이트(`sustained_extra_groups`) — 없으면 비트 동일.
        _extra_on = _is_enabled_value(section.get("sustained_extra_groups"))
        for (_lk, _pid), _v in (sus.items() if _extra_on else ()):
            if (_lk, _pid) in seed_lg:
                continue
            _geo = float(_SUS_LANES.get((_lk, _pid), 1)) * 1800.0
            _fl = clamp(_as_float(section.get("sustained_floor_frac"), 0.15), 0.0, 1.0) * _geo
            if queued is not None and _lk not in queued:
                _val = _geo * unqueued_frac
            else:
                _val = clamp(_v, _fl, _geo)
            seed[_lk] = seed.get(_lk, 0.0) + _val
            seed_lg[(_lk, _pid)] = _val
    elif seed_mode == "geometric":
        for g in groups:
            link = str(g.get("stopline_link", ""))
            if link:
                seed[link] = seed.get(link, 0.0) + _as_float(g.get("saturation_veh_h"), 0.0)
    else:
        # 접근로 총량 = 그 접근로 movement 들의 현재 용량 합. 이탈 계수(링크 단위)와
        # 같은 단위가 되고, 아래 배분에서 그대로 되돌려 놓으므로 실측이 없으면 무변화다.
        for link, (sig, pids) in _approach_topology(groups).items():
            total = sum(
                float(base_caps.get(m, cfg.network.movement_capacity_veh_h))
                for m, spec in (cfg.network.urban_movements or {}).items()
                if str(spec.get("signal", "")) == sig
                and any(str(spec.get("phase", "")).endswith("_" + pid) for pid in pids)
                and str(spec.get("kind", "")) not in PERIMETER_MOVEMENT_KINDS_ADAPTER
            )
            if total > 0.0:
                seed[link] = total

    # 그 링크 차로군의 직전 구간 녹색초. 커밋한 계획을 쓴다(러너가 그대로 적용한다).
    # 2026-09-06 est 상한 = 링크 기하 용량(차로군 합). 관측 스파이크(h4 sat_est_66 4586)를 물리 위로 못 올린다.
    _cap_geo: dict[str, float] = {}
    if _is_enabled_value(section.get("est_cap_geometric")):
        for g in groups:
            _lk = str(g.get("stopline_link", ""))
            _geo = _as_float(g.get("geometric_veh_h"), 0.0)
            if _geo <= 0.0:
                _geo = max(1.0, _as_float(g.get("lanes_from_heads"), 1.0)) * 1800.0
            if _lk:
                _cap_geo[_lk] = _cap_geo.get(_lk, 0.0) + _geo
        for (_lk2, _pid2), _n in _SUS_LANES.items():
            if _lk2 not in _cap_geo:
                _cap_geo[_lk2] = _cap_geo.get(_lk2, 0.0) + float(_n) * 1800.0
    green_sec = _measured_green_sec_by_link(cfg, groups, previous_path)
    interval = _as_float(state_json.get("control_interval_sec"), 150.0)
    est: dict[str, float] = {}
    observed_used = 0
    for link in set(seed) | set(prev_est) | set(departures):
        g = green_sec.get(link, 0.0)
        obs = 0.0
        if g > 1.0 and link in departures:
            cycles = max(1.0, interval / max(1.0, _as_float(cfg.network.cycle_length, 150.0)))
            obs = departures[link] / (g * cycles) * 3600.0
        carried = decay * prev_est.get(link, seed.get(link, 0.0))
        value = max(obs, carried)
        # 2026-09-06 SAT v2: 큐가 서 있는 창의 관측은 수요가 아니라 용량이다 — 그때는 러닝맥스가 아니라 EWMA 로 곧바로 따라간다.
        if str(section.get("update", "")).strip().lower() == "queued_ewma" and obs > 0.0:
            _stopped_now = _as_float(_mapping(local.get("link_stopped_counts")).get(link), 0.0)
            if _stopped_now >= _as_float(section.get("queued_stopped_min"), 6.0):
                _alpha = clamp(_as_float(section.get("ewma_alpha"), 0.3), 0.0, 1.0)
                _prev = prev_est.get(link, seed.get(link, 0.0))
                value = _alpha * obs + (1.0 - _alpha) * _prev
                observed_used += 1
        if _cap_geo.get(link, 0.0) > 0.0:
            value = min(value, _cap_geo[link])
        if value > 0.0:
            est[link] = value
            if obs >= carried and obs > 0.0:
                observed_used += 1

    caps = dict(getattr(cfg.network, "movement_capacity_by_movement_veh_h", {}) or {})
    distribute_mode = str(section.get("distribute", "approach")).strip().lower()
    if distribute_mode == "lane_group" and seed_lg:
        # 링크 총량 est 를 차로군엔 씨앗 비율로 나눈다(온라인 갱신은 링크 단위 이탈 계수라 차로군을 못 가른다).
        est_lg: dict[tuple[str, str], float] = {}
        for (link, pid), sv in seed_lg.items():
            tot = sum(v for (lk, _p), v in seed_lg.items() if lk == link)
            if link in est and tot > 0.0:
                est_lg[(link, pid)] = float(est[link]) * float(sv) / float(tot)
        applied = _distribute_lane_group_capacity_to_movements(cfg, groups, est_lg, caps)
        # 증거(차로군)가 없는 internal movement: 접근로 링크가 무제어에서 큐가 안 서면 물리값(차로×1800), 큐가 서면
        # 현재값 유지(측정이 없으니 과대 위험 — 온라인 이탈 계수가 올려 준다). origin 링크 매핑이 없는(비핵심 신호) 것은 그대로.
        fallback_mode = str(section.get("fallback", "")).strip().lower()
        if fallback_mode == "geometric":
            fb_frac = clamp(_as_float(section.get("fallback_frac"), 1.0), 0.0, 1.0)
            lanes_src = WORKSPACE_ROOT / "outputs/movement_lanes_core17legs4b_20260821.json"
            lanes_map = {}
            try:
                lanes_map = _mapping(json.loads(lanes_src.read_text(encoding="utf-8")).get("movement_lanes"))
            except (OSError, ValueError):
                lanes_map = {}
            covered_links = {lk for (lk, _p) in seed_lg}
            queued_all: set[str] = set()
            if _qpath:
                try:
                    queued_all = {str(x) for x in (json.loads((WORKSPACE_ROOT / _qpath).read_text(encoding="utf-8")).get("queued_links") or [])}
                except (OSError, ValueError):
                    queued_all = set()
            origin_links_all = _origin_links_by_signal()
            fb_applied = 0
            for m, spec in (cfg.network.urban_movements or {}).items():
                if str(spec.get("kind", "")) != "internal":
                    continue
                links = origin_links_all.get(str(spec.get("signal", "")), {}).get(str(spec.get("origin", "")), set())
                if not links or (links & covered_links):
                    continue
                if links & queued_all:
                    continue
                lanes_m = _as_float(lanes_map.get(m), 0.0)
                if lanes_m <= 0.0:
                    lanes_m = 1.0
                caps[m] = float(lanes_m) * 1800.0 * fb_frac
                fb_applied += 1
            applied += fb_applied
            meta_fb = float(fb_applied)
        else:
            meta_fb = 0.0
    else:
        applied = _distribute_group_capacity_to_movements(cfg, groups, est, caps)
        meta_fb = 0.0
    if applied:
        setattr(cfg.network, "movement_capacity_by_movement_veh_h", caps)
    meta = {
        "measured_capacity_enabled": 1.0,
        "measured_capacity_seed_mode_observed": 1.0 if seed_mode == "observed" else 0.0,
        "measured_capacity_seed_mode_sustained": 1.0 if seed_mode == "sustained" else 0.0,
        "measured_capacity_est_cap_geometric": 1.0 if _cap_geo else 0.0,
        "measured_capacity_update_queued_ewma": 1.0 if str(section.get("update", "")).strip().lower() == "queued_ewma" else 0.0,
        "measured_capacity_distribute_lane_group": 1.0 if (distribute_mode == "lane_group" and seed_lg) else 0.0,
        "measured_capacity_fallback_geometric_movements": float(meta_fb),
        "measured_capacity_links": float(len(est)),
        "measured_capacity_observed_links": float(observed_used),
        "measured_capacity_movements": float(applied),
        "measured_capacity_decay": float(decay),
    }
    for link, value in sorted(est.items()):
        meta[f"sat_est_{link}"] = float(value)
    return meta
