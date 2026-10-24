"""Independently check conditional requests, accepted lateral mass and outputs."""
import collections
import json
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'verification.json').exists()
    preserved=h.read(HERE/'preservation.json')
    for p,d in preserved['input_sha256'].items():assert h.sha(p)==d,p
    protocol=h.read(HERE/'protocol.json')
    for p,d in protocol['protected_sha256'].items():assert h.sha(p)==d,p
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    assert all(h.read(HERE/'parity.json').values())
    assert h.read(HERE/'status.json')['forecasts']==3
    source=h.read(HERE/'executed_function_sources.json')
    base=h.read(h.R/'spatial_context148/forecast/executed_function_sources.json')
    assert all(source[k]==v for k,v in base.items() if k!='RouteLaneRegion')
    pins={str(Path(__file__)):h.sha(__file__)}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    mapping=read(h.F/'route_inventory/mapping31.json')['freeway_model_links']['FW_E']['segment_bounds_m']
    comparisons=[];windows=[];flow_checks=0;max_error=0.;max_fraction_error=0.;max_moment_error=0.
    native_rows=h.read(h.R/'lateral_balance166/native.json')
    for arm in ('release','release_vsl90'):
        native=read(h.F/f'flow67/{arm}_frames.json.gz');fields=native['fields']
        frames={round(float(t),6):{str(vid):dict(zip(fields,r)) for vid,r in f.items()} for t,f in native['frames'].items()}
        initial=frames[2670.1]
        previous_n=collections.Counter((r['cell'],r['lane']) for r in initial.values())
        previous_v={key:sum(r['speed_kmh'] for r in initial.values() if (r['cell'],r['lane'])==key)/n for key,n in previous_n.items()}
        pred=read(HERE/f'{arm}.json.gz');diag=pred['diagnostics']['roads'][0]['joint_lane_region']
        by=collections.defaultdict(dict)
        for r in diag['rows']:by[round(r['time_s'],6)][r['cell'],r['lane']]=r
        requests=collections.defaultdict(dict)
        for r in read(HERE/f'{arm}_transfers.json.gz'):requests[round(r['time_s'],6)][r['cell']]=r
        assert len(requests)==450
        off={round(r['time_s'],6):r['off_accepted_veh'] for r in diag['junction_rows']}
        for t,rr in sorted(requests.items()):
            end=by[round(t+1,6)]
            start=round(2670.1+5*int(round(t-2670.1)//5),6)
            a,b=frames[start],frames[round(start+5,6)]
            donors=collections.Counter((x['cell'],x['lane']) for x in a.values())
            moved=collections.Counter((a[vid]['cell'],a[vid]['lane'],b[vid]['lane'])
                for vid in a.keys()&b.keys() if a[vid]['cell']==b[vid]['cell'] and a[vid]['lane']!=b[vid]['lane'])
            assert set(rr)==set(range(20,26))
            for cell,r in rr.items():
                n=r['donor_stock'];mat=r['requested']
                for g in range(3):
                    actual_n=previous_n[cell,g+1]+end[cell,g+1]['mainline_in_veh']+end[cell,g+1]['merge_veh']-end[cell,g+1]['mainline_out_veh']-(off[t] if cell==20 and g==0 else 0)
                    assert abs(n[g]-actual_n)<1e-8
                    for k in range(3):
                        fraction=moved[cell,g+1,k+1]/(5*donors[cell,g+1]) if donors[cell,g+1] else 0
                        err=abs(fraction-r['fractions'][g][k]);max_fraction_error=max(max_fraction_error,err);assert err<1e-12
                        assert abs(mat[g][k]-n[g]*fraction)<1e-8
                accepted=[list(row) for row in mat]
                capacity=180*(mapping[cell+1]-mapping[cell])/1000
                for k in range(3):
                    requested=sum(mat[g][k] for g in range(3));room=max(0,capacity-n[k])
                    factor=min(1,room/requested) if requested else 0
                    for g in range(3):accepted[g][k]*=factor
                moment0=sum(n[g]*previous_v[cell,g+1] for g in range(3));moment=list(n[g]*previous_v[cell,g+1] for g in range(3))
                for g in range(3):
                    for k in range(3):
                        value=accepted[g][k]*previous_v[cell,g+1]
                        moment[g]-=value;moment[k]+=value
                max_moment_error=max(max_moment_error,abs(sum(moment)-moment0))
                for g in range(3):
                    expected=n[g]+sum(accepted[k][g] for k in range(3))-sum(accepted[g])
                    err=abs(end[cell,g+1]['n_veh']-expected);max_error=max(max_error,err);assert err<1e-8;flow_checks+=1
            previous_n={key:r['n_veh'] for key,r in end.items()}
            previous_v={key:r['v_kmh'] for key,r in end.items()}
        original=read(h.R/f'spatial_context148/forecast/training/s67_late_{arm}.json.gz')
        for lo,hi in ((2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
            z=[r for r in native_rows if r['arm']==arm and r['cell']==20 and r['lane']==1 and lo-1e-6<=r['lo']<hi-1e-6]
            windows.append(dict(arm=arm,lo=lo,hi=hi,native_endpoint_off20=sum(r['disappear'] for r in z),
                baseline_off20=sum(r['off_accepted_veh'] for r in original['diagnostics']['roads'][0]['joint_lane_region']['junction_rows'] if lo-1e-6<=r['time_s']<hi-1e-6),
                conditioned_off20=sum(r['off_accepted_veh'] for r in diag['junction_rows'] if lo-1e-6<=r['time_s']<hi-1e-6)))
    assert flow_checks==16200
    # Output metrics are taken from the existing authoritative component analyzer.
    old=h.read(h.R/'spatial_context148/forecast/training/rows.json')
    baseline={r['arm']:r for r in old if r['case']=='s67_late'}
    candidate={r['arm']:r for r in h.read(HERE/'rows.json')}
    for mode,rows in [('baseline',baseline),('conditional',candidate)]:
        delta={kind:{k:rows['release_vsl90'][kind][k]-rows['release'][kind][k] for k in ('ttt','ramp_ttt','end_n','exits')}
               for kind in ('actual','predicted')}
        comparisons.append(dict(mode=mode,**delta))
    assert comparisons[0]['actual']==comparisons[1]['actual']
    a=h.read(HERE/'assessment.json')
    assert comparisons[1]['predicted']==a['deltas']['predicted']
    h.save(HERE/'comparison.json',dict(pairs=comparisons,windows=windows,
        limits='Native off20 labels independently confirmed131 for these windows; other appearance/disappearance is not classified as normal exits. Conditional outputs cannot qualify autonomous gains.'))
    for p,d in pins.items():assert h.sha(p)==d,p
    h.save(HERE/'verification.json',dict(status='pass',accepted_lane_balances=flow_checks,
        max_lane_mass_error=max_error,max_fraction_error=max_fraction_error,max_transport_moment_error=max_moment_error,
        parity_exact=True,core=True,STOP=True,input_sha256=pins,autonomous=False))
    print(dict(lane_checks=flow_checks,mass_error=max_error,fraction_error=max_fraction_error,moment_error=max_moment_error))
    print(comparisons)


if __name__=='__main__':main()
