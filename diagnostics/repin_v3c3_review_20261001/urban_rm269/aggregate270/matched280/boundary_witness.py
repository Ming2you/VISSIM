"""Localize the remaining pair error with saved150s boundaries and5s metrics."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
H = HERE.parent.parent
RUNS = Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29')
PINS = {}


def read(path):
    data = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def main():
    target = HERE / 'boundary_witness.json'
    assert not target.exists()
    review = read(HERE / 'review.json')
    old_heads = read(H / 'sc1_supply/comparison.json')['head_comparisons2400']
    model, native, mainline_admitted, heads = {}, {}, {}, []
    responses = {}
    for arm in ('hold', 'selected'):
        rp = HERE / 'authority' / (arm + '.response.json.gz')
        PINS[str(rp)] = hashlib.sha256(rp.read_bytes()).hexdigest()
        r = responses[arm] = json.loads(gzip.decompress(rp.read_bytes()))
        model[arm] = []
        for end in (2550, 2700, 2850):
            rows = [q for q in r['residence'] if q['end_sec'] <= end + 1e-7]
            model[arm].append(dict(end_sec=end, total_inside=sum(rows[-1]['inside_veh'].values()),
                ttt_veh_h=sum(sum(q['inside_veh'].values()) * q['dt_h'] for q in rows)))
        tp = H / 'native2400_analysis' / arm / 'area_timeseries.csv'
        PINS[str(tp)] = hashlib.sha256(tp.read_bytes()).hexdigest()
        rows = list(csv.DictReader(tp.open(encoding='utf8')))
        native[arm] = [next(q for q in rows if abs(float(q['sim_sec']) - at) < 1e-7) for at in (2550.1, 2700.1, 2850.)]
        raw = [read(RUNS / arm / f'decisions_sdmpc31_g_2400_{arm}_s29/state_{at:06}.json') for at in (2400, 2550, 2700, 2850)]
        mainline_admitted[arm] = {road: [b['obs150']['source_cumulative_vehs'][road] - a['obs150']['source_cumulative_vehs'][road]
                                      for a, b in zip(raw, raw[1:])] for road in ('FW_E', 'FW_W')}
    phases = {'SC6_S': {'p1': ['SC6_S_SC12_to_N_SC103', 'SC6_S_SC12_to_E_SC104'], 'p2': ['SC6_S_SC12_to_W_SC5']},
              'SC101_S': {'p1': ['SC101_S_SC1_to_N_SC2005'], 'p2': ['SC101_S_SC1_to_W_SC1002']}}
    for row in old_heads:
        sources = {'movement:' + m for m in phases[row['group']][row['phase']]}
        predicted = [sum(t['vehicles'] for t in responses[row['arm']]['transfers'] if t['source'] in sources and at <= t['start_sec'] < at + 150)
                     for at in (2400, 2550, 2700)]
        heads.append(dict(arm=row['arm'], group=row['group'], phase=row['phase'], actual=row['actual'], predicted=predicted))
    times = []
    for j, end in enumerate((2550, 2700, 2850)):
        a, b = native['hold'][j], native['selected'][j]
        x, y = model['hold'][j], model['selected'][j]
        times.append(dict(model_end_sec=end, native_sample_sec=float(a['sim_sec']),
            actual_delta_inside=float(b['inside_vehicles']) - float(a['inside_vehicles']),
            predicted_delta_inside=y['total_inside'] - x['total_inside'],
            actual_delta_ttt=float(b['ttt_veh_h_cumulative']) - float(a['ttt_veh_h_cumulative']),
            predicted_delta_ttt=y['ttt_veh_h'] - x['ttt_veh_h']))
    route_delta = review['variants']['authority']['boundary_delta_by_route']
    model_impulse = {field:sum(v[field] for v in route_delta.values()) for field in
                     ('entered','departed','generated_inside','entry_cost','departure_cost','generation_cost')}
    native_delta = review['native_boundary']['delta']
    native_impulse = dict(entry_or_appearance_cost=sum(native_delta[k]['weighted_veh_h'] for k in
        ('observed_entry_events','appeared_inside_events','reappeared_inside_events')),
        counted_departure_cost=sum(native_delta[k]['weighted_veh_h'] for k in ('observed_exit_events','terminal_exit_inferred_events')),
        unresolved_disappearance_cost=native_delta['unresolved_inside_disappearances']['weighted_veh_h'])
    record = dict(status='boundary_timing_and_admission_mismatch_localized_not_fixed', time_window=[2400,2850],
        cumulative_response=times, native_mainline_admitted=mainline_admitted, model_boundary_impulse=model_impulse,
        native_boundary_impulse=native_impulse, head_response_by150=heads, source_pins=PINS,
        diagnostic_correction='Initial boundary identity omitted exogenous generation insideOmega. Adding it closes both inventory andTTT; no production ledger bug was established.',
        findings=['The current10681 incremental merge and mainlineTTT are close for the jointpair; do not repair net gain by arbitrary merge damping.',
            'Actual selected departure timing increases residence despite19more countedOmegaexits by the end; model predicts early discharge benefit.',
            'ObservedFW_E admitted891vs935 andFW_W541vs533 differ; model admits900/519 inboth. Same inputvolume program does not imply identical native admissions.',
            'Extra native admissions do not identify insertionblocking versus stochastic arrival realization; no future counts were inserted into forecast.',
            'SC101 through andSC6 south phase response remain focused boundary checks, not a new coefficient grid.'],
        limitations=['Firsttwo native samples end0.1s after modelblock; fullwindowpairTTT uses existing matched5s integration.',
            'Source cumulative counters coverfreeway only; appearedinside totals do not identify everyurban input.',
            'No isolatedRM orcity-only native effect is inferred.'],
        new_predictions=0,new_native_runs=0,new_fits=0,new_optimizers=0)
    target.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:record[k] for k in ('cumulative_response','native_mainline_admitted','model_boundary_impulse','native_boundary_impulse','head_response_by150')},indent=2))


if __name__ == '__main__':
    main()
