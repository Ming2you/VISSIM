"""Inspect previously unseparated SC6 side exits from saved response operands."""
from collections import Counter
from pathlib import Path
import json,pickle
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.gain_account341 import audit
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.city_loss322.audit import green_seconds

HERE=Path(__file__).resolve().parent;A=HERE.parent
TARGETS={'SC6_W_SC5_to_E_SC104':'1220018504->10197',
         'SC6_E_SC104_to_N_SC103':'1220021201->10142'}

def main():
    assert not (HERE/'side_limits.json').exists()
    prior=audit.read(A/'exit_timing309/assessment.json')
    cfg,state,_=pickle.loads(audit.raw(audit.JOINT/'initial.pickle'))
    report={}
    for arm in ('hold','city'):
        r=audit.read(audit.BASE/(arm+'.response.json.gz'))
        resources={(x['resource'],x['start_sec'],x['kind']):x for x in r['resource_allocations']}
        events=audit.read(Path('E:/VISSIM_analysis/20261010_exit_timing309')/(arm+'.json.gz'))['events']
        report[arm]={}
        for movement,edge in TARGETS.items():
            spec=cfg.network.urban_movements[movement]
            rate=cfg.network.movement_capacity_by_movement_veh_h[movement]
            actual=[]
            for row in events:
                if row['kind']!='observed_exit':continue
                match=prior['native_observed_pair_topology'][row['from_link']+'->'+row['to_link']]
                if match['edge'] and '->'.join(match['edge'])==edge:actual.append(row)
            windows=[]
            for start in (2400,2550,2700):
                controlroot=A.parent/'selection2400_discrete/hold' if arm=='hold' else A/'citysplit287/forecast2400/city_only'
                control=audit.read(controlroot/f'action_{start:06}.json')
                totals=Counter();ticks=[]
                for t in range(start,start+150,10):
                    q=resources[movement,t,'urban_movement_stock']['available_veh']
                    request=resources[movement,t,'urban_movement_intended_limit']
                    wanted=request['available_veh'];accepted=request['accepted_total_veh']
                    green=green_seconds(control,cfg.network,movement,t);cap=rate*green/3600
                    assert -1e-7<=accepted<=wanted+1e-7 and wanted<=min(q,cap)+1e-7
                    rec=dict(sec=t,ready=q,green=green,cap=cap,accepted=accepted,
                        starved=max(0.,cap-q),other_request_loss=min(q,cap)-wanted,receiving_loss=wanted-accepted)
                    ticks.append(rec)
                    for k in ('green','cap','accepted','starved','other_request_loss','receiving_loss'):totals[k]+=rec[k]
                assert abs(totals['cap']-sum(totals[k] for k in ('accepted','starved','other_request_loss','receiving_loss')))<1e-7
                departures=sum(x['ttd_veh'] for x in r['transfers'] if x['route_key']=='movement:'+movement and
                               start<=x['start_sec'] and x['end_sec']<=start+150)
                windows.append(dict(start_sec=start,**dict(totals),model_omega_departures=departures,
                    native_exit_count=sum(start<=x['mid_sec']<start+150 for x in actual),ticks=ticks))
            origin=spec['origin'];keys={'storage:'+origin,*('movement:'+m for m,s in cfg.network.urban_movements.items() if s['origin']==origin)}
            support=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            report[arm][movement]=dict(edge=edge,spec=spec,rate=rate,windows=windows,
                initial_support={k:{owner:v for owner,v in entries.items() if owner in keys} for k,entries in support.items() if any(owner in keys and v for owner,v in entries.items())})
    result=dict(status='complete_saved_SC6_side_operands',arms=report,source_pins=audit.PINS,
        limitations=['Native5s midpoint exit bins are not exact head crossing times.',
          'Request starvation is a model operand result, not proof of actual demand shortage.',
          'No new fitting or simulation; causes require current geometry/route and native green validation before changes.'])
    (HERE/'side_limits.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for arm,moves in report.items():
        for m,r in moves.items():print(arm,m,'rate',r['rate'],[{k:v for k,v in w.items() if k!='ticks'} for w in r['windows']],flush=True)

if __name__=='__main__':main()
