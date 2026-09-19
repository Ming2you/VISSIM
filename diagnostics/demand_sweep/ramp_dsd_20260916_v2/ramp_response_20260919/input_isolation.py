"""Diagnostic-only observed arrival/supply substitutions, not deployable forecasts."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import *
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.state_response_20260919.study import direction_parts
import canonical_harness as ch

def main():
    out=HERE/'isolation_v1';out.mkdir(exist_ok=False);all_rows={}
    config=HERE/'arrival_v1/gap84/model/config.json'
    parameters=e.load(BASE/'selected_parameters.json')['parameters']
    for seed,folder,bank,start in [(13,H/'controller_response_4500_v1/none',H/'response_pairs_v1',1650),
            (23,H/'controller_response_s23_v1/none',H/'response_late_s23_v1',2400),
            (33,H/'state_response_20260919/native_s33_v1/observations/none',H/'state_response_20260919/native_s33_v1',2400)]:
        nc=prepare_data(folder);model=e.load_base_model(nc.geometry,config)
        protocol=e.load(bank/'protocol.json');rows={}
        for arrivals,supply in [(False,False),(True,False),(False,True),(True,True)]:
            name=f'arrivals_{arrivals}_supply_{supply}';rows[name]={}
            for arm in ['none','rm_ramp','vsl','both']:
                data=nc if arm=='none' else prepare_data(bank/'observations'/arm)
                seq=protocol['candidate_bank'].get(arm,{'green':[],'vsl':[]})
                def command(t):
                    i=int((t-start)//150)
                    return ({'RM_C10490':seq['green'][i]} if seq['green'] else {},
                        {d:seq['vsl'][i] for d in protocol.get('dsd_ids',[59,60,61,62])} if seq['vsl'] else {})
                w=e.window(nc,model,start,'history_forecast',e.load(BASE/'port_profile.json'),command)
                if arrivals:
                    for step in w['boundary_steps']:
                        step['ramp_arrival_profile']={}
                        for mid in TARGETS:
                            c=mid[4:];profile=[data.arrivals[t,c] for t in range(step['window_start_s']+1,step['window_end_s']+1)]
                            step['ramp_arrival_profile'][mid]=profile
                            step['ramp_arrival_vph'][mid]=sum(profile)*360.
                observed=local_case(data,model,start,'RM_C10484',command)['q'][::10]
                original=ch.gap_acceptance_supply_vph;called=[]
                def probe(q,tc,tf):
                    if supply and (tc,tf)==(2.5,2.5):
                        real=observed[len(called)];called.append({'model_q':q,'observed_q':real})
                        return original(real,tc,tf)
                    return original(q,tc,tf)
                ch.gap_acceptance_supply_vph=probe
                try:pred=e.simulate(model,w,parameters)
                finally:ch.gap_acceptance_supply_vph=original
                if supply:assert len(called)==45
                parts=direction_parts(nc,model,start,pred);actual=direction_parts(data,model,start)
                ports={}
                for mid in TARGETS:
                    rs=[r for r in pred['ramps'] if r['ramp']==mid];c=mid[4:]
                    # Left1s model inventory integral vs right1s native integral:
                    # retain both definitions; neither is the30s scoring metric.
                    ports[mid]={'model_ttt_1s_left':sum(r['connector_ttt_veh_h'] for r in rs),
                        'actual_ttt_1s_right':sum(float(data.headstocks[t,c]['prehead_n'])+float(data.headstocks[t,c]['posthead_n']) for t in range(start+1,start+451))/3600,
                        'model_merge':rs[-1]['end']['cumulative_merge_veh'],
                        'actual_merge':sum(data.departures[t,c] for t in range(start+1,start+451))}
                rows[name][arm]={'predicted':parts,'actual':actual,'ports':ports,
                    'supply_substitution':called,'invalid':e.score_rollout(data,start,pred,'FW_E')['invalid']}
            print('isolate',seed,name,[(arm,round(sum(rows[name][arm]['predicted']['FW_E'].values())-sum(rows[name]['none']['predicted']['FW_E'].values()),4)) for arm in ['rm_ramp','vsl','both']],flush=True)
        all_rows[str(seed)]=rows;write(out/'results.json',all_rows)
    write(out/'protocol.json',{'model':str(config.relative_to(ROOT)),
        'modes':'False/False is causal. Any True uses future native data only to diagnose input error; not a forecast.',
        'unchanged':'Mainline coefficients, signal service, costs, off-ramp model, source forecast',
        'supply_replacement':'Only10484 gap input q; original physical receiving upper bound remains active'})

if __name__=='__main__':main()
