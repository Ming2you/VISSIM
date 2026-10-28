# Compare the FZP frame at t = 900.10 s between B and NC3 (same seed), read-only, stops reading after t > 900.1.
# usage: python -B b_frame900.py <seed>
import sys, hashlib, ctypes
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
except Exception:
    pass
s = int(sys.argv[1])
F = {'B': 'D:/VISSIM_runs/20261026_codex_b_v3c3/s%d/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s%d_001.fzp' % (s, s),
     'NC3': 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (s, s)}
res = {}
for k, p in F.items():
    rows = []
    with open(p, 'rb') as f:
        for line in f:
            if not line[:1].isdigit():
                continue
            t = line.split(b';', 1)[0]
            if t == b'900.10':
                rows.append(line.rstrip(b'\r\n'))
            elif float(t) > 900.1:
                break
    rows.sort()
    res[k] = (len(rows), hashlib.sha256(b'\n'.join(rows)).hexdigest())
print('s%d' % s, res, 'equal=%s' % (res['B'] == res['NC3']))
