"""ReviewDeclare checks for amendment C1 (read-only; light; no VISSIM, no replay, no plant job).

Writes one JSON (argv[1]). Prints only counts / booleans / names, never objective or plan-green numbers.
Reads: GWT8 working tree (clean at c20aff1d) and `git show c20aff1d:`, CX (a49981ff) and FRZ_B1 files,
C1D/declared, V-A decision JSON key names / tokens / T=750 meter greens, V-A action CSV SC1001 SG2 row shape.
"""
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BS = chr(92)
SP = Path(r'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8')
C1D = SP / 'c_port' / 'c1'
GWT8 = Path('D:/VISSIM-merge/sim3-n31-k8')
CX = Path('D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff')
B0F = Path('D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410/diagnostics/b0_v3c3')
VA = {s: Path(f'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s{s}/decisions_sdmpc31_v3c3_k92va_s{s}')
      for s in (31, 41, 43)}
RO = {s: Path(f'D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s{s}/decisions_sdmpc31_v3c3_nc_s{s}')
      for s in (31, 43)}
METERS = ['RM_C10480', 'RM_C10482', 'RM_C10484', 'RM_C10490', 'RM_C10639', 'RM_C10644', 'RM_C10646', 'RM_C10681']
FWE = ['RM_C10639', 'RM_C10681', 'RM_C10490', 'RM_C10484']
OUT = {}


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


def sha_f(p):
    return sha_b(Path(p).read_bytes())


def show(rel):
    r = subprocess.run(['git', '-C', str(GWT8), 'show', 'c20aff1d:' + rel], capture_output=True)
    if r.returncode:
        raise SystemExit('git show failed ' + rel)
    return r.stdout


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def deep_diff(x, y, p=''):
    out = []
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y:
                out.append(p + '/' + k)
            else:
                out += deep_diff(x[k], y[k], p + '/' + k)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            out.append(p)
        else:
            for i, (u, v) in enumerate(zip(x, y)):
                out += deep_diff(u, v, p + '[%d]' % i)
    elif x != y or type(x) is not type(y):
        out.append(p)
    return out


def pins(v, p=''):
    if isinstance(v, dict):
        if isinstance(v.get('path'), str) and 'sha256' in v:
            yield p, v['path'], v['sha256']
        for k, x in v.items():
            yield from pins(x, p + '/' + k)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from pins(x, p + '/%d' % i)


def membership_paths(v, p=''):
    if isinstance(v, dict):
        for k, x in v.items():
            if k == 'membership_path' and isinstance(x, str):
                yield p + '/' + k, x
            yield from membership_paths(x, p + '/' + k)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from membership_paths(x, p + '/%d' % i)


def target_bytes(path):
    path = path.replace(BS, '/')
    if path.startswith('diagnostics/b0_v3c3/'):
        f = B0F / path[len('diagnostics/b0_v3c3/'):]
    else:
        f = GWT8 / path
    return f.read_bytes() if f.is_file() else None


# 0. pins and shas -------------------------------------------------------------------------------------
amend = SP / 'K8_PREDECLARATION_AMENDMENT_C1.md'
OUT['amendment_declare_sha256'] = sha_f(amend)
pin_rows = (C1D / 'declared' / 'PINS_C1_DECLARE.sha256').read_text(encoding='utf-8').splitlines()
ok = 0
for line in pin_rows:
    h, name = line.split(' ', 1)
    name = name.lstrip('*')
    f = Path(name) if re.match(r'^/[a-z]/', name) is None else Path(name[1].upper() + ':' + name[2:])
    f = f if f.is_absolute() else SP / name
    ok += int(f.is_file() and sha_f(f) == h)
OUT['pins_declare'] = {'lines': len(pin_rows), 'ok': ok}

