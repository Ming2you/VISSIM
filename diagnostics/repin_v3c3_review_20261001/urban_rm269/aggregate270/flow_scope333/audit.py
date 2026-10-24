"""Reuse332 predictions and obs150 frames; repair scope before changing physics."""
from pathlib import Path
from dataclasses import asdict
from collections import defaultdict
import gzip
import hashlib
import json
import pickle
import xml.etree.ElementTree as ET

from evaluation.controllers import obs150_contract as oc
from evaluation.controllers.obs150_observation import check_rule_crosscheck
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.flow_scope333.groups import family_keys, stock_total, boundary_ledger, crossing_edges

HERE = Path(__file__).resolve().parent
A = HERE.parent
ROOT = HERE.parents[4]
OUT = Path('E:/VISSIM_analysis/20261010_response332/forecast3300')
NET = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected/network/native_seed29.inpx'
CORRIDOR = {1220006403, 10655, 412, 10651, 10652, 410, 10654, 408,
            10647, 10648, 409, 10649, 403, 10661, 10669, 10671}
PORTS = {'headfree:10565': 'SC1005_N_SC105_to_W_SC1004',
         'headfree:10570': 'SC1005_N_SC105_to_E_SC107'}
PINS = {}


def blob(path):
    path = Path(path)
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return data


def read(path):
    data = blob(path)
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


def count(frame, links):
    assert frame['complete']
    return sum(v[1] in links for v in frame['vehicles'])


