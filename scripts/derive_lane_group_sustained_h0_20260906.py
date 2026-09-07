# -*- coding: utf-8 -*-
"""무제어(h0, lcd1000) 차량 레코드에서 정지선 링크 × 현시(차로군)의 **지속 방류율**을 잰다.

왜. movement_saturation_measured_20260822.json 은 (1) 다른 망(lcd200 이전)에서, (2) 상위 N 주기 평균으로 재서 막힌 접근로를
과대평가한다(SC1002 E 직진군 1573 vs plant 지속 ~760). 그 값이 씨앗이 되면 국소비용 지형이 평평해져 p3 몰빵이 p4 확대와
같은 값이 된다. 큐가 선 창에서 실제로 빠진 대수 / 그 현시 녹색초 = 그 조건에서의 방류 용량이다.

방법. state_t 와 state_{t+150} 의 records 에서 링크 L 에 있다가 사라진 차량을 차로별로 센다(이탈). 차로 → SG 는 .inpx 신호두,
SG → 현시는 actuation plan 의 phase_signal_groups, 현시 녹색은 native axis_green_sec. 신호두 없는 차로(우회전 자유)는 뺀다.
큐 조건: 창 시작 시 link_stopped_counts[L] >= threshold. 출력: outputs/lane_group_sustained_h0_20260906.json"""
import io, json, re, sys, glob, collections, statistics
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = "h0_nocontrol_lcd1000_x18_20260906"
NET = R / "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc_lcd1000.inpx"
TH = 6.0

