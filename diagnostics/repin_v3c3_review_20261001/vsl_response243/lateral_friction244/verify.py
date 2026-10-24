"""Verify finished244 forecasts, conservation, and executed reaction algebra."""
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    completion=h.read(HERE/'completion.json');assert completion['status']=='complete'
    assert completion['forecasts450']==33
    protocol=h.read(HERE/'protocol.json');pins=h.read(HERE/'pins.json')
    for p,d in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():assert h.sha(p)==d,p
    evaluations=h.read(HERE/'evaluations.json');selection=h.read(HERE/'selection_frozen.json')
    chosen=next(e for e in evaluations if e['tag']==selection['tag']);val=next(e for e in evaluations if e['scope']=='validation')
    assert chosen['z']==val['z']==selection['z']
    assert {r['case'] for e in evaluations if e['scope']=='train' for r in e['rows']}=={'s67_late'}
    assert {r['case'] for r in val['rows']}=={'s29_late','s43_early','s61_late'}
    counts=dict(forecasts=0,baseline_tables=0,cell_balances=0,ramp_balances=0,off_balances=0,friction_updates=0)
    maximum=dict(cell=0.,ramp=0.,off=0.,friction=0.,reported_continuity=0.)
    effects=[];contrasts=[]
    for e in evaluations:
        folder=HERE/e['tag'];setting=h.read(folder/'setting.json')
        assert Path(setting['manifest']).resolve()==(h.R/'lane_state132/eval_01/manifest.json').resolve()
        for p in (folder/'forecast/response243').glob('*.json.gz'):
            z=h.read(p);counts['forecasts']+=1
            if e['tag'] in ('parity','center'):
                baseline=h.read(h.R/'queue_dynamics178/forecast/baseline'/p.name)
                for key in ('cells','flows','ports','ramps'):
                    assert z[key]==baseline[key],(p,key)
                    counts['baseline_tables']+=1
            n={(round(r['time_s'],6),r['cell']):r['n_veh'] for r in z['cells']}
            flows={(round(r['window_end_s'],6),r['cell']):r for r in z['flows']}
            for (end,cell),r in flows.items():
                start=round(r['window_start_s'],6)
                if (start,cell) not in n:continue
                incoming=flows[end,cell-1]['downstream_crossings'] if cell else 0.
                residual=n[end,cell]-n[start,cell]-incoming-r['source_admissions']-r['ramp_merges']+r['off_departures']+r['downstream_crossings']+r['terminal_exits']
                maximum['cell']=max(maximum['cell'],abs(residual));counts['cell_balances']+=1
            for r in z['ramps']:
                residual=r['end']['connector_veh']-r['start']['connector_veh']-r['admitted_arrivals_veh']+r['accepted_merge_veh']
                maximum['ramp']=max(maximum['ramp'],abs(residual));counts['ramp_balances']+=1
            before={}
            for r in z['ports']:
                k=r['connector']
                if k in before:
                    a=before[k]
                    residual=r['n_veh']-a['n_veh']-(r['admitted_veh']-a['admitted_veh'])+(r['departed_veh']-a['departed_veh'])
                    maximum['off']=max(maximum['off'],abs(residual));counts['off_balances']+=1
                before[k]=r
            diag=z['diagnostics']['roads'][0]
            assert diag['negative_density_count']==0
            maximum['reported_continuity']=max(maximum['reported_continuity'],diag['continuity_residual_max_veh'])
            # Direct physical algebra from the saved actual accepted transfers.
            groups={}
            for r in diag['joint_lane_region']['rows']:
                a=r.get('friction244')
                if a is None:assert r['cell']==19;continue
                assert a['phi']==e['z'][1] and a['merge_scale']==e['z'][0]
                assert all(x>=0 for x in a['incoming'])
                numerator=math.fsum(amount*max(a['target_speed']-speed,0.) for amount,speed in zip(a['incoming'],a['origin_speeds']))
                expected=e['z'][1]*numerator/(a['length_km']*a['rho_crit'])
                maximum['friction']=max(maximum['friction'],abs(expected-a['loss']))
                assert a['loss']>=0 and math.isfinite(a['loss'])
                assert r['v_kmh']<=max(5.,a['before']-a['loss'])+1e-9
                counts['friction_updates']+=1
                key=(r['cell'],r['lane']);g=groups.setdefault(key,dict(steps=0,loss=0.,accepted_lateral=0.,nonzero=0,at_floor=0))
                g['steps']+=1;g['loss']+=a['loss'];g['accepted_lateral']+=sum(a['incoming']);g['nonzero']+=a['loss']>0;g['at_floor']+=r['v_kmh']<=5.+1e-9
            if e['tag'] in (selection['tag'],'validation'):
                effects.extend(dict(tag=e['tag'],case=p.name[:-8],cell=k[0],lane=k[1],mean_extra_loss_per_step=v['loss']/v['steps'],**v) for k,v in groups.items())
        if e['tag'] in ('center',selection['tag'],'validation'):
            for case in sorted({r['case'] for r in e['rows']}):
                for t in (150,450):
                    by={r['arm']:r for r in e['rows'] if r['case']==case and r['horizon']==t}
                    for a,b in [('hold','release'),('hold','hold_vsl90'),('release','release_vsl90'),('none','vsl')]:
                        if a not in by or b not in by:continue
                        keys=('ttt','mainline_ttt','ramp_ttt','off_ttt','exits','end_n')
                        contrasts.append(dict(tag=e['tag'],case=case,horizon=t,change=b+'-'+a,
                            actual={k:by[b]['actual'][k]-by[a]['actual'][k] for k in keys},predicted={k:by[b]['predicted'][k]-by[a]['predicted'][k] for k in keys}))
    assert counts['forecasts']==33 and counts['baseline_tables']==20
    assert counts['friction_updates']==33*450*6*3
    assert max(maximum.values())<1e-7,maximum
    h.save(HERE/'contrasts.json',contrasts);h.save(HERE/'friction_effects.json',effects)
    result=dict(status='PASS',counts=counts,max_residual=maximum,source_and_STOP_unchanged=True,baseline_exact=True,
        independent_cell_balance='First30s omitted because initial per-cell vector absent from output table; existing runtime continuity covers it.',
        qualification='Mechanical checks do not imply control-gain accuracy.',extra_forecasts=0,native=0,FZP=0,adopted=False)
    h.save(HERE/'verification.json',result);print(json.dumps(result))


if __name__=='__main__':main()
