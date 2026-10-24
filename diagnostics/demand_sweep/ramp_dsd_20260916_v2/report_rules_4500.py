"""Post-run4500s comparison; no live COM or repeated trajectory scans."""
import csv
import argparse
import json
from pathlib import Path
from datetime import datetime
import report_rules

HERE=Path(__file__).resolve().parent/'rules_4500_v1'
ARMS=('none','rm','vsl','both')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(head,data):return ['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|',*['|'+'|'.join(map(str,r))+'|' for r in data]]


def main():
    verification=load(HERE/'verification.json')
    comparison=load(HERE/'analysis/comparison.json')['arms']
    result={}
    for arm in ARMS:
        assert verification[arm]['same_policy_previous3000_prefix_exact']['passed']
        area=rows(HERE/f'analysis/{arm}/area_timeseries.csv')
        stocks=rows(HERE/f'analysis/{arm}/stocks_1s.csv')
        ramp_rows=rows(HERE/f'analysis/{arm}/ramp_150s.csv')
        links=rows(HERE/f'analysis/{arm}/freeway_links_150s.csv')
        decisions=[load(HERE/f'run_{arm}/decision_{t}.json') for t in range(900,4500,150)]
        policy=load(HERE/f'prepared_{arm}/rule_policy.json')
        receipt=load(HERE/f'run_{arm}/run.json')
        assert len(area)==len(stocks)==4500
        def window(a,b):
            first=area[a-1] if a else {'ttt_veh_h_cumulative':0,'ttd_observed_plus_terminal_cumulative':0}
            last=area[b-1]
            return {'omega_ttt_veh_h':float(last['ttt_veh_h_cumulative'])-float(first['ttt_veh_h_cumulative']),
                'ttd_events':int(last['ttd_observed_plus_terminal_cumulative'])-int(first['ttd_observed_plus_terminal_cumulative']),
                'loss_events':sum(int(r['unresolved_inside_disappearances']) for r in area[a:b]),
                'observed_entry_events':sum(int(r['observed_entry_events']) for r in area[a:b]),
                'appeared_inside_events':sum(int(r['appeared_inside_events']) for r in area[a:b])}
        def integral(key,a,b):
            values=[float(r[key]) for r in stocks[max(0,a-1):b]]
            if a==0:values.insert(0,0.)
            return (sum(values)-(values[0]+values[-1])/2)/3600
        windows={f'{a}_{b}':window(a,b) for a,b in ((0,2250),(2250,4500),(0,4500),(900,4500),(3000,4500))}
        components={f'{a}_{b}':{d:integral(d+'_n',a,b) for d in ('FW_E','FW_W')} for a,b in ((0,4500),(2250,4500))}
        full_parts=dict(components['0_4500'])
        full_parts['on_ramp_connectors']=sum(integral(f"ramp_{s['connector']}_n",0,4500) for s in policy['meters'].values())
        full_parts['remaining_omega']=windows['0_4500']['omega_ttt_veh_h']-sum(full_parts.values())
        ramps={}
        for mid,spec in policy['meters'].items():
            selected=[r for r in ramp_rows if int(r['ramp'])==spec['connector'] and int(r['start_s'])>=2250]
            ramps[mid]={'merges_2250_4500':sum(int(r['merges']) for r in selected),
                'arrivals_2250_4500':sum(int(r['ramp_arrivals']) for r in selected),
                'max_stock_2250_4500':max(int(r['ramp_max_n']) for r in selected),
                'stopped_veh_h_2250_4500':sum(float(r['ramp_stopped_vehicle_seconds']) for r in selected)/3600,
                'final_stock':int(stocks[-1][f"ramp_{spec['connector']}_n"]),
                'final_green':decisions[-1]['meters'][mid]['green_sec'],
                'minimum_green':min(d['meters'][mid]['green_sec'] for d in decisions),
                'first_green2_s':next((d['sec'] for d in decisions if d['meters'][mid]['green_sec']==2),None) if arm in ('rm','both') else None,
                'first_restriction_s':next((d['sec'] for d in decisions if d['meters'][mid]['green_sec']<10),None) if arm in ('rm','both') else None,
                'restricted_seconds':sum(150 for d in decisions if d['meters'][mid]['green_sec']<10) if arm in ('rm','both') else 0}
        exposure={zone:sum(150 for d in decisions if d['history']['vsl'].get(str(ids[0]),120)<120)
            for zone,ids in policy['zone_dsds'].items()}
        tail={link:{'speed_4350_4500':float(next(r for r in links if r['link']==link and int(r['start_s'])==4350)['mean_speed_kmh']),
            'slow_veh_h_2250_4500':sum(float(r['slow_veh_h']) for r in links if r['link']==link and int(r['start_s'])>=2250)} for link in ('74','2','10613','119','10702','26','120')}
        result[arm]={'windows':windows,'freeway_components':components,'ramps':ramps,'tail_links':tail,
            'whole_period_components':full_parts,
            'end_omega_stock':int(area[-1]['inside_vehicles']),
            'omega_stock_2250':int(area[2249]['inside_vehicles']),
            'vsl_restricted_seconds':exposure,'native_uninserted':comparison[arm]['native_uninserted_at_end'],
            'native_removal_warnings':comparison[arm]['native_removals'],
            'wall_seconds':(datetime.fromisoformat(receipt['finished'])-datetime.fromisoformat(receipt['started'])).total_seconds()}
    for arm,r in result.items():
        for key,w in r['windows'].items():w['ttt_improvement_pct']=100*(1-w['omega_ttt_veh_h']/result['none']['windows'][key]['omega_ttt_veh_h'])
    (HERE/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    text=['# 동일 룰 제어4조건:4500초 연장 검증','',
        '사용자 수정 기하+8램프 DSD120, 동측 본선 입력1098만0.8배. seed13. 수요·경로·기준 신호·검지 위치·정책을 유지하고 SimBreak만4500초로 연장했다. SimPeriod9001 유지.',
        '0–900초 native 무제어, 이후150초마다ALINEA/규칙 VSL을 갱신한다. 고정 명령2250초 실험과 구분한다. 이전3000초 룰 실험과 조건별 전체 FZP 데이터 행이 정확히 일치했다.','',
        '## 판단','',
        f"4500초로 늘려 보니 RM의 Ω TTT 감소율은 전체{result['rm']['windows']['0_4500']['ttt_improvement_pct']:.2f}%, 후반2250–4500초{result['rm']['windows']['2250_4500']['ttt_improvement_pct']:.2f}%다. 이전3000초의0.21%보다 커졌다. 10490에서2초 녹색에 처음 도달한 시점도{result['rm']['ramps']['RM_C10490']['first_green2_s']}초여서2250초 종료는 강한 제한 이후의 반응을 충분히 담지 못했다.",
        '동측 본선 혼잡 완화는 관측됐다. 다만 RM의 서측 체류시간과 램프 대기는 늘고, 미삽입도300대 많았다. Ω 밖 미생성 차량의 기다림은 현재 TTT에 포함되지 않는다. 따라서1.60%를 동일한 서비스 수요 전체의 확정적 개선이라고 단정하지 않는다.',
        'VSL과 동시 제어는 종료 직전 동측 하류119·10702의 속도를 회복시키지만, 전체 Ω TTT는 무제어보다 높다. 병목 국소 효과와 전체 비용을 구분해야 한다. 현재 규칙/검지 배치의 결과이며 VSL 자체가 무효라는 결론은 아니다.','',
        '## Ω 체류시간','',*table(['조건','0–4500 TTT[veh·h]','개선율','0–2250 개선율','2250–4500 개선율','TTD사건','종료Ω재고'],[
            [a,f"{r['windows']['0_4500']['omega_ttt_veh_h']:.2f}",f"{r['windows']['0_4500']['ttt_improvement_pct']:+.2f}%",
             f"{r['windows']['0_2250']['ttt_improvement_pct']:+.2f}%",f"{r['windows']['2250_4500']['ttt_improvement_pct']:+.2f}%",
             r['windows']['0_4500']['ttd_events'],r['end_omega_stock']] for a,r in result.items()]),'',
        'TTT는 고속도로+도시 protected network Ω 내부 차량시간. TTD는 살아서Ω 밖으로 이동한 사건 및 물리적 말단 유출 추정이다. 비정상 소실·종료잔여는 TTD에서 제외한다.','',
        '## 전체4500초 TTT 분해[veh·h]','',*table(['조건','동측 본선','서측 본선','8개on-ramp connector','나머지Ω'],[
            [a,*[f"{r['whole_period_components'][k]:.2f}" for k in ('FW_E','FW_W','on_ramp_connectors','remaining_omega')]] for a,r in result.items()]),'',
        'RM의 동측 본선 절감123.38veh·h 중 서측 증가49.13veh·h와 램프 증가13.61veh·h가 상당 부분을 상쇄했다. 접근도로는 혼합 목적지여서 on-ramp connector 항에 무조건 포함하지 않는다.','',
        '## 2250초 이후10490 램프','',*table(['조건','실제 도착','실제 합류','최대 재고','정지 차량시간[veh·h]','종료 재고','마지막 녹색[s/10s]'],[
            [a,r['ramps']['RM_C10490']['arrivals_2250_4500'],r['ramps']['RM_C10490']['merges_2250_4500'],r['ramps']['RM_C10490']['max_stock_2250_4500'],
             f"{r['ramps']['RM_C10490']['stopped_veh_h_2250_4500']:.2f}",r['ramps']['RM_C10490']['final_stock'],r['ramps']['RM_C10490']['final_green'] if a in ('rm','both') else 'native OFF'] for a,r in result.items()]),'',
        '도착은 connector에 실제 들어온 차량이다. 설정된 희망 수요가 아니며, 접근도로의 모든 차량을 램프행으로 취급하지 않는다.','',
        '## 8개 미터 작동 및 실제 합류','',*table(['램프','RM 첫 제한[s]','RM 최소/최종녹색','2250–4500 합류 무제어/RM','RM 종료재고','동시제어 최소/최종녹색'],[
            [mid,result['rm']['ramps'][mid]['first_restriction_s'],
             f"{result['rm']['ramps'][mid]['minimum_green']}/{result['rm']['ramps'][mid]['final_green']}",
             f"{result['none']['ramps'][mid]['merges_2250_4500']}/{result['rm']['ramps'][mid]['merges_2250_4500']}",
             result['rm']['ramps'][mid]['final_stock'],
             f"{result['both']['ramps'][mid]['minimum_green']}/{result['both']['ramps'][mid]['final_green']}"] for mid in result['rm']['ramps']]),'',
        '## 종료 직전 본선 속도[4350–4500s 평균km/h]','',*table(['조건','동측2','동측10613','동측119','동측10702','서측120'],[
            [a,*[f"{r['tail_links'][k]['speed_4350_4500']:.1f}" for k in ('2','10613','119','10702','120')]] for a,r in result.items()]),'',
        '![공간별 속도 변화](freeway_speed.png)','','![재고 변화](stocks.png)','',
        '## 손실과 실행 검증','',*table(['조건','Ω 미확인 소실','native 삭제경고','종료 미삽입','런 경과[s]'],[
            [a,r['windows']['0_4500']['loss_events'],r['native_removal_warnings'],r['native_uninserted'],f"{r['wall_seconds']:.1f}"] for a,r in result.items()]),'',
        '삭제경고와 미확인 소실은 중복 가능하므로 합산하지 않는다. 미삽입은 Ω TTT 밖이므로 실제 유입 차이와 함께 판단해야 한다. 단일 seed이므로 작은 개선은 확정하지 않는다.',
        'RM의 추가 미삽입은 도시 입력1102(link32) +245대, 서측 본선1099(link26) +81대가 주를 이룬다. 동측 본선1098(link74)은34대 감소했다. 입력별 native 종료 경고를 별도input_pending_comparison.json에 보존했다.',
        '',*table(['조건','Ω 경계 실제 진입사건','Ω 안 최초 관측'],[
            [a,r['windows']['0_4500']['observed_entry_events'],r['windows']['0_4500']['appeared_inside_events']] for a,r in result.items()]),'',
        '모든 대상신호는 native LDP·적용readback, VSL은 적용readback, 정책은 기록된 검지값 재생으로 검증했다. 매초 차량COM 전수조회·MPC/GNE 계산은 없다. 사후분석은4개 런 종료 후 수행했다.',
        '이번 비교는 기존 규칙정책의 시간 연장이다. 입력40m VSL 검지기에 초기 가속과 입구 혼잡이 섞이는 한계는 그대로이며, VSL의 최적 배치나 보정된 MPC 성능을 검증한 결과로 확대하지 않는다.',
        '4500초에 잔여혼잡이 있으면 회복을 입증한 것이 아니다. 수요를 줄이거나 종료시각에 차량을 지우지 않았다.','',
        '세부자료:summary.json,verification.json,analysis/*/area_timeseries.csv,stocks_1s.csv,ramp_150s.csv,freeway_links_150s.csv.']
    (HERE/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    report_rules.HERE=HERE;report_rules.plot(HERE/'analysis',4500)
    print(json.dumps({a:r['windows']['0_4500'] for a,r in result.items()},indent=2))


def summarize_new_suite(folder):
    """Use the same accounting for later seeds and the diagnostic MPC bank."""
    comparison=load(folder/'analysis/comparison.json')['arms']
    verification=load(folder/'verification.json')
    result={}
    for arm in ARMS:
        assert verification[arm]['ldp_and_readback_passed']
        a=comparison[arm]
        area=rows(folder/f'analysis/{arm}/area_timeseries.csv')
        stocks=rows(folder/f'analysis/{arm}/stocks_1s.csv')
        policy=load(folder/f'prepared_{arm}/rule_policy.json')
        decisions=[load(folder/f'run_{arm}/decision_{t}.json') for t in range(900,4500,150)]
        receipt=load(folder/f'run_{arm}/run.json')
        def integral(key):
            values=[0.]+[float(r[key]) for r in stocks]
            return (sum(values)-(values[0]+values[-1])/2)/3600
        parts={road:integral(road+'_n') for road in ('FW_E','FW_W')}
        parts['on_connectors']=sum(integral('ramp_'+str(r['connector'])+'_n') for r in policy['meters'].values())
        total=next(w for w in a['windows'] if w['start_s']==0 and w['end_s']==4500)
        late=next(w for w in a['windows'] if w['start_s']==2250 and w['end_s']==4500)
        parts['remaining_omega']=total['omega_ttt_veh_h']-sum(parts.values())
        rm={mid:{'minimum_green':min(d['meters'][mid]['green_sec'] for d in decisions),
            'first_restriction':next((d['sec'] for d in decisions if d['meters'][mid]['green_sec']<10),None),
            'final_green':decisions[-1]['meters'][mid]['green_sec']} for mid in policy['meters']}
        vsl={z:{'minimum':min(d['history']['vsl'].get(str(ids[0]),120) for d in decisions),
            'restricted_seconds':sum(150 for d in decisions if d['history']['vsl'].get(str(ids[0]),120)<120)} for z,ids in policy['zone_dsds'].items()}
        result[arm]={'total':total,'late':late,'components':parts,'rm':rm,'vsl':vsl,
            'end_omega_n':int(area[-1]['inside_vehicles']),
            'uninserted':a['native_uninserted_at_end'],'native_removals':a['native_removals'],
            'wall_seconds':(datetime.fromisoformat(receipt['finished'])-datetime.fromisoformat(receipt['started'])).total_seconds()}
        if 'mpc' in decisions[0]:
            audits=[load(folder/f'run_{arm}/mpc_candidates_{t}.json') for t in range(900,4500,150)]
            result[arm]['mpc']={'changed_decisions':sum(d['mpc']['selected']!='hold' for d in decisions),
                'selection':[{'sec':d['sec'],**d['mpc']} for d in decisions],
                'control_calculation_seconds':sum(a['control_calculation_sec'] for a in audits),
                'observation_seconds':sum(a['observation_sec'] for a in audits),
                'initialization_seconds':sum(a['model_initialization_sec'] for a in audits),
                'maximum_decision_calculation_seconds':max(a['control_calculation_sec'] for a in audits)}
    for arm,r in result.items():
        r['improvement_pct']=100*(1-r['total']['omega_ttt_veh_h']/result['none']['total']['omega_ttt_veh_h'])
    (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines=['# 4500초 독립 seed 비교','',
        '새 사용자 기하·DSD120·동측 본선 입력만0.8, seed23. 0–900초 native,150초 제어 갱신. 물리 망·수요·도시 신호는 조건 사이 동일.','']
    lines+=table(['조건','Ω TTT[veh·h]','개선[%]','TTD','종료Ω재고','미삽입','삭제경고'],[
        [a,f"{r['total']['omega_ttt_veh_h']:.2f}",f"{r['improvement_pct']:.2f}",r['total']['omega_exit_events_observed_plus_terminal_inferred'],r['end_omega_n'],r['uninserted'],r['native_removals']] for a,r in result.items()])
    lines+=['','## TTT 공간 분해','']+table(['조건','동측','서측','on connectors','나머지Ω'],[
        [a,*[f'{v:.2f}' for v in r['components'].values()]] for a,r in result.items()])
    lines+=['','MPC가 있는 경우: 기존 물리 plant의 작은 중앙집중 후보 비교다. 예측 비용은 본선+16개connector 및 예측한 미진입 대기이며, 도시부 전체 Ω를 예측하는 full GNE가 아니다. 실제 성능 표는 모든 조건에서 같은 Ω로 산정했다.',
        '단일 seed이며 미삽입·삭제 차이를 개선으로 오인하지 않는다. TTD에서 비정상 소실과 종료잔여를 제외했다. 상세 명령과 계산시간은 summary.json에 있다.',
        '','![구간 속도](freeway_speed.png)','![재고](stocks.png)']
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    report_rules.HERE=folder;report_rules.plot(folder/'analysis',4500)


def validate_new_seed(observations,runs):
    """Frozen seed13 calibration scored on seed23 without any refitting."""
    import evaluate_response as e
    root=Path(__file__).resolve().parent
    out=observations/'frozen_model_validation';out.mkdir(exist_ok=False)
    data={a:e.ObservationData(observations/a) for a in ARMS}
    old=root/'controller_response_v1/model_v2';new=root/'controller_response_4500_v1/model_v4'
    profile=e.load(new/'port_profile.json')
    result={}
    for name,source in [('previous',old),('dynamics_only',new.parent/'model_v3'),('calibrated',new)]:
        model=e.load_base_model(data['none'].geometry,source/'config.json')
        params=e.load(source/'selected_parameters.json')['parameters']
        records=[]
        for arm in ARMS:
            for t in (2250,3150,4050):
                w=e.window(data[arm],model,t,'history_forecast',profile,e.rule_commands(arm,runs,4500))
                prediction=e.simulate(model,w,params)
                scores={r:e.score_rollout(data[arm],t,prediction,r) for r in model.roads}
                assert not any(s['invalid'] for s in scores.values())
                records.append({'arm':arm,'cutoff':t,'scores':scores,
                    'prediction':e.component(data[arm],model,t,prediction),'actual':e.component(data[arm],model,t)})
        result[name]=records
    e.save(out/'comparison.json',result)
    e.save(out/'protocol.json',{'seed':23,'refitting':False,'latest_observation':'each cutoff',
        'command_policy':'Recorded future command replay to test plant; not prediction of future feedback decisions',
        'scope':'42mainline+16connector component; not Omega'})
    print('Frozen models evaluated on new seed',flush=True)


def consolidated_report():
    import statistics
    root=Path(__file__).resolve().parent
    suites={k:load(root/f'{k}_4500_s23_v1/summary.json') for k in ('rules','mpc')}
    validation=load(root/'mpc_4500_s23_v1/verification.json')
    assert validation['instrumentation_continuous_execution_equivalence']['passed']
    forecast=load(root/'controller_response_s23_v1/frozen_model_validation/comparison.json')
    paired=load(root/'paired_response_after_calibration.json')
    decision=load(root/'mpc_decision_audit_s23.json')
    entries=[('무제어',suites['rules']['none'])]+[(kind+' '+arm,suites[kind][arm]) for kind in suites for arm in ('rm','vsl','both')]
    lines=['# Plant 보정 및 규칙 제어·MPC 실제 실행 비교','',
        '2026-09-16. 완료: seed13 4500초 자료로 보정, 계수 동결 후 seed23에서 규칙 4조건과 작은 중앙집중 MPC 4조건을 각각 4500초 실행했다. 모든 native 실행·LDP/readback·정책 재생 검증을 통과했다.',
        '현재 가장 유망한 관측 결과는 MPC VSL 단독의 Ω TTT 2.07% 감소다. RM과 동시 제어의 전체 개선은 작다. 보정 모델의 제어 응답 크기·순위 검증은 여전히 불충분하므로 정본 성능 검증 완료로 판정하지 않는다.','',
        '## 동일 조건과 범위','',
        '사용자 수정 가속거리·8램프 DSD120 망, 동측 본선 입력1098만0.8배, seed23. 과거 전역80/도시50 조건이 아니다. 네트워크·도시 신호·수요·경로는 모든 조건에서 같다. 0–900초 native, 150초마다 갱신, SimPeriod9001을 유지하고 SimBreak4500에서 종료했다.',
        '규칙군은 기존 ALINEA와 규칙 VSL을 유지했다. MPC군은 본선42셀+8진입/8진출connector 및 예측한 미진입 대기 비용으로 명령을 선택한다. 450초/3개150초 제어 움직임을 예측하고 첫 명령만 적용한다. 미터10초 RG, 녹색2–10초, 직전 실제 명령 대비±2초. VSL은 기본 분포120에서 한 갱신당20씩 변경한다. 분포 ID는 모든 차량의 고정 주행속도가 아니다.',
        'MPC는 개별 제한·일괄 해제와 일부 결합 후보를 비교하는 진단이다. 전체 결합 공간이나 홀수 녹색을 모두 탐색하지 않는다. 도시 전체 Ω 동역학·green/offset·N_P/N_UF 게임 제약을 포함한 full GNE는 아직 연결하지 않았다. 기존 지원 차단은 유지했다.',
        '## 실제 0–4500초 결과','']
    lines+=table(['조건','Ω TTT[veh·h]','개선[%]','TTD 사건','종료Ω재고','미삽입','Ω 미확인 소실'],[
        [name,f"{r['total']['omega_ttt_veh_h']:.2f}",f"{r['improvement_pct']:+.2f}",r['total']['omega_exit_events_observed_plus_terminal_inferred'],r['end_omega_n'],r['uninserted'],r['total']['unresolved_inside_disappearances']] for name,r in entries])
    lines+=['','TTT는 Ω=고속도로+도시 protected network 내부 차량시간이다. 살아서 non-control area로 이동한 사건도 TTD에 포함한다. 비정상 소실·종료잔여는 제외하고, 물리적 말단 유출 추정은 별도 정의에 따라 포함한다. 미삽입 차량의 외부 기다림은 실제 Ω TTT 밖이다. 미확인 소실과 native 삭제경고는 겹칠 수 있어 합산하지 않는다.','',
        'MPC VSL은 무제어보다 TTD231대 증가, 미삽입28대 감소, 미확인 소실8대 감소다. native 삭제경고는260→267건으로 증가했다. 단일 seed 결과이므로 안정적인2.07% 개선이나 손실 없는 개선으로 단정하지 않는다. MPC RM은 미삽입67대·미확인 소실18대가 늘어0.27%의 작은 감소를 확정적인 제어 이득으로 볼 수 없다.',
        '## 혼잡·램프 반응','']
    lines+=table(['조건','동측 TTT','서측 TTT','8on connector TTT','나머지Ω TTT'],[
        [name,*[f'{v:.2f}' for v in r['components'].values()]] for name,r in entries])
    lines+=['','무제어는10702에서 시작한 저속 구간이119·10613으로 상류 확대되는 패턴을 보인다. 링크 평균속도40km/h 미만이2개150초 구간 연속인 첫 시각은 각각2700/3150/3300초다. 이는 공간 패턴이며 차량별 병목 원인 확정은 아니다.',
        'ALINEA는10490의2250–4500초 합류를481→371대로 줄였다. 최대connector재고15→40대, 정지 차량시간0.23→6.96veh·h로 늘었다.10613의 지속 저속은 완화됐지만10702의 혼잡은 남았고, 별도 상류10699의 저속은 더 일찍 나타났다. 동측 TTT14.65veh·h 감소 중 서측8.27와on connector4.17veh·h 증가가 상당 부분을 상쇄했다.',
        'MPC VSL의 감소77.71veh·h 중 동측 본선 감소가70.48veh·h다.10613·10699로의 저속 확대가 줄었지만10702는 종료까지 저속이 남는다. 전망450초에서 비용이 낮은 후보를 선택했다는 사실만으로 이 실제 이득을 모델이 정확히 예측했다고 보지 않는다.',
        'MPC VSL은 실제로100 분포까지만 제한했다. 서측seg0은1200–1500/3300–3450초, 동측seg5는2400–2850/3600–3900/4350–4500초, 동측seg0은3750–3900초 제한했다. 규칙 VSL의 동·서 입력부60 분포 장기 유지와 다르다. 특정 구간 하나의 인과효과를 분리한 실험은 아니다.',
        '![규칙 제어 공간별 속도](rules_4500_s23_v1/freeway_speed.png)','',
        '![MPC 공간별 속도](mpc_4500_s23_v1/freeway_speed.png)','',
        '## 보정한 항목과 독립 seed 예측','',
        'seed13에서만 보정했다. 동측 임계밀도 배율1.16→1.0, anticipation ν47.4→35, lane-drop φ6→0; merge δ1 유지. 서측 임계밀도 배율.68→.70, ν12.6→65, merge δ0 유지. 서측 φ는 실제 lane drop이 없어 식별되지 않았다. 제한된 좌표 탐색의 선택값이며 φ0의 보편적 타당성이나 모든 weaving의 부재를 뜻하지 않는다.',
        '램프 서비스의 차로 수 상한을1차로1800/2차로3600veh/h로 구분했다. 이는 관측 포화율 추정이 아니다.10490은 충분한 정지 큐가 있고 정지선 뒤 재고가 작은 seed13 사이클에서g2가45회 모두1대 방출하여, 예측 서비스.71→1대/주기로 보정했다. g3도.99→1로 수정했으며 다른 램프로 전이하지 않았다. 세부 근거는 model_v4/service_calibration.json에 있다.',
        '동일한 큐 조건으로 새 seed23을 검증했을 때도 g2의45개 사이클, g3의30개 사이클 모두 정지선 통과가1대였다. 이 국소 서비스 보정은 새 자료에서도 맞았지만, 그것이 전체 혼잡 동역학의 정확성을 보장하지는 않는다. 근거: controller_response_s23_v1/head_service_validation.json.',
        '아래는 seed23 4조건×2250/3150/4050초의450초 예측, 총12창이다. 관측 이후 경계 수요는 과거150초에서 예측했다. 미래 제어 명령은 기록된 명령을 재생하므로 향후 정책 결정 예측까지 검증한 것은 아니다. 계수를 재적합하지 않았다. RMSE는 창별RMSE의 산술평균이다.','']
    metrics={};frows=[]
    for label,records in forecast.items():
        metrics[label]={}
        for road in ('FW_E','FW_W'):
            ss=[r['scores'][road] for r in records]
            m={'mean_objective':statistics.mean(s['objective'] for s in ss),
               'speed_rmse':statistics.mean(s['speed']['rmse'] for s in ss),
               'density_rmse':statistics.mean(s['density']['rmse'] for s in ss),
               'freeway_ttt_mape_pct':100*statistics.mean(abs(s['freeway_ttt_predicted_veh_h']/s['freeway_ttt_observed_veh_h']-1) for s in ss),
               'TP':sum(s['congestion_confusion']['true_positive'] for s in ss),
               'FN':sum(s['congestion_confusion']['false_negative'] for s in ss)}
            metrics[label][road]=m
            frows.append([label,road,f"{m['mean_objective']:.3f}",f"{m['speed_rmse']:.2f}",f"{m['density_rmse']:.2f}",f"{m['freeway_ttt_mape_pct']:.2f}",f"{m['TP']}/{m['FN']}"])
    lines+=table(['모델','방향','복합 오차','속도RMSE[km/h]','밀도RMSE[veh/km/lane]','본선TTT MAPE[%]','저속TP/FN'],frows)
    lines+=['','previous=이전model_v2; dynamics_only=동역학·차로상한model_v3; calibrated=10490서비스까지 반영한model_v4. 속도·밀도·유량 복합 오차 감소는 실제 교통 개선율과 다르다. 저속 탐지와 TTT 오차를 함께 확인해야 한다.',
        '독립seed의 양방향 평균 복합 오차는 약19% 감소했지만, 본선TTT 오차는 동측4.30→7.85%, 서측4.64→5.61%로 모두 악화됐다. 동측 저속표본237개 중20개만 맞췄고, 서측 저속검출은187/249→62/249로 나빠졌다. 따라서 이 보정을 제어용 모델의 검증 성공으로 채택하지 않는다.','',
        '## 같은 초기 상태에서의 제어 반응 재검사','',
        '이미 완료된 seed13·1650–2100초 동일 초기 상태 실험을 재사용했다. 늦은 본격 혼잡의 독립 검증은 아니며, 비용은 일치하는 본선+16connector 부분 영역이다. 값은 무제어 대비 비용 증가[veh·h]다.','']
    lines+=table(['후보','실제 ΔTTT','이전 모델 ΔTTT','보정 모델 ΔTTT'],[
        [arm,*[f"{paired[k][arm]['component_ttt_veh_h']-paired[k]['none']['component_ttt_veh_h']:+.6f}" for k in ('actual','previous','calibrated')]] for arm in ('rm8','rm_ramp','vsl','both')])
    lines+=['','강한RM(g8→6→4)은 실제10490합류96→84대, 모델81.63→77.15대다. g8유지에서는 실제103대인데 모델은81.63대로 변하지 않는다. 비용 영향의 크기를 크게 놓치며 강한RM 비용 증가의 부호도 맞추지 못했다. 이 쌍은g2를 쓰지 않아g2서비스 보정의 효과 검증으로 해석하지 않는다.',
        '## 계산과 실행 검증','']
    lines+=table(['MPC 조건','변경 결정 수/24','계산 총[s]','계산 최대[s/결정]','관측 총[s]','초기화 총[s]'],[
        [a,len(r['changed_decisions']),f"{r['total_calculation_seconds']:.2f}",f"{r['max_calculation_seconds']:.2f}",f"{r['total_observation_seconds']:.2f}",f"{r['total_initialization_seconds']:.2f}"] for a,r in decision.items()])
    lines+=['','후보 예산 때문에 생략한 단일 후보는0개다. 이는 유한한 후보 목록을 다 봤다는 뜻이며 전체 허용 공간의 전수 탐색은 아니다. VSL 변경 시 모델이 예측한 이득은0.000019–0.00540veh·h에 불과했다. 이 작은 차이로 선택한 정책의 실제2.07% 이득을 정밀한 예측 성공이라고 주장하지 않는다.',
        '매초 차량COM 전수조회는 없고, MPC에 필요한150초 관측마다4개bulk read(런당96회)를 사용했다. 차량 이력은 그때까지의native FZP를 증분 읽었다. 신호 전환 때만 쓰며 VSL은 적용 시readback했다. native LDP·초기readback·기록 정책 재생을 검증했다. 무제어 두 방식은4500초 전체19,638,299개FZP행의SHA256이 정확히 같다.',
        '위 계산·관측·초기화 시간은 실제simulation 속도나 전체 실행시간과 섞지 않았다. 각suite summary.json의wall_seconds는 로딩·시뮬레이션·제어·실행검증을 포함한다.',
        '초기900초시험의 차량ID·COM/FZP 말단 제거 시점 차이 실패 기록을 보존했다. 현재는명시적차량No를 사용하고 동일 차량 좌표가 일치하는지 검사한다. native최종위치 기록 후 사라진 물리말단차량은 pausedCOM과의시점차이로 따로 기록했다. MPC RM의nativeOFF→첫제한 시점에 대한 사후검증기 오판도 원본receipt·코드를 보존하고 수정 후 재검증했다. 교통 자료를 수정하거나 실패한실런을 성공런으로 대체하지 않았다.',
        '## 판단과 다음 우선순위','',
        '1. RM이 물리적으로 안 먹는 망은 아니다. 실제 합류와 큐가 변했다. 다만 이 조건에서는 본선 이득이 다른 대기 비용과 상쇄된다. 모델은 그 변화량을 아직 충분히 설명하지 못한다.',
        '2. MPC VSL 단독 정책은 재검증할 가치가 있다. 같은망의 추가seed에서 정책을 고정해 반복하고, 동측seg5의 완만한 제한이 예방한 혼잡 전파를 별도 동일초기상태 실험으로 분리하는 것이 다음이다. 이번 결과를 보고 추가seed를 보정용으로 소급 전환하지 않는다.',
        '3. 추가 계수 전수탐색보다3000초 전후의동일초기상태에서 실제 정지선 서비스·합류량·하류진출배수·본선수용량·대기비용의 차이를 맞추는 것이 우선이다. 과거실현off-ramp분기율과constant배수proxy, 접근도로의혼합목적지 대기는 남은 구조적 한계다.',
        '4. 현재 계수는 명시적실험config에만 유지한다. 전체도시Ω예측과full GNE 연결·정본승격은 아직 완료하지 않았다. 근거 없는capacity drop이나lever보상항은 추가하지 않았다.',
        '','근거: 각suite의summary.json·verification.json·analysis, controller_response_s23_v1/frozen_model_validation, controller_response_4500_v1/model_v3/CALIBRATION_AUDIT.md 및model_v4, paired_response_after_calibration.json, mpc_decision_audit_s23.json.']
    (root/'RECALIBRATION_AND_CONTROL_4500_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (root/'recalibration_validation_summary.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--runs',type=Path)
    parser.add_argument('--observations',type=Path)
    parser.add_argument('--consolidated',action='store_true')
    args=parser.parse_args()
    if args.consolidated:consolidated_report()
    elif args.observations:
        if not args.runs:parser.error('--observations requires --runs')
        validate_new_seed(args.observations,args.runs)
    elif args.runs:summarize_new_suite(args.runs)
    else:main()
