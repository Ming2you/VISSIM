r"""VERIFY_N2: route split at decision 1135 (link 68) in ONE already-analysed V-A FZP (v3c3-s31), fresh code.
Per vehicle seen on link 68: its (ROUTDECNO, ROUTENO) at its LAST record on link 68 and the first link after 68.
Takes the shared FZP lock; BELOW_NORMAL. NC3 FZPs are deliberately NOT read (design P0 C-1 is pre-declared there)."""
import collections
import ctypes
import datetime
import io
import json
import os
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
VN2 = os.path.dirname(HERE)
LOCK = os.path.join(os.path.dirname(VN2), 'fzp.lock')
FZP = r'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s31\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp'


def main():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, ('verify_n2 v2_routes pid=%d at=%s\n' % (os.getpid(), datetime.datetime.now().astimezone().isoformat())).encode())
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(20)
    last68 = {}
    after = {}
    try:
        with io.open(FZP, 'rb', buffering=1 << 22) as f:
            for raw in f:
                if raw[:1] not in b'0123456789' or not raw[:1]:
                    continue
                p = raw.split(b';', 15)
                no, lk = p[1], p[2]
                if lk == b'68':
                    last68[no] = (p[11], p[12], float(p[0]))
                elif no in last68 and no not in after:
                    after[no] = lk
    finally:
        os.remove(LOCK)
    c = collections.Counter()
    c_after = collections.Counter()
    for no, (rd, rn, t) in last68.items():
        if t < 900.0:
            continue
        c[(rd.decode(), rn.decode())] += 1
        c_after[((rd.decode(), rn.decode()), after.get(no, b'').decode())] += 1
    tot1135 = sum(v for (rd, rn), v in c.items() if rd == '1135')
    res = {'fzp': FZP, 'vehicles_on_68_after_900s': sum(c.values()),
           'by_decision_route': {'%s:%s' % key: v for key, v in c.most_common()},
           'share_1135': {'%s' % rn: round(v / tot1135, 4) for (rd, rn), v in c.items() if rd == '1135'},
           'by_route_and_next_link': {'%s:%s->%s' % (k[0][0], k[0][1], k[1]): v for k, v in c_after.most_common(20)},
           'sec': round(time.time() - t0, 1)}
    with io.open(os.path.join(VN2, 'out', 'v2_routes_va_s31.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
