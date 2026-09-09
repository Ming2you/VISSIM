# -*- coding: utf-8 -*-
"""녹색분율 hot path 의 상수 재계산을 걷어낸다 — 결과 불변 (2026-09-08).

근거. 21셀 결정 1회 프로파일(`outputs/decision_profile_kbest_serial.log`):

    patched_phase_green_fraction   10,909,065 회   누적 315.8 s = 결정의 28%
      _validation_fixed_signal_enabled  8,470,965 회  누적  57.6 s   <- os.environ 읽기
      native_phase_green._share_key     8,470,965 회  누적  28.6 s   <- 문자열 4개 매번 생성
      vendor _phase_green_fraction      8,470,965 회  누적 158.2 s   (실제 물리)

앞의 둘은 **결정 중에 절대 안 바뀌는 값**을 movement x substep x 롤아웃마다 다시 만든 것이다.
  - env 는 프로세스 상수다(그리고 이 스위치는 검증 전용이라 런 도중 바뀌면 오히려 사고다).
  - share 는 spec 의 함수다 — `share_for` 가 `shares.get(_share_key(spec))` 뿐이다.

그래서 패치 설치 시점에 env 를 한 번 읽고, share 는 spec 별로 기억한다. 캐시 키는 `id(spec)` 인데
**spec 강참조를 같이 들고** 있어 id 재사용이 불가능하다(참조가 살아 있는 동안 그 id 는 재할당되지
않는다). movement 는 474개라 캐시가 커질 일이 없다.

한 비트도 안 바뀐다 — 같은 입력에 같은 값을 돌려준다. 가격 워커(spawn)도 같은 빌더를 다시 부르므로
자동으로 적용된다.

사용: python apply_greenfrac_hotpath_patch_20260908.py <adapter_path>
"""
import io
import sys

HOIST = '''    # --- hot path 상수 걷어내기 (2026-09-08) ---------------------------------------
    # 아래 둘은 결정 중에 바뀌지 않는데 종전에는 **매 호출** 다시 만들었다. 21셀 결정 1회에
    # 각각 847만 번(누적 57.6 s · 28.6 s = 결정의 7.7%)이다. 값이 같으므로 결과는 불변이다.
    _validation_fixed = _validation_fixed_signal_enabled()
    _share_cache: dict = {}          # id(spec) -> (spec 강참조, share)

    def _share_of(spec):
        hit = _share_cache.get(id(spec))
        if hit is not None and hit[0] is spec:
            return hit[1]
        value = share_table.share_for(spec)
        _share_cache[id(spec)] = (spec, value)
        return value

'''


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "_rw_greenfrac_hotpath" in s:
        print("already patched:", path)
        return

    anchor = "    def patched_phase_green_fraction(control, cfg_arg, spec, urban_step_index=None):"
    assert s.count(anchor) == 1, ("def anchor", s.count(anchor))
    s = s.replace(anchor, HOIST + anchor)

    old_env = "            if _validation_fixed_signal_enabled():"
    assert s.count(old_env) == 1, ("env anchor", s.count(old_env))
    s = s.replace(old_env, "            if _validation_fixed:")

    old_share = "            share = share_table.share_for(spec)"
    assert s.count(old_share) == 1, ("share anchor", s.count(old_share))
    s = s.replace(old_share, "            share = _share_of(spec)")

    old_ret = "    return patched_phase_green_fraction"
    assert s.count(old_ret) == 1, ("return anchor", s.count(old_ret))
    s = s.replace(old_ret,
                  "    patched_phase_green_fraction._rw_greenfrac_hotpath = True\n" + old_ret)

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("patched:", path)


if __name__ == "__main__":
    main()
