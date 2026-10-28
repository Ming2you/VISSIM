"""Synthetic self-tests of the C1 probe patch inside a patched tree (no run data, no traffic computation).

    python -B c1_selftest.py <tree root> <out.json>
Checks: (a) the seven ported functions ast.dump == CX (G-K1 (g) form); (b) normalise_service_table None path ==
c20aff1d function on a table set, keep_green_10 on the evidence curves == evidence installed tables (repr) and its
refusals; (c) c1_port.validate refusals (G-K3 form) and acceptances; (d) apply_tuning cases (i)-(iii) on OUC;
(e) operating_bounds: codex floor kept when it is a table green, lowered 9 -> 8 on the H table (RV-2), G-A7;
(f) M3 refusal on a new zero green and np_only domain; (g) the neighbor-count formula N = f(u_E) + f(u_W) on
synthetic sequence coordinates (P0-11 / G-K2 (a) form) through the ported meter_neighbors."""
import ast
import copy
import importlib
import json
import math
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2])
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
CX = Path(r'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff')
GWT8 = Path(r'D:/VISSIM-merge/sim3-n31-k8')
REV = 'c20aff1d7bf0c432cb4f20e2922bd406d857aa5d'
RES = {'cases': []}


def case(name, fn):
    try:
        ok, info = fn()
    except Exception as exc:  # noqa: BLE001
        ok, info = False, 'EXC ' + repr(exc)[:300]
    RES['cases'].append({'name': name, 'ok': bool(ok), 'info': info})


def raises(fn, needle):
    try:
        fn()
    except ValueError as exc:
        return needle in str(exc), str(exc)[:160]
    return False, 'no ValueError'


def fn_dump(path, name, text=None):
    src = text if text is not None else Path(path).read_bytes().decode('utf-8').replace('\r\n', '\n')
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.dump(node, include_attributes=False)
    return None


# (a) ported functions
for rel, name in (('evaluation/controllers/sdmpc.py', 'retain_feasible_held'),
                  ('evaluation/controllers/sdmpc.py', 'meter_neighbors'),
                  ('evaluation/controllers/sdmpc.py', 'audit_meter_neighbors'),
                  ('evaluation/controllers/sdmpc.py', 'audit_meter_budget_candidates'),
                  ('evaluation/controllers/physical_ramp_branches.py', 'configure_operating_bounds'),
                  ('evaluation/controllers/physical_ramp_branches.py', 'operating_green_allowed'),
                  ('evaluation/controllers/physical_ramp_branches.py', 'leader_seed_domain')):
    case('ast_' + name, lambda rel=rel, name=name: (fn_dump(ROOT / rel, name) == fn_dump(CX / rel, name)
                                                   and fn_dump(ROOT / rel, name) is not None, rel))

prb = importlib.import_module('evaluation.controllers.physical_ramp_branches')
old_src = subprocess.run(['git', '-C', str(GWT8), 'show', REV + ':evaluation/controllers/physical_ramp_branches.py'],
                         capture_output=True, check=True).stdout.decode('utf-8')
old_mod = types.ModuleType('old_prb')
old_mod.__dict__['__file__'] = str(ROOT / 'evaluation/controllers/physical_ramp_branches.py')
exec(compile(old_src, 'old_prb', 'exec'), old_mod.__dict__)
ref = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json').read_text(encoding='utf-8'))
ouc = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json').read_text(encoding='utf-8'))
ev = json.loads((ROOT / 'diagnostics/sdmpc_n31_20260924/c1/evidence/head_service_fwe_c1.json').read_text(encoding='utf-8'))
per_lane = ouc['actuation']['real_world_ramp_metering']['per_lane_veh_per_cycle']
tables = [{'0': 0., **{g: L * float(n) * 3600 / 10 for g, n in per_lane.items()}} for L in (1, 2)]
tables += [{'0': 0., **{g: n * 3600 / 10 for g, n in c.items()}}
           for c in ref['freeway']['physical_ramp_head_service_veh_per_cycle'].values()]
tables += [{'0': 0., '2': 360., '3': 360., '4': 720., '10': 900.}]


def none_path():
    for t in tables:
        a = old_mod.normalise_service_table(copy.deepcopy(t), 2.0)
        b = prb.normalise_service_table(copy.deepcopy(t), 2.0)
        if repr(a) != repr(b):
            return False, repr((a, b))[:200]
    try:
        old_mod.normalise_service_table({'0': 0., '9': 900., '10': 900.}, 2.0)
        old_ok = None
    except ValueError as exc:
        old_ok = str(exc)
    try:
        prb.normalise_service_table({'0': 0., '9': 900., '10': 900.}, 2.0)
        new_ok = None
    except ValueError as exc:
        new_ok = str(exc)
    return old_ok == new_ok and old_ok is not None, 'tables=%d refusal_same=%s' % (len(tables), old_ok == new_ok)


