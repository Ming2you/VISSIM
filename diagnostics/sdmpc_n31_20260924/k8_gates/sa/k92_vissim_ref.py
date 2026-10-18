"""K9-2 bundle 1 VISSIM reference of the F metrics (K8_PREDECLARATION_AMENDMENT_24 sections 3.1-3b, 5.3).  Read only:
the v3c3 NC FZP of the seed (sa_common.NC_FZP_REL under NC3) and its .inpx; one seed at a time, BELOW_NORMAL.

    python -B k92_vissim_ref.py [--root R] [--out O] [--nc3 D] --states <seed>:<T>,<T>... [--states ...]
                                [--gates-stage k92t --declaration-sha <amendment 24 sha>]
        -> <out>/sa/k92_vissim_ref.json (merged: an existing seed / state entry is kept, never recomputed)

Per state T (frames t = 5 k + 0.1 of the FZP):
  m1_T150 / m1_T450   vehicles on the P0-3 174-chain links (k92_common.CHAIN_LINKS, 13: 21, 173, 174, 1220000600 and
                      the nine SC108_to_SC109 origin connectors) at the frames T+150.1 / T+450.1
  m2_T150 / m2_T450   passages of the through heads 1090201-03 between the frames T+0.1 and T+150.1 / T+450.1
  m3_T150 / m3_T450   the same for the left-turn heads 1090501-02
Passage judge = the K8b-1 byte copies of the U4 measurers (k8b/u4/derive_head_saturation.py 369c2fdb...,
urban_b2_evidence.py 73565c5c...): their approach trees (build_trees) and crossing rule (analyze_run), with the
window (T+0.1, T+150.1] / (T+0.1, T+450.1] given as the 'green' interval of SC109 SG 2 / SG 5 and the count read from
the full-bin crossings gf_cross (the measurer's own counter); nothing of the measurer is edited.
Network identity (K8_PREDECLARATION_AMENDMENT_25 section 1): the seed's NC .inpx must equal the v3c3 network 3de889f0
except the value of the one randSeed attribute of the <simulation> start tag: the bytes with that value emptied
(randSeed="") must have sha256 INPX_NORM_SHA256 and the value must be the folder seed; anything else is a SystemExit.
The raw / normalized sha are recorded per seed (network_identity).  The blind s47 branch opens no file.
Blindness (section 3.1-3b): v3c3-s47 is refused unless --gates-stage k92t with the amendment 24 sha is given (the
judging stage); without it the s47 entries are written as null with reason k92_blind_s47 and the FZP is not opened."""
import argparse
import hashlib
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sa_common as sc  # noqa: E402
import k92_common as k92c  # noqa: E402

c = sc.c
U4_SHA256 = {'derive_head_saturation.py': '369c2fdbf9939a2cc60a96ffaa656934d02258246f667d3c692ca21fae2ffabd',
             'urban_b2_evidence.py': '73565c5c259389112164290fac271fa55f2c796a38d1d32303a94c2feadef0f5'}
INPX_SHA256 = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
INPX_NORM_SHA256 = 'b7f05dcd07042fce8a439529853429a642f4de7b998c96ede51ce8c2d1230eb3'  # amendment 25
RANDSEED_RE = re.compile(rb'(?<![A-Za-z0-9_])randSeed="([0-9]+)"')
NETWORK_RULE = 'k92-inpx-randseed-normalized/v1'
SCHEMA = 'k92-vissim-ref/v1'


def u4_modules(root):
    d = Path(root) / 'diagnostics/sdmpc_n31_20260924/k8b/u4'
    for name, want in U4_SHA256.items():
        if sc.sha256_file(d / name) != want:
            raise SystemExit(f'k8b/u4/{name} is not the pinned U4 measurer copy')
    sys.path.insert(0, str(d))
    import urban_b2_evidence as E
    import derive_head_saturation as D
    return E, D


def nc_paths(seed):
    fzp = Path(c.NC3) / sc.NC_FZP_REL.format(seed=seed)
    inpx = Path(c.NC3) / ('s%d_v3c3nc/prepared/network/baseline_s%d_v3c3nc.inpx' % (seed, seed))
    return fzp, inpx


def network_identity(inpx, seed):
    """Amendment 25 section 1 -> {path, bytes, raw_sha256, normalized_sha256, randSeed, reference_raw_sha256, rule}"""
    b = Path(inpx).read_bytes()
    ms = list(RANDSEED_RE.finditer(b))
    if len(ms) != 1:
        raise SystemExit(f'{inpx}: randSeed attribute found {len(ms)} times (want 1)')
    m = ms[0]
    lt = b.rfind(b'<', 0, m.start())
    if lt < 0 or not b.startswith(b'<simulation ', lt) or b.find(b'>', lt, m.start()) != -1:
        raise SystemExit(f'{inpx}: randSeed is not an attribute of the <simulation> start tag')
    if m.group(1) != str(int(seed)).encode('ascii'):
        raise SystemExit(f'{inpx}: randSeed value is not the folder seed {seed}')
    norm = hashlib.sha256(b[:m.start()] + b'randSeed=""' + b[m.end():]).hexdigest()
    if norm != INPX_NORM_SHA256:
        raise SystemExit(f'{inpx}: not the v3c3 network {INPX_SHA256[:16]} (randSeed-normalized {norm[:16]})')
    return {'path': str(inpx), 'bytes': len(b), 'raw_sha256': hashlib.sha256(b).hexdigest(),
            'normalized_sha256': norm, 'randSeed': int(seed), 'reference_raw_sha256': INPX_SHA256,
            'rule': NETWORK_RULE}


