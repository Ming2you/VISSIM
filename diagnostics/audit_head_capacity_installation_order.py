"""Read-only head-floor -> final cfg/local-cache audit; never solves or advances.

The optional artificial arm perturbs *private in-memory* member capacities
after the real observer returns. It is an installation-order regression probe,
not observed capacity, a new action, calibration, or a traffic prediction.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pickle
import time
from unittest.mock import patch

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected, replay_provenance
from evaluation.controllers import (signal_head_observation as observation,
    physical_movement_routes, area_dynamic_routes, route_choice_corridor,
    local_signal_service, native_internal_input, sc2001_corridor, runtime_setup)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def snapshot(cfg):
    return {'caps': deepcopy(cfg.network.movement_capacity_by_movement_veh_h),
            'specs': deepcopy(cfg.network.urban_movements),
            'renames': deepcopy(getattr(cfg.network, 'movement_merge_rename', {}))}


def consumers(cfg):
    # Constructor only: these are the actual Wu local-model caches, not a solve.
    from src.controllers.wu_faithful_follower import WuFaithfulFollower
    from src.models import urban_queue_model as uqm
    from src.models.state import ControlAction
    follower = WuFaithfulFollower(cfg)
    neutral = ControlAction.uncontrolled(cfg)
    neutral.inflow_outflow_allocation = {}
    local = {m: value for model in follower._local_models.values()
             for m, value in model.cap_flow_of.items()}
    global_caps = {m: uqm._movement_capacity_flow(neutral, cfg, m, s)
                   for m, s in follower._specs.items()}
    return {'global_neutral_caps': global_caps, 'fresh_Wu_local_caps': local,
            'mismatches': {m: [v, local.get(m)] for m, v in global_caps.items()
                           if m in local and v != local[m]}}


def run_arm(config, state_path, previous, *, artificial=False):
    observed = {}
    stages = []
    original_observer = observation.install

    def head_install(cfg, raw, old_action, caps, plan, distribute, options):
        geometry = observation.physical_groups(raw['network_path'], plan)
        groups = [{'stopline_link': link, 'signal': 'SC'+heads[0]['sc']}
                  for (link, phase), heads in geometry.items()]
        rows = {}
        for key, heads in geometry.items():
            weights = {}
            distribute(cfg, groups, {key: 1.}, weights)
            rows['|'.join(key)] = {'heads': heads, 'weights': weights,
                                  'base_caps': {m: caps[m] for m in weights}}
        observed['before'] = snapshot(cfg)
        metadata = original_observer(cfg, raw, old_action, caps, plan, distribute, options)
        observed['actual_metadata'] = deepcopy(metadata)
        observed['actual_after'] = snapshot(cfg)
        # Private sensitivity: unlike a real floor, this does not claim an
        # observed group total or resolve physical/member mapping ambiguity.
        if artificial:
            members = {m for row in rows.values() for m in row['weights']}
            changed = dict(cfg.network.movement_capacity_by_movement_veh_h)
            for m in members:
                changed[m] = 2. * changed[m] + 1.
            cfg.network.movement_capacity_by_movement_veh_h = changed
        observed['after'] = snapshot(cfg)
        observed['groups'] = rows
        return metadata

    def trace(module, name):
        original = getattr(module, name)
        def call(cfg, *args, **kwargs):
            before = snapshot(cfg)
            value = original(cfg, *args, **kwargs)
            after = snapshot(cfg)
            changed = {m: {'before': before['caps'].get(m), 'after': after['caps'].get(m),
                           'spec_before': before['specs'].get(m), 'spec_after': after['specs'].get(m)}
                       for m in before['caps'].keys() | after['caps'].keys()
                       if before['caps'].get(m) != after['caps'].get(m)
                       or before['specs'].get(m) != after['specs'].get(m)}
            stages.append({'function': module.__name__+'.'+name,
                           'evidence_path': args[2].get('evidence_path')
                           if name == '_configure_one' else None,
                           'changes': changed})
            return value
        return patch.object(module, name, call)

    with ExitStack() as stack:
        stack.enter_context(patch.object(observation, 'install', head_install))
        for module, name in ((physical_movement_routes, 'configure_topology_repair'),
                (area_dynamic_routes, 'configure'), (route_choice_corridor, '_configure_one'),
                (local_signal_service, 'configure'),
                (physical_movement_routes, 'configure_native_input_signal_authority'),
                (native_internal_input, 'configure'), (sc2001_corridor, 'configure')):
            stack.enter_context(trace(module, name))
        cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
            config, state_path, previous, fixture_inputs=False)
    final = snapshot(cfg)
    consumed = consumers(cfg)
    worker_cfg = pickle.loads(pickle.dumps(cfg))
    worker_before = snapshot(worker_cfg)
    runtime_setup.install_worker_runtime(adapter, worker_cfg, raw, detectors)
    worker = consumers(worker_cfg)
    rows = []
    owners = defaultdict(list)
    for key, group in observed['groups'].items():
        members = []
        for m, weight in group['weights'].items():
            owners[m].append(key)
            renamed = final['renames'].get(m)
            target = m if m in final['specs'] else renamed if renamed in final['specs'] else None
            members.append({'movement': m, 'weight': weight,
                'base_veh_h': group['base_caps'][m],
                'actual_observer_veh_h': observed['actual_after']['caps'][m],
                'probe_installed_veh_h': observed['after']['caps'][m],
                'final_target': target, 'final_veh_h': final['caps'].get(target),
                'global_veh_h': consumed['global_neutral_caps'].get(target),
                'fresh_local_veh_h': consumed['fresh_Wu_local_caps'].get(target),
                'worker_local_veh_h': worker['fresh_Wu_local_caps'].get(target),
                'events': [{'function': s['function'], 'evidence_path': s['evidence_path'],
                            **s['changes'][m]} for s in stages if m in s['changes']]})
        rows.append({'group': key, 'heads': group['heads'], 'members': members})
    altered = [row for row in rows if any(m['events'] for m in row['members'])]
    return {'arm': 'artificial_member_perturbation' if artificial else 'actual_observer',
        'scope': 'configure/project + constructor + pickle/worker reinstall only; no dynamics/optimization',
        'actual_observer_metadata': observed['actual_metadata'],
        'summary': {'physical_groups': len(rows), 'mapped_groups': sum(bool(r['members']) for r in rows),
            'changed_groups': len(altered), 'changed_group_ids': [r['group'] for r in altered],
            'global_local_mismatches': consumed['mismatches'],
            'worker_global_local_mismatches': worker['mismatches'],
            'worker_cap_or_spec_changes': snapshot(worker_cfg) != worker_before,
            'worker_consumer_values_equal': consumed == worker},
        'multiple_group_member_ownership': {m: ks for m, ks in owners.items() if len(ks) > 1},
        'groups': rows, 'stages': stages,
        'final_route_turn_services': {m: {'connector': s['connector'], 'service_veh_h': s['service_veh_h']}
            for m, s in getattr(cfg.network, 'route_choice_corridor', {}).get('turns', {}).items()},
        'note': 'Actual v1 raw may be replayed by corrected current code; this does not reclassify the recorded failed v1 smoke as successful.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--artificial-order-probe', action='store_true')
    args = parser.parse_args()
    paths = [p.resolve() for p in (args.config, args.state, args.previous)]
    tuning = adapter.load_optional_json(str(paths[0]))
    before = replay_provenance(tuning, *paths)
    # Include all controller source before lazy imports, not just loaded modules.
    before.update({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (ROOT/'evaluation/controllers').glob('*.py')})
    started = time.perf_counter()
    arms = [run_arm(*paths)]
    if args.artificial_order_probe:
        arms.append(run_arm(*paths, artificial=True))
    changes = [p for p, digest in before.items()
               if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest]
    result = {'schema': 'head-capacity-installation-order/v1',
              'input_paths': [str(p) for p in paths], 'source_sha256': before,
              'source_changes': changes, 'elapsed_sec': time.perf_counter()-started,
              'arms': arms}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'source_changes': changes,
                      'elapsed_sec': result['elapsed_sec'],
                      'arms': [a['summary'] for a in arms]}, ensure_ascii=False))
    if changes:
        raise RuntimeError('Pinned sources changed during audit')


if __name__ == '__main__':
    main()
