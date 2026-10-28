r"""Self-test of j1c_compare.py with synthetic changes (no recount is read; J1_REPORT values only).
python -B j1c_selftest.py   ->  AN/corr/selftest/selftest.json, ALL_OK or FAIL (exit 1).
  T1 identity: new := report values -> 0 changed, 0 sign changed, report text matched.
  T2 perturb: s31 4b +300 veh·h (bins moved in the last bin) and s41 4b -200 veh·h -> s31 4b/4/(a) cells change, the
     s31 4b sign flips, s41 label N flips to the 'same direction' text, s41 W stays 'moved' (d(removals A) > 0)."""
import io
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1c_compare as JC  # noqa: E402

PY = sys.executable
ST = os.path.join(JC.CORR, 'selftest')


def run_identity():
    p = subprocess.run([PY, '-B', os.path.join(HERE, 'j1c_compare.py'), '--identity'], capture_output=True, text=True,
                       encoding='utf-8')
    d = JC.V.jload(os.path.join(ST, 'j1c_compare.json'))
    return p.returncode, p.stdout.strip(), d


def run_perturb():
    orig = JC.load

    def patched(identity):
        an, old, new, nf = orig(True)
        new['4b']['31']['M4b'] += 300.0
        new['bins4b']['31'][-1] += 300.0
        new['4b']['41']['M4b'] -= 200.0
        new['bins4b']['41'][-1] -= 200.0
        return an, old, new, nf
    JC.load = patched
    JC.CORR = os.path.join(ST, 'perturb')
    sys.argv = ['j1c_compare.py', '--identity']
    try:
        JC.main()
        code = 0
    except SystemExit as e:
        code = e.code
    JC.load = orig
    d = JC.V.jload(os.path.join(ST, 'perturb', 'selftest', 'j1c_compare.json'))
    return code, d


def cell(d, loc, row, col):
    m = [c for c in d['cells'] if c['loc'] == loc and c['row'] == row and c['col'] == col]
    return m[0] if len(m) == 1 else None


def main():
    res = {}
    rc, out, d1 = run_identity()
    res['T1'] = {'exit': rc, 'stdout': out, 'cells': d1['cells_count'], 'report_text_checked': d1['checks']['K6_cells_with_report_text'],
                 'ok': rc == 0 and d1['cells_count']['changed'] == 0 and d1['cells_count']['sign_changed'] == 0
                 and d1['checks']['K6_cells_with_report_text'] >= 240}
    code, d2 = run_perturb()
    c_sign = cell(d2, '§3.1 d', 'M4b', 'd 31')
    c_lab = cell(d2, '§3.3 표시', 'label N', '41')
    c_w = cell(d2, '§3.3 표시', 'label W', '41')
    c_m4 = cell(d2, '§0 표', 'M4', 'd 31')
    c_cum = cell(d2, '§6 누적', 'OUT_a', '31 @9000')
    res['T2'] = {'exit': code, 'cells': d2['cells_count'],
                 'sign_4b_s31': c_sign and [c_sign['old'], c_sign['new'], c_sign['sign_changed']],
                 'label_N_s41': c_lab and [c_lab['old'], c_lab['new'], c_lab['changed']],
                 'label_W_s41': c_w and [c_w['old'], c_w['new'], c_w['changed']],
                 'd4_s31': c_m4 and [c_m4['old'], c_m4['new']], 'cum_out_a_s31_9000': c_cum and [c_cum['old'], c_cum['new']]}
    res['T2']['ok'] = bool(code == 0 and c_sign and c_sign['sign_changed'] and c_lab and c_lab['changed']
                           and c_lab['new'] == JC.V.LABEL_SAME and c_w and not c_w['changed']
                           and c_m4 and c_m4['changed'] and c_cum and c_cum['changed'])
    res['ALL_OK'] = res['T1']['ok'] and res['T2']['ok']
    with io.open(os.path.join(ST, 'selftest.json'), 'w', encoding='utf-8') as h:
        json.dump(res, h, ensure_ascii=False, indent=1)
    print('ALL_OK' if res['ALL_OK'] else 'FAIL', json.dumps(res, ensure_ascii=False)[:1500])
    sys.exit(0 if res['ALL_OK'] else 1)


if __name__ == '__main__':
    main()
