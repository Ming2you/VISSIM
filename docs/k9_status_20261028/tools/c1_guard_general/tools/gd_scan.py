# -*- coding: utf-8 -*-
"""gd_scan.py (guard/general DATA, 2026-10-27 KST) — read-only FZP scan of inventory segments, 5 s frames.

Usage:
  python -B gd_scan.py run  <inventory.json> <out_dir>            (12 FZPs, one at a time under heavy.lock)
  python -B gd_scan.py one  <inventory.json> <fzp> <out_npz>      (one FZP, NO lock; self-test only)

Segments: exactly the inv_occ.py list (controlled-phase head lanes, feeder lanes, meter pre-head lanes, meter approach
lanes, D5) + off-ramp landing lanes (landing .. landing + landing_to_server_end) + freeway diverge-lane windows.
Per frame and segment (vehicles with link == seg link, lane == seg lane, from_m <= Pos <= to_m; Pos = front):
  n      vehicle count
  lsum   sum of (Length + 1.51 m)
  nq     vehicles with Speed < 5 km/h
  flags  bit0 S0 = a vehicle with Speed < 5 km/h has Pos <= from_m + 12 m (whole segment if shorter)
         bit1 S  = S0 and, walking downstream from the most-upstream such vehicle, clear gaps
                   (leader Pos - leader Length - follower Pos) <= 20 m reach Pos >= to_m - max(20, 0.2 * len);
                   segments with len <= 12 m: S = S0
Freeway windows (diverge lane, [diverge - 500, diverge]): n500, mean speed, n of Speed < 20 km/h in last 100 m.
Definitions were fixed before this scan (LOG_GENERAL 17:10 KST). No VISSIM, no COM. Writes only out files + own lock.
"""
import bisect
import hashlib
import json
import os
import sys
import time

import numpy as np

LOCK = os.environ.get('GD_SELFTEST_LOCK') or 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
OWNER = 'c1_guard_general_data'
GAP = 1.51          # FZP median standstill gap (inventory spacing scan)
ZONE = 12.0
SLOW = 5.0
CHAIN_GAP = 20.0
FW_SLOW = 20.0
NF = 1810

