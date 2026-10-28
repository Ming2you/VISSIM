# B0 offline test of the ported exception-only hold (control_hold.write_hold + require_exception_hold) in the b0 tree.
# No VISSIM.  Inputs: A0 pristine T=1050 (codex joint recorded state + recorded previous action T=900), copied into a temp
# folder under work/b0/hold_test/.  Five cases: eligible ValueError -> held files; TimeoutError / BrokenProcessPool ->
# refused; frame in sdmpc.load_prices -> refused; no report -> refused.  Also the codex 'hold_previous' policy still
# accepted without a report.   usage: python -B test_hold_b0.py
import json, os, shutil, sys, types
B0 = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/code'
SRC = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/pristine/T001050/sdmpc/decisions_sdmpc31_sdmpc8100_s29'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, B0)
sys.dont_write_bytecode = True
from evaluation.controllers import control_hold  # noqa: E402
tuning = json.load(open(B0 + '/diagnostics/b0_v3c3/config_b0_v3c3.json', encoding='utf-8-sig'))
assert tuning['runtime']['decision_error_policy'] == 'hold_previous_on_exception'
TB = 'Traceback (most recent call last):'
REPORTS = {
    'eligible_valueerror': [TB, '  File "D:\\x\\evaluation\\controllers\\calibrated_urban_runtime.py", line 143, in install', "    raise ValueError('Missing observed speed')", "ValueError: Missing observed speed"],
    'excluded_timeout': [TB, '  File "D:\\x\\evaluation\\controllers\\sdmpc.py", line 10, in solve', 'TimeoutError: slow'],
    'excluded_brokenpool': [TB, '  File "D:\\x\\evaluation\\controllers\\sdmpc.py", line 10, in solve', 'concurrent.futures.process.BrokenProcessPool: gone'],
    'contract_frame': [TB, '  File "D:\\x\\evaluation\\controllers\\sdmpc.py", line 99, in load_prices', 'ValueError: bad prices'],
    'no_report': None,
}
results = {}
for name, report in list(REPORTS.items()) + [('codex_policy_no_report', None)]:
    d = os.path.join(HERE, 'hold_test', name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    for f in ('state_001050.json', 'action_000900.json', 'action_000900.csv'):
        shutil.copy2(SRC + '/' + f, d + '/' + f)
    if report is not None:
        open(d + '/action_001050.error.txt', 'w', encoding='utf-8').write(chr(10).join(report) + chr(10))
    args = types.SimpleNamespace(state_json=d + '/state_001050.json', previous_action_json=d + '/action_000900.json',
                                 out_action_json=d + '/action_001050.json', out_action_csv=d + '/action_001050.csv')
    tun = tuning
    if name == 'codex_policy_no_report':
        tun = json.loads(json.dumps(tuning))
        tun['runtime']['decision_error_policy'] = 'hold_previous'
    try:
        control_hold.write_hold(args, tun)
        ok = os.path.exists(args.out_action_json) and os.path.exists(args.out_action_csv)
        held = json.load(open(args.out_action_json, encoding='utf-8'))['metadata'] if ok else None
        results[name] = {'held': ok, 'status': held.get('controller_status') if held else None,
                         'source_sim_sec': held.get('hold_previous', {}).get('source_sim_sec') if held else None}
    except Exception as exc:  # noqa: BLE001
        results[name] = {'held': False, 'refused': type(exc).__name__ + ': ' + str(exc)[:160]}
want = {'eligible_valueerror': True, 'excluded_timeout': False, 'excluded_brokenpool': False, 'contract_frame': False,
        'no_report': False, 'codex_policy_no_report': True}
for k, v in results.items():
    print(k, 'held' if v['held'] else 'refused', 'want', 'held' if want[k] else 'refused', '|', v.get('status') or v.get('refused'))
json.dump({'results': results, 'want': want, 'all_as_wanted': all(results[k]['held'] == want[k] for k in want)},
          open(os.path.join(HERE, 'hold_test', 'test_hold_b0.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('all_as_wanted', all(results[k]['held'] == want[k] for k in want))
