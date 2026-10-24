"""Cached ramp-cost and boundary decomposition with the original30s metric."""
import csv
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h
HERE=Path(__file__).resolve().parent
RAMPS=('10639','10681','10490','10484')
TIMES=[round(2670.1+30*k,1) for k in range(16)]

def main():
    assert not (HERE/'ramp_costs.json').exists()
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    def csvrows(p):
        pins[str(p)]=h.sha(p)
        with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
    integ=lambda z:sum((z[a]+z[b])*30/7200 for a,b in zip(TIMES,TIMES[1:]))
    by={};boundaries={}
    measured={r['arm']:r for r in read(HERE/'forecast/state/rows.json') if r['case']=='s67_late'}
    for arm in ('hold','release','release_vsl90'):
        folder=h.I/'heldout67_freeway_20260930/observations'/arm
        ports=csvrows(folder/'ports_30s.csv')
        ports={(round(float(r['window_end_s']),1),r['connector']):r for r in ports}
        pred=read(HERE/f'forecast/state/s67_late_{arm}.json.gz')
        by[arm]={}
        for connector in RAMPS:
            actual={t:float(ports[t,connector]['end_n_veh']) for t in TIMES}
            part=[r for r in pred['ramps'] if r['start']['connector_id']==connector]
            forecast={round(r['end_sec'],1):r['end']['connector_veh'] for r in part}
            forecast[TIMES[0]]=actual[TIMES[0]]
            by[arm][connector]=dict(
                actual=dict(ttt=integ(actual),arrival=sum(float(ports[t,connector]['arrivals_veh']) for t in TIMES[1:]),
                    merge=sum(float(ports[t,connector]['departures_veh']) for t in TIMES[1:]),start=actual[TIMES[0]],end=actual[TIMES[-1]]),
                predicted=dict(ttt=integ(forecast),arrival=sum(r['admitted_arrivals_veh'] for r in part),
                    merge=sum(r['accepted_merge_veh'] for r in part),start=forecast[TIMES[0]],end=forecast[TIMES[-1]]))
            for kind,z in by[arm][connector].items():
                assert abs(z['end']-z['start']-z['arrival']+z['merge'])<1e-7,(arm,connector,kind,z)
        for kind in ('actual','predicted'):
            assert abs(sum(by[arm][c][kind]['ttt'] for c in RAMPS)-measured[arm][kind]['ramp_ttt'])<1e-8
        flows=[r for r in csvrows(folder/'flows_30s.csv') if r['road']=='FW_E' and TIMES[0]<float(r['window_end_s'])<=TIMES[-1]+1e-6]
        boundaries[arm]=dict(actual_source=sum(float(r['source_admissions']) for r in flows),
            predicted_source=sum(r['source_admissions'] for r in pred['flows']),
            actual_unexplained_losses=sum(float(r['unexplained_losses']) for r in flows),
            actual_native_removals=sum(float(r['native_removals']) for r in flows))
    pairs=[]
    for left,right in (('hold','release'),('release','release_vsl90')):
        d={c:{kind:{k:by[right][c][kind][k]-by[left][c][kind][k] for k in ('ttt','arrival','merge','end')}
              for kind in ('actual','predicted')} for c in RAMPS}
        pairs.append(dict(left=left,right=right,ramps=d))
        print(left,right,d)
    protocol=read(HERE/'protocol.json')
    for p,d in {**pins,**protocol['protected_sha256']}.items():assert h.sha(p)==d,p
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    h.save(HERE/'ramp_costs.json',dict(by_arm=by,pairs=pairs,boundaries=boundaries,input_sha256=pins,
        interpretation='Connector waiting only. Realized boundary arrivals can differ after control; differences are not automatically either causal gain or random noise. No future input supplied to forecasts. Native errors/removals kept separate. WholeOmega and outside waiting remain unqualified.',
        conservation=True,ramp_ttt_matches_existing_metric=True,new_forecasts=0,new_fits=0))
    print('boundaries',boundaries)

if __name__=='__main__':main()
