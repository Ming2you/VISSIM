"""V-A OfflineGates judge self-test (amendment 34 section 5.0 (i)(ii), plus a gh5_check parse check (iv) in the K8b
form SP/j1/fix/gates/selftest/gh5_on_k8r.json).  No V-A gate data: reads only K8b gate outputs (OUTH, read only), the
PushFreeze preflight capture (VA/freeze/k92_freeze_preflight.out) and FRZ_K92 evidence bytes.  No child process.
Writes only OUTVA/selftest_gjudge/ (synthetic bundles + result) and OUTVA/selftest_gh5/.  BLIND: prints booleans,
counts, paths only.

Expectations (written before the first run):
 (i)  K8b profile (FRZ_K8b, b9734abe, d0f9ef39..., list f954c2b0..., OUTH) reproduces the K8b judgement:
      GB-7' status FAIL, 61 present, fails [1], pass 60/61, cond_true_counts 61 except c7_diff_in_A 60,
      control_fields_equal_count 61, T=1 outside_A = outside_A_and_EK92 = [/diagnostics/leg_ramp_split_len_SC1001_W_out],
      no E_K92 hit in any row and c7_A_or_EK92 == c7_declared_A in every row (K8b outputs carry no E_K92 path);
      hash A/B PASS (9 runs, control fields equal); GB-9' PASS (4/4); S PASS 74/74.
 (ii) synthetic tampering of the K8b GB-7' T=750 bundle (copies; T <= 750 so that neither side carries the
      (173, p4) floor key, which R-obs3 has only from T = 900), K8b profile:
      base copy -> ok True; new metadata key in the replay JSON -> c7 False, ok False; one byte appended to the replay
      CSV -> c8 False, ok False; tuning sha in the summary changed -> c5 False, ok False.
      E_K92 wiring (K8b profile with E_K92 evidence Root = FRZ_K92): the four E_K92 keys added to the replay metadata
      with the declared values -> c7 True, c7_declared_A False, hits E1-E4, ok True; same but floor value 1 ulp larger
      -> c7 False, ok False.
 (iv) gh5_check (seed 31) on the PushFreeze no-control preflight capture: conditions all True except
      2_plan_detail_line (controller=no-control) and 7_exit_code_0 (other run name); status FAIL;
      run_name_folder_exists False.
Last line ALL_OK or NOT_OK."""
import copy
import json
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gcommon as c  # noqa: E402
import gjudge as gj  # noqa: E402
import gb7_k92decl as ek  # noqa: E402
import gh5_check  # noqa: E402

DK912 = '/diagnostics/leg_ramp_split_len_SC1001_W_out'
OUT = c.OUTV / 'selftest_gjudge'
OUT_GH5 = c.OUTV / 'selftest_gh5'
PRE_OUT = HERE.parent / 'freeze' / 'k92_freeze_preflight.out'
TS = 750
results = {}
ALL = True


def check(key, cond, detail=None):
    global ALL
    results[key] = {'ok': bool(cond), 'detail': detail}
    ALL = ALL and bool(cond)
    print('%-58s %s %s' % (key, 'OK ' if cond else 'BAD', '' if detail is None else json.dumps(detail)[:200]))


def part_i():
    P = gj.PROFILE_K8B
    g = gj.judge_gb7(P)
    keys = gj.COND_KEYS
    exp_counts = {k: (60 if k == 'c7_diff_in_A' else 61) for k in keys}
    check('i.gb7.status_FAIL', g['status'] == 'FAIL', g['status'])
    check('i.gb7.present_61_fails_[1]_pass_60', g['n_present'] == 61 and g['fails'] == [1] and g['pass_count'] == 60,
          [g['n_present'], g['fails'], g['pass_count']])
    check('i.gb7.cond_true_counts', g['cond_true_counts'] == exp_counts, g['cond_true_counts'])
    check('i.gb7.control_fields_equal_61', g['control_fields_equal_count'] == 61, g['control_fields_equal_count'])
    t1 = next(r for r in g['rows'] if r['T'] == 1)
    check('i.gb7.T1_c7_false_both', t1['c7_diff_in_A'] is False and t1['c7_declared_A'] is False)
    check('i.gb7.T1_outside_A_is_dk912', sorted({p for p, _k in t1['diff_outside_A']}) == [DK912],
          sorted({p for p, _k in t1['diff_outside_A']}))
    check('i.gb7.T1_outside_A_EK92_is_dk912', sorted({p for p, _k in t1['diff_outside_A_EK92']}) == [DK912])
    check('i.gb7.no_ek92_hit', all(not (r.get('ek92') or {}).get('hits') for r in g['rows']))
    check('i.gb7.c7_equals_declared_every_row', all(r['c7_diff_in_A'] == r['c7_declared_A'] for r in g['rows']))
    check('i.gb7.list_is_k8b', g['allowed_list']['list_sha256'] == c.LIST_K8B_SHA, g['allowed_list']['list_sha256'][:16])
    h = gj.judge_hash(P)
    check('i.hash.PASS', h['status'] == 'PASS', h['status'])
    check('i.hash.controls_equal_9', sum(1 for gg in h['groups'].values() for r in gg['runs'].values()
                                         if r.get('control_fields_equal') is True) == 9)
    g9 = gj.judge_gb9(P)
    check('i.gb9.PASS', g9['status'] == 'PASS' and len(g9['rows']) == 4, [g9['status'], g9['fails']])
    s = gj.judge_s(g, h, g9)
    check('i.S.PASS_74', s['status'] == 'PASS' and s['n'] == 74, [s['status'], s['n']])
    return {'gb7_status': g['status'], 'gb7_fails': g['fails'], 'hash': h['status'], 'gb9': g9['status'],
            'S': [s['status'], s['n']]}


