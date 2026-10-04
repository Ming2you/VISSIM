"""Assess the one frozen151 coefficient; no further fitting or forecasts."""
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'forecast';status=h.read(out/'status.json');assert status['status']=='complete_macro_gate_failed' and status['forecasts']==9
    protocol=h.read(out/'protocol.json');preserved=h.read(out/'preservation.json');proposal=h.read(HERE/'proposal.json')
    assert all(h.read(out/'parity.json').values()) and all(preserved[k] for k in ('core','inputs','STOP','hooks_restored'))
    pins={**protocol['protected_sha256'],**preserved['input_sha256'],**proposal['input_sha256']}
    def read(p):pins[str(p)]=h.sha(p);return h.read(p)
    base=h.R/'spatial_context148/forecast';rows=read(out/'training/rows.json');old=read(base/'training/rows.json')
    contrasts=[];local=[]
    for case in ('s29_late','s67_late'):
        a={r['arm']:r for r in rows if r['case']==case};b={r['arm']:r for r in old if r['case']==case}
        for left,right in [('hold','release'),('hold','hold_vsl90'),('release','release_vsl90')]:
            contrasts.append(dict(case=case,left=left,right=right,actual=a[right]['actual']['ttt']-a[left]['actual']['ttt'],
                corrected148=b[right]['predicted']['ttt']-b[left]['predicted']['ttt'],nu19_151=a[right]['predicted']['ttt']-a[left]['predicted']['ttt']))
    for arm in ('release','release_vsl90'):
        versions={label:read(folder/'training'/f's67_late_{arm}.json.gz') for label,folder in [('corrected148',base),('nu19_151',out)]}
        for label,pred in versions.items():
            region=pred['diagnostics']['roads'][0]['joint_lane_region']
            for lo,hi in ((2670.1,2700.1),(2670.1,2820.1),(2820.1,2970.1),(2970.1,3120.1)):
                rr=[r for r in region['rows'] if r['cell']==20 and r['lane']==1 and lo+1e-6<r['time_s']<=hi+1e-6]
                jj=[r for r in region['junction_rows'] if lo-1e-6<=r['time_s']<hi-1e-6]
                assert len(rr)==len(jj)==round(hi-lo)
                local.append(dict(arm=arm,version=label,lo=lo,hi=hi,arrivals20_lane1=sum(r['mainline_in_veh'] for r in rr),
                    through20_lane1=sum(r['mainline_out_veh'] for r in rr),off_request=sum(r['off_request_veh'] for r in jj),
                    off_accepted=sum(r['off_accepted_veh'] for r in jj),end_n20_lane1=rr[-1]['n_veh'],end_v20_lane1=rr[-1]['v_kmh']))
    original_helper=read(HERE/'preflight.json')['helper_sha256'];assert h.sha(h.__file__)==original_helper==h.sha(HERE/'executed_helper.py.txt')
    assert read(out/'executed_function_sources.json')==read(base/'executed_function_sources.json')
    for path,digest in pins.items():assert h.sha(path)==digest,path
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    result=dict(contrasts=contrasts,local=local,status=status,gate=read(out/'training_assessment.json'),
        max_mass=max(r['conservation_max'] for r in rows),max_route=max(r['route_error'] for r in rows),
        max_partition=max(r['spatial144']['max_class_partition_error'] for r in rows),spatial_samples=sum(r['spatial144']['samples'] for r in rows),
        verified_pins=len(pins),core=True,STOP=True,model_adopted=False,additional_fits=0,new_native=0,new_FZP=0,new_9000_analysis=0,push=0)
    assert max(result[k] for k in ('max_mass','max_route','max_partition'))<1e-7
    h.save(HERE/'assessment.json',result);h.save(HERE/'assessment_pins.json',pins)
    for r in contrasts:print(r)
    for r in local:
        if r['hi']==2700.1 or r['lo']==2820.1:print(r)
    print('verified',len(pins),'pins',result['max_mass'],'mass error')


if __name__=='__main__':main()
