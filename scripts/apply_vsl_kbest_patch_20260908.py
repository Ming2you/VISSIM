# -*- coding: utf-8 -*-
"""VSL 시퀀스 후보 생성의 데카르트 곱 폭발을 k-best 지연 생성으로 바꾼다 (2026-09-08).

무엇이 터졌나. `WuFaithfulFollower._freeway_vsl_sequence_candidates` 는 세그먼트마다 만든 옵션의
**전체 곱을 리스트로 통째 전개**한 뒤에야 vsl_sequence_candidate_limit(12)로 자른다:

    per_segment = [segment_sequences(i) for i in range(n_seg)]
    segment_combinations = [[]]
    for options in per_segment:
        segment_combinations = [partial + [option]
                                for partial in segment_combinations for option in options]
    generated = [...]                        # 두 번째 전량 복사
    for sequence in sorted(generated, ...):  # 세 번째 전량 정렬
        if len(sequences) >= limit: break    # 자르는 건 여기

자유도를 갖는 세그먼트는 upstream_control_idx = 첫 off-ramp 셀보다 상류인 셀들뿐이다. 격자가
8셀일 때 FW_E 는 그 수가 3이라 10^3 = 1,000 이었다. **21셀에서는 8이 되어 10^8 = 1억**이다
(FW_W 는 6 -> 10^6). 2026-09-08 실측: 결정 1회가 21 GB 를 먹고 MemoryError 로 죽어
controller_status=fallback_fixed 로 떨어졌다(런 n21x15_n0, t=900, decision_wall 560.5 s).
워크스테이션이 실제로 OOM 으로 꺼졌다.

무엇으로 바꾸나. 정렬 키 sequence_score = (mean, terminal, first) 는 세 개의 **세그먼트별 합**을
사전식으로 비교한 것이다(mean = 전 세그·전 스텝 합 / 상수, terminal = 마지막 스텝 합 / 상수,
first = 첫 스텝 합 / 상수). 합이므로 세그먼트 교체에 대해 단조다 - 즉 표준 k-best 지연 곱
(세그먼트별 옵션을 자기 키로 정렬한 뒤 인덱스 벡터를 힙으로 전개)이 **같은 순서**로 내놓는다.
필요한 건 최대 limit 개뿐이라 힙 pop 도 그만큼만 한다. 곱을 만들지 않는다.

동률 처리만 원본(안정 정렬)과 다를 수 있다. 동률이면 점수가 같다는 뜻이라 후보 품질은 같다.
그리고 limit 을 이미 base 후보가 채웠으면 원본은 첫 반복에서 break 한다 - 그 경우는 아예
생성을 시작도 하지 않는다(원본은 1억 개를 만든 뒤 버렸다).

config 키: freeway.vsl_sequence_kbest (기본 true). false 면 vendor 원본 그대로 - 회귀 대조용.
          freeway.vsl_sequence_max_expand (기본 20000) 힙 pop 안전 상한.
사용: python apply_vsl_kbest_patch_20260908.py <adapter_path>
"""
import io
import sys

