# -*- coding: utf-8 -*-
"""O4 (2026-10-24 rmcause): read-only FZP scan of the departures from the four on-ramp feeder links.

Usage: python -B o4_fzp_split.py <tag> <fzp_path> <out_dir>

For feeder links 68 (-> 10681 / 10772), 31 (-> 10484 / ...), 129 (-> 10490 / ...), 70 (-> 10639 / ...):
records each departure (t_detect, next link) when a vehicle's previous record was on the feeder link and its
current record is on another link. Also records first entries onto each feeder link (t, previous link or 0).
Reads only the FZP. Writes only <out_dir>/<tag>_split.json.
"""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prio import below_normal

FEED = {b'68': 68, b'31': 31, b'129': 129, b'70': 70}


def main():
    below_normal()
    tag, path, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    t0 = time.time()
    dep = {v: [] for v in FEED.values()}
    ent = {v: [] for v in FEED.values()}
    last = {}   # veh -> link bytes (only kept while on a feeder link or one step after)
    prevlink = {}
    cur_tb, cur_t = None, None
    h = hashlib.sha256()
    n = 0
    with open(path, 'rb') as f:
        for raw in f:
            h.update(raw)
            c0 = raw[:1]
            if c0 in (b'$', b'*', b'\r', b'\n') or not raw.strip():
                continue
            parts = raw.split(b';', 4)
            tb = parts[0]
            if tb != cur_tb:
                try:
                    cur_t = float(tb)
                except ValueError:
                    continue
                cur_tb = tb
            n += 1
            vb, lb = parts[1], parts[2]
            pl = prevlink.get(vb)
            fl = FEED.get(lb)
            if pl is not None and pl != lb:
                pf = FEED.get(pl)
                if pf is not None:
                    dep[pf].append((cur_t, int(lb)))
            if fl is not None and pl != lb:
                ent[fl].append((cur_t, int(pl) if pl is not None else 0))
            prevlink[vb] = lb
    out = {'tag': tag, 'fzp': path, 'fzp_sha256': h.hexdigest(), 'rows_used': n,
           'departures': {str(k): v for k, v in dep.items()}, 'entries': {str(k): v for k, v in ent.items()},
           'elapsed_s': time.time() - t0}
    os.makedirs(out_dir, exist_ok=True)
    tmp = os.path.join(out_dir, tag + '_split.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(out, g)
    os.replace(tmp, os.path.join(out_dir, tag + '_split.json'))
    print('done', tag, n, round(time.time() - t0, 1), flush=True)


if __name__ == '__main__':
    main()
