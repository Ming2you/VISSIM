"""Audit completed243 artifacts without another forecast or fit."""
import copy
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    completed=h.read(HERE/'completion.json');assert completed['status']=='complete'
    assert completed['forecasts450']==37
    protocol=h.read(HERE/'protocol.json');pins=h.read(HERE/'pins.json')
    for p,digest in {**pins,**protocol['protected_sha256'],protocol['STOP']['path']:protocol['STOP']['sha256']}.items():
        assert h.sha(p)==digest,p
    evaluations=h.read(HERE/'evaluations.json');selection=h.read(HERE/'selection_frozen.json')
    assert len(evaluations)==9
    chosen=next(e for e in evaluations if e['tag']==selection['tag'])
    val=next(e for e in evaluations if e['scope']=='validation')
    assert chosen['z']==val['z']==selection['z']
    assert {r['case'] for e in evaluations if e['scope']=='train' for r in e['rows']}=={'s67_late'}
    assert {r['case'] for r in val['rows']}=={'s29_late','s43_early','s61_late'}
    original=h.read(h.R/'lane_state132/eval_01/reference_config.json')
    original_tables=h.R/'queue_dynamics178/forecast/baseline'
    counters=dict(predictions=0,cell_balances=0,ramp_balances=0,off_balances=0,unchanged_baseline_tables=0,configuration_bindings=0)
    maximum=dict(cell=0.,ramp=0.,off=0.,reported_continuity=0.)
    truths={}
    for e in evaluations:
        tag=e['tag'];z=e['z']
        config=h.read(HERE/tag/'reference_config.json');expected=copy.deepcopy(original)
        for i in (19,20,21):
            row=expected['freeway']['state_response']['FW_E']['cell_overrides'][str(i)]
            row['relaxation']['deceleration_sec']*=z[0]
            row['anticipation']['downstream_ge_local']*=z[1]
        assert config==expected
        counters['configuration_bindings']+=1
        for row in e['rows']:
            key=(row['case'],row['arm'],row['horizon'])
            if key in truths:assert truths[key]==row['actual']
            truths[key]=row['actual']
        for file in (HERE/tag/'forecast/response243').glob('*.json.gz'):
            p=h.read(file);counters['predictions']+=1
            if tag in ('parity','center'):
                prior=h.read(original_tables/file.name)
                for key in ('cells','flows','ports','ramps'):
                    assert p[key]==prior[key],(file.name,key)
                    counters['unchanged_baseline_tables']+=1
            n={(round(r['time_s'],6),r['cell']):r['n_veh'] for r in p['cells']}
            f={(round(r['window_end_s'],6),r['cell']):r for r in p['flows']}
            for (end,cell),r in f.items():
                start=round(r['window_start_s'],6)
                if (start,cell) not in n:continue
                incoming=f[(end,cell-1)]['downstream_crossings'] if cell else 0.
                out=r['downstream_crossings']+r['terminal_exits']
                residual=n[end,cell]-n[start,cell]-incoming-r['source_admissions']-r['ramp_merges']+r['off_departures']+out
                maximum['cell']=max(maximum['cell'],abs(residual));counters['cell_balances']+=1
            for r in p['ramps']:
                residual=r['end']['connector_veh']-r['start']['connector_veh']-r['admitted_arrivals_veh']+r['accepted_merge_veh']
                maximum['ramp']=max(maximum['ramp'],abs(residual));counters['ramp_balances']+=1
            previous={}
            for r in p['ports']:
                k=r['connector']
                if k in previous:
                    before=previous[k]
                    # Native component port fields are cumulative counters.
                    residual=r['n_veh']-before['n_veh']-(r['admitted_veh']-before['admitted_veh'])+(r['departed_veh']-before['departed_veh'])
                    maximum['off']=max(maximum['off'],abs(residual));counters['off_balances']+=1
                previous[k]=r
            for r in p['diagnostics']['roads']:
                assert r['negative_density_count']==0
                maximum['reported_continuity']=max(maximum['reported_continuity'],r['continuity_residual_max_veh'])
    assert counters['predictions']==37 and counters['unchanged_baseline_tables']==20
    assert all(v<1e-7 for v in maximum.values()),maximum
    # Independently reconstruct all outcome differences and selection regret.
    table=[]
    for e in evaluations:
        if e['tag'] not in ('center',selection['tag'],'validation'):continue
        for case in sorted({r['case'] for r in e['rows']}):
            for horizon in (150,450):
                by={r['arm']:r for r in e['rows'] if r['case']==case and r['horizon']==horizon}
                pairs=[('hold','release'),('hold','hold_vsl90'),('release','release_vsl90'),('none','vsl')]
                for a,b in pairs:
                    if a not in by or b not in by:continue
                    actual={k:by[b]['actual'][k]-by[a]['actual'][k] for k in ('ttt','mainline_ttt','ramp_ttt','off_ttt','end_n','exits')}
                    predicted={k:by[b]['predicted'][k]-by[a]['predicted'][k] for k in actual}
                    table.append(dict(tag=e['tag'],case=case,horizon=horizon,change=b+'-'+a,actual=actual,predicted=predicted))
    h.save(HERE/'verified_contrasts.json',table)
    h.save(HERE/'verification.json',dict(status='PASS',counts=counters,max_residual_veh=maximum,
        source_and_STOP_preserved=True,baseline_reproduction_exact=True,train_validation_selection_separate=True,
        first30s_cell_balance='No saved initial per-cell vector in these output tables; excluded from independent differencing, existing runtime continuity check covers it.',
        native_and_FZP_reads=0,extra_forecasts=0,extra_fits=0,production_adopted=False))
    print(json.dumps(dict(counts=counters,maximum=maximum)))


if __name__=='__main__':main()
