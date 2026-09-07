# -*- coding: utf-8 -*-
"""Ver2 망 무제어(v0) 차량 레코드에서 정지선 링크 × 현시(차로군)의 지속 방류율을 잰다 — derive_lane_group_sustained_h0_20260906 의
Ver2 판. 차이: (1) 런·망·커넥터 지도·출력 경로를 인자로 받는다, (2) 대상 정지선 링크를 08-22 증거 파일이 아니라 **망의 신호두**에서 뽑는다
(Ver2 는 SC1001 서측 정지선이 32 → 127 로 옮겨져 증거 파일 링크 집합이 낡았다), (3) RAMP_EXIT 에 새 본선/연결 커넥터(10613·10771·119·120) 추가.
사용: python derive_lane_group_sustained_ver2_20260907.py [run] [inpx] [connector_map_json] [out_json]"""
import io, json, re, sys, glob, collections, statistics
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = sys.argv[1] if len(sys.argv) > 1 else "v0_nocontrol_ver2_x18_20260907"
NET = Path(sys.argv[2]) if len(sys.argv) > 2 else R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
CMAP = Path(sys.argv[3]) if len(sys.argv) > 3 else R / "outputs/movement_connector_map_ver2_20260907.json"
OUT = Path(sys.argv[4]) if len(sys.argv) > 4 else R / "outputs/lane_group_sustained_v0_ver2_20260907_v2.json"
TH = 6.0
RAMP_EXIT = {"10480", "10482", "10484", "10490", "10646", "10644", "10681", "10639", "26", "2", "24",
             "10479", "10491", "10638", "10645", "10481", "10483", "10643", "10682", "10702", "10613", "10771", "119", "120"}


