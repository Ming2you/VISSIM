"""Self-test of the VerifyGates tools BEFORE any V-A gate output is read (amendment 34 section 5.0 independent
verification).  Reads only: FRZ_K92 list / evidence files (definitions), the K7 gb_common.py text, the V-B chain outputs
(already reported, K92_VB_REPORT r3), the K8b gate outputs OUTH (already reported and verified).  Writes only under
VGO/selftest.  No V-A gate output (OUTVA) is opened here.

python -B v_selftest.py <VGO>/selftest

Expectations (written before the first run):
 (a) deep_diff synthetic: D1 /a type; D2 /l list_length; D3 /l[0]/x value; D4 /k presence replay; D5 /k presence
     original; D6 /a then /b (keys sorted); D7 root list '[0][0]' value.  And on three real K8b pairs (OUTH gb7 A
     T=1, 900, 9000 original vs replay) my path sequence == the K7 gb_common.deep_diff path sequence (function text
     executed from the K7 file, not imported).
 (b) E_K92 synthetic (list = FRZ_K92 gb7_allowed.py, evidence Root = FRZ_K92 unless said):
     c7_A_or_EK92 True: S01 (four paths replay-only, all conditions), S02 (floor key equal on both sides, binding 0.0),
     S18 (only V + R2-12 differences; here c7_declared_A is True too), S22 (four E paths + an R2-02 value path).
     c7_A_or_EK92 False: S03 W evidence sha, S04 u4 sha, S05 after 5209.800000000001, S06 H-b evidence sha, S07 rule
     sha, S08 Root W evidence file one byte different, S09 k92_w both sides (sub value differs), S09b binding both
     sides (value differs), S10 binding 2.0, S10b binding int 1, S11 floor key hash16 different, S12 floor 1 ulp above
     s, S13 floor key with binding 0.0, S14 floor both sides (original < s), S15 extra k92_other, S16 floor key without
     binding key, S17 k92_w not a dict, S19 k92_w original side only, S20 binding bool True, S21 k92_hb a list.
     c7_declared_A False in every case except S18.
 (c) V-B dry check (amendment 34 5.2-6 (나) text): VB-41w OFF (original role) vs B1 (replay role), T = 1, 150, ..., 750,
     Root = VBT, floor key = head_discharge_floor_173_p4_301ceabb95f116fa: E1, E2, E3 inside E_K92 in all six; E4 inside
     at T = 1, 150; at T = 300..750 E4 fails with exactly ['binding_float_1']; outside A u E_K92: T=1 none; T=150 the four
     chain paths {head_observation_prior_discarded, n31_binding/vsl_cohort_initialization/{sha256,source},
     /prediction_error/source_action_json}; T=300..750 head_observation_groups_carried + the same three + the floor key.
     With the FRZ_K92 floor name (e36d6761cfeac634) the 301ceabb path is outside A u E_K92 in all six.
 (d) K8b reproduction (v_judge profile K8B on OUTH): GB-7' FAIL with fails [1], condition 7 true 60 / others 61,
     control fields 61, outside A = ['/diagnostics/leg_ramp_split_len_SC1001_W_out'], E hits 0, every row equal to
     the K8b gate rows (c1-c6, c7 = K8b c7_diff_in_A, c8, control fields, ok, outside paths, diff count), hits by item
     equal to K8b gb7_result hits_by_item; ps1 exit inferred == harness record 74/74; hash A/B PASS, six pairs 0 outside V
     and CSV same, run flags equal K8b; GB-9' PASS, walls == K8b values (693.8/679.112104, 742/728.316562,
     723.4/710.84015, 705.2/691.14517), code bytes mismatch 0; S PASS 74/74.
Prints SELFTEST lines and ALL_OK / NOT_OK."""
import copy
import json
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v_lib as L  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
checks = {}


def check(name, cond, info=None):
    checks[name] = {'ok': bool(cond), 'info': info}
    print('SELFTEST %s %s %s' % ('OK ' if cond else 'BAD', name, '' if info is None else json.dumps(info, default=str)[:300]),
          flush=True)


