r"""Paired offline comparison of SDMPC cap margins at the saved 900 s and 1050 s states.

    cap_margin_sweep.py <arm_name> <np_margin_veh> <nuf_margin_veh_h>

Runs in the worktree D:\VISSIM-merge\sim3-capmargin (never the tree a native run uses):
  1. sets evaluation/parameters.json sdmpc_pfo_cap margins (bytes otherwise unchanged),
  2. replays 900 s from the isolated frames in capmargin\in_900, previous action 750 s
     (no SDMPC state -> zero prices, as in the native run),
  3. builds capmargin\dec_1050_<arm>: the native 900 s action with only its policy token
     replaced by this arm's token (load_prices refuses a different policy), its CSV, and
     a fresh .applied receipt; then replays 1050 s from capmargin\in_1050.
Open loop at 1050: the plant state and the entering prices come from the native
margin-0 900 s decision. Writes capmargin\<arm>\summary.json.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

WT = r'D:\VISSIM-merge\sim3-capmargin'
CM = r'D:\VISSIM_runs\20260923_sdmpc\capmargin'
NATIVE = r'D:\VISSIM_runs\20260923_sdmpc\sdmpc_lp_9000\decisions_sdmpc_lp_9000'
REPLAY = r'D:\VISSIM-merge\tools\replay_decision.ps1'


def set_margins(np_m, nuf_m):
    p = os.path.join(WT, 'evaluation', 'parameters.json')
    raw = open(p, 'rb').read()
    new = re.sub(rb'("np_cap_margin_veh": )[0-9.eE+-]+', b'\\g<1>' + repr(float(np_m)).encode(), raw, count=1)
    new = re.sub(rb'("nuf_cap_margin_veh_h": )[0-9.eE+-]+', b'\\g<1>' + repr(float(nuf_m)).encode(), new, count=1)
    doc = json.loads(new.decode('utf-8-sig'))['sdmpc_pfo_cap']
    if (doc['np_cap_margin_veh'], doc['nuf_cap_margin_veh_h']) != (float(np_m), float(nuf_m)):
        raise SystemExit('parameters.json margin edit failed')
    open(p, 'wb').write(new)


def replay(sec, prev, dec, state, out, log):
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', REPLAY,
           '-Root', WT, '-Dec', dec, '-Sec', str(sec), '-PrevSec', str(prev),
           '-StateJson', state, '-Out', out]
    with open(log, 'w', encoding='utf-8') as f:
        rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
    tail = open(log, encoding='utf-8', errors='replace').read().splitlines()[-3:]
    return rc, tail


def summarize(out, sec):
    prog = os.path.join(out, 'action_%06d.joint.progress.jsonl' % sec)
    rows = [json.loads(l) for l in io.open(prog, encoding='utf-8') if l.strip()]
    done = next((r for r in rows if r.get('stage') == 'sdmpc_completed'), None)
    init = next((r for r in rows if r.get('stage') == 'sdmpc_pfo_budget_initialized'), None)
    steps = [r for r in rows if r.get('stage') in ('sdmpc_step_accepted', 'sdmpc_pfo_step_accepted')]
    a = json.load(io.open(os.path.join(out, 'action_%06d.json' % sec), encoding='utf-8'))
    md = a.get('metadata', {})
    ps = md.get('joint_leader_selection', {}).get('price_state', {})
    bi = md.get('joint_leader_selection', {}).get('budget_initialization', {})
    meters = a.get('ramp_metering', {})
    return dict(
        objective=done and done['objective'], held=done and done.get('held_objective'),
        init=init, steps=[{k: r.get(k) for k in ('stage', 'iteration', 'objective', 'owned_cost', 'omega_cost')} for r in steps],
        policy_sha256=ps.get('policy_sha256'), prices_scaled=ps.get('prices_scaled'),
        next_prices_scaled=ps.get('next_prices_scaled'),
        budget_initialization={k: bi.get(k) for k in ('schema', 'achieved_np_veh', 'achieved_nuf_veh_h',
                                                      'np_cap_margin_veh', 'nuf_cap_margin_veh_h',
                                                      'np_cap_veh', 'nuf_cap_veh_h')},
        cap_np=a.get('N_P_star'), cap_nuf=a.get('N_UF_star'),
        final={k: {x: md.get('joint_leader_selection', {}).get('final_constraints', {}).get(k, {}).get(x)
                   for x in ('actual', 'target', 'residual', 'violation', 'mode')} for k in ('np', 'nuf')},
        iteration_dual_updates=md.get('joint_leader_selection', {}).get('iteration_dual_updates'),
        selection_status=md.get('joint_leader_selection', {}).get('selection_status'),
        meters_below_ceiling=sum(1 for k, v in meters.items()
                                 if v < (3024. if k in ('RM_C10482', 'RM_C10681') else 1512.) - 1e-6),
        vsl_below_120=sum(1 for v in a.get('vsl', {}).values() if v < 120 - 1e-6),
        wall=md.get('decision_wall_sec'))


def build_dec_1050(arm, token):
    d = os.path.join(CM, 'dec_1050_' + arm)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    src = open(os.path.join(NATIVE, 'action_000900.json'), 'rb').read()
    old = json.loads(re.search(rb'"policy_sha256": ?"([0-9a-f]{64})"', src).group(0).split(b':', 1)[1])
    if len(token) != 64:
        raise SystemExit('bad arm token')
    open(os.path.join(d, 'action_000900.json'), 'wb').write(src.replace(old.encode(), token.encode()))
    for name in ('action_000900.csv', 'state_000900.json', 'state_000750.json'):
        shutil.copy2(os.path.join(NATIVE, name), os.path.join(d, name))
    csv = os.path.join(d, 'action_000900.csv')
    with open(os.path.join(d, 'action_000900.json.applied'), 'w', encoding='utf-16', newline='\r\n') as f:
        f.write('900\n%s\n%d' % (os.path.abspath(csv), os.path.getsize(csv)))
    return d, old


def main():
    arm, np_m, nuf_m = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    out_arm = os.path.join(CM, arm)
    os.makedirs(out_arm, exist_ok=True)
    set_margins(np_m, nuf_m)
    result = dict(arm=arm, np_margin=np_m, nuf_margin=nuf_m)
    rc, tail = replay(900, 750, NATIVE, os.path.join(CM, 'in_900', 'state_000900.json'),
                      os.path.join(out_arm, 'd900'), os.path.join(out_arm, 'd900.log'))
    result['d900_rc'], result['d900_tail'] = rc, tail
    if rc != 0:
        json.dump(result, open(os.path.join(out_arm, 'summary.json'), 'w'), indent=1)
        raise SystemExit('900 failed: %s' % tail)
    result['d900'] = summarize(os.path.join(out_arm, 'd900'), 900)
    dec, old = build_dec_1050(arm, result['d900']['policy_sha256'])
    result['native_900_policy_sha256'] = old.decode() if isinstance(old, bytes) else old
    rc, tail = replay(1050, 900, dec, os.path.join(CM, 'in_1050', 'state_001050.json'),
                      os.path.join(out_arm, 'd1050'), os.path.join(out_arm, 'd1050.log'))
    result['d1050_rc'], result['d1050_tail'] = rc, tail
    if rc == 0:
        result['d1050'] = summarize(os.path.join(out_arm, 'd1050'), 1050)
    json.dump(result, open(os.path.join(out_arm, 'summary.json'), 'w'), indent=1)
    print(json.dumps({k: result.get(k) for k in ('arm', 'd900_rc', 'd1050_rc')}),
          'obj900', result.get('d900', {}).get('objective'), 'obj1050', result.get('d1050', {}).get('objective'))


if __name__ == '__main__':
    main()
