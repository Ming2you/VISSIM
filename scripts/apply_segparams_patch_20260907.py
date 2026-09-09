# -*- coding: utf-8 -*-
"""세그먼트별 본선 파라미터를 **롤아웃까지** 먹이는 패치 (2026-09-07).

왜 필요한가 — 2026-09-07 오전에 넣은 `install_freeway_segment_lanes` 는 VISSIM 관측(밀도)만 세그먼트 차로로
고쳤다. 롤아웃은 `metanet.effective_lane_profile` 이 매 스텝 `[net.freeway_lanes]*n` 으로 프로파일을 새로
만들기 때문에 **기하 차로수를 한 번도 못 봤다**(팔로워의 local_freeway_plant._local_lane_profile 도 같은 복제).
그리고 v_free/rho_crit/a/tau/kappa/nu 는 전부 링크 스칼라라 합류·위빙 세그먼트가 평지와 같은 FD 를 쓴다.

이 패치가 하는 일 (config 키 없으면 전부 비트 동일):
  freeway.segment_lanes  : "mapping"     → 기하 차로 프로파일이 관측 + **롤아웃 공급/용량**에 반영
  freeway.segment_params : "<경로.json>" → 세그먼트별 v_free·rho_crit·metanet_a_m·tau·nu·kappa 주입
                           | "mapping"     (control_mapping 의 freeway_model_links[*].segment_params)

세그먼트 문맥 전달. vendor 의 `freeway_substep`(그리고 팔로워 `freeway_substep_local`)은 세그먼트 루프에서
반드시  segment_vsl(control, link, i, cfg) -> effective_desired_speed_kmh(...) -> select_anticipation_nu(...)
-> metanet_speed_update_kmh(...)  순서로 부른다. 그래서 `segment_vsl` 을 감싸 (link,i) 의 파라미터 사전을
무장하고 뒤 셋이 그걸 읽으며 마지막이 해제한다. 완충 셀(`_adv_chain`)은 `segment_vsl` 을 안 부르므로 무장이
없어 자동으로 링크 스칼라로 퇴화한다 — 호출 순서가 바뀌어도 안전한 쪽으로 무너진다.

한계(문서화). `metanet_delta_merge` 는 `freeway_substep` 이 루프 **밖에서** 지역변수로 한 번 읽으므로
세그먼트별로 못 준다. 다만 merge 항은 `ramp_in[i]>0` 인 셀에서만 발화하므로 실질은 합류 셀 전용이다.

사용: python apply_segparams_patch_20260907.py <adapter_path>
"""
import io
import sys

