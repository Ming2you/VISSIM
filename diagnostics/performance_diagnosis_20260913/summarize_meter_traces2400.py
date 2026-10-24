"""Read the three completed raw captures; correct accounting identity with inside births."""
from pathlib import Path
import collections
import hashlib
import json
import math
import pickle

OUT=Path(__file__).with_name('lever_counterfactual2400')
p1=OUT/'meter_trace10490_attempt01/result.json';p2=OUT/'meter_trace10639_attempt01/result.json'
j=json.loads(p1.read_text(encoding='utf-8'));e=json.loads(p2.read_text(encoding='utf-8'))
assert j['completed'] and e['completed'] and not j['source_changes'] and not e['source_changes']
routes=e['input_generation_routes']
sources={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (p1,p2)}
summary={'schema':'same-state2400-meter-raw-response-audit/v1','completed':False,'new_endpoint_calls':0,
    'captured_endpoint_calls':3,'source_sha256':sources,'accounting_identity':'N_end = N_initial + generated_inside_Omega + boundary_entered - boundary_exited',
    'correction':'The earlier result.json closure_veh used an incomplete identity omitting inside generation. It is preserved as the diagnostic intermediate and does not establish a model accounting bug.',
    'TTT_definition':'Sum of captured inside_veh times existing stock-specific residence dt_h. Both urban and on-ramp residence are included.',
    'arms':{}}
cases={'hold':(j['arms']['hold'],p1.parent/'hold_captured_response.pickle'),
       'RM_C10490_g8':(j['arms']['g8'],p1.parent/'g8_captured_response.pickle'),
       'RM_C10639_g8':(e['g8'],p2.parent/'g8_captured_response.pickle')}
for name,(arm,path) in cases.items():
    raw=path.read_bytes();response=pickle.loads(raw)
    expected=arm.get('raw_response_file_sha256',e['raw_response_sha256'] if name=='RM_C10639_g8' else None)
    assert hashlib.sha256(raw).hexdigest()==expected
    sources[str(path.relative_to(OUT))]=expected
    result={'TTT_veh_h':arm['control_area']['ttt_veh_h'],'TD_veh':arm['control_area']['ttd_veh'],
        'TTT_by_stock_group_veh_h':arm['ttt_by_group_veh_h'],
        'TTT_by_ramp_connector_veh_h':{k:v for k,v in arm['ttt_by_stock_veh_h'].items() if k.startswith('ramp:')},
        'all_ramp_residence_duration_sec':arm['all_ramp_residence_duration_sec'],'windows':[],
        'binding_min_counts':arm['binding_counts'],'strict_meter_limit_times':arm['strict_request_binding_times']}
    for w in arm['windows']:
        born=collections.defaultdict(list)
        outside=collections.defaultdict(list)
        for r in response['transfers']:
            if r['end_sec']>w['end_sec'] or r['source'] is not None:continue
            route=routes[r['route_key']]
            assert type(route.get('target_inside')) is bool
            assert r['entered_veh']==0 and r['ttd_veh']==0
            (born if route['target_inside'] else outside)[r['route_key']].append(r['vehicles'])
        births={k:math.fsum(v) for k,v in born.items()};total=math.fsum(births.values())
        corrected=w['closure_veh']-total
        assert abs(corrected)<1e-7
        result['windows'].append({**{k:v for k,v in w.items() if k!='closure_veh'},
            'incomplete_formula_residual_veh':w['closure_veh'],'inside_generation_veh':total,
            'inside_generation_by_route':births,'outside_generation_veh':math.fsum(math.fsum(v) for v in outside.values()),
            'corrected_closure_veh':corrected})
    summary['arms'][name]=result
summary['RM_C10639']={'merge_cell':e['ramp_definition']['to_model_segment_index'],'same_traffic_captured':e['same_captured_traffic'],
    'query_count':len(e['g8']['query_T_f']),'available_stock_max_veh_per_T_f':max(r['available_veh_per_T_f'] for r in e['g8']['query_T_f']),
    'g8_request_veh_per_T_f':e['g8']['query_T_f'][0]['request_veh_per_T_f'],
    'effective_limiter':'available connector inventory in all45queries; g8 request never limits',
    'scope':'This is modeled arrival/availability at meter connector. Congested upstream or off-ramp vehicles are not all immediately dischargeable at this meter.'}
summary['RM_C10490']={'hold_query_binding_counts':j['arms']['hold']['binding_counts'],
    'g8_query_binding_counts':j['arms']['g8']['binding_counts'],'g8_strict_request_times':j['arms']['g8']['strict_request_binding_times'],
    'hold_request_veh_per_T_f':4.2,'g8_request_veh_per_T_f':3.24,
    'example2430_hold':next(r for r in j['arms']['hold']['query_T_f'] if r['start_sec']==2430.),
    'example2430_g8':next(r for r in j['arms']['g8']['query_T_f'] if r['start_sec']==2430.),
    'delta_ramp_TTT_veh_h':j['arms']['g8']['ttt_by_group_veh_h']['onramp_connector']-j['arms']['hold']['ttt_by_group_veh_h']['onramp_connector'],
    'delta_total_TTT_veh_h':j['arms']['g8']['control_area']['ttt_veh_h']-j['arms']['hold']['control_area']['ttt_veh_h']}
