# vc_refs.py -- check file:line references and porting-scope facts of C1_DESIGN_DRAFT / VSL_OFFLINE / READBACK (verify_c V5).
# Read-only: codex trees are read as files, our tree only through `git show c20aff1d:` / `git grep` (no checkout, no write).
import json, sys, subprocess, re, collections

GWT8 = 'D:/VISSIM-merge/sim3-n31-k8'
CX = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff/'
FRZ = 'D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410/'
EC = 'evaluation/controllers/'

def ou(path):
    return subprocess.run(['git', '-C', GWT8, 'show', 'c20aff1d:' + path], capture_output=True).stdout.decode('utf-8', 'replace').splitlines()

def cx(path, root=CX):
    return open(root + path, encoding='utf-8', errors='replace').read().splitlines()

# (label, tree, path, lo, hi, token) ; tree in {'cx','ou','frz'}
REFS = [
 ('CX SD:28-51 retain_feasible_held', 'cx', EC+'sdmpc.py', 28, 51, 'def retain_feasible_held'),
 ('CX SD:126-127 option list has meter_neighbor_audit', 'cx', EC+'sdmpc.py', 126, 127, "'meter_neighbor_audit'"),
 ('CX SD:197-198 three-block check', 'cx', EC+'sdmpc.py', 197, 198, 'Finite meter schedule audit requires three control blocks'),
 ('CX SD:406-414 meter allowed uses floor+operating_green_allowed', 'cx', EC+'sdmpc.py', 406, 414, 'operating_green_allowed(spec,int(g))'),
 ('CX SD:419-421 fixed_vsl skips VSL coords', 'cx', EC+'sdmpc.py', 419, 421, "options.get('fixed_vsl') is not None"),
 ('CX SD:480 VSL tie to reference', 'cx', EC+'sdmpc.py', 478, 482, 'abs(v-self.reference.vsl[key])'),
 ('CX SD:534-544 vsl_activation_axes', 'cx', EC+'sdmpc.py', 534, 544, 'def vsl_activation_axes'),
 ('CX SD:547-553 meter_activation_axes', 'cx', EC+'sdmpc.py', 547, 553, 'def meter_activation_axes'),
 ('CX SD:556-599 meter_neighbors', 'cx', EC+'sdmpc.py', 556, 599, 'def meter_neighbors'),
 ('CX SD:561 Signal/VSL fixed in audit', 'cx', EC+'sdmpc.py', 559, 562, 'Signal/VSL controls and quantity caps stay fixed'),
 ('CX SD:602-658 audit_meter_neighbors', 'cx', EC+'sdmpc.py', 602, 658, 'def audit_meter_neighbors'),
 ('CX SD:622-626 other actuator refusal', 'cx', EC+'sdmpc.py', 622, 626, 'Finite meter candidate changed another actuator'),
 ('CX SD:661-689 audit_meter_budget_candidates', 'cx', EC+'sdmpc.py', 661, 689, 'def audit_meter_budget_candidates'),
 ('CX SD:758-767 policy_token', 'cx', EC+'sdmpc.py', 758, 767, 'def policy_token'),
 ('CX SD:827-828 configure_operating_bounds call', 'cx', EC+'sdmpc.py', 827, 828, 'configure_operating_bounds(state, cfg, reference)'),
 ('CX SD:851-864 operating seed decode', 'cx', EC+'sdmpc.py', 851, 864, 'operating_seed = coord.decode(seed_z,reference)'),
 ('CX SD:898 valid(encode(action))', 'cx', EC+'sdmpc.py', 898, 898, 'coord.valid(coord.encode(action))'),
 ('CX SD:907 PFO from operating_seed', 'cx', EC+'sdmpc.py', 906, 907, 'operating_seed,coord,policy'),
 ('CX SD:919-922 held_old from operating_seed', 'cx', EC+'sdmpc.py', 919, 922, 'held_old = evaluate([operating_seed]'),
 ('CX SD:934 np_only', 'cx', EC+'sdmpc.py', 934, 934, 'np_only=True'),
 ('CX SD:952 np_only', 'cx', EC+'sdmpc.py', 952, 952, 'np_only=True'),
 ('CX SD:953-959 targets slice', 'cx', EC+'sdmpc.py', 953, 959, "targets = ordered[:options['max_leader_candidates']]"),
 ('CX SD:963 meter_budget_candidates=[]', 'cx', EC+'sdmpc.py', 963, 963, 'meter_budget_candidates = []'),
 ('CX SD:1209-1215 next_budget', 'cx', EC+'sdmpc.py', 1209, 1215, 'next_budget'),
 ('CX SD:1216-1220 append budget candidate', 'cx', EC+'sdmpc.py', 1216, 1220, 'meter_budget_candidates.append'),
 ('CX SD:1221-1230 held retention call', 'cx', EC+'sdmpc.py', 1221, 1230, 'retain_feasible_held(operating_seed'),
 ('CX SD:1233-1239 audit call', 'cx', EC+'sdmpc.py', 1233, 1239, 'audit_meter_budget_candidates(coord, best, meter_budget_candidates'),
 ('CX SD:1270 meter_operating_bounds record', 'cx', EC+'sdmpc.py', 1270, 1270, "'meter_operating_bounds': meter_operating_bounds"),
 ('CX SD:1287-1289 audit flag record', 'cx', EC+'sdmpc.py', 1287, 1289, "'finite_neighbor_audit_performed': meter_audit is not None"),
 ('CX SD:1300 original_held_candidate', 'cx', EC+'sdmpc.py', 1300, 1300, 'original_held_candidate=held_candidate'),
 ('CX SD:1126-1127 common line search', 'cx', EC+'sdmpc.py', 1120, 1130, 'line_search'),
 ('CX PRB:49-58 allow_zero + guard check', 'cx', EC+'physical_ramp_branches.py', 49, 58, "settings.get('allow_zero_green', True)"),
 ('CX PRB:55-58 trigger in (0,1]', 'cx', EC+'physical_ramp_branches.py', 55, 58, "0 < guard['trigger_fraction'] <= 1"),
 ('CX PRB:145 spec stores allow_zero', 'cx', EC+'physical_ramp_branches.py', 145, 145, "'allow_zero_green': allow_zero"),
 ('CX PRB:866-868 operating_green_allowed', 'cx', EC+'physical_ramp_branches.py', 866, 868, 'def operating_green_allowed'),
 ('CX PRB:871-908 configure_operating_bounds', 'cx', EC+'physical_ramp_branches.py', 871, 908, 'def configure_operating_bounds'),
 ('CX PRB:897-901 floor formula', 'cx', EC+'physical_ramp_branches.py', 897, 901, "floor = max(base, min(spec['cycle_sec'], old+spec['max_green_change_sec']))"),
 ('CX PRB:947-953 np_only branch', 'cx', EC+'physical_ramp_branches.py', 947, 953, 'if np_only'),
 ('CX LPR:616-620 head curve install', 'cx', EC+'lane_plant_runtime.py', 616, 620, "{'0':0.,**{g:n*3600/10 for g,n in curve.items()}}"),
 ('CX RCC:1929-1975 sc1001_shared_lane_receiving', 'cx', EC+'route_choice_corridor.py', 1929, 1975, 'sc1001_shared_lane_receiving'),
 ('CX PFO:48-49 AD only', 'cx', EC+'sdmpc_pfo.py', 46, 50, ''),
 ('CX PFO:65 line search on owned', 'cx', EC+'sdmpc_pfo.py', 63, 67, ''),
 ('OU SD:338-345 meter allowed g==0 or >=min', 'ou', EC+'sdmpc.py', 338, 345, "(int(g) == 0 or int(g) >= spec['minimum_green_sec'])"),
 ('OU SD:512-513 load_prices', 'ou', EC+'sdmpc.py', 512, 513, 'def load_prices'),
 ('OU SD:517-518 first decision passes', 'ou', EC+'sdmpc.py', 517, 518, "first_sdmpc_decision"),
 ('OU SD:527-528 policy token check', 'ou', EC+'sdmpc.py', 527, 528, "token(policy)"),
 ('OU SD:543 policy from sdmpc_options', 'ou', EC+'sdmpc.py', 543, 543, 'sdmpc_options'),
 ('OU SD:571 reference', 'ou', EC+'sdmpc.py', 571, 571, 'prepare_held_actual_reference'),
 ('OU SD:675 np_values', 'ou', EC+'sdmpc.py', 675, 675, "domain['np_values']"),
 ('OU SD:681 targets slice', 'ou', EC+'sdmpc.py', 681, 681, "targets = ordered[:options['max_leader_candidates']]"),
 ('OU SD:925-930 next_budget', 'ou', EC+'sdmpc.py', 925, 930, 'next_budget'),
 ('OU SD:958 state token(policy)', 'ou', EC+'sdmpc.py', 958, 958, "token(policy)"),
 ('OU SD:980 audit flag False', 'ou', EC+'sdmpc.py', 980, 980, "'finite_neighbor_audit_performed': False"),
 ('OU SD:262-297 S1-OWN', 'ou', EC+'sdmpc.py', 262, 297, 'S1-OWN'),
 ('OU PRB:36-81 normalise_service_table', 'ou', EC+'physical_ramp_branches.py', 36, 81, 'def normalise_service_table'),
 ('OU PRB:38-45 hybrid s31 3000 s', 'ou', EC+'physical_ramp_branches.py', 38, 45, 'hybrid s31 3000 s'),
 ('OU PRB:75-77 full-service ValueError', 'ou', EC+'physical_ramp_branches.py', 75, 77, 'The full-service physical meter green shares its service'),
 ('OU PRB:84-86 measured_head_service_table', 'ou', EC+'physical_ramp_branches.py', 84, 86, 'def measured_head_service_table'),
 ('OU PRB:195-198 spec minimum green', 'ou', EC+'physical_ramp_branches.py', 195, 198, "'minimum_green_sec': settings['min_green_sec']"),
 ('OU LPR:69-89 K6 reference keys', 'ou', EC+'lane_plant_runtime.py', 69, 89, 'REFERENCE_REFUSED_KEYS'),
 ('OU LPR:299 membership read', 'ou', EC+'lane_plant_runtime.py', 299, 299, 'physical_membership_from_ledger'),
 ('OU LPR:512-520 head table install', 'ou', EC+'lane_plant_runtime.py', 512, 520, 'measured_head_service_table'),
 ('OU LPR:534 LaneRampRuntime', 'ou', EC+'lane_plant_runtime.py', 534, 534, 'LaneRampRuntime('),
 ('OU RS:341-350 configure_runtime', 'ou', EC+'runtime_setup.py', 341, 350, 'def configure_runtime'),
 ('OU CAO:90-100 membership keys', 'ou', EC+'control_area_objective.py', 90, 100, 'inside_links'),
 ('OU CAO:125-150 unresolved', 'ou', EC+'control_area_objective.py', 125, 150, 'unresolved model membership'),
 ('OU AR:168-170 read_required', 'ou', EC+'area_runtime.py', 168, 170, "read_required('membership_path')"),
 ('OU ADP:12996-13013 leader options', 'ou', EC+'vissim_stackelberg_adapter.py', 12996, 13013, 'max_leader_candidates'),
 ('OU VBS:1241-1250 hold_previous_on_exception', 'ou', 'scripts/run_real_world_stackelberg_controller.vbs', 1241, 1250, 'hold_previous_on_exception'),
 ('OU VBS:4061 short audits', 'ou', 'scripts/run_real_world_stackelberg_controller.vbs', 4061, 4061, 'short audits'),
 ('FRZ VBS:1026-1038 RampStateAt', 'frz', 'scripts/run_real_world_stackelberg_controller.vbs', 1026, 1038, 'Function RampStateAt'),
 ('FRZ VBS:4123 readback env', 'frz', 'scripts/run_real_world_stackelberg_controller.vbs', 4120, 4126, 'RW_SIGNAL_READBACK_SEC'),
 ('FRZ VBS:1695-1716 green = Round(10*rate/900)', 'frz', 'scripts/run_real_world_stackelberg_controller.vbs', 1695, 1716, 'Round('),
 ('FRZ VBS:980-993 RunContinuous', 'frz', 'scripts/run_real_world_stackelberg_controller.vbs', 980, 993, 'RunContinuous'),
]

