r"""V-A analysis step 3 (amendment 34 sec.8.3-10 SC1001 EB local, 8.3-12 U9-a DESSPEED, FZP parts of 8.3-3 link 174
and 8.3-6 SC109 east links).  One read-only streaming pass per distinct FZP (V-A 3, J1 3, NC3 3; in the selftest
profile the V-A arm is J1, so 6 distinct files).  Runner FZP 0.10 s row skipped.  BELOW_NORMAL, one file at a time.
python -B va_fzp_local.py --profile va|selftest  ->  <out>/va_local.json
F1 spill definition copied from J1 an_fzp_local.py (= scratchpad/sc1001eb/tools/a1_stopline.py:26-27, 80-100, 232-237).
Pairs: A = V-A - NC3, B = V-A - J1 (statistics as J1, report only).  Frame counts per frame of link 174 (all lanes) and
links 1220000704 / 1220000803: mean, max, time of max over windows (F) all frames, (P) 1800-7200 s, and from 4350 s.
DESSPEED (V-A arm only): first frame of a vehicle in an FW_E zone [p_z, e_z) on the FW_E chain within (T, T+150] of a
SDMPC decision T (900 ... 8850); band reading C (m = command c) and reading M (m = written M(c) in {81, 91, 101, 110}),
both reported, none chosen; m = 110 band [98, 140]."""
import json
import math
import os
import statistics
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import va_common as V  # noqa: E402

ZONES_E = ['FW_E__seg0', 'FW_E__seg5', 'FW_E__seg10', 'FW_E__seg15']
MAP_M = {80.0: 81.0, 90.0: 91.0, 100.0: 101.0, 110.0: 110.0}
WINDOWS = (('P_1800_7200', 1800.0, 7200.0), ('F_all', -1.0, 1e9), ('from_4350', 4350.0, 1e9))


def header(path):
    with open(path, 'rb') as f:
        for i, raw in enumerate(f):
            if raw.startswith(b'$VEHICLE:'):
                cols = raw[len(b'$VEHICLE:'):].strip().decode('ascii', 'replace').split(';')
                return {c: cols.index(c) for c in ('SIMSEC', 'NO', 'LANE\\LINK\\NO', 'LANE\\INDEX', 'POS', 'SPEED',
                                                    'DESSPEED', 'ROUTDECNO', 'ROUTENO')}
            if i > 200:
                break
    raise SystemExit('no header ' + path)