# 1. Omega701 membership --------------------------------------------------------------------------------
new = load(B0F / 'omega701' / 'membership.json')
old = json.loads(show('diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json').decode('utf-8-sig'))
ni, no_ = set(map(str, new['inside_links'])), set(map(str, new['outside_links']))
oi, oo = set(map(str, old['inside_links'])), set(map(str, old['outside_links']))
added = load(C1D / 'declared' / 'omega701_added_links.json')
OUT['omega'] = {'inside': len(ni), 'outside': len(no_), 'old_inside': len(oi), 'added': len(ni - oi),
                'removed': len(oi - ni), 'overlap': len(ni & no_), 'added_equals_declared': set(map(str, added['added_links'])) == ni - oi,
                'roads_by_signal_sum': sum(v if isinstance(v, int) else len(v) for v in added['links_by_signal'].values()),
                'schema': new.get('schema'), 'unresolved': new.get('unresolved'),
                'added_unique_connector_support_in_membership': 'added_unique_connector_support' in json.dumps(new)}

# 2. pack document diffs (K7 deep_diff convention) --------------------------------------------------------
docs = {'native_input_1083_signal_authority_ver2_022a16.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'native_internal_inputs_c92673.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'physical_projection_support_635_proposal_ec2393.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'sc2001_corridor_nc13_2d0c62.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'route_choice_corridor_sc1004_calibrated_9e6354.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'route_choice_corridor_1128_ver2_0fd58c.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'route_choice_corridor_1099_sc15_calibrated_e02d01.json': 'diagnostics/sdmpc_n31_20260924/scenario/',
        'route_choice_corridor_1100_sc15_calibrated_05ed35.json': 'diagnostics/sdmpc_n31_20260924/scenario/'}
diffs = {}
for name, folder in docs.items():
    a = json.loads(show(folder + name).decode('utf-8-sig'))
    b = load(B0F / 'evidence' / name)
    d = deep_diff(a, b)
    groups = {}
    for k in d:
        top = k.split('/')[1]
        groups[top] = groups.get(top, 0) + 1
    diffs[name] = {'n': len(d), 'by_top': groups,
                   'value_paths': sorted(k for k in d if k.count('/') > 2 or k.split('/')[1] in ('membership', 'canonical_contract', 'membership_path'))[:8]}
OUT['pack_diffs'] = diffs
man_old = json.loads(show('diagnostics/sdmpc_n31_20260924/plant_n31_v2.json').decode('utf-8-sig'))
man_new = load(C1D / 'declared' / 'plant_n31_v2_omega701.json')
OUT['manifest_diff'] = deep_diff(man_old, man_new)
sup_old = json.loads(show('diagnostics/sdmpc_n31_20260924/scenario/physical_projection_support_635_proposal_ec2393.json').decode('utf-8-sig'))
sup_new = load(B0F / 'evidence' / 'physical_projection_support_635_proposal_ec2393.json')
aus = set(sup_new['controlled_approach_revision']['added_unique_connector_support'])
OUT['support'] = {'aus_n': len(aus), 'aus_eq_new_link_to_storage': aus == set(sup_new['link_to_storage']) - set(sup_old['link_to_storage']),
                  'aus_eq_new_evidence': aus == set(sup_new['evidence']) - set(sup_old['evidence']),
                  'aus_subset_added_links': aus <= {str(x['link']) for x in new['controlled_intersection_expansion']['added_links']},
                  'area_membership_sha_same': sup_old['full_area_coverage_audit'].get('area_membership_sha256') == sup_new['full_area_coverage_audit'].get('area_membership_sha256'),
                  'area_membership_sha8': sup_new['full_area_coverage_audit'].get('area_membership_sha256', '')[:8]}

# 3. {path, sha256} pins in the 10 B0 files + Omega701 manifest ----------------------------------------------
files = [('omega701/membership.json', B0F / 'omega701' / 'membership.json'), ('omega701/route_contract.json', B0F / 'omega701' / 'route_contract.json')]
files += [('evidence/' + n, B0F / 'evidence' / n) for n in docs] + [('MANIFEST', C1D / 'declared' / 'plant_n31_v2_omega701.json')]
EXCLUDED = {('omega701/membership.json', '/previous_membership')} | {('omega701/membership.json', '/area_revision_sources/%d' % i) for i in range(4)}
rows, bad, excl = 0, [], []
for label, f in files:
    d = load(f)
    for p, path, h in pins(d):
        rows += 1
        tb = target_bytes(path)
        row = {'file': label, 'pointer': p, 'backslash': BS in path, 'exists': tb is not None, 'sha_ok': tb is not None and sha_b(tb) == h,
               'relative': not (path.startswith('/') or ':' in path or '..' in path.replace(BS, '/').split('/'))}
        if (label, p) in EXCLUDED:
            excl.append(row)
        elif not (row['sha_ok'] and row['relative']):
            bad.append(row)
