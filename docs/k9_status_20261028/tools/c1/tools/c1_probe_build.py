"""C1 probe patch (amendment C1 sections 4 / 5.1: M0-M5 + M4a/M4b + np_only at the declared places) and trees.

    python -B c1_probe_build.py patch            -> TOOLS/c1_probe.patch + TOOLS/c1_probe_patch_manifest.json
                                                    (dev repo TC1/work/patchdev: only the changed files of git archive
                                                    c20aff1d, committed, edited, the new files added, git diff)
    python -B c1_probe_build.py tree <kind>      -> TC1/trees/<kind>_<patch sha8> = git archive c20aff1d + the patch
                                                    (git apply), every patched file checked against the manifest
Edits: exact anchors (consecutive lines, one match only); inserted lines take the anchor's line ending.  The codex
functions are copied from CX by ast span (byte text with CR removed)."""
import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c1common as C  # noqa: E402

DEV = C.TC1 / 'work' / 'patchdev'
PATCH = C.TOOLS / 'c1_probe.patch'
MANIFEST = C.TOOLS / 'c1_probe_patch_manifest.json'
SD, PRB, LPR, RS, ADP, AFO = ('evaluation/controllers/' + n for n in (
    'sdmpc.py', 'physical_ramp_branches.py', 'lane_plant_runtime.py', 'runtime_setup.py',
    'vissim_stackelberg_adapter.py', 'area_follower_objective.py'))
CHANGED = (SD, PRB, LPR, RS, ADP, AFO)
NEW = {'evaluation/controllers/c1_port.py': C.TOOLS / 'src' / 'c1_port.py',
       'diagnostics/b0_v3c3/omega701/membership.json': C.B0F / 'omega701' / 'membership.json',
       'diagnostics/b0_v3c3/omega701/route_contract.json': C.B0F / 'omega701' / 'route_contract.json',
       'diagnostics/sdmpc_n31_20260924/c1/evidence/omega701_v3c3_bundle.json': C.DECL / 'omega701_v3c3_bundle.json',
       'diagnostics/sdmpc_n31_20260924/c1/evidence/plant_n31_v2_omega701.json': C.DECL / 'plant_n31_v2_omega701.json',
       'diagnostics/sdmpc_n31_20260924/c1/evidence/head_service_fwe_c1.json': C.DECL / 'head_service_fwe_c1.json'}
for _n in ('native_input_1083_signal_authority_ver2_022a16.json', 'native_internal_inputs_c92673.json',
           'physical_projection_support_635_proposal_ec2393.json', 'sc2001_corridor_nc13_2d0c62.json',
           'route_choice_corridor_sc1004_calibrated_9e6354.json', 'route_choice_corridor_1128_ver2_0fd58c.json',
           'route_choice_corridor_1099_sc15_calibrated_e02d01.json',
           'route_choice_corridor_1100_sc15_calibrated_05ed35.json'):
    NEW['diagnostics/b0_v3c3/evidence/' + _n] = C.B0F / 'evidence' / _n
