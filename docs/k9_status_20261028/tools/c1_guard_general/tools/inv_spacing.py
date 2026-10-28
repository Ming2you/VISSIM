# -*- coding: utf-8 -*-
"""inv_spacing.py (guard/general, 2026-10-27 KST) — read-only FZP scan: standstill front-to-front spacing.

Usage: python -B inv_spacing.py <fzp> <net_facts.json> <out.json>
- Takes the shared heavy lock D:/VISSIM-merge/k8_gate_trees/heavy.lock (exclusive create, retry every 2 s),
  scans ONE FZP, writes <out.json>, deletes only its own lock.
- Definition (fixed before the scan): in every FZP frame, vehicles on the same link+lane are sorted by Pos (front
  position). For each adjacent pair (follower, leader) with BOTH speeds < 1.0 km/h (the controller's stopped
  threshold, vehicle_records/stopped_threshold_kph), spacing d = Pos_leader - Pos_follower (= leader length + gap),
  gap = d - Length_leader. Summary = count, mean, percentiles of d; recommended jam spacing = median d over all
  stopped pairs (all links). Also: by link behaviour type, for listed links, vehicle-length distribution.
No VISSIM, no COM. Writes only <out.json> and the lock file.
"""
import hashlib
import json
import math
import os
import sys
import time
from array import array
from collections import defaultdict

LOCK = os.environ.get('INV_SELFTEST_LOCK') or 'D:/VISSIM-merge/k8_gate_trees/heavy.lock'
OWNER = 'c1_guard_general'
FOCUS = ['127', '129', '10491', '26', '70', '71', '10638', '10481', '10483', '10682', '10643', '124', '121', '126', '31',
         '32', '68', '69', '66', '21', '174', '10480', '10482', '10646', '10644', '10639', '10681', '10490', '10484',
         '29', '37', '40', '30', '39', '46', '47', '52', '57', '62', '72', '427', '329', '403', '425']
BIN = 0.1
NBIN = 400   # 0..40 m


def kst():
    return time.strftime('%Y-%m-%d %H:%M:%S KST', time.localtime())


def acquire(job):
    waited = 0.0
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            time.sleep(2.0)
            waited += 2.0
            if waited > 6 * 3600:
                raise SystemExit('lock wait > 6 h')
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


class Acc:
    def __init__(self):
        self.n = 0
        self.s = 0.0
        self.s2 = 0.0
        self.hist = [0] * (NBIN + 1)
        self.gap_hist = [0] * (NBIN + 1)
        self.lead_len_s = 0.0
        self.vals = array('d')
        self.gaps = array('d')

    def add(self, d, gap, lead_len):
        self.vals.append(d)
        self.gaps.append(gap)
        self.n += 1
        self.s += d
        self.s2 += d * d
        self.hist[min(NBIN, max(0, int(d / BIN)))] += 1
        self.gap_hist[min(NBIN, max(0, int(max(gap, 0.0) / BIN)))] += 1
        self.lead_len_s += lead_len

    def pct(self, hist, q):
        tot = sum(hist)
        if not tot:
            return None
        k = q * tot
        c = 0
        for i, v in enumerate(hist):
            c += v
            if c >= k:
                return (i + 0.5) * BIN
        return NBIN * BIN

    @staticmethod
    def exact(vals, q):
        v = sorted(vals)
        if not v:
            return None
        k = q * (len(v) - 1)
        i = int(math.floor(k))
        j = min(i + 1, len(v) - 1)
        return v[i] + (v[j] - v[i]) * (k - i)

    def summary(self):
        if not self.n:
            return {'pairs': 0}
        m = self.s / self.n
        return {'pairs': self.n, 'mean_d_m': m, 'sd_d_m': math.sqrt(max(0.0, self.s2 / self.n - m * m)),
                'mean_leader_len_m': self.lead_len_s / self.n,
                'd_pct': {str(q): self.exact(self.vals, q) for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)},
                'gap_pct': {str(q): self.exact(self.gaps, q) for q in (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95)},
                'mean_gap_m': sum(self.gaps) / self.n, 'share_gap_negative': sum(1 for x in self.gaps if x < 0) / self.n,
                'share_d_over_15m': sum(self.hist[150:]) / self.n}


