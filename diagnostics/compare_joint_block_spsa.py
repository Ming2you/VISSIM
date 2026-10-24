"""Bounded diagnostic block-SPSA against one completed common price field.

The optional recorded-state CLI intercepts the canonical adapter before leader
selection; it never writes an applied action. Canonical realization,
writer/box validation and decision response callbacks are reused. This
does not manufacture matched single-owner secants from joint perturbations or
install an approximate field as a certified production price field.
"""
from __future__ import annotations

import copy
import hashlib
import math
import pickle
import random
import time

import numpy as np


def _digest(value):
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _vectors(follower, owner, edges, fixed_meters=None):
    net = follower.cfg.network
    rows = []
    if owner in net.signals:
        live = tuple(p for p in ('p1', 'p2', 'p3', 'p4') if p in net.signal_live_phases(owner))
        native = (getattr(net, 'signal_actuation_contract', {}) or {}).get('nodes', {}).get(owner, {}).get('native_clock_basis')
        if isinstance(native, dict) and native.get('kind') == 'concurrent_p1_p2':
            if set(live) != {'p1', 'p2', 'p4'}:
                raise ValueError('Concurrent native price basis requires p1, p2 and p4')
            columns = [('phase', owner+'_p1', 'veh*h/s'),
                       ('phase', owner+'_p2_minus_p4', 'veh*h/s'), ('offset', owner, 'veh*h/s')]
            for edge in edges:
                d = edge['coordinate']['direction']
                rows.append([d[owner+'_p1'], d[owner+'_p2']-d[owner+'_p4'], d[owner]])
            return np.asarray(rows, dtype=float), columns
        columns = [('phase', owner+'_'+p, 'veh*h/s') for p in live[:-1]] + [('offset', owner, 'veh*h/s')]
        for edge in edges:
            d = edge['coordinate']['direction']
            rows.append([d[owner+'_'+p]-d[owner+'_'+live[-1]] for p in live[:-1]]+[d[owner]])
    else:
        heads = tuple(net.freeway_vsl_zone_heads[owner][z] for z in net.freeway_vsl_zone_free)
        ramps = tuple(r for r in follower._local_freeway_models[owner].owned_ramps if r not in (fixed_meters or {}))
        columns = [('vsl_zone', owner+f'__seg{h}', 'veh*h/(km/h)') for h in heads]
        columns += [('meter', ramp, 'h^2') for ramp in ramps]
        for edge in edges:
            d = edge['coordinate']['direction']
            rows.append([d[owner+f'__seg{h}'] for h in heads]+[d[r] for r in ramps])
    return np.asarray(rows, dtype=float), columns