NEW_SHA = {'diagnostics/b0_v3c3/omega701/membership.json': '9bb740b321d28162c0e849b56e0e618adf4ec800caa60476c96f3fc469318d51',
           'diagnostics/b0_v3c3/omega701/route_contract.json': '08fec9c71b1c612ad3f95555173e372fd2f9428ef58d7010246a00bf0b77063a',
           'diagnostics/b0_v3c3/evidence/native_input_1083_signal_authority_ver2_022a16.json': '8f65b25c7af1e2f4f83e07890bab90b07d0fe0af283180e3d51052757670a3a1',
           'diagnostics/b0_v3c3/evidence/native_internal_inputs_c92673.json': 'a23a13632f20cdb81824a406e0c3a83fa9b88cd3eb7f8d32fb33ce318fd820d8',
           'diagnostics/b0_v3c3/evidence/physical_projection_support_635_proposal_ec2393.json': '7d092b3db6e4107b47ecf751c60196e11a32120dc722d9221c1fb888d447faec',
           'diagnostics/b0_v3c3/evidence/sc2001_corridor_nc13_2d0c62.json': 'cc5e6863ca8f9ade6f47689db0ca83744b2ce1186f0d56a92ca8f55074a00c62',
           'diagnostics/b0_v3c3/evidence/route_choice_corridor_sc1004_calibrated_9e6354.json': '7067a6610b052830885bc56726d944f05fac48daf43dda8ba06fff4750f63716',
           'diagnostics/b0_v3c3/evidence/route_choice_corridor_1128_ver2_0fd58c.json': 'd92f90aacb24f44849826ab0c9ed41dd5574a596d27c6d6637ea709e52b2f4b1',
           'diagnostics/b0_v3c3/evidence/route_choice_corridor_1099_sc15_calibrated_e02d01.json': '8e40f046558d921868bc2f5db435ba131eece073e41052107496f6a541620306',
           'diagnostics/b0_v3c3/evidence/route_choice_corridor_1100_sc15_calibrated_05ed35.json': '59fa5c59d58c97c7170de273484ebfb002b158b9f6a2325b23accc3a260c850e',
           'diagnostics/sdmpc_n31_20260924/c1/evidence/omega701_v3c3_bundle.json': '40f4a84b547bf9a9a2d1fa44980da5e0d5b3d026c80c55edaa5e5aa6d15ee42e',
           'diagnostics/sdmpc_n31_20260924/c1/evidence/plant_n31_v2_omega701.json': '93f171437fbc55420e234a98efb262e83010566902a691a0cc438f17d247a4f7',
           'diagnostics/sdmpc_n31_20260924/c1/evidence/head_service_fwe_c1.json': '3933a882b7948abdae825731ecd06494dead4628d5d26c69d1d8f53dc6866333'}
CX_SD_SHA = '5c1ba251a3526cafa6574459e23627e59cb96e9373ff7d1c5588bcdde3c3a0c0'
CX_PRB_SHA = '0ab140ac0967348b1b475d06668965284ac2170a93a7ee963cbd80b22c4dc966'


def cx_source(rel, digest):
    raw = (C.CX / rel).read_bytes()
    if C.sha256_bytes(raw) != digest:
        raise SystemExit('CX file differs from its pin: ' + rel)
    return raw.decode('utf-8').replace('\r\n', '\n')


def cx_function(text, name):
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return text.split('\n')[node.lineno - 1:node.end_lineno]
    raise SystemExit('CX function not found: ' + name)


def cx_lines(text, first, last):
    return text.split('\n')[first - 1:last]


def edit(raw, anchor, new):
    """raw bytes; anchor / new = lists of str (no EOL).  Exactly one match of the consecutive anchor lines."""
    lines = raw.split(b'\n')
    plain = [ln[:-1] if ln.endswith(b'\r') else ln for ln in lines]
    enc = [a.encode('utf-8') for a in anchor]
    hits = [i for i in range(len(plain) - len(enc) + 1) if plain[i:i + len(enc)] == enc]
    if len(hits) != 1:
        raise SystemExit('anchor matched %d times: %r' % (len(hits), anchor[:2]))
    i = hits[0]
    eol = b'\r' if lines[i].endswith(b'\r') else b''
    repl = [n.encode('utf-8') + eol for n in new]
    return b'\n'.join(lines[:i] + repl + lines[i + len(enc):])


