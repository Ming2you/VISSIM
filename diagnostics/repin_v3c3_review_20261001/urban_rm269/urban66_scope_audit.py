"""Read completed artifacts; reconstruct omitted gate transit without any rollout.

Only trusted, locally produced request pickles are read. Future native frames
are validation targets, never model inputs. This audit does not modify a plant.
"""
import hashlib
import json
import pickle
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
from src.models.urban_queue_model import _inflow_delay_steps

FRAMES = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29/lane_observations')
ORIGIN = 'in_SC1004_S'
pins = {}


def data(path, binary=False):
    raw = path.read_bytes()
    pins[str(path)] = hashlib.sha256(raw).hexdigest()
    return pickle.loads(raw) if binary else json.loads(raw)


def frame(t):
    f = data(FRAMES / f'frame_{t:06}.json')
    assert f['complete'] and f['time_s'] == t
    return {v[0]: v for v in f['vehicles']}


def native(t):
    before, after = frame(t), frame(t + 150)
    start = {k: v for k, v in before.items() if v[1] == 66}
    end = {k: v for k, v in after.items() if v[1] == 66}
    by_lane = {}
    for lane in range(1, 5):
        by_lane[str(lane)] = dict(Counter(
            f'{v[6]}:{v[7]}' if v[8] == 'STATIC' else 'before_choice_or_unknown'
            for v in start.values() if v[2] == lane))
    # These are snapshot transitions, not a trajectory-derived exit count.
    return dict(initial=len(start), final=len(end),
                initial_still66=len(start.keys() & end.keys()),
                initial_no_longer66=len(start.keys() - end.keys()),
                initial_missing_from_next_frame=len(start.keys() - after.keys()),
                newly_seen66=len(end.keys() - start.keys()), route_counts_by_lane=by_lane)


def partial66(response, end, keys):
    values = response['central_physical']
    lookup = dict(zip(values['names'], values['values']))
    total = 0.
    for key in keys:
        kind, name = key.split(':', 1)
        field, bound = ('storage', 'upper') if kind == 'storage' else ('urban_movement_queue', '0/lower')
        total -= lookup[f'physical/{end}/{field}/{name}/{bound}']
    return total


rows = []
for at, leaf in ((1800, 'local1800'), (2400, 'local2400_v2'), (3300, 'local3300'), (4500, 'local4500')):
    row = dict(start_sec=at, native=native(at))
    request_path = HERE / f'cap_probe{at}_verified_env/request.pickle'
    if not request_path.exists():
        row.update(status='incomplete_footprint', reason='No saved forecast request to independently reconstruct gate transit; old 66 underprediction claim withdrawn.')
        rows.append(row)
        continue
    request = data(request_path, binary=True)
    follower, state, reference, forecast = request['owned']
    cfg = follower.cfg
    assert state.time_sec == at
    assert not state.urban_inflow_transit_buffer.get('gate:' + ORIGIN)
    gate_spec = getattr(cfg.network, 'physical_gate_travel', {}) or {}
    # The candidate retains the same regular boundary-inflow implementation.
    assert ORIGIN != gate_spec.get('source')
    dt = cfg.simulation.T_u_sec
    delay_sec = _inflow_delay_steps(cfg, ORIGIN) * dt
    assert delay_sec > 150
    assert cfg.simulation.control_interval == 150 and len(forecast) == 3
    expected450 = sum(x.urban_boundary[ORIGIN] * 150 / 3600 for x in forecast)
    transit150 = forecast[0].urban_boundary[ORIGIN] * 150 / 3600
    row.update(status='complete_first150_footprint',
               gate_delay_sec=delay_sec, omitted_gate_transit150=transit150,
               initial_gate_transit=0, boundary_inputs450=expected450, models={})
    base = HERE.parent / f'goal8_265/spillback2000/coupling268/lane{at}'
    if not (base / 'continuous450.json').exists():
        base = HERE / f'baseline{at}'
    initial = data(FRAMES.parent / f'action_{at:06}.json')
    keys = list(initial['projection_diagnostics']['physical_stock_assignment_by_link']['66'])
    assert sum(initial['projection_diagnostics']['physical_stock_assignment_by_link']['66'].values()) == row['native']['initial']
    for model, folder in (('baseline', base), ('candidate', HERE / leaf)):
        prepared = data(folder / 'network.json')
        assert prepared['urban_boundary_travel_time_sec'][ORIGIN] == cfg.network.urban_boundary_travel_time_sec[ORIGIN]
        before = data(folder / 'state.json')
        assert not before['urban_inflow_transit_buffer'].get('gate:' + ORIGIN)
        responses = data(folder / 'continuous450.json')
        for result in responses:
            recorded = result['response']['control_area']['flow_counts']['input:gate:' + ORIGIN]
            assert abs(recorded - expected450) < 1e-7, (at, model, recorded, expected450)
        old = dict(predicted=partial66(responses[0]['response'], at + 150, keys),
                   release=partial66(responses[1]['response'], at + 150, keys), observed=row['native']['final'])
        row['models'][model] = dict(
            old_incomplete_hold=old['predicted'], old_incomplete_release=old['release'],
            corrected_hold=old['predicted'] + transit150,
            corrected_release=old['release'] + transit150,
            observed=old['observed'],
            corrected_hold_error=old['predicted'] + transit150 - old['observed'],
            model_initial_stock_departed150=row['native']['initial'] - old['predicted'],
            native_initial_stock_no_longer66=row['native']['initial_no_longer66'],
            predicted_gate_transit_minus_native_new_stock=transit150 - row['native']['newly_seen66'])
    rows.append(row)

result = dict(schema='urban66-comparison-footprint/v1',
    scope='First150 only: initial storage+movement queues plus new gate transit. Full 450s response costs already include transit; objective/AD results are not changed.',
    correction='Previous 66 stock comparison omitted transit:gate:in_SC1004_S, which did not exist at initialization but grows during prediction.',
    method='Regular gate delay exceeds150s; initial gate buffer empty. Thus all first-block predicted gate inputs are still on66 at150s. Independently reconcile450s input ledger against saved forecast.',
    limits=['Snapshot departures are not classified normal exits/deletions.', 'Newly seen native end stock is not total gate inflow: vehicles may enter and leave between snapshots. Its difference from predicted transit can reflect demand or travel-time errors.', 'No native RM counterfactual or long-run gain claim.', 'No recalibration is justified by the superseded incomplete stock comparison.'],
    rows=rows, source_pins=pins)
(HERE / 'urban66_scope_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps([dict(start_sec=r['start_sec'], status=r['status'], models=r.get('models')) for r in rows], indent=2))
