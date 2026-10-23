"""Assess completed spatial refinement against fixed native and old caches."""
import datetime,gzip,hashlib,json
from pathlib import Path
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;CAND=OUT/'refine15_candidate'
PINS={}
def read(p):
    b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not (OUT/'refine15_assessment.json').exists()
    done=read(CAND/'completion.json');assert done['new_forecasts']==2 and done['new_native']==0
    for p,h in done['source_pins'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    cases={r['name']:r for r in read(CAND/'results.json')}
    original={r['name']:r for r in read(HERE/'matched_off2250_v3/summary.json')['results']}
    cut=read(OUT/'approach_flux.json')
    oldnative=read(OUT/'summary.json')
    responses={n:read(CAND/f'{n}_response.json.gz') for n in ('hold','selected')}
    rows=[];balances=[]
    for i,end in enumerate((150,300,450),1):
        flows={}
        for name,response in responses.items():
            flows[name]={key:sum(r['accepted_total_veh'] for r in response['resource_allocations'] if r['kind']==kind and r['resource']==resource and r['end_sec']<=2250+end+1e-8)
                for key,kind,resource in [('incoming13','freeway_mainline_sending','FW_E:cell:13'),('outgoing18','freeway_mainline_sending','FW_E:cell:18'),('off10481','freeway_offramp_sending','10481')]}
            stock=sum(cases[name]['snapshots'][i]['n']['FW_E'][14:19]);initial=sum(cases[name]['snapshots'][0]['n']['FW_E'][14:19]);f=flows[name]
            error=abs(stock-initial-f['incoming13']+f['outgoing18']+f['off10481']);balances.append(error);assert error<1e-7
        old=next(r for r in cut['rows'] if r['case']=='selected' and r['horizon_sec']==end)
        rows.append(dict(horizon=end,native_outgoing_delta=old['outgoing18_detector_delta'],native_first_meter_stock_delta=old['outgoing18_first_meter_storage_delta'],
            baseline_outgoing_delta=old['outgoing18_model_delta'],candidate_outgoing_delta=flows['selected']['outgoing18']-flows['hold']['outgoing18'],
            native_stock_delta=old['native_region_stock_delta'],
            baseline_stock_delta=sum(original['selected']['snapshots'][i]['n']['FW_E'][14:19])-sum(original['hold']['snapshots'][i]['n']['FW_E'][14:19]),
            candidate_stock_delta=sum(cases['selected']['snapshots'][i]['n']['FW_E'][14:19])-sum(cases['hold']['snapshots'][i]['n']['FW_E'][14:19]),
            candidate_incoming_delta=flows['selected']['incoming13']-flows['hold']['incoming13'],candidate_off_delta=flows['selected']['off10481']-flows['hold']['off10481']))
    actual_omega=next(r for r in oldnative['rows'] if r['case']=='selected' and r['horizon_sec']==450)
    # Resolve the already qualified horizon report rather than rescan native data.
    horizons=read(HERE/'native_analysis_repaired_20261016/horizon_summary.json')
    omega_native=horizons['comparisons']['selected']['450']
    save(CAND/'assessment_schema.json',dict(native_comparison_keys=list(omega_native)))
    baseline_delta=original['selected']['ttt_veh_h']-original['hold']['ttt_veh_h']
    candidate_delta=cases['selected']['ttt_veh_h']-cases['hold']['ttt_veh_h']
    # Native delta retained from the completed qualified distribution assessment.
    native_delta=read(OUT/'distribution_assessment.json')['whole_omega_delta']['native']
    final=rows[-1]
    gates=dict(through_direction=final['candidate_outgoing_delta']>0,stock_direction=final['candidate_stock_delta']<0,
        through_error=abs(final['candidate_outgoing_delta']-final['native_outgoing_delta'])<abs(final['baseline_outgoing_delta']-final['native_outgoing_delta']),
        stock_error=abs(final['candidate_stock_delta']-final['native_stock_delta'])<abs(final['baseline_stock_delta']-final['native_stock_delta']),
        omega_contrast_error=abs(candidate_delta-native_delta)<abs(baseline_delta-native_delta),
        physical=all(x['physical_constraints'] for x in cases.values()),tag_conservation=max(done['max_tag_balance'],done['max_vsl_balance'],*balances)<1e-7)
    status='requires_independent_validation' if all(gates.values()) else 'rejected_fixed_cell15_refinement'
    result=dict(status=status,gates=gates,rows=rows,whole_omega_delta=dict(native=native_delta,baseline=baseline_delta,candidate=candidate_delta),
        absolute_model_ttt={name:dict(baseline=original[name]['ttt_veh_h'],candidate=cases[name]['ttt_veh_h']) for name in cases},
        seconds={name:dict(baseline=original[name]['seconds'],candidate=cases[name]['seconds']) for name in cases},
        max_balance=max(balances),max_route_tag_balance=done['max_tag_balance'],max_vsl_tag_balance=done['max_vsl_balance'],
        initial_stock_speed_parity=True,commands_fixed=True,source_pins=PINS,new_forecasts=2,new_native=0,new_fits=0,
        new_optimizer_runs=0,production_edits=0,candidate_adopted=False,goal_complete=False,
        limitations=['Parent FD calibration unchanged under finer spatial representation; explicit resolution hypothesis.',
                    'No independent or AD/NP/NUF optimization validation yet; not production-ready.',
                    'The detector is1m inside connector; one-meter storage corrections remain separate.'])
    save(OUT/'refine15_assessment.json',result)
    print(json.dumps({k:result[k] for k in ('status','gates','rows','whole_omega_delta','seconds','max_balance')},indent=2))


if __name__=='__main__':main()
