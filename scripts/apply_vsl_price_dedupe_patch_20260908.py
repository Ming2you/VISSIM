# -*- coding: utf-8 -*-
"""VSL 가격 롤아웃의 중복을 제거한다 — 비트 동치 (2026-09-08).

왜. `_vsl_price_rollouts` 는 코너마다 hi/lo 두 개의 **전역 롤아웃**을 돌린다. 셀이 21개면
2링크 x 21셀 x 2 = **84회**다(8셀일 때는 32회). 그런데 VSL 구역이 설치되면 `segment_vsl` 이
셀의 **구역 머리 키**만 읽으므로, 머리가 아닌 셀을 흔들면 아무도 안 읽는 키를 쓰는 것이라
결과 제어가 기준선과 **완전히 같다**. 같은 구역 머리를 같은 값으로 흔든 태스크끼리도 같다.

롤아웃은 (state, control, forecast, spec) 의 순수 함수다. 그래서 **실효 제어가 같은 태스크는
값도 같다** — 대표 하나만 돌리고 나머지에 복사하면 비트 동치다. 추정이 아니라 항등이다.

실효 제어는 `rollout_endpoint.apply_action_schedule` 규약 그대로 계산한다:

    base = dict(previous.vsl); base[seg_key] = value
    base[link] = min(base.get(link, value), value)
    셀 j 가 읽는 값 = base[f"{link}__seg{head(j)}"] (없으면 base[link])

이 벡터 + 링크 키 값을 묶음 키로 쓴다(링크 키를 따로 넣는 것은 그 값을 읽는 다른 소비자가
있어도 안전하게 갈라 두려는 것이다).

구역이 없으면 아무것도 안 한다 — vendor 원본 그대로다.
사용: python apply_vsl_price_dedupe_patch_20260908.py <adapter_path>
"""
import io
import sys

INSTALLER = '''def install_freeway_vsl_price_dedupe(cfg, tuning=None) -> dict[str, float]:
    """VSL 가격 코너 중 **실효 제어가 같은** 태스크를 하나로 묶어 롤아웃 수를 줄인다.

    구역이 설치돼 있어야 의미가 있다(머리가 아닌 셀의 섭동이 무효가 되는 것이 전제다).
    반환값은 종전과 같은 (seg_key, 'lo'|'hi') -> 튜플 이고, 값도 같다.
    """
    if not (getattr(cfg.network, "freeway_vsl_zone_head_of_cell", None) or {}):
        return {"fw_vsl_price_dedupe_enabled": 0.0}
    import src.controllers.stackelberg_wu_metered as _swm

    _cls = _swm.StackelbergWuMeteredController if hasattr(
        _swm, "StackelbergWuMeteredController") else None
    if _cls is None:
        for _name in dir(_swm):
            _obj = getattr(_swm, _name)
            if isinstance(_obj, type) and hasattr(_obj, "_vsl_price_rollouts"):
                _cls = _obj
                break
    if _cls is None:
        return {"fw_vsl_price_dedupe_enabled": 0.0}
    _orig = _cls._vsl_price_rollouts
    if getattr(_orig, "_rw_vsl_dedupe", False):
        return {"fw_vsl_price_dedupe_enabled": 1.0, "fw_vsl_price_dedupe_patched": 0.0}
    _worker = _swm._price_worker_vsl

    def _patched_vsl_price_rollouts(self, state, previous, forecast, v_corners, vsl_upper):
        net = self.cfg.network
        head_tbl = _mapping(getattr(net, "freeway_vsl_zone_head_of_cell", None) or {})
        if not head_tbl:
            return _orig(self, state, previous, forecast, v_corners, vsl_upper)

        tasks = []
        for key, (_x0, v_lo, v_hi, link, _req) in v_corners.items():
            if float(v_hi) - float(v_lo) <= 1.0e-9:
                continue
            tasks.append((key, "hi", link, float(v_hi), vsl_upper))
            tasks.append((key, "lo", link, float(v_lo), vsl_upper))
        if not tasks:
            return {}

        prev_vsl = dict(previous.vsl or {})

        def effective(seg_key, link, value):
            base = dict(prev_vsl)
            base[str(seg_key)] = float(value)
            base[str(link)] = min(float(base.get(str(link), value)), float(value))
            arr = head_tbl.get(str(link)) or []
            fallback = float(base.get(str(link), value))
            vec = []
            for j in range(len(arr)):
                vec.append(round(float(base.get("%s__seg%d" % (link, int(arr[j])), fallback)), 9))
            return (str(link), tuple(vec), round(float(base[str(link)]), 9))

        groups: dict = {}
        for t in tasks:
            groups.setdefault(effective(t[0], t[2], t[3]), []).append(t)
        reps = [g[0] for g in groups.values()]

        def serial():
            return {
                (k, w): (self._global_rollout_ttt_with_vsl(
                    state, previous, forecast, link, k, val, up),)
                for k, w, link, val, up in reps
            }

        got = self._price_batch(reps, _worker, serial, state, previous, forecast)
        out = {}
        for members in groups.values():
            rep = members[0]
            value = got.get((rep[0], rep[1]))
            for m in members:
                out[(m[0], m[1])] = value
        _FW_VSL_DEDUPE_STATE["tasks"] = len(tasks)
        _FW_VSL_DEDUPE_STATE["rollouts"] = len(reps)
        return out

    _patched_vsl_price_rollouts._rw_vsl_dedupe = True
    _cls._vsl_price_rollouts = _patched_vsl_price_rollouts
    return {"fw_vsl_price_dedupe_enabled": 1.0, "fw_vsl_price_dedupe_patched": 1.0}


'''

STATE = '''_FW_VSL_DEDUPE_STATE: dict[str, int] = {"tasks": 0, "rollouts": 0}


'''


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "def install_freeway_vsl_price_dedupe(" in s:
        print("already patched:", path)
        return
    assert "def install_freeway_vsl_zones(" in s, "VSL 구역 패치가 먼저 적용돼야 한다"

    anchor = "def install_freeway_vsl_zones(cfg, tuning=None) -> dict[str, float]:"
    assert s.count(anchor) == 1, ("installer anchor", s.count(anchor))
    s = s.replace(anchor, STATE + INSTALLER + anchor)

    old_main = "    runtime_patch_metadata.update(install_freeway_vsl_sequence_kbest(cfg, tuning))"
    assert s.count(old_main) == 1, ("main anchor", s.count(old_main))
    s = s.replace(old_main, old_main +
                  "\n    runtime_patch_metadata.update(install_freeway_vsl_price_dedupe(cfg, tuning))")

    old_worker = "    out.update(install_freeway_vsl_sequence_kbest(cfg, None))"
    assert s.count(old_worker) == 1, ("worker anchor", s.count(old_worker))
    s = s.replace(old_worker, old_worker +
                  "\n    out.update(install_freeway_vsl_price_dedupe(cfg, None))")

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("patched:", path)


if __name__ == "__main__":
    main()
