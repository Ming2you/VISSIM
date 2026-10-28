# DIAGNOSTIC ONLY (not a replay): wrap configure_native_choice_groups to print why the partition check fails.
import sys, runpy, json
sys.path[:0] = ['D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/code']
import evaluation.controllers.physical_movement_routes as pmr
_orig = pmr.configure_native_choice_groups


def wrapped(cfg, detectors, tuning, *, state_json):
    path = tuning.get('urban', {}).get('movements', {}).get('physical_route_topology')
    document, routes, edges = pmr.load_evidence(path)
    groups = document.get('native_choice_groups', {})
    specs = dict(cfg.network.urban_movements)
    owned = set()
    for group, row in groups.items():
        chosen = row['route_to_movement']
        members = set(chosen.values())
        current = {m for m, s in specs.items() if s.get('origin') == row['origin'] and s.get('signal') == row['signal']}
        available = {k for k in routes if k.split(':')[0] == row['decision']}
        bad = (set(chosen) != available or not available or len(members) != len(chosen)
               or members != current or members != set(row['expected_specs']) or members & owned)
        if bad:
            print('GROUP', group, 'decision', row['decision'], 'origin', row['origin'], 'signal', row['signal'], file=sys.stderr)
            print('  chosen-available', sorted(set(chosen) - available), 'available-chosen', sorted(available - set(chosen)), file=sys.stderr)
            print('  members-current', sorted(members - current), 'current-members', sorted(current - members), file=sys.stderr)
            print('  members-expected', sorted(members - set(row['expected_specs'])), 'expected-members', sorted(set(row['expected_specs']) - members), file=sys.stderr)
            for m in sorted(members | current):
                s = specs.get(m)
                print('   spec', m, None if s is None else {k: s.get(k) for k in ('origin', 'signal', 'phase', 'destination')}, file=sys.stderr)
        owned |= members
    return _orig(cfg, detectors, tuning, state_json=state_json)


pmr.configure_native_choice_groups = wrapped
adapter = sys.argv[1]
sys.argv = [adapter] + sys.argv[2:]
runpy.run_path(adapter, run_name='__main__')
