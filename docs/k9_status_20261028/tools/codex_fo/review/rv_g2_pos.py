# Review probe (read-only): v3c3 positive control for G2 using the codex 64cf freeway_only T=900 baseline rows
# (same baseline values) against the B v3c3 .lsa native of each seed; plus .sig byte comparison 64cf vs FRZ_FO.
import importlib.util, json, sys, hashlib, os, glob
spec = importlib.util.spec_from_file_location('m', r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/fo/work/gate/fog_sg_native.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
act64 = m.HO.replace('/sdmpc', '/sdmpc') + '/decisions_sdmpc31_sdmpc8100_s29/action_000900.csv'
out = {'act64': act64, 'act64_sha256': m.sha(act64)}
FRZ = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954'
for s in (31, 41, 43):
    tmp = 'rv_g2_pos_s%d.json' % s
    m.mode_gate(s, act64, tmp, FRZ)
    g = json.load(open(tmp, encoding='utf-8'))
    out['s%d' % s] = {k: g[k] for k in ('written_sg', 'sg_with_difference', 'differing_frames_total', 'cycles_equal', 'pass', 'written_not_expected', 'plan_sg_not_written')}
# .sig bytes: 64cf network folder vs FRZ_FO network folder
def shas(folder):
    return {os.path.basename(p): m.sha(p) for p in glob.glob(folder + '/*.sig')}
a = shas(m.HO + '/network'); b = shas(FRZ + '/diagnostics/sdmpc_n31_20260924/network')
out['sig_64cf_n'] = len(a); out['sig_frz_n'] = len(b)
out['sig_same_names'] = sorted(set(a) & set(b)).__len__()
out['sig_diff'] = sorted(k for k in set(a) & set(b) if a[k] != b[k])
print(json.dumps(out, ensure_ascii=False))
json.dump(out, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
