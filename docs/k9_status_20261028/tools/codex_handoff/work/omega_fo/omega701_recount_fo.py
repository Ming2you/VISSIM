r"""[FO copy 2026-10-27 KST, COMPARE_RULE_FO: path constants only; the slot that held B now holds FO] [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; slot "j1" = B runs v3c3-s31/s41/s43] OMEGA701_V3C3 (2026-10-25 KST): Omega701 recount of our 9 v3c3 runs + joint metric table, one tool.

Usage (python -B, PYTHONHASHSEED=0):
  omega701_recount.py scan      one streaming pass per FZP (10 files: 9 v3c3 runs + LNC 64cf-s29 NC for the codex
                                partition check), one at a time under codex_handoff/fzp.lock; writes cache/<tag>.npz/.json
  omega701_recount.py metrics   everything else from the caches (no FZP read); writes omega701_v3c3.json + CSVs

Read only toward every run folder, the stage-1 tools (sha-checked, imported), sim3 membership, the local raw copy.
Writes only under codex_handoff/work/omega/ and the lock file.

Two link-integration conventions (both from the same per-frame link counts):
  ours  = stage-1 / V-A report: FZP frames 5.1 .. last frame <= T_end, trapezoid between consecutive frames, the runner
          0.10 s row skipped (FZP_SKIP shim), no extension at either end.
  codex = handoff/check_fzp.py integrate(): start from an empty network at t=0, trapezoid between observed
          timestamps (every data row, the 0.10 s row included), rows with t > end dropped, the last frame's inventory
          held to end.
Uninserted delay (4b): stage-1 reconstruction (stage1_uninserted.py, imported) with the seed's NC3 anchor, the union of
inputs that queue (queued or remain > 0) in the run set; window [first frame, last frame <= T_end] (ours) or
[0, T_end] (codex)."""
import hashlib
import io
import json
import os
import sys
import time

sys.dont_write_bytecode = True
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
LOCK = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'fzp.lock')
STAGE1 = 'D:/VISSIM-merge/tools/stage1'
STAGE1_SHA = {
    'stage1_common.py': 'e000c69eebad2636c00299727ceb1624d408d5ac3c6ae26204301b1fa891fdae',
    'stage1_scan.py': '651c4f51fdddf49d46c77ed4c28b0626c410b3282426b9fd30f2a6ef43f7625f',
    'stage1_uninserted.py': '19eba94ed01bce47b591b47362aba13b2ac697cfbf2cb9156954b573e7727cd1',
    'stage1_report.py': 'cb4ccc3a431f32ebb6f716a0b67c148a71d82470c443b4851f80832d98d7a1b9',
}
OMEGA701 = 'D:/VISSIM_handoff/20261024/derived/omega_membership_exact.json'
OMEGA701_SHA = 'efdfaeb1b9d0d670119c8e158eabd615033bb1127cabd84d187b064ba64cd473'
REDERIVED = os.path.join(os.path.dirname(HERE), 'net', 'omega', 'omega701_rederived.json')
PARTITION = 'D:/VISSIM_handoff/20261024/derived/reporting_partition.json'
LINK_SETS = ('D:/VISSIM-merge/review-d80faf9/diagnostics/vsl_handoff_20260924/evidence/accounting/'
             'east_link_sets_source.json')
SP = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))          # .../scratchpad/k8
SEEDS = (31, 41, 43)
S7 = {74, 10699, 2, 10613, 119, 10702, 24}
S19 = S7 | {10484, 10490, 10639, 10681, 10481, 10483, 10643, 10682, 129, 31, 68, 70}
WINDOWS = (9000.0, 8100.0)
FZP_SKIP = b'0.10;'


def runner(root, name):
    rd = root + '/' + name
    return {'fzp': rd + '/vissim_eval/sdmpc31_%s_001.fzp' % name, 'inpx': rd + '/network/sdmpc31_%s.inpx' % name,
            'err': rd + '/network/sdmpc31_%s_001.err' % name, 'run_dir': rd}


def nc3(seed):
    a = 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc' % seed
    return {'fzp': a + '/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % seed,
            'inpx': a + '/prepared/network/baseline_s%d_v3c3nc.inpx' % seed,
            'err': a + '/run/baseline_s%d_v3c3nc_001.err' % seed, 'run_dir': a + '/run'}