def edits():
    sd = cx_source('evaluation/controllers/sdmpc.py', CX_SD_SHA)
    prb = cx_source('evaluation/controllers/physical_ramp_branches.py', CX_PRB_SHA)
    retain = cx_function(sd, 'retain_feasible_held')
    neighbors = cx_function(sd, 'meter_neighbors')
    audit = cx_function(sd, 'audit_meter_neighbors')
    audit_budget = cx_function(sd, 'audit_meter_budget_candidates')
    allowed = cx_function(prb, 'operating_green_allowed')
    bounds = cx_function(prb, 'configure_operating_bounds')
    np_only_block = cx_lines(prb, 947, 953)
    if not np_only_block[0].strip() == 'if np_only:' or 'joint-leader-np-domain/v1' not in np_only_block[4]:
        raise SystemExit('CX PRB:947-953 is not the np_only block')
    E = {f: [] for f in CHANGED}
    # ---------------------------------------------------------------- SD (amendment C1 sections 2.3, 2.4, 2.6)
    E[SD].append((['def token(value):', '    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()',
                   '', '', 'class GradientCache:'],
                  ['def token(value):', '    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()',
                   '', ''] + retain + ['', '', 'class GradientCache:']))
    E[SD].append((['            options = dict(options, **{name:value})',
                   "    fifo_batch = tuning.get('adapter', {}).get('sdmpc_fifo_batch')"],
                  ['            options = dict(options, **{name:value})',
                   "    c1 = tuning.get('c1_port') or {}",
                   "    if 'meter_neighbor_audit' in c1:",
                   '        options = dict(options, meter_neighbor_audit=True)',
                   "    fifo_batch = tuning.get('adapter', {}).get('sdmpc_fifo_batch')"]))
    E[SD].append((['        options = dict(options, control_blocks=blocks)',
                   "    if options.get('fast_primitives') and (backend != 'reverse-v1' or primal_audit is not True):"],
                  ['        options = dict(options, control_blocks=blocks)',
                   "    if options.get('meter_neighbor_audit') and options.get('control_blocks') != 3:",
                   "        raise ValueError('Finite meter schedule audit requires three control blocks')",
                   "    if options.get('fast_primitives') and (backend != 'reverse-v1' or primal_audit is not True):"]))
    E[SD].append((['            spec = net.physical_ramp_branches',
                   "            a, limit, _ = self.limits['diagnostics', 'rw_meter_green_'+ramp]",
                   "            allowed = [int(g) for g in spec['ramps'][ramp]['service_by_green_veh_h']",
                   "                       if abs(int(g)-a) <= limit and (int(g) == 0 or int(g) >= spec['minimum_green_sec'])]"],
                  ['            spec = net.physical_ramp_branches',
                   "            a, limit, _ = self.limits['diagnostics', 'rw_meter_green_'+ramp]",
                   "            if 'allow_zero_green' in spec or hasattr(net, 'ramp_operating_green_floors'):",
                   '                from evaluation.controllers.physical_ramp_branches import operating_green_allowed',
                   "                floor = getattr(net, 'ramp_operating_green_floors', {}).get(ramp, 0.)",
                   "                allowed = [int(g) for g in spec['ramps'][ramp]['service_by_green_veh_h']",
                   '                           if abs(int(g)-a) <= limit and int(g) >= floor and operating_green_allowed(spec,int(g))]',
                   '                if not allowed:',
                   "                    raise ValueError('No meter command satisfies operating bounds and actual-change limit: '+ramp)",
                   '            else:',
                   "                allowed = [int(g) for g in spec['ramps'][ramp]['service_by_green_veh_h']",
                   "                           if abs(int(g)-a) <= limit and (int(g) == 0 or int(g) >= spec['minimum_green_sec'])]"]))
    E[SD].append((['    return y/scale, max_sweeps, False', '', '', 'def load_prices(previous_path, state, policy):'],
                  ['    return y/scale, max_sweeps, False', '', ''] + neighbors + ['', ''] + audit + ['', '']
                  + audit_budget + ['', '', 'def load_prices(previous_path, state, policy):']))
    E[SD].append((['    reference = meters.prepare_held_actual_reference(historical, cfg)',
                   "    scale = np.array([policy['budget_scale_np_veh'], policy['budget_scale_nuf_veh_h']])"],
                  ['    reference = meters.prepare_held_actual_reference(historical, cfg)',
                   "    if ('allow_zero_green' in cfg.network.physical_ramp_branches",
                   "            or 'storage_release_guard' in cfg.network.physical_ramp_branches):",
                   '        from evaluation.controllers import c1_port',
                   '        meter_operating_bounds = c1_port.operating_bounds(state, cfg, reference)',
                   '    else:',
                   '        meter_operating_bounds = None',
                   "    scale = np.array([policy['budget_scale_np_veh'], policy['budget_scale_nuf_veh_h']])"]))
    E[SD].append((["        coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)",
                   "        surrogate = bool(policy.get('surrogate_reuse'))"],
                  ["        coord = coordinate_type(cfg, reference, callbacks['move_box'], policy)",
                   '        operating_seed = reference',
                   '        if meter_operating_bounds is not None and not coord.valid(coord.encode(reference)):',
                   '            seed_z = coord.encode(reference)',
                   '            for j, axis in enumerate(coord.axes):',
                   "                if axis['kind'] == 'meter':",
                   '                    seed_z[j] = np.clip(seed_z[j],coord.lower[j],coord.upper[j])',
                   '            operating_seed = coord.decode(seed_z,reference)',
                   '            coord.validate(operating_seed)',
                   "        surrogate = bool(policy.get('surrogate_reuse'))"]))
    E[SD].append((['        def feasible(action, item):', "            coverage = item['model_constraint_coverage']",
                   "            return (quantity(action, item)['feasible'] and item['conditional_model_feasibility_witness']"],
                  ['        def feasible(action, item):', "            coverage = item['model_constraint_coverage']",
                   '            if meter_operating_bounds is not None and not bool(coord.valid(coord.encode(action))):',
                   '                return False',
                   "            return (quantity(action, item)['feasible'] and item['conditional_model_feasibility_witness']"]))
    for old, new in (('                reference,coord,policy,options,evaluate,query.derivative,vector,budget.check,emit)',
                      '                operating_seed,coord,policy,options,evaluate,query.derivative,vector,budget.check,emit)'),
                     ('            held_old = evaluate([reference], derivatives=shared_initial)[0]',
                      '            held_old = evaluate([operating_seed], derivatives=shared_initial)[0]'),
                     ('            anchor, initialization = joint.initialize_decision_nuf(follower, state, reference, held_old)',
                      '            anchor, initialization = joint.initialize_decision_nuf(follower, state, operating_seed, held_old)'),
                     ('                query.bind_initial_target(reference, anchor)',
                      '                query.bind_initial_target(operating_seed, anchor)'),
                     ("            == callbacks['command_evidence'](warm_action if cap_mode else reference, context)['owner_physical_sha256'])",
                      "            == callbacks['command_evidence'](warm_action if cap_mode else operating_seed, context)['owner_physical_sha256'])")):
        E[SD].append(([old], [new]))
    for before in ('            # queried and checked below, while this frozen Jacobian is prepared.', '        if domain is None:'):
        lead = '            ' if before.startswith('            #') else '            '
        E[SD].append(([before, lead + 'domain = joint.prepare_joint_leader_candidates(controller, state, forecast, historical,',
                       "                budget_tolerance_veh_h=options['nuf_tolerance_veh_h'], check_budget=budget.check)"],
                      [before, lead + 'domain = joint.prepare_joint_leader_candidates(controller, state, forecast, historical,',
                       "                budget_tolerance_veh_h=options['nuf_tolerance_veh_h'], check_budget=budget.check,",
                       "                np_only=('allow_zero_green' in cfg.network.physical_ramp_branches))"]))
    E[SD].append((['        central_rows, dual_updates = [], []',
                   '        candidate_rows, gradient_rows, local_rows, trials = [], [], [], []'],
                  ['        central_rows, dual_updates = [], []', '        meter_budget_candidates = []',
                   '        candidate_rows, gradient_rows, local_rows, trials = [], [], [], []']))
    E[SD].append((["            if candidate_best and (best is None or candidate_best[1]['objective_veh_h'] < best[1]['objective_veh_h']-policy['objective_tolerance']):",
                   '                best = candidate_best', '        if best is None:',
                   "            raise ValueError('SDMPC found no executable feasible candidate; hold was also infeasible')",
                   '        selected, item, signal = best'],
                  ["            if policy.get('meter_neighbor_audit') and candidate_best:",
                   '                meter_budget_candidates.append(candidate_best)',
                   "            if candidate_best and (best is None or candidate_best[1]['objective_veh_h'] < best[1]['objective_veh_h']-policy['objective_tolerance']):",
                   '                best = candidate_best',
                   '        held_candidate = None',
                   "        if cap_mode and 'held_retention' in (getattr(cfg.network, 'c1_port', None) or {}):",
                   '            # PFO evaluated operating_seed, which may project the actual reference',
                   '            # onto storage-protection bounds. Retain that same action/cost pair.',
                   '            if coord.valid(coord.encode(operating_seed)):',
                   "                best, held_candidate = retain_feasible_held(operating_seed, pfo_initial['objective_veh_h'],",
                   "                    best, best[0] if best is not None else anchor, policy['objective_tolerance'], evaluate, feasible)",
                   '            else:',
                   "                held_candidate = dict(evaluated=False,selected=False,reason='outside_current_operating_bounds')",
                   "            held_candidate['reference_source'] = 'current_operating_seed'",
                   '        if best is None:',
                   "            raise ValueError('SDMPC found no executable feasible candidate; hold was also infeasible')",
                   '        meter_audit = None',
                   "        if policy.get('meter_neighbor_audit'):",
                   '            finish_trial_derivatives()',
                   "            emit('sdmpc_meter_neighbors_start')",
                   '            best, meter_audit = audit_meter_budget_candidates(coord, best, meter_budget_candidates,',
                   "                policy['objective_tolerance'], evaluate, feasible)",
                   "            emit('sdmpc_meter_neighbors_done', **meter_audit)",
                   '        selected, item, signal = best']))
    E[SD].append((["        metadata = {'algorithm': SCHEMA, 'converged': False, 'feasible': True,",
                   "            'selection_status': 'best_observed_feasible_sdmpc', 'candidates': candidate_rows,"],
                  ["        metadata = {'algorithm': SCHEMA, 'converged': False, 'feasible': True,",
                   "            **({'meter_operating_bounds': meter_operating_bounds} if meter_operating_bounds is not None else {}),",
                   "            'selection_status': 'best_observed_feasible_sdmpc', 'candidates': candidate_rows,"]))
    E[SD].append((["            'finite_neighbor_audit_performed': False, 'policy': policy}", '        if central_mode:'],
                  ["            'finite_neighbor_audit_performed': meter_audit is not None, 'policy': policy}",
                   '        if meter_audit is not None:', "            metadata['meter_neighbor_audit'] = meter_audit",
                   '        if central_mode:']))
    E[SD].append((["            metadata.update(algorithm='sdmpc-central-pfo-cap/v3',pfo_warm_start=pfo_receipt,",
                   "                budget_initialization=initialization,budget_constraint_policy='NP <= cap; actual_merge_NUF <= cap',"],
                  ["            metadata.update(algorithm='sdmpc-central-pfo-cap/v3',pfo_warm_start=pfo_receipt,",
                   "                **({'original_held_candidate': held_candidate}",
                   "                   if 'held_retention' in (getattr(cfg.network, 'c1_port', None) or {}) else {}),",
                   "                budget_initialization=initialization,budget_constraint_policy='NP <= cap; actual_merge_NUF <= cap',"]))
    # ---------------------------------------------------------------- PRB (sections 2.4, 2.5, 2.6, 2.7)
    E[PRB].append((['def normalise_service_table(table, minimum_green_sec):'],
                   ['def normalise_service_table(table, minimum_green_sec, full_service_rule=None):']))
    E[PRB].append((['    minimum = float(minimum_green_sec)',
                    '    if not math.isfinite(minimum) or minimum <= 0:',
                    "        raise ValueError('Physical meter service normalisation needs a positive minimum green')",
                    '    groups = {}',
                    '    for green, service in table.items():',
                    '        if type(service) not in (int, float) or not math.isfinite(service) or service < 0:',
                    "            raise ValueError('Invalid physical meter service: %r -> %r' % (green, service))",
                    '        groups.setdefault(service, []).append(green)',
                    '    keep = {}',
                    '    for greens in groups.values():',
                    '        if len(greens) < 2:',
                    '            continue',
                    '        admissible = [g for g in greens if int(g) == 0 or int(g) >= minimum]'],
                   ['    minimum = float(minimum_green_sec)',
                    '    if not math.isfinite(minimum) or minimum <= 0:',
                    "        raise ValueError('Physical meter service normalisation needs a positive minimum green')",
                    "    if full_service_rule not in (None, 'keep_green_10'):",
                    "        raise ValueError('Unknown physical meter full-service rule: %r' % (full_service_rule,))",
                    '    groups = {}',
                    '    for green, service in table.items():',
                    '        if type(service) not in (int, float) or not math.isfinite(service) or service < 0:',
                    "            raise ValueError('Invalid physical meter service: %r -> %r' % (green, service))",
                    '        groups.setdefault(service, []).append(green)',
                    '    if full_service_rule is not None:',
                    '        # C1 keep_green_10: the largest-service group keeps green 10, the largest green of the table;',
                    '        # every other equal-service group keeps its lowest admissible green as before.',
                    '        full = max(table.values())',
                    "        if '10' not in groups[full] or max(int(g) for g in table) != 10:",
                    "            raise ValueError('keep_green_10 requires green 10 as the largest green of the full-service group')",
                    '    keep = {}',
                    '    for greens in groups.values():',
                    '        if len(greens) < 2:',
                    '            continue',
                    '        if full_service_rule is not None and table[greens[0]] == full:',
                    "            keep.update((g, '10') for g in greens if g != '10')",
                    '            continue',
                    '        admissible = [g for g in greens if int(g) == 0 or int(g) >= minimum]']))
    E[PRB].append((['    top = max(table.values())', '    if any(table[g] == top for g in keep):'],
                   ['    top = max(table.values())', '    if full_service_rule is None and any(table[g] == top for g in keep):']))
    E[PRB].append((['def measured_head_service_table(curve, minimum_green_sec):',
                    '    """Installed table of a measured head curve (veh per 10 s cycle): lane_plant_runtime\'s install path."""',
                    "    return normalise_service_table({'0': 0., **{g: n*3600/10 for g, n in curve.items()}}, minimum_green_sec)"],
                   ['def measured_head_service_table(curve, minimum_green_sec, full_service_rule=None):',
                    '    """Installed table of a measured head curve (veh per 10 s cycle): lane_plant_runtime\'s install path."""',
                    "    return normalise_service_table({'0': 0., **{g: n*3600/10 for g, n in curve.items()}}, minimum_green_sec,",
                    '                                   full_service_rule=full_service_rule)']))
    E[PRB].append((["        raise ValueError('Invalid physical service table or declared green change limit')", '    rows = {}'],
                   ["        raise ValueError('Invalid physical service table or declared green change limit')",
                    "    c1 = tuning.get('c1_port') or {}",
                    "    if 'allow_zero_green' in c1 or 'storage_release_guard' in c1:",
                    '        from evaluation.controllers import c1_port',
                    "        for c1_key in ('allow_zero_green', 'storage_release_guard'):",
                    '            if c1_key in c1:',
                    '                c1_port.check_value(c1_key, c1[c1_key])',
                    '    rows = {}']))
    E[PRB].append((["        'unresolved': copy.deepcopy(spec.get('unresolved', []))}", '    if city is not None:',
                    "        net.physical_ramp_branches['shared_city_arrival']=city"],
                   ["        'unresolved': copy.deepcopy(spec.get('unresolved', []))}",
                    "    if 'allow_zero_green' in c1:",
                    "        net.physical_ramp_branches['allow_zero_green'] = False",
                    "    if 'storage_release_guard' in c1:",
                    "        net.physical_ramp_branches['storage_release_guard'] = copy.deepcopy(c1['storage_release_guard'])",
                    '    if city is not None:', "        net.physical_ramp_branches['shared_city_arrival']=city"]))
    E[PRB].append((["            raise ValueError('Unrealizable physical meter green: '+mid)",
                    '        candidate.diagnostics[key] = float(value)'],
                   ["            raise ValueError('Unrealizable physical meter green: '+mid)",
                    "        if 'allow_zero_green' in spec and not operating_green_allowed(spec, value):",
                    "            raise ValueError('Physical meter green is below the operating minimum: '+mid)",
                    '        candidate.diagnostics[key] = float(value)']))
    E[PRB].append((['    return prepare_control(candidate, cfg)', '', '',
                    'def candidate_from_services(incumbent, actual_reference, cfg, services):'],
                   ['    return prepare_control(candidate, cfg)', '', ''] + allowed + ['', ''] + bounds
                   + ['', '', 'def candidate_from_services(incumbent, actual_reference, cfg, services):']))
    E[PRB].append((['def leader_seed_domain(controller, state, forecast, historical, *, check_budget=None):'],
                   ['def leader_seed_domain(controller, state, forecast, historical, *, check_budget=None, np_only=False):']))
    E[PRB].append((["        raise ValueError('Physical leader requires finite installed NP proposals')", '    groups = []'],
                   ["        raise ValueError('Physical leader requires finite installed NP proposals')"] + np_only_block
                   + ['    groups = []']))
    # ---------------------------------------------------------------- AFO (section 2.4, RV-1)
    E[AFO].append((['def prepare_joint_leader_candidates(controller, state, forecast, previous, *,',
                    '                                    budget_tolerance_veh_h, check_budget=None):'],
                   ['def prepare_joint_leader_candidates(controller, state, forecast, previous, *,',
                    '                                    budget_tolerance_veh_h, check_budget=None, np_only=False):']))
    E[AFO].append((['        return physical_ramp_branches.leader_seed_domain(controller, state, forecast, previous,',
                    '            check_budget=check_budget)'],
                   ['        return physical_ramp_branches.leader_seed_domain(controller, state, forecast, previous,',
                    '            check_budget=check_budget, np_only=np_only)']))
    # ---------------------------------------------------------------- LPR (section 2.7)
    E[LPR].append((["            row['service_by_green_veh_h'],dropped=physical_ramp_branches.measured_head_service_table(",
                    "                curve,net.physical_ramp_branches['minimum_green_sec'])"],
                   ["            if name in context.get('c1_head_service',{}).get('meters',()):",
                    "                row['service_by_green_veh_h'],dropped=physical_ramp_branches.measured_head_service_table(",
                    "                    curve,net.physical_ramp_branches['minimum_green_sec'],full_service_rule='keep_green_10')",
                    '            else:',
                    "                row['service_by_green_veh_h'],dropped=physical_ramp_branches.measured_head_service_table(",
                    "                    curve,net.physical_ramp_branches['minimum_green_sec'])"]))
    # ---------------------------------------------------------------- RS (sections 2.2, 2.7, 2.8)
    E[RS].append((['    """', "    timetable = (tuning or {}).get('prediction', {}).get('native_input_schedule', False)"],
                  ['    """', '    from evaluation.controllers import c1_port',
                   '    tuning, c1_meta = c1_port.apply_tuning(tuning, state_json=state_json)',
                   "    if isinstance(tuning, dict) and 'c1_port' in tuning:",
                   '        import copy as c1_copy',
                   "        cfg.network.c1_port = c1_copy.deepcopy(tuning['c1_port'])",
                   "    timetable = (tuning or {}).get('prediction', {}).get('native_input_schedule', False)"]))
    E[RS].append((["        lane_context['initial_spillback_projection']=spillback_projection",
                   "        if lane_context.get('plant_mode')=='v2':"],
                  ["        lane_context['initial_spillback_projection']=spillback_projection",
                   '        c1_port.install_head_service(lane_context, tuning)',
                   "        if lane_context.get('plant_mode')=='v2':"]))
    E[RS].append((['        lane_plant_runtime.bind_area(state,cfg)', '    return state, detector_mapping, metadata'],
                  ['        lane_plant_runtime.bind_area(state,cfg)', '    if c1_meta:',
                   "        metadata['c1_port'] = c1_meta", '    return state, detector_mapping, metadata']))
    # ---------------------------------------------------------------- ADP (sections 2.2, 2.4)
    E[ADP].append((['    tuning = load_optional_json(args.tuning_json)', '    bind_joint_cli_module(tuning)'],
                   ['    tuning = load_optional_json(args.tuning_json)',
                    '    from evaluation.controllers import c1_port',
                    '    tuning, _ = c1_port.apply_tuning(tuning)',
                    '    bind_joint_cli_module(tuning)']))
    E[ADP].append((["        raise ValueError('Decision budget must leave observation/application time inside the control interval')",
                    '    return result'],
                   ["        raise ValueError('Decision budget must leave observation/application time inside the control interval')",
                    "    c1 = (tuning or {}).get('c1_port') or {}",
                    "    if 'max_leader_candidates' in c1:",
                    "        result['max_leader_candidates'] = c1['max_leader_candidates']",
                    '    return result']))
    return E


