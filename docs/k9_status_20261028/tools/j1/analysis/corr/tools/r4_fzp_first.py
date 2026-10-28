r"""V-A r4 step 1: fresh first-observation scan of ONE run's FZP (independent of stage-1).  Read-only on the FZP.
python -B r4_fzp_first.py <tag>      tag = va_s31 | j1_s31 | nc3_s31 | ... (one run per call; BELOW_NORMAL)
Columns by name from the $VEHICLE header (SIMSEC, NO, LANE\LINK\NO).  Rows starting with b'0.10;' (runner FZP 0.10 s
row) are skipped and counted, as the r3 read shim does (va_common.FZP_SKIP).  For every vehicle number: first frame
time and first link.  Writes AV/r4/out/fzp_first_<tag>.json: per first link a histogram {time*10: vehicles}, totals,
frame checks, the closed-form window integral sum(t_last - t_first)/3600 over all vehicles."""
import io
import os
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r4_common as RC  # noqa: E402

V = RC.V
NEED = ('SIMSEC', 'NO', 'LANE\\LINK\\NO')


def header(path):
    with io.open(path, 'rb') as h:
        for i, raw in enumerate(h):
            if raw.startswith(b'$VEHICLE:'):
                cols = raw[len(b'$VEHICLE:'):].strip().decode('ascii', 'replace').split(';')
                return [cols.index(n) for n in NEED]
            if i > 300:
                break
    raise SystemExit('no $VEHICLE header: ' + path)


def scan_path(path, tag):
    t_start = time.perf_counter()
    it, ino, ilk = header(path)
    m = max(it, ino, ilk) + 1
    digits = frozenset(b'0123456789')
    first = {}
    rows = skipped = frames = irregular = 0
    last_tb, tcur, t_first_frame, prev_t = None, None, None, None
    with io.open(path, 'rb', buffering=1 << 22) as h:
        for raw in h:
            if raw[0] not in digits:
                continue
            if raw.startswith(V.FZP_SKIP):
                skipped += 1
                continue
            p = raw.split(b';', m)
            tb = p[it]
            if tb != last_tb:
                last_tb = tb
                tcur = float(tb)
                frames += 1
                if t_first_frame is None:
                    t_first_frame = tcur
                elif abs((tcur - prev_t) - 5.0) > 1e-6:
                    irregular += 1
                prev_t = tcur
            rows += 1
            no = p[ino]
            if no not in first:
                first[no] = (tcur, p[ilk])
    t_last = prev_t
    hist = {}
    total = 0.0
    for no, (t, lk) in first.items():
        d = hist.setdefault(lk.decode('ascii'), {})
        k = int(round(t * 10))
        d[k] = d.get(k, 0) + 1
        total += t_last - t
    out = {'schema': 'k92-va-r4-fzp-first/v1', 'tag': tag, 'fzp': path, 'fzp_bytes': os.path.getsize(path),
           'fzp_mtime': os.path.getmtime(path), 'columns': dict(zip(NEED, (it, ino, ilk))), 'rows': rows,
           'skipped_0p10_rows': skipped, 'frames': frames, 'first_frame_sec': t_first_frame, 'last_frame_sec': t_last,
           'irregular_steps': irregular, 'vehicles': len(first),
           'closed_form_window_veh_h': total / 3600.0,
           'hist_by_first_link_t10': {lk: {str(k): v for k, v in sorted(d.items())} for lk, d in sorted(hist.items())},
           'scan_sec': round(time.perf_counter() - t_start, 1),
           'script_sha256': V.sha(os.path.abspath(__file__)), 'common_sha256': V.sha(RC.__file__)}
    return out


def scan(tag):
    prio = V.set_below_normal()
    out = scan_path(RC.fzp_of(tag), tag)
    out['priority'] = hex(prio)
    RC.jdump(out, os.path.join(RC.OUT, 'fzp_first_%s.json' % tag))
    first_n, rows, skipped, frames = out['vehicles'], out['rows'], out['skipped_0p10_rows'], out['frames']
    t_first_frame, t_last, irregular = out['first_frame_sec'], out['last_frame_sec'], out['irregular_steps']
    print('%s vehicles=%d rows=%d skipped=%d frames=%d [%s, %s] irregular=%d sec=%.1f' % (
        tag, first_n, rows, skipped, frames, t_first_frame, t_last, irregular, out['scan_sec']))


if __name__ == '__main__':
    tags = sys.argv[1:]
    if len(tags) != 1 or tags[0] not in RC.TAGS:
        raise SystemExit('usage: r4_fzp_first.py <one of %s>' % ', '.join(RC.TAGS))
    scan(tags[0])