def seed_ref(root, seed, states):
    E, D = u4_modules(root)
    fzp, inpx = nc_paths(seed)
    ident = network_identity(inpx, seed)
    net = E.Network(inpx)
    groups = [{'heads': [dict(net.heads[h]) for h in k92c.THROUGH_HEADS]},
              {'heads': [dict(net.heads[h]) for h in k92c.LEFT_HEADS]}]
    heads = [h for g in groups for h in g['heads']]
    if {h['sg'] for h in groups[0]['heads']} != {'2'} or {h['sg'] for h in groups[1]['heads']} != {'5'} \
            or any(h['sc'] != '109' or h['link'] != '173' for h in heads):
        raise SystemExit('K92 VISSIM ref: head identity differs from the declaration')
    trees, down, links, keep = D.build_trees(net, groups)
    keep = set(keep) | set(k92c.CHAIN_LINKS)
    t0 = time.time()
    arr, meta = E.stream_fzp(str(fzp), keep)
    wins = []
    for T in states:
        for d in (150, 450):
            wins.append((float(T) + 0.1, float(T) + d + 0.1))
    windows = {'109-2': {'green': list(wins), 'amber': []}, '109-5': {'green': list(wins), 'amber': []}}
    out_heads, stats, _agree = D.analyze_run(arr, meta['itt_names'], heads, trees, down, links, windows)
    import numpy as np
    k_arr = arr['k']
    link_arr = arr['link']
    chain = np.isin(link_arr, np.asarray([int(x) for x in k92c.CHAIN_LINKS], dtype=np.int64))
    rows = {}
    for T in states:
        rec = {}
        for d in (150, 450):
            k = int(round((T + d) / E.FRAME_SEC))
            sel = chain & (k_arr == k)
            rec['m1_T%d' % d] = int(sel.sum())
            rec['m1_by_link_T%d' % d] = {str(L): int((sel & (link_arr == int(L))).sum()) for L in k92c.CHAIN_LINKS}
            want = (float(T) + 0.1, float(T) + d + 0.1)
            for key, hs in (('m2', k92c.THROUGH_HEADS), ('m3', k92c.LEFT_HEADS)):
                tot, per = 0, {}
                for h in hs:
                    cyc = [cy for cy in out_heads[h]['cycles'] if (round(cy['gs'], 6), round(cy['ge'], 6))
                           == (round(want[0], 6), round(want[1], 6))]
                    if len(cyc) != 1:
                        raise SystemExit(f'K92 VISSIM ref s{seed} T={T}: window {want} found {len(cyc)} times for {h}')
                    per[h] = int(cyc[0]['gf_cross'])
                    tot += per[h]
                rec['%s_T%d' % (key, d)] = tot
                rec['%s_by_head_T%d' % (key, d)] = per
        rows[str(T)] = rec
    return {'fzp': {'path': meta['path'], 'sha256': meta['sha256'], 'bytes': meta['bytes'],
                    'rows_total': meta['rows_total'], 'rows_kept': meta['rows_kept']},
            'network_identity': ident, 'states': rows, 'crossing_stats': stats,
            'sec': round(time.time() - t0, 1)}


def main():
    ap = c.add_nc3(c.parser(__doc__))
    ap.add_argument('--states', action='append', required=True, help='<seed>:<T>,<T>,...')
    sc.add_k8b_stage_args(ap)
    args = ap.parse_args()
    c.apply(args)
    c.lower_priority()
    opened = k92c.k92_stage_open(args)
    path = sc.sa_out() / 'k92_vissim_ref.json'
    doc = sc.read_json(path, {}) or {'schema': SCHEMA, 'seeds': {}}
    for spec in args.states:
        seed_s, Ts = spec.split(':')
        seed = int(seed_s)
        if seed in sc.SEALED_SEEDS or seed not in sc.FH_SEEDS:
            raise SystemExit(f'seed {seed} refused (sealed / not an NC fit seed)')
        states = [int(x) for x in Ts.split(',') if x]
        entry = doc['seeds'].setdefault('s%d' % seed, {'states': {}})
        if seed == k92c.F_PRIMARY_SEED and not opened:
            for T in states:
                entry['states'].setdefault(str(T), {'value': None, 'reason': k92c.K92_BLIND_REASON})
            print(f'K92_VISSIM_REF_BLIND s{seed} {states} (null, {k92c.K92_BLIND_REASON}; FZP not opened)', flush=True)
            sc.write_json(path, doc)
            continue
        ident = network_identity(nc_paths(seed)[1], seed)
        if entry.setdefault('network_identity', ident) != ident:
            raise SystemExit(f's{seed}: recorded network_identity differs from this .inpx')
        todo = [T for T in states if str(T) not in entry['states'] or (entry['states'][str(T)] or {}).get('value',
                                                                                                       1) is None]
        if not todo:
            sc.write_json(path, doc)
            print(f'K92_VISSIM_REF_SKIP s{seed} (all states present)', flush=True)
            continue
        ref = seed_ref(c.R, seed, todo)
        if ref['network_identity'] != entry['network_identity']:
            raise SystemExit(f's{seed}: network_identity changed during the run')
        for T, rec in ref['states'].items():
            entry['states'][T] = rec
        entry.setdefault('fzp', ref['fzp'])
        entry.setdefault('runs', []).append({'states': todo, 'fzp_sha256': ref['fzp']['sha256'],
                                             'crossing_stats': ref['crossing_stats'], 'sec': ref['sec'],
                                             'when': time.strftime('%Y-%m-%dT%H:%M:%S')})
        sc.write_json(path, doc)
        print(f'K92_VISSIM_REF s{seed} states={todo} fzp={ref["fzp"]["sha256"][:16]} '
              f'inpx={ident["raw_sha256"][:16]} sec={ref["sec"]}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