case('normalise_none_path_equals_c20aff1d', none_path)


def keep10():
    out = {}
    for m, curve in ev['values']['curves_veh_per_cycle'].items():
        t, d = prb.measured_head_service_table(curve, 2.0, full_service_rule='keep_green_10')
        out[m] = (repr(t) == repr(ev['values']['installed_service_by_green_veh_h'][m]), d == {'9': '10'})
    return all(a and b for a, b in out.values()), out


case('keep_green_10_equals_evidence', keep10)
case('keep_green_10_refuses_no_10', lambda: raises(lambda: prb.normalise_service_table(
    {'0': 0., '8': 900., '9': 900.}, 2.0, full_service_rule='keep_green_10'), 'keep_green_10'))
case('keep_green_10_refuses_10_not_largest', lambda: raises(lambda: prb.normalise_service_table(
    {'0': 0., '10': 900., '11': 900.}, 2.0, full_service_rule='keep_green_10'), 'keep_green_10'))
case('keep_green_10_refuses_unknown_rule', lambda: raises(lambda: prb.normalise_service_table(
    {'0': 0., '10': 900.}, 2.0, full_service_rule='keep_lowest'), 'Unknown physical meter full-service rule'))

# (c) validate
c1p = importlib.import_module('evaluation.controllers.c1_port')
sec = json.loads((Path(__file__).resolve().parents[1] / 'declared' / 'c1_port_section.json').read_text(
    encoding='utf-8'))['c1_port']
case('validate_full_section', lambda: (c1p.validate(copy.deepcopy(sec), ouc) is not None, 'ok'))
bad = {
    'unknown_key': ({**sec, 'x': 1}, 'unknown'),
    'name_with_slash': ({**sec, 'omega701': {**sec['omega701'], 'bundle_name': 'a/b.json'}}, 'plain evidence name'),
    'name_dotdot': ({**sec, 'head_service': {**sec['head_service'], 'evidence_name': '..x.json'}}, 'plain evidence name'),
    'sha_upper': ({**sec, 'omega701': {**sec['omega701'], 'bundle_sha256': sec['omega701']['bundle_sha256'].upper()}}, 'lowercase sha256'),
    'audit_alone': ({'meter_neighbor_audit': True}, 'requires allow_zero_green'),
    'audit_false': ({**sec, 'meter_neighbor_audit': False}, 'accepts only true'),
    'held_false': ({**sec, 'held_retention': False}, 'accepts only true'),
    'zero_true': ({**sec, 'allow_zero_green': True}, 'accepts only false'),
    'cap_bool': ({**sec, 'max_leader_candidates': True}, 'positive integer'),
    'cap_zero': ({**sec, 'max_leader_candidates': 0}, 'positive integer'),
    'guard_frac_0': ({**sec, 'storage_release_guard': {'enabled': True, 'trigger_fraction': 0}}, 'trigger_fraction'),
    'guard_frac_gt1': ({**sec, 'storage_release_guard': {'enabled': True, 'trigger_fraction': 1.5}}, 'trigger_fraction'),
    'guard_bool': ({**sec, 'storage_release_guard': {'enabled': True, 'trigger_fraction': True}}, 'trigger_fraction'),
    'guard_disabled': ({**sec, 'storage_release_guard': {'enabled': False, 'trigger_fraction': 0.9}}, 'trigger_fraction'),
    'head_meters_order': ({**sec, 'head_service': {**sec['head_service'], 'meters': list(reversed(sec['head_service']['meters']))}}, 'in that order'),
    'head_rule': ({**sec, 'head_service': {**sec['head_service'], 'full_service_rule': 'keep_lowest'}}, 'keep_green_10'),
    'empty': ({}, 'non-empty'),
}
for label, (s, needle) in bad.items():
    case('validate_refuses_' + label, lambda s=s, needle=needle: raises(lambda: c1p.validate(copy.deepcopy(s), ouc), needle))
no_blocks = copy.deepcopy(ouc)
no_blocks['adapter'].pop('sdmpc_control_blocks', None)
case('validate_refuses_audit_without_3_blocks',
     lambda: raises(lambda: c1p.validate(copy.deepcopy(sec), no_blocks), 'three control blocks'))
no_plant = copy.deepcopy(ouc)
no_plant['freeway'].pop('lane_plant', None)
case('validate_refuses_head_without_lane_plant',
     lambda: raises(lambda: c1p.validate({'head_service': sec['head_service']}, no_plant), 'lane_plant'))
