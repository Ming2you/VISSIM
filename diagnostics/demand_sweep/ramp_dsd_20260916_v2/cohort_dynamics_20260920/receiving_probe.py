"""Bounded structural probe: finite backward-wave receiving, no cost fitting.

Exploratory values are not estimated wave speeds. Observed aggregate incoming
flow only bounds wave supply from below; lane-wave identification remains open.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups
from contextlib import contextmanager
import argparse

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'


@contextmanager
def wave_receiving(wave):
    original=PhysicalLaneGroups.free_space
    def supply(plant,cfg):
        space=original(plant,cfg)
        return [[x*min(1.,wave*plant.dt/plant.lengths[i]) for x in row] for i,row in enumerate(space)]
    PhysicalLaneGroups.free_space=supply
    try:yield
    finally:PhysicalLaneGroups.free_space=original


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='receiving_probe_v1')
    args=parser.parse_args();out=HERE/args.output;out.mkdir(exist_ok=False)
    params=e.load(LANE/'qualification_v6/parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    results={}
    for wave in [18.,24.,36.]:
        results[str(wave)]={}
        for seed,folder,bank,start in CASES:
            data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
            model=e.load_base_model(data.geometry,LANE/'qualification_v6/config.json')
            protocol=e.load(bank/'protocol.json');arms={};guards={}
            with wave_receiving(wave):
                for t in [900,1650,2400,3600]:
                    w=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}))
                    w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)]}}
                    pred=e.simulate(model,w,params)
                    guards[str(t)]=e.score_rollout(data,t,pred,'FW_E')
                for arm in ARMS:
                    seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                    def command(t):
                        i=int((t-start)//150)
                        return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                            {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                    w=e.window(data,model,start,'history_forecast',profile,command)
                    w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
                    pred=e.simulate(model,w,params);arms[arm]=parts(pred)
                    e.save(out/f'prediction_w{wave}_s{seed}_{arm}.json',pred)
            delta={a:{k:v-arms['none'][k] for k,v in arms[a].items()} for a in ARMS[1:]}
            for row in delta.values():row['total']=sum(row.values())
            results[str(wave)][str(seed)]={'state_guards':guards,'parts':arms,'delta':delta}
            e.save(out/f'result_w{wave}_s{seed}.json',results[str(wave)][str(seed)])
            print(wave,seed,{a:round(v['total'],6) for a,v in delta.items()},flush=True)
    e.save(out/'results.json',results)
    e.save(out/'protocol.json',{'status':'STRUCTURAL_PROBE_NOT_CALIBRATED',
        'formula':'min(remaining storage, w * (rho_jam-rho) * lanes * dt_h)',
        'unchanged':'METANET speed, sending, queue costs, actuators, source and all other boundaries',
        'waves_kmh':[18,24,36],'scope':'FW_E lane groups only; no native runs',
        'reference':'https://its.berkeley.edu/node/4777',
        'caution':'Hybrid receiving probe, not a full CTM or a proven hyperbolic discretization. No additional capacity bonus/drop.'})


if __name__=='__main__':main()
