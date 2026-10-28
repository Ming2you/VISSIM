# make_spec_b.py - writes spec_b_copies.json: the exact text replacements that turn pinned analysis tools into B copies
# (path constants only; the slot names of the originals are kept). Run: python -B make_spec_b.py ; then mkcopy.py.
import json
W = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
BR = 'D:/VISSIM_runs/20261026_codex_b_v3c3'


def bfzp(s):
    return '%s/s%d/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s%d_001.fzp' % (BR, s, s)


def ncfzp(s):
    return 'D:/VISSIM_runs/20261001_v3c3/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (s, s)


def vafzp(s):
    return 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s%d/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s%d_001.fzp' % (s, s)


J1 = {31: 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1r_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1r_s31_001.fzp',
      41: 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1_s41_001.fzp',
      43: 'D:/VISSIM_runs/20261004_sdmpc31_k8/sdmpc31_v3c3_k8j1_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k8j1_s43_001.fzp'}
SPW = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work'
TAG = '[B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; slot "j1" = B runs v3c3-s31/s41/s43] '
spec = []
# A. omega701_recount.py
brl = ("B_RUNS = {_s: {'fzp': '" + BR + "/s%d/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s%d_001.fzp' % (_s, _s),\n"
       "                'inpx': '" + BR + "/s%d/sdmpc/network/sdmpc31_sdmpc9000_s%d.inpx' % (_s, _s),\n"
       "                'err': '" + BR + "/s%d/sdmpc/network/sdmpc31_sdmpc9000_s%d_001.err' % (_s, _s),\n"
       "                'run_dir': '" + BR + "/s%d/sdmpc' % _s} for _s in SEEDS}   # B copy: codex-runner layout\n")
spec.append({'src': W + '/omega/omega701_recount.py', 'dst': W + '/omega_b/omega701_recount_b.py',
             'why': 'B: slot j1 -> B run paths (FZP, inpx, err, run dir); no stage-1 scan cross-check for the slot; outputs in omega_b/',
             'reps': [
                 ['r"""OMEGA701_V3C3 (2026-10-25 KST)', 'r"""' + TAG + 'OMEGA701_V3C3 (2026-10-25 KST)'],
                 ["RUNS = {}\nfor _s in SEEDS:\n", brl + "RUNS = {}\nfor _s in SEEDS:\n"],
                 ["    RUNS['j1_s%d' % _s] = dict(runner(RJ1, J1_NAMES[_s]), arm='j1', seed=_s)",
                  "    RUNS['j1_s%d' % _s] = dict(B_RUNS[_s], arm='j1', seed=_s)   # B copy: slot j1 = B"],
                 ["OLD_SCANS.update({('j1_s%d' % s): SP + '/j1/analysis/scans/j1_s%d' % s for s in SEEDS})\n",
                  "# B copy: no stage-1 scan exists for the B runs in slot j1 (the J1 scans are not B)\n"]]})
# D/E. vhr_scan.py, vhr_firstseen.py
for name in ('vhr_scan', 'vhr_firstseen'):
    reps = [["OUT = '" + SPW + "/vhr/scan_out'", "OUT = '" + SPW + "/vhr_b/scan_out'   # " + TAG]]
    for s in (31, 41, 43):
        reps.append(["    'j1_s%d': '%s'," % (s, J1[s]), "    'j1_s%d': '%s',   # B copy: slot j1 = B" % (s, bfzp(s))])
    spec.append({'src': W + '/vhr/%s.py' % name, 'dst': W + '/vhr_b/%s_b.py' % name,
                 'why': 'B: output folder vhr_b/scan_out; slot j1 -> B FZP paths', 'reps': reps})
# F. vhr_v3c3_all.py
spec.append({'src': W + '/vhr/vhr_v3c3_all.py', 'dst': W + '/vhr_b/vhr_v3c3_all_b.py',
             'why': 'B: read vhr_b/scan_out (slot j1 = B); writes vhr_b/v3c3_all.json',
             'reps': [["S = '" + SPW + "/vhr/scan_out'", "S = '" + SPW + "/vhr_b/scan_out'   # " + TAG]]})
