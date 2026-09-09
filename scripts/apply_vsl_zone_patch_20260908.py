# -*- coding: utf-8 -*-
"""VSL 을 **표지판 구역** 단위로 만든다 — 모형·가격·플랜트 정합 (2026-09-08).

무엇이 어긋나 있었나. 이 망의 VSL 은 방향당 **표지판 8개**이고 자리가 고정돼 있다
(셀 0·2·5·7·10·13·15·18, 간격 ~1,347 m — `control_mapping_ver2n21.json` 의 `segments[].dsds`
와 VBS 의 `RW_EXPECTED_VSL_ACTION_KEYS` 66행이 같은 자리를 가리킨다). 그런데

  * 모형은 **셀 21개**에 각각 다른 VSL 을 걸 수 있다고 보고 롤아웃한다.
  * 플랜트(VBS)는 그 8개 자리에만 쓴다 — 표지판 없는 셀에 건 값은 **아무 데도 안 써진다**.
  * 팔로워의 자유 셀 규칙은 표지판이 아니라 `첫 off-ramp 상류`(upstream_control_idx)라,
    FW_E 는 표지판 8개 중 4개(S0·2·5·7), FW_W 는 3개(S0·2·5)만 움직이고 나머지는 영구 고정.
  * 커밋된 행동의 `vsl` 은 링크 키뿐이라 `segment_vsl` 이 전부 링크 값으로 떨어지고,
    `apply_action_schedule` 의 `control.vsl[link]=min(...)` 때문에 세그먼트 하나를 내리면
    링크 전체가 내려간다 — 세그먼트별 VSL 가격 84회 중 대부분이 같은 제어의 중복이다.

무엇으로 바꾸나. **구역**을 정본으로 둔다. 셀은 자기 구역 머리(=표지판)의 값을 물려받는다.
표지판 사이 구간은 상류 표지판이 지시한 속도를 유지하는 실제 거동과 같다(사용자 지시).

  구역 머리   셀 0 / 5 / 10 / 15   (전부 실제 표지판 자리, 구역 길이 2.57~3.08 km)
  구역 0 [0-4]   상류 접근        가변
  구역 1 [5-9]   첫 IC 포함        가변
  구역 2 [10-14] 둘째 IC 포함      가변
  구역 3 [15-20] 하류 회복         vsl_max 고정 (config 로 해제 가능)

한 자리만 고치면 셋이 같이 맞는다 — 모형 롤아웃·가격 코너·플랜트 쓰기가 전부
`segment_vsl(control, link, i, cfg)` 를 거치기 때문이다(플랜트 쓰기는 어댑터의 action CSV
writer 가 세그먼트마다 이 함수를 부른다). 그래서 `segment_vsl` 을 구역 인식으로 바꾸고,
후보 생성기(k-best 판)는 `cfg.network.freeway_vsl_zone_*` 를 읽어 구역 머리만 훑는다.

config 키:
  freeway.vsl_zone_heads   {"FW_E": [0,5,10,15], "FW_W": [0,5,10,15]}   없으면 no-op(비트 동일)
  freeway.vsl_zone_free    [0,1,2]   생략하면 전 구역 가변
전제: apply_vsl_kbest_patch_20260908.py 가 먼저 적용돼 있어야 한다(후보 생성기가 구역을 읽는다).
설치 순서: **install_freeway_segment_runtime 보다 먼저** — 그쪽이 `_o_sv = _st.segment_vsl` 를
잡아 두므로, 먼저 심어야 구역판이 그 원본이 된다.

사용: python apply_vsl_zone_patch_20260908.py <adapter_path>
"""
import io
import sys

