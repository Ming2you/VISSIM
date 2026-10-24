"""Diagnostic-only integration/merge-pulse separation; native controls unchanged."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, CASES, MODEL, H, ARMS
import copy
from collections import Counter

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'clock_v1';out.mkdir(exist_ok=False)
    params=e.load(MODEL/'selected_parameters.json')['parameters']
    profile=e.load(MODEL/'port_profile.json');results={}
    for seed,folder,bank,start in CASES:
        nc=e.ObservationData(folder);protocol=e.load(bank/'protocol.json');result={}
        for mode in ['one_sec_mean_merge','one_sec_actual_merge']:
            result[mode]={}
            for arm in ARMS:
                data=nc if arm=='none' else e.ObservationData(bank/'observations'/arm)
                model=e.load_base_model(nc.geometry,MODEL/'config.json')
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                            {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                w=e.window(nc,model,start,'history_forecast',profile,command)
                counts=Counter((int(float(r['time_s'])),r['connector']) for r in e.rows(data.folder/'port_events.csv') if r['kind']=='departure')
                steps=[]
                for old in w['boundary_steps']:
                    rates={mid:sum(counts[t,str(r['connector'])] for t in range(old['window_start_s']+1,old['window_end_s']+1))*360.
                           for mid,r in model.ramps.items()}
                    for t in range(old['window_start_s'],old['window_end_s']):
                        row=copy.deepcopy(old);row.update(window_start_s=t,window_end_s=t+1)
                        row['ramp_release_vph']=(rates if mode=='one_sec_mean_merge' else
                            {mid:counts[t+1,str(r['connector'])]*3600. for mid,r in model.ramps.items()})
                        steps.append(row)
                model.base.simulation.T_f=1.
                model.ramp_receiving_nodes={}
                pred=model.rollout(w['initial_cells'],steps,params,w['initial_origin_queue'],port_dynamics=w['port_dynamics'],
                    vsl_zone_heads=w['vsl_zone_heads'],residence_audit=True)
                row=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
                result[mode][arm]={'mainline_ttt':row['model_residence_10s_veh_h'],
                                  'score':e.score_rollout(data,start,pred,'FW_E')}
                # The existing ledger field name is historic; this experiment explicitly uses1s.
            result[mode]['delta']={a:result[mode][a]['mainline_ttt']-result[mode]['none']['mainline_ttt'] for a in ARMS[1:]}
            print(seed,mode,result[mode]['delta'],flush=True)
        results[str(seed)]=result
    e.save(out/'results.json',results)
    e.save(out/'protocol.json',{'diagnostic_only':True,'future_actual_merge_input':True,
        'one_sec_mean_merge':'1s freeway/port integration, actual accepted merges averaged within original10s bins',
        'one_sec_actual_merge':'Same1s integration, actual observed1s merge pulses',
        'unchanged':'Physical coefficients,450s horizon, native commands, control cycle, source/split/drainage forecasts',
        'default_model_unchanged':True,'native_runs_started':0,
        'mainline_ttt_field_note':'Historic model_residence_10s_veh_h name contains1s residence in this diagnostic only'})


if __name__=='__main__':main()
