# -*- coding: utf-8 -*-
"""Write the post-run job list for vsl_heavy.ps1 (PRE_VSL.md section 7.3). 2026-10-27 KST, vsl_v3c3.

Usage: python -B vsl_analysis_jobs.py   -> VS/tools/jobs_analysis.json (refuses if it exists)
For each seed it uses the same run pick as vsl_metrics.py (run_retry1 only if the launcher recorded run2 as done) and
lists the scans of the VSL FZP: vsl_vhr.py (B-copy vhr scan + first-seen), fwe_scan.py (unchanged, pinned 0619e9fc...),
vsl_cell_scan.py, vsl_firstdiff.py (VSL vs NC3 of the same seed); then vsl_metrics.py run. A seed whose FZP is missing is
left out of the scans (vsl_metrics then writes 'mot naem' for it). Checks the sha256 of every tool before writing.
"""
import hashlib, json, os, sys

SP = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8'
VS = SP + '/vsl_v3c3'
RR = 'D:/VISSIM_runs/20261027_vsl_v3c3'
V3 = 'D:/VISSIM_runs/20261001_v3c3'
TOOLS = {SP + '/rmcause/phys/fwe_scan.py': '0619e9fcbe14fd1b2e53d1cf884a8d740c0542f5686df33ef26f450a2b08bae7'}
PIN_FILE = VS + '/tools/analysis_tool_pins.json'   # {path: sha} of vsl_vhr / vsl_cell_scan / vsl_firstdiff / vsl_metrics


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def pick_run(s):
    e2 = RR + '/_launcher/end_s%d_run2.json' % s
    if os.path.exists(e2) and json.load(open(e2, encoding='utf-8-sig')).get('status') == 'done':
        return RR + '/s%d/run_retry1' % s
    return RR + '/s%d/run' % s


def main():
    out = VS + '/tools/jobs_analysis.json'
    if os.path.exists(out):
        raise SystemExit('exists: ' + out)
    pins = dict(TOOLS)
    pins.update(json.load(open(PIN_FILE, encoding='utf-8')))
    bad = {p: sha(p) for p, v in pins.items() if sha(p) != v}
    if bad:
        raise SystemExit('tool sha changed: %s' % bad)
    jobs, vhr_args, missing = [], [], []
    fz = {}
    for s in (31, 41, 43):
        f = pick_run(s) + '/vissim_eval/baseline_s%d_v3c3vsl_001.fzp' % s
        if os.path.exists(f):
            fz[s] = f
            vhr_args.append('vsl_s%d=%s' % (s, f))
        else:
            missing.append(f)
    if vhr_args:
        jobs.append({'tag': 'vhr', 'args': [VS + '/tools/vsl_vhr.py', VS + '/out/vhr'] + vhr_args})
    for s, f in fz.items():
        jobs.append({'tag': 'phys_s%d' % s, 'args': [SP + '/rmcause/phys/fwe_scan.py', 'vsl_s%d' % s, f, VS + '/out/phys']})
        jobs.append({'tag': 'cell_s%d' % s, 'args': [VS + '/tools/vsl_cell_scan.py', 'vsl_s%d' % s, f, VS + '/out/cell']})
        nc = V3 + '/s%d_v3c3nc/run/vissim_eval/baseline_s%d_v3c3nc_001.fzp' % (s, s)
        jobs.append({'tag': 'firstdiff_s%d' % s, 'args': [VS + '/tools/vsl_firstdiff.py', 's%d' % s, f, nc, VS + '/out/firstdiff']})
    jobs.append({'tag': 'metrics', 'args': [VS + '/tools/vsl_metrics.py', 'run']})
    json.dump({'name': 'analysis_vsl', 'jobs': jobs, 'missing_fzp': missing, 'tool_pins': pins}, open(out, 'w', encoding='utf-8'), indent=1)
    print(out, sha(out), 'jobs', len(jobs), 'missing', missing)


if __name__ == '__main__':
    main()
