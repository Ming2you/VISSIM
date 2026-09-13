"""Compare existing JSON receipts only; no model imports or trajectory access."""
from pathlib import Path
import hashlib
import json
import math

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
pins = {}


def read(name):
    path = D/name
    assert path.suffix == '.json'
    content = path.read_bytes()
    pins[str(path.relative_to(ROOT)).replace('\\','/')] = hashlib.sha256(content).hexdigest()
    return json.loads(content.decode('utf-8-sig'))


def errors(actual, predicted):
    assert len(actual) == len(predicted) and actual
    residual = [p-a for a,p in zip(actual,predicted)]
    return {'n':len(actual), 'native_total':math.fsum(actual), 'model_total':math.fsum(predicted),
        'total_bias':math.fsum(residual), 'mean_bias':math.fsum(residual)/len(actual),
        'MAE':math.fsum(abs(v) for v in residual)/len(actual)}


names = {'legacy':'open1350_model450_v1.json',
         'sc1005_unsignalized_only':'sc1005_bypass_config_model450_v1.json',
         'route_inventory':'fidelity_routes_recorded900_v1.json'}
models = {name:read(path) for name,path in names.items()}
native = read('open1350_area450_v1/boundary_metrics.json')
off = read('offramp_eight_branches_450_v1.json')
merge = read('ramp_merge_three_windows_v1.json')
native_merge_receipt = read('open1350_ramp450_v1.json')
identity = read('open1350_model_native_comparison_v1.json')
commands = read('open1350_preflight_command_equality_v1.json')
legacy_windows = read('open1350_ttd_windows_v1.json')
windows_proof = read('ttd_windows_qualification_v1.json')
unsignalized_proof = read('sc1005_bypass_config_parity_v1.json')
capacity = read('sc1005_service_capacity_origin_v1.json')
legacy = models['legacy']
arms = {name:record['arms']['open'] for name,record in models.items()}
assert native['completed'] and native['window_sec'] == [900,1350]
assert off['completed'] and off['window_sec'] == [900,1350]
assert merge['completed'] and merge['windows_sec'] == [[900,1050],[1050,1200],[1200,1350]]
assert native_merge_receipt['analysis_window_sec'] == [900,1350]
assert identity['completed'] and identity['state900_observation_values_exact']
assert commands['passed'] and commands['rows'] == [213,213]
assert all(row['rows_exact'] == 213 for row in identity['held_physical_commands'])
assert windows_proof['full_response_sha256_exact']
assert legacy_windows['arms']['open']['response_sha256'] == arms['legacy']['response_sha256']
assert all(unsignalized_proof['checks'].values())
input_fields = ('state_000900.json','action_000750.json','action_000900.json','action_000900.csv')
def input_pins(record):
    rows = {path.replace('\\','/').split('/')[-1]:token for path,token in record['source_sha256'].items()
            if path.replace('\\','/').split('/')[-1] in input_fields}
    assert set(rows) == set(input_fields)
    return rows
for name,record in models.items():
    assert record['complete'] and not record['native_run'] and record['source_changes'] == []
    assert record['initial_inventory'] == legacy['initial_inventory']
    assert record['initial_ramp_stocks'] == legacy['initial_ramp_stocks']
    assert record['forecast_sha256'] == legacy['forecast_sha256']
    assert record['native_reference_meter_commands_exact']
    assert arms[name]['physical_commands'] == arms['legacy']['physical_commands']
    assert input_pins(record) == input_pins(legacy)
    assert arms[name]['model_coverage']['complete'] and not arms[name]['model_coverage']['missing_constraints']
    assert (arms[name]['predicted_merge_450']['start_sec'],arms[name]['predicted_merge_450']['end_sec']) == (900,1350)
assert set(native['terminal_inferred_by_link']) == {'120','24'}
assert native['TD'] == native['observed_exit_events'] + native['terminal_exit_inferred_events']
assert math.fsum(native['terminal_inferred_by_link'].values()) == native['terminal_exit_inferred_events']

terminal_rows = [{'freeway':fw,'native_terminal_link':link,'native_veh':native['terminal_inferred_by_link'][link],
    'model_veh':{name:arm['area']['flow_counts']['freeway:'+fw+'->external:terminal:'+fw] for name,arm in arms.items()}}
    for fw,link in (('FW_W','120'),('FW_E','24'))]
off_rows = []
for row in off['rows']:
    key = 'offramp_'+row['branch']+':'+row['group']
    values = {name:arm['area']['flow_counts'][key] for name,arm in arms.items()}
    assert values['legacy'] == row['model_accepted_entry_veh']
    off_rows.append({k:row[k] for k in ('group','branch','connector','native_source_mainline','inside_omega')} |
        {'boundary':'native mainline -> branch connector entry; model accepted branch landing',
         'native_veh':row['native_entry_veh'],'model_veh':values,
         'bias_veh':{name:value-row['native_entry_veh'] for name,value in values.items()}})
