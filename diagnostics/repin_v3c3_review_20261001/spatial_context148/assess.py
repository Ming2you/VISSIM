"""Review completed148 physical outputs; no new prediction or extraction."""
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    out=HERE/'forecast';status=h.read(out/'status.json')
    assert status['status']=='complete_macro_gate_failed' and status['forecasts']==9
    rows=h.read(out/'training/rows.json');base=h.read(h.R/'spatial_speed144/audit_repair/training/rows.json')
    protocol=h.read(out/'protocol.json');preserved=h.read(out/'preservation.json');unit=h.read(HERE/'unit_result.json')
    assert all(h.read(out/'parity.json').values()) and all(preserved[k] for k in ('core','inputs','STOP','hooks_restored'))
    pins={**protocol['protected_sha256'],**preserved['input_sha256']}
    contrasts=[];local=[]
    for case in ('s29_late','s67_late'):
        a={r['arm']:r for r in rows if r['case']==case};b={r['arm']:r for r in base if r['case']==case}
        for left,right in [('hold','release'),('hold','hold_vsl90'),('release','release_vsl90')]:
            contrasts.append(dict(case=case,left=left,right=right,
                actual=a[right]['actual']['ttt']-a[left]['actual']['ttt'],
                old144=b[right]['predicted']['ttt']-b[left]['predicted']['ttt'],
                corrected148=a[right]['predicted']['ttt']-a[left]['predicted']['ttt']))
        for arm in a:
            p=out/'training'/f'{case}_{arm}.json.gz';pins[str(p)]=h.sha(p);pred=h.read(p)
            region=pred['diagnostics']['roads'][0]['joint_lane_region']
            middle=[x for x in region['junction_rows'] if 2820.1-1e-6<=x['time_s']<2970.1-1e-6]
            assert len(middle)==150
            local.append(dict(case=case,arm=arm,off10483_request=sum(x['off_request_veh'] for x in middle),off10483_accepted=sum(x['off_accepted_veh'] for x in middle),
                first30=[dict(cell=i,**{key:next(x[key] for x in region['rows'] if x['cell']==i and x['lane']==1 and abs(x['time_s']-2700.1)<1e-6) for key in ('n_veh','v_kmh')}) for i in (19,20,21,22,23)]))
    for path,digest in pins.items():assert h.sha(path)==digest,path
    assert h.sha(protocol['STOP']['path'])==protocol['STOP']['sha256']
    assert h.sha(h.__file__)==h.read(HERE/'preflight.json')['helper_sha256']==h.sha(HERE/'executed_helper.py.txt')
    result=dict(contrasts=contrasts,local=local,unit=unit,status=status,
        max_conservation=max(r['conservation_max'] for r in rows),max_route=max(r['route_error'] for r in rows),
        max_half_partition=max(r['spatial144']['max_class_partition_error'] for r in rows),half_samples=sum(r['spatial144']['samples'] for r in rows),
        verified_pin_count=len(pins),core=True,STOP=True,helper=True,
        model_adopted=False,implementation_correction_retained=True,
        limits='Correction repairs execution of intended cell-specific law; macro gain gate still fails. Old144-146 results are preserved as executions of the defective spatial implementation,not evidence for correctly bound spatial dynamics. Nonspatial132 is not invalidated by this bug.',
        new_forecasts=0,new_native=0,new_FZP=0,new_9000_analysis=0,push=0)
    assert result['max_conservation']<1e-7 and result['max_route']<1e-7 and result['max_half_partition']<1e-7
    h.save(HERE/'assessment.json',result)
    print('VERIFIED',result['verified_pin_count'],'pins','mass',result['max_conservation'],'halfstates',result['half_samples'])
    for x in contrasts:print(x)
    for x in local:
        if x['case']=='s67_late' and x['arm'].startswith('release'):print(x)


if __name__=='__main__':main()
