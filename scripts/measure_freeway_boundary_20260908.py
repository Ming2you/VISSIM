# -*- coding: utf-8 -*-
"""무제어 런 .fzp 에서 **실현된** 본선 경계조건을 잰다 — 보정용 (2026-09-08).

왜. METANET 보정이 `demand.freeway_mainline` 에 .inpx 의 **요구 수요**를 넣고 있었다. 그런데 이 망은
진입이 막힌다 — x18 에서 FW_E 는 첨두 수요 8316 vph 중 **53% 가 아예 진입하지 못한다**(2026-09-07 실측).
모형에 요구치를 먹이면 상류 셀이 실제보다 과충전되고, 적합은 그 오차를 τ·κ·δ 로 흡수한다. 그래서
문헌값과 동떨어진 파라미터가 나온다. 경계는 **실현된 유입**이어야 한다.

재는 것 (150 s = 제어 간격 창):
  mainline_in_vph : 직전 프레임에 사슬 밖(또는 망에 없음)이었다가 지금 **셀 0** 에 있는 차량 = 본선 진입
  ramp_in_vph     : 사슬 밖에서 **합류 셀**로 들어온 차량, 모형 램프 키로 합산 = 실현 램프 유입
둘 다 5 s 프레임 전이로 세므로 계수 누락이 없다.

사용: python measure_freeway_boundary_20260908.py <fzp> <mapping_json> <split_json> <out_csv> [t_min]
"""
import collections
import io
import json
import sys


def main():
    fzp, mapj, splitj, outc = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    t_min = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    M = json.load(io.open(mapj, encoding="utf-8"))
    fl = M["freeway_model_links"]
    chain, meta = {}, {}
    for d, spec in fl.items():
        for lk, off in zip(spec["chain_links"], spec["chain_offsets_m"]):
            chain[str(lk)] = (d, float(off))
        n = len(spec["segment_lanes"])
        meta[d] = {"seglen": float(spec["length_m"]) / n, "n": n}
    split = json.load(io.open(splitj, encoding="utf-8"))
    ramp_of_cell = {}
    for r in split["on_ramps"]:
        ramp_of_cell[(r["direction"], int(r["segment_index"]))] = r["legacy_group"]

    WIN = 150.0
    main_in = collections.Counter()      # (dir, wid) -> veh
    ramp_in = collections.Counter()      # (ramp, wid) -> veh
    prev, prev_t = {}, None
    cur, tcur = {}, None

    def flush(t):
        if prev_t is None or t - prev_t > 5.001 or t < t_min:
            return
        wid = int((t - t_min) // WIN)
        for v, c2 in cur.items():
            if c2 is None:
                continue
            d2, cp = c2
            c1 = prev.get(v, "new")
            if c1 is not None and c1 != "new" and c1[0] == d2:
                continue                       # 이미 같은 사슬 위에 있었다
            si = min(meta[d2]["n"] - 1, int(cp // meta[d2]["seglen"]))
            if si == 0:
                main_in[(d2, wid)] += 1
            else:
                rk = ramp_of_cell.get((d2, si))
                if rk:
                    ramp_in[(rk, wid)] += 1

    with io.open(fzp, encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line or line[0] in "*$":
                continue
            p = line.split(";")
            if len(p) < 7:
                continue
            try:
                t = float(p[0])
            except ValueError:
                continue
            if tcur is None:
                tcur = t
            if t != tcur:
                flush(tcur)
                prev, prev_t = cur, tcur
                cur, tcur = {}, t
            c = chain.get(p[2])
            if c is None:
                cur[p[1]] = None
                continue
            try:
                cur[p[1]] = (c[0], c[1] + float(p[4]))
            except ValueError:
                cur[p[1]] = None
        flush(tcur)

    wids = sorted({w for _, w in list(main_in) + list(ramp_in)})
    with io.open(outc, "w", encoding="utf-8", newline="") as g:
        g.write("t_start,kind,key,veh_h" + chr(10))
        for w in wids:
            t0 = t_min + w * WIN
            for d in fl:
                g.write("%.0f,mainline,%s,%.1f%s" % (t0, d, main_in[(d, w)] * 3600.0 / WIN, chr(10)))
            for rk in sorted({r for r, _ in ramp_in}):
                g.write("%.0f,ramp,%s,%.1f%s" % (t0, rk, ramp_in[(rk, w)] * 3600.0 / WIN, chr(10)))
    print("창 %d개 → %s" % (len(wids), outc))
    for d in fl:
        vals = [main_in[(d, w)] * 3600.0 / WIN for w in wids]
        print("  %s 본선 진입 중앙 %.0f · 최대 %.0f vph" % (d, sorted(vals)[len(vals) // 2], max(vals)))
    for rk in sorted({r for r, _ in ramp_in}):
        vals = [ramp_in[(rk, w)] * 3600.0 / WIN for w in wids]
        print("  %-6s 램프 유입 중앙 %.0f · 최대 %.0f vph" % (rk, sorted(vals)[len(vals) // 2], max(vals)))


if __name__ == "__main__":
    main()
