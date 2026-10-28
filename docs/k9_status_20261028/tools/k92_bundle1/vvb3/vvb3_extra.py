"""VerifyVB 3 -- report-only extras of the V-B report r2 that vvb3_recalc.py does not recompute.  Written AFTER the
report r2 was read (disclosed); every judged number (VB-I, VB-M, ZI z2-z6, selection, hook names, archive) comes from
the pinned vvb3_recalc.py run.  This file only recounts report-only items:
  - ZI: z1_off hook-off output vs the RR record (amendment 32 section 3.5 (b)) with the pinned comparator
    (vvb3_recalc.compare_dec), the hook cost table, the distinct wall-clock paths of each cell;
  - chain decision wall clock (done records) and the SDMPC medians, RR decision_wall_sec median of the same T;
  - done records: tree / tool bytes before and after, receipts; stage records; STOP files; VBR size;
  - the B1 / OFF ranges over the 8 shared states (from out/vvb3_recalc.json).
Standard library + numpy (through vvb3_recalc) only; no driver / recalculator / hook / harness import.

    python -B vvb3_extra.py run   -> out/vvb3_extra.json"""
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vvb3_recalc as R  # noqa: E402

VBR = R.VBR


def main():
    out = {'tool_sha256': R.fsha(__file__), 'recalc_tool_sha256': R.fsha(R.__file__)}
    rc = json.loads((R.OUT / 'vvb3_recalc.json').read_text(encoding='utf-8'))
    out['recalc_json_sha256'] = R.fsha(R.OUT / 'vvb3_recalc.json')
    # ZI extras
    zi = {}
    for cell, run, T in R.ZI:
        cd = VBR / 'zi' / cell
        s = R.t6(T)
        d = {}
        if cell == 'z1_off':
            rep = R.compare_dec(R.rr_dir(run), cd / 'replay_off', T, R.VBT, R.FRZ8)
            d['off_vs_record'] = {'verdict': rep['verdict'], 'hard_same': rep.get('hard_same'),
                                  'unclassified_n': rep.get('unclassified_n'), 'allowed': rep.get('allowed'),
                                  'csv_same': rep.get('csv_same')}
        a = R.nobj(json.loads((cd / 'replay_off' / ('action_%s.json' % s)).read_text(encoding='utf-8-sig')))
        b = R.nobj(json.loads((cd / 'replay_on' / ('action_%s.json' % s)).read_text(encoding='utf-8-sig')))
        dd = []
        R.ddiff(a, b, '', dd)
        d['n_diff_leaves'] = len(dd)
        d['wallclock_paths_distinct'] = len({R.gpath(p) for p, k, x, y in dd if R.wallclock(p, k, x, y)})
        d['other'] = [R.gpath(p) for p, k, x, y in dd if not R.wallclock(p, k, x, y)][:20]
        del a, b
        ron = R.jload(cd / 'replay_on' / ('run_t%s.json' % s)) or {}
        roff = R.jload(cd / 'replay_off' / ('run_t%s.json' % s)) or {}
        hook = cd / 'hook_on'
        cands = [p for p in hook.iterdir() if p.is_dir() and p.name.startswith('c_')]
        hs = [R.fnum((R.jload(p / 'cand.json') or {}).get('hook_sec')) for p in cands]
        d.update({'wall_off': roff.get('wall_sec'), 'wall_on': ron.get('wall_sec'),
                  'n_candidates': len(cands), 'hook_sec_total': math.fsum(x for x in hs if x is not None),
                  'candidate_mb': sum(f.stat().st_size for p in cands for f in p.iterdir()) / 1e6,
                  'n_loaded': len([p for p in hook.iterdir() if p.name.startswith('loaded_')])})
        zi[cell] = d
    out['zi'] = zi
    # chain walls, done records
    walls, tree_ok, receipts, prev_rule = {}, True, 0, []
    sd_b1, sd_off, rec_t = [], [], []
    for arm in ('off', 'b1'):
        for c in R.CHAINS:
            ws = []
            for T in (c['off'] if arm == 'off' else c['times']):
                P = R.dec_paths(c['key'], arm, T)
                dn = R.jload(P['done']) or {}
                rr = R.jload(P['run']) or {}
                ws.append(dn.get('wall_sec'))
                tree_ok = tree_ok and all((dn.get('tree_files_ok_before') or {'x': False}).values()) and \
                    all((dn.get('tree_files_ok_after') or {'x': False}).values())
                if dn.get('receipt'):
                    receipts += 1
                prev_rule.append([c['chain'], arm, T, dn.get('previous')])
                if T >= 900:
                    (sd_b1 if arm == 'b1' else sd_off).append(R.fnum(rr.get('wall_sec')))
                    if arm == 'b1':
                        rec_t.append((c['run'], T))
            ws = [w for w in ws if R.isnum(w)]
            walls['%s/%s' % (c['chain'], arm)] = {'n': len(ws), 'sum_h': sum(ws) / 3600.0, 'min': min(ws),
                                                  'max': max(ws)}
    out['walls'] = walls
    out['walls_sum_h'] = {'off': sum(v['sum_h'] for k, v in walls.items() if k.endswith('/off')),
                          'b1': sum(v['sum_h'] for k, v in walls.items() if k.endswith('/b1'))}
    out['sdmpc_wall_median'] = {'b1_n': len(sd_b1), 'b1': statistics.median(sd_b1), 'b1_min': min(sd_b1),
                                'b1_max': max(sd_b1), 'off_n': len(sd_off), 'off': statistics.median(sd_off),
                                'off_min': min(sd_off), 'off_max': max(sd_off)}
    rw = []
    for run, T in rec_t:
        d = R.jload(R.rr_dir(run) / ('action_%s.json' % R.t6(T))) or {}
        rw.append(R.fnum((d.get('metadata') or {}).get('decision_wall_sec')))
        del d
    out['rec_decision_wall_median'] = {'n': len(rw), 'median': statistics.median(rw)}
    out['done_tree_files_ok_all'] = tree_ok
    out['receipts_written'] = receipts
    out['previous'] = prev_rule
    # stages, STOP files, VBR size, driver end
    out['stages'] = sorted(p.name for p in (VBR / 'stages').glob('*.json'))
    out['stop_files'] = sorted(p.name for p in VBR.glob('STOP_vb_*'))
    tot = 0
    for d, dirs, names in os.walk(R.lp(VBR)):
        for n in names:
            tot += os.stat(os.path.join(d, n)).st_size
    out['vbr_bytes'] = tot
    dl = (VBR / 'driver_log.txt').read_text(encoding='utf-8', errors='replace').splitlines()
    out['driver_log_last'] = dl[-2:]
    v0 = R.jload(VBR / 'stages' / 'V0.json') or {}
    v10 = R.jload(VBR / 'stages' / 'V10.json') or {}
    out['v0_free'] = v0.get('C11') if isinstance(v0.get('C11'), dict) else {k: v0.get(k) for k in v0 if 'free' in k}
    out['v0_ok2'] = v0.get('ok2_outside_vb')
    out['v10_free'] = v10.get('free_gb')
    out['v10_flags'] = {k: v10.get(k) for k in ('a33_pins_ok', 'rr_same', 'ok2_outside_vb_same', 'archive_tree_same',
                                                 'archive_bytes_ok', 'ok', 'vissim')}
    # 8 shared states ranges
    rows = rc['VB_M_rows']

    def rr(ch, side, T):
        x = [r for r in rows if r['chain'] == ch and r['side'] == side and r['T'] == T]
        return x[0] if x else None
    shared = [(s['chain'], s['T']) for s in rc['derived']['b1_minus_off_shared']]
    rng = {}
    for side in ('B1', 'OFF'):
        for f in ('chain_T450', 'e_out_over_220'):
            v = [rr(ch, side, T)[f] for ch, T in shared]
            rng['%s/%s' % (side, f)] = [min(v), max(v)]
    out['shared_ranges'] = rng
    out['shared_states'] = shared
    # no_match decisions: which part of the signature differs per candidate (report only, no cause decided)
    nm = []
    for x in rc['derived']['no_match']:
        c = [y for y in R.CHAINS if y['chain'] == x['chain']][0]
        P = R.dec_paths(c['key'], x['arm'], x['T'])
        doc = R.jload(P['json']) or {}
        w = R.wsig(doc)
        md = doc.get('metadata') or {}
        jls = md.get('joint_leader_selection') or {}
        rows_c = []
        for p in sorted(q for q in P['hook'].iterdir() if q.is_dir() and q.name.startswith('c_')):
            cj = R.jload(p / 'cand.json') or {}
            sg = cj.get('signature') or {}
            fa, fb = sg.get('future_green_times'), w['f']
            fut_eq = (fa is None and fb is None) or (fa is not None and fb is not None and len(fa) == len(fb) and all(
                (u is None and v is None) or (u is not None and v is not None and R.map_eq(u, v)) for u, v in zip(fa, fb)))
            rows_c.append({'folder': p.name, 'is_ad': cj.get('is_ad'), 'green_eq': R.map_eq(sg.get('green_times'), w['g']),
                           'offsets_eq': R.map_eq(sg.get('offsets'), w['o']), 'future_eq': fut_eq,
                           'future_len': [None if fa is None else len(fa), None if fb is None else len(fb)],
                           'action_from': cj.get('action_from'), 'callers': cj.get('callers')})
        nm.append({'chain': x['chain'], 'arm': x['arm'], 'T': x['T'], 'candidates': rows_c,
                   'jls_keys_status': {k: jls.get(k) for k in ('selection_status', 'converged', 'feasible')}})
        del doc
    out['no_match_detail'] = nm
    out['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    dest = R.OUT / 'vvb3_extra.json'
    if dest.exists():
        raise SystemExit('exists')
    dest.write_text(json.dumps(out, indent=1, default=str), encoding='utf-8')
    print('VVB3_EXTRA done sha=%s' % R.fsha(dest), flush=True)
    return 0


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        sys.exit(main())
    print(__doc__)
    sys.exit(2)
