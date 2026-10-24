"""One unchanged conditional replay with observers for local sending allocation.

Future native arrivals and signals are diagnostic inputs only. This is not an
autonomous prediction or a control-gain calibration.
"""
import copy
import gzip
import hashlib
import importlib.util
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
PINS = {}


def read(p):
    b = p.read_bytes()
    PINS[str(p)] = hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix == '.gz' else b)


def main():
    target = HERE / 'assessment_prefix.json'
    assert not target.exists()
    completed = read(R / 'ramp10681_lane_conflict/completion.json')
    for p, h in completed['previous_production_exact'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
    module = R / 'urban10643_conditional/replay.py'
    spec = importlib.util.spec_from_file_location('unchanged_conditional_replay', module)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    prior = read(R / 'urban10643_conditional/assessment.json')
    manifest = read(R / 'retained10638/candidate_manifest.json')
    network = ROOT / manifest['sources']['network']['path']
    assert hashlib.sha256(network.read_bytes()).hexdigest() == manifest['sources']['network']['sha256']
    protocol = read(ROOT / manifest['sources']['reference_protocol']['path'])
    cache = read(R / 'lane10643_native/rows.json.gz')
    routes, exits = replay.geometry(network)
    rows = [r for r in cache['rows'] if r[0] == replay.START and r[2] in replay.LOCAL]
    current = replay.observe(replay.raw_frame(rows, replay.START), routes, exits)
    clocks = read(R / 'local10643_receiver/head_audit.json')['cases']['47hold']
    program = replay.NativeProgram(clocks)
    trace = read(I / 'closedloop_recorded2700_select_check_trace10681_entry10643/held_actual_RM_C10681_trace.json.gz')
    room = defaultdict(dict)
    for r in trace['local_receiver_diagnostics']['resources']:
        if r['kind'] == 'lane_urban_exit_receiving':
            room[int(r['start_sec'])][int(r['resource'])] = r['available_veh']
    recorded = []
    original = replay.UrbanTransport.step

    def observed_step(model, external, **kwargs):
        t = model.time
        keys = [(71, lane, len(model.edges[71])-2) for lane in range(1, 6)]
        queues = {k: replay.FIFO(copy.deepcopy(list(model.cells[k].q))) for k in keys}
        old_receiving = {k: max(0., min(model.capacity_rate,
            model.wave/model.dx[k]*(model.cap[k]-q.stock))) for k, q in model.cells.items()}
        got = original(model, external, **kwargs)
        lateral = Counter()
        outgoing = Counter()
        transfers = []
        for source, dest, packets in model.last_transfers:
            n = math.fsum(n for _, n in packets)
            if source in queues:
                if dest[0] == 'exit':
                    outgoing[source] += n
                elif dest[0] == source[0] and dest[1] != source[1]:
                    lateral[source] += n
                    for label, amount in packets:
                        queues[source].take_label(label, amount)
                    transfers.append(dict(source=list(source), target=list(dest),
                        packets=[[list(label), amount] for label, amount in packets]))
        end = model.time
        try:
            model.time = t  # Read-only classification at the same signal clock.
            for key in keys:
                q = queues[key]
                green = program.green_at(t, 2 if key[1] <= 3 else 5)
                destination, reason = model.route(key, q.q[0][0], old_receiving) if q.q else (None, 'empty')
                prefix = list(q.q[0][0]) if q.q else None
                prefix_amount = q.q[0][1] if q.q else 0.
                positions = []
                if green and reason == 'lane_access' and q.q:
                    label = q.q[0][0]
                    positions = [dict(cell=list(k), amount=cell.counts()[label])
                                 for k, cell in model.cells.items() if label in cell.counts()]
                sending = model.last_sending_limits[key]
                recorded.append(dict(time_s=t, lane=key[1], green=green,
                    sending=sending, lateral_out=lateral[key], exit_out=outgoing[key],
                    residual_sending=max(0., sending-lateral[key]-outgoing[key]),
                    prefix_after_lateral=prefix, reason_after_lateral=reason,
                    prefix_amount_after_lateral=prefix_amount,
                    blocking_label_locations_end_step=positions,
                    route_target=destination, lateral_transfers=[x for x in transfers if x['source']==list(key)]))
        finally:
            model.time = end
        return got

    replay.UrbanTransport.step = observed_step
    try:
        result = replay.run(current, network, protocol, prior['events'], program,
                            room, 'early', 'frozen_exit', [])
    finally:
        replay.UrbanTransport.step = original
    old = prior['cases']['early_frozen_exit_conserved']
    assert {k: v for k, v in result.items() if k != 'wall_sec'} == {k: v for k, v in old.items() if k != 'wall_sec'}
    summary = {}
    for lane in range(1, 6):
        selected = [r for r in recorded if r['lane']==lane and r['green']]
        classes = defaultdict(lambda: dict(steps=0, residual_sending=0., lateral_out=0., exit_out=0.))
        prefixes = defaultdict(lambda: dict(steps=0, residual_sending=0.))
        for row in selected:
            reason = row['reason_after_lateral']
            bucket = classes[reason]
            bucket['steps'] += 1
            for k in ('residual_sending', 'lateral_out', 'exit_out'):
                bucket[k] += row[k]
            if row['prefix_after_lateral'] is not None and row['residual_sending'] > 1e-6:
                label = str(row['prefix_after_lateral'])
                prefixes[label]['steps'] += 1
                prefixes[label]['residual_sending'] += row['residual_sending']
        summary[str(lane)] = dict(green_steps=len(selected), by_reason=dict(classes),
            prefixes=sorted(prefixes.items(), key=lambda x:-x[1]['residual_sending'])[:8])
    for p, h in completed['previous_production_exact'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest() == completed['stop_sha256']
    output = dict(status='completed_unchanged_conditional_sending_audit',
        future_native_input=True, autonomous=False, parity_exact_except_wall=True,
        conditional_replays=1, full_forecasts=0, new_native=0, new_fzp=0, fit_calls=0,
        native_departures=prior['native']['implied_normal_departures'],
        model_departures=result['departures'], summary=summary, rows=recorded,
        wall_sec=result['wall_sec'], source_pins=PINS,
        limitations=['Repeated unserved sending is an opportunity measure, not a count of unique missing vehicles.',
            'Post-lateral prefix classification is diagnostic; downstream room competition is not removed.',
            'Same future native input as the already completed conditional replay; no autonomous gain claim.'])
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k: v for k, v in output.items() if k not in ('rows','source_pins')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
