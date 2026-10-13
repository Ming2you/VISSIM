"""Scope for existing native joint minus city-only; no traffic scans."""
from pathlib import Path
import hashlib,json
from diagnostics.repin_v3c3_review_20261001.urban_rm269.qualify_native2400 import validate_scope

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
BASE=Path('E:/VISSIM_analysis/20261010_native_routes329/forecast2400')
NATIVE_CITY=Path('E:/VISSIM_analysis/20261010_urbanrm269_cityonly289')
RUNS={'joint':Path('E:/VISSIM_runs/20261008_urbanrm269_native2400_s29/selected/decisions_sdmpc31_g_2400_selected_s29'),
       'city':Path('E:/VISSIM_runs/20261010_urbanrm269_cityonly289_s29/selected/decisions_sdmpc31_g_2400_selected_s29')}
COMMANDS={'joint':H/'selection2400_discrete/selected','city':A/'citysplit287/forecast2400/city_only',
          'hold':H/'selection2400_discrete/hold'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())

def validate_commands(joint,city):
    for field in ('green_times','offsets','vsl','inflow_outflow_allocation','N_P_star','N_UF_star'):
        if joint[field]!=city[field]:raise ValueError('Not an RM-only contrast: '+field)
    if set(joint['ramp_metering'])!=set(city['ramp_metering']):raise ValueError('Ramp catalog differs')
    changed=[r for r in joint['ramp_metering'] if joint['ramp_metering'][r]!=city['ramp_metering'][r]]
    if not changed:raise ValueError('No RM intervention')
    return changed

def preflight():
    pins={}
    def load(p):pins[str(p)]=sha(p);return read(p)
    prior=load(BASE/'summary.json')
    assert prior['status']=='complete' and prior['start_sec']==2400 and prior['end_sec']==2850
    for p,h in prior['source_pins'].items():assert sha(p)==h,p
    pins.update(prior['source_pins'])
    city=load(NATIVE_CITY/'cached_summary.json')
    joint=load(H/'native2400_analysis/summary.json')
    qualification=load(H/'native2400_analysis/observed_input_qualification.json')
    valid=validate_scope(joint,qualification)
    assert city['counterfactual_valid'] and city['paired_prefix_exact'] and city['common_start_vehicle_records_exact']
    assert (city['start_sec'],city['end_sec'])==(2400,2850)
    assert city['physical_area']['membership_sha256']==joint['physical_area']['sha256']
    prefix=load(NATIVE_CITY/'cached_prefix_qualification.json')
    assert prefix['selected_prefix']==joint['prefixes']['selected']==joint['prefixes']['hold']
    checks=[]
    for at in (2400,2550,2700):
        commands={}
        for arm in ('joint','city'):
            p=COMMANDS[arm]/f'action_{at:06}.json';n=RUNS[arm]/p.name
            commands[arm]=load(p);load(n);assert sha(p)==sha(n),'Prediction command differs from native execution'
        changes=validate_commands(commands['joint'],commands['city'])
        checks.append(dict(start_sec=at,changed_ramps=changes,
            green_seconds={arm:{r:d['diagnostics']['rw_meter_green_'+r] for r in d['ramp_metering']} for arm,d in commands.items()}))
    start=[load(p/'state_002400.json') for p in RUNS.values()]
    assert start[0]['vehicle_records']['complete'] and start[1]['vehicle_records']['complete']
    assert start[0]['vehicle_records']['records']==start[1]['vehicle_records']['records']
    assert city['arms']['hold']['TTT_0_2850_veh_h']==joint['arms']['hold']['TTT_0_2850_veh_h']
    return dict(status='scope_verified',scope=valid,whole_RM_vector_not_single10681=True,
        native_delta_omega_veh_h=joint['delta_TTT_veh_h']-city['delta_TTT_veh_h'],
        model_source_initial_reconstruction='Same pinned bootstrap/current observations/forecast and initial application reports as329; previous microscopic replay failure remains recorded.',
        baseline_qualification='Matched observed forecast inputs; original microscopic older-history bit-exact replay failed',
        command_checks=checks,source_pins=pins,extra_native=0,extra_traffic_scans=0)