def check_refs():
    rows = []
    cache = {}
    for label, tree, path, lo, hi, tok in REFS:
        key = (tree, path)
        if key not in cache:
            cache[key] = ou(path) if tree == 'ou' else cx(path, CX if tree == 'cx' else FRZ)
        L = cache[key]
        seg = L[lo-1:hi]
        hit = bool(tok) and any(tok in x for x in seg)
        where = [i+1 for i, x in enumerate(L) if tok and tok in x][:6]
        rows.append({'ref': label, 'in_range': hit, 'token_lines': where,
                     'text': [x.strip()[:150] for x in seg][:4] if (not tok or not hit) else None})
    return rows

def membership():
    m = json.load(open(FRZ + 'diagnostics/b0_v3c3/omega701/membership.json', encoding='utf-8'))
    o635_path = 'diagnostics/sdmpc_n31_20260924/scenario/control_area_membership_213a5d.json'
    raw = subprocess.run(['git', '-C', GWT8, 'show', 'c20aff1d:' + o635_path], capture_output=True).stdout
    import hashlib
    o635 = json.loads(raw.decode('utf-8-sig'))
    ins701 = {str(x) for x in m['inside_links']}; ins635 = {str(x) for x in o635['inside_links']}
    cie = m['controlled_intersection_expansion']
    added = cie['added_links']
    def lid(a): return str(a['link'] if isinstance(a, dict) else a)
    ids = [lid(a) for a in added]
    conn = [i for i in ids if 10000 <= int(i) <= 10999]
    roads = [i for i in ids if not (10000 <= int(i) <= 10999)]
    per_sc = collections.Counter()
    sc1001 = []
    for a in added:
        rs = a.get('reasons', []) if isinstance(a, dict) else []
        scs = sorted({re.findall(r'(SC\d+)', r)[0] for r in rs if re.findall(r'(SC\d+)', r)})
        if not (10000 <= int(lid(a)) <= 10999):
            for s in scs: per_sc[s] += 1
        if 'SC1001' in scs: sc1001.append({'link': lid(a), 'reasons': rs})
    probe = ['26', '127', '129', '10491', '124', '32', '121', '69', '70', '68', '31', '37', '120', '10480', '10490']
    return {'omega635_sha256': hashlib.sha256(raw).hexdigest(), 'n701': len(ins701), 'n635': len(ins635),
            'n_outside701': len(m['outside_links']), 'counts': m['counts'],
            'diff_701_minus_635': len(ins701 - ins635), 'diff_635_minus_701': len(ins635 - ins701),
            'added_equals_diff': set(ids) == (ins701 - ins635),
            'added_n': len(ids), 'added_roads': len(roads), 'added_connectors': len(conn),
            'per_signal_road_counts': dict(per_sc), 'sc1001_added': sc1001,
            'previous_inside_eq_635': {str(x) for x in cie['previous_inside_links']} == ins635,
            'probe_in701': {p: p in ins701 for p in probe}, 'probe_in635': {p: p in ins635 for p in probe},
            'np_rule': cie.get('np_rule')}

