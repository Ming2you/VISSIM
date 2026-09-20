"""Diagnostic only: does exact initial exit intent resolve response error?

Future paths identify current intent in cells5..8; they are NEVER online inputs.
No future speed, flow, exchange or stock is supplied after initialization.
"""
from pathlib import Path
import sys
import json
import hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,MODEL,CASES,ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from evaluation.controllers.physical_lane_groups import PhysicalLaneGroups

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'upstream_exit_inventory_v1/initial_intent_oracle';out.mkdir(exist_ok=False)
    config=HERE/'upstream_exit_inventory_v1/replay/upstream_inventory_config.json'
    params_file=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(params_file)['parameters'];profile=e.load(MODEL/'port_profile.json')
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          [Path(__file__),config,params_file,e.CAL/'canonical_harness.py',H/'evaluate_response.py',
           e.ROOT/'evaluation/controllers/physical_lane_groups.py']}
    results={}
    for seed,folder,bank,start in CASES:
        if seed not in (23,33):continue
        assert start==2400
        data=e.ObservationData(folder);model=e.load_base_model(data.geometry,config)
        lanes=e.load(H/'lane_group_response_20260919'/f'observations_v1/s{seed}.json')
        origins=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        audit=e.load(HERE/f'initial_exit_intent_audit_v1/s{seed}.json')
        modes={}
        for mode in ('causal','initial_intent_oracle'):
            modes[mode]={}
            for arm in ARMS:
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                            {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                w=e.window(data,model,start,'history_forecast',profile,command,port_origin_counts=origins['counts'])
                w['lane_group_dynamics']={'FW_E':{**lanes['geometry'],**lanes['cutoffs'][str(start)],
                    'initial_ramp_origin':origins['counts'][str(start)],
                    'initial_off_eligible':origins['eligible_before_off'][str(start)]}}
                for step in w['boundary_steps']:step['off_split_ratio']['10643']=1/6
                original=PhysicalLaneGroups.__init__
                def observed_initial(self,*args,**kwargs):
                    original(self,*args,**kwargs)
                    if self.road!='FW_E':return
                    for i in range(5,9):
                        rows=[audit['groups'][f'{i}:{g}'] for g in range(len(self.n[i]))]
                        assert all(r['unknown_by3000']==0 for r in rows)
                        values=[float(r['known_off10643']) for r in rows]
                        eligible=self.initial_off_eligible['10643'] if i==8 else self.n[i]
                        assert all(0<=x<=n for x,n in zip(values,eligible))
                        if i==8:self.off['10643']=values
                        else:self.upstream_off['10643'][i]=values
                    self.intent_initial['10643']=sum(map(sum,self.upstream_off['10643']))+sum(self.off['10643'])
                if mode=='initial_intent_oracle':PhysicalLaneGroups.__init__=observed_initial
                try:pred=e.simulate(model,w,params)
                finally:PhysicalLaneGroups.__init__=original
                old=e.load(HERE/f'upstream_exit_inventory_v1/replay/prediction_{seed}_upstream_inventory_{arm}.json')
                if mode=='causal':assert json.loads(json.dumps(pred))==old
                for key in ('cells','flows'):
                    assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
                road=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
                assert road['first_exit_inventory']['max_residual_veh']<1e-7
                modes[mode][arm]=parts(pred)
                e.save(out/f'prediction_{seed}_{mode}_{arm}.json',pred)
            modes[mode]['deltas']={a:{k:v-modes[mode]['none'][k] for k,v in modes[mode][a].items()} for a in ARMS[1:]}
            for d in modes[mode]['deltas'].values():d['total']=sum(d.values())
            print(seed,mode,{a:round(d['total'],6) for a,d in modes[mode]['deltas'].items()},flush=True)
        results[str(seed)]=modes
    for path,pin in pins.items():assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest()==pin
    e.save(out/'result.json',{'results':results,'diagnostic_future_paths_used_for_initial_intent':True,
        'not_causal_not_for_controller':True,'later_traffic_is_predicted':True,'corrected_cells':[5,6,7,8],
        'uncorrected_initial_cells':[0,1,2,3,4],'native_runs_started':0,'pins':pins})


if __name__=='__main__':main()
