# A1 FZP frame-by-frame comparison (rule COMPARE_RULE_A1_FULL.md, part B). Read-only on FZP; shares codex_handoff fzp.lock.
# usage: python -B a1_fzp_firstdiff.py <out.json> [--smoke]
#   pairs: a1-joint (main), a1-lnc, joint-lnc (context). --smoke: "a1" = codex joint FZP.
# A frame = consecutive data rows with the same SIMSEC text. Rows are compared as LF-normalised bytes keyed by vehicle NO.
# Per pair: prefix rows <= 895.1 equal?, first frame (t <= 8100) whose rows differ, what differs there (vehicles only in one,
# vehicles with a different row, links of those), and per 150-s block: frames that differ, max vehicles differing in a frame.
import json, os, sys, time, ctypes, collections
try:
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL
except Exception:
    pass
SMOKE = '--smoke' in sys.argv
LOCK = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/omega/fzp.lock'
JOINT = 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp'   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s41; slot joint = NC3, a1 = B, lnc = V-A]
LNC = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp'   # B copy: slot lnc = V-A v3c3-s41
A1 = JOINT if SMOKE else 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp'   # B copy: slot a1 = B v3c3-s41
FILES = {'a1': A1, 'joint': JOINT, 'lnc': LNC}
PAIRS = [('a1', 'joint'), ('a1', 'lnc'), ('joint', 'lnc')]
END, PREFIX_END = 8100.0, 895.1


def frames(path):
    cur_t, rows = None, {}
    with open(path, 'rb', buffering=1 << 22) as fh:
        for raw in fh:
            if not raw[:1].isdigit():
                continue
            p = raw.split(b';', 3)
            tb = p[0]
            if tb != cur_t:
                if cur_t is not None:
                    yield float(cur_t), rows
                cur_t, rows = tb, {}
            rows[p[1]] = (raw.rstrip(b'\r\n'), p[2])
    if cur_t is not None:
        yield float(cur_t), rows


def compare(na, nb):
    ga, gb = frames(FILES[na]), frames(FILES[nb])
    fa, fb = next(ga, None), next(gb, None)
    res = {'pair': na + '-' + nb, 'prefix_equal_le_895_1': True, 'first_diff_t': None, 'first_diff': None, 'frames_compared': 0,
           'frames_differing': 0, 'blocks': {}}
    while fa is not None or fb is not None:
        ta = fa[0] if fa is not None else 1e18
        tb = fb[0] if fb is not None else 1e18
        t = min(ta, tb)
        if t > END:
            break
        ra = fa[1] if ta == t else {}
        rb = fb[1] if tb == t else {}
        res['frames_compared'] += 1
        if ra != rb:
            only_a = [k for k in ra if k not in rb]
            only_b = [k for k in rb if k not in ra]
            changed = [k for k in ra if k in rb and ra[k][0] != rb[k][0]]
            nveh = len(only_a) + len(only_b) + len(changed)
            res['frames_differing'] += 1
            if t <= PREFIX_END:
                res['prefix_equal_le_895_1'] = False
            blk = str(int(t // 150) * 150)
            b = res['blocks'].setdefault(blk, {'frames_differing': 0, 'max_vehicles_differing': 0})
            b['frames_differing'] += 1
            b['max_vehicles_differing'] = max(b['max_vehicles_differing'], nveh)
            if res['first_diff_t'] is None:
                links = collections.Counter()
                for k in only_a:
                    links[ra[k][1].decode()] += 1
                for k in only_b:
                    links[rb[k][1].decode()] += 1
                for k in changed:
                    links[ra[k][1].decode()] += 1
                ex = []
                for k in changed[:5]:
                    ex.append([ra[k][0].decode('latin-1')[:200], rb[k][0].decode('latin-1')[:200]])
                res['first_diff_t'] = t
                res['first_diff'] = {'rows_a': len(ra), 'rows_b': len(rb), 'only_a': len(only_a), 'only_b': len(only_b), 'changed': len(changed),
                                     'links_top': links.most_common(20), 'changed_examples': ex,
                                     'only_a_examples': [ra[k][0].decode('latin-1')[:200] for k in only_a[:3]],
                                     'only_b_examples': [rb[k][0].decode('latin-1')[:200] for k in only_b[:3]]}
        if ta == t:
            fa = next(ga, None)
        if tb == t:
            fb = next(gb, None)
    return res


while True:
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, ('a1_fzp_firstdiff pid=%d start=%s\n' % (os.getpid(), time.strftime('%Y-%m-%d %H:%M:%S'))).encode())
        os.close(fd)
        break
    except FileExistsError:
        time.sleep(5)
try:
    t0 = time.time()
    st = {k: (os.path.getsize(v), os.path.getmtime(v)) for k, v in FILES.items()}
    out = {'rule': 'COMPARE_RULE_A1_FULL.md', 'smoke': SMOKE, 'files': FILES, 'stat': st, 'pairs': []}
    for a, b in PAIRS:
        r = compare(a, b)
        out['pairs'].append(r)
        print(r['pair'], 'prefix_equal', r['prefix_equal_le_895_1'], 'first_diff_t', r['first_diff_t'], 'frames', r['frames_compared'],
              'differing', r['frames_differing'], round(time.time() - t0, 1), flush=True)
    assert st == {k: (os.path.getsize(v), os.path.getmtime(v)) for k, v in FILES.items()}
    out['sec'] = round(time.time() - t0, 1)
    json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1)
finally:
    try:
        os.remove(LOCK)
    except FileNotFoundError:
        pass
