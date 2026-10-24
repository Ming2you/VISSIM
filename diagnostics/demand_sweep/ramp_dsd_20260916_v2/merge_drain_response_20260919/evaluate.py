"""Causal450s entry-speed trial with native1s and model-internal residence."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.merge_drain_response_20260919.audit import *
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.spatial_calibration_20260919.calibrate import summary
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_response_20260919.study import direction_parts
import copy,hashlib

def simulate(model,w,params):
    pred=model.rollout(w['initial_cells'],w['boundary_steps'],params,w['initial_origin_queue'],
        port_dynamics=w['port_dynamics'],ramp_dynamics=w['ramp_dynamics'],vsl_zone_heads=w['vsl_zone_heads'],residence_audit=True)
    for r in pred['ramps']:
        assert abs(r['conservation_residual_veh'])<1e-7
        assert r['accepted_merge_veh']<=r['receiving_budget_veh']+1e-7
        assert all(abs(x['conservation_residual_veh'])<1e-7 for x in r.pop('local_receipts'))
    return pred

def internal_parts(pred):
    return {r['road']:{'mainline':r['model_residence_10s_veh_h'],
        'on':r['ramp_connector_residence_local_1s_veh_h'],
        'off':r['off_connector_residence_event_veh_h']}
        for r in pred['diagnostics']['roads']}

def main():
    out=HERE/'causal_v1';out.mkdir(exist_ok=False)
    prior=H/'ramp_response_20260919/arrival_v1/gap84/model'
    cfg=e.load(prior/'config.json')
    cfg['freeway']['physical_offramp_entry_speed']=e.load(HERE/'transit_fit_v1/protocol.json')['selected_accel_mps2']
    modeldir=out/'model';modeldir.mkdir()
    write(modeldir/'config.json',cfg)
    for name in ['selected_parameters.json','port_profile.json']:write(modeldir/name,e.load(prior/name))
    files=[e.CAL/'canonical_harness.py',H/'evaluate_response.py',ROOT/'evaluation/controllers/physical_ramp_boundary.py',
        ROOT/'evaluation/controllers/vissim_stackelberg_adapter.py',ROOT/'evaluation/controllers/area_freeway_accounting.py',
        ROOT/cfg['freeway']['segment_params'],modeldir/'config.json',modeldir/'selected_parameters.json']
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    write(out/'freeze.json',hashes)
    actual=e.load(HERE/'native_audit_v1/result.json');results={}
    params=e.load(prior/'selected_parameters.json')['parameters'];profile=e.load(prior/'port_profile.json')
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);protocol=e.load(bank/'protocol.json');results[str(seed)]={}
        for name,path in [('baseline',prior),('entry_speed',modeldir)]:
            model=e.load_base_model(data.geometry,path/'config.json');arms={};scores=[]
            for cutoff in [900,1650,2400,3600]:
                w=e.window(data,model,cutoff,'history_forecast',profile,lambda t: ({},{}))
                pred=simulate(model,w,params);scores.append(e.score_rollout(data,cutoff,pred,'FW_E'))
            for arm in ['none','rm_ramp','vsl','both']:
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def commands(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                            {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                w=e.window(data,model,start,'history_forecast',profile,commands)
                pred=simulate(model,w,params)
                native=data if arm=='none' else e.ObservationData(bank/'observations'/arm)
                arms[arm]={'predicted_internal':internal_parts(pred),'actual_1s':actual[str(seed)]['arms'][arm]['parts'],
                    'predicted_30s':direction_parts(data,model,start,pred),
                    'off_residence':{c:v for r in pred['diagnostics']['roads'] for c,v in r['off_connector_residence_by_port'].items()},
                    'invalid':e.score_rollout(native,start,pred,'FW_E')['invalid']}
                write(out/f'prediction_{seed}_{name}_{arm}.json',pred)
            ds={}
            for arm in ['rm_ramp','vsl','both']:
                ds[arm]={}
                for metric in ['predicted_internal','actual_1s','predicted_30s']:
                    values={k:arms[arm][metric]['FW_E'][k]-v for k,v in arms['none'][metric]['FW_E'].items()}
                    ds[arm][metric]={**values,'total':sum(values.values())}
            results[str(seed)][name]={'no_control':summary(scores),'arms':arms,'deltas':ds}
            print(seed,name,{a:{m:round(v['total'],5) for m,v in d.items()} for a,d in ds.items()},flush=True)
        write(out/'results.json',results)
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in hashes.items())
    write(out/'protocol.json',{'mainline_coefficients_fixed':True,'only_physical_change':'Entry-speed finite-acceleration FIFO transit on10483 and10682',
        'causal':'Only state at cutoff and past150s boundaries; future actual speed not used',
        'native_cost':'FZP1s end stock sum','model_cost':'Canonical10s mainline residence +local1s ramp residence +event-integrated off residence',
        'historic_metric':'30s stock trapezoid retained separately; not the primary cost comparison',
        'native_runs_started':0,'frozen_files_unchanged':True})

if __name__=='__main__':main()