INSTALLER = '''def install_freeway_vsl_zones(cfg, tuning=None) -> dict[str, float]:
    """VSL 자유도를 표지판 구역으로 묶는다. 셀은 자기 구역 머리의 값을 쓴다.

    `freeway.vsl_zone_heads` 가 없으면 아무것도 안 한다(비트 동일).
    """
    section = _mapping(_mapping(tuning).get("freeway")) if tuning is not None else {}
    net = cfg.network
    heads_cfg = _mapping(section.get("vsl_zone_heads"))
    if not heads_cfg:
        # 가격 워커(spawn)는 tuning 을 못 받는다. 값은 cfg.network 로 피클돼 오므로 그걸 되읽어
        # **모듈 패치만** 다시 심는다 - 안 심으면 워커 10개가 셀 단위 VSL 로 가격을 매긴다.
        heads_cfg = _mapping(getattr(net, "freeway_vsl_zone_heads", None) or {})
        if not heads_cfg:
            return {"fw_vsl_zones_enabled": 0.0}

    lanes_tbl = _mapping(getattr(net, "freeway_segment_lanes", None) or {})
    heads: dict = {}
    head_of: dict = {}
    zone_of: dict = {}
    for link in net.freeway_links:
        n = len(lanes_tbl.get(str(link)) or []) or int(net.freeway_segments_per_link)
        hs = sorted({int(x) for x in (heads_cfg.get(str(link)) or [])})
        if not hs:
            continue
        if hs[0] != 0:
            raise ValueError("VSL 구역 머리는 셀 0 을 포함해야 한다: %s %s" % (link, hs))
        if hs[-1] >= n:
            raise ValueError("VSL 구역 머리가 셀 수를 넘는다: %s %s (셀 %d)" % (link, hs, n))
        hd, zo = [], []
        for i in range(n):
            z = 0
            for j, h in enumerate(hs):
                if h <= i:
                    z = j
            zo.append(z)
            hd.append(hs[z])
        heads[str(link)] = hs
        head_of[str(link)] = hd
        zone_of[str(link)] = zo
    if not heads:
        return {"fw_vsl_zones_enabled": 0.0}

    free_cfg = section.get("vsl_zone_free")
    if free_cfg is None:
        free_cfg = getattr(net, "freeway_vsl_zone_free", None)
    n_zone = max(len(v) for v in heads.values())
    free = sorted({int(x) for x in free_cfg}) if free_cfg is not None else list(range(n_zone))

    setattr(net, "freeway_vsl_zone_heads", heads)
    setattr(net, "freeway_vsl_zone_head_of_cell", head_of)
    setattr(net, "freeway_vsl_zone_of_cell", zone_of)
    setattr(net, "freeway_vsl_zone_free", free)

    out = {"fw_vsl_zones_enabled": 1.0, "fw_vsl_zone_count": float(n_zone),
           "fw_vsl_zone_free_count": float(len(free))}
    for link, hs in heads.items():
        out["fw_vsl_zone_heads_%s" % link] = float(len(hs))

    # `segment_vsl` 을 구역 인식으로. 롤아웃·가격·플랜트 쓰기가 전부 이 함수를 거치므로
    # 한 자리에서 셋이 같이 맞는다.
    import src.models.state as _st
    _o_sv = _st.segment_vsl
    if not getattr(_o_sv, "_rw_vsl_zone", False):
        def _zoned_segment_vsl(control, link, i, cfg_):
            tbl = getattr(cfg_.network, "freeway_vsl_zone_head_of_cell", None) or {}
            arr = tbl.get(str(link))
            if arr:
                idx = int(i)
                if 0 <= idx < len(arr):
                    i = int(arr[idx])
            return _o_sv(control, link, i, cfg_)

        _zoned_segment_vsl._rw_vsl_zone = True
        out["fw_vsl_zone_rebind"] = _fw_rebind("segment_vsl", _o_sv, _zoned_segment_vsl)
        _st.segment_vsl = _zoned_segment_vsl

    # `local_vsl_costs` 는 세그먼트 벡터를 `vsl_override` 로 **직접** 먹여 segment_vsl 을
    # 우회한다. 구역 밖 셀을 흔든 벡터가 그대로 들어가면 국소 채점만 구역을 안 지킨다 -
    # 요청 벡터를 구역으로 사영해 맞춘다.
    from src.controllers import wu_faithful_follower as _wff
    _cls = _wff.WuFaithfulFollower
    _o_lvc = getattr(_cls, "local_vsl_costs", None)
    if _o_lvc is not None and not getattr(_o_lvc, "_rw_vsl_zone", False):
        def _zoned_local_vsl_costs(self, requests, state, previous, demand, *a, **k):
            tbl = getattr(self.cfg.network, "freeway_vsl_zone_head_of_cell", None) or {}
            if tbl and isinstance(requests, Mapping):
                proj = {}
                for link, vecs in requests.items():
                    arr = tbl.get(str(link))
                    if not arr:
                        proj[link] = vecs
                        continue
                    proj[link] = [[float(v[int(arr[i])]) if int(arr[i]) < len(v) else float(v[i])
                                   for i in range(len(v))] for v in vecs]
                requests = proj
            return _o_lvc(self, requests, state, previous, demand, *a, **k)

        _zoned_local_vsl_costs._rw_vsl_zone = True
        _cls.local_vsl_costs = _zoned_local_vsl_costs
        out["fw_vsl_zone_local_costs_patched"] = 1.0
    return out


'''


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "def install_freeway_vsl_zones(" in s:
        print("already patched:", path)
        return
    assert "def install_freeway_vsl_sequence_kbest(" in s, "k-best 패치가 먼저 적용돼야 한다"

    anchor = "def install_freeway_vsl_sequence_kbest(cfg, tuning=None) -> dict[str, float]:"
    assert s.count(anchor) == 1, ("installer anchor", s.count(anchor))
    s = s.replace(anchor, INSTALLER + anchor)

    # main(): 세그먼트 런타임 **앞**에 둔다(그쪽이 원본 segment_vsl 을 잡는다).
    old_main = "    runtime_patch_metadata.update(install_freeway_segment_runtime(cfg))"
    assert s.count(old_main) == 1, ("main anchor", s.count(old_main))
    s = s.replace(old_main,
                  "    runtime_patch_metadata.update(install_freeway_vsl_zones(cfg, tuning))\n" + old_main)

    # 가격 워커(spawn)도 같은 순서로 되살려야 한다.
    old_worker = "    out.update(install_freeway_segment_runtime(cfg))"
    assert s.count(old_worker) == 1, ("worker anchor", s.count(old_worker))
    s = s.replace(old_worker,
                  "    out.update(install_freeway_vsl_zones(cfg, None))\n" + old_worker)

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("patched:", path)


if __name__ == "__main__":
    main()