mp = []
for label, f in files:
    for p, path in membership_paths(load(f)):
        mp.append({'file': label, 'pointer': p, 'exists': target_bytes(path) is not None})
OUT['pins_b0'] = {'total': rows, 'excluded': excl, 'judged': rows - len(excl), 'judged_bad': bad,
                  'judged_backslash': sum(1 for label, f in files for p, path, h in pins(load(f)) if (label, p) not in EXCLUDED and BS in path),
                  'membership_path_fields': mp}

# 4. route contract input rows and vehicle inputs on added links ------------------------------------------
rc_old = json.loads(show('diagnostics/control_area_route_contract_physical_routes.json').decode('utf-8-sig'))
rc_new = load(B0F / 'omega701' / 'route_contract.json')
changed = {k: [rc_old[k].get('event_kind'), rc_new[k].get('event_kind'), rc_new[k].get('status')]
           for k in rc_new if k.startswith('input:') and rc_new[k] != rc_old.get(k)}
OUT['route_inputs_changed'] = changed
OUT['route_mixed_new'] = sum(1 for k, v in rc_new.items() if isinstance(v, dict) and v.get('status') == 'mixed_transition')
OUT['route_mixed_old'] = sum(1 for k, v in rc_old.items() if isinstance(v, dict) and v.get('status') == 'mixed_transition')
OUT['route_contract_sha'] = [sha_b(show('diagnostics/control_area_route_contract_physical_routes.json'))[:8], sha_f(B0F / 'omega701' / 'route_contract.json')[:8]]
import xml.etree.ElementTree as ET
tree = ET.fromstring(show('diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx'))
inputs = {x.get('no'): x.get('link') for x in tree.findall('./vehicleInputs/vehicleInput')}
OUT['vehicle_inputs_on_added_links'] = sorted((n for n, l in inputs.items() if l in ni - oi), key=int)

# 5. head-service install table under keep_green_10 and the current tables ----------------------------------
ev = load(C1D / 'declared' / 'head_service_fwe_c1.json')
ouc = json.loads(show('diagnostics/sdmpc_n31_20260924/config_n31_v2.json').decode('utf-8-sig'))
ref = json.loads(show('diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json').decode('utf-8-sig'))
rw = ouc['actuation']['real_world_ramp_metering']
lanes = {m: rw.get('meter_lanes', {}).get(m, 1) for m in METERS}


def keep_lowest(table, minimum=2.0):          # OU PRB:36-81 (None rule)
    groups = {}
    for g, s in table.items():
        groups.setdefault(s, []).append(g)
    keep = {}
    for gs in groups.values():
        if len(gs) < 2:
            continue
        adm = [g for g in gs if int(g) == 0 or int(g) >= minimum]
        k = min(adm, key=int)
        keep.update((g, k) for g in gs if g != k)
    if not keep:
        return table, {}
    top = max(table.values())
    if any(table[g] == top for g in keep):
        raise ValueError('full-service shared')
    return {g: s for g, s in table.items() if g not in keep}, {g: keep[g] for g in table if g in keep}


def keep10(table, minimum=2.0):               # amendment 2.7 rule
    top = max(table.values())
    grp = [g for g, s in table.items() if s == top]
    if '10' not in grp or max(map(int, table)) != 10:
        raise ValueError('rule')
    drop = {g: '10' for g in grp if g != '10'}
    rest = {g: s for g, s in table.items() if g not in drop}
    others = {g: s for g, s in rest.items() if s != top}
    kept, d2 = keep_lowest(others, minimum)
    result = {g: s for g, s in rest.items() if g in kept or s == top}
    drop.update(d2)
    if len(set(result.values())) != len(result):
        raise ValueError('not unique')
    return result, {g: drop[g] for g in table if g in drop}


