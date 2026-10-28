r"""O1 step 5: one streaming read of four FZPs (RM s41, NC3 s41, RM s31, NC3 s31; one at a time) for the coupling
around link 129 / 127: transitions between links per 150 s bin (a vehicle seen on link A in one 5 s frame and on link B
in the next), and per-frame stocks on link 26 (FW_W) by NEXTLINK and speed, on 129 / 127 / 10491 / 10490 / 10777,
and FW_E link 2 lane 1 slow vehicles.  Read only (FZP opened 'rb'); writes o1o4/o1/out/o1_fzp_coupling.json.
Columns by header name (SIMSEC, NO, LANE\LINK\NO, LANE\INDEX, POS, SPEED, NEXTLINK\NO).  BELOW_NORMAL."""
import io
import json
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), 'out')
ROOT = r'D:\VISSIM_runs\20261001_v3c3'
RUNS = [('rm_s41', os.path.join(ROOT, 's41_v3c3rm', 'run', 'vissim_eval', 'baseline_s41_v3c3rm_001.fzp')),
        ('nc3_s41', os.path.join(ROOT, 's41_v3c3nc', 'run', 'vissim_eval', 'baseline_s41_v3c3nc_001.fzp')),
        ('rm_s31', os.path.join(ROOT, 's31_v3c3rm', 'run', 'vissim_eval', 'baseline_s31_v3c3rm_001.fzp')),
        ('nc3_s31', os.path.join(ROOT, 's31_v3c3nc', 'run', 'vissim_eval', 'baseline_s31_v3c3nc_001.fzp'))]
WATCH_T = {(b'10481', b'127'), (b'10777', b'127'), (b'129', b'10490'), (b'129', b'10777'), (b'10491', b'129'),
           (b'10778', b'129'), (b'26', b'10491'), (b'26', b'10771'), (b'10490', b'119'), (b'2', b'10481'),
           (b'127', b'10118'), (b'127', b'10368'), (b'127', b'10695'), (b'10777', b'127'), (b'31', b'10484'),
           (b'10484', b'24'), (b'68', b'10681'), (b'10681', b'2'), (b'70', b'10639'), (b'10639', b'2'),
           (b'2', b'10643'), (b'2', b'10682'), (b'2', b'10613')}
TARGETS = {b'127', b'129', b'10490', b'10491', b'10777', b'10481', b'26', b'10484', b'10681', b'10639'}
STOCK_LINKS = (b'129', b'127', b'10491', b'10490', b'10777', b'26', b'2', b'31', b'10484', b'68', b'10681')
NB = 60


def below_normal():
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass.restype = wintypes.BOOL
    k.GetPriorityClass.argtypes = [wintypes.HANDLE]
    k.GetPriorityClass.restype = wintypes.DWORD
    h = k.GetCurrentProcess()
    k.SetPriorityClass(h, 0x00004000)
    return k.GetPriorityClass(h)


def scan(path):
    t0 = time.time()
    trans = {}
    # per-bin sums of frame stocks (divide by frames per bin for the mean)
    stock = {l.decode(): [0] * NB for l in STOCK_LINKS}
    slow = {l.decode(): [0] * NB for l in STOCK_LINKS}            # speed < 20 km/h
    l26_next = {}                                                  # NEXTLINK of slow vehicles on 26 -> per-bin sums
    l26_slow_lane = {}
    l2_lane1_slow = [0] * NB
    l26_tail = [None] * NB                                          # min POS of slow vehicles on 26 in the bin
    frames = [0] * NB
    last = {}
    cur_t = None
    idx = None
    rows = 0
    with io.open(path, 'rb') as f:
        for raw in f:
            if idx is None:
                if raw.startswith(b'$VEHICLE:'):
                    cols = raw[len(b'$VEHICLE:'):].strip().split(b';')
                    idx = [cols.index(c) for c in (b'SIMSEC', b'NO', b'LANE\\LINK\\NO', b'LANE\\INDEX', b'POS', b'SPEED',
                                                   b'NEXTLINK\\NO')]
                continue
            if not raw or raw[0:1] in (b'*', b'$', b'\r', b'\n'):
                continue
            p = raw.split(b';')
            try:
                t = p[idx[0]]
            except IndexError:
                continue
            if t != cur_t:
                cur_t = t
                tf = float(t)
                b = min(NB - 1, int(tf // 150))
                frames[b] += 1
            rows += 1
            no, link = p[idx[1]], p[idx[2]]
            prev = last.get(no)
            if prev is not None and prev != link and (link in TARGETS or prev in TARGETS):
                k = '%s>%s' % (prev.decode(), link.decode())
                arr = trans.get(k)
                if arr is None:
                    arr = trans[k] = [0] * NB
                arr[b] += 1
            last[no] = link
            if link in stock:
                pass
            if link in (b'129', b'127', b'10491', b'10490', b'10777', b'26', b'2', b'31', b'10484', b'68', b'10681'):
                ls = link.decode()
                stock[ls][b] += 1
                sp = float(p[idx[5]])
                if sp < 20.0:
                    slow[ls][b] += 1
                    if link == b'26':
                        nx = p[idx[6]].decode() or '-'
                        l26_next.setdefault(nx, [0] * NB)[b] += 1
                        ln = p[idx[3]].decode()
                        l26_slow_lane.setdefault(ln, [0] * NB)[b] += 1
                        pos = float(p[idx[4]])
                        if l26_tail[b] is None or pos < l26_tail[b]:
                            l26_tail[b] = pos
                    elif link == b'2' and p[idx[3]] == b'1':
                        l2_lane1_slow[b] += 1
    fr = [max(1, x) for x in frames]
    mean = lambda arr: [round(a / n, 2) for a, n in zip(arr, fr)]
    return {'path': path, 'rows': rows, 'frames_per_bin': frames, 'sec': round(time.time() - t0, 1),
            'transitions_per_bin': trans,
            'stock_mean_veh': {k: mean(v) for k, v in stock.items()},
            'slow_lt20_mean_veh': {k: mean(v) for k, v in slow.items()},
            'link26_slow_by_nextlink_mean_veh': {k: mean(v) for k, v in l26_next.items()},
            'link26_slow_by_lane_mean_veh': {k: mean(v) for k, v in l26_slow_lane.items()},
            'link26_slow_tail_min_pos_m': [round(x, 1) if x is not None else None for x in l26_tail],
            'link2_lane1_slow_mean_veh': mean(l2_lane1_slow)}


def main():
    prio = below_normal()
    res = {'priority': hex(prio), 'doc': __doc__, 'runs': {}}
    for tag, p in RUNS:
        r = scan(p)
        res['runs'][tag] = r
        print(tag, r['rows'], r['sec'], flush=True)
        with io.open(os.path.join(OUT, 'o1_fzp_coupling.json'), 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=1)
    print('done')


if __name__ == '__main__':
    main()
