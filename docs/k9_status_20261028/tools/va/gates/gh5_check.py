"""G-H5' judge (amendment 34 section 5.1 row 5; form of amendment 21 section 7.5 / amendment 22 section 9.3) for the
preflight output of one V-A run name sdmpc31_v3c3_k92va_s<S>.
Copy of the K8b tool SP/j1/fix/gates/gh5_check.py (bb013ae6...) with expected values only (amendment 34 5.0 R4 item 1):
FRZ_K92 sha / K9-2-7 head / tuning c8e3ee2c... come from gcommon; the run name and seed are per seed; the
run-name-folder check looks in RVA.  Conditions 1-7 as K8b; condition 8 (no RVA run-name folder) is judged by the
driver's G-H5' stage from report.run_name_folder_exists (K8b already reported it here).
python -B gh5_check.py <preflight.out> <out.json> <seed>        prints paths, counts, sha, booleans only."""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gcommon as c  # noqa: E402

NET_SHA = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
WD_LINE = 'RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)'


def run_name(seed):
    return 'sdmpc31_v3c3_k92va_s%d' % int(seed)


def main(out_path, res_path, seed):
    seed = int(seed)
    NAME = run_name(seed)
    text = Path(out_path).read_text(encoding='utf-8-sig', errors='replace')
    lines = text.splitlines()
    k, rep = {}, {}

    def grab(pat):
        return [l for l in lines if re.search(pat, l)]
    fv = grab(r'FREEZE_VERIFIED')
    k['1_freeze_verified'] = (len(fv) == 1 and ('sha256=' + c.FREEZE_SHA) in fv[0] and ('head=' + c.HEAD) in fv[0])
    lp = grab(r'LAUNCH_PLAN_DETAIL')
    k['2_plan_detail_line'] = (len(lp) == 1 and 'network_sha=3de889f0' in lp[0] and 'controller=wu-link' in lp[0]
                               and 'sim_period=9000' in lp[0] and re.search(r'\bseed=%d\b' % seed, lp[0]) is not None)
    rd = grab(r'\bRUN_DIR\b')
    run_dir = Path(rd[-1].split('RUN_DIR', 1)[1].strip()) if rd else None
    rep['run_dir'] = str(run_dir) if run_dir else None
    plan_p = run_dir / 'launch_plan.json' if run_dir else None
    plan = c.read_json(plan_p) if plan_p and plan_p.is_file() else {}
    rep['plan_sha256'] = c.sha256_file(plan_p) if plan_p and plan_p.is_file() else None
    k['2_plan_tuning_sha'] = (plan.get('tuning') or {}).get('sha256') == c.TUNING_SHA
    k['2_plan_warnings_empty'] = plan.get('warnings') == []
    nc = grab(r'NETWORK_COPY_OK')
    no = grab(r'\bNETWORK_OK\b')
    k['3_network_copy_ok'] = len(nc) == 1 and ('sha256=' + NET_SHA) in nc[0]
    k['3_network_ok'] = len(no) == 1 and ('sha256=' + NET_SHA) in no[0]
    po = grab(r'PROVENANCE_OK')
    k['4_provenance_ok_freeze'] = len(po) == 1 and ('freeze=' + c.FREEZE_SHA) in po[0]
    prov_p = None
    if po:
        m = re.search(r'path=(.+?\.json)', po[0])
        prov_p = Path(m.group(1)) if m else None
    prov = c.read_json(prov_p) if prov_p and prov_p.is_file() else {}
    rep['provenance'] = str(prov_p) if prov_p else None
    rep['provenance_sha256'] = c.sha256_file(prov_p) if prov_p and prov_p.is_file() else None
    rep['provenance_run_id'] = prov.get('run_id')
    k['5_prov_env_policy'] = (prov.get('env') or {}).get('RW_DECISION_ERROR_POLICY') == 'hold_previous_on_exception'
    k['5_plan_expected_env_policy'] = (plan.get('expected_env') or {}).get('RW_DECISION_ERROR_POLICY') == \
        'hold_previous_on_exception'
    wd = [l for l in lines if WD_LINE in l]
    k['6_wd_line_exactly_1'] = len(wd) == 1
    rep['lines_with_RW_DECISION_ERROR_POLICY'] = sum('RW_DECISION_ERROR_POLICY' in l for l in lines)
    k['7_preflight_only_done'] = len(grab(r'PREFLIGHT_ONLY done; no VISSIM started')) == 1
    ex = grab(r'\bEXIT\b')
    k['7_exit_code_0'] = len(ex) == 1 and ('EXIT %s code=0' % NAME) in ex[0]
    rep['refused_lines'] = sum('REFUSED' in l for l in lines)
    rep['plan_tuning_sha256'] = (plan.get('tuning') or {}).get('sha256')
    rep['plan_controller'] = plan.get('controller')
    rep['plan_seed'] = plan.get('seed')
    rep['run_name_folder_exists'] = (c.RVA / NAME).exists()
    res = {'gate': "G-H5'", 'conditions': k, 'report': rep, 'output_file': str(out_path),
           'output_sha256': c.sha256_file(out_path),
           'status': 'PASS' if all(v is True for v in k.values()) else 'FAIL'}
    c.write_json(res_path, res)
    print('GH5', res['status'], json.dumps(k))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
