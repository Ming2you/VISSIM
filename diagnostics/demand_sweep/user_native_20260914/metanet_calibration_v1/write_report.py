"""Summarize completed frozen validation, preserving both gains and failures."""
import csv
import datetime
import json
from pathlib import Path
from boundary_factory import ObservationData
from evaluate import check_freeze

HERE=Path(__file__).resolve().parent

def main():
    check_freeze(HERE/'FREEZE.json',HERE/'fit_v2/parameters.json')
    result=json.loads((HERE/'seed17_evaluation_v1/evaluation.json').read_text(encoding='utf-8'))
    fit=json.loads((HERE/'fit_v2/parameters.json').read_text(encoding='utf-8'))
    groups={(g['road'],g['mode'],g['version']):g for g in result['groups']}
    get=lambda road,version:groups[road,'history_forecast',version]
    reduction=lambda a,b:100*(1-b/a)
    table=[]
    for road in ('FW_E','FW_W'):
        for field,unit in [('density','veh/km/lane'),('speed','km/h'),('flow_vph','veh/h')]:
            a,b=(get(road,v)[field]['rmse'] for v in ('baseline','calibrated'))
            table.append({'road':road,'metric':field,'unit':unit,'baseline_rmse':a,'calibrated_rmse':b,'reduction_percent':reduction(a,b)})
    local=[]
    with (HERE/'seed17_evaluation_v1/predicted_cells_30s.csv').open(encoding='utf-8',newline='') as f:
        predictions=list(csv.DictReader(f))
    data=ObservationData(HERE/'seed17_observations')
    observed={(t,r['road'],r['cell']):r for t,rows in data.cells.items() for r in rows}
    for road,c in [('FW_E',0),('FW_E',13),('FW_W',0),('FW_W',5),('FW_W',6)]:
        for version in ('baseline','calibrated'):
            pairs=[]
            for p in predictions:
                if p['mode']!='history_forecast' or p['version']!=version or p['road']!=road or int(p['cell'])!=c:continue
                o=observed[int(float(p['time_s'])),road,c]
                if o['n_veh']>=5 and o['v_kmh'] is not None:pairs.append((o['v_kmh'],float(p['v_kmh'])))
            local.append({'road':road,'cell_display':c+1,'version':version,'count':len(pairs),
                          'observed_mean_speed':sum(a for a,b in pairs)/len(pairs),
                          'predicted_mean_speed':sum(b for a,b in pairs)/len(pairs),
                          'speed_rmse':(sum((b-a)**2 for a,b in pairs)/len(pairs))**.5})
    e14=[]
    for mode in ('history_forecast','conditioned_diagnostic'):
        for version in ('baseline','calibrated'):
            scores=[s for s in result['scores'] if s['road']=='FW_E' and s['mode']==mode and s['version']==version]
            events=[e for s in scores for e in s['onset_events'] if e['cell']==13]
            e14.append({'mode':mode,'version':version,'observed_veh':sum(s['e14_discharge_observed_veh'] for s in scores),
                'predicted_veh':sum(s['e14_discharge_predicted_veh'] for s in scores),
                'sustained_congestion_observed_windows':sum(e['observed_first_sustained_in_window_s'] is not None for e in events),
                'missed_windows':sum(e['status']=='miss' for e in events)})
    summary={'scope':'same edited network, E input1098x0.8, training13/test17; canonical freeway component, no control response validation',
             'rmse':table,'local_speed_diagnostics':local,'e14':e14,
             'groups':result['groups'],'persistence':result['persistence'],'failed_windows':result['failures'],
             'parameters':fit['parameters'],'parameters_promoted_to_controller':False}
    (HERE/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for s in result['scores']:
        rows.append({**{k:s[k] for k in ('cutoff_s','road','mode','version','invalid','objective')},
                     **{k+'_rmse':s[k]['rmse'] for k in ('density','speed','flow_vph')},
                     'density_450_rmse':s['horizons']['450']['density']['rmse'],
                     'speed_450_rmse':s['horizons']['450']['speed']['rmse'],
                     'freeway_ttt_observed_veh_h':s['freeway_ttt_observed_veh_h'],
                     'freeway_ttt_predicted_veh_h':s['freeway_ttt_predicted_veh_h']})
    with (HERE/'forecast_window_metrics.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lines=['**동측 본선 ×0.8: seed13 보정 / seed17 450초 독립 예측 검증**','',
        '실제 추가 런과 검증까지 완료했다. 보정은 새 seed에서도 밀도와 유량 오차를 줄였지만, E14의 혼잡 상태를 놓치는 문제가 남았다. 현재 계수를 controller 정본에 적용하지 않는다. METANET 전체가 불가능하다는 판정도 아니다. 이번에 시험한 기존 구조·경계 처리·제한된 계수 보정으로는 부족하다는 결과다.','',
        '**실행과 분리 원칙**','',
        '- 사용자가 수정한 망에서 동측 본선 input1098만 ×0.8. 서측·도시·램프 수요, 경로, native 신호, 희망속도 분포는 유지. 과거의 전역 80–50 시나리오와 다르다.',
        '- 기존 seed13 9000초 자료로 방향별 6개 계수를 보정하고, seed17을 같은 망·수요로 새로 9000초 실행했다. 무제어 native 런이며 seed만 다르다.',
        '- seed17 실행 완료 2026-09-14 22:42:52 KST. 22:57:23에 계수·모델·관측 추출·평가 정의 211개 파일을 SHA256으로 고정한 뒤 seed17 궤적을 처음 추출했다. 평가 전후 해시가 일치했다.',
        '- seed13 훈련 시작 시각: 900,1800,…,8100초(9개). 보정에 쓰지 않은 같은 seed의 시간 구간은 1350,2250,…,8550초(9개); 인접 구간이므로 독립 seed 검증을 대신하지 않는다.',
        '- seed17 평가: 900,1350,…,8550초의 18개 시작 상태. 각각 450초를 10초 step으로 전개하고 30초마다 채점. 예측 중 실제 본선 N·밀도·속도를 다시 넣지 않았다.',
        '- 실사용 조건 예측: 시작 전 150초 경계 흐름과 알려진 입력 시간표만 사용. 별도 진단: 실제 미래 합류·진출·원점 진입량과 진출 연결부 재고를 제공. 두 결과를 섞지 않았다.',
        '- 대상은 정본 고속도로 METANET 구성요소다. 실제 8개 진입·8개 진출 포트를 유지했다. 도시 전체 예측, 램프 목적지 queue 모델, VSL/RM 변경 효과는 이번 검증 대상이 아니다.','',
        '**미래 실측값을 쓰지 않은 seed17 예측 결과**','',
        '18개 구간, 양방향 전체 셀의 30–450초 오차를 합산한 RMSE다. 속도는 실제 차량 수≥5인 셀로 평가했다. 밀도는 실제 lane-km로 계산했고, 유량은 셀 하류 통과+진출 분기+말단 유출의 합이다. 양방향 모두 18개 전 구간이 평가됐으며 실패·밀도 보정·음수·jam 초과 구간은 0개였다.','',
        '| 방향 | 지표 | 기존 | 보정 후 | 오차 감소 |','|---|---|---:|---:|---:|']
    for r in table:
        lines.append(f"| {'동측' if r['road']=='FW_E' else '서측'} | {r['metric']} [{r['unit']}] | {r['baseline_rmse']:.2f} | {r['calibrated_rmse']:.2f} | {r['reduction_percent']:+.1f}% |")
    lines+=['','동측 속도 RMSE는 2.6% 악화했다. 동측 밀도는 18/18개 구간, 유량은 17/18개 구간에서 개선됐다. 서측도 같은 구간 수에서 개선됐다. 따라서 일부 유리한 구간만 고른 개선은 아니지만, 모든 물리량이 함께 맞아진 것은 아니다.','',
        '| 방향 | +450초 속도 RMSE 기존→보정 [km/h] | +450초 밀도 RMSE 기존→보정 [veh/km/lane] |','|---|---:|---:|']
    for road in ('FW_E','FW_W'):
        a,b=(get(road,v)['horizons']['450'] for v in ('baseline','calibrated'))
        lines.append(f"| {'동측' if road=='FW_E' else '서측'} | {a['speed']['rmse']:.2f} → {b['speed']['rmse']:.2f} | {a['density']['rmse']:.2f} → {b['density']['rmse']:.2f} |")
    lines+=['','[예측 길이에 따른 오차](figures/seed17_error_by_lead.png) · [18개 구간 전체 시간–공간 비교](figures/seed17_speed_space_time.png) · [사전 지정한 1350/3600/7200초 시작 예측](figures/seed17_450s_examples.png)','',
        '**유량 개선만으로 합격시킬 수 없는 이유**','',
        '1. E14의 총 방출량(평가 범위 900–9000초)은 실제 12,295대, 기존 8,867대, 보정 12,067대였다. 오차가 −27.9%→−1.85%로 줄었다. 그러나 같은 셀의 평균 속도는 실제 29.49km/h, 기존 28.58km/h, 보정 39.58km/h였다. 속도 RMSE는 5.82→11.77km/h로 커졌다.',
        '2. E14에서 “N≥5, v<30km/h가 120초 이상 유지”된 12개 예측 구간을 기존 모델은 12개 모두 검출했으나, 보정 모델은 12개 모두 놓쳤다. 이는 12개의 서로 독립된 혼잡 발생 사건이 아니라, 각 450초 창 안의 지속 저속 상태 여부다. 미래 실제 경계를 제공한 진단에서도 동일한 누락이 나타났다.',
        '3. E14 1350초 시작 예측에서는 실제 속도가 41→21km/h로 내려가지만, 보정 모델의 +450초 속도는 약44km/h다. 3600초 시작에서도 실제 약24km/h인 말단 상태를 약37km/h로 예측한다. 차량 수가 맞아도 병목 속도·혼잡 상태를 잘못 표현한다.',
        '4. 진입 셀에도 큰 오차가 남는다. E1 실제 평균35.87km/h에 보정68.79km/h, W1 실제20.80km/h에 보정62.13km/h다. W1 지속 저속은 양 모델 모두 18개 구간에서 놓쳤다. 반대로 W6/W7은 실제 약81/79km/h보다 보정 약56/51km/h로 너무 느리다. 단일 방향 계수를 조정하면서 공간별 오차를 서로 교환한 흔적이다.',
        '5. 현재 상태를 그대로 유지하는 기준의 속도 RMSE는 동측12.52/서측16.05km/h, 밀도7.13/5.00veh/km/lane다. 보정 METANET보다 작다. 이 기준 자체에는 제어 반응 예측 능력이 없지만, 현재 모델을 충분히 정확하다고 인정하기 어려운 검사 결과다.',
        '6. 실제 미래 경계를 넣어도 보정 속도 RMSE는 동측19.75/서측23.20km/h로 실사용 조건19.75/23.34와 거의 같다. 따라서 과거 경계를 고정한 예측만이 원인이라는 설명은 약해진다. 다만 진출 처리용량은 실측 방출량의 proxy이므로 순수 모델 구조만의 오차라고 단정하지 않는다.','',
        '**보정 내용과 물리적 유효성**','',
        '| 계수 | 기존 | 동측 | 서측 |','|---|---:|---:|---:|',
        '| 자유속도 배율 | 1 | 0.91 | 1.00 |','| 임계밀도 배율 | 1 | 1.16 | 0.68 |',
        '| τ [s] | 18 | 12 | 12 |','| ν [km²/h] | 30 | 51.75 | 30 |',
        '| κ [veh/km/lane] | 40 | 17 | 5 |','| 합류 계수 δ | 0.3 | 0.55 | 0 |','',
        '이번 보정은 merge항 δ를 포함했지만 별도 weaving 계수는 보정하지 않았다. 실제 실행 경로에는 진출·진입 교차 차로변경 강도에 따른 독립 weaving 감속항이 없다. 차로감소 항 φ=3.0은 적용하되 고정했으며, 이 항은 차로 수가 줄어드는 지점의 감속이므로 weaving 자체와 구별해야 한다. 진출부 재고·수용량에 따른 제약은 별도로 유지했다. 8개 진입램프의 위치·유량은 각각 반영하지만 δ는 방향별 하나를 사용했다. 따라서 weaving과 merge를 독립 식별해 맞춘 결과는 아니다.',
        '',
        '기존 FD 계열과 공간별 프로파일, lane-drop 계수, capacity-drop 설정을 유지했다. 두 방향 τ와 서측 κ·δ는 탐색 하한에 도달했다. 서측 δ=0이 실제 합류 마찰이 없다는 증거는 아니다. 제한된 목적값과 탐색에서 다른 오차를 흡수한 계수일 수 있다. bounded coordinate search는 동측100/서측95번의 후보 계산을 수행했으며 전역 최적성은 주장하지 않는다.',
        '',
        '원래 정본의 연속방정식은 공통 셀 길이를 사용하고 속도 계산에는 공간별 geometry hook이 있다. 초기 실제 차량 수를 보존하도록 정본 밀도로 변환하고, 보고할 때 다시 물리 lane-km로 환산했다. 이 표현 차이는 이번에 임의로 고치지 않았다. E14 등 국소 상태–유량 불일치 원인 후보로 다시 살펴볼 부분이다.',
        '',
        '실제 궤적 두 시드 합계25,200개 셀 보존식과 모든 누적·경계 계수를 독립 재계산해 불일치0. 미확인 유입·소실·건너뛴 램프 연결·ID 재등장도0. 모델 연속방정식 최대 잔차는 약5.7e−14대다. 속도 제한 투영은 기존 물리 제한 로직에 따라 남아 있으며, 이것을 수치 불안정과 동일시하지 않았다.',
        '',
        '| 시드·방향 | 실제 원점 진입 | 램프 합류 | 진출 분기 | 말단 유출 추론 | 종료 본선 재고 |',
        '|---|---:|---:|---:|---:|---:|',
        '|13 E|13,326|6,408|7,365|11,288|1,081|','|13 W|8,196|7,008|7,186|7,563|455|',
        '|17 E|13,282|6,428|7,331|11,256|1,123|','|17 W|8,296|7,069|7,240|7,734|391|','',
        '말단 유출은 1초 프레임의 위치·속도로 판정한 운동학적 추론이다. 명시적인 차로변경 차량 삭제는 seed13/17에서523/516대, 모두 도시·접근도로였고 본선·진입·진출 연결부는0이다. 도시 전체가 오류 없이 정상이라는 뜻은 아니며, 전체 Ω 제어 성능과 도시 대기 비용은 이번 본선 예측만으로 평가할 수 없다. 본선 체류시간 비교도 900–9000초의 예측 구간 합계이며 전체 Ω TTT 또는 controller 개선율이 아니다.','',
        '**다음 판단**','',
        '지금은 수요를 더 낮춰 예측이 쉬운 조건으로 옮기기보다, 0.8 자료를 유지하면서 E14의 N–밀도–속도–방출량 관계와 E1/W1의 진입 속도·가속 경계를 먼저 분리 진단하는 편이 좋다. 이는 원인 후보이며 확정 원인은 아니다. 임계밀도·ν 등을 전 구간에 더 넓게 튜닝하는 것만으로 해결됐다고 판단하지 않는다.',
        '',
        '해당 국소 불일치를 설명한 뒤 보정할 경우 seed17은 이미 열람했으므로 개발 자료가 된다. 다음 독립 검증은 새 seed로 해야 한다. 그 다음 동일 초기 상태에서 실제 방출량을 바꾸는 RM 후보와 VSL 후보의 Δ유량·Δ재고·Δ체류시간 순위를 비교해야 한다. 무제어 궤적 적합만으로 controller가 이득을 예측한다고 주장할 수 없다. 현재 보정 계수는 실험 산출물로만 보존했다.','',
        '**기록·재현**','',
        '- 추가 native9000: 약519초(시작부터 종료까지, 로딩·설정 포함). 최초 실제 진행 기록은 시작 약22초 뒤. 매초 COM 전수 조회는 사용하지 않았고 native FZP/LSA/LDP/ERR를 보존했다.',
        '- 종료 후 FZP 추출: seed13 약103초, seed17 약107초. seed13 보정 fit_v2 약48초. seed17의72회 양방향 450초 예측·채점 약3.72초. MPC 최적화·게임 계산 시간과는 다르다.',
        '- [실행 기록](../east080_seed17_v1/native9000/run.json), [동결 명세](FREEZE.json), [실험 규약](PROTOCOL.json), [최종 보정 계수](fit_v2/parameters.json).',
        '- [전체 평가](seed17_evaluation_v1/evaluation.json), [18개 구간별 표](forecast_window_metrics.csv), [요약 데이터](SUMMARY.json).',
        '- 정본 물리식을 복제하지 않고 `canonical_harness.py`에서 기존 `area_freeway_accounting._freeway_substep_events`를 직접 호출했다. 관측 추출은 기존 native parser를 사용했다. 운영 controller 및 기본 물리 설정은 이번 보정값으로 변경하지 않았다.',
        '- 독립 검토에서 지적된 의존성 해시·경계 준비 실패 보존을 테스트 데이터 열람 전에 보완했다. seed13의 인위적 누락 검사에서 실패 구간을 보존하고 나머지 구간을 계속 평가하는 것을 확인했다. 그 검사 결과는 성능 표에 섞지 않았다.',
        '',
        '재현은 이 폴더의 `evaluate.py --data seed17_observations --parameters fit_v2/parameters.json --out 새_결과_폴더 --freeze FREEZE.json`에 해당하는 실제 경로를 지정하면 된다. 기존 결과 폴더는 덮어쓰지 않는다. 도표 스크립트 수정은 표시용 숫자 파싱 수정뿐이며 동결 모델·평가·계수는 변경하지 않았다.','']
    (HERE/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    check_freeze(HERE/'FREEZE.json',HERE/'fit_v2/parameters.json')
    print(json.dumps({'report':str(HERE/'RESULTS.md'),'rows':len(rows),'all_frozen_hashes_match':True},ensure_ascii=False))

if __name__=='__main__': main()