for single in ('omega701', 'max_leader_candidates', 'allow_zero_green', 'storage_release_guard', 'held_retention',
               'head_service'):
    case('validate_single_' + single, lambda single=single: (c1p.validate({single: sec[single]}, ouc) is not None, 'ok'))


# (d) apply_tuning
def apply_cases():
    t0 = copy.deepcopy(ouc)
    same, meta0 = c1p.apply_tuning(t0)
    t1 = {**copy.deepcopy(ouc), 'c1_port': copy.deepcopy(sec)}
    r1, meta1 = c1p.apply_tuning(t1)
    r2, meta2 = c1p.apply_tuning(r1)
    diff = sorted(c1p._leaf_diff(t1, r1))
    bundle = json.loads((ROOT / c1p.C1_DIRS['c1'] / 'omega701_v3c3_bundle.json').read_text(encoding='utf-8'))
    ptrs = sorted(p for e in bundle['entries'] for p in e['tuning_pointers'])
    t3 = {**copy.deepcopy(ouc), 'c1_port': {'max_leader_candidates': 3}}
    r3, meta3 = c1p.apply_tuning(t3)
    info = {'i_same_object': same is t0 and meta0 == {}, 'ii_copy': r1 is not t1, 'ii_changed_eq_11': diff == ptrs,
            'ii_n': len(diff), 'iii_same_object': r2 is r1, 'meta_eq': meta1 == meta2,
            'no_omega_same_object': r3 is t3 and 'omega701' not in meta3,
            'meta_keys': sorted(meta1), 'replaced_n': len(meta1['omega701']['replaced']),
            'head_dropped': meta1['head_service']['dropped']}
    bad_t = copy.deepcopy(t1)
    bad_t['control_area_objective']['membership_path'] = 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'
    ok_bad, msg = raises(lambda: c1p.apply_tuning(bad_t), 'needs the c20aff1d tuning pointers')
    info['mixed_refused'] = ok_bad
    return all(v for k, v in info.items() if k in ('i_same_object', 'ii_copy', 'ii_changed_eq_11', 'iii_same_object',
                                                     'meta_eq', 'no_omega_same_object', 'mixed_refused')), info


case('apply_tuning_cases', apply_cases)


# (e) operating_bounds
class Buf:
    def __init__(self, occ, cap):
        self.head_position_m, self.lanes, self.spacing_m = cap * 7.5, 1, 7.5
        self._occ = occ

    def snapshot(self):
        return {'upstream_travelling_veh': self._occ, 'head_ready_veh': 0.0}


def fake(prev, occ, table_keys, allow_zero=False, guard=True):
    spec = {'ramps': {'R': {'service_by_green_veh_h': {k: float(i) for i, k in enumerate(table_keys)}}},
            'minimum_green_sec': 2.0, 'cycle_sec': 10.0, 'max_green_change_sec': 2}
    if not allow_zero:
        spec['allow_zero_green'] = False
    if guard:
        spec['storage_release_guard'] = {'enabled': True, 'trigger_fraction': 0.9}
    cfg = types.SimpleNamespace(network=types.SimpleNamespace(physical_ramp_branches=spec))
    state = types.SimpleNamespace(lane_ramp_runtime=types.SimpleNamespace(buffers={'R': Buf(occ, 10.0)}))
    ref_ = types.SimpleNamespace(diagnostics={'rw_meter_green_R': float(prev)})
    return state, cfg, ref_


H_KEYS = ['0', '2', '3', '4', '5', '6', '7', '8', '10']
T_KEYS = ['0', '2', '3', '4', '5', '6', '7', '8', '9', '10']


def bounds_cases():
    out = {}
    s, c, r = fake(7, 9.5, H_KEYS)
    res = c1p.operating_bounds(s, c, r)
    out['H_prev7_trig'] = (c.network.ramp_operating_green_floors['R'], res['ramps']['R'].get('table_rounded_from'))
    s, c, r = fake(7, 9.5, T_KEYS)
    res = c1p.operating_bounds(s, c, r)
    out['T_prev7_trig'] = (c.network.ramp_operating_green_floors['R'], res['ramps']['R'].get('table_rounded_from'))
    s, c, r = fake(10, 9.5, H_KEYS)
    c1p.operating_bounds(s, c, r)
    out['H_prev10_trig'] = c.network.ramp_operating_green_floors['R']
    s, c, r = fake(10, 1.0, H_KEYS)
    c1p.operating_bounds(s, c, r)
    out['H_prev10_free'] = c.network.ramp_operating_green_floors['R']
    s, c, r = fake(8, 9.5, T_KEYS)
    c1p.operating_bounds(s, c, r)
    out['T_prev8_trig'] = c.network.ramp_operating_green_floors['R']
    for prev in (2, 4, 6, 8, 10):
        for occ in (1.0, 9.5):
            s, c, r = fake(prev, occ, T_KEYS)
            c1p.operating_bounds(s, c, r)
            out.setdefault('GA4_even', []).append(c.network.ramp_operating_green_floors['R'] in (2.0, 4.0, 6.0, 8.0, 10.0))
    ok = (out['H_prev7_trig'] == (8.0, 9.0) and out['T_prev7_trig'] == (9.0, None) and out['H_prev10_trig'] == 10.0
          and out['H_prev10_free'] == 2.0 and out['T_prev8_trig'] == 10.0 and all(out['GA4_even']))
    return ok, out