def compare(follower, reference, measured, *, realize, validate, response_query,
            pair_budgets=(8, 16), seed=13, check_budget=None, sign_tolerance_veh_h=1e-9,
            move_box=None):
    """Cycle one measured basis edge per owner, with independent pair signs.

    Each owner uses its actual-anchor/probe endpoints, so a meter or discrete
    VSL at an upper bound uses a one-sided displacement. Positive and negative
    whole actions are complementary combinations of those owner endpoints.
    For owner i, sign_i * [Delta J - Delta C_i] estimates its selected edge's
    external COST delta. Other-owner cross terms cause finite-sample error;
    nonlinear interactions can bias this relative to the actual anchor. It is
    sparse block simultaneous perturbation, not dense symmetric SPSA.

    The canonical realizer must return an independent action without changing
    any requested lever. The validator must return actual writer/box evidence.
    Any failed pair is retained and is never partially used in the estimate.
    Missing basis coordinates remain unknown. Prices are diagnostic only.
    """
    budgets = tuple(pair_budgets)
    if (not budgets or tuple(sorted(set(budgets))) != budgets
            or any(type(k) is not int or k < 1 for k in budgets)
            or type(seed) is not int or not math.isfinite(sign_tolerance_veh_h)
            or sign_tolerance_veh_h < 0):
        raise ValueError('Explicit increasing pair budgets, integer seed and nonnegative sign tolerance required')
    field, secants = measured['field'], measured['secants']
    expected_response_context = measured['responses']['results'][0]['frozen_context_token']
    if field['nuf_price_policy'] != 'independent':
        raise ValueError('This comparison requires the current independent-meter common price field')
    net = follower.cfg.network
    owners = tuple(net.signals)+tuple(net.freeway_links)
    if set(secants) != set(owners) or any(not secants[o] for o in owners):
        raise ValueError('Complete observed owner basis required before simultaneous comparison')
    frozen = _digest((follower, reference, measured))
    fixed_meters = {}
    if field.get('fixed_meter_proofs') is not None:
        from evaluation.controllers.joint_owner_neighbors import validate_fixed_meter_coordinate_proofs
        fixed_meters = validate_fixed_meter_coordinate_proofs(follower.cfg, reference,
            field['fixed_meter_proofs'], move_box=move_box)
        for ramp, rate in fixed_meters.items():
            if reference.ramp_metering[ramp] != rate:
                raise ValueError('Fixed meter proof differs from the measured actual anchor')
        for owner in net.freeway_links:
            expected = {r: fixed_meters[r] for r in follower._local_freeway_models[owner].owned_ramps if r in fixed_meters}
            if field['owner_fits'][owner].get('fixed_meter_coordinates', {}) != expected:
                raise ValueError('Exact price field and validated fixed meter proof differ')
    actions_by_owner, matrices, columns, true_deltas = {}, {}, {}, {}
    fields = {'green': 'green_times', 'offset': 'offsets', 'vsl': 'vsl', 'meter': 'ramp_metering'}
    for owner in owners:
        matrices[owner], columns[owner] = _vectors(follower, owner, secants[owner], fixed_meters)
        true_deltas[owner] = np.asarray([r['external_delta_veh_h'] for r in secants[owner]], dtype=float)
        actions_by_owner[owner] = []
        for edge in secants[owner]:
            coord = edge['coordinate']
            if coord['displacement'] != 1.:
                raise ValueError('Existing runtime basis must use unit directional displacement')
            request = copy.deepcopy(reference)
            for key, value in coord['base_values'].items():
                attr = fields[coord['address_kinds'][key]]
                if getattr(reference, attr)[key] != value:
                    raise ValueError('Measured basis is anchored to another actual action')
                if key in fixed_meters and coord['probe_values'][key] != value:
                    raise ValueError('Measured edge moves a proved fixed meter coordinate')
                getattr(request, attr)[key] = coord['probe_values'][key]
            actions_by_owner[owner].append(request)
    rng = random.Random(seed)
    samples = {o: [[] for _ in secants[o]] for o in owners}
    result = {'schema': 'diagnostic-joint-block-spsa/v1', 'seed': seed, 'pair_budgets': list(budgets),
        'reference_token': _digest(reference), 'fixed_price_context': copy.deepcopy(field['context']),
        'pairs': [], 'comparisons': [], 'requested_response_actions': 0, 'successful_response_actions': 0,
        'selection_compared': False, 'selected_actions': None, 'production_field_installed': False,
        'fixed_meter_coordinates': dict(fixed_meters),
        'fixed_meter_price_convention': 'Excluded only by current source/context/actual-anchor interval proof; zero representatives are not identified derivatives',
        'fixed_meter_proof': copy.deepcopy(field.get('fixed_meter_proofs')),
        'approximation': 'One actual measured basis direction per owner per pair; signs independent across owners; finite-sample cross-owner noise and nonlinear off-anchor interaction bias remain'}
    started, cpu_started = time.perf_counter(), time.process_time()

    def check(stage):
        if check_budget:
            check_budget(stage)

    def compose(indices, signs, polarity):
        action = copy.deepcopy(reference)
        for owner in owners:
            if signs[owner] != polarity:
                continue
            coord = secants[owner][indices[owner]]['coordinate']
            source = actions_by_owner[owner][indices[owner]]
            for key, kind in coord['address_kinds'].items():
                getattr(action, fields[kind])[key] = getattr(source, fields[kind])[key]
        for owner in net.freeway_links:
            count = len(net.freeway_vsl_zone_head_of_cell[owner])
            action.vsl[owner] = min(action.vsl[owner+f'__seg{i}'] for i in range(count))
        action.N_UF_star = math.fsum(action.ramp_metering[r] for r in sorted(action.ramp_metering))
        requested = {name: copy.deepcopy(value) for name, value in vars(action).items() if name != 'diagnostics'}
        action = realize(action)
        if any(getattr(action, name) != value for name, value in requested.items()):
            raise ValueError('Canonical realization changed a requested measured-basis lever')
        if any(action.ramp_metering[r] != value for r, value in fixed_meters.items()):
            raise ValueError('Simultaneous action moves a proved fixed meter coordinate')
        before_validation = _digest(action)
        evidence = validate(action)
        if _digest(action) != before_validation:
            raise ValueError('Writer/fixed-box validation changed its action')
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError('Actual writer/fixed-box evidence required')
        return action, evidence

    for pair in range(max(budgets)):
        entry = {'pair_index': pair, 'status': 'pending'}
        result['pairs'].append(entry)
        tick, cpu_tick = time.perf_counter(), time.process_time()
        indices = {o: (pair+i) % len(secants[o]) for i, o in enumerate(owners)}
        signs = {o: rng.choice((-1, 1)) for o in owners}
        entry.update(basis_indices=indices, signs=signs)
        try:
            check('spsa_pair_prepare')
            plus, plus_evidence = compose(indices, signs, 1)
            minus, minus_evidence = compose(indices, signs, -1)
            entry.update(plus_action_token=_digest(plus), minus_action_token=_digest(minus),
                         plus_evidence=plus_evidence, minus_evidence=minus_evidence)
            check('spsa_pair_responses')
            result['requested_response_actions'] += 2
            batch = response_query((plus, minus))
            if len(batch['results']) != 2:
                raise ValueError('Incomplete simultaneous pair response')
            for action, item in zip((plus, minus), batch['results']):
                if (item['action_token'] != _digest(action)
                        or item.get('conditional_model_feasibility_witness') is not True
                        or set(item['local_base_costs']) != set(owners)):
                    raise ValueError('Unbound/incomplete simultaneous physical response')
            hi, lo = batch['results']
            if (hi['frozen_context_token'] != lo['frozen_context_token']
                    or hi['frozen_context_token'] != expected_response_context):
                raise ValueError('Simultaneous pair differs from the measured common physical context')
            result['successful_response_actions'] += 2
            estimates = {o: signs[o]*((hi['objective_veh_h']-lo['objective_veh_h'])
                         -(hi['local_base_costs'][o]-lo['local_base_costs'][o])) for o in owners}
            if not all(math.isfinite(v) for v in estimates.values()):
                raise ValueError('Nonfinite simultaneous external cost estimate')
            for owner, estimate in estimates.items():
                samples[owner][indices[owner]].append(float(estimate))
            entry.update(status='complete', external_delta_samples_veh_h=estimates)
        except Exception as exc:
            entry.update(status='failed', failure={'type': type(exc).__name__, 'message': str(exc)})
            if isinstance(exc, TimeoutError):
                result['stop_reason'] = 'decision_time_budget'
        finally:
            entry.update(wall_sec=time.perf_counter()-tick, cpu_sec=time.process_time()-cpu_tick)
        if pair+1 in budgets or result.get('stop_reason'):
            checkpoint = {'attempted_pairs': pair+1, 'owners': {}, 'all_coordinates_observed': True}
            for owner in owners:
                seen = [i for i, v in enumerate(samples[owner]) if v]
                missing = [i for i, v in enumerate(samples[owner]) if not v]
                row = {'basis_sample_counts': [len(v) for v in samples[owner]], 'missing_basis_indices': missing,
                       'fitted_prices': None, 'price_rank_complete': False,
                       'active_dimension': len(columns[owner]), 'unknown_reason': None}
                checkpoint['owners'][owner] = row
                if missing:
                    checkpoint['all_coordinates_observed'] = False
                    row['unknown_reason'] = 'missing basis samples'
                    continue
                y = np.asarray([math.fsum(v)/len(v) for v in samples[owner]])
                matrix = matrices[owner]
                scales = np.linalg.norm(matrix, axis=0)
                if np.any(scales == 0.):
                    row['unknown_reason'] = 'unproved unobserved active coordinates'
                    row['unknown_coordinates'] = [list(c) for c, scale in zip(columns[owner], scales) if scale == 0.]
                    continue
                solution, _, rank, _ = np.linalg.lstsq(matrix/scales, y, rcond=None)
                if rank != matrix.shape[1]:
                    row.update(rank=int(rank), unknown_reason='observed basis is rank deficient')
                    continue
                solution = solution/scales
                exact, _, _, _ = np.linalg.lstsq(matrix/scales, true_deltas[owner], rcond=None)
                exact = exact/scales
                error = y-true_deltas[owner]
                eligible = np.abs(true_deltas[owner]) > sign_tolerance_veh_h
                row.update(price_rank_complete=True, rank=int(rank),
                    estimated_external_deltas_veh_h=y.tolist(), exact_external_deltas_veh_h=true_deltas[owner].tolist(),
                    external_delta_mae_veh_h=float(np.mean(np.abs(error))),
                    external_delta_relative_l1_error=(float(np.sum(np.abs(error))/np.sum(np.abs(true_deltas[owner])))
                        if np.sum(np.abs(true_deltas[owner])) > 0 else None),
                    sign_compared_count=int(np.sum(eligible)), sign_agreement=(float(np.mean(np.sign(y[eligible])
                        == np.sign(true_deltas[owner][eligible]))) if np.any(eligible) else None),
                    fitted_prices=[{'channel': c[0], 'address': c[1], 'unit': c[2], 'exact': float(e),
                                    'estimated': float(v), 'absolute_error': abs(float(v-e))}
                                   for c, e, v in zip(columns[owner], exact, solution)])
            result['comparisons'].append(checkpoint)
        if result.get('stop_reason'):
            break
    if _digest((follower, reference, measured)) != frozen:
        raise ValueError('Simultaneous comparison changed frozen inputs')
    result.update(wall_sec=time.perf_counter()-started, cpu_sec=time.process_time()-cpu_started,
                  timing_scope='Pair wall/CPU are nested within overall; endpoint count reduction is not total speedup or traffic improvement')
    return result


