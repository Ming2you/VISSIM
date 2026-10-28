# Review probe (read-only, B v3c3 records + 64cf): (1) .lsa [901,9000] of SGs NOT written by COM vs native extension;
# (2) urban readback rows requested == readback and ok == 1.
import importlib.util, json, sys, csv
spec = importlib.util.spec_from_file_location('m', r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work/gate/fog_sg_native.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
out = {}
cases = [('b_s%d' % s,) + m.b_inputs(s)[1:] + (9000,) for s in (31, 41, 43)]
cases.append(('64cf', m.HO + '/vissim_eval/sdmpc31_sdmpc8100_s29_001.lsa', m.HO + '/decisions_sdmpc31_sdmpc8100_s29/signal_readback.csv', 8100))
for name, lsa, rb, tend in cases:
    ev, cyc = m.read_lsa(lsa)
    written = m.written_set(rb)
    late = list(range(901, tend + 1)); early = list(range(2, 900))
    nd, nn, per = 0, 0, {}
    ctrl_sc = sorted({k[0] for k in written})
    for key in sorted(k for k in ev if k[0] < 9000 and k not in written):
        C, delta, ok = m.native_cycle(cyc.get(key[0], []))
        base = m.lsa_green_frames(ev[key], early)
        prog = {(t + delta) % C for t in base if t >= 2 + C} if ok else set()
        lg = m.lsa_green_frames(ev[key], late)
        d = [t for t in late if (t in lg) != (((t + delta) % C) in prog)] if ok else late
        nn += 1
        if d:
            nd += 1
            per['%d:%d' % key] = {'n': len(d), 'ex': d[:3], 'native_ok': ok}
    in_ctrl = sorted('%d:%d' % k for k in ev if k[0] in ctrl_sc and k not in written)
    bad = n = 0
    with open(rb, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if int(row['sc_no']) < 9000:
                n += 1
                if row['requested_state'] != row['readback_state'] or row['ok'] != '1':
                    bad += 1
    out[name] = {'not_written_sg_in_lsa': nn, 'not_written_with_diff': nd, 'not_written_in_controlled_sc': in_ctrl,
                 'diff_examples': dict(list(per.items())[:10]), 'urban_readback_rows': n, 'urban_readback_bad': bad}
    print(name, 'not_written', nn, 'with_diff', nd, 'in_ctrl_sc', len(in_ctrl), 'readback rows', n, 'bad', bad, list(per.items())[:4])
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), indent=1)