def make_case(name, src_dir, summary, mutate_json=None, mutate_csv=False, mutate_summary=None):
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    for side in ('original', 'replay'):
        (d / side).mkdir(parents=True)
        for ext in ('json', 'csv'):
            shutil.copy2(src_dir / side / ('action_%06d.%s' % (TS, ext)), d / side / ('action_%06d.%s' % (TS, ext)))
    if mutate_json:
        p = d / 'replay' / ('action_%06d.json' % TS)
        doc = json.loads(p.read_text(encoding='utf-8-sig'))
        mutate_json(doc)
        p.write_text(json.dumps(doc), encoding='utf-8')
    if mutate_csv:
        p = d / 'replay' / ('action_%06d.csv' % TS)
        p.write_bytes(p.read_bytes() + b'#')
    s = copy.deepcopy(summary)
    s['replay_dir'] = str(d)
    if mutate_summary:
        mutate_summary(s)
    return s


def ek_keys(doc, floor_value=1045.1612903225805):
    md = doc.setdefault('metadata', {})
    md['k92_w'] = {'after': 5209.8, 'evidence_sha256': ek.W_EVIDENCE_SHA256, 'u4_sha256': ek.U4_SHA256}
    md['k92_hb'] = {'evidence_sha256': ek.HB_EVIDENCE_SHA256, 'rule_code_sha256': ek.RULE_CODE_SHA256}
    md['k92_hb_seed_binding'] = 1.0
    md[c.FLOOR_KEY] = floor_value


def part_ii():
    P = gj.PROFILE_K8B
    PE = dict(P, EK92_ROOT=c.FRZN)
    src_sum = c.read_json(c.OUTH / 'gb7' / 'A' / ('T%06d.summary.json' % TS))
    src = Path(src_sum['replay_dir'])
    out = {}
    r = gj.gb7_row(make_case('base', src, src_sum), TS, P)
    check('ii.base_ok', r['ok'] is True, {k: r.get(k) for k in gj.COND_KEYS})
    out['base'] = r['ok']
    r = gj.gb7_row(make_case('newkey', src, src_sum,
                             mutate_json=lambda d: d['metadata'].__setitem__('k92va_selftest_new_key', 1.0)), TS, P)
    check('ii.newkey_c7_false', r['c7_diff_in_A'] is False and r['ok'] is False
          and all(r[k] is True for k in gj.COND_KEYS if k != 'c7_diff_in_A'), r.get('diff_outside_A_EK92'))
    r = gj.gb7_row(make_case('csv1', src, src_sum, mutate_csv=True), TS, P)
    check('ii.csv1_c8_false', r['c8_csv'] is False and r['ok'] is False
          and all(r[k] is True for k in gj.COND_KEYS if k != 'c8_csv'))
    r = gj.gb7_row(make_case('tuning', src, src_sum,
                             mutate_summary=lambda s: s['replay_run'].__setitem__('tuning_sha256', '0' * 64)), TS, P)
    check('ii.tuning_c5_false', r['c5_tuning'] is False and r['ok'] is False
          and all(r[k] is True for k in gj.COND_KEYS if k != 'c5_tuning'))
    r = gj.gb7_row(make_case('ek92_four', src, src_sum, mutate_json=ek_keys), TS, PE)
    hits = sorted(e for _p, e in (r.get('ek92') or {}).get('hits', []))
    check('ii.ek92_four_c7_true_declared_false', r['c7_diff_in_A'] is True and r['c7_declared_A'] is False
          and hits == ['E1', 'E2', 'E3', 'E4'] and r['ok'] is True, hits)
    check('ii.ek92_four_hits_counted', all(r['hits'].get(e, {}).get('paths') == 1 for e in ('E1', 'E2', 'E3', 'E4')),
          {e: r['hits'].get(e) for e in ('E1', 'E2', 'E3', 'E4')})
    r = gj.gb7_row(make_case('ek92_floor_1ulp', src, src_sum,
                             mutate_json=lambda d: ek_keys(d, 1045.1612903225807)), TS, PE)
    check('ii.ek92_floor_1ulp_c7_false', r['c7_diff_in_A'] is False and r['ok'] is False,
          sorted({p for p, _k in r.get('diff_outside_A_EK92', [])}))
    return out


def part_iv():
    OUT_GH5.mkdir(parents=True, exist_ok=True)
    resp = OUT_GH5 / 'gh5_on_k92pre_s31.json'
    gh5_check.main(str(PRE_OUT), str(resp), 31)
    r = c.read_json(resp)
    k = r['conditions']
    exp_false = {'2_plan_detail_line', '7_exit_code_0'}
    check('iv.gh5_parse_pattern', all((v is False) == (n in exp_false) for n, v in k.items()) and len(k) == 12, k)
    check('iv.gh5_status_FAIL', r['status'] == 'FAIL')
    check('iv.gh5_run_folder_absent', r['report']['run_name_folder_exists'] is False)
    return r['status']


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {'schema': 'k92-va-gates-selftest/v1',
           'files_sha256': {n: c.sha256_file(HERE / n) for n in ('gcommon.py', 'gjudge.py', 'gb7_k92decl.py',
                                                                 'gh5_check.py', 'va_gates_selftest.py')},
           'i': part_i(), 'ii': part_ii(), 'iv': part_iv()}
    res['checks'] = results
    res['ALL_OK'] = ALL
    c.write_json(OUT / 'va_gates_selftest.json', res)
    print('CHECKS %d/%d' % (sum(1 for v in results.values() if v['ok']), len(results)))
    print('ALL_OK' if ALL else 'NOT_OK')
    return 0 if ALL else 1


if __name__ == '__main__':
    sys.exit(main())
