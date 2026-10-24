"""Read-only source/mapping probes for the 6056c94 review; no COM or adapter writes."""
from pathlib import Path
import csv, json, sys, importlib.util, collections, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import protected_ttt_from_fzp_20260828 as pt

def read_json(p):
    return json.loads((ROOT / p).read_text(encoding='utf-8'))

def csv_rows(p):
    with (ROOT / p).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(x for x in f if not x.startswith('#')))

cfg = read_json('evaluation/configs/n21_n7_20260908.json')
net = cfg['config_overrides']['network']
det = read_json(cfg['detector_mapping_json'])
terr_path = ROOT / 'outputs/urban_player_territory_v2_20260907.json'
sets = pt.link_sets(terr_path, ROOT / cfg['detector_mapping_json'])
union = sets['controlled'] | sets['freeway'] | sets['ramp']
terr = read_json('outputs/urban_player_territory_v2_20260907.json')['territory']
turns = read_json('outputs/pn_boundary_turns_v2_20260907.json')['turns']
roles = {x['no']: x for x in csv_rows('evaluation/real_world_modi_inventory/vehicle_input_roles.csv')}
gates = {x['no']: x for x in csv_rows('evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv')}
tree = ET.parse(ROOT / 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx')
out = {}
intervals = collections.defaultdict(lambda: collections.defaultdict(float))
for v in tree.findall('.//vehicleInput'):
    no, link = v.get('no'), v.get('link')
    role = roles.get(no, {}).get('role', '')
    factor = .8333 if role.startswith('freeway') else 1.
    for iv in v.findall('./timeIntVehVols/timeIntervalVehVolume'):
        val = float(iv.get('volume')) * factor
        k = iv.get('timeInt')
        intervals[k]['all_vph'] += val
        if role.startswith('freeway'):
            intervals[k]['fw_' + no] = val
        else:
            status = gates.get(no, {}).get('status', 'unmapped')
            intervals[k]['urban_' + status + '_vph'] += val
out['demand_intervals_scaled_from_inpx'] = dict(intervals)
out['gate_counts'] = dict(collections.Counter(x['status'] for x in gates.values()))
out['urban_demand_ignored_by_adapter_fields'] = ['urban_internal_volume_vph', 'urban_unmapped_volume_vph']
out['mapping_counts'] = {k: len(v) for k, v in sets.items()} | {'union_unique': len(union)}
out['legacy_sets_overlap'] = sorted(sets['freeway'] & sets['ramp'])
out['movement_observation_sc_counts'] = dict(collections.Counter({sc: len({r['movement'] for rs in det.get('link_to_movements', {}).values() for r in rs if r.get('movement','').startswith(sc+'_')}) for sc in terr['urban']}))
out['ramp_spillback_mapping'] = det.get('ramp_spillback_links', {})
in_keys = {k for k in net['urban_link_storage_veh'] if k.startswith('in_')}
out['in_storage'] = {'count': len(in_keys), 'origins': len({v.get('origin') for v in net['urban_movements'].values()} & in_keys), 'receivers': len({v.get('receiving_link') for v in net['urban_movements'].values()} & in_keys), 'boundary_seed_config': cfg.get('urban', {}).get('boundary', {})}
far_rows = csv_rows('evaluation/real_world_modi_inventory/far_measurement_links_20260901.csv')
far_links = {x['link'] for x in far_rows}
observed = {str(x) for a in det.get('agents',{}).values() for x in a.get('visible_links',[])}
out['offramp_connector_coverage'] = {k: {'far': k in far_links, 'observable_agent': k in observed, 'origins': det.get('link_to_origins',{}).get(k), 'movements': det.get('link_to_movements',{}).get(k), 'union': k in union} for k in ['10481','10483','10682','10643']}
out['physical_links_membership'] = {k: [zone for zone, ls in sets.items() if k in ls] for k in ['2','24','26','74','119','120','121','31','32','68','69','70','71','78','10479','10481','10483','10643','10682','10771','10772','10773']}
out['pn_boundary_turns_vs_union'] = collections.defaultdict(list)
for t in turns:
    if t.get('class') not in ('outflow','external'): continue
    key = ('in' if str(t['from_link']) in union else 'out') + '->' + ('in' if str(t['to_link']) in union else 'out')
    out['pn_boundary_turns_vs_union'][key].append({k:t.get(k) for k in ['class','sc','from_link','connector','to_link']})

# Actual adapter invocation verifies a known future value is not accepted and
# every forecast entry holds the current state rate, with shared identity.
sp = importlib.util.spec_from_file_location('review_vsa', ROOT / 'evaluation/controllers/vissim_stackelberg_adapter.py')
ad = importlib.util.module_from_spec(sp); sp.loader.exec_module(ad)
_, DemandStep, _, _, TrafficState, _ = ad.repo_imports(ROOT / 'vendor/NumSim-mine')
from types import SimpleNamespace
tiny = SimpleNamespace(network=SimpleNamespace(freeway_links=['FW_E','FW_W'], boundary_in_links=['in_A'], boundary_out_links=[], ramps=['R_D_W']))
forecast = ad.demand_from_state({'demand': {'urban_volume_vph_by_gate': {'in_A':100}, 'freeway_volume_vph':2000, 'ramp_volume_vph':0, 'future':{'freeway_volume_vph':4000}}}, tiny, DemandStep, 3)
out['forecast_probe'] = {'fw_rates':[x.freeway_mainline for x in forecast], 'same_object_all_steps': len({id(x) for x in forecast}) == 1}
ad.install_config_switches(cfg)
cal = ad.deep_update(read_json('evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'), cfg.get('calibration_override', {}))
runtime_cfg = ad.build_config(ROOT / 'vendor/NumSim-mine', 150, 5400, 'fast-smoke', cal, cfg, local_observation=True, flagship=True)
synthetic = {'sim_sec':900,'total_vehicles':20,'local_observation': {'link_counts':{'32':20},'link_stopped_counts':{'32':20},'link_speeds_kph':{'32':0}},'vehicle_records':{'records':[{'veh_no':i,'link_no':'32','lane_no':1,'position_m':500,'stopped':True} for i in range(20)]}}
summary = ad.build_local_observation_summary(synthetic, runtime_cfg, det, cal)
runtime_cfg.network.ramp_spillback_obs = False
summary_off = ad.build_local_observation_summary(synthetic, runtime_cfg, det, cal)
out['spillback_projection_probe'] = {label:{'urban_movement_queue_veh':sum(s['urban_movement_queue'].values()),'urban_storage_veh':sum(s['urban_link_storage_occupancy'].values()),'ramp_queue_veh':sum(s['ramp_queue'].values()),'spillback':s['ramp_spillback'],'projection_diagnostics':s['projection_diagnostics']} for label,s in [('on',summary),('off',summary_off)]}
on_stock = sum(summary['urban_movement_queue'].values()) + sum(summary['urban_link_storage_occupancy'].values()) + sum(summary['ramp_queue'].values())
off_stock = sum(summary_off['urban_movement_queue'].values()) + sum(summary_off['urban_link_storage_occupancy'].values()) + sum(summary_off['ramp_queue'].values())
assert on_stock == 40 and off_stock == 20
assert summary['projection_diagnostics']['mass_balance_error_veh'] == 0
out['spillback_projection_probe']['strict_mass_test'] = {'actual_vehicles':20,'model_stock_with_spillback':on_stock,'model_stock_without_spillback':off_stock,'existing_diagnostic_reports_error':0,'conservation_satisfied':False}
live_path = ROOT / 'evaluation/runs/codex_nc_s13_6056c94_20260909_retry/decisions_codex_nc_s13_6056c94_20260909_retry/state_000900.json'
if live_path.is_file():
    raw = json.loads(live_path.read_text(encoding='utf-8'))
    real = {}
    for enabled in [False,True]:
        runtime_cfg.network.ramp_spillback_obs = enabled
        s = ad.build_local_observation_summary(raw, runtime_cfg, det, cal)
        real[str(enabled)] = {'urban_movement_queue_veh':sum(s['urban_movement_queue'].values()),'urban_storage_veh':sum(s['urban_link_storage_occupancy'].values()),'ramp_queue_veh':sum(s['ramp_queue'].values()),'spillback':s['ramp_spillback'],'mass_balance_error_veh':s['projection_diagnostics']['mass_balance_error_veh']}
    out['real_900_spillback_probe'] = {'state_path':str(live_path.relative_to(ROOT)), 'demand':raw.get('demand'), 'detector_mapping':raw.get('local_observation',{}).get('detector_mapping_json'), 'landing_counts':{k:raw['local_observation']['link_counts'].get(k) for k in ['10481','10483','10682','10643','121','124']},'comparison':real}
out_path = ROOT / 'diagnostics/demand_observation_probe.json'
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(out, ensure_ascii=False, indent=2))
