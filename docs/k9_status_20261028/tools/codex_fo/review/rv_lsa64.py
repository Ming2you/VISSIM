# Review probe (read-only): on the codex 64cf-s29 freeway_only run (handoff copy), does the run's own .lsa after 900 s equal
# (a) the LDP and (b) the native program extended from frames [2,899], for ALL urban SGs incl. native-only (SC5 9-24, SC7 9-16)?
import importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location('m', r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work/gate/fog_sg_native.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
HO = m.HO
ev, cyc = m.read_lsa(HO + '/vissim_eval/sdmpc31_sdmpc8100_s29_001.lsa')
written = m.written_set(HO + '/decisions_sdmpc31_sdmpc8100_s29/signal_readback.csv')
urban = sorted(k for k in ev if k[0] < 9000)
res = {'urban_sg_in_lsa': len(urban), 'written': len(written)}
late = list(range(1050, 8100)); early = list(range(2, 900))
nat_ext = {}; lsa_vs_ldp = {}; lsa_late_vs_nat = {}
for key in urban:
    sc = key[0]
    C, delta, ok = m.native_cycle(cyc.get(sc, []))
    base = m.lsa_green_frames(ev[key], early)
    prog = {(t + delta) % C for t in base if t >= 2 + C} if ok else set()
    lg = m.lsa_green_frames(ev[key], late)
    d = [t for t in late if ((t in lg) != (((t + delta) % C) in prog))] if ok else None
    lsa_late_vs_nat['%d:%d' % key] = {'n': None if d is None else len(d), 'ex': (d or [])[:3], 'written': key in written}
for sc in sorted({k[0] for k in urban}):
    p = HO + '/vissim_eval/sdmpc31_sdmpc8100_s29_%d_001.ldp' % sc
    if not os.path.exists(p):
        continue
    labels, rows = m.read_ldp(p)
    for j, sg in enumerate(labels):
        key = (sc, sg)
        if key not in ev:
            continue
        lg = m.lsa_green_frames(ev[key], late)
        d = [t for t in late if t in rows and ((rows[t][j] == 'I') != (t in lg))]
        # native-only check on LDP: late LDP vs early LDP periodic extension
        C, delta, ok = m.native_cycle(cyc.get(sc, []))
        early_g = {t for t in early if t in rows and rows[t][j] == 'I' and t >= 2 + C}
        prog = {(t + delta) % C for t in early_g}
        d2 = [t for t in late if t in rows and ((rows[t][j] == 'I') != (((t + delta) % C) in prog))]
        lsa_vs_ldp['%d:%d' % key] = {'lsa_vs_ldp': len(d), 'ldp_late_vs_ldp_native': len(d2), 'written': key in written}
def summ(dct, f):
    w = [v for v in dct.values() if v['written']]; nw = [v for v in dct.values() if not v['written']]
    return {'written_n': len(w), 'written_with_diff': sum(1 for v in w if (v[f] or 0) > 0), 'written_frames': sum((v[f] or 0) for v in w),
            'native_only_n': len(nw), 'native_only_with_diff': sum(1 for v in nw if (v[f] or 0) > 0), 'native_only_frames': sum((v[f] or 0) for v in nw)}
res['lsa_late_vs_native_ext'] = summ(lsa_late_vs_nat, 'n')
res['lsa_vs_ldp_late'] = summ(lsa_vs_ldp, 'lsa_vs_ldp')
res['ldp_late_vs_ldp_native_ext'] = summ(lsa_vs_ldp, 'ldp_late_vs_ldp_native')
res['native_only_keys'] = sorted(k for k, v in lsa_late_vs_nat.items() if not v['written'])
res['per_sg_lsa_late'] = lsa_late_vs_nat
res['per_sg_ldp'] = lsa_vs_ldp
out = sys.argv[1]
json.dump(res, open(out, 'w', encoding='utf-8'), indent=1)
print(json.dumps({k: res[k] for k in ('urban_sg_in_lsa', 'written', 'lsa_late_vs_native_ext', 'lsa_vs_ldp_late', 'ldp_late_vs_ldp_native_ext')}))
print('native_only', len(res['native_only_keys']), res['native_only_keys'][:30])