installed, dropped = {}, {}
for m in FWE:
    curve = ev['values']['curves_veh_per_cycle'][m]
    installed[m], dropped[m] = keep10({'0': 0., **{g: n * 3600 / 10 for g, n in curve.items()}})
current = {}
for m in METERS:
    t = {'0': 0., **{g: lanes[m] * float(n) * 3600 / rw['cycle_sec'] for g, n in rw['per_lane_veh_per_cycle'].items()}}
    if m in ref['freeway'].get('physical_ramp_head_service_veh_per_cycle', {}):
        t, _ = keep_lowest({'0': 0., **{g: n * 3600 / 10 for g, n in ref['freeway']['physical_ramp_head_service_veh_per_cycle'][m].items()}})
    current[m] = t
OUT['head'] = {'installed_repr_equals_evidence': {m: repr(installed[m]) == repr(ev['values']['installed_service_by_green_veh_h'][m]) for m in FWE},
               'dropped': dropped, 'g10_same_as_current': {m: installed[m]['10'] == current[m]['10'] for m in FWE},
               'ouc_head_keys': sorted(ouc['freeway'].get('physical_ramp_head_service_veh_per_cycle', {})),
               'ref_head_keys': sorted(ref['freeway'].get('physical_ramp_head_service_veh_per_cycle', {})),
               'ouc_equals_ref_head': ouc['freeway'].get('physical_ramp_head_service_veh_per_cycle') == ref['freeway'].get('physical_ramp_head_service_veh_per_cycle'),
               'reference_config_sha8': sha_b(show('diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json'))[:8]}

# 6. storage-guard floor realizability (codex floor = max(base, min(10, old+2))) ---------------------------


def floor_gaps(tables, base=2):
    gaps = {}
    for m, t in tables.items():
        greens = sorted(int(g) for g in t)
        for old in greens:
            if old < base:
                continue
            f = max(base, min(10, old + 2))
            allowed = [g for g in greens if abs(g - old) <= 2 and g >= f and (g != 0)]
            if not allowed:
                gaps.setdefault(m, []).append({'old': old, 'floor': f, 'rounded_down': max(g for g in greens if base <= g <= f)})
    return gaps


OUT['floor_gaps_with_H'] = floor_gaps({**current, **installed})
OUT['floor_gaps_without_H'] = floor_gaps(current)

# 7. zero-green seed in the leader lattice when the actual green is 2 ---------------------------------------
OUT['g0_in_lattice_at_actual2'] = {m: ('0' in t and any(int(g) == 0 for g in t if abs(int(g) - 2) <= 2)) for m, t in {**current, **installed}.items()}

# 8. code facts --------------------------------------------------------------------------------------------
ou = {k: show('evaluation/controllers/' + k).decode('utf-8').replace('\r', '') for k in
      ('sdmpc.py', 'physical_ramp_branches.py', 'area_follower_objective.py', 'joint_owner_neighbors.py', 'physical_ramp_boundary.py', 'lane_plant_runtime.py')}
cx = {k: (CX / 'evaluation' / 'controllers' / k).read_text(encoding='utf-8').replace('\r', '') for k in
      ('sdmpc.py', 'physical_ramp_branches.py', 'area_follower_objective.py')}