INSTALLER = '''def install_freeway_vsl_sequence_kbest(cfg, tuning=None) -> dict[str, float]:
    """`_freeway_vsl_sequence_candidates` 의 곱 전개를 k-best 지연 생성으로 교체한다.

    자유 세그먼트 s 개 · 세그먼트당 옵션 k 개면 원본은 k^s 를 전부 만든다. 21셀 FW_E 는
    10^8 이라 MemoryError 가 난다(2026-09-08 실측). 정렬 키가 세그먼트별 합의 사전식 비교라
    단조이므로, 힙으로 상위 limit 개만 뽑아도 순서가 같다.
    """
    section = _mapping(_mapping(tuning).get("freeway")) if tuning is not None else {}
    if "vsl_sequence_kbest" in section and not bool(section.get("vsl_sequence_kbest")):
        return {"fw_vsl_kbest_enabled": 0.0}
    max_expand = int(_as_float(section.get("vsl_sequence_max_expand"), 20000.0))
    import heapq as _heapq
    from src.controllers import wu_faithful_follower as _wff

    _cls = _wff.WuFaithfulFollower
    if getattr(_cls._freeway_vsl_sequence_candidates, "_rw_vsl_kbest", False):
        return {"fw_vsl_kbest_enabled": 1.0, "fw_vsl_kbest_patched": 0.0}
    _segment_vsl = _wff.segment_vsl
    _repair = _wff.repair_vsl_value

    def _patched_freeway_vsl_sequence_candidates(self, link, n_seg, previous, base_candidates, horizon):
        ff = self.cfg.freeway_follower
        horizon = max(1, int(horizon))
        sequences = []
        seen = set()

        def add_sequence(sequence):
            normalized = [
                [float(v) for v in vec]
                for vec in (sequence + [sequence[-1]] * max(0, horizon - len(sequence)))
            ][:horizon]
            key = tuple(tuple(round(v, 6) for v in vec) for vec in normalized)
            if key not in seen:
                seen.add(key)
                sequences.append(normalized)

        if not ff.vsl_sequence_search:
            for vec in base_candidates:
                add_sequence([[float(v) for v in vec]])
            return sequences

        vsl_set = sorted(float(v) for v in ff.vsl_set)
        if not vsl_set:
            return sequences
        vsl_max = max(vsl_set)
        max_step = max(0.0, float(ff.max_vsl_step))
        sequence_steps = max(1, min(horizon, int(ff.vsl_sequence_horizon_steps)))
        net = self.cfg.network
        # VSL 구역이 설치돼 있으면 자유 변수는 **구역 머리 셀**이고 나머지 셀은 자기 구역 머리를
        # 물려받는다. 플랜트가 실제로 그렇게 동작한다 - VSL 표지판은 정해진 자리에만 있고,
        # 표지판 사이 구간은 상류 표지판이 지시한 속도를 유지한다(2026-09-08 사용자 지시).
        # 구역이 없으면 종전 규칙(첫 off-ramp 상류)으로 떨어진다 - 비트 동일.
        _head_of = (getattr(net, "freeway_vsl_zone_head_of_cell", None) or {}).get(str(link))
        _zone_of = (getattr(net, "freeway_vsl_zone_of_cell", None) or {}).get(str(link))
        _free_z = getattr(net, "freeway_vsl_zone_free", None)
        if _head_of and _zone_of:
            head_of = [int(x) for x in _head_of]
            free_zones = set(int(z) for z in (_free_z if _free_z is not None else set(_zone_of)))
            upstream_control_idx = {i for i in range(n_seg)
                                    if head_of[i] == i and int(_zone_of[i]) in free_zones}
        else:
            head_of = list(range(n_seg))
            bottleneck_idx = {
                int(net.off_ramp_segment_index.get(off_ramp, n_seg - 1))
                for off_ramp in net.off_ramps
                if net.off_ramp_from_freeway.get(off_ramp) == link
            } or {n_seg - 1}
            upstream_control_idx = {i for i in range(max(0, min(bottleneck_idx)))}

        def sanitize_base_vector(vec):
            sanitized = []
            for index in range(n_seg):
                src = head_of[index]          # 구역 머리 값을 물려받는다(구역 없으면 자기 자신)
                value = float(vec[src]) if src < len(vec) else _segment_vsl(previous, link, src, self.cfg)
                if src not in upstream_control_idx:
                    prev = _segment_vsl(previous, link, src, self.cfg)
                    value = _repair(vsl_max, prev, self.cfg).value
                sanitized.append(float(value))
            return sanitized

        for vec in base_candidates:
            add_sequence([sanitize_base_vector([float(v) for v in vec])])
        limit = max(len(sequences), int(ff.vsl_sequence_candidate_limit))
        # base 후보가 이미 limit 을 채웠으면 원본도 첫 반복에서 break 한다 - 곱을 만들 이유가 없다.
        if len(sequences) >= limit:
            return sequences

        def segment_sequences(index):
            prev = _segment_vsl(previous, link, index, self.cfg)
            if index not in upstream_control_idx:
                repaired = _repair(vsl_max, prev, self.cfg).value
                return [[float(repaired)] * sequence_steps]
            first_values = [
                value for value in vsl_set
                if value <= prev + 1.0e-9 and prev - value <= max_step + 1.0e-9
            ]
            if not first_values:
                first_values = [_repair(prev, prev, self.cfg).value]
            out = []

            def extend(prefix):
                if len(prefix) >= sequence_steps:
                    out.append([float(v) for v in prefix])
                    return
                current = prefix[-1]
                next_values = [
                    value for value in vsl_set
                    if value <= current + 1.0e-9 and current - value <= max_step + 1.0e-9
                ]
                for value in sorted(set(next_values), reverse=True):
                    extend(prefix + [float(value)])

            for value in sorted(set(first_values), reverse=True):
                extend([float(value)])
            return out

        # 세그먼트별 옵션을 자기 키 (합, 마지막, 첫)로 정렬 - 전역 키가 이 셋의 합이라 단조다.
        # 원본은 곱을 만든 뒤 sorted(안정) 하므로 동률이면 **생성 순서**가 이긴다. 그 순서는
        # 세그먼트 0 이 바깥인 원래 옵션 인덱스의 사전식이다 - 키 4번째 성분으로 그대로 넣는다.
        # (세그먼트 안에서 동률인 옵션을 원래 인덱스 오름차순으로 두었으므로 이 성분도 단조다.)
        per_segment = []
        for i in range(n_seg):
            opts = segment_sequences(i)
            if not opts:
                opts = [[float(vsl_max)] * sequence_steps]
            ranked = sorted(range(len(opts)),
                            key=lambda j: (sum(opts[j]), opts[j][-1], opts[j][0], j))
            per_segment.append([(opts[j], j) for j in ranked])

        def key_of(vec_idx):
            s = t = f = 0.0
            orig = []
            for i, j in enumerate(vec_idx):
                o, oj = per_segment[i][j]
                s += sum(o)
                t += o[-1]
                f += o[0]
                orig.append(oj)
            return (s, t, f, tuple(orig))

        start = tuple([0] * n_seg)
        heap = [(key_of(start), start)]
        visited = {start}
        pops = 0
        while heap and len(sequences) < limit and pops < max_expand:
            _k, vec_idx = _heapq.heappop(heap)
            pops += 1
            combo = [per_segment[i][j][0] for i, j in enumerate(vec_idx)]
            # 셀은 자기 구역 머리의 값을 쓴다(구역 없으면 head_of[seg] == seg 라 종전과 같다).
            add_sequence([[float(combo[head_of[seg]][step]) for seg in range(n_seg)]
                          for step in range(sequence_steps)])
            for i in range(n_seg):
                if vec_idx[i] + 1 < len(per_segment[i]):
                    nxt = vec_idx[:i] + (vec_idx[i] + 1,) + vec_idx[i + 1:]
                    if nxt not in visited:
                        visited.add(nxt)
                        _heapq.heappush(heap, (key_of(nxt), nxt))
        return sequences

    _patched_freeway_vsl_sequence_candidates._rw_vsl_kbest = True
    _cls._freeway_vsl_sequence_candidates = _patched_freeway_vsl_sequence_candidates
    return {"fw_vsl_kbest_enabled": 1.0, "fw_vsl_kbest_patched": 1.0,
            "fw_vsl_kbest_max_expand": float(max_expand)}


'''