class _DiagnosticComplete(BaseException):
    """Leave the adapter before its ordinary failure/action writer paths."""


def _recorded_arguments(receipt, output_dir):
    """Keep every saved input flag; redirect only the two unused action outputs."""
    from pathlib import Path
    argv = list(receipt['arguments'])
    program = 'evaluation/controllers/vissim_stackelberg_adapter.py'
    if len(argv) < 4 or argv[:3] != ['-B', '-X', 'utf8'] or argv[3].replace('\\', '/') != program:
        raise ValueError('Expected an explicit saved canonical adapter invocation')
    argv = argv[4:]
    required = {'--state-json', '--previous-action-json', '--out-action-json', '--out-action-csv',
                '--mapping-json', '--detector-mapping-json', '--calibration-json', '--tuning-json',
                '--controller', '--mode'}
    if len(argv) != 2*len(required) or set(argv[::2]) != required:
        raise ValueError('Saved invocation must have the exact unique recorded-state flags')
    values = dict(zip(argv[::2], argv[1::2]))
    if values['--controller'] != 'wu-link' or values['--mode'] != 'fast-smoke':
        raise ValueError('This diagnostic requires the saved wu-link fast-smoke invocation')
    for flag, name in (('--out-action-json', 'unused_action.json'), ('--out-action-csv', 'unused_action.csv')):
        argv[argv.index(flag)+1] = str(Path(output_dir) / name)
    return argv