merge_rows = []
for row in merge['rows']:
    key = 'RM_C'+str(row['connector'])
    actual = math.fsum(row['native_merges150'])
    values = {name:arm['predicted_merge_450']['accepted_vehicles_by_ramp'][key] for name,arm in arms.items()}
    for name,label in (('legacy','original'),('sc1005_unsignalized_only','sc1005_unsignalized_only')):
        assert math.isclose(values[name],math.fsum(row['model_merges150'][label]),abs_tol=1e-9)
    merge_rows.append({'ramp':key,'connector':row['connector'],'boundary':'ramp connector -> mainline; accepted merge',
        'native_veh':actual,'model_veh':values,'bias_veh':{name:value-actual for name,value in values.items()}})
assert math.fsum(r['native_veh'] for r in off_rows) == 790
assert math.fsum(r['native_veh'] for r in merge_rows) == merge['native_total_450'] == 301

comparison = {}
for name,arm in arms.items():
    terminal = math.fsum(row['model_veh'][name] for row in terminal_rows)
    comparison[name] = {
        'TTT_veh_h':errors([native['TTT_veh_h']],[arm['area']['ttt_veh_h']]),
        'TD_veh':errors([native['TD']],[arm['area']['ttd_veh']]),
        'terminal_veh':errors([r['native_veh'] for r in terminal_rows],[r['model_veh'][name] for r in terminal_rows]),
        'live_external_TD_veh':errors([native['observed_exit_events']],[arm['area']['ttd_veh']-terminal]),
        'offramp_8_entry_veh':errors([r['native_veh'] for r in off_rows],[r['model_veh'][name] for r in off_rows]),
        'ramp_8_merge_veh':errors([r['native_veh'] for r in merge_rows],[r['model_veh'][name] for r in merge_rows])}

windows = []
for i,(start,end) in enumerate(merge['windows_sec']):
    physical = [r for r in native['time_rows'] if start < r['sim_sec'] <= end]
    assert len(physical) == end-start
    actual_terminal = sum(r['terminal_exit_inferred_events'] for r in physical)
    actual_live = sum(r['observed_exit_events'] for r in physical)
    values = {}
    for name,record in (('legacy',legacy_windows),('route_inventory',models['route_inventory'])):
        row = record['arms']['open']['ttd_150_windows'][i]
        assert (row['start_sec'],row['end_sec']) == (start,end)
        terminal = math.fsum(v for k,v in row['by_route'].items() if k.startswith('freeway:') and 'external:terminal:' in k)
        total = math.fsum(row['by_route'].values())
        values[name] = {'TD_veh':total,'terminal_veh':terminal,'live_external_TD_veh':total-terminal}
    windows.append({'start_sec':start,'end_sec':end,'native':{'TD_veh':actual_terminal+actual_live,
        'terminal_veh':actual_terminal,'live_external_TD_veh':actual_live},'models':values})
window_errors = {name:{metric:errors([r['native'][metric] for r in windows],
    [r['models'][name][metric] for r in windows]) for metric in ('TD_veh','terminal_veh','live_external_TD_veh')}
    for name in ('legacy','route_inventory')}
for name in window_errors:
    for metric in window_errors[name]:
        assert math.isclose(window_errors[name][metric]['model_total'],comparison[name][metric]['model_total'],abs_tol=1e-7)
        assert window_errors[name][metric]['native_total'] == comparison[name][metric]['native_total']

