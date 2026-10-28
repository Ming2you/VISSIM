"""VERIFY_VP data-after read (verifier, 2026-10-27 KST): does response_token follow the job folder?  Read-only.
(a) the same producer state run twice in the SAME job folder name (P1 v3c3-s31 T=1,800: r2 stop copy, now under
    out/interrupted, and the r3 run): R1 AD objective, costs, request sha, response token;
(b) the out-of-list smoke state run in five DIFFERENT folders (smoke v1..v5): objective and response token of the
    same plans (R1 REC AD, EXEC scalar);
(c) the verifier re-run of probe-A v3c3-s31 T=4,050 vs the original (different folder).
    python -B vv_token_check.py <out.json>"""
import glob
import json
import os
import sys

G = 'D:/VISSIM-merge/k8_gate_trees/vsl_plant/'


def load(p):
    with open(p, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def r1req(p):
    return [r['request_sha256'] for r in p['runs'] if r['batch'] == 'R1'][0]


res = {}
a = load(glob.glob(G + 'out/interrupted/plant_P/*/probe.json')[0])
b = load(G + 'out/plant_P/v3c3-s31_T001800/probe.json')
ea, eb = a['evaluations']['R1_REC_ad'], b['evaluations']['R1_REC_ad']
res['same_folder_P_s31_T1800'] = {'objective_equal': ea['objective_veh_h'] == eb['objective_veh_h'],
                                  'costs_equal': ea['costs'] == eb['costs'],
                                  'request_sha_equal': r1req(a) == r1req(b),
                                  'response_token_equal': ea['response_token'] == eb['response_token']}
sm = [load(f) for f in sorted(glob.glob(G + 'smoke/s31_T002400*/probe.json'))]
for lab in ('R1_REC_ad', 'EXEC_scalar'):
    ev = [p['evaluations'][lab] for p in sm if lab in p.get('evaluations', {})]
    res['smoke_' + lab] = {'n_runs': len(ev), 'distinct_action_token': len({e['action_token'] for e in ev}),
                           'distinct_objective': len({e['objective_veh_h'] for e in ev}),
                           'distinct_response_token': len({e['response_token'] for e in ev})}
o = load(G + 'out/plant_A/v3c3-s31_T004050/probe.json')
n = load(G + 'verify/plant_A/v3c3-s31_T004050/probe.json')
res['rerun_A'] = {lab: {'objective_equal': o['evaluations'][lab]['objective_veh_h'] == n['evaluations'][lab]['objective_veh_h'],
                        'response_token_equal': o['evaluations'][lab]['response_token'] == n['evaluations'][lab]['response_token']}
                  for lab in o['evaluations']}
outp = sys.argv[1]
tmp = outp + '.tmp%d' % os.getpid()
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(res, f, indent=1)
os.replace(tmp, outp)
print(json.dumps(res['same_folder_P_s31_T1800']), json.dumps(res['smoke_R1_REC_ad']), json.dumps(res['smoke_EXEC_scalar']))