def main():
    x = io.open(NET, encoding="utf-8", errors="replace").read()
    heads = {}  # (link, lane) -> (sc, sg)
    for m in re.finditer(r'<signalHead [^>]*>', x):
        h = m.group(0); lane = re.search(r'lane="(\d+) (\d+)"', h); sg = re.search(r'sg="(\d+) (\d+)"', h)
        if lane and sg:
            heads[(lane.group(1), int(lane.group(2)))] = (sg.group(1), sg.group(2))
    plan = json.load(io.open(R / "outputs/signal_group_actuation_plan_v3.json", encoding="utf-8"))["controllers"]
    sg_pid = {}  # (sc, sg) -> pid
    native = {}  # (sc, pid) -> green
    for sc, e in plan.items():
        for pid, sgs in (e.get("phase_signal_groups") or {}).items():
            for sg in sgs:
                sg_pid[(str(sc), str(sg))] = pid
        for pid, g in (e.get("axis_green_sec") or {}).items():
            native[(str(sc), pid)] = float(g)
    ev = json.load(io.open(R / "outputs/movement_saturation_measured_20260822.json", encoding="utf-8"))["lane_groups"]
    links = sorted({str(g["stopline_link"]) for g in ev})
    # 차로군 → 수신 plant 링크(커넥터 지도 turns 의 to_link; sg 로 현시 매칭). 하류가 막힌 창은 포화가 아니라 spillback 제한이다.
    cm = json.load(io.open(R / "outputs/movement_connector_map_20260824.json", encoding="utf-8"))
    recv = collections.defaultdict(set)  # (link, pid) -> {to_link}
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
    prev = None; prev_t = None; prev_stopped = None
    dep = collections.defaultdict(list)  # (link,pid) -> [(departures, queued)] per window
    lanes_of = collections.defaultdict(set)
    total_link = collections.defaultdict(list)
    for t in ts:
        j = json.load(io.open(D / ("state_%06d.json" % t), encoding="utf-8"))
        recs = j["vehicle_records"].get("records") or []
        cur = {}
        for r in recs:
            lk = str(r.get("link_no"))
            # 모든 링크를 담는다 — 다음 링크(정지선 이탈 판정)를 알아야 한다. 차로군 집계는 증거 링크만.
            cur[r["veh_no"]] = (lk, int(r.get("lane_no") or 0))
        stopped = j["local_observation"]["link_stopped_counts"]
        if prev is not None and t - prev_t == 150 and prev_t >= 900:
            # v2: 정지선 이탈만 센다 — 다음 링크가 그 차로군의 수신 링크(커넥터 지도 to_link)여야 한다. 링크 32·31·68 처럼 중간에서
            # 램프로 빠지는 차량(다음 링크 26·2 등)은 방류가 아니다(v1 은 이것을 세어 32 p3 가 5520 으로 부풀었다).
            # 사라진 차량(망 밖)은 수신 링크 집합이 비어 있는(경계 유출) 차로군에서만 방류로 센다.
            # v2b: 레코드의 다음 링크는 커넥터 번호일 수 있어 "수신 링크 집합" 매칭은 정상 방류까지 뺀다. 부풀림의 원인은 램프 유출뿐이므로
            # 다음 링크가 램프 커넥터(미터·off-ramp)·본선 링크이면 제외하고 나머지는 방류로 센다.
            RAMP_EXIT = {"10480", "10482", "10484", "10490", "10646", "10644", "10681", "10639", "26", "2", "24",
                         "10479", "10491", "10638", "10645", "10481", "10483", "10643", "10682", "10702"}
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
            # 큐 판정은 차로수에 비례: 3차로 링크에 정지 6대는 과도적이다(SC105 N 3차로가 150/h 로 잡혔다). 링크 신호두 차로수 × 3 (최소 TH).
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
    sc_of = {}
    for (lk, ln), (sc, sg) in heads.items():
        sc_of[lk] = sc
    out = {"schema": "lane_group_sustained_v1", "source_run": RUN, "network": NET.name, "threshold_stopped_mean": TH,
           "definition": "큐가 선 창(창 시작 link_stopped_counts>=threshold)의 차로군 이탈 대수 / native 현시 녹색초 × 3600 의 중앙값. 창 = 150 s = 1 주기.",
           "links": {}}
    rows = []
    for (lk, pid), vals in sorted(dep.items()):
        sc = sc_of.get(lk); g = native.get((sc, pid))
        if not g or g <= 0:
            continue
        qv = [n for n, q, b in vals if q]; fv = [n for n, q, b in vals if q and not b]; av = [n for n, q, b in vals]
        cyc = 150.0 / 150.0
        f = lambda arr: (statistics.median(arr) / (g * cyc) * 3600.0) if arr else None
        sus_q, sus_f, sus_all = f(qv), f(fv), f(av)
        top = sorted(av)[-max(1, len(av) // 5):] if av else []
        sus_top = statistics.mean(top) / (g * cyc) * 3600.0 if top else None
        out["links"].setdefault(lk, {"signal": "SC" + str(sc), "groups": {}})["groups"][pid] = {
            "lanes": sorted(lanes_of[(lk, pid)]), "native_green_sec": g, "receiving_links": sorted(recv.get((lk, pid), ())),
            "windows": len(av), "windows_queued": len(qv), "windows_free": len(fv),
            "sustained_queued_veh_h": (round(sus_q) if sus_q is not None else None),
            "sustained_free_veh_h": (round(sus_f) if sus_f is not None else None),
            "sustained_all_veh_h": (round(sus_all) if sus_all is not None else None),
            "top20pct_veh_h": (round(sus_top) if sus_top is not None else None)}
        rows.append((lk, sc, pid, len(lanes_of[(lk, pid)]), len(qv), len(fv), sus_q, sus_f, sus_all))
    out["schema"] = "lane_group_sustained_v2"
    out["definition"] += " v2: 정지선 이탈만(다음 링크가 차로군 수신 링크). 중간 램프 유출 제외."
    io.open(R / "outputs/lane_group_sustained_h0_20260906_v2.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("링크 %d · 차로군 %d 저장" % (len(out["links"]), len(rows)))
    print("  링크        SC     pid 차로 큐창 자유창  지속(큐)  지속(자유)  지속(전체)")
    fm = lambda v: ("%.0f" % v) if v else "-"
    for r in rows:
        if r[0] in ("329", "30", "72", "427", "420", "32", "66", "1220018401", "1220011503", "1220014201", "40", "403", "1220007200", "1220007001", "416") or str(r[1]) == "105":
            print("  %-11s %-6s %s  %d  %3d  %3d  %8s  %8s  %8s" % (r[0], "SC" + str(r[1]), r[2], r[3], r[4], r[5], fm(r[6]), fm(r[7]), fm(r[8])))

if __name__ == "__main__":
    main()
