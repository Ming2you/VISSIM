# v_prefix.py — VERIFY_VSL (2026-10-27 KST). Fresh script. Read-only on FZPs.
# Compare VSL and NC3 FZP data rows: rows with t <= 895.1 (count, sha256 each side, equal?), first differing row,
# and for frames 900.1 .. 960.1 the vehicles whose rows differ (by vehicle No), with link/pos/desspeed on both sides.
# Usage: python -B v_prefix.py <vsl.fzp> <nc3.fzp> <out.json>
import sys, json, hashlib

A, B, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
T_PREFIX = 895.1 + 1e-6
T_END = 960.1 + 1e-6


def data_lines(p):
    f = open(p, 'rb')
    for line in f:
        if line.startswith(b'$VEHICLE:'):
            break
    for line in f:
        yield line.rstrip(b'\r\n')


ga, gb = data_lines(A), data_lines(B)
ha, hb = hashlib.sha256(), hashlib.sha256()
na = nb = 0
first_diff = None
frames_a, frames_b = {}, {}
done_a = done_b = False
la = lb = None
while True:
    la = next(ga, None) if not done_a else None
    lb = next(gb, None) if not done_b else None
    if la is None:
        done_a = True
    if lb is None:
        done_b = True
    if done_a and done_b:
        break
    for line, h, frames, side in ((la, ha, frames_a, 'a'), (lb, hb, frames_b, 'b')):
        if line is None:
            continue
        t = float(line.split(b';', 1)[0])
        if t <= T_PREFIX:
            h.update(line + b'\n')
            if side == 'a':
                na += 1
            else:
                nb += 1
        elif t <= T_END:
            p = line.decode().split(';')
            frames.setdefault(p[0], {})[p[1]] = p
        else:
            if side == 'a':
                done_a = True
            else:
                done_b = True
    if first_diff is None and la is not None and lb is not None and la != lb:
        first_diff = dict(vsl=la.decode()[:200], nc3=lb.decode()[:200])

SIGN = 3998.6659943877257
DOWN = {'10613', '119', '10702', '24', '10481', '10483', '10490', '10484', '127', '124'}


def where(p):
    link, pos = p[2], float(p[4])
    if link == '2':
        return 'link2_past_sign' if pos >= SIGN else 'link2_before_sign(%.0f)' % pos
    if link in DOWN:
        return 'downstream_' + link
    return 'other_' + link


per_frame = {}
for t in sorted(set(frames_a) | set(frames_b), key=float):
    fa, fb = frames_a.get(t, {}), frames_b.get(t, {})
    diffs = []
    for no in sorted(set(fa) | set(fb), key=int):
        pa, pb = fa.get(no), fb.get(no)
        if pa != pb:
            diffs.append(dict(no=no,
                              vsl=None if pa is None else dict(link=pa[2], lane=pa[3], pos=pa[4], speed=pa[6], des=pa[9], where=where(pa)),
                              nc3=None if pb is None else dict(link=pb[2], lane=pb[3], pos=pb[4], speed=pb[6], des=pb[9], where=where(pb))))
    wh = {}
    for d in diffs:
        k = (d['vsl'] or d['nc3'])['where']
        wh[k] = wh.get(k, 0) + 1
    per_frame[t] = dict(n_rows_vsl=len(fa), n_rows_nc3=len(fb), n_diff=len(diffs), where_counts=wh, diffs=diffs[:40])

out = dict(vsl=A, nc3=B, prefix_le_895_1=dict(rows_vsl=na, rows_nc3=nb, sha_vsl=ha.hexdigest(), sha_nc3=hb.hexdigest(),
                                               equal=(na == nb and ha.hexdigest() == hb.hexdigest())),
           first_diff=first_diff, frames=per_frame)
json.dump(out, open(OUT, 'w', encoding='utf-8'), indent=1)
print(json.dumps(out['prefix_le_895_1']), json.dumps(first_diff)[:400])
for t, r in per_frame.items():
    print(t, r['n_rows_vsl'], r['n_rows_nc3'], r['n_diff'], r['where_counts'])
