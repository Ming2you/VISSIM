r"""VERIFY_N2 fresh FZP scanner (written for the verify step; imports nothing from stage1 / r2c / o1 / n34 / vn tools).

One streaming pass per FZP. Takes the shared FZP lock (exclusive create) around each FZP read, deletes it after.
Run folders are read only. Writes only <verify_n2>/out/scan_<tag>.npz and scan_<tag>.json.

Per frame it keeps: vehicle count per link (dense matrix), per FW_E meter the count of vehicles on the meter's
from-link whose NEXTLINK is the meter connector, per meter lane the count of vehicles within 50 m before the head
with speed < 15 km/h and the count of vehicles after the head with speed < 15 km/h.
Per vehicle: first record (SimSec, TmInNetTot, link) for insertion times.
Events: meter head crossings (previous record on the connector before the head; current record after the head or
on another link) and connector exits (previous record on the connector, current record on another link).
FW_E chain records: count and speed sum per (300 s bin by frame time, link, 10 m position bucket).
Usage: python -B v2_scan.py tag=path.fzp [tag=path.fzp ...]
"""
import ctypes
import datetime
import hashlib
import io
import json
import os
import sys
import time
from ctypes import wintypes

import numpy as np

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
VN2 = os.path.dirname(HERE)
OUT = os.path.join(VN2, 'out')
LOCK = os.path.join(os.path.dirname(VN2), 'fzp.lock')

CHAIN = (b'74', b'10699', b'2', b'10613', b'119', b'10702', b'24')
# meter connector -> (from-link, head pos on connector [m], lanes) ; head pos from inpx signalHead 90030897-90030901
METERS = {b'10639': (b'70', 314.83469380887993, 1), b'10681': (b'68', 290.72003141146473, 2),
          b'10490': (b'129', 272.60355928160652, 1), b'10484': (b'31', 377.11076285480539, 1)}
MKEYS = list(METERS)
FROMS = {v[0]: k for k, v in METERS.items()}


def below_normal():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)


def take_lock(tag):
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ('verify_n2 v2_scan %s pid=%d at=%s\n' % (tag, os.getpid(), datetime.datetime.now().astimezone().isoformat())).encode())
            os.close(fd)
            return round(time.time() - t0, 1)
        except FileExistsError:
            if time.time() - t0 > 6 * 3600:
                raise SystemExit('lock busy too long')
            time.sleep(20)