result = {'schema':'offramp-fidelity-existing-json-comparison/v1','complete':True,
    'new_model_queries':0,'new_native_runs':0,'new_fzp_reads':0,'window_sec':[900,1350],
    'scope':'One held-command forecast from the same recorded900 observation; cached completed native1350 baseline. Prediction correction, not closed-loop controller benefit or runtime benchmark.',
    'identity_checks':{'initial_inventory_exact_between_models':True,'initial_ramp_stocks_exact':True,
        'forecast_sha256':legacy['forecast_sha256'],'source_state_and_action_pins_exact':input_pins(legacy),
        'physical_meter_commands_exact_between_models':True,'native_command_rows_exact':213,
        'native_control_metadata_column_excluded':True,'native_state900_observation_values_exact_cached_proof':True,
        'native_state_identity_exclusions':identity['state_identity_exclusions'],
        'initial_omega_stock_existing_model_vs_native':identity['initial_omega_stock']},
    'metric_grain':{'TTT_veh_h':'one450s window; veh*h; MAE=absolute aggregate bias',
        'TD_veh':'one450s window; Omega outward crossings including qualified inferred terminal exits; MAE=absolute aggregate bias',
        'terminal_veh':'two freeway terminal links120/24 over450s; MAE over2 directions',
        'live_external_TD_veh':'one450s total of live Omega outward crossings; model TD minus terminal; MAE=absolute aggregate bias, not per-link error',
        'offramp_8_entry_veh':'8 physical mainline-to-offramp entries over450s; MAE over8 branches',
        'ramp_8_merge_veh':'8 physical ramp-to-mainline accepted merges over450s; MAE over8 ramps'},
    'comparisons':comparison,'terminal_rows':terminal_rows,'offramp_rows':off_rows,'merge_rows':merge_rows,
    'adjacent150_windows':windows,'adjacent150_MAE_and_bias':window_errors,
    'adjacent150_scope':'Three adjacent bins of the same held450 forecast; not three independently initialized forecasts. SC1005-only full window bins were not stored and are not inferred.',
    'model_coverage':{name:arm['model_coverage'] for name,arm in arms.items()},
    'headfree_initial_capacity':{'movement':capacity['movement'],
        'legacy_effective_capacity_veh_h':capacity['observed_effective_movement']['capacity_veh_h'],
        'new312_floor_active_in_this_rollout':False,
        'reason':'The reused900 snapshot has the legacy prior without a qualified head-free floor. The current rollout retains206.53061224489795veh/h; the separate312 lower-bound diagnostic is not credited here.'},
    'findings':['Offramp8 MAE improves48.4068596252 ->25.9555716486veh; both native and model measure accepted mainline-to-branch entries, not desired routing demand.',
        'Terminal total and live external TD each move toward native totals. Their opposite signed biases cancel less, so aggregate TD error worsens419.6259523899 ->426.1666049618veh.',
        'Merge total deficit narrows, but8-ramp MAE worsens10.9173508573 ->10.9783743329veh; connector10484 overprediction increases.',
        'The combined route model also includes the adopted SC1005 unsignalized correction; the intermediate SC1005-only receipt is retained for separation.',
        'TTT bias falls24.5333170101 ->21.3419538561veh*h, but overall native fidelity and controller benefit are not established.'],
    'caveats':{'native_TD_requires_review':native['TD_requires_review'],
        'unresolved_native_inside_disappearances_excluded_from_TD':native['unresolved_inside_disappearances'],
        'native_stock_closure':native['closure'],
        'nonadditive_metrics':'Eight off-ramp entries and eight merges must not be added to TD. Only westbound direct off-ramp entries are Omega exits at the branch itself; live TD also contains other city crossings.',
        'routing_resolution':'21-cell proportional mixing with corrected8 source cells; no exact sub-cell travel or vehicle lane behavior claim.',
        'saturation_capacity_identified':False,'full_native_fidelity_certified':False,'GNE_certified':False,
        'timing_comparison':'No runtime/speed conclusion is drawn from these differently instrumented receipts.'},
    'source_receipts_sha256':pins,
    'analysis_code':{'path':str(Path(__file__).relative_to(ROOT)).replace('\\','/'),
        'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
result['source_receipts_unchanged'] = all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==token for path,token in pins.items())
assert result['source_receipts_unchanged']
target=D/'fidelity_routes_comparison_v1.json'
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
columns=list(names)
labels={'TTT_veh_h':'TTT (veh*h)','TD_veh':'TD (veh)','terminal_veh':'Terminal exits (veh)',
        'live_external_TD_veh':'Live Omega exits (veh)','offramp_8_entry_veh':'8 off-ramp entries (veh)','ramp_8_merge_veh':'8 ramp merges (veh)'}
lines=['# Recorded900 held450 fidelity comparison','',
    'Window 900–1350; stored JSON only. Same initial model inventory, forecast hash and held physical commands. This is prediction validation, not closed-loop control benefit.','',
    '| Metric | Native | Legacy | SC1005 unsignalized only | Route inventory |','|---|---:|---:|---:|---:|']
for metric,label in labels.items():
    lines.append('| '+label+' | '+f"{comparison['legacy'][metric]['native_total']:.3f}"+' | '+' | '.join(f"{comparison[name][metric]['model_total']:.3f}" for name in columns)+' |')
lines += ['', '| Error grain | Legacy MAE | SC1005 only MAE | Route inventory MAE |','|---|---:|---:|---:|']
for metric,label in [('terminal_veh','2 terminal directions'),('offramp_8_entry_veh','8 off-ramp branches'),('ramp_8_merge_veh','8 ramp merges')]:
    lines.append('| '+label+' | '+' | '.join(f"{comparison[name][metric]['MAE']:.3f}" for name in columns)+' |')
lines += ['', 'Off-ramp and terminal errors decrease. Aggregate TD absolute bias increases 419.626→426.167 veh; 8-ramp MAE increases 10.917→10.978 veh despite a smaller total merge deficit. Model TTT remains 21.342 veh*h above native.',
    '', 'The legacy 900 input has no qualified head-free floor. This rollout retains 206.531 veh/h; 312 veh/h was not active here.',
    '', 'Native TD 1558 retains its existing review flag; 12 unresolved inside disappearances are excluded. Model/native initial Omega stocks are 1033/1034. The 8 off-ramp and 8 merge rows are separate physical boundaries and must not be added to TD.',
    '', 'Source SHA256s, identity checks, per-branch errors and adjacent150s terminal/live bins are in [fidelity_routes_comparison_v1.json](fidelity_routes_comparison_v1.json). No new model, native or FZP work was performed.','']
(D/'fidelity_routes_comparison_v1.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'complete':True,'source_receipts':len(pins),'comparison':comparison},ensure_ascii=True))