def windows_events(flags, frames, t0=900.0, t1=9000.0):
    """J1 an_fzp_local.windows_events (a1_stopline.windows_events without pandas)."""
    g = {}
    for t, fl in zip(frames, flags):
        if t0 <= t < t1:
            w = int((t - t0) // 30)
            g[w] = g.get(w, 0) + int(fl)
    ks = sorted(g)
    ev = {k: g[k] >= 3 for k in ks}
    starts = [t0 + k * 30 for k in ks if ev[k]]
    pk = [k for k in ks if 1800 <= t0 + k * 30 < 7200]
    return {'frac_all': sum(ev[k] for k in ks) / len(ks) if ks else None,
            'frac_peak': sum(ev[k] for k in pk) / len(pk) if pk else None,
            'n_windows': len(ks), 'n_windows_peak': len(pk),
            'n_event_windows': sum(ev[k] for k in ks), 'n_event_windows_peak': sum(ev[k] for k in pk),
            'first': starts[0] if starts else None, 'total_event_s': sum(ev[k] for k in ks) * 30}


def scan_fzp(path, skip, chainE, zones, want_zone):
    ix = header(path)
    I_T, I_NO, I_LK, I_LN, I_POS, I_SP, I_DS, I_RD, I_RN = (ix['SIMSEC'], ix['NO'], ix['LANE\\LINK\\NO'],
                                                            ix['LANE\\INDEX'], ix['POS'], ix['SPEED'], ix['DESSPEED'],
                                                            ix['ROUTDECNO'], ix['ROUTENO'])
    nsplit = max(I_T, I_NO, I_LK, I_LN, I_POS, I_SP, I_DS, I_RD, I_RN) + 1
    offE = {str(k).encode(): v for k, v in chainE.items()}
    K174, K704, K803 = b'174', str(V.EAST_LINKS[0]).encode(), str(V.EAST_LINKS[1]).encode()
    frames, c10491, c127_12, spW, spE, c174, c704, c803 = [], [], [], [], [], [], [], []
    cur_tb = None
    n491 = n127 = n174 = n704 = n803 = 0
    fW = fE = False
    minseen = {}
    first_in_zone = {}
    zp = [(z['p'], z['e']) for z in zones]
    skipped = rows = 0
    t = None
    with open(path, 'rb', buffering=1 << 22) as f:
        for raw in f:
            c0 = raw[:1]
            if not (b'0' <= c0 <= b'9'):
                continue
            if skip and raw.startswith(skip):
                skipped += 1
                continue
            p = raw.split(b';', nsplit)
            tb = p[I_T]
            if tb != cur_tb:
                if cur_tb is not None:
                    frames.append(float(cur_tb))
                    c10491.append(n491); c127_12.append(n127); spW.append(fW); spE.append(fE)
                    c174.append(n174); c704.append(n704); c803.append(n803)
                cur_tb = tb
                n491 = n127 = n174 = n704 = n803 = 0
                fW = fE = False
                t = float(tb)
            rows += 1
            lk = p[I_LK]
            if lk == b'10491':
                n491 += 1
                if not fW and float(p[I_POS]) <= 30 and float(p[I_SP]) < 15:
                    fW = True
            elif lk == b'127':
                if p[I_LN] in (b'1', b'2'):
                    n127 += 1
            elif lk == b'26':
                if not fW and p[I_LN] == b'1' and p[I_RD] == b'1132' and p[I_RN] == b'2':
                    pos = float(p[I_POS])
                    if 3550 <= pos <= 3651 and float(p[I_SP]) < 15:
                        fW = True
            elif lk == b'10481':
                if not fE and float(p[I_POS]) <= 30 and float(p[I_SP]) < 15:
                    fE = True
            elif lk == K174:
                n174 += 1
            elif lk == K704:
                n704 += 1
            elif lk == K803:
                n803 += 1
            if lk in offE:
                if lk == b'2' and not fE and p[I_LN] == b'1' and p[I_RD] == b'1131' and p[I_RN] == b'2':
                    pos = float(p[I_POS])
                    if 3950 <= pos <= 4092.3 and float(p[I_SP]) < 15:
                        fE = True
                if want_zone:
                    cp = offE[lk] + float(p[I_POS])
                    no = p[I_NO]
                    prev_min = minseen.get(no)
                    for zi, (pz, ez) in enumerate(zp):
                        if pz <= cp < ez:
                            key = (no, zi)
                            if key not in first_in_zone:
                                first_in_zone[key] = (t, float(p[I_DS]) if p[I_DS] else None,
                                                      prev_min is not None and prev_min < pz)
                            break
                    if prev_min is None or cp < prev_min:
                        minseen[no] = cp
        if cur_tb is not None:
            frames.append(float(cur_tb))
            c10491.append(n491); c127_12.append(n127); spW.append(fW); spE.append(fE)
            c174.append(n174); c704.append(n704); c803.append(n803)
    return {'frames': frames, 'c10491': c10491, 'c127_12': c127_12, 'spW': spW, 'spE': spE, 'c174': c174,
            'c704': c704, 'c803': c803, 'first_in_zone': first_in_zone, 'skipped': skipped, 'rows': rows}


def occ_stats(frames, vals, with_t=False):
    out = {}
    for nm, lo, hi in WINDOWS:
        sel = [(t, x) for t, x in zip(frames, vals) if lo <= t < hi]
        v = [x for _, x in sel]
        r = {'n_frames': len(v), 'mean': statistics.fmean(v) if v else None, 'max': max(v) if v else None}
        if with_t and v:
            r['max_t'] = sel[v.index(max(v))][0]
        out[nm] = r
    return out


def commands(dec):
    out = {}
    for T, p in V.action_files(dec):
        if T < 900 or T >= 9000:
            continue
        v = V.load_json_bytes(p).get('vsl') or {}
        out[T] = {z: float(v.get(z, v.get('FW_E', 110.0))) for z in ZONES_E}
    return out


def pstats(vals, bases, ncs):
    st = V.stats(vals, ncs)
    st['per_seed'] = vals
    st['base'] = bases
    return st


def band(m):
    return (98.0, 140.0) if m >= 110 else (m - 1.0, m + 1.0)


def desspeed(cmd, fiz):
    by_zone = {}
    for (no, zi), (t, ds, passed) in fiz.items():
        by_zone.setdefault(zi, []).append((t, ds, passed))
    agg, per_zone, cells = {}, {}, []
    for T, zc in sorted(cmd.items()):
        for zi, z in enumerate(ZONES_E):
            c = zc[z]
            for reading, m in (('C_command', c), ('M_written', MAP_M.get(c, c))):
                lo, hi = band(m)
                sub = [x for x in by_zone.get(zi, []) if T < x[0] <= T + 150]
                for t, ds, passed in sub:
                    grp = 'sign_passed' if passed else 'no_upstream_obs'
                    for tgt in (agg.setdefault(reading, {}).setdefault('%g' % c, {}),
                                per_zone.setdefault(reading, {}).setdefault('%g' % c, {}).setdefault(z, {})):
                        a = tgt.setdefault(grp, {'n': 0, 'in_band': 0, 'ds_missing': 0, 'band': [lo, hi]})
                        a['n'] += 1
                        if ds is None:
                            a['ds_missing'] += 1
                        elif lo <= ds <= hi:
                            a['in_band'] += 1
                if c < 110 and reading == 'C_command':
                    sp = [x for x in sub if x[2]]
                    cells.append({'T': T, 'zone': z, 'c': c, 'n_sign_passed': len(sp),
                                  'in_band_C': sum(1 for x in sp if x[1] is not None and c - 1 <= x[1] <= c + 1),
                                  'in_band_M': sum(1 for x in sp if x[1] is not None and
                                                   MAP_M.get(c, c) - 1 <= x[1] <= MAP_M.get(c, c) + 1),
                                  'n_no_upstream_obs': len(sub) - len(sp)})
    for d in (agg, per_zone):
        stack = [d]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if 'n' in x and 'in_band' in x:
                    x['frac_in_band'] = x['in_band'] / x['n'] if x['n'] else None
                else:
                    stack.extend(x.values())
    return {'by_level': agg, 'by_level_zone': per_zone, 'below110_cells': cells}


def main():
    prof = V.profile_from_argv()
    pin = V.require_pinned(prof, __file__)
    t0 = time.time()
    prio = V.set_below_normal()
    C = V.import_stage1()
    va31 = prof.va_run(31)
    net = C.load_network(va31['inpx'])
    ch = C.chains(net)
    zext = C.zone_extents(net, ch, C.DEFAULT_ZONE_DSDS)
    zones = [{'zone': z, 'p': min(zext[z]['sign_chain_pos_m']), 'e': zext[z]['end_m'], 'start_m': zext[z]['start_m'],
              'signs': zext[z]['sign_chain_pos_m']} for z in ZONES_E]
    chainE = ch['FW_E']['offsets_m']
    res = {'schema': 'k92-va-local/v1', 'profile': prof.name, 'pinned': pin, 'priority': hex(prio),
           'zones_FW_E': zones, 'zone_net': va31['inpx'], 'runs': {}, 'desspeed': {}}
    files = {}
    for s in V.SEEDS:
        files['va_s%d' % s] = (prof.va_run(s)['fzp'], V.FZP_SKIP)
        files['j1_s%d' % s] = (V.j1_run(s)['fzp'], V.FZP_SKIP)
        files['nc3_s%d' % s] = (V.nc3_run(s)['fzp'], None)
    cache, scans = {}, {}
    for tag in sorted(files, key=lambda x: (x.split('_')[0] != 'va', x)):
        path, skip = files[tag]
        key = os.path.normcase(os.path.abspath(path))
        t1 = time.time()
        if key in cache:
            sc = cache[key]
            reused = True
        else:
            sc = scan_fzp(path, skip, chainE, zones, want_zone=tag.startswith('va_'))
            cache[key] = sc
            reused = False
        scans[tag] = sc
        res['runs'][tag] = {
            'fzp': path, 'reused_pass': reused, 'rows': sc['rows'], 'skipped': sc['skipped'], 'n_frames': len(sc['frames']),
            'first_frame': sc['frames'][0], 'last_frame': sc['frames'][-1],
            'occ_10491': occ_stats(sc['frames'], sc['c10491']),
            'occ_127_lanes12': occ_stats(sc['frames'], sc['c127_12']),
            'spill_FW_W': windows_events(sc['spW'], sc['frames']),
            'spill_FW_E': windows_events(sc['spE'], sc['frames']),
            'occ_174': occ_stats(sc['frames'], sc['c174'], with_t=True),
            'occ_1220000704': occ_stats(sc['frames'], sc['c704'], with_t=True),
            'occ_1220000803': occ_stats(sc['frames'], sc['c803'], with_t=True),
            'wall_sec': round(time.time() - t1, 1)}
        print(tag, 'rows', sc['rows'], 'frames', len(sc['frames']), 'reused', reused,
              'wall %.1f' % (time.time() - t1), flush=True)
    paired = {}
    for pk, base in (('A', 'nc3'), ('B', 'j1')):
        pp = {}
        for item in ('occ_10491', 'occ_127_lanes12', 'occ_174', 'occ_1220000704', 'occ_1220000803'):
            for win in [w[0] for w in WINDOWS]:
                for stat in ('mean', 'max'):
                    k = '%s.%s.%s' % (item, win, stat)
                    b = [res['runs']['%s_s%d' % (base, s)][item][win][stat] for s in V.SEEDS]
                    a = [res['runs']['va_s%d' % s][item][win][stat] for s in V.SEEDS]
                    nc = [res['runs']['nc3_s%d' % s][item][win][stat] for s in V.SEEDS]
                    pp[k] = dict(pstats([x - y for x, y in zip(a, b)], b, nc), arm=a)
        for item in ('spill_FW_W', 'spill_FW_E'):
            for stat in ('frac_peak', 'frac_all'):
                k = '%s.%s' % (item, stat)
                b = [res['runs']['%s_s%d' % (base, s)][item][stat] for s in V.SEEDS]
                a = [res['runs']['va_s%d' % s][item][stat] for s in V.SEEDS]
                nc = [res['runs']['nc3_s%d' % s][item][stat] for s in V.SEEDS]
                pp[k] = dict(pstats([x - y for x, y in zip(a, b)], b, nc), arm=a)
        paired[pk] = pp
    res['paired'] = paired
    for s in V.SEEDS:
        cmd = commands(prof.va_run(s)['dec'])
        d = desspeed(cmd, scans['va_s%d' % s]['first_in_zone'])
        tot = sum(a['n'] for g in d['by_level'].get('C_command', {}).values() for a in g.values())
        nup = sum(a['n'] for g in d['by_level'].get('C_command', {}).values() for gg, a in g.items()
                  if gg == 'no_upstream_obs')
        d['n_total'] = tot
        d['share_no_upstream_obs'] = nup / tot if tot else None
        d['n_decisions'] = len(cmd)
        res['desspeed']['s%d' % s] = d
    res['elapsed_sec'] = round(time.time() - t0, 1)
    V.jdump(res, os.path.join(prof.out, 'va_local.json'))
    print('elapsed', res['elapsed_sec'])


if __name__ == '__main__':
    main()
