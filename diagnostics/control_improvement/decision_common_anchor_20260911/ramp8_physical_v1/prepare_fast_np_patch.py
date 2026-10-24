"""Prepare surgical edits without changing a running decision's pinned sources."""
import hashlib
import json
from pathlib import Path
import textwrap

D = Path(__file__).resolve().parent
ROOT = D.parents[3]


def manifest(name, path, edits):
    source = ROOT / path
    before = source.read_text(encoding='utf-8')
    after = before
    for old, new in edits:
        if after.count(old) != 1:
            raise ValueError((path, after.count(old), old[:120]))
        after = after.replace(old, new)
    compile(after, str(source), 'exec')
    result = {'schema': 'pending-source-edit/v2', 'applied': False, 'path': path,
        'source_file_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'old_text_sha256': hashlib.sha256(before.encode()).hexdigest(),
        'new_text_sha256': hashlib.sha256(after.encode()).hexdigest(),
        'replacements': [{'before': a, 'after': b} for a, b in edits],
        'scope': 'Opt-in fast NP initializer and bounded per-candidate restoration. No physical model, target, trust-region, price, or follower neighborhood change.'}
    (D / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


HELPERS = '''
def _np_kind_totals(quantities, signals):
    """Exactly the canonical 17-owner accepted-service coordinate, never Omega."""
    kinds = ('boundary_in', 'off_ramp', 'boundary_out', 'on_ramp', 'internal')
    if (quantities.get('schema') != 'shared-urban-kind-service/v1'
            or len(signals) != 17 or set(quantities.get('owners', {})) != set(signals)):
        raise ValueError('Fast NP initialization needs all canonical 17 urban owners')
    totals = dict.fromkeys(kinds, 0.)
    for owner in signals:
        row = quantities['owners'][owner]
        by_kind = row['by_kind_veh']
        if set(by_kind) != set(kinds) or any(type(v) not in (int, float)
                or not math.isfinite(v) or v < 0 for v in by_kind.values()):
            raise ValueError('Invalid accepted movement service in NP basis')
        nin = by_kind['boundary_in'] + by_kind['off_ramp'] - by_kind['boundary_out'] - by_kind['on_ramp']
        if not math.isclose(nin, row['net_inflow_veh'], rel_tol=0., abs_tol=1e-8):
            raise ValueError('NP kind-signed service differs from canonical owner total')
        for kind in kinds:
            totals[kind] += by_kind[kind]
    return totals


def _linear_green_extreme(net, owner, coefficients, move_box, reference):
    """Tiny linear heuristic on the exact millisecond phase/actual-command box."""
    from evaluation.controllers import signal_actuation_contract as signals
    live = tuple(net.signal_live_phases(owner))
    physical = signals.phase_bounds(net, owner)
    limits = {key: (ref, limit) for field, key, ref, limit, cycle in move_box.entries
              if field == 'green_times'}
    box = {}
    for p in live:
        ref, limit = limits[owner + '_' + p]
        lo, hi = physical[p]
        box[p] = (math.ceil(1000 * max(lo, ref-limit) - 1e-8),
                  math.floor(1000 * min(hi, ref+limit) + 1e-8))
        if box[p][0] > box[p][1]:
            raise ValueError('Empty actual-command phase intersection')
    total = round(1000 * net.signal_effective_green_total(owner))
    if abs(total / 1000 - net.signal_effective_green_total(owner)) > 1e-9:
        raise ValueError('Green total is not on writer millisecond grid')
    basis = signals.native_clock_basis(net, owner)
    # No measured green direction: retain the actual command instead of
    # arbitrarily filling a phase at a flat objective's extreme.
    concurrent = basis is not None and basis['kind'] == 'concurrent_p1_p2'
    flat = (all(v == 0. for v in coefficients.values()) if concurrent else
            max(coefficients.values()) == min(coefficients.values()))
    if flat:
        return {p: float(reference.green_times[owner+'_'+p]) for p in signals.PHASES}
    if basis is not None and basis['kind'] == 'concurrent_p1_p2':
        if set(live) != {'p1', 'p2', 'p4'}:
            raise ValueError('Unsupported concurrent phase basis')
        amber = round(1000 * basis['amber_sec'])
        if abs(amber / 1000 - basis['amber_sec']) > 1e-9:
            raise ValueError('Concurrent amber is not on writer grid')
        lo = max(box['p2'][0], total-box['p4'][1], box['p1'][0]+amber)
        hi = min(box['p2'][1], total-box['p4'][0])
        if lo > hi:
            raise ValueError('Empty concurrent phase intersection')
        points = {lo, hi, min(hi, max(lo, box['p1'][1]+amber))}
        def vector(y):
            x = box['p1'][0] if coefficients['p1'] >= 0 else min(box['p1'][1], y-amber)
            return {'p1': x, 'p2': y, 'p4': total-y}
        candidates = [vector(y) for y in sorted(points)]
        chosen = min(candidates, key=lambda v: (math.fsum(coefficients[p]*v[p] for p in live),
            math.fsum((v[p]/1000-reference.green_times[owner+'_'+p])**2 for p in live)))
    else:
        chosen = {p: box[p][0] for p in live}
        residual = total - sum(chosen.values())
        if not 0 <= residual <= sum(hi-lo for lo, hi in box.values()):
            raise ValueError('Phase box cannot preserve the current cycle')
        for p in sorted(live, key=lambda p: (coefficients[p], live.index(p))):
            addition = min(residual, box[p][1]-chosen[p])
            chosen[p] += addition
            residual -= addition
    result = {p: chosen.get(p, 0)/1000 for p in signals.PHASES}
    signals.validate_vector(net, owner, result)
    return result


def prepare_fast_np_seeds(follower, reference, measured, move_box):
    """Reuse existing full-horizon price responses for a signed-flow initializer.

    These secants already include destination queues, predicted arrivals, travel
    time, receiving/lane/shared-stock constraints, spillback and signal clocks
    implemented by the canonical model. Extrapolation is only a heuristic.
    No physical response or new search is performed here.
    """
    import copy
    import numpy as np
    from time import perf_counter
    from evaluation.controllers import signal_actuation_contract as signals
    net = follower.cfg.network
    started = perf_counter()
    if move_box is None:
        raise ValueError('Fast NP seeds require a fixed actual-command trust region')
    responses = measured['responses']['results']
    base = _np_kind_totals(responses[0]['quantities'], net.signals)
    kinds = tuple(base)
    green_only, with_offset = copy.deepcopy(reference), copy.deepcopy(reference)
    evidence = {}
    for owner in net.signals:
        live = tuple(net.signal_live_phases(owner))
        keys = tuple(owner+'_'+p for p in live) + (owner,)
        selection = measured['probe_selection'][owner]
        edges = measured['secants'][owner]
        indices = selection['action_indices']
        if len(edges) != len(indices) or len(edges) != len(live):
            raise ValueError('Incomplete urban NP tangent basis')
        x = np.asarray([[edge['coordinate']['direction'][key] for key in keys] for edge in edges])
        y = np.asarray([[(_np_kind_totals(responses[i]['quantities'], net.signals)[k]-base[k])
                         for k in kinds] for i in indices])
        coefficients, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
        if rank != len(live) or not np.isfinite(coefficients).all():
            raise ValueError('Unidentified urban NP tangent direction')
        signed = coefficients @ np.asarray([1., 1., -1., -1., 0.])
        greens = _linear_green_extreme(net, owner, dict(zip(live, signed[:-1])), move_box, reference)
        for p, value in greens.items():
            green_only.green_times[owner+'_'+p] = with_offset.green_times[owner+'_'+p] = value
        cycle = float(net.signal_cycle_length(owner))
        entry = next(e for e in move_box.entries if e[:2] == ('offsets', owner))
        ref, limit = entry[2:4]
        delta = lambda value: ((value-ref+cycle/2) % cycle)-cycle/2
        offsets = {float(reference.offsets[owner])}
        offsets.update(round((float(f)*cycle) % cycle, 3) % cycle for f in follower.offset_fractions)
        offsets = {v for v in offsets if abs(delta(v)) <= limit+1e-9}
        with_offset.offsets[owner] = min(offsets, key=lambda v: (float(signed[-1])*delta(v), abs(delta(v)), v))
        evidence[owner] = {'coordinates': keys, 'kind_service_secants_veh_per_sec': coefficients.tolist(),
            'signed_np_secants_veh_per_sec': signed.tolist(), 'phase_green_sec': greens,
            'offset_sec': with_offset.offsets[owner], 'response_indices': indices}
    move_box.validate(green_only)
    move_box.validate(with_offset)
    return {'seeds': (green_only, with_offset), 'evidence': {
        'schema': 'fast-np-initialization/v1', 'anchor_token': move_box.anchor_token,
        'base_kind_service_veh': base, 'owners': evidence,
        'forecast_window': {k: responses[0]['quantities']['provenance'][k] for k in ('start_sec', 'end_sec')},
        'frozen_context_token': responses[0]['frozen_context_token'],
        'response_tokens': [r['response_token'] for r in responses], 'new_endpoint_calls': 0,
        'initializer_generation_wall_sec': perf_counter()-started,
        'possibility': 'unknown', 'global_np_lower_bound_veh': None,
        'domain_infeasible': False, 'full_control_domain_bound_certified': False,
        'bound_limit': 'Local observed secants do not bound all green/offset/VSL/meter combinations. No target may be excluded by these values.',
        'scope': '17-owner boundary_in + off_ramp - boundary_out - on_ramp accepted service. Full model and writer must validate each retargeted seed; no queue-only 450s service cap.'}}


'''


def main():
    runtime_edits = [("    cfg.network.control_area_beta_seconds = beta\n", '''    import math
    fast_np = section.get('fast_np_initialization')
    if fast_np is not None:
        required = {'candidate_time_budget_sec', 'restoration_time_budget_sec', 'restoration_max_evaluations'}
        if not isinstance(fast_np, dict) or set(fast_np) != required:
            raise ValueError('Explicit fast NP candidate/restoration budgets required')
        for key in ('candidate_time_budget_sec', 'restoration_time_budget_sec'):
            if type(fast_np[key]) not in (int, float) or not math.isfinite(fast_np[key]) or fast_np[key] <= 0:
                raise ValueError('Positive finite fast NP time budgets required')
        if (type(fast_np['restoration_max_evaluations']) is not int or fast_np['restoration_max_evaluations'] < 3
                or fast_np['restoration_time_budget_sec'] > fast_np['candidate_time_budget_sec']):
            raise ValueError('Restoration must fit candidate time and allow the incumbent plus two seeds')
        if full_prefetch:
            raise ValueError('Bounded fast NP candidates cannot use unlimited full-sweep prefetch')
        cfg.network.control_area_fast_np_initialization = dict(fast_np)
    elif hasattr(cfg.network, 'control_area_fast_np_initialization'):
        del cfg.network.control_area_fast_np_initialization
    cfg.network.control_area_beta_seconds = beta
''')]
    manifest('fast_np_runtime_pending_v2', 'evaluation/controllers/area_runtime.py', runtime_edits)
    game_edits = [
        ("                        nuf_semantics='fixed_target', deadline_check=None):\n", "                        nuf_semantics='fixed_target', deadline_check=None, initial_seeds=()):\n"),
        ("        current_eval = checked(current)\n        if current_eval.feasible:\n", '''        current_eval = checked(current)
        if type(initial_seeds) is not tuple:
            raise ValueError('Explicit finite initializer tuple required')
        for seed in initial_seeds if not current_eval.feasible else ():
            if _extra(seed, nuf_semantics=nuf_semantics) != _extra(incumbent, nuf_semantics=nuf_semantics):
                raise ValueError('Initializer changed fixed targets or nonlever payload')
            value = checked(seed)
            if value.feasible or value.violation < current_eval.violation - improvement_tolerance:
                current, current_eval = deepcopy(seed), value
            if current_eval.feasible:
                break
        if current_eval.feasible:
''')]
    manifest('fast_np_restoration_pending_v2', 'evaluation/controllers/joint_owner_game.py', game_edits)
    edits = [
        ('def prepare_common_joint_prices(', HELPERS + 'def prepare_common_joint_prices('),
        ("    return {'measured': measured, 'installed': installed, 'follower': follower,\n", '''    fast_np = None
    if getattr(follower.cfg.network, 'control_area_fast_np_initialization', None) is not None:
        fast_np = prepare_fast_np_seeds(follower, reference, measured, callbacks['move_box'])
    return {**({'fast_np': fast_np} if fast_np is not None else {}),
            'measured': measured, 'installed': installed, 'follower': follower,
'''),
        ("    target_np, target_nuf = proposal['target_np_veh'], proposal['target_nuf_veh_h']\n", '''    from time import perf_counter
    candidate_started = perf_counter()
    fast_policy = getattr(cfg.network, 'control_area_fast_np_initialization', None)
    target_np, target_nuf = proposal['target_np_veh'], proposal['target_nuf_veh_h']
'''),
        ("        result = solve_fixed_shared_game(follower, state, common['reference'], forecast, initial,\n", '''        fast_seeds = ()
        if fast_policy is not None:
            if common.get('fast_np') is None:
                raise ValueError('Fast NP candidate lacks common response-derived seeds')
            prepared_seeds = []
            for prototype in common['fast_np']['seeds']:
                seed = copy.deepcopy(initial)
                seed.green_times, seed.offsets = copy.deepcopy((prototype.green_times, prototype.offsets))
                prepared_seeds.append(seed)
            fast_seeds = tuple(prepared_seeds)
            cap = max(0., fast_policy['candidate_time_budget_sec'] - (perf_counter()-candidate_started))
            work_options['time_budget_sec'] = min(cap, work_options['time_budget_sec']) if work_options['time_budget_sec'] is not None else cap
        result = solve_fixed_shared_game(follower, state, common['reference'], forecast, initial,
'''),
        ("            restore_initializer=True,\n", "            restore_initializer=True, initial_seeds=fast_seeds, restoration_policy=fast_policy,\n"),
        ("        status, validated, initializer_evidence = _runtime_joint_candidate_validation(result,\n", '''        if fast_policy is not None:
            result['fast_np'] = copy.deepcopy(common['fast_np']['evidence'])
            result['fast_np']['candidate_time_budget_sec'] = fast_policy['candidate_time_budget_sec']
            result['fast_np']['candidate_elapsed_sec'] = perf_counter()-candidate_started
            result['fast_np']['candidate_time_overrun_sec'] = max(0., perf_counter()-candidate_started-fast_policy['candidate_time_budget_sec'])
            result['fast_np']['seed_checks'] = copy.deepcopy(result['initializer_seed_checks'])
            observed = [r['np_veh'] for r in result['initializer_seed_checks']
                        if r.get('model_and_writer_validated') and r['nuf_satisfied']]
            result['fast_np']['observed_np_range_veh'] = [min(observed), max(observed)] if observed else None
            result['fast_np']['observed_range_scope'] = 'Only evaluated seeds satisfying the fixed NUF band and model/writer constraints; no whole-domain limit.'
            result['fast_np']['skip_rule'] = 'Unrestored cap/NUF within short budget remains unknown; advance to the next leader candidate. Model/command contract failure aborts.'
        status, validated, initializer_evidence = _runtime_joint_candidate_validation(result,
'''),
        ("            status = solved['candidate_status']\n", "            if 'fast_np' in solved['response']:\n                row['fast_np'] = copy.deepcopy(solved['response']['fast_np'])\n            status = solved['candidate_status']\n"),
        ("                            progress=None):\n    \"\"\"Select a realized joint action", "                            progress=None, initial_seeds=(), restoration_policy=None):\n    \"\"\"Select a realized joint action"),
        ("        restoration = game.restore_feasibility(callbacks['ownership'], incumbent, context,\n", '''        restore_evaluations, restore_time = max_evaluations, time_budget_sec
        if restoration_policy is not None:
            restore_evaluations = min(max_evaluations, restoration_policy['restoration_max_evaluations'])
            restore_time = min(time_budget_sec, restoration_policy['restoration_time_budget_sec']) if time_budget_sec is not None else restoration_policy['restoration_time_budget_sec']
        restoration = game.restore_feasibility(callbacks['ownership'], incumbent, context,
'''),
        ("            physical_fingerprint=callbacks['physical_fingerprint'], max_evaluations=max_evaluations,\n            time_budget_sec=time_budget_sec, deadline_check=deadline_check,\n", "            physical_fingerprint=callbacks['physical_fingerprint'], max_evaluations=restore_evaluations,\n            time_budget_sec=restore_time, deadline_check=deadline_check, initial_seeds=initial_seeds,\n"),
        ("    game_neighbors = callbacks['neighbors']\n", '''    if restoration_policy is not None and restoration is not None and not restoration['feasible']:
        # Keep the existing checked infeasible witness; do not spend a second
        # game budget trying to score the same failed initializer again.
        remaining_evaluations = 0
    game_neighbors = callbacks['neighbors']
'''),
        ("    started = perf_counter()\n    restoration = None\n", "    started = perf_counter()\n    seed_incumbent = copy.deepcopy(incumbent) if restoration_policy is not None else None\n    restoration = None\n"),
        ("    return {'game': result, 'final_score': final_score, 'command_evidence': evidence, **extra,\n", '''    if restoration_policy is not None:
        seed_checks = []
        for index, seed in enumerate((seed_incumbent, *initial_seeds)):
            raw_seed = cache.get(packed(seed))
            row = {'seed_index': index, 'action_token': token(seed), 'evaluated': raw_seed is not None}
            if raw_seed is not None:
                observed = pickle.loads(raw_seed)
                q = observed['quantity_constraints']
                row.update(np_veh=q['np']['actual'], nuf_veh_h=q['nuf']['actual'],
                    nuf_satisfied=q['nuf']['satisfied'], target_cap_satisfied=q['np']['satisfied'],
                    model_and_writer_validated=(observed.get('conditional_model_feasibility_witness') is True
                        and observed['model_constraint_coverage'].get('complete') is True
                        and observed['resource_summary']['max_exceedance_veh'] <= shared_tolerance),
                    accepted_as_initializer=bool(restoration and restoration['feasible'] and packed(seed)==packed(incumbent)))
            seed_checks.append(row)
        extra['initializer_seed_checks'] = seed_checks
    return {'game': result, 'final_score': final_score, 'command_evidence': evidence, **extra,
'''),
    ]
    manifest('fast_np_follower_pending_v2', 'evaluation/controllers/area_follower_objective.py', edits)
    config = json.loads((D/'joint_config_unlimited_prefetch_v1.json').read_text(encoding='utf-8'))
    config['name'] = 'joint_fast_np_bounded_v2'
    config['control_area_objective']['prefetch_complete_sweep_responses'] = False
    config['control_area_objective']['fast_np_initialization'] = {
        'candidate_time_budget_sec': 120., 'restoration_time_budget_sec': 45., 'restoration_max_evaluations': 8}
    (D/'joint_config_fast_np_v2.json').write_text(json.dumps(config, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print('Prepared three source manifests and an explicit future diagnostic config; no canonical source edits.')


if __name__ == '__main__':
    main()