BLOCK = r'''# ---------------------------------------------------------------------------
# 세그먼트별 본선 파라미터 (2026-09-07) — 값 적재는 install_freeway_segment_lanes,
# 모듈 패치는 install_freeway_segment_runtime. 가격 워커(spawn)는 후자를 다시 부른다.
# ---------------------------------------------------------------------------
_FW_SEG_CTX: dict[str, Any] = {"p": {}, "armed": False}


def _fw_seg_param_dict(net, link, idx) -> Mapping:
    """(link, idx) 세그먼트의 파라미터 사전. 없으면 빈 dict → 링크 스칼라 그대로."""
    tbl = getattr(net, "freeway_segment_params", None) or {}
    if not isinstance(tbl, Mapping):
        return {}
    arr = tbl.get(str(link))
    if isinstance(arr, (list, tuple)) and 0 <= int(idx) < len(arr):
        row = arr[int(idx)]
        if isinstance(row, Mapping):
            return row
    return {}


def _fw_rebind(name: str, old, new) -> float:
    """`from ... import name` 으로 이름을 복사해 간 모듈까지 전부 재바인딩(5모듈 패치와 같은 사유)."""
    import sys as _sys
    n = 0
    for mod in list(_sys.modules.values()):
        if mod is None:
            continue
        try:
            if getattr(mod, name, None) is old:
                setattr(mod, name, new)
                n += 1
        except Exception:
            continue
    return float(n)


def install_freeway_segment_runtime(cfg) -> dict[str, float]:
    """cfg.network 에 실린 세그먼트 기하/파라미터를 vendor 롤아웃에 실제로 먹인다.

    부모와 가격 워커 양쪽에서 불린다 — 값(cfg.network.*)은 피클로 넘어가지만 **모듈 패치는 spawn 을
    못 넘기 때문에** 워커에서 다시 심어야 한다(far 램프 용량 패치와 같은 사유)."""
    import src.models.metanet as _mn
    import src.models.state as _st
    geo = getattr(cfg.network, "freeway_segment_lanes", None) or {}
    par = getattr(cfg.network, "freeway_segment_params", None) or {}
    if isinstance(par, Mapping):
        par = {k: v for k, v in par.items() if isinstance(v, (list, tuple)) and any(v)}
    else:
        par = {}
    out: dict[str, float] = {"fw_seg_geo_links": float(len(geo)), "fw_seg_param_links": float(len(par))}
    if not geo and not par:
        return out

    # (1) 기하 차로 프로파일 — 원본이 적용한 감소분(off-ramp spillback / incident)은 보존하고 바닥만 교체.
    if geo and not getattr(_mn.effective_lane_profile, "_rw_fw_seg_patch", False):
        _orig_elp = _mn.effective_lane_profile

        def _patched_effective_lane_profile(state, cfg_, demand=None):
            profile, diag = _orig_elp(state, cfg_, demand)
            g = getattr(cfg_.network, "freeway_segment_lanes", None) or {}
            if not g:
                return profile, diag
            base = float(cfg_.network.freeway_lanes)
            for link, lanes in profile.items():
                arr = g.get(str(link))
                if not arr:
                    continue
                for i in range(len(lanes)):
                    gi = float(arr[i]) if i < len(arr) else base
                    reduction = max(0.0, base - float(lanes[i]))
                    lanes[i] = max(1.0e-9, gi - reduction)
                if lanes:
                    diag["fw_geo_lanes_%s_min" % link] = float(min(lanes))
                    diag["fw_geo_lanes_%s_max" % link] = float(max(lanes))
            return profile, diag

        _patched_effective_lane_profile._rw_fw_seg_patch = True
        out["fw_seg_geo_rebind"] = _fw_rebind("effective_lane_profile", _orig_elp, _patched_effective_lane_profile)
        _mn.effective_lane_profile = _patched_effective_lane_profile

        try:
            import src.controllers.local_freeway_plant as _lfp
        except Exception:
            _lfp = None
        if _lfp is not None and not getattr(_lfp._local_lane_profile, "_rw_fw_seg_patch", False):
            _orig_llp = _lfp._local_lane_profile

            def _patched_local_lane_profile(model, occupancy, demand):
                lanes = _orig_llp(model, occupancy, demand)
                net_ = model.cfg.network
                arr = (getattr(net_, "freeway_segment_lanes", None) or {}).get(str(model.link))
                if not arr:
                    return lanes
                base = float(net_.freeway_lanes)
                for i in range(len(lanes)):
                    gi = float(arr[i]) if i < len(arr) else base
                    lanes[i] = max(1.0e-9, gi - max(0.0, base - float(lanes[i])))
                return lanes

            _patched_local_lane_profile._rw_fw_seg_patch = True
            _lfp._local_lane_profile = _patched_local_lane_profile
            out["fw_seg_geo_local_plant"] = 1.0

    # (2) 세그먼트별 FD/동역학 파라미터 — segment_vsl 이 문맥을 무장하고 뒤 셋이 읽는다.
    if par and not getattr(_st.segment_vsl, "_rw_fw_seg_patch", False):
        _o_sv = _st.segment_vsl
        _o_ed = _mn.effective_desired_speed_kmh
        _o_nu = _mn.select_anticipation_nu
        _o_up = _mn.metanet_speed_update_kmh

        def _patched_segment_vsl(control, link, index, cfg_):
            try:
                _FW_SEG_CTX["p"] = _fw_seg_param_dict(cfg_.network, link, index)
                _FW_SEG_CTX["armed"] = True
            except Exception:
                _FW_SEG_CTX["p"] = {}
                _FW_SEG_CTX["armed"] = False
            return _o_sv(control, link, index, cfg_)

        def _patched_effective_desired_speed_kmh(rho, v_free, rho_crit, vsl, alpha_vsl=0.0,
                                                 vsl_active=True, a=1.867, two_branch=False,
                                                 rho_jam=0.0, rho_crit_tb=0.0):
            p = _FW_SEG_CTX["p"] if _FW_SEG_CTX["armed"] else {}
            if p:
                v_free = float(p.get("v_free", v_free))
                rho_crit = float(p.get("rho_crit", rho_crit))
                a = float(p.get("metanet_a_m", a))
                if _as_float(p.get("rho_max"), 0.0) > 0.0:
                    rho_jam = float(p["rho_max"])
            return _o_ed(rho, v_free, rho_crit, vsl, alpha_vsl, vsl_active, a, two_branch, rho_jam, rho_crit_tb)

        def _patched_select_anticipation_nu(rho, net, vsl=None):
            p = _FW_SEG_CTX["p"] if _FW_SEG_CTX["armed"] else {}
            if not p:
                return _o_nu(rho, net, vsl)
            rho_c = float(p.get("rho_crit", getattr(net, "rho_crit", 0.0)))
            if getattr(net, "capacity_drop_anticipation", False) and rho > rho_c:
                return float(p.get("metanet_nu_cong_km2_h", net.metanet_nu_cong_km2_h))
            return float(p.get("metanet_nu_km2_h", net.metanet_nu_km2_h))

        def _patched_metanet_speed_update_kmh(speed, upstream_speed, rho, downstream_rho, v_eff,
                                              dt_h, length_km, tau_h, nu_km2_h,
                                              kappa_veh_km_lane, v_min):
            p = _FW_SEG_CTX["p"] if _FW_SEG_CTX["armed"] else {}
            _FW_SEG_CTX["armed"] = False      # 문맥은 여기서 해제 — 완충 셀은 링크 스칼라로 퇴화
            if p:
                tau_h = float(p.get("metanet_tau_h", tau_h))
                kappa_veh_km_lane = float(p.get("metanet_kappa_veh_km_lane", kappa_veh_km_lane))
                length_km = float(p.get("segment_length_km", length_km))
            return _o_up(speed, upstream_speed, rho, downstream_rho, v_eff, dt_h, length_km,
                         tau_h, nu_km2_h, kappa_veh_km_lane, v_min)

        for _f in (_patched_segment_vsl, _patched_effective_desired_speed_kmh,
                   _patched_select_anticipation_nu, _patched_metanet_speed_update_kmh):
            _f._rw_fw_seg_patch = True
        out["fw_seg_rebind_vsl"] = _fw_rebind("segment_vsl", _o_sv, _patched_segment_vsl)
        out["fw_seg_rebind_ved"] = _fw_rebind("effective_desired_speed_kmh", _o_ed, _patched_effective_desired_speed_kmh)
        out["fw_seg_rebind_nu"] = _fw_rebind("select_anticipation_nu", _o_nu, _patched_select_anticipation_nu)
        out["fw_seg_rebind_upd"] = _fw_rebind("metanet_speed_update_kmh", _o_up, _patched_metanet_speed_update_kmh)
        _st.segment_vsl = _patched_segment_vsl
        _mn.segment_vsl = _patched_segment_vsl
        _mn.effective_desired_speed_kmh = _patched_effective_desired_speed_kmh
        _mn.select_anticipation_nu = _patched_select_anticipation_nu
        _mn.metanet_speed_update_kmh = _patched_metanet_speed_update_kmh
        out["fw_seg_param_segments"] = float(sum(len(v) for v in par.values()))
    return out


'''