RVA, RJ1 = 'D:/VISSIM_runs/20261023_sdmpc31_k92', 'D:/VISSIM_runs/20261004_sdmpc31_k8'
J1_NAMES = {31: 'sdmpc31_v3c3_k8j1r_s31', 41: 'sdmpc31_v3c3_k8j1_s41', 43: 'sdmpc31_v3c3_k8j1_s43'}
B_RUNS = {_s: {'fzp': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s%d/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s%d_001.fzp' % (_s, _s),
                'inpx': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s%d/sdmpc/network/sdmpc31_sdmpc9000_s%d.inpx' % (_s, _s),
                'err': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s%d/sdmpc/network/sdmpc31_sdmpc9000_s%d_001.err' % (_s, _s),
                'run_dir': 'D:/VISSIM_runs/20261028_codex_fo_v3c3/s%d/sdmpc' % _s} for _s in SEEDS}   # FO copy (of the B copy): codex-runner layout, FO run root
RUNS = {}
for _s in SEEDS:
    RUNS['va_s%d' % _s] = dict(runner(RVA, 'sdmpc31_v3c3_k92va_s%d' % _s), arm='va', seed=_s)
    RUNS['j1_s%d' % _s] = dict(B_RUNS[_s], arm='j1', seed=_s)   # FO copy: slot j1 = FO
    RUNS['nc3_s%d' % _s] = dict(nc3(_s), arm='nc3', seed=_s)
RUNS['lnc_64cf_s29'] = {'fzp': 'D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp',
                        'inpx': None, 'err': None, 'arm': 'lnc', 'seed': 29, 'run_dir': 'D:/VISSIM_runs/vsl_repro_s29/none/run'}
# existing stage-1 scans (V-A report inputs) for the cross-check, read only
OLD_SCANS = {('va_s%d' % s): SP + '/k92/va/analysis/scans/va_s%d' % s for s in SEEDS}
# B copy: no stage-1 scan exists for the B runs in slot j1 (the J1 scans are not B)
OLD_SCANS.update({('nc3_s%d' % s): SP + '/j1/analysis/scans/nc3_s%d' % s for s in SEEDS})


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def set_below_normal():
    try:
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.GetCurrentProcess.restype = wintypes.HANDLE
        k.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k.GetPriorityClass.argtypes = [wintypes.HANDLE]
        k.GetPriorityClass.restype = wintypes.DWORD
        h = k.GetCurrentProcess()
        k.SetPriorityClass(h, 0x00004000)
        return hex(k.GetPriorityClass(h))
    except Exception as e:  # noqa: BLE001
        return 'unknown: %r' % e


