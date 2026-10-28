# -*- coding: utf-8 -*-
"""O4 (2026-10-24 rmcause): read-only FZP event scan for the four FW_E on-ramp connectors.

Usage: python -B o4_fzp.py <tag> <fzp_path> <out_dir>

Records, from one VISSIM vehicle record file (5 s frames, t = 5k + 0.1):
- merge events: a vehicle whose previous record was on connector C and whose current record is on
  another link (the mainline) -> (t_detect, lane on C, new link)
- connector entry events (first record on C) -> (t, lane)
- meter-head passage events (pos crosses the signal-head position on C) -> (t, lane)
- connector stock snapshots at frames t = 150 k + 0.1 (by lane, pre-head / post-head, speed < 15 km/h)
- mainline crossing events at one line just upstream of each merge -> (t, lane)
Reads only the FZP. Writes only <out_dir>/<tag>.json. No VISSIM, no COM.
"""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal

# connector -> (head position m, length m, landing link)  [inpx 3de889f0 signal heads 90030897-90030901, links]
CONN = {10639: (314.83469380887993, 408.45, 2), 10681: (290.72003141146473, 437.52, 2),
        10490: (272.60355928160652, 368.38, 119), 10484: (377.11076285480539, 541.91, 24)}
# upstream mainline line per connector: (link, pos m, upstream link feeding that link)
LINE = {10639: (2, 1900.0, 10699), 10681: (2, 2250.0, 10699), 10490: (119, 340.0, 10613), 10484: (24, 110.0, 10702)}
QSPEED = 15.0
CONN_B = {str(c).encode(): c for c in CONN}
MAIN_B = {str(l).encode(): l for l in {v[0] for v in LINE.values()}}


def main():
    below_normal()
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    merges = {c: [] for c in CONN}
    entries = {c: [] for c in CONN}
    heads = {c: [] for c in CONN}
    land = {c: {} for c in CONN}
    snaps = {}
    cross = {c: [] for c in CONN}
    on_conn = {}     # veh bytes -> (conn, lane, pos)
    main_last = {}   # veh bytes -> (link, pos)
    cur_tb = None
    cur_t = None
    snap_now = False
    snap_acc = None
    h = hashlib.sha256()
    nrows = 0
    with open(path, 'rb') as f:
        for raw in f:
            h.update(raw)
            c0 = raw[:1]
            if c0 in (b'$', b'*', b'\r', b'\n') or not raw.strip():
                continue
            parts = raw.split(b';', 7)
            tb = parts[0]
            if tb != cur_tb:
                try:
                    tnew = float(tb)
                except ValueError:
                    continue
                if snap_now and snap_acc is not None:
                    snaps['%.1f' % cur_t] = snap_acc
                cur_tb, cur_t = tb, tnew
                k = (cur_t - 0.1) / 150.0
                snap_now = abs(k - round(k)) < 1e-6 and cur_t > 1.0
                snap_acc = {str(c): {} for c in CONN} if snap_now else None
            nrows += 1
            vb = parts[1]
            lb = parts[2]
            c = CONN_B.get(lb)
            if c is not None:
                lane = int(parts[3]); pos = float(parts[4])
                prev = on_conn.get(vb)
                if prev is None or prev[0] != c:
                    entries[c].append((cur_t, lane))
                hp = CONN[c][0]
                if pos >= hp and (prev is None or prev[0] != c or prev[2] < hp):
                    heads[c].append((cur_t, lane))
                on_conn[vb] = (c, lane, pos)
                main_last.pop(vb, None)
                if snap_now:
                    spd = float(parts[6])
                    d = snap_acc[str(c)].setdefault(str(lane), [0, 0, 0])
                    if pos < hp:
                        d[0] += 1
                    else:
                        d[1] += 1
                    if spd < QSPEED:
                        d[2] += 1
                continue
            prev = on_conn.pop(vb, None)
            link = None
            if prev is not None:
                link = int(lb)
                merges[prev[0]].append((cur_t, prev[1], link))
                land[prev[0]][str(link)] = land[prev[0]].get(str(link), 0) + 1
            m = MAIN_B.get(lb)
            if m is not None:
                pos = float(parts[4]); lane = int(parts[3])
                pl = main_last.get(vb)
                for cc, (ll, X, up) in LINE.items():
                    if ll != m:
                        continue
                    if pl is not None and pl[0] == m and pl[1] < X <= pos:
                        cross[cc].append((cur_t, lane))
                    elif pl is not None and pl[0] == up and pos >= X:
                        cross[cc].append((cur_t, lane))
                main_last[vb] = (m, pos)
            else:
                # remember the upstream feeder links so a one-step jump past the line still counts
                if lb in (b'10699', b'10613', b'10702'):
                    main_last[vb] = (int(lb), 0.0)
                else:
                    main_last.pop(vb, None)
    if snap_now and snap_acc is not None:
        snaps['%.1f' % cur_t] = snap_acc
    out = {'tag': tag, 'fzp': path, 'fzp_sha256': h.hexdigest(), 'rows_used': nrows,
           'conn': {str(k): v for k, v in CONN.items()}, 'line': {str(k): v for k, v in LINE.items()},
           'qspeed': QSPEED, 'merges': {str(k): v for k, v in merges.items()},
           'entries': {str(k): v for k, v in entries.items()}, 'heads': {str(k): v for k, v in heads.items()},
           'landing_links': {str(k): v for k, v in land.items()}, 'snapshots': snaps,
           'cross': {str(k): v for k, v in cross.items()}, 'elapsed_s': time.time() - t0}
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, tag + '.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g)
    os.replace(tmp, os.path.join(out_dir, tag + '.json'))
    print('done', tag, nrows, round(time.time() - t0, 1), flush=True)


if __name__ == '__main__':
    main()