def adapter_diff():
    cb = json.load(open(FRZ + 'diagnostics/b0_v3c3/config_b0_v3c3.json', encoding='utf-8'))
    raw = subprocess.run(['git', '-C', GWT8, 'show', 'c20aff1d:diagnostics/sdmpc_n31_20260924/config_n31_v2.json'], capture_output=True).stdout
    oc = json.loads(raw.decode('utf-8-sig'))
    a, b = cb.get('adapter', {}), oc.get('adapter', {})
    diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return {'adapter_keys_differ': diff,
            'jog_max_leader': (a.get('joint_owner_game', {}).get('max_leader_candidates'), b.get('joint_owner_game', {}).get('max_leader_candidates'))}

def sd_diff_lines():
    a = [x.rstrip('\r') for x in ou(EC + 'sdmpc.py')]
    b = [x.rstrip('\r') for x in open(CX + EC + 'sdmpc.py', encoding='utf-8').read().split('\n')]
    import difflib
    d = list(difflib.unified_diff(a, b, lineterm='', n=0))
    plus = sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))
    minus = sum(1 for x in d if x.startswith('-') and not x.startswith('---'))
    return {'ou_lines': len(a), 'cx_lines': len(b), 'added': plus, 'removed': minus}

def greps():
    out = {}
    for tok in ('direct_exit_legsplit', 'def meter_neighbors', 'def configure_operating_bounds', 'def operating_green_allowed', 'retain_feasible_held', 'control_area_membership_213a5d'):
        r = subprocess.run(['git', '-C', GWT8, 'grep', '-c', tok, 'c20aff1d', '--', 'evaluation', 'diagnostics/sdmpc_n31_20260924/config_n31_v2.json'], capture_output=True)
        out[tok] = r.stdout.decode('utf-8', 'replace').strip().splitlines()[:12]
    return out

if __name__ == '__main__':
    res = {'refs': check_refs(), 'membership': membership(), 'adapter': adapter_diff(), 'sd_diff': sd_diff_lines(), 'greps': greps()}
    json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), indent=1, default=str)
    print('done')
