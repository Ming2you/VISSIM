"""Reinitialize at the shared2550s state: hold g8 versus g6/g4/g4.

Reuses completed native experiments and the established diagnostic component
plant. No VISSIM run, model fitting, default change, or full GNE claim.
"""
from pathlib import Path
import sys
import hashlib
import copy
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import prepare_data

HERE = Path(__file__).resolve().parent
BANK = H / 'response_late_s23_v1'
START, END = 2550, 3000
ARMS = ('rm8', 'rm_ramp')


def current_frame(path):
    """Exact nine-column native payload at the new cutoff, all network vehicles."""
    before = path.stat()
    selected = []
    header = None
    with path.open('rb') as f:
        for line in f:
            if line.startswith(b'$VEHICLE:'):
                header = line.strip()
                continue
            if header is None or not line.strip():
                continue
            t = float(line.partition(b';')[0])
            if t > START:
                break
            if t == START:
                selected.append(line.strip())
    after = path.stat()
    assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    assert header and len(header.split(b';')) == 9 and selected
    return header, sorted(selected), dict(bytes=after.st_size, mtime_ns=after.st_mtime_ns,
                                         current_rows=len(selected), current_payload_sha256=hashlib.sha256(b'\n'.join(sorted(selected))).hexdigest())


def native(data, arm):
    stocks = {int(r['time_s']): r for r in e.rows(BANK / 'analysis' / arm / 'stocks_1s.csv')}
    component = dict(mainline=sum(float(stocks[t]['FW_E_n']) for t in range(START+1, END+1))/3600,
                     on=0., off=0.)
    ports = {}
    for spec in data.definitions.values():
        if spec['road'] != 'FW_E' or spec['kind'] not in ('ramp', 'offramp'):
            continue
        c = str(spec['connector'])
        initial = len(data.port_cohorts[str(START)][c]); n = initial
        stock_seconds = arrivals = departures = checks = 0
        for t in range(START+1, END+1):
            a, d = data.arrivals[t,c], data.departures[t,c]
            arrivals += a; departures += d; n += a-d
            assert n >= 0
            stock_seconds += n
            if t % 30 == 0:
                assert n == len(data.port_cohorts[str(t)][c])
                assert float(data.ports[t,c]['unresolved_absences_veh']) == 0
                checks += 1
            if spec['kind'] == 'ramp':
                head = data.headstocks[t,c]
                assert n == int(head['prehead_n']) + int(head['posthead_n'])
        assert n == initial + arrivals-departures
        ports[c] = dict(initial=initial, final=n, arrivals=arrivals, departures=departures,
                        ttt_veh_h=stock_seconds/3600, snapshot_checks=checks)
        component['on' if spec['kind'] == 'ramp' else 'off'] += stock_seconds/3600
    return dict(component=component, ports=ports)


def main():
    out = HERE / 'matched_meter2550_v1'; out.mkdir(exist_ok=False)
    data = {a: prepare_data(BANK / 'observations' / a) for a in ARMS}
    assert data['rm8'].cells[START] == data['rm_ramp'].cells[START]
    assert data['rm8'].port_cohorts[str(START)] == data['rm_ramp'].port_cohorts[str(START)]
    profile = e.load(MODEL / 'port_profile.json')
    parameters = e.load(MODEL / 'selected_parameters.json')['parameters']
    model = e.load_base_model(data['rm8'].geometry, MODEL / 'config.json')
    protocol = e.load(BANK / 'protocol.json')
    commands = {a: protocol['candidate_bank'][a]['green'][1:4] for a in ARMS}
    assert commands == {'rm8': [8,8,8], 'rm_ramp': [6,4,4]}
    files = [Path(__file__), MODEL / 'config.json', MODEL / 'selected_parameters.json', MODEL / 'port_profile.json',
             e.CAL / 'canonical_harness.py', e.CAL / 'boundary_factory.py', H / 'evaluate_response.py',
             e.ROOT / 'evaluation/controllers/physical_ramp_boundary.py',
             e.ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py', BANK / 'protocol.json']
    for arm in ARMS:
        files += [BANK / 'observations' / arm / name for name in
                  ['cells_30s.csv','flows_30s.csv','boundaries_30s.csv','ports_30s.csv','port_cohorts_30s.json',
                   'port_events.csv','head_stock_1s.csv','head_crossings.csv']]
        files.append(BANK / 'analysis' / arm / 'stocks_1s.csv')
    pins = {p.relative_to(e.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    e.save(out / 'protocol.json', dict(source_pins=pins, seed=23, start_s=START, end_s=END,
        commands=commands, prediction_model=str(MODEL.relative_to(e.ROOT)),
        qualification=False, hypothesis='Does a later shared observed state repair the predicted marginal response to stronger metering?',
        information='Forecasts use shared current state and preceding150s only. Native outcomes evaluated afterwards.',
        scope='FW_E mainline+four on/four off connectors;not Omega;established diagnostic reference,not latest unqualified spatial candidates.'))
    predictions = {}
    for arm in ARMS:
        def command(t):
            return {'RM_C10490': commands[arm][int((t-START)//150)]}, {}
        w = e.window(data['rm8'], model, START, 'history_forecast', profile, command)
        truncated = copy.deepcopy(data['rm8'])
        truncated.cells = {t:r for t,r in truncated.cells.items() if t <= START}
        for field in ('flows','boundaries','ports','headstocks'):
            setattr(truncated, field, {key:value for key,value in getattr(truncated,field).items() if key[0] <= START})
        truncated.port_cohorts = {t:r for t,r in truncated.port_cohorts.items() if float(t) <= START}
        for field in ('events','heads'):
            setattr(truncated,field,[r for r in getattr(truncated,field) if float(r['time_s']) <= START])
        assert e.window(truncated, model, START, 'history_forecast', profile, command) == w
        pred = e.simulate(model, w, parameters)
        e.save(out / f'prediction_{arm}.json', pred)
        predictions[arm] = dict(component=parts(pred),
            merges={r['ramp']: r['end']['cumulative_merge_veh'] for r in pred['ramps'] if r['road']=='FW_E' and r['end_sec']==END},
            score=e.score_rollout(data[arm], START, pred, 'FW_E'))
        assert pred['local_ramp_audit']['passed']
        print('PREDICTED', arm, predictions[arm]['component'], flush=True)
    frames = {a: current_frame(BANK / f'run_{a}' / 'vissim_eval/baseline_001.fzp') for a in ARMS}
    assert frames['rm8'][:2] == frames['rm_ramp'][:2], 'Different native cutoff states'
    observed = {a: native(data[a], a) for a in ARMS}
    deltas = {}
    for name, records in [('predicted', predictions), ('actual', observed)]:
        delta = {k:records['rm_ramp']['component'][k]-records['rm8']['component'][k] for k in ('mainline','on','off')}
        deltas[name] = {**delta, 'total': sum(delta.values())}
    result = dict(status='MATCHED_LATER_STATE_DIAGNOSTIC_NOT_QUALIFIED', qualified=False,
                  actual=observed, predicted=predictions, deltas=deltas,
                  exact_native_cutoff_payload=True, native_receipts={a:r[2] for a,r in frames.items()},
                  future_truncation_windows_exact=2, new_native_runs=0, production_changes=0,
                  cost_convention='Native1s end-stock sum;model internal10s/mainline,1s/ramp,event/off residence.')
    for path, digest in pins.items():
        assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest() == digest, path
    e.save(out / 'result.json', result)
    print('RESULT', deltas, flush=True)


if __name__ == '__main__':
    main()
