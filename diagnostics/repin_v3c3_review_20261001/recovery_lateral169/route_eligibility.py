"""Audit route eligibility of168/169 lateral transport from completed records.

No replay. A conservative lower bound uses the exact old exit demand to recover
current aligned exit stock; unknown nonnegative route-specific arrivals omitted.
Repeated transfer events are not counts of unique vehicles or causal TTT loss.
"""
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent

def main():
    assert not (HERE/'route_eligibility.json').exists()
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    source=read(HERE/'forecast/executed_function_sources.json')['RouteLaneRegion']
    # The demand excludes all exit classes from through movements at source20.
    assert "self.off_requests.setdefault(target,[0.]*self.groups)[g] += n*fraction" in source
    assert "classes = {key:n*amount/ns[g] for key,n in old[g].items()}" in source
    # No local merge at20; check existing physical mapping instead of assuming.
    spec=read(h.F/'route_inventory/contract.json')
    print('contract keys',list(spec))
    mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    length=(mapping[21]-mapping[20])/1000
    native=read(h.R/'exit_sending131/attempt2/steps.json')
    summary=[];steps=[];early=[]
    for mode in ('168','169'):
        folder=h.R/('state_lateral168' if mode=='168' else 'recovery_lateral169')
        for arm in ('release','release_vsl90'):
            pred=read(folder/f'forecast/state/s67_late_{arm}.json.gz')
            region=pred['diagnostics']['roads'][0]['joint_lane_region']
            junction={round(r['time_s'],6):r for r in region['junction_rows']}
            trace=[r for r in read(folder/f'forecast/state/s67_late_{arm}_transfers.json.gz') if r['cell']==20]
            assert len(trace)==450 and all(r['merge_veh']==0 for r in region['rows'] if r['cell']==20)
            final_exit=sum(n for k,n in pred['diagnostics']['roads'][0]['route_inventory_final']['cells']['FW_E'][20].items()
                           if k.rsplit('|',1)[-1]=='10483')
            final_lane0=[r for r in region['rows'] if r['cell']==20 and r['lane']==1][-1]['n_veh']
            for r in trace:
                t=round(r['time_s'],6);j=junction[t];donor=r['donor_stock']
                fraction=min(1.,r['state_v'][0]/3600/length)
                assert fraction>0
                exit_n=j['off_request_veh']/fraction
                assert -1e-9<=exit_n<=r['state_n'][0]+1e-8
                # Classes in lane1 leave20 only through accepted off10483;
                # any class-specific arrival can only increase pre-lateral N.
                lower=max(0.,exit_n-j['off_accepted_veh'])
                assert lower<=donor[0]+1e-8
                mat=[row[:] for row in r['requested']]
                for k in range(3):
                    total=sum(mat[g][k] for g in range(3))
                    factor=min(1.,max(0.,180*length-donor[k])/total) if total else 0.
                    for g in range(3):mat[g][k]*=factor
                moved=sum(mat[0])
                bound=moved*lower/donor[0] if donor[0] else 0.
                assert 0<=bound<=moved+1e-8
                steps.append(dict(model=mode,arm=arm,t=t,current_exit_lane1=exit_n,
                    postflow_exit_lower=lower,postflow_lane1_total=donor[0],
                    allclass_lane1_departures=moved,aligned_exit_departure_lower=bound))
            for lo,hi in ((2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                z=[x for x in steps if x['model']==mode and x['arm']==arm and lo-1e-6<=x['t']<hi-1e-6]
                obs=[x for x in native if x['case']==arm and lo-1e-6<=x['start']<hi-1e-6]
                summary.append(dict(model=mode,arm=arm,lo=lo,hi=hi,
                    aligned_exit_departures_lower=sum(x['aligned_exit_departure_lower'] for x in z),
                    allclass_lane1_departures=sum(x['allclass_lane1_departures'] for x in z),
                    model_mean_exit_n=sum(x['current_exit_lane1'] for x in z)/len(z),
                    observed_exit_n_mean=sum(x['n0'] for x in obs)/len(obs),
                    observed_mean_scope=[obs[0]['start'],obs[-1]['end']],
                    forced_nonaccess_final_min=max(0.,final_exit-final_lane0) if hi==3120.1 else None))
            early.append(dict(model=mode,arm=arm,
                first30_off=sum(r['off_accepted_veh'] for r in junction.values() if r['time_s']<2700.1-1e-6),
                lane_states30=[r for r in region['rows'] if abs(r['time_s']-2700.1)<1e-6 and r['lane']==1 and r['cell'] in (20,21)]))
    protocol=h.read(HERE/'protocol.json')
    for p,d in {**pins,**protocol['protected_sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    h.save(HERE/'route_eligibility.json',dict(summary=summary,steps=steps,early=early,
        interpretation='Conditional same-class arithmetic lower bound on aligned10483 traffic transported away from lane1 by the current all-class law. Repeated events, not unique vehicles. Native108/131 found no visible off-bound lane switching; unobserved within5s returns are not excluded. Does not quantify causal TTT or prove the alignment correction alone restores gains.108 already failed that test on older physics.',
        initial_window_limit='Native131 starts2700.1, so its first mean covers120s; model first mean covers150s. Middle/last windows match exactly.',
        input_sha256=pins,core=True,STOP=True,new_forecasts=0,new_fits=0))
    for r in summary:
        if r['lo']==2820.1:print(r)

if __name__=='__main__':main()
