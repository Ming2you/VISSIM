"""Trace the remaining upstream supply deficit using closed records only."""
from collections import Counter
from pathlib import Path
import gzip
import json
import pickle

from audit import A, ROOT, HERE, RUNS, MODEL, oc, read, pin, PINS


def main():
    output = HERE / 'source_limits.json'
    assert not output.exists(), 'Do not overwrite a completed diagnosis'
    cfg, state, _ = pickle.loads(pin(A/'citysplit287/forecast2400/initial.pickle'))
    labels = {
        'SC109_left': ('SC109', 'p4', 173, 'SC109_W_SC108_to_N_SC16'),
        'SC16_south': ('SC16', 'p1', 1210009503, 'SC16_S_'),
        'SC12_south': ('SC12', 'p1', 1210012700, 'SC12_S_'),
    }
    arms = {}
    for arm, folder in RUNS.items():
        response = json.loads(gzip.decompress(pin(MODEL / (arm+'.response.json.gz'))))
        blocks = []
        for start in (2400, 2550, 2700):
            raw = read(folder/f'state_{start+150:06}.json')
            bundle = oc.load_bundle(raw)
            window = oc.assign_window(bundle.obs, bundle.mer_rows)
            dets, _ = oc.read_detector_csv(bundle.obs['detector_config']['path'],
                                           bundle.obs['detector_config']['sha256'])
            pin(bundle.obs['detector_config']['path'])
            pin(folder/bundle.obs['mer']['chunk'])
            rows = [r for r in response['transfers'] if start <= r['start_sec'] < start+150]
            resources = [r for r in response['resource_allocations'] if start <= r['start_sec'] < start+150]
            heads = {}
            for label, (signal, phase, link, prefix) in labels.items():
                groups = set(cfg.network.signal_actuation_contract['nodes'][signal]['phase_signal_groups'][phase])
                wanted = [d for d in dets if d.role == 'head' and d.link == link
                          and oc.parse_head_ref(d.ref)[2] in groups]
                assert wanted, (signal, link)
                movements = {m for m, spec in cfg.network.urban_movements.items()
                             if m.startswith(prefix) and spec['phase'] == signal+'_'+phase}
                transfers = [r for r in rows if (r['source'] or '').removeprefix('movement:') in movements
                             and r['target'] != r['source']]
                intended = {(r['start_sec'],r['resource']):r for r in resources
                            if r['kind']=='urban_movement_intended_limit' and r['resource'] in movements}
                stocks = {(r['start_sec'],r['resource']):r for r in resources
                          if r['kind']=='urban_movement_stock' and r['resource'] in movements}
                assert intended.keys() == stocks.keys()
                counters = Counter()
                maximum_rejection = 0.
                for key, r in intended.items():
                    q = stocks[key]['available_veh']
                    request, accepted = r['available_veh'], r['accepted_total_veh']
                    maximum_rejection = max(maximum_rejection,request-accepted)
                    if q <= 1e-8: counters['empty_ready_queue_steps'] += 1
                    if request > 1e-8:
                        counters['positive_request_steps'] += 1
                        counters['all_ready_requested_steps' if abs(q-request)<1e-8 else 'request_below_ready_steps'] += 1
                heads[label] = dict(native_known=sum(len(window.entries[d.dcp_no]) for d in wanted),
                    native_unresolved_tail=sum(window.tails[d.dcp_no] for d in wanted),
                    model_departures=sum(r['vehicles'] for r in transfers),
                    max_requested_but_not_received=maximum_rejection, diagnostics=dict(counters))
            incoming = {}
            for origin in ('SC109_to_SC16', 'SC16_to_SC12', 'SC12_to_SC6'):
                count = Counter()
                for r in rows:
                    if r['target']=='storage:'+origin and r['source']!=r['target']:
                        count[r['source'] or r['route_key']] += r['vehicles']
                incoming[origin] = dict(count)
            blocks.append(dict(start_sec=start,heads=heads,incoming=incoming))
        arms[arm] = blocks
    prior = read(A.parent/'sc109_service/assessment.json')
    for name in ['sc109_service/README.md','sc16_supply/README.md','sc12_source/README.md']:
        pin(A.parent/name)
    for name in ['diag_c3_r2/U7.md','diag_c3/C3_DIAGNOSIS.md','impl/STAGE3.md']:
        pin(A.parent.parent/'upstream_worklog/02_urban_b2'/name)
    pin(Path(__file__))
    result = dict(status='complete_closed_upstream_request_supply_audit',arms=arms,
        prior_sc109=dict(assessment_status=prior['status'],head_departures=prior['head_departures']),
        limitations=[
            'Native signal-head departures precede connector boundaries; phase-head totals may include competing turns.',
            'No rejection of requested flow does not prove adequate upstream supply.',
            'All-ready-requested identifies a local supply limit only during a positive service request.',
            'Past SC109 resource improved training discharge but overestimated the old3300 state; it remains unqualified.',
            'Native future arrivals/counts are diagnostic outcomes, never prediction inputs.'
        ],budget=dict(new_forecasts=0,new_native=0,fzp_scans=0,new_fits=0),source_pins=PINS)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    for arm, blocks in arms.items():
        print(arm, json.dumps([dict(start=b['start_sec'],heads=b['heads']) for b in blocks]))


if __name__ == '__main__':
    main()