SET_NEW = r'''    # `freeway.segment_params` 가 경로면 보정 산출물에서 세그먼트 배열을 만든다
    # (schema freeway_segment_params_v1: segments["FW_E_S3"] = {파라미터...}).
    _pspec = str(section.get("segment_params", "") or "").strip()
    if _pspec and _pspec.lower() != "mapping":
        _root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(_pspec if os.path.isabs(_pspec) else os.path.join(_root, _pspec), encoding="utf-8") as _pf:
            _pj = json.load(_pf)
        _segs = _mapping(_pj.get("segments"))
        _keys = ("v_free", "rho_crit", "rho_max", "metanet_a_m", "metanet_tau_h", "metanet_nu_km2_h",
                 "metanet_nu_cong_km2_h", "metanet_kappa_veh_km_lane", "segment_length_km")
        for model, arr in lanes_by.items():
            rows = []
            for i in range(len(arr)):
                row = _mapping(_segs.get("%s_S%d" % (model, i)))
                rows.append({k: float(row[k]) for k in _keys
                             if isinstance(row.get(k), (int, float)) and not isinstance(row.get(k), bool)})
            params_by[str(model)] = rows
    setattr(cfg.network, "freeway_segment_lanes", lanes_by)
    setattr(cfg.network, "freeway_segment_params", params_by)'''

