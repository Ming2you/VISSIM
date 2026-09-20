"""Offline structural check of an open outlet; not a calibrated capacity bonus.

Use the existing zero-gradient terminal rule only on FW_E. No future boundary
flows, fitted parameters, altered inputs or native runs. Preserve all failures.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
import json
import hashlib
import argparse

HERE=Path(__file__).resolve().parent
LANE=H/'lane_group_response_20260919'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=HERE/'terminal_probe_v1')
    parser.add_argument('--lane-observations',type=Path,
        help='Compare old/new observed lane resolution with the SAME open outlet and fixed coefficients')
    args=parser.parse_args()
    out=args.output.resolve();out.mkdir(exist_ok=False)
    config=HERE/'port_origin_split_v1/config.json'
    parameter_file=HERE/'port_travel_fit_v1/selected_parameters.json'
    params=e.load(parameter_file)['parameters'];profile=e.load(MODEL/'port_profile.json')
    files=[Path(__file__),config,parameter_file,MODEL/'port_profile.json',
           e.CAL/'canonical_harness.py',H/'evaluate_response.py',
           e.ROOT/'evaluation/controllers/physical_lane_groups.py']
    pins={str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    labels=['open_reference','open_lanes'] if args.lane_observations else ['existing','open_outlet']
    e.save(out/'protocol.json',{'status':'STRUCTURAL_DIAGNOSTIC_NOT_ADOPTED',
        'change':('Only observed mainline lane-state resolution; both modes use existing open outlet and the same coefficients.'
                  if args.lane_observations else 'FW_E existing terminal_zero_gradient=True: outgoing predicted sending without global terminal cap; equal ghost density.'),
        'lane_observations':str(args.lane_observations.resolve()) if args.lane_observations else None,
        'unchanged':'Source admission, internal capacities, all physical ports, ramp waits, VSL law, commands, objective, observations and parameters.',
        'future_observations_used_as_inputs':False,'native_runs_started':0,'pins':pins})
    results={};exact=0;west=0
    for seed,folder,bank,start in CASES:
        data=e.ObservationData(folder);lane=e.load(LANE/f'observations_v1/s{seed}.json')
        origins=e.load(HERE/f'port_positions_v1/s{seed}.json');protocol=e.load(bank/'protocol.json')
        modes={};guards={}
        for mode in labels:
            selected_lane=(e.load(args.lane_observations/f's{seed}.json')
                           if args.lane_observations and mode=='open_lanes' else lane)
            model=e.load_base_model(data.geometry,config)
            if mode!='existing':
                original=model._config
                def configured(road, override):
                    cfg=original(road,override)
                    if road=='FW_E':cfg.network.terminal_zero_gradient=True
                    return cfg
                model._config=configured
            def window(t,command):
                w=e.window(data,model,t,'history_forecast',profile,command,port_origin_counts=origins['counts'])
                w['lane_group_dynamics']={'FW_E':{**selected_lane['geometry'],**selected_lane['cutoffs'][str(t)],
                    'initial_ramp_origin':origins['counts'][str(t)],
                    'initial_off_eligible':origins['eligible_before_off'][str(t)]}}
                return w
            modes[mode]={};guards[mode]={}
            for cutoff in [900,1650,2400,3600]:
                pred=e.simulate(model,window(cutoff,lambda _: ({},{})),params)
                guards[mode][str(cutoff)]=e.score_rollout(data,cutoff,pred,'FW_E')
            for arm in ARMS:
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                pred=e.simulate(model,window(start,command),params)
                old=e.load(HERE/f'terminal_probe_v1/prediction_s{seed}_open_outlet_{arm}.json' if args.lane_observations
                           else HERE/f'port_origin_split_qualification_v2/prediction_{seed}_{arm}.json')
                if mode==labels[0]:
                    assert json.loads(json.dumps(pred))==old,(seed,arm,'existing replay');exact+=1
                else:
                    for key in ['cells','flows']:
                        assert [r for r in pred[key] if r['road']=='FW_W']==[r for r in old[key] if r['road']=='FW_W']
                    west+=1
                r=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
                assert r['continuity_residual_max_veh']<1e-7 and r['lane_group_continuity_residual_max_veh']<1e-7
                final=[r for r in pred['lane_groups']['FW_E'] if r['cell']==20]
                modes[mode][arm]={'parts':parts(pred),'terminal_exits':sum(r['mainline_out_veh'] for r in final),
                    'terminal_time_moment':-sum((start+450-r['time_s']+10)*r['mainline_out_veh']/3600 for r in final)}
                e.save(out/f'prediction_s{seed}_{mode}_{arm}.json',pred)
            modes[mode]['deltas']={a:{k:v-modes[mode]['none']['parts'][k] for k,v in modes[mode][a]['parts'].items()} for a in ARMS[1:]}
            for row in modes[mode]['deltas'].values():row['total']=sum(row.values())
            print(seed,mode,{a:round(v['total'],6) for a,v in modes[mode]['deltas'].items()},flush=True)
        results[str(seed)]={'modes':modes,'state_guards':guards,
            'within_ten_percent':{t:guards[labels[1]][t]['objective']<=1.1*guards[labels[0]][t]['objective'] for t in guards[labels[0]]}}
        e.save(out/f'result_s{seed}.json',results[str(seed)])
    for name,pin in pins.items():assert hashlib.sha256((e.ROOT/name).read_bytes()).hexdigest()==pin
    e.save(out/'results.json',{'status':'NOT_QUALIFIED_STRUCTURAL_PROBE','results':results,
        'existing_full_json_exact':exact,'west_cells_and_flows_exact':west,'source_pins_unchanged':True,
        'terminal_moment_note':'10s start-edge quadrature; native1s moments use end frames and cannot be equated exactly.'})


if __name__=='__main__':main()
