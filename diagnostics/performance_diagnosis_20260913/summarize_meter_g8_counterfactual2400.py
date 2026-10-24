"""Summarize the completed9-endpoint g8 comparison; no new model evaluation."""
from pathlib import Path
import hashlib
import json

OUT=Path(__file__).with_name('lever_counterfactual2400')/'meter_g8_attempt01'
source=OUT/'result.json'
j=json.loads(source.read_text(encoding='utf-8'))
assert j['completed'] and j['endpoint_calls']==9 and not j['source_changes'] and all(j['replay_checks'].values())
hold=j['rows'][0]
summary={'schema':'physical-meter-g8-single-change-summary/v1','completed':True,
    'source_result_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'new_endpoint_calls':0,
    'replay_endpoint_calls':9,'replay_checks':j['replay_checks'],'window_sec':[2400,2850],
    'native_execution':False,'TTT_unit':'veh*h','NUF_unit':'veh/h','NP_cap_veh':2400.,'NUF_target_veh_h':2996.9313872526645,
    'NUF_tolerance_veh_h':40.,'rows':[],
    'scope':'Each ramp changes g10->g8 alone; original actual-command box and other7meters/VSL/green/offset unchanged. Model prediction for one recorded state only.'}
for row in j['rows'][1:]:
    mid=row['name'];ctx=j['ramp_context'][mid];owner=j['canonical_candidate_indices'][mid]['owner']
    before=next(r for r in hold['physical_meter_rows'] if r['id']==mid)
    after=next(r for r in row['physical_meter_rows'] if r['id']==mid)
    assert before['green_sec']==10 and after['green_sec']==8
    region=j['existing_projected_observation_regions'][mid]
    before_merge=hold['quantity_constraints']['physical_ramp_merge']['accepted_vehicles_by_ramp']
    after_merge=row['quantity_constraints']['physical_ramp_merge']['accepted_vehicles_by_ramp']
    summary['rows'].append({'ramp':mid,'owner':owner,'candidate_index':j['canonical_candidate_indices'][mid]['candidate_index'],
        'lane_count':ctx['definition']['lane_count'],'initial_connector_queue_veh':ctx['initial_connector_queue_veh'],
        'observed_region':region,'upstream_movement_queue_veh':ctx['upstream_movement_queue_veh'],
        'service_hold_veh_h':ctx['service_hold_veh_h'],'service_g8_veh_h':ctx['service_g8_veh_h'],
        'predicted_accepted_merge450_hold_veh':before_merge[mid],
        'predicted_accepted_merge450_g8_veh':after_merge[mid],
        'delta_TTT_veh_h':row['delta_TTT_veh_h'],'delta_TD_veh':row['delta_TD_veh'],
        'delta_NUF_veh_h':row['delta_NUF_veh_h'],'delta_own_cost':row['delta_owner_cost'][owner],
        'feasible':row['feasible'],'all_aggregate_control_area_equal_hold':row['all_aggregate_control_area_equal_hold'],
        'all_owner_costs_equal_hold':row['owner_costs']==hold['owner_costs'],
        'physical_command_before':before,'physical_command_after':after,
        'accepted_merge450_changes_by_ramp':{r:after_merge[r]-before_merge[r] for r in after_merge if after_merge[r]!=before_merge[r]}})
summary['findings']=[
    'All8 pure g8 commands exist in the canonical63-candidate owner neighborhoods at interleaved indexes6/12/18/22, outside the first3 inspected neighbors.',
    'Six commands give exactly equal retained control_area aggregates and all19owner costs. RM_C10644 andRM_C10490 increase modeled TTT and own cost slightly. None improves TTT.',
    'All8 candidates satisfy the unchanged NP/NUF constraints, model witness, and213-row physical command checks. NUF rejection is not the reason these tested single-meter moves lack benefit.',
    'Each treated ramp450s accepted merge total is unchanged. Two candidates still alter TTT and downstream quantities, so unchanged aggregate throughput does not imply identical timing/traffic.',
    'Service table capacity is not desired demand or actual observed native output.1lane1512->1166.4veh/h and2lane3024->2332.8veh/h are model ceilings; effective release also depends on stock/arrivals/receiving/travel.',
    'This one-state result does not establish multi-meter joint moves, stronger future steps, other states, or native g8 response.'
]
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 2400초: 8개 미터 각각g8 단독 검증','',
    '동일 실제 관측·450초 예측·기록 가격·NP cap2400·NUF2996.931387±40veh/h를 유지했다. 다른7개 미터와VSL·도시 green·offset은hold와같다. 정본 후보 생성기에서각g8이실제로존재하고213행중해당미터한행만바뀌는지확인했다.9개응답을37.985초에계산했고기준TTT·NP·NUF·own cost는원기록과일치했다.','',
    '| 미터 | 차로 | 서비스 상한 g10→g8 [대/h] | 초기 connector 재고 | 예측450초 합류: hold=g8 [대] | ΔTTT [veh·h] | Δown cost | 제약 |',
    '|---|---:|---:|---:|---:|---:|---:|---|']
for r in summary['rows']:
    assert r['predicted_accepted_merge450_hold_veh']==r['predicted_accepted_merge450_g8_veh']
    lines.append(f"|{r['ramp']}|{r['lane_count']}|{r['service_hold_veh_h']:.1f}→{r['service_g8_veh_h']:.1f}|{r['initial_connector_queue_veh']:.0f}|{r['predicted_accepted_merge450_g8_veh']:.6f}|{r['delta_TTT_veh_h']:.9f}|{r['delta_own_cost']:.9f}|{'PASS' if r['feasible'] else 'FAIL'}|")
lines += ['',
    '**6개는정확한집계·비용동률,2개는작은손해이며TTT를개선하는단독g8명령은없었다.** 이2400초기록에서g8을방문하지않았다는사실만으로큰개선을놓쳤다고설명할수없다. 반면g8의VISSIM응답이나다른시각까지무효라고결론낼수도없다.',
    '',
    '두비동률명령도해당램프450초예측합류총량은변하지않았다. RM_C10644는다른램프의작은파급으로전체NUF+0.000407veh/h,RM_C10490은−0.014824veh/h이며모두±40안이다. 통과총량이같아도방출시각과재고시간은다를수있으므로평균합류량만으로전체동역학동률을판정하지않는다.',
    '',
    '표의초기재고는connector만이다. 접근링크차량전체를램프행으로보지않았다. 예를들어RM_C10644권역43대에는해당램프행40·다른램프행2·현재경로상램프없음1대가포함된다. 원시관측으로구분한8개권역과별도도시movement재고는result.json에보존했다.',
    '',
    '서비스상한1512/1166.4는모형의차로당평균서비스표다. 희망수요나VISSIM실측방출량이아니다. 이검증은원래모델을유지한한시점의예측민감도이며포화방출표의현실적타당성을증명하지않는다.',
    '', '원자료·입력SHA·모델보존검사·각미터정본후보index·실행행: `result.json`. 간략기계판독값: `summary.json`.']
(OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'completed':True,'ramps':len(summary['rows'])}))