summary['scope']=['No native run or new physical calibration was performed. The average service cap is not the native10s RED/GREEN pulse.',
    'The model does respond to g8 and counts additional ramp residence when the cap limits. Exact E8g8 flatness is due to modeled availability below the service ceiling in this state.',
    'Inside generation closes the stock identity; TTT residence decomposition agrees with the endpoint. This rejects the specific omitted-ramp-TTT/simple-stock-closure hypotheses for the tested captures, not all model fidelity issues.',
    'The model already has a merge speed-effect term; capacity benefit or its accuracy must not be inferred merely from metering local sensitivity.',
    'Urban approach residence is part of urban_and_other; that group also contains other urban/off-ramp stocks. It is not a mutually exclusive on-ramp control-region inventory.']
summary['completed']=True
(OUT/'meter_trace_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 2400초 metering·Ω TTT 회계 확인','',
    '**정상 보존식은 N종료=N초기+Ω내발생+경계유입−경계유출이며, 이번3개모델응답은이식을1e−7대이내로만족한다.** 초안result.json의closure_veh는Ω내발생항을빼놓은진단식이었다. 원자료를보존하고이곳에서명시적으로정정한다. 모델재고계산오류로판정하지않는다.','',
    '| 구간 종료 | 초안 잔차 [대] | Ω 내 발생 [대] | 보정 후 잔차 [대] |', '|---:|---:|---:|---:|']
for w in summary['arms']['hold']['windows']:
    lines.append(f"|{w['end_sec']:.0f}|{w['incomplete_formula_residual_veh']:.9f}|{w['inside_generation_veh']:.9f}|{w['corrected_closure_veh']:.3g}|")
lines += ['',
    '발생원은기존내부input10개,shared69,input in_SC1_W/in_SC1001_W의13개이다. 생성은경계통과가아니므로entered/TTD에넣지않는다. Ω안에서태어난차량의재고와이후체류시간은계산한다.','',
    '| 2400–2850 모델 Ω TTT [veh·h] | hold | RM_C10490 g8 |', '|---|---:|---:|']
for group in ('mainline','urban_and_other','onramp_connector'):
    a=summary['arms']['hold']['TTT_by_stock_group_veh_h'][group];b=summary['arms']['RM_C10490_g8']['TTT_by_stock_group_veh_h'][group]
    lines.append(f'|{group}|{a:.9f}|{b:.9f}|')
lines += [f"|합계|{summary['arms']['hold']['TTT_veh_h']:.9f}|{summary['arms']['RM_C10490_g8']['TTT_veh_h']:.9f}|",'',
    '8개ramp connector의Ω내재고가모두각450초동안TTT에포함됐다. RM_C10490 g8은추가ramp TTT0.022822035veh·h를만들어전체TTT를0.023061152veh·h늘렸다. 미터가작동했는데램프대기시간을계산에서빼버린결과가아니다.',
    '',
    '**E8에합류하는RM_C10639는다르다.** 45개10초query모두유효min이connector재고였다. 모델상최대2대인데g8서비스는3.24대/10초여서요청상한에한번도걸리지않았다. hold와g8의모든transfer·residence·8개램프합류시계열·본선density·전체stock시계열이정확히일치했다. 평균450초합류총량만보고동률이라판정한것이아니다.',
    '',
    '**RM_C10490에서는모델이g8의효과를본다.** 2430초예를들면재고5대,본선수용상한19.269444대/10초,램프capacity4.2대/10초에대해g8요청3.24가최소였다. g8은총5개의T_f(2430,2440,2520,2530,2540초)에서서비스를직접제한했다. 결국450초총합류는같아도방출시각과체류시간은달라졌다.',
    '',
    '첫150초의Ω TTT는hold100.268653314,10490g8 100.267564367veh·h로작게감소하지만450초에서는증가한다. 같은한명령을450초유지한예측의일부이며,폐루프450초실측과같은명령이라고대조하지않는다.',
    '',
    '이는현재관측·도착예측·평균서비스모형의결과다. 실제VISSIM의RED/GREEN pulse,상류도착예측오차,merge효과계수의현실성은별도검증이필요하다. 도시접근재고는urban_and_other에포함되므로connector재고만보고전체램프권역혼잡이없다고판정하지않는다.',
    '', '각T_f의4개min항·T_u 도착/방출·stock별TTT·원시capture는`meter_trace10490_attempt01/`와`meter_trace10639_attempt01/`에보존했다. 최종수치와발생원분해는`meter_trace_summary.json`이다.']
(OUT/'meter_trace_summary.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'completed':True,'captured_endpoint_calls':3,'max_corrected_closure':max(abs(w['corrected_closure_veh']) for a in summary['arms'].values() for w in a['windows'])}))