# ------------------------------------------------------------------------------------------------ (a)
dd = lambda a, b: L.deep_diff(a, b)  # noqa: E731
check('a.D1', dd({'a': 1}, {'a': 1.0}) == [('/a', 'type', None)])
check('a.D2', dd({'l': [1, 2]}, {'l': [1, 2, 3]}) == [('/l', 'list_length', None)])
check('a.D3', dd({'l': [{'x': 1}]}, {'l': [{'x': 2}]}) == [('/l[0]/x', 'value', None)])
check('a.D4', dd({}, {'k': {'z': 1}}) == [('/k', 'presence', 'replay')])
check('a.D5', dd({'k': 1}, {}) == [('/k', 'presence', 'original')])
check('a.D6', [p for p, _k, _s in dd({'b': 1, 'a': 1}, {'b': 2, 'a': 2})] == ['/a', '/b'])
check('a.D7', dd([[1]], [[2]]) == [('[0][0]', 'value', None)])
k7src = L.read_text(Path(r'D:/VISSIM_runs/20261001_v3c3/reports/gb/gb_common.py'))
m = re.search(r'^def deep_diff\(a, b, path=\'\', out=None\):\n(?:    .*\n|\n)+?(?=\S)', k7src, re.M)
ns = {}
exec(compile(m.group(0), 'k7_deep_diff', 'exec'), ns)  # noqa: S102 - K7 definition text, read only
for T in (1, 900, 9000):
    d = L.OUTH / 'gb7' / 'A' / ('T%06d' % T)
    a = L.read_json(d / 'original' / ('action_%06d.json' % T))
    b = L.read_json(d / 'replay' / ('action_%06d.json' % T))
    mine = [p for p, _k, _s in L.deep_diff(a, b)]
    k7 = [p for p, _m in ns['deep_diff'](a, b)]
    check('a.k7_equiv_T%d' % T, mine == k7 and len(mine) > 0, {'n': len(mine)})

# ------------------------------------------------------------------------------------------------ (b)
G = L.AllowedList(L.FRZN, L.GB7_FILE_SHA, L.LIST_SHA, 35)
check('b.list', G.ok, G.record())
check('b.evidence_files_fixed', L.sha256_file(L.FRZN / L.W_EVID_REL) == L.W_EVID_SHA
      and L.sha256_file(L.FRZN / L.HB_EVID_REL) == L.HB_EVID_SHA)
S = 1045.1612903225805
FK = L.FLOOR_KEY
base = {'N_P_star': [1, 2], 'metadata': {'decision_wall_sec': 1.0, 'x': 1}, 'diagnostics': {}, 'prediction': {'state_summary': {'q': 1}}}
GW = {'evidence': 'x.json', 'evidence_sha256': L.W_EVID_SHA, 'u4_sha256': L.U4_SHA, 'after': 5209.8, 'before': 1.0}
GH = {'evidence_sha256': L.HB_EVID_SHA, 'rule_code_sha256': L.RULE_SHA, 'seed': S}


def mk(meta_b=None, meta_a=None, other_b=None):
    a = copy.deepcopy(base)
    b = copy.deepcopy(base)
    a['metadata'].update(meta_a or {})
    b['metadata'].update(meta_b or {})
    for p, v in (other_b or {}).items():
        cur = b
        keys = p.strip('/').split('/')
        for k in keys[:-1]:
            cur = cur.setdefault(k, {})
        cur[keys[-1]] = v
    return a, b


good4 = {'k92_w': GW, 'k92_hb': GH, 'k92_hb_seed_binding': 1.0, FK: S}
badroot = OUT / 'root_bad'
if badroot.exists():
    shutil.rmtree(badroot)
for rel in (L.W_EVID_REL, L.HB_EVID_REL):
    t = badroot / Path(*rel.split('/'))
    t.parent.mkdir(parents=True, exist_ok=True)
    data = open(L.long(L.FRZN / Path(*rel.split('/'))), 'rb').read()
    if rel == L.W_EVID_REL:
        data = data[:-1] + bytes([data[-1] ^ 1])
    t.write_bytes(data)
