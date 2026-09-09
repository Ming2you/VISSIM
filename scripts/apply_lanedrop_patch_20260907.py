# -*- coding: utf-8 -*-
"""METANET 차로감소항(φ) 추가 패치 (2026-09-07).

vendor 에는 이 항이 **없다**. 있는 것은 (a) 유효차로수 λ 를 통한 공급·용량 축소와 (b) 합류항 δ 뿐이다.
차로가 줄면 그 직전 셀에서 속도가 추가로 떨어지는데, 표준 METANET 은 그것을 별도 항으로 둔다:

    Δv = − φ · T · Δλ · ρ_i · v_i²  /  (L · λ_i · ρ_cr,i)        Δλ = λ_i − λ_{i+1}

**차로가 줄어드는 직전 셀에만** 건다(Δλ > 0). 차로가 느는 곳(FW_W 의 3→4)은 이 형태가 아니므로 걸지 않는다.
Ver2 N=21 에서 해당 셀은 FW_E 12 (λ 4 → 13번 셀 3) 하나다.

단위 확인: [h]·[veh/km/lane]·[km²/h²] / ([km]·[veh/km/lane]) = km/h. dt_h·rho·speed²/(L_km·rho_crit) 로 쓴다.

config 키: `freeway.lane_drop_phi` (없거나 0 이면 비트 동일). 세그먼트별 λ 는 `freeway.segment_lanes` 가,
ρ_cr 은 `freeway.segment_params` 가 제공한다 — 둘 중 하나라도 없으면 이 항은 발화하지 않는다.

전제: apply_segparams_patch_20260907.py 가 먼저 적용돼 있어야 한다(세그먼트 문맥을 그 패치가 무장한다).
사용: python apply_lanedrop_patch_20260907.py <adapter_path>
"""
import io
import sys

INSTALLER = '''def install_freeway_lane_drop(cfg, tuning) -> dict[str, float]:
    """config `freeway.lane_drop_phi` → cfg.network.freeway_lane_drop_phi. 없거나 0 이면 no-op."""
    section = _mapping(_mapping(tuning).get("freeway"))
    phi = _as_float(section.get("lane_drop_phi"), 0.0)
    setattr(cfg.network, "freeway_lane_drop_phi", float(phi))
    out = {"freeway_lane_drop_phi": float(phi)}
    if phi > 0.0:
        geo = _mapping(getattr(cfg.network, "freeway_segment_lanes", None) or {})
        n = 0
        for link, arr in geo.items():
            for i in range(len(arr) - 1):
                if float(arr[i]) - float(arr[i + 1]) > 1.0e-9:
                    n += 1
                    out["lane_drop_cell_%s" % link] = float(i)
        out["lane_drop_cells"] = float(n)
    return out


'''


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "def install_freeway_lane_drop(" in s:
        print("already patched:", path)
        return
    assert "_FW_SEG_CTX" in s, "apply_segparams_patch_20260907.py 를 먼저 적용해라"

    anchor = "def install_freeway_segment_runtime(cfg) -> dict[str, float]:"
    assert s.count(anchor) == 1, ("installer anchor", s.count(anchor))
    s = s.replace(anchor, INSTALLER + anchor)

    # (1) 문맥 무장에 Δλ 와 ρ_cr 을 함께 싣는다 — 속도 갱신 시점에는 cfg 가 없다.
    old_ctx = '''        def _patched_segment_vsl(control, link, index, cfg_):
            try:
                _FW_SEG_CTX["p"] = _fw_seg_param_dict(cfg_.network, link, index)
                _FW_SEG_CTX["armed"] = True
            except Exception:
                _FW_SEG_CTX["p"] = {}
                _FW_SEG_CTX["armed"] = False
            return _o_sv(control, link, index, cfg_)'''
    new_ctx = '''        def _patched_segment_vsl(control, link, index, cfg_):
            try:
                _FW_SEG_CTX["p"] = _fw_seg_param_dict(cfg_.network, link, index)
                _FW_SEG_CTX["armed"] = True
                # 차로감소항 재료. Δλ = λ_i − λ_{i+1} (감소일 때만 양수) 와 φ 를 여기서 실어 둔다 —
                # metanet_speed_update_kmh 는 cfg 를 못 본다.
                _phi = _as_float(getattr(cfg_.network, "freeway_lane_drop_phi", 0.0), 0.0)
                _dl = 0.0
                if _phi > 0.0:
                    _arr = _mapping(getattr(cfg_.network, "freeway_segment_lanes", None) or {}).get(str(link))
                    if isinstance(_arr, (list, tuple)) and 0 <= int(index) + 1 < len(_arr):
                        _dl = max(0.0, float(_arr[int(index)]) - float(_arr[int(index) + 1]))
                _FW_SEG_CTX["phi"] = _phi
                _FW_SEG_CTX["dlam"] = _dl
                _FW_SEG_CTX["lanes"] = float(_arr[int(index)]) if (_phi > 0.0 and _dl > 0.0) else 0.0
            except Exception:
                _FW_SEG_CTX["p"] = {}
                _FW_SEG_CTX["armed"] = False
                _FW_SEG_CTX["phi"] = 0.0
                _FW_SEG_CTX["dlam"] = 0.0
            return _o_sv(control, link, index, cfg_)'''
    assert s.count(old_ctx) == 1, ("ctx anchor", s.count(old_ctx))
    s = s.replace(old_ctx, new_ctx)

    # (2) 속도 갱신 뒤 차로감소항을 뺀다.
    old_upd = '''            return _o_up(speed, upstream_speed, rho, downstream_rho, v_eff, dt_h, length_km,
                         tau_h, nu_km2_h, kappa_veh_km_lane, v_min)'''
    new_upd = '''            v_new = _o_up(speed, upstream_speed, rho, downstream_rho, v_eff, dt_h, length_km,
                          tau_h, nu_km2_h, kappa_veh_km_lane, v_min)
            # 차로감소항: Δv = −φ·T·Δλ·ρ·v² / (L·λ·ρ_cr). 차로가 주는 직전 셀에만 걸린다.
            _phi = _FW_SEG_CTX.get("phi") or 0.0
            _dl = _FW_SEG_CTX.get("dlam") or 0.0
            if _phi > 0.0 and _dl > 0.0:
                _lam = max(1.0e-9, float(_FW_SEG_CTX.get("lanes") or 1.0))
                _rc = float((p or {}).get("rho_crit", 0.0)) or 27.0
                v_new = max(v_min, v_new - _phi * dt_h * _dl * max(rho, 0.0) * (speed ** 2)
                            / (max(length_km, 1.0e-9) * _lam * max(_rc, 1.0e-9)))
            return v_new'''
    assert s.count(old_upd) == 1, ("upd anchor", s.count(old_upd))
    s = s.replace(old_upd, new_upd)

    # (3) main() 과 가격 워커에서 설치기를 부른다.
    old_call = "    runtime_patch_metadata.update(install_freeway_segment_runtime(cfg))\n"
    assert s.count(old_call) == 1, ("call anchor", s.count(old_call))
    s = s.replace(old_call, "    runtime_patch_metadata.update(install_freeway_lane_drop(cfg, tuning))\n" + old_call, 1)
    # 워커 쪽은 tuning 이 없다 — 값은 cfg.network 로 피클돼 오므로 재설치가 필요 없다.

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("lane drop patch applied to", path)


if __name__ == "__main__":
    main()
