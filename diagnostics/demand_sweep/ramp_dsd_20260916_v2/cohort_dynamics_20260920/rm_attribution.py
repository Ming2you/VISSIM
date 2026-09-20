"""Reuse native port events to separate meter response from propagated benefit."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e,H,CASES
from collections import Counter
import hashlib

HERE=Path(__file__).resolve().parent
START,END=2400,2850


def native_ports(folder):
    rows=e.rows(folder/'ports_30s.csv')
    table={(int(float(r['window_end_s'])),r['connector']):r for r in rows if r['road']=='FW_E'}
    connectors=sorted({c for t,c in table})
    counts=Counter((int(float(r['time_s'])),r['connector'],r['kind']) for r in e.rows(folder/'port_events.csv'))
    result={};checks=0
    for c in connectors:
        n=int(float(table[START,c]['end_n_veh']));initial=n;ttt=0.;arrivals=departures=0;trace=[]
        for t in range(START+1,END+1):
            a,d=counts[t,c,'arrival'],counts[t,c,'departure']
            unexpected={kind:q for (sec,connector,kind),q in counts.items()
                        if sec==t and connector==c and kind not in ('arrival','departure')}
            assert not unexpected,(c,t,unexpected)
            arrivals+=a;departures+=d;n+=a-d;assert n>=0,(c,t,n)
            ttt+=n/3600
            if t%30==0:
                assert n==float(table[t,c]['end_n_veh']),(c,t,n,table[t,c])
                assert float(table[t,c]['unresolved_absences_veh'])==0
                checks+=1
                trace.append({'t':t,'n':n,'cumulative_arrivals':arrivals,
                    'cumulative_departures':departures,'cumulative_ttt_veh_h':ttt})
        assert n==initial+arrivals-departures
        result[c]={'kind':table[END,c]['kind'],'initial_n':initial,'end_n':n,
            'arrivals':arrivals,'departures':departures,'ttt_veh_h':ttt,'trace':trace}
    return result,checks


def model_ports(pred):
    result={}
    for c in ['10639','10681','10490','10484']:
        rows=[r for r in pred['ramps'] if r['ramp']=='RM_C'+c]
        result[c]={'kind':'ramp','initial_n':rows[0]['start']['connector_veh'],
            'end_n':rows[-1]['end']['connector_veh'],
            'arrivals':sum(r['admitted_arrivals_veh'] for r in rows),
            'departures':sum(r['accepted_merge_veh'] for r in rows),
            'head_service':sum(r['head_service_veh'] for r in rows),
            'ttt_veh_h':sum(r['connector_ttt_veh_h'] for r in rows)}
    return result


def main():
    out=HERE/'rm_port_attribution_v1';out.mkdir(exist_ok=False)
    result={};checks=0;inputs=[]
    for seed in [23,33,43]:
        bank=(HERE/'fresh_s43_v1' if seed==43 else next(r[2] for r in CASES if r[0]==seed))
        nc=bank/'observations/none' if seed==43 else next(r[1] for r in CASES if r[0]==seed)
        arms={}
        for arm in ['none','rm_ramp']:
            folder=nc if arm=='none' else bank/'observations'/arm
            actual,n=native_ports(folder);checks+=n
            path=(HERE/f'fresh_s43_v1/predictions/port_travel_{arm}.json' if seed==43 else
                  HERE/f'port_origin_split_qualification_v2/prediction_{seed}_{arm}.json')
            model=model_ports(e.load(path));inputs.extend([path,folder/'port_events.csv',folder/'ports_30s.csv'])
            arms[arm]={'native':actual,'model':model}
        delta={}
        for source in ['native','model']:
            delta[source]={c:{k:arms['rm_ramp'][source][c][k]-arms['none'][source][c][k]
                             for k in ['arrivals','departures','end_n','ttt_veh_h']}
                           for c in arms['none'][source]}
        result[str(seed)]={'arms':arms,'delta':delta,
            'model_note':'Frozen port_travel candidate for43; latest port_origin_split for23/33. Do not pool as one model test.'}
        print(seed,delta['model'],flush=True)
    e.save(out/'result.json',{'status':'DIAGNOSTIC_NOT_QUALIFICATION','results':result,
        'native_stock_checks':checks,'cost_scope':'1s native end-frame port residence; model internal physical residence',
        'pins':{str(p.relative_to(e.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs+[Path(__file__)]}})


if __name__=='__main__':main()