def run_recorded(receipt_path, output_dir, *, exact_budget_sec=120., spsa_budget_sec=180.,
                 pair_budgets=(8, 16), seed=13, parallel_workers=0):
    """Offline recorded-state comparison; no VISSIM or final action generation.

    Exact preparation and SPSA have separately declared diagnostic budgets.
    Their combined upper bound owns the single query/worker lifetime. This is
    not a completed joint decision under the production 120-second deadline.
    """
    import json
    import os
    import sys
    import traceback
    from pathlib import Path
    from unittest.mock import patch
    from diagnostics.check_selected_open_meter_alias import validate_environment

    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        raise ValueError('Run this diagnostic from the canonical worktree root')
    environment = validate_environment()  # Before any controller/model import.
    if (any(not math.isfinite(v) or v <= 0. for v in (exact_budget_sec, spsa_budget_sec))
            or type(parallel_workers) is not int or not 0 <= parallel_workers <= 4):
        raise ValueError('Positive explicit offline budgets and zero to four response workers required')
    receipt_path, output_dir = Path(receipt_path).resolve(strict=True), Path(output_dir).resolve()
    if not output_dir.is_relative_to(root) or output_dir.exists():
        raise ValueError('Fresh diagnostic output directory inside the worktree required')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig'))
    argv = _recorded_arguments(receipt, output_dir)
    flags = dict(zip(argv[::2], argv[1::2]))
    input_paths = [receipt_path] + [Path(value).resolve(strict=True) for key, value in flags.items()
        if key.endswith('-json') and not key.startswith('--out-')]
    pins = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in input_paths}
    expected_env = receipt.get('experiment_environment', {})
    if expected_env != {'RW_OFFSET_WRITER': 'experiment'}:
        raise ValueError('Saved experiment offset-writer authority must be explicit')
    if os.environ.get('RW_OFFSET_WRITER', 'experiment') != 'experiment':
        raise ValueError('Inherited offset writer differs from the saved invocation')
    output_dir.mkdir(parents=True)
    report = {'schema': 'recorded-state-joint-block-spsa/v1', 'status': 'running',
        'receipt': str(receipt_path), 'historical_receipt_completed': receipt.get('completed'),
        'input_sha256': pins, 'environment': environment, 'adapter_arguments': argv,
        'exact_budget_sec': exact_budget_sec, 'spsa_budget_sec': spsa_budget_sec,
        'parallel_workers': parallel_workers, 'pair_budgets': list(pair_budgets), 'seed': seed,
        'production_joint_decision_completed': False, 'action_written': False,
        'approximate_price_field_installed': False, 'native_execution': False,
        'scope': 'Same recorded inputs and canonical current model/horizon/action box; diagnostic work budgets and optional worker count only. No selection, traffic improvement or production deadline certificate.'}
    started, cpu_started = time.perf_counter(), time.process_time()
    try:
        with patch.dict(os.environ, expected_env):
            from evaluation.controllers import vissim_stackelberg_adapter as adapter
            from evaluation.controllers import area_follower_objective as joint, area_meter_finalization as meters

            def intercepted(controller, state, forecast, historical, mapping, *, runtime_sources,
                            options, progress=None, budget=None, worker_bootstrap=None):
                report['hook_entered'] = True
                report['sim_sec'] = float(state.time_sec)
                report['canonical_options'] = copy.deepcopy(options)
                report['runtime_source_sha256'] = dict(runtime_sources)
                # The query receives a lifetime upper bound. Its live check
                # still enforces the current phase's narrower work budget.
                lifetime = joint.DecisionBudget(exact_budget_sec+spsa_budget_sec, reserve_sec=0.)
                active = [joint.DecisionBudget(exact_budget_sec, reserve_sec=0., started=lifetime.started)]
                lifetime.check = lambda stage: active[0].check(stage)
                options = {**options, 'response_parallel_workers': parallel_workers}
                try:
                    if parallel_workers and worker_bootstrap is None:
                        raw = json.loads(Path(flags['--state-json']).read_text(encoding='utf-8-sig'))
                        worker_bootstrap = {'state_json': {'network_path': str(Path(raw['network_path']).resolve(strict=True))},
                            'detector_mapping': json.loads(Path(flags['--detector-mapping-json']).read_text(encoding='utf-8-sig')),
                            'runtime_sources': runtime_sources}
                    tick, cpu_tick = time.perf_counter(), time.process_time()
                    common = joint.prepare_common_joint_prices(controller, state, forecast, historical, mapping,
                        runtime_sources=runtime_sources, options=options, budget=lifetime,
                        progress=progress, worker_bootstrap=worker_bootstrap)
                    report['exact_preparation'] = {'wall_sec': time.perf_counter()-tick,
                        'cpu_sec': time.process_time()-cpu_tick, 'budget': active[0].report()}
                    measured, follower, reference, query = (common[k] for k in
                        ('measured', 'follower', 'reference', 'response_query'))
                    report['exact_price'] = {k: measured[k] for k in ('field', 'probe_selection', 'secants', 'timings')}
                    report['exact_response_actions'] = len(measured['responses']['results'])
                    report['query_after_exact'] = query.stats()
                    active[0] = joint.DecisionBudget(spsa_budget_sec, reserve_sec=0.)
                    with joint.shared_query_runtime_scope():
                        adapter._PHASE_VECTOR_FOLLOWER['ref'] = follower
                        callbacks, context, _ = joint._joint_runtime_callbacks(follower, state, forecast,
                            historical, reference, mapping, runtime_sources, reference=reference,
                            total_budget=None, directional={}, tolerance=options['nuf_tolerance_veh_h'],
                            budget=lifetime, price_probe=True, progress=progress)
                        if len(callbacks['ownership'].owners) != 19:
                            raise ValueError('The real comparison requires all 19 owners')
                        def realize(action):
                            with joint.shared_query_runtime_scope():
                                return meters.prepare_canonical_candidate(action, follower.cfg,
                                    owned_ramps=tuple(follower.cfg.network.ramps), total_budget=None,
                                    directional_budgets={}, budget_tolerance_veh_h=options['nuf_tolerance_veh_h'])
                        def validate(action):
                            evidence = callbacks['command_evidence'](action, context)
                            # The original physical rows use tuple address keys.
                            # Keep their exact digest plus all 19 owner hashes;
                            # do not serialize 213 repeated rows for every pair.
                            return {'canonical_writer_and_fixed_box_checked': True,
                                'ordered_row_count': len(evidence['ordered_rows']),
                                'physical_address_count': len(evidence['physical_rows']),
                                'physical_rows_sha256': _digest(evidence['physical_rows']),
                                'owner_physical_sha256': evidence['owner_physical_sha256'],
                                'owner_model_sha256': evidence['owner_model_sha256'],
                                'provenance': evidence['provenance']}
                        report['comparison'] = compare(follower, reference, measured, realize=realize,
                            validate=validate,
                            response_query=query, pair_budgets=pair_budgets, seed=seed,
                            check_budget=lifetime.check, move_box=callbacks['move_box'])
                    report['spsa_budget'] = active[0].report()
                    report['query_after_spsa'] = query.stats()
                    report['status'] = ('completed' if len(report['comparison']['pairs']) == max(pair_budgets)
                        and all(p['status'] == 'complete' for p in report['comparison']['pairs']) else 'incomplete')
                except Exception as exc:
                    report.update(status='failed', error={'type': type(exc).__name__, 'message': str(exc)},
                                  traceback=traceback.format_exc(), failed_phase_budget=active[0].report())
                finally:
                    query = getattr(lifetime, 'response_query', None)
                    if query is not None:
                        # Let the canonical adapter finally close workers and
                        # check runtime source hashes even after interception.
                        if budget is not None:
                            budget.response_query = query
                        else:
                            query.close()
                raise _DiagnosticComplete()

            with patch.object(joint, 'solve_runtime_joint_leader', intercepted), patch.object(sys, 'argv', [adapter.__file__, *argv]):
                try:
                    adapter.main()
                except _DiagnosticComplete:
                    report['adapter_intercepted_before_action_write'] = True
                else:
                    raise ValueError('Adapter did not enter the diagnostic price-comparison hook')
    except Exception as exc:
        report.update(status='failed', error={'type': type(exc).__name__, 'message': str(exc)}, traceback=traceback.format_exc())
    finally:
        report['input_changes'] = [str(p) for p in input_paths if hashlib.sha256(p.read_bytes()).hexdigest() != pins[str(p)]]
        outputs = [Path(flags[key]) for key in ('--out-action-json', '--out-action-csv')]
        report['action_written'] = any(path.exists() for path in outputs)
        if report['input_changes'] or report['action_written']:
            report['status'] = 'failed'
        report.update(wall_sec=time.perf_counter()-started, cpu_sec=time.process_time()-cpu_started)
        (output_dir/'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    return report


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--exact-budget-sec', type=float, default=120.)
    parser.add_argument('--spsa-budget-sec', type=float, default=180.)
    parser.add_argument('--parallel-workers', type=int, choices=range(5), default=0)
    parser.add_argument('--seed', type=int, default=13)
    args = parser.parse_args()
    result = run_recorded(args.receipt, args.output_dir, exact_budget_sec=args.exact_budget_sec,
        spsa_budget_sec=args.spsa_budget_sec, parallel_workers=args.parallel_workers, seed=args.seed)
    print(json.dumps({k: result[k] for k in ('status', 'wall_sec', 'action_written')}, ensure_ascii=False))
    return 0 if result['status'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
