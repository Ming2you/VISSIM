"""Freeze the new geometry and DSD network for native four-arm rule runs."""
import csv
import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from diagnostics.fast_nc_prepare import prepare_native_preserve
from diagnostics.fast_fixed_profile import prepare
from diagnostics.rule_baseline_20260914.instrument_network import build_mapping, instrument_network


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--terminal-sec',type=int,choices=(1050,3000,4500,5400,7200,9000),default=3000)
    parser.add_argument('--seed',type=int,default=13)
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--network',type=Path,help='Explicit saved network; preserve its demand, paths and geometry')
    parser.add_argument('--arms',nargs='+',choices=('none','rm','vsl','both'),default=['none','rm','vsl','both'])
    parser.add_argument('--mpc-model',type=Path)
    parser.add_argument('--recording-interval-sec',type=int,choices=(1,5),default=5)
    parser.add_argument('--plant-step-sec',type=int,choices=(1,5),default=5)
    args=parser.parse_args()
    terminal=args.terminal_sec
    here = Path(__file__).resolve().parent
    destination = args.destination or here/('rules_v1' if terminal==3000 else 'rules_4500_v1')
    if destination.exists(): raise FileExistsError(destination)
    source = args.network.resolve() if args.network else here/'source_dsd/baseline.inpx'
    original = source.read_bytes()
    if args.seed<=0:raise ValueError('Seed must be positive')
    old_seed=int(ET.fromstring(original).find('simulation').get('randSeed'))
    if args.seed!=old_seed:
        original,n=re.subn(rb'(<simulation\b[^>]*\brandSeed=")[0-9]+',
            lambda m:m[1]+str(args.seed).encode('ascii'),original)
        if n!=1:raise ValueError('Expected exactly one simulation seed attribute')
    mapping = json.loads((ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json').read_text())
    base = json.loads((ROOT/'diagnostics/rule_baseline_20260914/config_both_v2.json').read_text())
    declaration = build_mapping(original, mapping)
    native = ET.fromstring(original)
    groups = {int(sc.get('no')): [int(sg.get('no')) for sg in sc.findall('./sgs/signalGroup')]
              for sc in native.findall('./signalControllers/signalController')}
    instrumented = instrument_network(original, groups, declaration)
    prepare_native_preserve(source.resolve(), destination/'source', terminal)
    net = destination/'source/network/baseline.inpx'
    net.write_bytes(instrumented)
    # source/ is preparation only; remove its superseded receipt to avoid implying
    # that the uninstrumented SHA describes the new bytes.
    (destination/'source/prepared.json').unlink()
    (destination/'source/native_simulation.csv').unlink()
    settings = base['actuation']['real_world_ramp_metering']
    rule = base['diagnostic']['rule_profile']
    rule.update(reference_speed_kph=120)
    rule['vsl_rule']['speed_commands_kph'] = [60,80,120]
    for key in ('detector_mapping_json','detector_mapping_sha256'): rule.pop(key, None)
    meters = {}
    for meter in mapping['ramp_meters']:
        mid = meter['id']
        heads = native.findall(f"./signalHeads/signalHead[@sg='{meter['sc_no']} 1']")
        lanes = len({h.get('lane') for h in heads})
        if lanes != settings['meter_lanes'].get(mid, 1): raise ValueError('Meter lane count differs')
        meters[mid] = {'sc':meter['sc_no'], 'connector':meter['connector'],
            'table':{'0':0, **{g:lanes*n*360 for g,n in settings['per_lane_veh_per_cycle'].items()}}}
    zones = {}
    for segment in mapping['segments']:
        if not segment.get('dsds'): continue
        head = max(h for h in (0,5,10,15) if h <= segment['model_segment_index'])
        zones.setdefault(f"{segment['model_link']}__seg{head}", []).extend(d['dsd_no'] for d in segment['dsds'])
    dsds = {int(n.get('no')):n for n in native.findall('./desSpeedDecisions/desSpeedDecision')}
    for no in [n for values in zones.values() for n in values]:
        if any(int(v.get('desSpeedDistr')) != 120 for v in dsds[no].findall('./vehClassDesSpeedDistr/vehClassDesSpeedDistribution')):
            raise ValueError('All controlled mainline DSDs must initially be120')
    for arm in args.arms:
        profile = {'schema':'native-fixed-profile/v1','network_sha256':hashlib.sha256(instrumented).hexdigest(),
            'seed':args.seed,'control_start_sec':900,'terminal_sec':terminal,'vsl_commands':[], 'meter_commands':[],
            'native_off_service_anchor_green_sec':10,'vehicle_record_interval_sec':args.recording_interval_sec}
        if int(native.find('simulation').get('simRes')) != 1:
            profile['native_resolution_probe'] = int(native.find('simulation').get('simRes'))
        profile_path=destination/f'{arm}.json'; profile_path.write_text(json.dumps(profile))
        prepared=destination/f'prepared_{arm}'
        meta=prepare(net.resolve(),profile_path,prepared)
        policy={'rule':{**rule,'arm':arm}, 'meters':meters, 'zone_dsds':zones, 'detectors':declaration,
            'minimum_green':settings['min_green_sec'], 'max_green_change':2,
            'source_sha256':hashlib.sha256(original).hexdigest(),
            'scope':'Native feedback policy only; no MPC plant initialization or forecast claim. Native OFF retained until RM activation. Distribution IDs are not fixed vehicle speeds.'}
        (prepared/'rule_policy.json').write_text(json.dumps(policy,indent=2),encoding='utf-8')
        (prepared/'rule_runtime.txt').write_text(str(Path(sys.executable))+'\n'+str(ROOT/'diagnostics/fast_fixed_profile.py')+'\n900\n',encoding='utf-16')
        with (prepared/'rule_measurements.csv').open('w',newline='',encoding='ascii') as f:
            w=csv.writer(f);w.writerow(['measurement']); w.writerows([i] for s in declaration['stations'] for i in s['measurement_ids'])
        for name in ('rule_policy.json','rule_runtime.txt','rule_measurements.csv'):
            meta['snapshot_sha256'][str((prepared/name).resolve())]=hashlib.sha256((prepared/name).read_bytes()).hexdigest()
        if args.mpc_model:
            model=args.mpc_model.resolve()
            model_config=json.loads((model/'config.json').read_text(encoding='utf-8-sig'))
            model_config['freeway']['physical_integration_step_sec']=args.plant_step_sec
            config_path=prepared/'mpc_model_config.json'
            config_path.write_text(json.dumps(model_config,indent=2),encoding='utf-8')
            files={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                (model/'config.json',config_path,model/'selected_parameters.json',model/'port_profile.json',
                 here/'evaluate_response.py',ROOT/'evaluation/controllers/physical_ramp_boundary.py',
                 ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/extract_observations.py',
                 ROOT/'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py')}
            contract={'model_directory':str(model),'model_pins':files,
                'model_config':str(config_path.resolve()),'plant_step_sec':args.plant_step_sec,
                'observation_interval_sec':args.recording_interval_sec,
                'geometry':str((model.parent/'none/geometry.json').resolve()),
                'scope':'Centralized diagnostic RM/VSL MPC, 450s prediction and150s update; not full GNE or full urban Omega objective',
                'objective':'Mainline+on/off connector residence plus predicted unadmitted source/ramp waiting; unit vehicle-time weights',
                'candidate_budget':24,'soft_budget_sec':60,
                'candidate_commands':'Three150s moves in each candidate direction; apply only first150s, +/-2s meter and +/-20 VSL per update',
                'physical_constraints':'RG10s; min2 max10; real DSD support; local conservation/storage; NP/NUF game constraints not imposed'}
            (prepared/'mpc_policy.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
            meta['snapshot_sha256'][str((prepared/'mpc_policy.json').resolve())]=hashlib.sha256((prepared/'mpc_policy.json').read_bytes()).hexdigest()
            meta['snapshot_sha256'].update(files)
        meta['rule_policy']=policy['rule']
        (prepared/'prepared.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    (destination/'detector_mapping.json').write_text(json.dumps(declaration,indent=2),encoding='utf-8')
    (destination/'README.md').write_text(f'New ramp geometry + DSD120. Same native demand, seed{args.seed}, SimPeriod9001, stop{terminal}.\n'
        f'Native recording every{args.recording_interval_sec}s; MPC mainline integration{args.plant_step_sec}s when enabled. SimRes and actuator event clock unchanged.\n'
        'Four arms: native none / ALINEA / rule VSL / both. Control starts900, interval150.\n'
        'ALINEA target15pct; gain70veh/h/pct/lane; RG10s, max green change2s. VSL thresholds1600veh/h/lane,15pct,60/80km/h; commands60/80/120.\n'
        'Only recording/detectors added to immutable source; reversible byte edit validation passed. No forecast or full GNE certification.\n',encoding='utf-8')
    names=['diagnostics/fast_nc_runner.vbs','diagnostics/fast_nc_run.ps1',
        'diagnostics/fast_fixed_profile.py','diagnostics/fast_fixed_profile_verify.py',
        'evaluation/controllers/diagnostic_profile.py']
    (destination/'code_pins.json').write_text(json.dumps({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names},indent=2),encoding='utf-8')
    (destination/'seed_provenance.json').write_text(json.dumps({'source_seed':old_seed,'run_seed':args.seed,
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'seed_adjusted_source_sha256':hashlib.sha256(original).hexdigest(),
        'only_physical_source_edit':'simulation.randSeed'},indent=2),encoding='utf-8')
    print(destination)


if __name__ == '__main__': main()
