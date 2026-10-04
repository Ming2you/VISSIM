"""Independently check saved allocations, cumulative ports and local response."""
import csv
import gzip
import json
import math
from pathlib import Path
from diagnostics.repin_v3c3_review_20261001.junction_calibration125 import run as h

HERE=Path(__file__).resolve().parent


def main():
    assert not (HERE/'verification.json').exists()
    out=HERE/'forecast';status=h.read(out/'status.json')
    assert status==dict(status='complete',forecasts=21)
    p=h.read(HERE/'protocol.json');pins={str(Path(__file__)):h.sha(__file__)}
    def read(path):pins[str(path)]=h.sha(path);return h.read(path)
    rows=read(out/'rows.json');assessment=read(out/'assessment.json')
    assert all(read(out/'disabled_parity.json').values())
    checks=0;max_budget=0.;max_port_mass=0.;port_corrections=[];summaries=[]
    for row in rows:
        path=out/row['version']/(row['case']+'_'+row['arm']+'.json.gz');pred=read(path)
        previous={};increments=[]
        for port in pred['ports']:
            key=port['connector'];old=previous.get(key)
            # admitted/departed counters are cumulative, not per-step flows.
            da=port['admitted_veh']-(old['admitted_veh'] if old else 0.)
            dd=port['departed_veh']-(old['departed_veh'] if old else 0.)
            assert da>=-1e-9 and dd>=-1e-9
            if old:
                residual=port['n_veh']-old['n_veh']-da+dd
                max_port_mass=max(max_port_mass,abs(residual));assert abs(residual)<1e-7
                checks+=1
            increments.append(dict(time_s=port['time_s'],connector=key,admitted=da,departed=dd,end_n=port['n_veh']))
            previous[key]=port
        if row['version']=='target_lanes':
            region=pred['diagnostics']['roads'][0]['joint_lane_region']
            budgets={(round(x['time_s']+1,6),x['cell'],x['lane']):x for x in region['receiving_rows']}
            assert len(budgets)==3600
            for x in region['rows']:
                b=budgets[round(x['time_s'],6),x['cell'],x['lane']]
                difference=x['mainline_in_veh']+x['merge_veh']-b['accepted_budget_veh']
                max_budget=max(max_budget,difference)
                assert difference<1e-7;checks+=1
            assert region['route_marginal_max_error']<1e-7
        ramp_rows=pred['ramps']
        for x in ramp_rows:
            assert abs(x['end']['connector_veh']-x['start']['connector_veh']-x['admitted_arrivals_veh']+x['accepted_merge_veh'])<1e-7
            assert x['accepted_merge_veh']<=x['receiving_budget_veh']+1e-8
            checks+=1
        internal=sum(x['connector_ttt_veh_h'] for x in ramp_rows)
        external=sum(x['start']['outside_component_backlog_veh']*x['duration_sec']/3600 for x in ramp_rows)
        summaries.append(dict(case=row['case'],arm=row['arm'],version=row['version'],
            ramp_residence_1s_veh_h=dict(internal=internal,outside_component=external,total=internal+external),
            merge10639_actual=row['actual']['merges']['RM_C10639'],merge10639_predicted=row['predicted']['merges']['RM_C10639']))
        if row['case']=='s67_late' and row['arm']=='release':
            blocks=[]
            for lo in (2670.1,2820.1,2970.1):
                z=[x for x in increments if x['connector']=='10682' and lo<x['time_s']<=lo+150+1e-6]
                assert len(z)==150
                blocks.append(dict(start=lo,admitted=sum(x['admitted'] for x in z),departed=sum(x['departed'] for x in z),end_n=z[-1]['end_n']))
            port_corrections.append(dict(version=row['version'],blocks=blocks))
    # Correct the model-only subtable in172 context. Original execution/source
    # are retained; native counts and172 conclusions were unaffected.
    correction=[]
    for arm in ('release','release_vsl90'):
        d=read(h.R/f'prehead_storage171/forecast/state/s67_late_{arm}.json.gz')
        z={round(x['time_s'],6):x for x in d['ports'] if x['connector']=='10682'}
        for lo in (2670.1,2820.1,2970.1):
            a=z.get(lo);b=z[round(lo+150,6)]
            correction.append(dict(arm=arm,start=lo,model171_off10682=dict(
                arrivals_veh=b['admitted_veh']-(a['admitted_veh'] if a else 0),
                departures_veh=b['departed_veh']-(a['departed_veh'] if a else 0),end_n_veh=b['n_veh'])))
    h.save(HERE/'port_counter_correction.json',dict(
        original='merge_target172/context.json blocks[*].off10682_prediction',
        error='Summed cumulative native-model port counters rather than differences. These model-only fields are invalid in original172 context; use this corrected table.',
        unaffected='Native port counts, native stopped-lane labels, matched state comparison,172 main findings and all traffic forecasts.',
        corrected172=correction,correct173=port_corrections))
    source=(h.R/'state_lateral168/run.py');(HERE/'run.py.executed.txt').write_bytes(source.read_bytes())
    for path,digest in {**pins,**p['pins'],**p['protected_sha256'],p['STOP']['path']:p['STOP']['sha256']}.items():assert h.sha(path)==digest,path
    h.save(HERE/'verification.json',dict(status='engineering_checked_physical_candidate_rejected',
        allocation_and_mass_checks=checks,shared_budget_excess_max_veh=max_budget,port_mass_residual_max_veh=max_port_mass,
        source_sha256=h.sha(source),input_sha256=pins,protected_and_STOP_preserved=True,
        records=summaries,port_counter_semantics='Cumulative model admitted/departed; checked differences against stock conservation.',
        candidate_qualified=False,production_adopted=False))
    h.save(HERE/'completion.json',dict(status='complete_rejected',forecasts=21,forecast_seconds=assessment['seconds'],
        preparation_failure='Wrong regional cache had no10--11 exposures; assertion failed before protocol/forecast. Original source/log retained, corrected full-road cache pinned to old48 record.',
        source_change='Existing168 driver adds explicit merge173 mode; original main AST unchanged; production model untouched.',
        reason='10639 release merge error did not improve;67VSL sign still wrong,61arrival deficit remains. This trial did not recalibrate per-lane speed parameters or combine with19--25.',
        full_goal='ACTIVE_NOT_QUALIFIED',new_native=0,FZP=0,push=0))
    print('checked',checks,'max_budget',max_budget,'max_port_mass',max_port_mass)
    print(port_corrections)


if __name__=='__main__':main()