def main():
    path = sys.argv[1]
    s = io.open(path, encoding="utf-8").read()
    if "def install_freeway_vsl_sequence_kbest(" in s:
        print("already patched:", path)
        return

    anchor = "def install_freeway_lane_drop(cfg, tuning) -> dict[str, float]:"
    assert s.count(anchor) == 1, ("installer anchor", s.count(anchor))
    s = s.replace(anchor, INSTALLER + anchor)

    # main() 설치 순서: 세그먼트 런타임 바로 뒤.
    old_main = "    runtime_patch_metadata.update(install_freeway_segment_runtime(cfg))"
    assert s.count(old_main) == 1, ("main anchor", s.count(old_main))
    s = s.replace(old_main, old_main + "\n"
                  "    runtime_patch_metadata.update(install_freeway_vsl_sequence_kbest(cfg, tuning))")

    # 가격 워커(spawn)도 같은 클래스 패치를 되살려야 한다 - 안 심으면 워커가 1억 곱을 만든다.
    old_worker = "    out.update(install_freeway_segment_runtime(cfg))"
    assert s.count(old_worker) == 1, ("worker anchor", s.count(old_worker))
    s = s.replace(old_worker, old_worker + "\n"
                  "    out.update(install_freeway_vsl_sequence_kbest(cfg, None))")

    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print("patched:", path)


if __name__ == "__main__":
    main()
