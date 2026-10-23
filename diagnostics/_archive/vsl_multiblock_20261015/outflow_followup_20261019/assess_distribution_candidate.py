"""Assess the predeclared one-forecast mean-speed hypothesis; no forecasts."""
import datetime
import gzip
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
HERE=OUT.parent
CAND=OUT/'distribution_candidate'
PINS={}
def read(path):
    blob=path.read_bytes();PINS[str(path)]=hashlib.sha256(blob).hexdigest()
    return json.loads(gzip.decompress(blob) if path.suffix=='.gz' else blob)
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')


def main():
    assert not (OUT/'distribution_assessment.json').exists()
    closure=read(CAND/'completion.json');assert closure['new_forecasts']==1 and closure['new_native']==0
    for p,h in closure['source_pins'].items(): assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,p
    candidate=read(CAND/'candidate_result.json')
    response=read(CAND/'selected_response.json.gz')
    baseline={r['name']:r for r in read(HERE/'matched_off2250_v3/summary.json')['results']}
    cut=read(OUT/'approach_flux.json')
    contract=read(OUT/'distribution_contract.json')
    rows=[]
    for i,end in enumerate((150,300,450),1):
        flow={key:sum(r['accepted_total_veh'] for r in response['resource_allocations']
                     if r['kind']==kind and r['resource']==resource and r['end_sec']<=2250+end+1e-8)
              for key,kind,resource in [('incoming13','freeway_mainline_sending','FW_E:cell:13'),
                                        ('outgoing18','freeway_mainline_sending','FW_E:cell:18'),
                                        ('off10481','freeway_offramp_sending','10481')]}
        stock=sum(candidate['snapshots'][i]['n']['FW_E'][14:19])
        assert abs(stock-sum(candidate['snapshots'][0]['n']['FW_E'][14:19])-flow['incoming13']+flow['outgoing18']+flow['off10481'])<1e-7
        old=next(r for r in cut['rows'] if r['case']=='selected' and r['horizon_sec']==end)
        row=dict(horizon=end,native_outgoing_delta=old['outgoing18_detector_delta'],
            native_first_meter_stock_delta=old['outgoing18_first_meter_storage_delta'],
            baseline_outgoing_delta=old['outgoing18_model_delta'],
            candidate_outgoing_delta=flow['outgoing18']-cut['cases']['hold']['model_cumulative'][str(end)]['outgoing18'],
            native_stock_delta=old['native_region_stock_delta'],
            baseline_stock_delta=sum(baseline['selected']['snapshots'][i]['n']['FW_E'][14:19])-sum(baseline['hold']['snapshots'][i]['n']['FW_E'][14:19]),
            candidate_stock_delta=stock-sum(baseline['hold']['snapshots'][i]['n']['FW_E'][14:19]))
        rows.append(row)
    final=rows[-1]
    direction_pass=final['candidate_outgoing_delta']>0 and final['candidate_stock_delta']<0
    assert abs(candidate['ttt_veh_h']-sum(candidate['costs'].values()))<1e-7
    costs={k:dict(baseline_delta=baseline['selected']['costs'][k]-v,candidate_delta=candidate['costs'][k]-v)
           for k,v in baseline['hold']['costs'].items()}
    report=dict(status='requires_independent_validation' if direction_pass else 'rejected_as_sufficient_response_correction',
        rows=rows,whole_omega_delta=dict(native=-.045833333333,baseline=baseline['selected']['ttt_veh_h']-baseline['hold']['ttt_veh_h'],candidate=candidate['delta_veh_h']),
        regional_model_cost_deltas=costs,seconds=candidate['seconds'],baseline_seconds=baseline['selected']['seconds'],
        initial_state_parity=closure['initial_stock_speed_parity'],commands_unchanged=closure['commands_fixed'],
        stock_balance_pass=True,physical_model_feasible=candidate['physical_constraints'],
        direction_gate_pass=direction_pass,candidate_adopted=False,new_forecasts=1,new_native=0,new_optimizer_runs=0,
        parameter_fits=0,production_edits=0,goal_complete=False,source_pins=PINS,
        limitations=['One conditional two-zone replay, no independent validation of this new candidate.',
                    'Population CDF mean correction omits variance, lane changes and composition selection.',
                    'No scalar/AD, NP/NUF optimization, or new native validation is claimed.'])
    save(OUT/'distribution_assessment.json',report)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    next_step=('Qualify unchanged input/source recipes for the existing67/71 pair before independent forecasts; no adoption yet.' if direction_pass else
        'Mean-actuation amplitude alone failed the local response-direction gate. Do not tune this multiplier or run its independent forecasts. Preserve native CDF contract and inspect missing spatial/variance state using existing lane/vehicle observations; no capacity bonus or new native.')
    record=dict(status=report['status'],updated_utc=now,app_goal_status='active',goal_complete=False,
        current_goal_turn='progress: verified native CDF actuator mismatch, eight algebraic tests and one bounded450s correction forecast; no duplicate baseline/native runs',
        new_native=0,new_forecasts=1,new_optimizer_runs=0,new_fzp_scans=0,new_fits=0,production_edits=0,
        candidate_adopted=False,remaining_native_budget=0,automation_status='PAUSED',next=next_step,
        evidence={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'distribution_contract.json',OUT/'distribution_candidate_protocol.json',CAND/'completion.json',OUT/'distribution_assessment.json')})
    save(OUT/'distribution_decision.json',record)
    for filename in ('plan.json','summary.json'):
        path=HERE/filename;backup=HERE/(path.stem+'_before_distribution_candidate_20261019.json')
        assert not backup.exists();backup.write_bytes(path.read_bytes())
        doc=read(path);doc['status']='offline_vsl_response_calibration_active';doc['app_goal_status']='active';doc['updated_utc']=now
        doc['distribution_followup_20261019']=record
        if filename=='plan.json': doc['next']=next_step
        save(path,doc)
    text=('\n\n## 2026-10-19 희망속도 분포 연결 검증\n\n'
          'INPX의90분포는 평균97.125·표준편차6.428km/h,110분포는평균112.275·표준편차12.254km/h이다. 현재Carlson속도배율90/110=.81818과 분포평균비율.86506은다르다. PTV문서에따르면차량은희망속도분포에서같은백분위를유지하므로90은모든차량의상한이아니다.\n\n'
          '분포평균만반영한속도성분배율1.05730후보를기존두구역90명령에서450초1회검사했다. 임계밀도·형상·보존·경계·도시/RM명령은유지했다. 이는새로운집계가설이며분산감소·추월/차로변경효과를표현한모델은아니다.\n\n'
          f"접근부통과량Δ는기존{final['baseline_outgoing_delta']:+.3f}대에서후보{final['candidate_outgoing_delta']:+.3f}대(실제+31대),재고Δ는기존{final['baseline_stock_delta']:+.3f}대에서후보{final['candidate_stock_delta']:+.3f}대(실제−30대)였다. 전체ΩTTTΔ는후보{candidate['delta_veh_h']:+.6f}대·시간이다. 상태: {report['status']}. 생산채택없음·추가native0·목표ACTIVE미완료.\n")
    (OUT/'distribution_README.md').write_text(text,encoding='utf8')
    with (HERE/'README.md').open('a',encoding='utf8') as f:
        f.write('\n\n희망속도분포 연결 후보의2026-10-19검증은[outflow distribution report](outflow_followup_20261019/distribution_README.md)에 기록했다. 최신인계는outflow_followup_20261019/distribution_decision.json이며 이전decision은역사로보존한다.\n')
    print(json.dumps({k:report[k] for k in ('status','rows','whole_omega_delta','seconds')},indent=2))


if __name__=='__main__': main()
