"""Summarize the finished eight-endpoint replay without rerunning any model."""
from pathlib import Path
import hashlib
import json

OUT=Path(__file__).with_name('lever_counterfactual2400')
path=OUT/'attempt02/result.json'
j=json.loads(path.read_text(encoding='utf-8'))
assert j['completed'] and j['endpoint_calls']==8 and not j['source_changes']
assert all(j['replay_checks'].values())
hold=j['rows'][0]
summary={'schema':'same-state2400-lever-counterfactual-summary/v1','completed':True,
         'new_endpoint_calls':0,'source_result_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'source_result':'attempt02/result.json','recorded_replay_checks':j['replay_checks'],
         'endpoint_calls_in_replay':8,'replay_wall_sec':j['wall_sec'],
         'window_sec':[2400,2850],'beta_seconds':0,'rows':[],
         'first150_metrics_available':False,
         'first150_reason':'Canonical public shared-owner batch retains450s aggregate control_area and releases its captured trajectory. Do not compare450s held prediction to450s closed-loop native as if commands match.',
         'native_claim':False,'whole63_candidate_domain_certified':False}
columns=('kind','id','sc_no','sg_no','green_sec','red_sec','amber_sec','offset','speed_kmh','start_sec','end_sec')
for row in j['rows']:
    changes={}
    for field,value in row['fields'].items():
        previous=hold['fields'][field]
        if isinstance(value,dict):
            changes[field]={key:{'before':previous.get(key),'after':v} for key,v in value.items() if previous.get(key)!=v}
        elif value!=previous: changes[field]={'before':previous,'after':value}
    physical=[]
    for old,new in zip(hold['command_rows'],row['command_rows']):
        # Metadata carries logical receipt fields; it is not a physical actuator.
        before={k:v for k,v in old.items() if k!='metadata'}
        after={k:v for k,v in new.items() if k!='metadata'}
        if before!=after: physical.append({'before':before,'after':after})
    family=j['families'].get(row['name'],{})
    owner=family.get('owner','SC6' if row['name']=='selected' else None)
    summary['rows'].append({'name':row['name'],'owner':owner,'family':family.get('family'),
        'TTT_veh_h':row['control_area']['ttt_veh_h'],'TD_veh':row['control_area']['ttd_veh'],
        'delta_TTT_veh_h':row['delta_objective_from_hold_veh_h'],
        'TTT_reduction_pct':-100*row['delta_objective_from_hold_veh_h']/hold['objective_veh_h'],
        'delta_owner_cost':row['delta_own_cost_from_hold'][owner] if owner else 0,
        'NP_veh':row['quantity_constraints']['np']['actual'],'NUF_veh_h':row['quantity_constraints']['nuf']['actual'],
        'feasible':row['feasible'],'seven_field_changes':{k:v for k,v in changes.items() if v},
        'physical_changes':physical,
        'aggregate_control_area_exact_to_hold':row['control_area']==hold['control_area'],
        'all_owner_costs_exact_to_hold':row['owner_costs']==hold['owner_costs']})
summary['findings']=[
    'At this state, the selected SC6 update predicts only0.2576362499veh*h improvement over held actual control (0.079008%).',
    'The first pure meter neighbor is green9, not green8. It changes physical output but all retained450s control_area aggregates and all owner costs equal hold for both W RM_C10480 and E RM_C10639.',
    'The first W VSL head0 move and its meter9 combination are aggregate ties. The first E VSL head0 move and its meter9 combination have the same tiny0.0009336061veh*h gain.',
    'All eight tested actions satisfy the original NP and NUF constraints and full implemented-model witness. These first-neighbor ties were not caused by an infeasibility filter.',
    'The selected urban own-cost gain0.2486083126 exceeds E own-cost gain0.0009336061, matching the recorded greatest-own-payoff partial-sweep commit policy.',
    'This does not establish whether g8, other ramps/VSL zones, combinations, or later states have material benefit.'
]
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 2400초 동일 상태: 실제 후보 8개 제한 재현','',
       'V3의 원래 상태·450초 수요 예측·직전 실제 명령·가격을 사용했다. NP cap2400, NUF2996.931387±40veh/h, β0을 유지했다. 새 가격 계산·GNE·VISSIM 실행은 없었다. 총36.17초에8개 물리 응답을 계산했다. 원기록의 hold NP/NUF·동서 own cost·selected Ω TTT가 모두1e−7 이내로 재현됐다.','',
       '| 후보 | Ω TTT [veh·h] | hold 대비 감소 [veh·h] | 후보 owner 비용 변화 | NP [대] | NUF [대/h] | 제약 |',
       '|---|---:|---:|---:|---:|---:|---|']
for r in summary['rows']:
    lines.append(f"|{r['name']}|{r['TTT_veh_h']:.9f}|{-r['delta_TTT_veh_h']:.9f}|{r['delta_owner_cost']:.9f}|{r['NP_veh']:.6f}|{r['NUF_veh_h']:.6f}|{'PASS' if r['feasible'] else 'FAIL'}|")
lines += ['',
    '실제 선택된 SC6 변경의 예상 Ω TTT 개선은 약0.079%였다. 처음 방문한 동측 VSL 변경의 예상 개선은약0.000286%였다. 모델이 큰 이득을 예상했는데 실행에서 전부 잃었다고 설명할 근거는 이2400초 결정에는 없다.',
    '',
    'W/E neighbor1은VSL+meter, neighbor2는VSL만, neighbor3는meter만이다. 첫meter 후보는RM_C10480(W) 또는RM_C10639(E)의g10→g9다. 양쪽모두실제명령은변하지만보존된450초통행집계·전체owner 비용은hold와정확히같았다. 서측첫VSL도동률이고, 동측VSL은작은개선만있어더큰SC6own-payoff개선에밀렸다.',
    '',
    '이결과는g8·나머지램프·다른VSL구역·다른시각까지무효라는뜻이아니다. 첫3개씩만재현했고모두feasible였다. 전체domain의효과한계나NUF가다른후보를막지않는다는증명이아니다.',
    '',
    '정본public batch는captured response를이용해450초집계와비용을만든뒤큰trajectory를해제한다. 이번출력에는첫150초TTT/TTD/종료재고가없다. 450초held예측을150초마다명령이바뀌는native450초와바로같은명령의예측오차라고대조하지않는다.',
    '',
    '초기실패(endpoint0)는부모폴더의result/receipt에남았다. 기록JSON이native clock 내부tuple을list로저장한문제였다. attempt02는모든native node JSON값이정확히같음을검사한후컨테이너형식만복원해정본가격installer를통과했다. 원본가격·값·기록SHA는바꾸지않았다.',
    '', '상세원본·7필드·213행실행표·입력/응답SHA: `attempt02/result.json`. 중립집계: `summary.json`.']
(OUT/'summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'completed':True,'rows':len(summary['rows'])}))
