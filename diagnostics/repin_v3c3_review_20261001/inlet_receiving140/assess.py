"""Compare the completed140 run with cached initial30-second lane balances."""
import csv
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
R=HERE.parent
U=R.parents[1]
I=U/'diagnostics/sdmpc_n31_20260924/integration_20260926'
F=I/'baseline_reproduction_20260929/cellwise_calibration/freeway_first'
PINS={}


def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)


def main():
    assert read(HERE/'status.json')['status']=='complete_macro_gate_failed'
    observed=read(R/'onset_reaction134/rows.json.gz')
    native_flow=I/'heldout67_freeway_20260930/observations/release/flows_30s.csv'
    PINS[str(native_flow)]=hashlib.sha256(native_flow.read_bytes()).hexdigest()
    with native_flow.open() as f:native={int(x['cell']):x for x in csv.DictReader(f)
        if x['road']=='FW_E' and abs(float(x['window_end_s'])-2700.1)<1e-6}
    native_rows=[]
    for cell in (19,20,21):
        for lane in (1,2,3):
            rr=sorted([x for x in observed if x['case']=='s67_late' and x['arm']=='release'
                and x['cell']==cell and x['lane']==lane and x['time_s']<2700],key=lambda x:x['time_s'])
            assert len(rr)==6
            counts={k:sum(x['counts'][k] for x in rr) for k in rr[0]['counts']}
            delta=sum(v if k.startswith('enter') else -v for k,v in counts.items())
            assert rr[-1]['n1']-rr[0]['n0']==delta
            # All initial-window unobserved entries are the known cell21 merge;
            # all unobserved departures are the known cell20 off entry.
            assert counts['enter_unobserved']==0 or (cell,lane)==(21,1)
            assert counts['leave_unobserved']==0 or (cell,lane)==(20,1)
            if (cell,lane)==(21,1):assert counts['enter_unobserved']==int(native[cell]['ramp_merges'])
            if (cell,lane)==(20,1):assert counts['leave_unobserved']==int(native[cell]['off_departures'])
            native_rows.append(dict(cell=cell,lane=lane,n0=rr[0]['n0'],n1=rr[-1]['n1'],v1=rr[-1]['v1'],
                incoming=counts['enter_longitudinal'],outgoing=counts['leave_longitudinal'],
                merge=counts['enter_unobserved'],off=counts['leave_unobserved'],
                lateral=counts['enter_samecell_lateral']-counts['leave_samecell_lateral']))
    models={};prefix_checks={};checks={}
    for label,folder in [('frozen132',R/'lane_state132/autonomous_diagnostic/training'),('receiving140',HERE/'training')]:
        p=read(folder/'s67_late_release.json.gz');reg=p['diagnostics']['roads'][0]['joint_lane_region']
        prefix={k:[x for x in p[k] if x['time_s' if k in ('cells','ports') else 'window_end_s' if k=='flows' else 'end_sec']<=2700.1+1e-6]
            for k in ('cells','flows','ports','ramps')}
        for arm in ('hold','hold_vsl90','release_vsl90'):
            other=read(folder/f's67_late_{arm}.json.gz')
            checks_arm={k:[x for x in other[k] if x['time_s' if k in ('cells','ports') else 'window_end_s' if k=='flows' else 'end_sec']<=2700.1+1e-6]==v for k,v in prefix.items()}
            assert all(checks_arm.values());prefix_checks[label+'_'+arm]=checks_arm
        output=[]
        for n in native_rows:
            rr=[x for x in reg['rows'] if x['cell']==n['cell'] and x['lane']==n['lane'] and x['time_s']<=2700.1+1e-6]
            assert len(rr)==30
            incoming=sum(x['mainline_in_veh'] for x in rr);outgoing=sum(x['mainline_out_veh'] for x in rr);merge=sum(x['merge_veh'] for x in rr)
            off=sum(x['off_departures'] for x in prefix['flows'] if x['cell']==20) if (n['cell'],n['lane'])==(20,1) else 0.
            lateral=rr[-1]['n_veh']-n['n0']-incoming-merge+outgoing+off
            errors=dict(incoming=incoming-n['incoming'],outgoing=-(outgoing-n['outgoing']),
                merge=merge-n['merge'],off=-(off-n['off']),lateral=lateral-n['lateral'])
            assert abs(sum(errors.values())-(rr[-1]['n_veh']-n['n1']))<1e-9
            output.append(dict(cell=n['cell'],lane=n['lane'],n1=rr[-1]['n_veh'],v1=rr[-1]['v_kmh'],
                incoming=incoming,outgoing=outgoing,merge=merge,off=off,lateral_balance_residual=lateral,end_n_error_parts=errors))
        models[label]=output
        if label=='receiving140':
            rec=[x for x in reg['receiving_rows'] if x['cell']==19 and x['lane']==1 and x['time_s']<2700.1-1e-6]
            mov={round(x['time_s']-1,6):x for x in reg['rows'] if x['cell']==19 and x['lane']==1}
            checks['entrance_first30']=dict(supply_total=sum(x['supply_veh'] for x in rec),
                accepted=sum(mov[round(x['time_s'],6)]['mainline_in_veh'] for x in rec),
                supply_binding_seconds=sum(abs(mov[round(x['time_s'],6)]['mainline_in_veh']-x['accepted_budget_veh'])<1e-8 for x in rec))
    frames=read(F/'flow67/release_frames.json.gz')['frames']
    initial_inlet=[]
    for g in (2,3,4):
        rr=[x for x in frames['2670.1'].values() if x[0]==18 and x[3]==g]
        initial_inlet.append(dict(cell=18,physical_lane=g,n_veh=len(rr),
            mean_speed_kmh=sum(x[1] for x in rr)/len(rr),sum_speed_kmh=sum(x[1] for x in rr)))
    ambiguous=[]
    for k in range(6):
        t=round(2670.1+5*k,1);a=frames[str(t)];b=frames[str(round(t+5,1))]
        for vid,z in b.items():
            if z[0]!=19 or vid not in a or a[vid][0]>=19:continue
            # The4-to3 lane map is verified in the original geometric contract.
            if a[vid][0]!=18 or a[vid][3]-1!=z[3]:ambiguous.append(dict(time=t,vehicle=vid,before=a[vid],after=z))
    rows=read(HERE/'training/rows.json')
    checks.update(max_conservation=max(x['conservation_max'] for x in rows),max_route_error=max(x['route_error'] for x in rows),
        checked_receiving_samples=sum(x['receiving140']['samples'] for x in rows),
        max_receiving_excess=max(x['receiving140']['max_receiving_excess'] for x in rows))
    result=dict(status='REJECTED_NOT_ADOPTED',native=native_rows,models=models,checks=checks,
        common_first30=prefix_checks,inlet_crossing_lane_uncertainties=ambiguous,initial_inlet=initial_inlet,
        limitations='5s observed cell-membership arrivals/departures; crossing and lane-change order can be ambiguous. Model lateral is a conserved balance residual, not measured lane-change counts. Current comparison is before command divergence, not a VSL causal effect.',
        new_forecasts=0,new_native=0,new_FZP=0,input_sha256=PINS)
    (HERE/'local_assessment.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(checks));print('uncertain_crossing_lanes',len(ambiguous))
    for label,rows in models.items():
        for x in rows:
            if x['lane']==1:print(label,x)


if __name__=='__main__':main()
