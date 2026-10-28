# -*- coding: utf-8 -*-
"""fwe_pins_existing.py - sha256 of existing tools / definitions / documents / result tables used by PRE_FWE (read-only, light).
Writes only <SP>/fwe_decomp/out/pins_existing.json and pins_existing.sha256 (sha256sum -c format)."""
import hashlib, json, os, time

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
H = 'D:/VISSIM_handoff/20261024'
G = {
    'tool': [
        SP + '/rmcause/phys/fwe_scan.py', SP + '/rmcause/phys/fwe_analyze.py', SP + '/rmcause/o1o4/work/tails.py',
        SP + '/rmcause/o1o4/work/linkbin_scan.py', SP + '/codex_handoff/work/vhr/vhr_firstseen.py',
        SP + '/codex_handoff/work/vhr/vhr_unins.py', SP + '/codex_handoff/work/vhr/vhr_scan.py',
        SP + '/codex_handoff/work/vhr/vhr_v3c3_all.py', SP + '/codex_handoff/work/vhr_b/vhr_v3c3_all_b.py',
        SP + '/codex_handoff/work/omega/omega701_recount.py', SP + '/codex_handoff/work/omega/check_fzp_copy.py',
        SP + '/vsl_v3c3/tools/vsl_metrics.py', SP + '/vsl_v3c3/tools/vsl_cell_scan.py', SP + '/vsl_v3c3/tools/vsl_vhr.py',
        SP + '/codex_handoff/work/rawcheck/rm_exec.py', SP + '/c_port/readback/tools/rb_readback.py',
        SP + '/c_port/readback/tools/rb_fzp_scan.py', SP + '/c_port/readback/tools/rb_discharge.py',
        H + '/code/handoff/check_fzp.py' if os.path.exists(H + '/code/handoff/check_fzp.py') else SP + '/codex_handoff/work/omega/check_fzp_copy.py',
        H + '/analysis/original_scripts/solo355_compare_20261014.py',
    ],
    'definition': [
        H + '/derived/omega_membership_exact.json', H + '/derived/reporting_partition.json',
        H + '/derived/metrics_0_8100.csv', H + '/derived/independent_fzp_counts.json', H + '/derived/decision_greens.csv',
    ],
    'document': [
        SP + '/K9_1_J1_NOTES_20261013.md', SP + '/codex_handoff/HANDOFF_RESULTS.md', SP + '/codex_handoff/B_RESULTS.md',
        SP + '/codex_handoff/B_RESULTS_ERRATA_20261027.md', SP + '/codex_handoff/OMEGA701_V3C3.md', SP + '/codex_handoff/R_NET.md',
        SP + '/codex_handoff/a1/A1_RESULT.md', SP + '/c_port/READBACK_METER.md', SP + '/c_port/INPUT1099.md',
        SP + '/c_port/VSL_OFFLINE.md', SP + '/vsl_v3c3/VSL_RESULTS.md', SP + '/vsl_v3c3/VSL_REPORT.md', SP + '/vsl_v3c3/PRE_VSL.md',
        SP + '/vsl_v3c3/o1o2/PRE_O1O2.md', SP + '/rmcause/METER_CAUSE.md', SP + '/rmcause/o1o4/METER_NEXT.md',
        SP + '/rmcause/r2c_n/METER_NEXT2.md', SP + '/rmcause/INV_PHYSICS.md', SP + '/rmcause/o1o4/O4_MERGE_10681.md',
        SP + '/rmcause/o1o4/W264_READ.md', SP + '/k92/va/analysis/VA_REPORT.md', SP + '/HANDOFF_codex_a49981ff.md',
    ],
    'result_table': [
        SP + '/codex_handoff/work/omega/omega701_pairs.csv', SP + '/codex_handoff/work/omega/omega701_levels.csv',
        SP + '/codex_handoff/work/omega/omega701_per_link.csv', SP + '/codex_handoff/work/omega/omega701_v3c3.json',
        SP + '/codex_handoff/work/omega_b/omega701_v3c3.json', SP + '/codex_handoff/work/omega_b/omega701_per_link.csv',
        SP + '/codex_handoff/work/vhr/v3c3_all.json', SP + '/codex_handoff/work/vhr_b/v3c3_all.json',
        SP + '/codex_handoff/work/vhr/unins_out.json', SP + '/vsl_v3c3/out/vsl_metrics.json', SP + '/rmcause/phys/out_all.json',
        SP + '/c_port/vsl/out/v2b.json', SP + '/c_port/vsl/out/v4_omega.json', SP + '/codex_handoff/work/a1/full/metrics_out_a1.json',
        SP + '/c_port/readback/out/readback.json', SP + '/c_port/readback/out/discharge.json',
    ],
}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    out = {'tool': 'fwe_pins_existing.py', 'at_kst': time.strftime('%Y-%m-%d %H:%M:%S'), 'groups': {}}
    lines = []
    for g, ps in G.items():
        out['groups'][g] = []
        for p in ps:
            if not os.path.exists(p):
                out['groups'][g].append({'path': p, 'missing': True})
                continue
            s = sha(p)
            out['groups'][g].append({'path': p, 'bytes': os.path.getsize(p), 'sha256': s})
            lines.append('%s *%s' % (s, p))
    d = SP + '/fwe_decomp/out'
    json.dump(out, open(d + '/pins_existing.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(d + '/pins_existing.sha256', 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('done', len(lines))


if __name__ == '__main__':
    main()
