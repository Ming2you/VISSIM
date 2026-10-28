"""Development smoke of the probe patch BEFORE the P0 pin (not P0 / probe data; never used by a judgment).
State outside every declared list: R-obs v3c3-s43 T=3000 (sdmpc31_v3c3_nc_s43), controller wu-link (first SDMPC
decision: the previous action is NoControl, load_prices takes the first-decision path).  Dev tree TC1/trees/dev_<sha8>.
  1. configure-only (c1_p0_child) arms off and c1
  2. one full decision, arm c1, through the tree's k92_replay.py --no-compare
Takes the shared LOCK; prints only exit codes / flags / wall (no traffic value)."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402
import c1_p0 as P  # noqa: E402

RUN, T = 'sdmpc31_v3c3_nc_s43', 3000
DEV = C.TC1 / 'trees' / ('dev_' + P.PATCH_SHA8)
OUTD = C.TC1 / 'out' / 'dev'
LOG = C.make_logger(OUTD / 'dev_smoke.log')
P.LOG = LOG
P.NUMBA = OUTD / 'numba_cache'


def main():
    C.set_below_normal()
    C.lock_acquire('c1 dev smoke (configure x2 + one decision)', LOG)
    try:
        for arm in ('off', 'c1'):
            rec = P.cfg_run('robs_s43_t003000__' + arm, RUN, T, arm, tree=DEV, controller='wu-link', base=OUTD)
            LOG('DEV_CFG %s ok=%s token=%s err=%s' % (arm, rec.get('ok'), (rec.get('token') or '')[:8],
                                                     (rec.get('error') or rec.get('collect_error') or '')[-300:]))
        d = OUTD / 'dec_robs_s43_t003000__c1'
        if not (d / 'replay' / 'replay_run.json').is_file():
            P.prepare(RUN, T, d)
            env = C.child_env(OUTD / 'numba_cache')
            kr = DEV / 'diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_replay.py'
            argv = [C.PY, '-B', str(kr), '--replay-dir', str(d), '--root', str(DEV), '--tuning',
                    str(C.TOOLS / 'arms' / 'c1.json'), '--controller', 'wu-link', '--no-compare']
            t0 = time.time()
            rc, sec, text = C.run_capture(argv, OUTD / 'dec_robs_s43_t003000__c1.launch.txt', env)
            LOG('DEV_DEC exit=%s wall=%.0f' % (rc, time.time() - t0))
        rd = d / 'replay'
        rr = C.read_json(rd / 'replay_run.json', {}) or {}
        err = sorted(p.name for p in rd.glob('*.error.txt'))
        df = [C.text_count(rd / n, 'DECISION_FAILED') for n in ('adapter_stdout.txt', 'adapter_stderr.txt')]
        act = C.read_json(rd / ('action_%06d.json' % T), {}) or {}
        js = (act.get('metadata') or {}).get('joint_leader_selection') or {}
        flags = {'exit': rr.get('exit_code'), 'wall_sec': rr.get('wall_sec'), 'error_files': err, 'decision_failed': df,
                 'has_meter_neighbor_audit': 'meter_neighbor_audit' in js,
                 'finite_neighbor_audit_performed': js.get('finite_neighbor_audit_performed'),
                 'has_meter_operating_bounds': 'meter_operating_bounds' in js,
                 'has_original_held_candidate': 'original_held_candidate' in js,
                 'policy_has_audit': 'meter_neighbor_audit' in (js.get('policy') or {}),
                 'candidates_n': len(js.get('candidates') or []),
                 'audit_budget_audits_n': len(((js.get('meter_neighbor_audit') or {}).get('budget_audits')) or []),
                 'metadata_c1_port_keys': sorted(((act.get('metadata') or {}).get('c1_port') or {}).keys()),
                 'controller_variant': (act.get('metadata') or {}).get('controller_variant')}
        C.write_json(OUTD / 'dev_smoke_flags.json', flags)
        LOG('DEV_FLAGS %s' % json.dumps(flags))
    finally:
        C.lock_release(LOG)


if __name__ == '__main__':
    main()
