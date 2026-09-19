"""Reconstruct native port residence at1s before fitting boundary dynamics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.calibrate_ramps import e, H, ROOT, BASE, prepare_data, write
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.ramp_response_20260919.verify import CASES
from collections import Counter
import statistics

HERE=Path(__file__).resolve().parent

def main():
    out=HERE/'native_audit_v1';out.mkdir(exist_ok=False)
    result={}
    for seed,folder,bank,start in CASES:
        rows={}
        for arm in ['none','rm_ramp','vsl','both']:
            data=prepare_data(folder if arm=='none' else bank/'observations'/arm)
            model=e.load_base_model(data.geometry,BASE/'config.json')
            analysis=(H/('rules_4500_v1' if seed==13 else 'rules_4500_s23_v1')/'analysis/none'
                      if arm=='none' and seed!=33 else bank/'analysis'/arm)
            stocks={int(r['time_s']):r for r in e.rows(analysis/'stocks_1s.csv')}
            parts={road:{'mainline':sum(float(stocks[t][road+'_n']) for t in range(start+1,start+451))/3600,
                        'on':0.,'off':0.} for road in ['FW_E','FW_W']}
            ports={}
            for b in data.definitions.values():
                if b['kind'] not in ['ramp','offramp']:continue
                c=str(b['connector']);n=len(data.port_cohorts[str(start)][c]);ns=[n]
                for t in range(start+1,start+451):
                    n+=data.arrivals[t,c]-data.departures[t,c]
                    assert n>=0,(seed,arm,c,t,n)
                    if t%30==0:assert n==len(data.port_cohorts[str(t)][c]),(seed,arm,c,t,'native mass')
                    if b['kind']=='ramp':
                        h=data.headstocks[t,c]
                        assert n==int(h['prehead_n'])+int(h['posthead_n'])
                    ns.append(n)
                events=[r for r in data.events if r['connector']==c and start<float(r['time_s'])<=start+450]
                arrivals=[r for r in events if r['kind']=='arrival']
                departures=[r for r in events if r['kind']=='departure']
                residence=[float(r['residence_s']) for r in departures if r['residence_s']]
                ttt=sum(ns[1:])/3600
                coarse=sum((ns[t]+ns[t+30])*30/7200 for t in range(0,450,30))
                before=sum(ns[::30][:-1])/120
                port={'kind':b['kind'],'road':b['road'],'ttt_native_1s_right':ttt,
                    'ttt_30s_trapezoid':coarse,'arrivals':len(arrivals),'departures':len(departures),
                    'end':ns[-1],'mean_completed_residence_sec':statistics.mean(residence) if residence else None,
                    'median_completed_residence_sec':statistics.median(residence) if residence else None,
                    'arrival_time_moment_veh_h':sum(start+450-int(r['time_s'])+1 for r in arrivals)/3600,
                    'departure_time_moment_veh_h':sum(start+450-int(r['time_s'])+1 for r in departures)/3600,
                    'low_speed_stock_30s_veh_h':sum(sum(float(row[1])<5 for row in data.port_cohorts[str(t)][c])
                        for t in range(start+30,start+451,30))/120}
                assert abs(ttt-(ns[0]*450/3600+port['arrival_time_moment_veh_h']-port['departure_time_moment_veh_h']))<1e-9
                ports[c]=port
                parts[b['road']]['on' if b['kind']=='ramp' else 'off']+=ttt
            rows[arm]={'parts':parts,'ports':ports}
        delta={}
        for arm in ['rm_ramp','vsl','both']:
            delta[arm]={}
            for road in ['FW_E','FW_W']:
                p={k:rows[arm]['parts'][road][k]-v for k,v in rows['none']['parts'][road].items()}
                delta[arm][road]={**p,'total':sum(p.values())}
        result[str(seed)]={'start_sec':start,'end_sec':start+450,'arms':rows,'delta_1s':delta}
        print(seed,delta,flush=True)
        print('off',[(c,{arm:rows[arm]['ports'][c]['ttt_native_1s_right'] for arm in rows}) for c in ['10483','10682']],flush=True)
    write(out/'result.json',result)
    write(out/'definition.json',{'scope':'Native mainline+all on/off connectors, separately by direction; not Omega',
        'clock':'Sum end-of-second inventory,1s native FZP convention',
        'port_conservation':'Every30s snapshot checked; ramps additionally every1s against head stocks',
        'residence_censoring':'Completed-traversal averages exclude vehicles still on connector; not a causal outcome estimator'})

if __name__=='__main__':main()
