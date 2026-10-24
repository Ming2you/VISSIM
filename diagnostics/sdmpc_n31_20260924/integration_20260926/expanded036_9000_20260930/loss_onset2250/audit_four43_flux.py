"""Conservative accounting of existing native30s flows and saved450s responses."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

L = Path(__file__).resolve().parent
I = L.parent.parent
O = L / 'physical_speed/four43/flux'
O.mkdir(exist_ok=False)
pins = {}


def read(path):
    raw = path.read_bytes()
    pins[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
    return raw


def load(path):
    raw = read(path)
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def rows(path):
    return list(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))


def close(a, b):
    assert abs(a-b) < 1e-7, (a, b)


comparison = load(I / 'seed43_fullplant_20260929/comparison.json')
native_decomposition = load(I / 'seed43_fullplant_20260929/decomposition.json')
arms = ('nc', 'rm', 'vsl', 'both')
folders = {}
for name in comparison['source_pins']:
    path = Path(name)
    if path.name == 'ports_30s.csv':
        folders['nc' if path.parent.name == 'none' else path.parent.name] = path.parent
assert set(folders) == set(arms)
signs = dict(source_admissions=1, ramp_merges=1, off_departures=-1,
    terminal_exits_inferred=-1, unexplained_entries=1, unexplained_losses=-1, native_removals=-1)
flows = {}
ports = {}
native = {}
bins = []
for arm in arms:
    folder = folders[arm]
    manifest = load(folder/'manifest.json')
    flows[arm] = {(float(r['window_start_s']), int(r['cell'])): r for r in rows(folder/'flows_30s.csv')
        if r['road'] == 'FW_E' and 2250 < float(r['window_start_s']) < 2700}
    ports[arm] = [r for r in rows(folder/'ports_30s.csv') if r['kind'] == 'ramp'
        and r['connector'] == '10484' and 2250 < float(r['window_start_s']) < 2700]
    if 'files' in manifest:
        for name in ('flows_30s.csv', 'ports_30s.csv'):
            assert pins[str((folder/name).resolve())] == manifest['files'][name]
    assert len(flows[arm]) == 31*15 and len(ports[arm]) == 15
    assert flows[arm].keys() == flows['nc'].keys()
    for key, row in flows[arm].items():
        assert float(row['conservation_residual_veh']) == 0
        net = sum(s*float(row[k]) for k,s in signs.items())
        net += float(row['upstream_crossings']) - float(row['downstream_crossings'])
        close(float(row['end_n_veh']) - float(row['start_n_veh']), net)
        if abs(key[0]-2250.1) < 1e-7:
            close(float(row['start_n_veh']), float(flows['nc'][key]['start_n_veh']))
    terms = {k:0. for k in signs}
    totals = {k:0. for k in signs}
    cells = {k:0. for k in range(31)}
    for key, row in flows[arm].items():
        base = flows['nc'][key]
        midpoint = (float(row['window_start_s'])+float(row['window_end_s']))/2
        for k, sign in signs.items():
            delta = float(row[k])-float(base[k])
            totals[k] += delta
            terms[k] += sign*delta*(2700.1-midpoint)/3600
        cells[key[1]] += (float(row['start_n_veh'])+float(row['end_n_veh'])
            -float(base['start_n_veh'])-float(base['end_n_veh']))*15/3600
    close(sum(terms.values()), sum(cells.values()))
    close(sum(cells.values()), native_decomposition['arms'][arm]['delta_native_30s_veh_h']['FW_E'])
    first = next((key[0] for key in sorted(flows[arm]) if key[1] == 0
        and flows[arm][key]['source_admissions'] != flows['nc'][key]['source_admissions']), None)
    native[arm] = dict(delta_counts=totals, weighted_TTT_delta_terms=terms,
        cell_TTT_delta=cells, east_TTT_delta=sum(cells.values()), first_different_source_bin_start=first,
        remainder_after_source_bookkeeping=sum(terms.values())-terms['source_admissions'])
    for t in sorted({key[0] for key in flows[arm]}):
        block = [flows[arm][t, cell] for cell in range(31)]
        base = [flows['nc'][t, cell] for cell in range(31)]
        close(sum(float(r['upstream_crossings'])-float(r['downstream_crossings']) for r in block), 0)
        row = dict(arm=arm,start_sec=t,end_sec=t+30)
        for k in signs:
            row[k] = sum(float(r[k]) for r in block)
            row['delta_'+k] = sum(float(r[k])-float(b[k]) for r,b in zip(block,base))
        for r in block:
            close(float(r['source_admissions']), float(r['source_first_appearances'])+float(r['source_reappearances']))
            assert float(r['source_reappearances']) == 0
        bins.append(row)

models = {}
timing = []
for model in ('before', 'after'):
    folder = I / f'closedloop_recorded2250_lever450_trace10484_physical_speed_{model}_s43_20261001'
    result = {}
    for arm in arms:
        key = 'held_actual' if arm == 'nc' else arm
        r = load(folder/f'{key}.json')
        trace = load(folder/f'{key}_RM_C10484_trace.json.gz')
        assert not trace['future_observation_inputs']
        result[arm] = r
        for index, native_port in enumerate(ports[arm]):
            start = 2250+30*index
            transfers = [r for r in trace['transfers'] if start <= r['start_sec'] < start+30]
            arrival = sum(r['vehicles'] for r in transfers if r['target'] == 'ramp:RM_C10484')
            merge = sum(r['vehicles'] for r in transfers if r['source'] == 'ramp:RM_C10484' and r['target'] == 'merge_pending:RM_C10484')
            head = sum(r['accepted_total_veh'] for r in trace['resources']
                if r['kind'] == 'physical_ramp_head_service' and start <= r['start_sec'] < start+30)
            timing.append(dict(model=model,arm=arm,start_sec=start,native_start_sec=float(native_port['window_start_s']),
                native_arrival=float(native_port['arrivals_veh']),native_merge=float(native_port['departures_veh']),
                native_start_stock=float(native_port['start_n_veh']),native_end_stock=float(native_port['end_n_veh']),
                model_arrival=arrival,model_head=head,model_merge=merge))
        chosen = [row for row in timing if row['model']==model and row['arm']==arm]
        for k in ('arrival','merge'):
            close(sum(row['model_'+k] for row in chosen), r['ramps']['RM_C10484'][k])
        # This native profile controls four east ramps, not only10484.
        for index, command in enumerate(r['commands']):
            for ramp, green in command['meters'].items():
                expected = 8-2*index if arm in ('rm','both') and ramp in ('RM_C10639','RM_C10681','RM_C10490','RM_C10484') else 10
                close(green, expected)
    delta = {}
    for arm,r in result.items():
        flow = r['control_area']['flow_counts']; base = result['nc']['control_area']['flow_counts']
        delta[arm] = dict(east_TTT=r['cost_by_stock']['freeway:FW_E']-result['nc']['cost_by_stock']['freeway:FW_E'],
            boundaries={k:flow[k]-base.get(k,0) for k in flow if 'freeway:FW_E' in k})
    models[model] = delta

for name, values in (('native_flow_30s.csv',bins),('ramp10484_timing_30s.csv',timing)):
    with (O/name).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
report=dict(status='complete_accounting_not_causal_identification',native=native,models=models,
    verified_native_cell_windows=4*31*15,verified_ramp_model_windows=2*4*15,
    new_forecasts=0,new_native=0,fzp_scans=0,fit=0,source_pins=pins,
    limitations=['Weighted terms exactly explain30s trapezoidal inventory differences, not causal shares.',
        'Subtracting the source term is bookkeeping only, not the response under identical future inflow.',
        'Initial source and commanded input settings match; later inserted vehicles do not. Stochastic generation versus insertion accessibility remains unseparated.',
        'Native10484 flows come from cached trajectory cohort transitions; model head release is a different cross-section from merge.',
        'Current seed43 RM changes all four east ramps. Existingseed47 strong comparison changes only10484.',
        'Earlier source_response_separation_20260929 already established conditional sensitivity; do not repeat or relabel it as a new autonomous success.'])
(O/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({a:{k:native[a][k] for k in ('delta_counts','weighted_TTT_delta_terms','first_different_source_bin_start')} for a in arms},indent=2))