cases = {
    'S01': (mk(good4), L.FRZN, True, False),
    'S02': (mk({'k92_w': GW, 'k92_hb': GH, 'k92_hb_seed_binding': 0.0, FK: S}, {FK: S}), L.FRZN, True, False),
    'S03': (mk(dict(good4, k92_w=dict(GW, evidence_sha256='0' * 64))), L.FRZN, False, False),
    'S04': (mk(dict(good4, k92_w=dict(GW, u4_sha256='0' * 64))), L.FRZN, False, False),
    'S05': (mk(dict(good4, k92_w=dict(GW, after=5209.800000000001))), L.FRZN, False, False),
    'S06': (mk(dict(good4, k92_hb=dict(GH, evidence_sha256='0' * 64))), L.FRZN, False, False),
    'S07': (mk(dict(good4, k92_hb=dict(GH, rule_code_sha256='0' * 64))), L.FRZN, False, False),
    'S08': (mk(good4), badroot, False, False),
    'S09': (mk(good4, {'k92_w': dict(GW, after=1.0)}), L.FRZN, False, False),
    'S09b': (mk({'k92_w': GW, 'k92_hb': GH, 'k92_hb_seed_binding': 0.0}, {'k92_hb_seed_binding': 1.0}), L.FRZN, False, False),
    'S10': (mk({'k92_w': GW, 'k92_hb': GH, 'k92_hb_seed_binding': 2.0}), L.FRZN, False, False),
    'S10b': (mk(dict(good4, k92_hb_seed_binding=1)), L.FRZN, False, False),
    'S11': (mk({'k92_w': GW, 'k92_hb': GH, 'k92_hb_seed_binding': 1.0, FK[:-1] + '5': S}), L.FRZN, False, False),
    'S12': (mk(dict(good4, **{FK: 1045.1612903225807})), L.FRZN, False, False),
    'S13': (mk(dict(good4, k92_hb_seed_binding=0.0)), L.FRZN, False, False),
    'S14': (mk(good4, {FK: 1000.0}), L.FRZN, False, False),
    'S15': (mk(dict(good4, k92_other=1.0)), L.FRZN, False, False),
    'S16': (mk({'k92_w': GW, 'k92_hb': GH, FK: S}), L.FRZN, False, False),
    'S17': (mk(dict(good4, k92_w='w')), L.FRZN, False, False),
    'S18': (mk({'decision_wall_sec': 2.0}, None, {'/diagnostics/leg_ramp_split_len_SC1001_W_out': 3.0}), L.FRZN, True, True),
    'S19': (mk({'k92_hb': GH, 'k92_hb_seed_binding': 1.0, FK: S}, {'k92_w': GW}), L.FRZN, False, False),
    'S20': (mk(dict(good4, k92_hb_seed_binding=True)), L.FRZN, False, False),
    'S21': (mk(dict(good4, k92_hb=[GH])), L.FRZN, False, False),
    'S22': (mk(good4, None, {'/prediction/state_summary/q': 2}), L.FRZN, True, False),
}
for name, ((a, b), root, exp_ae, exp_a) in cases.items():
    j = L.cond7(a, b, G, root)
    check('b.' + name, j['c7_A_or_EK92'] is exp_ae and j['c7_declared_A'] is exp_a and not j['which_disagree'],
          {'ae': j['c7_A_or_EK92'], 'a': j['c7_declared_A'], 'outAE': j['outside_A_and_EK92'],
           'failed': j['ek92_failed']})
shutil.rmtree(badroot)

# ------------------------------------------------------------------------------------------------ (c)
F41 = 'head_discharge_floor_173_p4_301ceabb95f116fa'
chain3 = ['/metadata/n31_binding/vsl_cohort_initialization/sha256', '/metadata/n31_binding/vsl_cohort_initialization/source',
          '/prediction_error/source_action_json']
for T in (1, 150, 300, 450, 600, 750):
    off = L.read_json(L.VBCHAIN / 'vb41w_off' / 'dec' / ('action_%06d.json' % T))
    b1 = L.read_json(L.VBCHAIN / 'vb41w_b1' / 'dec' / ('action_%06d.json' % T))
    j = L.cond7(off, b1, G, L.VBT, floor_key=F41)
    items = sorted(i for _p, i in j['ek92_hits'])
    if T in (1, 150):
        exp_items, exp_failed = ['E1', 'E2', 'E3', 'E4'], []
    else:
        exp_items, exp_failed = ['E1', 'E2', 'E3'], [{'path': '/metadata/' + F41, 'item': 'E4', 'false': ['binding_float_1']}]
    if T == 1:
        exp_out = []
    elif T == 150:
        exp_out = sorted(['/metadata/head_observation_prior_discarded'] + chain3)
    else:
        exp_out = sorted(['/metadata/head_observation_groups_carried'] + chain3 + ['/metadata/' + F41])
    check('c.T%d' % T, items == exp_items and j['ek92_failed'] == exp_failed and sorted(j['outside_A_and_EK92']) == exp_out
          and j['c7_A_or_EK92'] is (T == 1) and not j['which_disagree'],
          {'items': items, 'failed': j['ek92_failed'], 'outAE': j['outside_A_and_EK92']})
    jx = L.cond7(off, b1, G, L.VBT)
    check('c.T%d_frzk92_name' % T, ('/metadata/' + F41) in jx['outside_A_and_EK92'])

# ------------------------------------------------------------------------------------------------ (d)
import v_judge as VJ  # noqa: E402  (my own tool)
kout = OUT / 'k8b_judge.json'
VJ.main('K8B', kout)
R = L.read_json(kout)
K = {n: L.read_json(L.OUTH / 'judge' / n) for n in ('gb7_result.json', 'hash_result.json', 'gb9_result.json', 's_result.json')}
g7 = R['gb7']
check('d.gb7_status', g7['status'] == 'FAIL' and g7['fails'] == [1] and g7['control_fields_equal_count'] == 61,
      {'status': g7['status'], 'fails': g7['fails']})