def jdump(o, p):
    tmp = p + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(o, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def import_stage1():
    for n, want in STAGE1_SHA.items():
        got = sha(STAGE1 + '/' + n)
        if got != want:
            raise SystemExit('stage1 %s sha mismatch %s' % (n, got))
    if STAGE1 not in sys.path:
        sys.path.insert(0, STAGE1)
    import stage1_common as C
    import stage1_uninserted as U
    C.find_rule_policy = lambda run_dir: None   # never glob sibling (sealed-seed) folders
    return C, U


# ------------------------------------------------------------------------------------------------ lock
def acquire_lock(tag, max_wait=540.0):
    t0 = time.time()
    while True:
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump({'owner': 'OMEGA701_V3C3', 'pid': os.getpid(), 'tag': tag,
                           'since': time.strftime('%Y-%m-%d %H:%M:%S')}, f)
            return
        except FileExistsError:
            if time.time() - t0 > max_wait:
                raise SystemExit('fzp.lock held by someone else for > %d s; stop' % max_wait)
            time.sleep(10)


def release_lock():
    try:
        with io.open(LOCK, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('pid') == os.getpid():
            os.remove(LOCK)
    except (OSError, ValueError):
        pass


# ------------------------------------------------------------------------------------------------ scan
def scan_fzp(path):
    t_start = time.perf_counter()
    digits = frozenset(b'0123456789')
    with io.open(path, 'rb', buffering=1 << 22) as f:
        cols = None
        for raw in f:
            if raw.startswith(b'$VEHICLE:'):
                cols = raw[len(b'$VEHICLE:'):].strip().decode('ascii').split(';')
                break
        if cols is None:
            raise SystemExit('no $VEHICLE header: ' + path)
        ti, ni, li, mi = (cols.index('SIMSEC'), cols.index('NO'), cols.index('LANE\\LINK\\NO'),
                          cols.index('TMINNETTOT'))
        base = max(ti, ni, li, mi) + 1
        frames_tb, frames_cnt = [], []
        seen = {}
        cur_tb, cnt, skip = None, None, False
        rows = skip_rows = blank_star = other = 0
        for raw in f:
            if raw[0] not in digits:
                s = raw.strip()
                if not s or s.startswith(b'*'):
                    blank_star += 1
                else:
                    other += 1
                continue
            p = raw.split(b';', base)
            tb = p[ti]
            if tb != cur_tb:
                cur_tb = tb
                cnt = {}
                frames_tb.append(tb)
                frames_cnt.append(cnt)
                skip = raw.startswith(FZP_SKIP)
            lk = p[li]
            cnt[lk] = cnt.get(lk, 0) + 1
            rows += 1
            if skip:
                skip_rows += 1
                continue
            no = p[ni]
            if no not in seen:
                seen[no] = (tb, lk, p[mi])
    scan_sec = time.perf_counter() - t_start
    links = sorted({int(k) for c in frames_cnt for k in c})
    idx = {str(l).encode(): i for i, l in enumerate(links)}
    M = np.zeros((len(frames_cnt), len(links)), dtype=np.int32)
    for i, c in enumerate(frames_cnt):
        for k, n in c.items():
            M[i, idx[k]] = n
    t = np.array([float(x) for x in frames_tb])
    skipf = np.array([x + b';' == FZP_SKIP for x in frames_tb])
    veh = np.array([int(k) for k in seen], dtype=np.int64)
    ft = np.array([float(v[0]) for v in seen.values()])
    fl = np.array([int(v[1]) for v in seen.values()], dtype=np.int64)

    def tmf(b):
        try:
            return float(b)
        except ValueError:
            return float('nan')
    ftm = np.array([tmf(v[2]) for v in seen.values()])
    meta = {'fzp': path, 'fzp_bytes': os.path.getsize(path), 'fzp_mtime': os.path.getmtime(path),
            'columns': {'SIMSEC': ti, 'NO': ni, 'LINK': li, 'TMINNETTOT': mi}, 'rows': rows,
            'skip_rows_0p10': skip_rows, 'blank_or_star_lines_after_header': blank_star,
            'other_nondigit_lines_after_header': other, 'frames': int(len(t)),
            'frames_skip_0p10': int(skipf.sum()), 'first_sec': float(t[0]), 'last_sec': float(t[-1]),
            'links_seen': len(links), 'vehicles_seen_ours': int(len(veh)), 'scan_sec': scan_sec}
    return dict(t=t, skipf=skipf, links=np.array(links, dtype=np.int64), M=M, veh=veh, ft=ft, fl=fl, ftm=ftm), meta


def cmd_scan(only=None):
    prio = set_below_normal()
    os.makedirs(CACHE, exist_ok=True)
    log = []
    for tag, r in RUNS.items():
        if only and tag not in only:
            continue
        for k in ('fzp', 'inpx', 'err'):
            if r.get(k) and not os.path.isfile(r[k]):
                raise SystemExit('%s missing %s %s' % (tag, k, r[k]))
        acquire_lock(tag)
        try:
            t_wall = time.strftime('%Y-%m-%d %H:%M:%S')
            arrays, meta = scan_fzp(r['fzp'])
            meta['fzp_sha256'] = sha(r['fzp'])
        finally:
            release_lock()
        meta.update(tag=tag, started=t_wall, priority=prio, inpx=r.get('inpx'), err=r.get('err'),
                    inpx_sha256=sha(r['inpx']) if r.get('inpx') else None,
                    err_sha256=sha(r['err']) if r.get('err') else None)
        np.savez_compressed(os.path.join(CACHE, tag + '.npz'), **arrays)
        jdump(meta, os.path.join(CACHE, tag + '.json'))
        log.append(meta)
        print('%s rows=%d frames=%d first=%.1f last=%.1f skip0.10=%d other=%d links=%d veh=%d scan=%.1fs sha=%s'
              % (tag, meta['rows'], meta['frames'], meta['first_sec'], meta['last_sec'], meta['skip_rows_0p10'],
                 meta['other_nondigit_lines_after_header'], meta['links_seen'], meta['vehicles_seen_ours'],
                 meta['scan_sec'], meta['fzp_sha256'][:16]), flush=True)
    jdump(log, os.path.join(CACHE, 'scan_log.json'))


# ------------------------------------------------------------------------------------------------ metrics
def integ_ours(c, T):
    sel = (~c['skipf']) & (c['t'] <= T + 1e-9)
    tt = c['t'][sel]
    MM = c['M'][sel].astype(np.float64)
    dt = np.diff(tt)
    area = ((MM[:-1] + MM[1:]) * dt[:, None]).sum(0) / 7200.0
    irr = int(np.sum(np.abs(dt - 5.0) > 1e-6))
    return area, {'first': float(tt[0]), 'last': float(tt[-1]), 'frames': int(len(tt)), 'irregular_steps': irr}


def integ_codex(c, T):
    sel = c['t'] <= T + 1e-9
    tt = np.concatenate([[0.0], c['t'][sel]])
    MM = np.vstack([np.zeros((1, c['M'].shape[1])), c['M'][sel].astype(np.float64)])
    dt = np.diff(tt)
    area = ((MM[:-1] + MM[1:]) * dt[:, None]).sum(0) / 7200.0
    area = area + MM[-1] * (T - tt[-1]) / 3600.0
    return area, {'first': float(tt[1]), 'last': float(tt[-1]), 'frames': int(len(tt) - 1),
                  'tail_sec': float(T - tt[-1])}


def insertions(C, net, c):
    """stage1_scan.py insertion attribution, same rules (direct input link, else upstream trace depth 6)."""
    input_by_link = {}
    for inp in net['inputs']:
        input_by_link.setdefault(inp['link'], []).append(inp['no'])
    preds = {}
    for lk, rec in net['links'].items():
        if rec['connector']:
            preds.setdefault(lk, []).append(rec['from_link'])
            preds.setdefault(rec['to_link'], []).append(lk)

    def trace(link, depth=6):
        frontier, visited = [link], {link}
        for _ in range(depth):
            hits = sorted({i for lk in frontier for i in input_by_link.get(lk, [])})
            if hits:
                return hits
            nxt = []
            for lk in frontier:
                for q in preds.get(lk, []):
                    if q not in visited:
                        visited.add(q)
                        nxt.append(q)
            frontier = nxt
            if not frontier:
                break
        return []
    ins = {inp['no']: [] for inp in net['inputs']}
    attrib = {'direct': 0, 'traced': 0, 'ambiguous': 0, 'unattributed': 0}
    cache = {}
    for tf, lk, tm in zip(c['ft'].tolist(), c['fl'].tolist(), c['ftm'].tolist()):
        entry = round(tf - tm, 1) if tm == tm else tf
        if lk in input_by_link:
            hits, kind = input_by_link[lk], 'direct'
        else:
            if lk not in cache:
                cache[lk] = trace(lk)
            hits, kind = cache[lk], 'traced'
        if len(hits) == 1:
            attrib[kind] += 1
            ins[hits[0]].append(entry)
        elif len(hits) > 1:
            attrib['ambiguous'] += 1
        else:
            attrib['unattributed'] += 1
    return {str(k): sorted(v) for k, v in ins.items()}, attrib


def cmd_metrics():
    prio = set_below_normal()
    C, U = import_stage1()
    t_start = time.time()
    # ---------------------------------------------------------------- link sets
    inside635, keys1236, _ = C.membership_inside()
    if sha(OMEGA701) != OMEGA701_SHA:
        raise SystemExit('omega701 membership sha mismatch')
    ex = C.jload(OMEGA701)
    in701 = set(map(int, ex['inside_links']))
    rd = C.jload(REDERIVED)
    set_checks = {'omega635': len(inside635), 'omega701': len(in701),
                  'omega635_subset_701': inside635 <= in701, 'added_66': len(in701 - inside635),
                  'previous_inside_links_eq_635': set(map(int, ex['controlled_intersection_expansion']
                                                          ['previous_inside_links'])) == inside635,
                  'membership_keys_eq_701_inside_outside': keys1236 == (in701 | set(map(int, ex['outside_links'])))}
    for k, v in rd.items():
        ins_ = v if isinstance(v, list) else (v.get('inside_links') or v.get('inside'))
        if ins_ is not None:
            set_checks['rederived_%s_eq_701' % k] = set(map(int, ins_)) == in701
    part = C.jload(PARTITION)
    on = {int(k): v for k, v in part['onramp_roads'].items()}
    off = set(map(int, part['offramp_links']))
    ls = C.jload(LINK_SETS)['link_sets']
    our19 = set()
    for k in ('mainline', 'on_connectors', 'off_connectors', 'on_approaches'):
        our19 |= set(map(int, ls[k]))
    set_checks['our_local19_eq_codex_S19'] = our19 == S19
    # ---------------------------------------------------------------- per run
    caches, metas, nets, chains, uns, ins_all, attribs = {}, {}, {}, {}, {}, {}, {}
    for tag, r in RUNS.items():
        z = np.load(os.path.join(CACHE, tag + '.npz'))
        caches[tag] = {k: z[k] for k in z.files}
        metas[tag] = C.jload(os.path.join(CACHE, tag + '.json'))
        if r.get('inpx'):
            net = C.load_network(r['inpx'])
            nets[tag] = net
            chains[tag] = C.chains(net)
    fw_e = set(chains['nc3_s31']['FW_E']['links'])
    fw_w = set(chains['nc3_s31']['FW_W']['links'])
    for tag in nets:
        if set(chains[tag]['FW_E']['links']) != fw_e or set(chains[tag]['FW_W']['links']) != fw_w:
            raise SystemExit('chain differs ' + tag)
    set_checks['fw_e_chain_eq_S7'] = fw_e == S7
    set_checks['fw_w_chain'] = sorted(fw_w)

    def link_groups(links):
        L = [int(x) for x in links]
        g = {}
        g['omega635'] = np.array([l in inside635 for l in L])
        g['omega701'] = np.array([l in in701 for l in L])
        g['fw_e7'] = np.array([l in S7 for l in L])
        g['local19'] = np.array([l in S19 for l in L])
        g['fw_w_main'] = np.array([l in fw_w for l in L])
        g['omega701_minus_west'] = g['omega701'] & ~g['fw_w_main']
        g['onramps_E'] = np.array([l in in701 and l not in fw_e and l not in fw_w and on.get(l) == 'FW_E' for l in L])
        g['onramps_W'] = np.array([l in in701 and l not in fw_e and l not in fw_w and on.get(l) == 'FW_W' for l in L])
        g['offramps'] = np.array([l in in701 and l not in fw_e and l not in fw_w and l not in on and l in off for l in L])
        g['urban_roads'] = (g['omega701'] & ~g['fw_e7'] & ~g['fw_w_main'] & ~g['onramps_E'] & ~g['onramps_W']
                            & ~g['offramps'])
        g['all'] = np.ones(len(L), bool)
        g['not_in_1236'] = np.array([l not in keys1236 for l in L])
        return g
    GROUPS = ['omega635', 'omega701', 'omega701_minus_west', 'urban_roads', 'offramps', 'onramps_E', 'onramps_W',
              'fw_e7', 'fw_w_main', 'local19', 'all']
    link_tot = {}
    per_link_rows = []
    for tag, c in caches.items():
        g = link_groups(c['links'])
        res = {}
        for conv, fn in (('ours', integ_ours), ('codex', integ_codex)):
            for T in WINDOWS:
                area, info = fn(c, T)
                key = '%s_%d' % (conv, int(T))
                res[key] = {'links': {grp: float(area[g[grp]].sum()) for grp in GROUPS}, 'window': info,
                            'not_in_1236_veh_h': float(area[g['not_in_1236']].sum())}
                for l, a in zip(c['links'].tolist(), area.tolist()):
                    per_link_rows.append((tag, key, l, a))
        link_tot[tag] = res
    # ---------------------------------------------------------------- uninserted (v3c3 runs only)
    for tag in nets:
        c, r, net = caches[tag], RUNS[tag], nets[tag]
        ins, att = insertions(C, net, c)
        ins_all[tag], attribs[tag] = ins, att
        err = C.parse_err(r['err'])
        sel = (~c['skipf'])
        ft_ours = c['t'][sel]
        scan_like = {'tag': tag, 'frames': {'first_sec': float(ft_ours[0]), 'last_sec': float(ft_ours[-1])},
                     'n_bins': 60, 'bin_sec': 150, 'err': {'remains': {str(k): v for k, v in err['remains'].items()},
                                                            'removals': len(err['removals'])},
                     'frame_series': {'t': ft_ours.tolist()},
                     'insertions': {k: {'entry_times': v} for k, v in ins.items()}}
        uns[tag] = U.reconstruct_from_scan(scan_like, net)
        uns[tag]['_removals'] = len(err['removals'])
        uns[tag]['_removals_outside635'] = sum(1 for _, _, l in err['removals'] if l not in inside635)
        uns[tag]['_removals_outside701'] = sum(1 for _, _, l in err['removals'] if l not in in701)
    unions = {}
    for uname, arms in (('U9', ('va', 'j1', 'nc3')), ('U6VA', ('va', 'nc3')), ('U6J1', ('j1', 'nc3'))):
        src = set()
        for tag in nets:
            if RUNS[tag]['arm'] in arms:
                for k, v in uns[tag]['inputs'].items():
                    if v.get('queued') or v.get('remain_err', 0) > 0:
                        src.add(k)
        unions[uname] = sorted(src, key=int)
    anchors = {s: {k: v['anchored_total_generated'] for k, v in uns['nc3_s%d' % s]['inputs'].items()} for s in SEEDS}
    unins = {}
    for tag in nets:
        s = RUNS[tag]['seed']
        c = caches[tag]
        sel = (~c['skipf'])
        ft_ours = c['t'][sel]
        out = {}
        for uname, keys in unions.items():
            for conv in ('ours', 'codex'):
                for T in WINDOWS:
                    if conv == 'ours':
                        t0 = float(ft_ours[0])
                        t1 = float(ft_ours[ft_ours <= T + 1e-9][-1])
                    else:
                        t0, t1 = 0.0, T
                    per = {}
                    for k in keys:
                        rec = uns[tag]['inputs'].get(k)
                        if not rec or 'clipped_bins_veh_h' not in rec:
                            continue
                        b_, _ = U.clipped_series(rec['schedule'], ins_all[tag][k], anchors[s][k], t0, t1,
                                                 ft_ours[:2], 60, 150)
                        per[k] = float(b_.sum())
                    out['%s|%s_%d' % (uname, conv, int(T))] = {
                        'total': sum(per.values()), 'i1098': per.get('1098', 0.0), 'i1099': per.get('1099', 0.0),
                        'urban_inputs': sum(v for k, v in per.items() if k not in ('1098', '1099')),
                        'per_input': per, 't0': t0, 't1': t1}
        unins[tag] = out
    # ---------------------------------------------------------------- assemble metrics per run
    def metrics_for(tag, conv, T, uname):
        L = link_tot[tag]['%s_%d' % (conv, int(T))]['links']
        u = unins[tag]['%s|%s_%d' % (uname, conv, int(T))]
        m = {'Omega635': L['omega635'], 'Omega701': L['omega701'], 'Omega701_minus_west': L['omega701_minus_west'],
             'urban_roads': L['urban_roads'], 'offramps701': L['offramps'], 'onramps_E': L['onramps_E'],
             'onramps_W': L['onramps_W'], 'FW_E7': L['fw_e7'], 'FW_W_main': L['fw_w_main'], 'local19': L['local19'],
             'M4a': L['all'], 'M4b': u['total'], 'unins_1098': u['i1098'], 'unins_1099': u['i1099'],
             'unins_urban': u['urban_inputs']}
        m['M4'] = m['M4a'] + m['M4b']
        m['out_a_635'] = m['M4'] - m['Omega635']
        m['out_b_635'] = m['M4a'] - m['Omega635']
        m['out_a_701'] = m['M4'] - m['Omega701']
        m['out_b_701'] = m['M4a'] - m['Omega701']
        return m
    table = {}
    for tag in nets:
        for conv in ('ours', 'codex'):
            for T in WINDOWS:
                for uname in unions:
                    table['%s|%s_%d|%s' % (tag, conv, int(T), uname)] = metrics_for(tag, conv, T, uname)
    pairs = {}
    for s in SEEDS:
        for pname, a, b in (('VA-NC3', 'va', 'nc3'), ('J1-NC3', 'j1', 'nc3'), ('VA-J1', 'va', 'j1')):
            for conv in ('ours', 'codex'):
                for T in WINDOWS:
                    for uname in unions:
                        ka = '%s_s%d|%s_%d|%s' % (a, s, conv, int(T), uname)
                        kb = '%s_s%d|%s_%d|%s' % (b, s, conv, int(T), uname)
                        pairs['%s|s%d|%s_%d|%s' % (pname, s, conv, int(T), uname)] = {
                            k: table[ka][k] - table[kb][k] for k in table[ka]}
    # ---------------------------------------------------------------- cross-checks
    checks = {'sets': set_checks}
    # (1) ours 0-9000 vs existing stage-1 scans (V-A report inputs)
    x1 = {}
    for tag, d in OLD_SCANS.items():
        sc = C.jload(d + '/scan.json')
        un_old = C.jload(d + '/uninserted.json')
        mine = link_tot[tag]['ours_9000']['links']
        c = caches[tag]
        area, _ = integ_ours(c, 9000.0)
        lv = sc['link_vh']
        per_link_max = 0.0
        for l, a in zip(c['links'].tolist(), area.tolist()):
            old = sum(lv.get(str(l), [0.0]))
            per_link_max = max(per_link_max, abs(old - a))
        old_un = {k: (v['anchored_total_generated'], v.get('queued'), v['remain_err'], v['inserted_seen'],
                      round(v.get('delay_veh_h', 0.0), 6)) for k, v in un_old['inputs'].items()}
        new_un = {k: (v['anchored_total_generated'], v.get('queued'), v['remain_err'], v['inserted_seen'],
                      round(v.get('delay_veh_h', 0.0), 6)) for k, v in uns[tag]['inputs'].items()}
        diff_un = {k: (old_un.get(k), new_un.get(k)) for k in set(old_un) | set(new_un) if old_un.get(k) != new_un.get(k)}
        x1[tag] = {'rows_old': sc['rows'], 'rows_new_ours': metas[tag]['rows'] - metas[tag]['skip_rows_0p10'],
                   'vehicles_old': sc['vehicles_seen'], 'vehicles_new': metas[tag]['vehicles_seen_ours'],
                   'omega635_old': sc['totals']['omega_ttt_veh_h'], 'omega635_new': mine['omega635'],
                   'omega635_diff': mine['omega635'] - sc['totals']['omega_ttt_veh_h'],
                   'all_old': sc['totals']['all_ttt_veh_h'], 'all_new': mine['all'],
                   'all_diff': mine['all'] - sc['totals']['all_ttt_veh_h'],
                   'per_link_max_abs_diff_vs_rounded_bins': per_link_max,
                   'attribution_old': {k: sc['insertion_attribution'].get(k) for k in attribs[tag]},
                   'attribution_new': attribs[tag],
                   'uninserted_total_old': un_old['total_veh_h'], 'uninserted_total_new': uns[tag]['total_veh_h'],
                   'uninserted_input_records_differing': diff_un,
                   'removals_old': sc['err']['removals'], 'removals_new': uns[tag]['_removals']}
    checks['vs_stage1_scans'] = x1
    # (2) codex convention on LNC (= codex NC, VT 2.1) vs codex evidence and the codex partition
    lnc = link_tot['lnc_64cf_s29']['codex_8100']['links']
    ifc = C.jload('D:/VISSIM_handoff/20261024/derived/independent_fzp_counts.json')['nc']
    summ = C.jload('D:/VISSIM_handoff/20261024/analysis/comparison/summary.json')['reporting_partition']['parts']['nc']
    wwm = C.jload('D:/VISSIM_handoff/20261024/analysis/comparison/without_west_mainline.json')
    wwm_nc = [x for x in wwm['comparison'] if x['condition'] == 'nc'][0]
    checks['lnc_vs_codex'] = {
        'rows_le_8100': (int(caches['lnc_64cf_s29']['M'][caches['lnc_64cf_s29']['t'] <= 8100.0].sum()), ifc['rows']),
        'frames': (link_tot['lnc_64cf_s29']['codex_8100']['window']['frames'], ifc['frames']),
        'FW_E_7': (lnc['fw_e7'], ifc['FW_E_7'], lnc['fw_e7'] - ifc['FW_E_7']),
        'local_19': (lnc['local19'], ifc['local_19'], lnc['local19'] - ifc['local_19']),
        'Omega701': (lnc['omega701'], ifc['Omega701'], lnc['omega701'] - ifc['Omega701']),
        'whole_observed': (lnc['all'], ifc['whole_observed'], lnc['all'] - ifc['whole_observed']),
        'part_FW_E': (lnc['fw_e7'], summ['FW_E'], lnc['fw_e7'] - summ['FW_E']),
        'part_FW_W': (lnc['fw_w_main'], summ['FW_W'], lnc['fw_w_main'] - summ['FW_W']),
        'part_onramps_E': (lnc['onramps_E'], summ['onramps_E'], lnc['onramps_E'] - summ['onramps_E']),
        'part_onramps_W': (lnc['onramps_W'], summ['onramps_W'], lnc['onramps_W'] - summ['onramps_W']),
        'part_urban_roads': (lnc['urban_roads'], summ['urban_roads'], lnc['urban_roads'] - summ['urban_roads']),
        'part_offramps': (lnc['offramps'], summ['offramps'], lnc['offramps'] - summ['offramps']),
        'part_outside': (lnc['all'] - lnc['omega701'], summ['outside'], lnc['all'] - lnc['omega701'] - summ['outside']),
        'omega701_minus_west': (lnc['omega701_minus_west'], wwm_nc['ttt_veh_h'],
                                lnc['omega701_minus_west'] - wwm_nc['ttt_veh_h']),
        'lnc_omega635_codex_8100': lnc['omega635'],
        'lnc_ours_8100': link_tot['lnc_64cf_s29']['ours_8100']['links'],
    }
    out = {'schema': 'omega701-v3c3/v1', 'made': time.strftime('%Y-%m-%d %H:%M:%S'), 'priority': prio,
           'tool_sha256': sha(os.path.abspath(__file__)), 'stage1_sha256': STAGE1_SHA,
           'inputs_sha256': {'omega701_membership': OMEGA701_SHA, 'reporting_partition': sha(PARTITION),
                             'sim3_membership': sha(C.MEMBERSHIP), 'link_sets': sha(LINK_SETS)},
           'unions': unions, 'anchors_nc3': {str(s): {k: anchors[s][k] for k in unions['U9']} for s in SEEDS},
           'scan_meta': metas, 'link_totals': link_tot, 'unins': unins, 'table': table, 'pairs': pairs,
           'checks': checks, 'attribution': attribs,
           'removals': {t: {'all': uns[t]['_removals'], 'outside635': uns[t]['_removals_outside635'],
                            'outside701': uns[t]['_removals_outside701']} for t in nets},
           'remains': {t: {k: v['remain_err'] for k, v in uns[t]['inputs'].items() if v['remain_err']} for t in nets},
           'seconds': time.time() - t_start}
    jdump(out, os.path.join(HERE, 'omega701_v3c3.json'))
    with io.open(os.path.join(HERE, 'omega701_per_link.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('run,convention_window,link,veh_h\n')
        for row in per_link_rows:
            f.write('%s,%s,%d,%.9f\n' % row)
    print('metrics done in %.1f s; unions %s' % (out['seconds'], {k: len(v) for k, v in unions.items()}), flush=True)


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('scan', 'metrics'):
        raise SystemExit(__doc__)
    if sys.argv[1] == 'scan':
        cmd_scan(set(sys.argv[2:]) or None)
    else:
        cmd_metrics()