def archive_members(paths=None):
    """git archive c20aff1d (working-tree conversion, = GWT8 work files) -> {name: bytes} for `paths` or all."""
    cmd = ['git', '-C', str(C.GWT8), 'archive', '--format=tar', C.REV] + (list(paths) if paths else [])
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    out = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r') as tf:
        for m in tf:
            if m.isfile():
                out[m.name] = tf.extractfile(m).read()
    return out


def git(*args, cwd):
    r = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', *args], cwd=str(cwd),
                       capture_output=True)
    if r.returncode:
        raise SystemExit('git %s failed: %s' % (' '.join(args), r.stderr.decode('utf-8', 'replace')[-800:]))
    return r.stdout


def cmd_patch():
    if DEV.exists() or PATCH.exists() or MANIFEST.exists():
        raise SystemExit('patchdev / patch / manifest already exist (never overwritten)')
    base = archive_members(CHANGED)
    if set(base) != set(CHANGED):
        raise SystemExit('archive lacks a changed file')
    DEV.mkdir(parents=True)
    for rel, b in base.items():
        p = DEV / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
    git('init', '-q', cwd=DEV)
    (DEV / '.git' / 'info' / 'attributes').write_text('* -text\n', encoding='utf-8')
    git('add', '--', *CHANGED, cwd=DEV)
    git('-c', 'user.name=c1probe', '-c', 'user.email=c1probe@localhost', 'commit', '-q', '-m', 'base c20aff1d', cwd=DEV)
    rec = {'schema': 'c1-probe-patch/v1', 'rev': C.REV, 'pre': {}, 'post': {}, 'edits': {}}
    for rel, items in edits().items():
        raw = base[rel]
        rec['pre'][rel] = C.sha256_bytes(raw)
        for anchor, new in items:
            raw = edit(raw, anchor, new)
        (DEV / rel).write_bytes(raw)
        rec['post'][rel] = C.sha256_bytes(raw)
        rec['edits'][rel] = len(items)
        compile(raw.decode('utf-8'), rel, 'exec')
    for rel, src in NEW.items():
        b = Path(src).read_bytes()
        if rel in NEW_SHA and C.sha256_bytes(b) != NEW_SHA[rel]:
            raise SystemExit('new file differs from its declared sha: ' + rel)
        p = DEV / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        rec['post'][rel] = C.sha256_bytes(b)
        if rel.endswith('.py'):
            compile(b.decode('utf-8'), rel, 'exec')
    git('add', '--', *CHANGED, *NEW, cwd=DEV)
    diff = git('diff', '--cached', '--binary', '--full-index', cwd=DEV)
    PATCH.write_bytes(diff)
    rec['patch_sha256'] = C.sha256_file(PATCH)
    rec['patch_bytes'] = PATCH.stat().st_size
    rec['new_files'] = sorted(NEW)
    rec['changed_files'] = sorted(CHANGED)
    MANIFEST.write_text(json.dumps(rec, indent=1, sort_keys=True), encoding='utf-8')
    print('C1_PATCH ok sha256=%s bytes=%d changed=%d new=%d' % (rec['patch_sha256'], rec['patch_bytes'],
                                                               len(CHANGED), len(NEW)))