check('d.gb7_cond', g7['cond_true_counts'] == {k: (60 if k == 'c7_A_or_EK92' else 61) for k in VJ.COND}, g7['cond_true_counts'])
check('d.gb7_outside', g7['outside_A_union'] == ['/diagnostics/leg_ramp_split_len_SC1001_W_out']
      and g7['outside_A_and_EK92_union'] == ['/diagnostics/leg_ramp_split_len_SC1001_W_out']
      and g7['ek92_item_decisions'] == {'E1': 0, 'E2': 0, 'E3': 0, 'E4': 0} and g7['c7_declared_A_count'] == 60)
kr = {r['T']: r for r in K['gb7_result.json']['rows']}
bad = []
for r in g7['rows']:
    x = kr[r['T']]
    pairs = [('c1_prepare', 'c1_prepare'), ('c2_ps1_and_compare', 'c2_ps1_and_compare'), ('c3_freeze', 'c3_freeze'),
             ('c4_roots', 'c4_roots'), ('c5_tuning', 'c5_tuning'), ('c6_S', 'c6_S'), ('c7_A_or_EK92', 'c7_diff_in_A'),
             ('c8_csv', 'c8_csv'), ('control_fields_equal', 'control_fields_equal'), ('ok', 'ok')]
    d = [m for m, k in pairs if bool(r.get(m)) != bool(x.get(k))]
    if sorted(p for p, _k in x.get('diff_outside_A') or []) != sorted(r.get('outside_A') or []) or x.get('diff_count') != r.get('diff_count'):
        d.append('paths')
    if d:
        bad.append([r['T'], d])
check('d.gb7_rows_equal_k8b', not bad, bad[:5])
mi = {k: v['paths'] for k, v in g7['hits_by_item'].items()}
ki = {k: v['paths'] for k, v in K['gb7_result.json']['hits_by_item'].items()}
check('d.gb7_hits_by_item_equal_k8b', mi == ki, {'mine_only': sorted(set(mi) - set(ki)), 'k8b_only': sorted(set(ki) - set(mi))})
n_agree = (g7['ps1_exit_agrees_harness_count']
           + sum(1 for g in R['hash']['groups'].values() for r in g['runs'].values() if r.get('ps1_exit_agrees_harness'))
           + sum(1 for r in R['gb9']['rows'] if r.get('ps1_exit_agrees_harness')))
check('d.ps1_exit_inference_74', n_agree == 74, n_agree)
h = R['hash']
pairs_ok = all(v['n_outside_V'] == 0 and v['csv_same'] for g in h['groups'].values() for v in g['pairs'].values())
runs_eq = all(bool(K['hash_result.json']['groups'][T]['runs'][s]['ok_h']) == bool(r['ok_h'])
              for T, g in h['groups'].items() for s, r in g['runs'].items())
check('d.hash', h['status'] == 'PASS' and pairs_ok and runs_eq, {'status': h['status']})
g9 = R['gb9']
kw = {r['T']: (r['wall']['replay_run_wall_sec'], r['wall']['decision_wall_sec']) for r in K['gb9_result.json']['rows']}
check('d.gb9', g9['status'] == 'PASS' and all((r['wall']['a'], r['wall']['b']) == kw[r['T']] for r in g9['rows'])
      and all(r['c1_S'] and r['c2_valid'] and r['c3_wall'] and not r['code_bytes']['mismatch'] and r['code_bytes']['checked'] > 0
              for r in g9['rows']),
      [(r['T'], r['wall']['a'], r['wall']['b'], r['code_bytes']['checked'], r['code_bytes']['mismatch'][:3]) for r in g9['rows']])
check('d.S', R['S']['status'] == 'PASS' and R['S']['n'] == 74)
check('d.previous_arg_and_controller', g7['report_previous_arg_ok_count'] == 61 and g7['report_controllers'] == ['no-control']
      and g7['original_is_robs3_count'] == 61 and g7['which_disagree_total'] == 0,
      [g7['report_previous_arg_ok_count'], g7['report_controllers'], g7['original_is_robs3_count'], g7['which_disagree_total']])

ok = all(v['ok'] for v in checks.values())
L.write_json(OUT / 'v_selftest.json', {'checks': checks, 'all_ok': ok, 'n': len(checks)})
print('SELFTEST_SUMMARY %d/%d %s' % (sum(v['ok'] for v in checks.values()), len(checks), 'ALL_OK' if ok else 'NOT_OK'))
sys.exit(0 if ok else 1)