def main():
    fzp, nf_p, out = sys.argv[1], sys.argv[2], sys.argv[3]
    nf = json.loads(open(nf_p, 'rb').read().decode('utf-8'))
    behav = {k: v['behav'] for k, v in nf['links'].items()}
    info, waited = acquire('inv_spacing ' + os.path.basename(fzp))
    t0 = time.time()
    try:
        allacc = Acc()
        by_beh = defaultdict(Acc)
        by_link = defaultdict(Acc)
        by_hgv = {'leader_len_lt_7m': Acc(), 'leader_len_ge_7m': Acc()}
        len_hist_all = defaultdict(int)
        len_hist_stopped = defaultdict(int)
        uniq = set()
        frames = 0
        rows = 0
        cur_t = None
        bucket = defaultdict(list)
        h = hashlib.sha256()

        def flush():
            for (lk, ln), vs in bucket.items():
                if len(vs) < 2:
                    continue
                vs.sort(key=lambda v: v[0])
                for a, b in zip(vs, vs[1:]):
                    if a[1] < 1.0 and b[1] < 1.0:
                        d = b[0] - a[0]
                        gap = d - b[2]
                        allacc.add(d, gap, b[2])
                        by_beh[behav.get(lk, '?')].add(d, gap, b[2])
                        if lk in FOCUS:
                            by_link[lk].add(d, gap, b[2])
                        by_hgv['leader_len_ge_7m' if b[2] >= 7.0 else 'leader_len_lt_7m'].add(d, gap, b[2])
                        if len(uniq) < 3_000_000:
                            uniq.add((a[3], b[3]))
            bucket.clear()

        header_done = False
        with open(fzp, 'rb') as g:
            for raw in g:
                h.update(raw)
                if not header_done:
                    if raw.startswith(b'$VEHICLE:'):
                        header_done = True
                    continue
                p = raw.split(b';', 11)
                if len(p) < 11:
                    continue
                t = p[0]
                if t != cur_t:
                    if cur_t is not None:
                        flush()
                        frames += 1
                    cur_t = t
                rows += 1
                lk = p[2].decode()
                ln = int(p[3])
                pos = float(p[4])
                spd = float(p[6])
                L = float(p[10])
                bucket[(lk, ln)].append((pos, spd, L, int(p[1])))
                lb = round(L, 1)
                len_hist_all[lb] += 1
                if spd < 1.0:
                    len_hist_stopped[lb] += 1
            if cur_t is not None:
                flush()
                frames += 1
        rec = allacc.summary()['d_pct']['0.5']
        res = {'tool': 'inv_spacing.py', 'fzp_name': os.path.basename(fzp), 'fzp_sha256': h.hexdigest(),
               'net_facts_sha256': hashlib.sha256(open(nf_p, 'rb').read()).hexdigest(),
               'definition': __doc__.split('- Definition (fixed before the scan): ')[1].split('No VISSIM')[0].strip(),
               'frames': frames, 'rows': rows, 'unique_pairs_capped': len(uniq),
               'all': allacc.summary(), 'by_link_behaviour': {k: v.summary() for k, v in sorted(by_beh.items())},
               'by_leader_length': {k: v.summary() for k, v in by_hgv.items()},
               'by_focus_link': {k: v.summary() for k, v in sorted(by_link.items(), key=lambda kv: int(kv[0]))},
               'vehicle_length_hist_all_rows': {str(k): v for k, v in sorted(len_hist_all.items())},
               'vehicle_length_hist_stopped_rows': {str(k): v for k, v in sorted(len_hist_stopped.items())},
               'recommended_spacing_m': rec, 'recommended_rule': 'median d over all stopped pairs (exact, linear interpolation)',
               'lock': {'waited_s': waited, 'held_s': time.time() - t0, 'acquired_kst': info['started_kst']}}
        tmp = out + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp, out)
        print('done', kst(), 'frames', frames, 'rows', rows, 'pairs', allacc.n, 'median', rec,
              hashlib.sha256(open(out, 'rb').read()).hexdigest())
    finally:
        print('lock', release(info), kst())


if __name__ == '__main__':
    main()
