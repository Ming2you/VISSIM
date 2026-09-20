"""Equal-peak-capacity FD shape diagnostic in the existing component harness.

No independent adapter. Temporary hooks are restored; only FW_E uses the
existing two-branch implementation. Critical densities are derived from the
old exponential peak q=vc*rhoc*exp(-1/a), so shape alone cannot buy capacity.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from evaluation.controllers import freeway_fd as fd
import canonical_harness as ch
from src.controllers import wu_faithful_follower as follower
from contextlib import contextmanager
import math
import argparse

HERE=Path(__file__).resolve().parent;LANE=H/'lane_group_response_20260919'


@contextmanager
def shape(model):
    original=model._config;old_cell=fd.cell_parameters;audit=[]
    def parameters(net,link=None,index=None):
        row=(net.freeway_segment_params.get(str(link),[])[index]
            if link is not None and index is not None else {})
        v=row.get('v_free',net.v_free)
        rho=row.get('rho_crit',net.rho_crit)*math.exp(-1/net.metanet_a_m)
        result=fd.FDParameters(v,rho,row.get('rho_max',net.rho_max));result.validate()
        return result
    def config(road,overrides):
        cfg=original(road,overrides)
        if road=='FW_E':
            cfg.network.vsl_fd_two_branch=True
            cfg.network.rho_crit_two_branch=parameters(cfg.network).rho_crit
            fd.install_freeway_fd_runtime(ch.adapter,follower,cfg)
            audit.append({'road':road,'cells':[{'cell':i,'v_free':parameters(cfg.network,road,i).v_free,
                'rho_crit':parameters(cfg.network,road,i).rho_crit,
                'peak_vph_per_lane':parameters(cfg.network,road,i).v_free*parameters(cfg.network,road,i).rho_crit}
                for i in range(21)]})
        return cfg
    fd.cell_parameters=parameters;model._config=config
    try:yield audit
    finally:fd.cell_parameters=old_cell;model._config=original


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='fd_shape_probe_v1')
    args=parser.parse_args();out=HERE/args.output;out.mkdir(exist_ok=False)
    params=e.load(LANE/'qualification_v6/parameters.json')['parameters'];profile=e.load(MODEL/'port_profile.json')
    results={}
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
        model=e.load_base_model(data.geometry,HERE/'destination_clear_ending_lane_v1/config.json')
        protocol=e.load(bank/'protocol.json');arms={};guards={}
        with shape(model) as audit:
            for t in [900,1650,2400,3600]:
                w=e.window(data,model,t,'history_forecast',profile,lambda _: ({},{}))
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(t)]}}
                pred=e.simulate(model,w,params);guards[str(t)]=e.score_rollout(data,t,pred,'FW_E')
            for arm in ARMS:
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                w=e.window(data,model,start,'history_forecast',profile,command)
                w['lane_group_dynamics']={'FW_E':{**lane['geometry'],**lane['cutoffs'][str(start)]}}
                pred=e.simulate(model,w,params);arms[arm]=parts(pred)
                reference=e.load(HERE/f'destination_clear_ending_lane_qualification_v2/prediction_{seed}_{arm}.json')
                for key in ['cells','flows','ports','ramps']:
                    assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in reference[key] if r['road']=='FW_W']
                e.save(out/f'prediction_s{seed}_{arm}.json',pred)
        delta={a:{k:v-arms['none'][k] for k,v in arms[a].items()} for a in ARMS[1:]}
        for row in delta.values():row['total']=sum(row.values())
        results[str(seed)]={'state_guards':guards,'parts':arms,'delta':delta}
        e.save(out/f'result_s{seed}.json',results[str(seed)]);e.save(out/f'fd_s{seed}.json',audit)
        print(seed,{a:round(v['total'],6) for a,v in delta.items()},flush=True)
    e.save(out/'results.json',results)


if __name__=='__main__':main()
