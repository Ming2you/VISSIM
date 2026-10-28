# VERIFY_NEXT: transitions out of / into ramp supply links 68, 31, 129, 70 (read-only, one FZP).
# Usage: python -B vn_fzp_split.py <fzp> <out.json>
import sys, json, time
fzp, out = sys.argv[1], sys.argv[2]
SUP = {68, 31, 129, 70}
t0 = time.time()
last = {}
outk = {}   # (from, to) -> [k]
ink = {}    # (from, to) -> [k] for to in SUP
in_data = False
with open(fzp, 'rb') as f:
    for line in f:
        if not in_data:
            if line.startswith(b'$VEHICLE:'):
                in_data = True
            continue
        p = line.split(b';', 4)
        if len(p) < 4:
            continue
        k = int(round((float(p[0]) - 0.1) / 5.0))
        vid = p[1]; L = int(p[2])
        prev = last.get(vid)
        if prev is not None and prev != L:
            if prev in SUP:
                outk.setdefault(f'{prev}>{L}', []).append(k)
            if L in SUP:
                ink.setdefault(f'{prev}>{L}', []).append(k)
        last[vid] = L
json.dump({'fzp': fzp, 'out': outk, 'in': ink, 'elapsed_s': round(time.time() - t0, 1)}, open(out, 'w', encoding='utf-8'))
print('OK', fzp, round(time.time() - t0, 1))
