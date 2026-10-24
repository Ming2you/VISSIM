"""Review the completed two-arm delay experiment using existing caches only."""
import gzip,hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
A=HERE.parent
OUT=HERE/'forecast2400'
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not (HERE/'assessment.json').exists()
    current=read(OUT/'summary.json')
    assert current['status']=='complete' and current['forecasts']==2
    assert all(sha(p)==h for p,h in current['source_pins'].items())
    oldhold=read(A/'matched280/authority/summary.json')['results']['hold']
    oldcity=read(A/'citysplit287/forecast2400/summary.json')['results']['city_only']
    truth=read(A/'cityresponse290/assessment.json')
    timing=read(A/'cityresponse290/head_timing.json')
    native=sum(x['cost'] for x in truth['native_boundary']['delta'].values())
    old=oldcity['omega_ttt_veh_h']-oldhold['omega_ttt_veh_h']
    new=current['results']['city']['omega_ttt_veh_h']-current['results']['hold']['omega_ttt_veh_h']
    movements={'SC6_S':{'movement:SC6_S_SC12_to_N_SC103','movement:SC6_S_SC12_to_E_SC104'},
               'SC101_S':{'movement:SC101_S_SC1_to_N_SC2005'}}
    heads={};receipts={}
    for arm in ('hold','city'):
        response=json.loads(gzip.decompress((OUT/(arm+'.response.json.gz')).read_bytes()))
        heads[arm]={}
        for group,sources in movements.items():
            trips=[t for t in response['transfers'] if t['source'] in sources and t['source']!=t['target']]
            counts=[sum(t['vehicles'] for t in trips if start<=t['start_sec']<start+150)
                    for start in (2400,2550,2700)]
            cost=-sum(t['vehicles']*sum(x['dt_h'] for x in response['residence'] if x['end_sec']>=t['end_sec']-1e-7) for t in trips)
            oldrows=[x for x in truth['head_counts'][arm] if x['group']==group and x['phase']=='p1']
            actual=[x['actual'] for x in oldrows];previous=[x['model'] for x in oldrows]
            heads[arm][group]=dict(actual_by150=actual,baseline_by150=previous,candidate_by150=counts,
                candidate_count=sum(counts),candidate_time_cost=cost,
                baseline_mae=sum(abs(x-y) for x,y in zip(actual,previous))/3,
                candidate_mae=sum(abs(x-y) for x,y in zip(actual,counts))/3)
        rows=read(OUT/(arm+'.delay_receipts.json'))
        receipts[arm]={key:dict(calls=sum(r['source']==key for r in rows),
            min_sec=min(r['delay_sec'] for r in rows if r['source']==key),
            max_sec=max(r['delay_sec'] for r in rows if r['source']==key)) for key in {r['source'] for r in rows}}
    delta={g:dict(native_count=sum(heads['city'][g]['actual_by150'])-sum(heads['hold'][g]['actual_by150']),
                  baseline_count=timing['delta'][g]['model']['count'],
                  candidate_count=heads['city'][g]['candidate_count']-heads['hold'][g]['candidate_count'],
                  native_time_cost_bounds=timing['delta'][g]['native_head_time_cost_bounds'],
                  baseline_time_cost=timing['delta'][g]['model']['head_time_cost'],
                  candidate_time_cost=heads['city'][g]['candidate_time_cost']-heads['hold'][g]['candidate_time_cost']) for g in movements}
    report=dict(status='complete_not_adopted',native_city_minus_hold_veh_h=native,
        baseline_city_minus_hold_veh_h=old,candidate_city_minus_hold_veh_h=new,
        baseline_absolute_gain_error=abs(old-native),candidate_absolute_gain_error=abs(new-native),
        error_reduction_percent=100*(1-abs(new-native)/abs(old-native)),
        native_material_direction_matched=new*native>0,heads=heads,head_response_delta=delta,delay_receipts=receipts,
        resource_max_exceedance=max(x['resource_max_exceedance'] for x in current['results'].values()),
        initial_state_error=current['initial_state_error'],valid_forecasts=2,
        total_forecast_computations_including_unsaved_report_failure=2,optimizer_iterations=0,
        new_native=0,new_fzp_reads=0,production_changes=0,fit=0,goal_complete=False,
        limitations=['Head timing cost is not Omega TTT.',
          'Same initial state and offered demand; actual future native admission can differ.',
          'SC10 native clock is added for future accepted traffic; current initial cohorts unchanged and internal spatial gate queues remain aggregate.',
          'Geometry uses shortest physical source-to-head path; no future vehicle times are inputs.'],
        decision='Do not adopt as gain-corrected plant: the material city-effect direction remains wrong. Preserve as a single geometry-only decomposition; no distance/speed coefficient grid or full optimizer.',
        source_pins={str(p):sha(p) for p in [Path(__file__),OUT/'summary.json',A/'cityresponse290/assessment.json',A/'cityresponse290/head_timing.json']})
    (HERE/'assessment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:report[k] for k in ('native_city_minus_hold_veh_h','baseline_city_minus_hold_veh_h',
        'candidate_city_minus_hold_veh_h','error_reduction_percent','head_response_delta','resource_max_exceedance')},ensure_ascii=False))


if __name__=='__main__':main()