WORKER_NEW = (
    "    # 세그먼트 기하 차로/FD 파라미터 모듈 패치. 값은 cfg.network 로 피클돼 오지만\n"
    "    # 모듈 패치는 spawn 을 못 넘는다 — 안 심으면 워커 10개가 링크 스칼라 FD 로 가격을 매긴다.\n"
    "    out.update(install_freeway_segment_runtime(cfg))\n")


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "def install_freeway_segment_runtime(" in s:
        print("already patched:", path)
        return

    anchor = "def _plant_gate_peeloff_into(cfg, tuning) -> None:"
    assert s.count(anchor) == 1, ("anchor", s.count(anchor))
    s = s.replace(anchor, BLOCK + anchor)

    old_par = ('        if isinstance(spec.get("segment_params"), Mapping):\n'
               '            params_by[str(model)] = dict(spec.get("segment_params"))')
    new_par = ('        if isinstance(spec.get("segment_params"), list):\n'
               '            params_by[str(model)] = [dict(r) if isinstance(r, Mapping) else {} for r in spec["segment_params"]]\n'
               '        elif isinstance(spec.get("segment_params"), Mapping):\n'
               '            params_by[str(model)] = dict(spec.get("segment_params"))')
    assert s.count(old_par) == 1, ("par anchor", s.count(old_par))
    s = s.replace(old_par, new_par)

    old_set = ('    setattr(cfg.network, "freeway_segment_lanes", lanes_by)\n'
               '    setattr(cfg.network, "freeway_segment_params", params_by)')
    assert s.count(old_set) == 1, ("set anchor", s.count(old_set))
    s = s.replace(old_set, SET_NEW)

    old_call = "    runtime_patch_metadata.update(install_freeway_segment_lanes(cfg, tuning, mapping))\n"
    assert s.count(old_call) == 1, ("main anchor", s.count(old_call))
    s = s.replace(old_call, old_call + "    runtime_patch_metadata.update(install_freeway_segment_runtime(cfg))\n")

    old_worker = "    out.update(install_landing_storage_runtime(cfg))\n"
    assert s.count(old_worker) == 1, ("worker anchor", s.count(old_worker))
    s = s.replace(old_worker, old_worker + WORKER_NEW)

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("segparams patch applied to", path)


if __name__ == "__main__":
    main()