def main():
    x = io.open(NET, encoding="utf-8", errors="replace").read()
    heads = {}
    for m in re.finditer(r'<signalHead [^>]*>', x):
        h = m.group(0); lane = re.search(r'lane="(\d+) (\d+)"', h); sg = re.search(r'sg="(\d+) (\d+)"', h)
        if lane and sg:
            heads[(lane.group(1), int(lane.group(2)))] = (sg.group(1), sg.group(2))
    plan = json.load(io.open(R / "outputs/signal_group_actuation_plan_v3.json", encoding="utf-8"))["controllers"]
    sg_pid = {}; native = {}
    for sc, e in plan.items():
        for pid, sgs in (e.get("phase_signal_groups") or {}).items():
            for sg in sgs:
                sg_pid[(str(sc), str(sg))] = pid
        for pid, g in (e.get("axis_green_sec") or {}).items():
            native[(str(sc), pid)] = float(g)
    links = sorted({lk for (lk, ln) in heads}, key=lambda v: int(v))
    cm = json.load(io.open(CMAP, encoding="utf-8"))
    recv = collections.defaultdict(set)
    for ap, e in cm["approaches"].items():
        sc = ap.split("|", 1)[0].replace("SC", "")
        for t in e.get("turns", []):
            fl = str(t.get("from_link")); tl = str(t.get("to_link"))
            for sg in (t.get("sg") or []):
                pid = sg_pid.get((sc, str(sg)))
                if pid:
                    recv[(fl, pid)].add(tl)
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    ts = sorted(int(re.search(r"(\d+)\.json", p).group(1)) for p in glob.glob(str(D / "state_*.json")))
    if not ts:
        raise SystemExit("state 파일이 없다: %s" % D)
    prev = None; prev_t = None; prev_stopped = None
    dep = collections.defaultdict(list); lanes_of = collections.defaultdict(set); total_link = collections.defaultdict(list)
    for t in ts:
        j = json.load(io.open(D / ("state_%06d.json" % t), encoding="utf-8"))
        recs = j["vehicle_records"].get("records") or []
        cur = {}
        for r in recs:
            cur[r["veh_no"]] = (str(r.get("link_no")), int(r.get("lane_no") or 0))
        stopped = j["local_observation"]["link_stopped_counts"]
        if prev is not None and t - prev_t == 150 and prev_t >= 900:
            by = collections.Counter()
            for v, (lk, ln) in prev.items():
                if v in cur and cur[v][0] == lk:
                    continue
                nxt = cur[v][0] if v in cur else None
                if nxt is not None and nxt in RAMP_EXIT:
                    continue
                by[(lk, ln)] += 1
            per_link_pid = collections.Counter(); per_link = collections.Counter()
            for (lk, ln), n in by.items():
                per_link[lk] += n
                hd = heads.get((lk, ln))
                if not hd:
                    continue
                pid = sg_pid.get(hd)
                if not pid:
                    continue
                per_link_pid[(lk, pid)] += n; lanes_of[(lk, pid)].add(ln)
            for lk in links:
                n_lanes_link = max(1, len({ln for (l2, ln) in heads if l2 == lk}))
                queued = float(prev_stopped.get(lk, 0)) >= max(TH, 3.0 * n_lanes_link)
                total_link[lk].append((per_link[lk], queued))
            for (lk, pid), n in per_link_pid.items():
                n_lanes_link = max(1, len({ln for (l2, ln) in heads if l2 == lk}))
                queued = float(prev_stopped.get(lk, 0)) >= max(TH, 3.0 * n_lanes_link)
                blocked = any(float(prev_stopped.get(tl, 0)) >= TH for tl in recv.get((lk, pid), ()))
                dep[(lk, pid)].append((n, queued, blocked))
        prev, prev_t, prev_stopped = cur, t, stopped
    sc_of = {lk: sc for (lk, ln), (sc, sg) in heads.items()}
    out = {"schema": "lane_group_sustained_v2", "source_run": RUN, "network": NET.name, "threshold_stopped_mean": TH,
           "definition": "큐가 선 창(창 시작 link_stopped_counts>=max(6, 3×신호두 차로))의 차로군 정지선 이탈 대수 / native 현시 녹색초 × 3600 의 중앙값. 창 = 150 s. v2: 램프·본선·분할 연결 커넥터로의 이탈 제외. Ver2: 정지선 링크 = 망 신호두 보유 링크.",
           "links": {}}
    rows = []
    for (lk, pid), vals in sorted(dep.items()):
        sc = sc_of.get(lk); g = native.get((sc, pid))
        if not g or g <= 0:
            continue
        qv = [n for n, q, b in vals if q]; fv = [n for n, q, b in vals if q and not b]; av = [n for n, q, b in vals]
        f = lambda arr: (statistics.median(arr) / g * 3600.0) if arr else None
        sus_q, sus_f, sus_all = f(qv), f(fv), f(av)
        top = sorted(av)[-max(1, len(av) // 5):] if av else []
        sus_top = statistics.mean(top) / g * 3600.0 if top else None
        out["links"].setdefault(lk, {"signal": "SC" + str(sc), "groups": {}})["groups"][pid] = {
            "lanes": sorted(lanes_of[(lk, pid)]), "native_green_sec": g, "receiving_links": sorted(recv.get((lk, pid), ())),
            "windows": len(av), "windows_queued": len(qv), "windows_free": len(fv),
            "sustained_queued_veh_h": (round(sus_q) if sus_q is not None else None),
            "sustained_free_veh_h": (round(sus_f) if sus_f is not None else None),
            "sustained_all_veh_h": (round(sus_all) if sus_all is not None else None),
            "top20pct_veh_h": (round(sus_top) if sus_top is not None else None)}
        rows.append((lk, sc, pid, len(lanes_of[(lk, pid)]), len(qv), len(fv), sus_q, sus_f, sus_all))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("링크 %d · 차로군 %d 저장 → %s" % (len(out["links"]), len(rows), OUT))
    fm = lambda v: ("%.0f" % v) if v else "-"
    print("  링크        SC     pid 차로 큐창 자유창  지속(큐)  지속(자유)  지속(전체)")
    for r in rows:
        if r[0] in ("329", "30", "72", "427", "420", "127", "32", "66", "71", "40", "403") or str(r[1]) in ("105", "1001", "1004"):
            print("  %-11s %-6s %s  %d  %3d  %3d  %8s  %8s  %8s" % (r[0], "SC" + str(r[1]), r[2], r[3], r[4], r[5], fm(r[6]), fm(r[7]), fm(r[8])))


if __name__ == "__main__":
    main()