def main():
    assert not (HERE / 'assessment.json').exists(), 'Preserve completed audit'
    summary = read(OUT / 'summary.json')
    assert summary['status'] == 'complete' and summary['forecasts'] == 3
    cfg, state, _ = pickle.loads(blob(A / 'transfer331/build3300_v2/initial.pickle'))
    source = Path(read(A / 'transfer331/build3300_v2/summary.json')['source'])
    groups = {
        'approach52_all_origins': family_keys(cfg.network.urban_movements, ('SC1005_to_SC1004', 'SC107_to_SC1004')),
        'approach52_first_origin': family_keys(cfg.network.urban_movements, ('SC1005_to_SC1004',)),
        'approach52_second_origin': family_keys(cfg.network.urban_movements, ('SC107_to_SC1004',)),
        'parent_SC105_to_SC1005': family_keys(cfg.network.urban_movements, ('SC105_to_SC1005',)),
    }
    assert len(groups['approach52_all_origins']) == 8
    assignment = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    support = {g: {link: sum(v for key, v in entries.items() if key in keys)
                   for link, entries in assignment.items() if any(key in keys and v for key, v in entries.items())}
               for g, keys in groups.items()}
    net = ET.fromstring(blob(NET))
    assert PINS[str(NET)] == '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
    edges = set()
    for link in net.find('links'):
        u, v = link.find('fromLinkEndPt'), link.find('toLinkEndPt')
        if u is not None:
            connector = int(link.attrib['no'])
            edges.update(((int(u.attrib['lane'].split()[0]), connector),
                          (connector, int(v.attrib['lane'].split()[0]))))
    ins, outs = crossing_edges(edges, CORRIDOR)
    assert ins == [(416, 10671), (1220007001, 10669), (1220007200, 10661)], ins
    assert outs == [(403, 10565), (403, 10570)], outs
    direct_inputs = [dict(x.attrib) for x in net.find('vehicleInputs') if int(x.attrib['link']) in CORRIDOR]
    assert not direct_inputs
    # A static routing destination does not remove a vehicle. Removal events
    # are checked separately; none of the corridor links is a network sink.
    assert all(any(u == link for u, _ in edges) for link in CORRIDOR)
    native = []
    previous = None
    for sec in (3300, 3450, 3600, 3750):
        raw = read(source / f'state_{sec:06}.json')
        bundle = oc.load_bundle(raw)
        assert raw['sim_sec'] == sec and raw['vehicle_records']['complete']
        assert raw['vehicle_records']['record_count'] == len(bundle.frame_end['vehicles'])
        if previous is not None:
            assert bundle.frame_start['vehicles'] == previous['vehicles']
        previous = bundle.frame_end
        row = dict(sec=sec, corridor_inventory=count(bundle.frame_end, CORRIDOR),
                   corridor_by_link={str(link): count(bundle.frame_end, {link}) for link in sorted(CORRIDOR)},
                   physical52_58=count(bundle.frame_end, {52, 58}),
                   fixed_projection_footprint=count(bundle.frame_end, {52, 58, 10498, 10501}) + .5 * count(bundle.frame_end, {10565}))
        if sec > 3300:
            obs = bundle.obs
            detectors, _ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
            PINS[obs['detector_config']['path']] = obs['detector_config']['sha256']
            oc.validate_raw(obs, detectors, expected_simres=oc.EXPECTED_SIMRES)
            check_rule_crosscheck(obs, detectors)
            boundaries = oc.evaluate_boundaries(obs, detectors, bundle.frame_end, bundle.frame_start, bundle.err_rows)
            removed = [r for r in oc.window_removals(bundle.err_rows, sec-150, sec) if int(r['link']) in CORRIDOR]
            row['boundary'] = {key: asdict(boundaries[key]) for key in PORTS}
            row['removed'] = removed
            row['exits'] = sum(boundaries[key].cross for key in PORTS)
            row['entries_balance_derived'] = row['corridor_inventory'] - native[-1]['corridor_inventory'] + row['exits'] + len(removed)
            row['upstream_heads'] = {d.boundary_ref: asdict(boundaries[d.boundary_ref]) for d in detectors
                                     if d.link in {1220007200, 1220007001, 416} and d.role == 'head'}
            assert len(row['upstream_heads']) == 8
            assert all(boundaries[key].lane_exact for key in PORTS)
            assert row['entries_balance_derived'] >= 0
        native.append(row)
    models = {}
    for arm in ('hold', 'release', 'recorded'):
        scalar = read(OUT / (arm + '.json'))
        stocks = read(OUT / (arm + '.stocks.json'))
        response = read(OUT / (arm + '.response.json.gz'))
        costs = scalar['costs_by_stock']
        model = dict(cost={g: sum(costs.get(key, 0.) for key in keys) for g, keys in groups.items()},
                     omega=scalar['omega_ttt_veh_h'], windows=[],
                     stocks=[dict(sec=r['time_sec'], **{g: stock_total(r, keys) for g, keys in groups.items()}) for r in stocks])
        for j, end in enumerate((3450, 3600, 3750)):
            window = dict(start_sec=end-150, end_sec=end, groups={})
            for g, keys in groups.items():
                ledger = boundary_ledger(response['transfers'], keys, end-150, end)
                ledger['initial'] = stock_total(stocks[j], keys)
                ledger['final'] = stock_total(stocks[j+1], keys)
                ledger['balance_error'] = ledger['initial'] + ledger['incoming'] - ledger['outgoing'] - ledger['final']
                assert abs(ledger['balance_error']) < 1e-7, (arm, g, end, ledger)
                window['groups'][g] = ledger
            window['ports'] = {port: sum(x['vehicles'] for x in response['transfers']
                                         if x['source'] == 'movement:' + movement
                                         and x['target'] not in groups['parent_SC105_to_SC1005']
                                         and x['start_sec'] >= end-150 and x['end_sec'] <= end)
                               for port, movement in PORTS.items()}
            # Existing proof ledger identifies available sending stock and
            # intended service; summarize it without another rollout.
            resources = defaultdict(lambda: dict(available=0., accepted=0., binding_steps=0, steps=0))
            for x in response['resource_allocations']:
                if x['start_sec'] < end-150 or x['end_sec'] > end:
                    continue
                relevant = x['resource'] == 'storage:SC105_to_SC1005' or x['resource'] in set(PORTS.values()) or x['resource'] in {
                    'SC105_N_SC1002_to_S_SC1005', 'SC105_E_SC1_to_S_SC1005', 'SC105_W_SC1003_to_S_SC1005'}
                if not relevant:
                    continue
                rec = resources[x['kind'] + ':' + x['resource']]
                rec['available'] += x['available_veh']
                rec['accepted'] += x['accepted_total_veh']
                rec['steps'] += 1
                rec['binding_steps'] += x['available_veh'] - x['accepted_total_veh'] < 1e-7
            window['resources'] = dict(resources)
            model['windows'].append(window)
        models[arm] = model
    delta = {g: models['release']['cost'][g] - models['hold']['cost'][g] for g in groups}
    result = dict(status='complete_scope_and_boundary_audit', goal_complete=False,
                  physical_parent=dict(links=sorted(CORRIDOR), in_edges=ins, out_edges=outs, direct_inputs=direct_inputs),
                  group_keys={g: sorted(keys) for g, keys in groups.items()}, initial_assignment_support=support,
                  native=native, models=models, corrected_release_minus_hold_cost=delta,
                  limitations=[
                      'All-origin52 group fixes local diagnostic omission, not the already complete Omega objective.',
                      'Fixed fractional projection footprint is not an exact geographic volume; do not subtract a fixed1.5vehicle offset.',
                      'Parent native entries are balance-derived aggregate entries, not direct observations of individual shared-lane turns.',
                      'Counts are total inventory, not stopped queues; recorded future actions condition the model, future traffic is only a target.',
                      'No new forecasts, fitting, AD, optimization, FZP, native, or production adoption.'],
                  source_pins=PINS)
    (HERE / 'assessment.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print('NATIVE_PARENT', [(r['sec'], r['corridor_inventory'], r.get('entries_balance_derived'), r.get('exits'), len(r.get('removed', []))) for r in native])
    print('MODEL_PARENT', [(r['start_sec'], r['groups']['parent_SC105_to_SC1005']) for r in models['recorded']['windows']])
    print('SCOPE52', [(r['sec'], r['approach52_all_origins'], r['approach52_second_origin']) for r in models['recorded']['stocks']])
    print('CORRECTED_COST', delta)


if __name__ == '__main__':
    main()