case('operating_bounds_floor_and_table_lowering', bounds_cases)


# (f) M3 refusal (new zero green) and the operating_green_allowed rule
def m3():
    spec = {'allow_zero_green': False, 'minimum_green_sec': 2.0}
    return (prb.operating_green_allowed(spec, 0) is False and prb.operating_green_allowed(spec, 2) is True
            and prb.operating_green_allowed({'minimum_green_sec': 2.0}, 0) is True), 'ok'


case('m3_operating_green_allowed', m3)


# (g) neighbor count formula through the ported meter_neighbors (synthetic coordinates, no traffic)
sd = importlib.import_module('evaluation.controllers.sdmpc')


class FakeBox:
    def __init__(self, entries):
        self.entries = entries


class FakeCoord:
    """Three blocks x eight meters, block k allowed = floors-limited table greens within +-2(k+1) of the reference,
    consecutive blocks +-2 (SEQ:101-106 / 147-155 form)."""
    def __init__(self, floors, ref=10.0):
        self.axes = []
        self.ref = ref
        owners = {m: ('FW_E' if m in ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484') else 'FW_W')
                  for m in ('RM_C10480', 'RM_C10482', 'RM_C10484', 'RM_C10490', 'RM_C10639', 'RM_C10644', 'RM_C10646',
                            'RM_C10681')}
        greens = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for k in range(3):
            for m, o in owners.items():
                allowed = [g for g in greens if abs(g - ref) <= 2 * (k + 1) and g >= floors.get(m, 2) and g >= 2]
                self.axes.append(dict(kind='meter', key=m, owner=o, scale=10.0, block=k, allowed=allowed,
                                      reference_value=ref))
        self.move_box = FakeBox([('diagnostics', 'rw_meter_green_' + m, ref, 2, 10.0) for m in owners])

    def encode(self, action):
        return list(action) if not hasattr(action, 'z') else list(action.z)

    def decode(self, z, action):
        return types.SimpleNamespace(z=[float(x) for x in z])

    def validate(self, action):
        return True


class Z(list):
    pass


def count(floors):
    import numpy as np
    coord = FakeCoord(floors)
    start = types.SimpleNamespace(z=[0.0] * len(coord.axes))
    coord.encode = lambda a: np.array(a.z if hasattr(a, 'z') else a, dtype=float)
    out = sd.meter_neighbors(coord, start)
    tight = [l for l, _ in out if l.endswith(':tighten')]
    rel = [l for l, _ in out if l.endswith(':release')]
    plans = {}
    for label, cand in out:
        if label == 'RM_C10639:tighten':
            plans['RM_C10639'] = [round(coord.ref + cand.z[j] * 10.0, 6) for j, a in enumerate(coord.axes)
                                  if a['key'] == 'RM_C10639']
    return len(tight), len(rel), plans


def f(u):
    return u + (1 if u >= 2 else 0)


def formula():
    fwe = ('RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484')
    fww = ('RM_C10480', 'RM_C10482', 'RM_C10646', 'RM_C10644')
    rows = []
    for ue in range(5):
        for uw in range(5):
            floors = {m: (10 if i >= ue else 2) for i, m in enumerate(fwe)}
            floors.update({m: (10 if i >= uw else 2) for i, m in enumerate(fww)})
            nt, nr, plans = count(floors)
            rows.append((ue, uw, nt, f(ue) + f(uw), nr))
    free = count({})
    ok = all(nt == expect and nr == 0 for _, _, nt, expect, nr in rows) and free[0] == 10 and \
        free[2].get('RM_C10639') == [8.0, 6.0, 4.0]
    return ok, {'rows_bad': [r for r in rows if r[2] != r[3] or r[4] != 0], 'free': free[:2], 'plan': free[2]}


case('neighbor_count_formula', formula)
RES['ok'] = all(c['ok'] for c in RES['cases'])
RES['n'] = len(RES['cases'])
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(RES, indent=1, default=repr), encoding='utf-8')
print('C1_SELFTEST ok=%s n=%d bad=%s' % (RES['ok'], RES['n'], [c['name'] for c in RES['cases'] if not c['ok']]))