RUNS = [
    ('B_s31', 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp'),
    ('VA_s31', 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp'),
    ('NC3_s31', 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp'),
    ('VSL_s31', 'D:/VISSIM_runs/20261027_vsl_v3c3/s31/run/vissim_eval/baseline_s31_v3c3vsl_001.fzp'),
    ('B_s41', 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp'),
    ('VA_s41', 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp'),
    ('NC3_s41', 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp'),
    ('VSL_s41', 'D:/VISSIM_runs/20261027_vsl_v3c3/s41/run/vissim_eval/baseline_s41_v3c3vsl_001.fzp'),
    ('B_s43', 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp'),
    ('VA_s43', 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp'),
    ('NC3_s43', 'D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/vissim_eval/baseline_s43_v3c3nc_001.fzp'),
    ('VSL_s43', 'D:/VISSIM_runs/20261027_vsl_v3c3/s43/run/vissim_eval/baseline_s43_v3c3vsl_001.fzp'),
]


def kst():
    return time.strftime('%Y-%m-%d %H:%M:%S KST', time.localtime())


def build_segments(inv):
    seg = []
    for a in inv['approach_lanes']:
        if a['role'] != 'controlled_phase':
            continue
        seg.append(dict(id='A:%s:%s:%s' % (a['link'], a['lane'], a['sg']), kind='approach_lane', group='%s:%s' % (a['sc'], a['link']),
                        link=a['link'], lane=int(a['lane']), from_m=float(a['segment_start_m']), to_m=float(a['head_pos_m']),
                        part=a['part'], sc=a['sc'], sg=a['sg'], phases=a['phases'],
                        codex=bool((a.get('codex_usg') or {}).get('included'))))
    for f in inv['feeders']:
        for ln in range(1, f['link_lanes'] + 1):
            seg.append(dict(id='F:%s:%s' % (f['link'], ln), kind='feeder_lane', group='F:%s' % f['link'], link=f['link'],
                            lane=ln, from_m=float(f['from_m']), to_m=float(f['to_m']), part=f['part'], servers=f['servers'],
                            upstream_stopline=any(b['kind'] == 'upstream_stopline' for b in f['boundaries']),
                            freeway_spill=f['freeway_spill']))
    for name, m in inv['meters'].items():
        for h in m['heads']:
            seg.append(dict(id='M:%s:%s' % (name, h['lane']), kind='meter_prehead_lane', group='M:' + name, link=m['connector'],
                            lane=int(h['lane']), from_m=0.0, to_m=float(h['head_pos_m']), meter=name, road=m['road']))
        a = m['approach_segment']
        for ln in a['lanes']:
            seg.append(dict(id='MA:%s:%s' % (name, ln), kind='meter_approach_lane', group='MA:' + name, link=a['link'],
                            lane=int(ln), from_m=float(a['from_m']), to_m=float(a['to_m']), meter=name, road=m['road']))
    seg.append(dict(id='D5:129:1', kind='special', group='D5', link='129', lane=1, from_m=239.38, to_m=299.99,
                    note='10491 landing to 10490 diverge (METER_NEXT2 D5)'))
    for f in inv['feeders']:
        if not f['freeway_spill']:
            continue
        ends = {}
        for l in f['landings']:
            for ln in l['on_lanes']:
                k = (l['on_link'], int(ln))
                e = float(l['landing_pos_m']) + float(l['landing_to_server_end_m'])
                ends[k] = (float(l['landing_pos_m']), max(e, ends.get(k, (0, 0))[1]))
        for (lk, ln), (a0, e) in sorted(ends.items()):
            seg.append(dict(id='L:%s:%s:%s' % (f['link'], lk, ln), kind='offramp_landing_lane', group='L:%s' % f['link'], link=lk,
                            lane=ln, from_m=a0, to_m=e, offramp=f['link'], road=f['freeway_spill']['road']))
    fws = []
    for f in inv['feeders']:
        if f['freeway_spill']:
            fs = f['freeway_spill']
            fws.append(dict(id='W:%s' % f['link'], offramp=f['link'], link=fs['link'], lane=int(fs['lane']),
                            diverge=float(fs['diverge_pos_m']), road=fs['road']))
    return seg, fws


def acquire(job):
    waited = 0.0
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            time.sleep(2.0)
            waited += 2.0
            if waited > 8 * 3600:
                raise SystemExit('lock wait > 8 h')
            continue
        info = {'owner': OWNER, 'pid': os.getpid(), 'started_kst': kst(), 'job': job}
        os.write(fd, json.dumps(info).encode('utf-8'))
        os.close(fd)
        return info, waited


def release(info):
    try:
        cur = json.loads(open(LOCK, 'rb').read().decode('utf-8'))
    except Exception:
        return 'lock unreadable or gone'
    if cur.get('owner') == OWNER and cur.get('pid') == info['pid']:
        os.remove(LOCK)
        return 'released'
    return 'not ours: ' + json.dumps(cur)


def scan(fzp, seg, fws):
    keys = {}
    seg_by_key = {}
    for i, s in enumerate(seg):
        k = (s['link'].encode(), str(s['lane']).encode())
        keys.setdefault(k, len(keys))
        seg_by_key.setdefault(keys[k], []).append(i)
    fw_by_key = {}
    for j, w in enumerate(fws):
        k = (w['link'].encode(), str(w['lane']).encode())
        keys.setdefault(k, len(keys))
        fw_by_key.setdefault(keys[k], []).append(j)
    S = len(seg)
    W = len(fws)
    cnt = np.zeros((S, NF), np.uint16)
    lsum = np.zeros((S, NF), np.float32)
    nq = np.zeros((S, NF), np.uint16)
    flg = np.zeros((S, NF), np.uint8)
    w_n = np.zeros((W, NF), np.uint16)
    w_v = np.full((W, NF), np.nan, np.float32)
    w_s = np.zeros((W, NF), np.uint16)
    times = []
    h = hashlib.sha256()
    bucket = {}
    rows = 0
    rows_kept = 0
    fr = -1
    segs_l = [(s['from_m'], s['to_m'], s['to_m'] - s['from_m']) for s in seg]

    def flush(f):
        for k, vs in bucket.items():
            vs.sort()
            poss = [v[0] for v in vs]
            for i in seg_by_key.get(k, ()):
                a, b, L = segs_l[i]
                lo = bisect.bisect_left(poss, a - 1e-6)
                hi = bisect.bisect_right(poss, b + 1e-6)
                if hi <= lo:
                    continue
                sub = vs[lo:hi]
                cnt[i, f] = hi - lo
                lsum[i, f] = sum(v[2] for v in sub) + GAP * (hi - lo)
                nq[i, f] = sum(1 for v in sub if v[1] < SLOW)
                zone_end = a + ZONE
                j0 = -1
                for j, v in enumerate(sub):
                    if v[0] > zone_end:
                        break
                    if v[1] < SLOW:
                        j0 = j
                        break
                if j0 < 0:
                    continue
                fl = 1
                if L <= ZONE:
                    fl |= 2
                else:
                    cur = sub[j0]
                    for nxt in sub[j0 + 1:]:
                        if nxt[0] - nxt[2] - cur[0] <= CHAIN_GAP:
                            cur = nxt
                        else:
                            break
                    if cur[0] >= b - max(CHAIN_GAP, 0.2 * L):
                        fl |= 2
                flg[i, f] = fl
            for j in fw_by_key.get(k, ()):
                d = fws[j]['diverge']
                lo = bisect.bisect_left(poss, d - 500.0)
                hi = bisect.bisect_right(poss, d + 1e-6)
                if hi > lo:
                    sub = vs[lo:hi]
                    w_n[j, f] = hi - lo
                    w_v[j, f] = sum(v[1] for v in sub) / (hi - lo)
                    w_s[j, f] = sum(1 for v in sub if v[0] >= d - 100.0 and v[1] < FW_SLOW)
        bucket.clear()

    header = False
    cur_t = None
    with open(fzp, 'rb') as g:
        for raw in g:
            h.update(raw)
            if not header:
                if raw.startswith(b'$VEHICLE:'):
                    header = True
                continue
            p = raw.split(b';', 11)
            if len(p) < 11:
                continue
            t = p[0]
            if t != cur_t:
                if cur_t is not None:
                    flush(fr)
                fr += 1
                if fr >= NF:
                    raise SystemExit('too many frames')
                times.append(float(t))
                cur_t = t
            rows += 1
            k = keys.get((p[2], p[3]))
            if k is None:
                continue
            rows_kept += 1
            bucket.setdefault(k, []).append((float(p[4]), float(p[6]), float(p[10])))
        if cur_t is not None:
            flush(fr)
    nfr = fr + 1
    return dict(cnt=cnt[:, :nfr], lsum=lsum[:, :nfr], nq=nq[:, :nfr], flg=flg[:, :nfr], w_n=w_n[:, :nfr], w_v=w_v[:, :nfr],
                w_s=w_s[:, :nfr], times=np.array(times, np.float64)), dict(rows=rows, rows_kept=rows_kept, frames=nfr,
                                                                            fzp_sha256=h.hexdigest())


def save(out_npz, arrs, meta):
    tmp = out_npz + '.tmp.npz'
    np.savez_compressed(tmp, **arrs)
    os.replace(tmp, out_npz)
    meta['npz_sha256'] = hashlib.sha256(open(out_npz, 'rb').read()).hexdigest()
    mp = out_npz[:-4] + '.meta.json'
    with open(mp + '.tmp', 'w', encoding='utf-8') as g:
        json.dump(meta, g, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(mp + '.tmp', mp)
    return meta['npz_sha256']


def main():
    mode = sys.argv[1]
    inv_p = sys.argv[2]
    inv = json.loads(open(inv_p, 'rb').read().decode('utf-8'))
    inv_sha = hashlib.sha256(open(inv_p, 'rb').read()).hexdigest()
    seg, fws = build_segments(inv)
    tool_sha = hashlib.sha256(open(__file__, 'rb').read()).hexdigest()
    if mode == 'one':
        fzp, out = sys.argv[3], sys.argv[4]
        t0 = time.time()
        arrs, m = scan(fzp, seg, fws)
        m.update(run='selftest', fzp_name=os.path.basename(fzp), inventory_sha256=inv_sha, tool_sha256=tool_sha,
                 seg_ids=[s['id'] for s in seg], fw_ids=[w['id'] for w in fws], scan_s=time.time() - t0)
        print('selftest', save(out, arrs, m), m['frames'], m['rows'])
        return
    out_dir = sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'segments.json'), 'w', encoding='utf-8') as g:
        json.dump(dict(inventory_sha256=inv_sha, tool_sha256=tool_sha, segments=seg, fws=fws), g, ensure_ascii=False, sort_keys=True)
    for run, fzp in RUNS:
        out = os.path.join(out_dir, run + '.npz')
        mp = out[:-4] + '.meta.json'
        if os.path.exists(out) and os.path.exists(mp):
            try:
                mm = json.load(open(mp, encoding='utf-8'))
                if mm.get('tool_sha256') == tool_sha and mm.get('inventory_sha256') == inv_sha and \
                        hashlib.sha256(open(out, 'rb').read()).hexdigest() == mm.get('npz_sha256'):
                    print('skip', run, flush=True)
                    continue
            except Exception:
                pass
        info, waited = acquire('gd_scan ' + run)
        t0 = time.time()
        try:
            print('start', run, kst(), 'waited', waited, flush=True)
            arrs, m = scan(fzp, seg, fws)
            m.update(run=run, fzp_name=os.path.basename(fzp), inventory_sha256=inv_sha, tool_sha256=tool_sha,
                     seg_ids=[s['id'] for s in seg], fw_ids=[w['id'] for w in fws],
                     lock=dict(waited_s=waited, held_s=time.time() - t0, acquired_kst=info['started_kst']))
            sha = save(out, arrs, m)
            print('done', run, kst(), 'frames', m['frames'], 'rows', m['rows'], 'held', round(time.time() - t0, 1), sha, flush=True)
        finally:
            print('lock', release(info), kst(), flush=True)
        time.sleep(25.0)
    print('all done', kst(), flush=True)


if __name__ == '__main__':
    main()