# per seed: scan_fzp, metrics, rm_exec, walltimes, ramp_fc, a1_fzp_firstdiff
for s in (31, 41, 43):
    D = W + '/rawcheck_b/s%d' % s
    TS = '[B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s%d; slot "nc" = NC3, "joint" = B] ' % s
    spec.append({'src': W + '/rawcheck/scan_fzp.py', 'dst': D + '/scan_fzp_b_s%d.py' % s,
                 'why': 'B s%d: output folder rawcheck_b/s%d/scan; slot nc -> NC3 s%d FZP, joint -> B s%d FZP' % (s, s, s, s),
                 'reps': [['OUT = "' + SPW + '/rawcheck/scan"', 'OUT = "' + SPW + '/rawcheck_b/s%d/scan"   # %s' % (s, TS)],
                          ['    "nc": f"{R}/nc/vissim_eval/sdmpc31_nc9000_s29_001.fzp",',
                           '    "nc": "%s",   # B copy: slot nc = NC3 v3c3-s%d' % (ncfzp(s), s)],
                          ['    "joint": f"{R}/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp",',
                           '    "joint": "%s",   # B copy: slot joint = B v3c3-s%d' % (bfzp(s), s)]]})
    spec.append({'src': W + '/rawcheck/metrics.py', 'dst': D + '/metrics_b_s%d.py' % s,
                 'why': 'B s%d: read rawcheck_b/s%d/scan (nc = NC3, joint = B; the other five = byte copies of the codex scans)' % (s, s),
                 'reps': [['S = "' + SPW + '/rawcheck/scan"', 'S = "' + SPW + '/rawcheck_b/s%d/scan"   # %s' % (s, TS)]]})
    spec.append({'src': W + '/rawcheck/rm_exec.py', 'dst': D + '/rm_exec_b_s%d.py' % s,
                 'why': 'B s%d: B results root, arm folder s%d, B file names (sdmpc9000_s%d)' % (s, s, s),
                 'reps': [['R = "D:/VISSIM_handoff/20261024/raw"', 'R = "%s"   # %s' % (BR, TS)],
                          ['for a in ["joint", "window", "off", "freeway_only", "urban_only"]:', 'for a in ["s%d"]:' % s],
                          ['open(f"{R}/{a}/sdmpc/action_sdmpc31_sdmpc8100_s29.csv"', 'open(f"{R}/{a}/sdmpc/action_sdmpc31_sdmpc9000_s%d.csv"' % s],
                          ['open(f"{R}/{a}/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_{sc}_001.ldp"',
                           'open(f"{R}/{a}/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s%d_{sc}_001.ldp"' % s]]})
    spec.append({'src': W + '/rawcheck/walltimes.py', 'dst': D + '/walltimes_b_s%d.py' % s,
                 'why': 'B s%d: slot joint -> B run folder (the only arm)' % s,
                 'reps': [['ARMS = {"joint": f"{R}/joint/sdmpc", "window": f"{R}/window/sdmpc", "off": f"{R}/off/sdmpc",\n'
                           '        "freeway_only": f"{R}/freeway_only/sdmpc", "urban_only": f"{R}/urban_only/sdmpc", "nc": f"{R}/nc"}',
                           'ARMS = {"joint": "%s/s%d/sdmpc"}   # %s' % (BR, s, TS)]]})
    spec.append({'src': W + '/rawcheck/ramp_fc.py', 'dst': D + '/ramp_fc_b_s%d.py' % s,
                 'why': 'B s%d: decision folder of the B run' % s,
                 'reps': [['D = "D:/VISSIM_handoff/20261024/raw/joint/sdmpc/decisions_sdmpc31_sdmpc8100_s29"',
                           'D = "%s/s%d/sdmpc/decisions_sdmpc31_sdmpc9000_s%d"   # %s' % (BR, s, s, TS)]]})
    spec.append({'src': W + '/a1/full/a1_fzp_firstdiff.py', 'dst': D + '/a1_fzp_firstdiff_b_s%d.py' % s,
                 'why': 'B s%d: slot a1 -> B, joint -> NC3 s%d, lnc -> V-A s%d (PRE_B s2-5 prefix check)' % (s, s, s),
                 'reps': [["JOINT = 'D:/VISSIM_handoff/20261024/raw/joint/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'",
                           "JOINT = '%s'   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only; seed v3c3-s%d; slot joint = NC3, a1 = B, lnc = V-A]" % (ncfzp(s), s)],
                          ["LNC = 'D:/VISSIM_runs/vsl_repro_s29/none/run/vissim_eval/vsl_seed29_none_001.fzp'",
                           "LNC = '%s'   # B copy: slot lnc = V-A v3c3-s%d" % (vafzp(s), s)],
                          ["A1 = JOINT if SMOKE else 'D:/VISSIM_runs/20261025_codex_a1_s29/sdmpc/vissim_eval/sdmpc31_sdmpc8100_s29_001.fzp'",
                           "A1 = JOINT if SMOKE else '%s'   # B copy: slot a1 = B v3c3-s%d" % (bfzp(s), s)]]})
spec.append({'src': W + '/rawcheck/dec_extract.py', 'dst': W + '/rawcheck_b/dec_extract_b.py',
             'why': 'B: decision folders under the B results root; arm argument = s31/s41/s43',
             'reps': [['D = glob.glob(f"D:/VISSIM_handoff/20261024/raw/{arm}/sdmpc/decisions_*")[0]',
                       'D = glob.glob(f"' + BR + '/{arm}/sdmpc/decisions_*")[0]   # [B copy 2026-10-26 KST, COMPARE_RULE_B: path constants only]']]})
json.dump(spec, open(W + '/gate1/spec_b_copies.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(spec))