k92c = show('diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_common.py').decode('utf-8').replace('\r', '')
capc = show('diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_cap_child.py').decode('utf-8').replace('\r', '')
OUT['code'] = {
    'ou_np_only_count': {k: v.count('np_only') for k, v in ou.items() if k in ('sdmpc.py', 'physical_ramp_branches.py', 'area_follower_objective.py')},
    'cx_np_only_count': {k: v.count('np_only') for k, v in cx.items()},
    'ou_sd_uses_domain_only_np_values': ou['sdmpc.py'].count("domain['np_values']") >= 1 and "domain['candidates']" not in ou['sdmpc.py'],
    'ou_lattice_includes_actual_pm2': "abs(green-actual[mid])<=spec['max_green_change_sec']" in ou['joint_owner_neighbors.py'],
    'lane_buffers_only_in_lane_resolved': ou['physical_ramp_boundary.py'].count('self._lane_buffers = []') == 1,
    'k92_stage_open_refuses_other_tokens': "if stage != K92_GATES_STAGE or sha != K92_AMENDMENT24_SHA256:" in k92c,
    'capture_child_stops_at_query': 'until sdmpc.solve builds its' in capc,
    'load_prices_policy_check': "saved['policy_sha256'] != token(policy)" in ou['sdmpc.py'],
    'sd980_line': [l.strip() for l in ou['sdmpc.py'].splitlines()[979:980]],
    'ou_lpr_516': [l.strip()[:90] for l in ou['lane_plant_runtime.py'].splitlines()[515:516]],
}

# 9. V-A / R-obs facts (key names, tokens, T=750 meter greens, SG2 row shape) ----------------------------------
va = {}
for s, d in VA.items():
    j900 = load(d / 'action_000900.json')
    j750 = load(d / 'action_000750.json')
    keys = set()

    def walk(v, p=''):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, p + '/' + k)
        elif isinstance(v, list):
            for x in v:
                walk(x, p + '[*]')
        else:
            keys.add(p)
    walk(j900)
    ts = sorted({re.sub(r'.*transformed_source_sha256/', '', k).replace(BS, '/').split('/evaluation/controllers/')[-1]
                 for k in keys if 'transformed_source_sha256' in k and '/evaluation/controllers/' in k.replace(BS, '/')})
    sg = []
    for T in range(900, 2701, 150):
        with open(d / ('action_%06d.csv' % T), encoding='utf-8-sig', newline='') as h:
            r = [x for x in csv.DictReader(l for l in h if not l.startswith('#'))]
        w = [(float(x['p1_green']), float(x['p2_green'])) for x in r if x.get('kind') == 'signal_sg' and x.get('id', '').startswith('SC1001_SG2_W')]
        sg.append((len(w), any(b < a for a, b in w), any(max(a0, b0) < min(a1, b1) for i, (a0, a1) in enumerate(w) for b0, b1 in w[i + 1:])))
    va[s] = {'token16': j900['metadata']['sdmpc_state']['policy_sha256'][:16],
             'audit_flag': j900['metadata']['joint_leader_selection']['finite_neighbor_audit_performed'],
             't750_greens': sorted({j750['diagnostics']['rw_meter_green_' + m] for m in METERS}),
             't750_has_sdmpc_state': 'sdmpc_state' in j750.get('metadata', {}),
             'transformed_controllers': ts, 'sg2_rows_shape_900_2700': sorted(set(sg))}
OUT['va'] = va
ro = {}
for s, d in RO.items():
    j750 = load(d / 'action_000750.json')
    ro[s] = {'t750_greens': sorted({j750['diagnostics']['rw_meter_green_' + m] for m in METERS}),
             't750_has_sdmpc_state': 'sdmpc_state' in j750.get('metadata', {})}
OUT['robs'] = ro

# 10. line endings of files the commits touch ------------------------------------------------------------------
le = {}
for rel in ('evaluation/controllers/sdmpc.py', 'evaluation/controllers/physical_ramp_branches.py', 'evaluation/controllers/runtime_setup.py',
            'evaluation/controllers/lane_plant_runtime.py', 'evaluation/controllers/vissim_stackelberg_adapter.py',
            'evaluation/controllers/area_follower_objective.py', '.gitattributes'):
    b = (GWT8 / rel).read_bytes()
    attr = subprocess.run(['git', '-C', str(GWT8), 'check-attr', 'text', '--', rel], capture_output=True, text=True).stdout.strip().split(': ')[-1]
    le[rel] = {'cr': b.count(b'\r'), 'lf': b.count(b'\n'), 'text_attr': attr}
OUT['line_endings'] = le

Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
Path(sys.argv[1]).write_text(json.dumps(OUT, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
print('written', sys.argv[1])