def scan(path):
    link_idx = {}
    frames_t = []
    rows_cnt = []  # list of (idx array, count array)
    mb = {m: [] for m in MKEYS}
    qnear = {(m, ln): [] for m in MKEYS for ln in range(1, METERS[m][2] + 1)}
    qpost = {(m, ln): [] for m in MKEYS for ln in range(1, METERS[m][2] + 1)}
    first = {}
    last_on = {}  # vehicle no -> (conn, lane, pos)
    cross = []  # (conn, lane, t)
    exits = []  # (conn, lane, t)
    zone = {}  # (bin300, link, bucket) -> [n, speed_sum]
    conn_maxpos = {m: 0.0 for m in MKEYS}
    chain_maxpos = {c: 0.0 for c in CHAIN}
    digits = frozenset(b'0123456789')
    rows = 0
    cur_tb = None
    cnt = None
    fmb = fqn = fqp = None
    t = None

    def close():
        frames_t.append(t)
        ks = list(cnt.keys())
        idx = np.fromiter((link_idx.setdefault(k, len(link_idx)) for k in ks), dtype=np.int32, count=len(ks))
        rows_cnt.append((idx, np.fromiter(cnt.values(), dtype=np.int32, count=len(ks))))
        for m in MKEYS:
            mb[m].append(fmb[m])
        for key in qnear:
            qnear[key].append(fqn[key])
            qpost[key].append(fqp[key])

    with io.open(path, 'rb', buffering=1 << 22) as f:
        for raw in f:
            if raw[0] not in digits:
                continue
            p = raw.split(b';', 15)
            tb = p[0]
            if tb != cur_tb:
                if cur_tb is not None:
                    close()
                cur_tb = tb
                t = float(tb)
                b300 = int(t // 300)
                cnt = {}
                fmb = dict.fromkeys(MKEYS, 0)
                fqn = dict.fromkeys(qnear, 0)
                fqp = dict.fromkeys(qnear, 0)
            rows += 1
            lk = p[2]
            cnt[lk] = cnt.get(lk, 0) + 1
            no = p[1]
            if no not in first:
                first[no] = (t, float(p[7]), lk)
            prev = last_on.get(no)
            if lk in METERS:
                head = METERS[lk][1]
                pos = float(p[4])
                sp = float(p[6])
                ln = int(p[3])
                if pos > conn_maxpos[lk]:
                    conn_maxpos[lk] = pos
                fmb[lk] += 1
                key = (lk, ln)
                if key in fqn:
                    if pos < head and pos >= head - 50.0 and sp < 15.0:
                        fqn[key] += 1
                    elif pos >= head and sp < 15.0:
                        fqp[key] += 1
                if prev is not None and prev[0] == lk:
                    if prev[2] < head <= pos:
                        cross.append((MKEYS.index(lk), prev[1], t))
                elif prev is not None:  # moved from another meter connector directly (should not happen)
                    if prev[2] < METERS[prev[0]][1]:
                        cross.append((MKEYS.index(prev[0]), prev[1], t))
                    exits.append((MKEYS.index(prev[0]), prev[1], t))
                last_on[no] = (lk, ln, pos)
            else:
                if prev is not None:
                    if prev[2] < METERS[prev[0]][1]:
                        cross.append((MKEYS.index(prev[0]), prev[1], t))
                    exits.append((MKEYS.index(prev[0]), prev[1], t))
                    del last_on[no]
                if lk in FROMS:
                    if p[14] == FROMS[lk]:
                        fmb[FROMS[lk]] += 1
                elif lk in chain_maxpos:
                    pos = float(p[4])
                    if pos > chain_maxpos[lk]:
                        chain_maxpos[lk] = pos
                    zk = (b300, lk, int(pos // 10.0))
                    z = zone.get(zk)
                    if z is None:
                        zone[zk] = [1, float(p[6])]
                    else:
                        z[0] += 1
                        z[1] += float(p[6])
        if cur_tb is not None:
            close()
    nl = len(link_idx)
    M = np.zeros((len(frames_t), nl), dtype=np.int32)
    for i, (idx, c) in enumerate(rows_cnt):
        M[i, idx] = c
    links = [None] * nl
    for k, i in link_idx.items():
        links[i] = k.decode()
    fr = np.array(sorted(first.items(), key=lambda kv: int(kv[0])), dtype=object)
    veh_no = np.array([int(k) for k, _ in fr], dtype=np.int64)
    veh_t = np.array([v[0] for _, v in fr], dtype=np.float64)
    veh_tmin = np.array([v[1] for _, v in fr], dtype=np.float64)
    veh_link = np.array([v[2].decode() for _, v in fr])
    zk = sorted(zone)
    out = dict(frames_t=np.array(frames_t), links=np.array(links), counts=M,
               veh_no=veh_no, veh_t=veh_t, veh_tmin=veh_tmin, veh_link=veh_link,
               cross=np.array(cross, dtype=np.float64).reshape(-1, 3), exits=np.array(exits, dtype=np.float64).reshape(-1, 3),
               zone_bin=np.array([k[0] for k in zk], dtype=np.int32), zone_link=np.array([k[1].decode() for k in zk]),
               zone_bucket=np.array([k[2] for k in zk], dtype=np.int32),
               zone_n=np.array([zone[k][0] for k in zk], dtype=np.int64), zone_vsum=np.array([zone[k][1] for k in zk]))
    for m in MKEYS:
        out['mb_' + m.decode()] = np.array(mb[m], dtype=np.int32)
    for (m, ln) in qnear:
        out['qnear_%s_%d' % (m.decode(), ln)] = np.array(qnear[(m, ln)], dtype=np.int32)
        out['qpost_%s_%d' % (m.decode(), ln)] = np.array(qpost[(m, ln)], dtype=np.int32)
    meta = dict(rows=rows, frames=len(frames_t), t_first=frames_t[0], t_last=frames_t[-1], n_links=nl,
                n_veh=len(veh_no), conn_maxpos={k.decode(): v for k, v in conn_maxpos.items()},
                chain_maxpos={k.decode(): v for k, v in chain_maxpos.items()}, meter_order=[m.decode() for m in MKEYS],
                n_cross=len(cross), n_exits=len(exits))
    return out, meta


def main():
    below_normal()
    os.makedirs(OUT, exist_ok=True)
    log = []
    for a in sys.argv[1:]:
        tag, path = a.split('=', 1)
        st = os.stat(path)
        waited = take_lock(tag)
        t0 = time.time()
        try:
            out, meta = scan(path)
        finally:
            os.remove(LOCK)
        st2 = os.stat(path)
        meta.update(tag=tag, fzp=path, fzp_bytes=st.st_size, fzp_mtime=st.st_mtime, fzp_unchanged=(st.st_size == st2.st_size and st.st_mtime == st2.st_mtime),
                    lock_wait_sec=waited, scan_sec=round(time.time() - t0, 1), lock_released=not os.path.exists(LOCK) or 'other')
        np.savez_compressed(os.path.join(OUT, 'scan_%s.npz' % tag), **out)
        with io.open(os.path.join(OUT, 'scan_%s.json' % tag), 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=1)
        log.append(meta)
        print(json.dumps(meta), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