def cmd_tree(kind):
    man = json.loads(MANIFEST.read_text(encoding='utf-8'))
    psha = C.sha256_file(PATCH)
    if psha != man['patch_sha256']:
        raise SystemExit('patch bytes differ from its manifest')
    if not kind.replace('_', '').isalnum() or kind != kind.lower():
        raise SystemExit('tree kind must be lowercase [a-z0-9_]')
    name = '%s_%s' % (kind, psha[:8])
    dest = C.TC1 / 'trees' / name
    if dest.exists():
        raise SystemExit('tree exists: %s' % dest)
    C.require_space()
    members = set()
    proc = subprocess.Popen(['git', '-C', str(C.GWT8), 'archive', '--format=tar', C.REV], stdout=subprocess.PIPE)
    with tarfile.open(fileobj=proc.stdout, mode='r|') as tf:
        for m in tf:
            if not m.isfile():
                continue
            p = C.lp(dest / m.name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, 'wb') as f:
                shutil.copyfileobj(tf.extractfile(m), f)
            members.add(m.name)
    if proc.wait() != 0:
        raise SystemExit('git archive failed')
    git('apply', '--binary', '--whitespace=nowarn', str(PATCH), cwd=dest)
    bad = {}
    for rel, digest in man['post'].items():
        got = C.sha256_file(dest / rel)
        if got != digest:
            bad[rel] = got
    for rel in members:
        if rel not in man['post'] and rel in man['pre']:
            bad[rel] = 'unexpected'
    count = sum(len(fs) for _, _, fs in os.walk(C.lp(dest)))
    rec = {'tree': name, 'rev': C.REV, 'patch_sha256': psha, 'archive_files': len(members), 'files_after': count,
           'expected_files_after': len(members) + len(man['new_files']), 'post_check_bad': bad,
           'ok': not bad and count == len(members) + len(man['new_files'])}
    C.write_json(C.TC1 / 'trees' / (name + '.build.json'), rec)
    print('C1_TREE %s ok=%s files=%d bad=%d' % (name, rec['ok'], count, len(bad)))
    if not rec['ok']:
        raise SystemExit(3)


if __name__ == '__main__':
    if sys.argv[1:2] == ['patch']:
        cmd_patch()
    elif sys.argv[1:2] == ['tree'] and len(sys.argv) == 3:
        cmd_tree(sys.argv[2])
    else:
        raise SystemExit(__doc__)
