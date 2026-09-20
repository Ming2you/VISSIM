"""Freeze a second development-seed RM response contrast; use existing runners."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import matched_meter_increment as m
from diagnostics.fast_fixed_profile import prepare

K = Path(__file__).resolve().parent
OUT = K/'matched_meter_midpoint_s33_v2'
BANK = K.parent/'state_response_20260919/native_s33_v1'
e = m.e


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=False)
    source = Path(e.load(BANK/'prepared_rm_ramp/prepared.json')['source_network'])
    original = e.load(BANK/'rm_ramp.json')
    assert original['seed']==33 and original['network_sha256']==sha(source)
    commands = {'rm8':[8,8,8], 'rm6':[6,6,6], 'rm_ramp':[6,4,4]}
    data = m.prepare_data(BANK/'observations/rm_ramp')
    model = e.load_base_model(data.geometry,m.MODEL/'config.json')
    params = e.load(m.MODEL/'selected_parameters.json')['parameters']
    ports = e.load(m.MODEL/'port_profile.json')
    forecasts = {}
    for arm, sequence in commands.items():
        command = lambda t: ({'RM_C10490':sequence[int((t-m.START)//150)]},{})
        window = e.window(data,model,m.START,'history_forecast',ports,command)
        cut = copy.deepcopy(data)
        for field in ('events','heads','port_events'):
            if hasattr(cut,field):
                setattr(cut,field,[r for r in getattr(cut,field) if float(r['time_s'])<=m.START])
        cut.cells = {t:r for t,r in cut.cells.items() if t<=m.START}
        cut.port_cohorts = {t:r for t,r in cut.port_cohorts.items() if float(t)<=m.START}
        for field in ('flows','boundaries','ports','headstocks','arrivals','departures','head_counts'):
            value = getattr(cut,field); selected = {k:v for k,v in value.items() if k[0]<=m.START}
            setattr(cut,field,Counter(selected) if isinstance(value,Counter) else selected)
        assert e.window(cut,model,m.START,'history_forecast',ports,command)==window
        prediction = e.simulate(model,window,params)
        assert prediction['local_ramp_audit']['passed']
        e.save(OUT/f'window_{arm}.json',window)
        e.save(OUT/f'prediction_{arm}.json',prediction)
        forecasts[arm] = dict(component=m.parts(prediction),
            merges={r['ramp']:r['end']['cumulative_merge_veh'] for r in prediction['ramps']
                    if r['road']=='FW_E' and r['end_sec']==m.END})
        if arm=='rm_ramp': continue  # Already completed; reuse only after prefix gates.
        profile = copy.deepcopy(original)
        profile['terminal_sec']=3000
        profile['meter_commands']=[dict(time_s=t,sc_no=9107,green_sec=g)
            for t,g in zip((2400,2550,2700,2850),[8]+sequence)]
        assert not profile['vsl_commands']
        e.save(OUT/(arm+'.json'),profile)
        prepare(source,OUT/(arm+'.json'),OUT/('prepared_'+arm))
    for arm in ('rm6','rm_ramp'):
        delta = {k:forecasts[arm]['component'][k]-forecasts['rm8']['component'][k] for k in ('mainline','on','off')}
        forecasts[arm]['delta_vs_g8'] = dict(**delta,total=sum(delta.values()))
    e.save(OUT/'predictions.json',forecasts)
    paths = [Path(__file__),source,m.MODEL/'config.json',m.MODEL/'selected_parameters.json',m.MODEL/'port_profile.json',
        e.CAL/'canonical_harness.py',e.CAL/'boundary_factory.py',e.ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',
        e.ROOT/'evaluation/controllers/physical_ramp_boundary.py']
    paths += sorted(OUT.glob('*.json'))
    paths += [data.folder/n for n in ('cells_30s.csv','flows_30s.csv','boundaries_30s.csv','ports_30s.csv',
        'port_events.csv','port_cohorts_30s.json','head_crossings.csv','head_stock_1s.csv')]
    e.save(OUT/'protocol.json',dict(seed=33,start_s=2550,run_end_s=3000,
        candidate_bank={arm:dict(green=[8]+commands[arm],vsl=[]) for arm in ('rm8','rm6')},
        reuse_strong_run=str(BANK/'run_rm_ramp'),reuse_strong_observations=str(data.folder),
        all_commands=commands,source_pins={p.relative_to(e.ROOT).as_posix():sha(p) for p in paths},
        predictions_frozen_before_new_runs=True,future_truncation_windows_exact=3,
        qualification=False,new_native_runs_planned=2,seed_role='Previously used development seed,not fresh holdout',
        purpose='Check whether the mild-vs-strong benefit ordering is stable across development states before fitting.',
        scope='Same FW_E mainline and four on/four off connectors;whole-link1s native cost incl.Pos<0.',
        gates=['Exact full FZP prefix through2550 versus existing strong run for both new arms',
            'Exact prefix2700 for rm6 versus strong','Native LDP/readback validation',
            'Include ramp/off queues and source-position accounting consistently;no unexplained disappearance']))
    print(json.dumps({arm:r.get('delta_vs_g8') for arm,r in forecasts.items()}),flush=True)


if __name__=='__main__': main()
