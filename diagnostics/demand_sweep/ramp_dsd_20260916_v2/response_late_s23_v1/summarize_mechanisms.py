"""Report completed response-model hypotheses and native lane evidence."""
import csv
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'.review-deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):
    with p.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))


fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
for ax,name,folder,start in [(axes[0],'early13','controller_response_4500_v1/none',1650),
                            (axes[1],'late23','controller_response_s23_v1/none',2400)]:
    stocks=load(HERE.parent/folder/'port_cohorts_30s.json')
    times=list(range(start,start+451,30))
    ax.plot(times,[len(stocks[str(t)]['10681']) for t in times],color='black',label='VISSIM',lw=2)
    for label,path,color in [('Existing',HERE/'mechanism_ablation_v3'/f'{name}_baseline_none.json','#ce772d'),
                             ('Recent speed held',HERE/'mechanism_ablation_v3'/f'{name}_ramp_history_none.json','#287e98'),
                             ('Lane buffers only',HERE/'lane_candidate_v1'/f'{name}_none_prediction.json','#9865a4')]:
        rs=[r for r in load(path)['ramps'] if r['ramp']=='RM_C10681']
        ax.plot([start]+[r['end_sec'] for r in rs],[rs[0]['start']['connector_veh']]+[r['end']['connector_veh'] for r in rs],color=color,label=label)
    ax.set(title=f'10681 stock: {name}',xlabel='Simulation time [s]',ylabel='Vehicles on ramp',ylim=(0,65))
    ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.savefig(HERE/'mechanism_queue_comparison.png',dpi=180)
plt.close(fig)

validation=load(HERE/'transit_history_validation_v1/summary.json')
ablation=load(HERE/'mechanism_ablation_v3/results.json')
actual_early=load(HERE.parent/'response_pairs_v1/component_actual.json')
actual_late=load(HERE/'response_analysis/comparison.json')
summary={'transit_validation':validation,'vsl_cost_deltas':{},'native_zone':{},'adopted':False}
for name,bank in [('early13',actual_early),('late23',actual_late)]:
    b=ablation[name]['variants']
    # Older bank is already the component dictionary, late bank nests it.
    actual={a:(r['actual_component'] if 'actual_component' in r else r) for a,r in bank.items()}
    summary['vsl_cost_deltas'][name]={'actual':actual['vsl']['component_ttt_veh_h']-actual['none']['component_ttt_veh_h'],
        **{v:b[v]['vsl']['component_ttt_veh_h']-b[v]['none']['component_ttt_veh_h'] for v in ['baseline','vsl_ratio']}}
for name in ['s23_none','s23_vsl']:
    rs=rows(HERE/'lane_response_v1'/f'{name}_lane150.csv')
    cs=rows(HERE/'lane_response_v1'/f'{name}_stations150.csv')
    z=[r for r in rs if 2400<=int(r['start_s'])<2850 and r['link']=='2' and int(r['start_m'])<2000]
    n=sum(float(r['n_mean']) for r in z);v=sum(float(r['n_mean'])*float(r['speed_mean_kmh']) for r in z)/n
    v2=sum(float(r['n_mean'])*(float(r['speed_mean_kmh'])**2+float(r['speed_sd_kmh'])**2) for r in z)/n
    summary['native_zone'][name]={'speed_mean':v,'pooled_speed_sd':math.sqrt(max(0.,v2-v*v)),
        'lane_changes_per1000veh_s':sum(int(r['lane_changes']) for r in z)/(n*150)*1000,
        'braking_steps_per1000veh_s':sum(int(r['braking_steps']) for r in z)/(n*150)*1000,
        'crossings_link2_pos2000':sum(int(r['vehicles']) for r in cs if 2400<=int(r['start_s'])<2850 and r['link']=='2' and r['station_m']=='2000.0')}
(HERE/'mechanism_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

lines=['# 후속 검증: 10681 차로별 대기와 VSL 반응','',
'완료: 기존 native FZP 3런의 차로별 재분석, 24개 시작 상태×4조건의 transit 검증96예측, 32개 반응식 ablation, 차로 분리 후보8예측 및8개 재현 검증. 신규 VISSIM 실행은 하지 않았다. **세 가지 단순 수정 모두 제어용 예측 검증을 충분히 통과하지 못하여 정본에 채택하지 않았다.**','',
'## 10681: 실제로 무엇이 빠졌나','',
'seed23 무제어2400초의 램프 재고는48대, 차량 평균속도는약10km/h이다. 기존 모델은 혼잡 전 통행에서 얻은41.45km/h와3600대/h 수용 상한으로 첫30초에30대를 내보냈다. 실제는8대이다. 미래 접근량까지 실측으로 공급한 진단에서도450초 합류가163대/실제126대로 달랐다.','',
'2400–2550초 FZP 차로별 평균:','',
'|위치|1차로|2차로|','|---|---:|---:|',
'|10681 평균 재고|1.8대|42.9대|',
'|10681 평균 속도|25.3km/h|8.6km/h|',
'|합류 직후 본선2번 2300–2400m 평균 재고|0.6대|4.7대|',
'|같은 본선 위치 평균 속도|70.4km/h|31.7km/h|','',
'총량 모델은 램프 차로별 재고를 저장해도 동역학에서는 합쳐 사용한다. 초기 저속 재고를 고속으로 보내는 문제와, 비어 있는 차로의 공간·서비스를 다른 차로에 사용할 수 있는 문제가 함께 있다. 단, 이것만으로 합류 과대의 전부를 설명했다고 단정하지 않는다.','',
'## 수정 후보를 직접 구현해 비교한 결과','',
'1. **최근150초 관측속도를450초 동안 유지:** seed23 혼잡 지속 상태는 개선되지만 seed13 회복 상태를 놓친다. 미래 도착까지 공급한 원인분리 조건에서는 seed13 합류MAE가7.44→9.53대로 악화된다. 현재 정체를 지평 끝까지 고정하는 것도 잘못이다.',
'2. **차로별 저장·head 서비스·합류 예산 분리:** 기존 PhysicalRampBoundary를 사용한 실험 코드를 작성하고 보존·적색·차로 간 서비스/저장 공유 금지 등5개 단위검사를 통과했다. seed23 첫30초 과다 방출은30→16대로 줄지만 실제8대보다 크다. 450초 합류는157.6대로 그대로다(history forecast 기준). 저장 공간 분리만으로 하류 수용이 좋아지지 않는다.',
'3. **VSL desired-speed 분포 평균비로 평형속도 조정:** 분포ID100/120의 평균비0.883을 사용했다. 용량 증가·capacity drop·레버 보상은 추가하지 않았다. 초기 상태에서는 비용 차이가 가까워졌으나 후기 상태에서 비용 부호가 틀렸다. 아래 표 참조.','',
'![램프 재고 예측 비교](mechanism_queue_comparison.png)','',
'|10681 합류 MAE [대/450초], 12개 시작 상태씩|seed13 기존→관측속도|seed23 기존→관측속도|','|---|---:|---:|',
f"|과거 이력만 사용하는 예측|{validation['13']['history_forecast_baseline']['merge_mae']:.2f}→{validation['13']['history_forecast_observed_transit']['merge_mae']:.2f}|{validation['23']['history_forecast_baseline']['merge_mae']:.2f}→{validation['23']['history_forecast_observed_transit']['merge_mae']:.2f}|",
f"|미래 접근량을 공급한 사후 진단|{validation['13']['conditioned_diagnostic_baseline']['merge_mae']:.2f}→{validation['13']['conditioned_diagnostic_observed_transit']['merge_mae']:.2f}|{validation['23']['conditioned_diagnostic_baseline']['merge_mae']:.2f}→{validation['23']['conditioned_diagnostic_observed_transit']['merge_mae']:.2f}|",'',
'seed13·23 모두 이미 본 개발자료이다. 독립 holdout으로 표현하지 않는다. 시작점은900,1200,1500,1650,1950,2250,2400,2700,3000,3300,3600,3900초이며 각450초이다. 중첩 예측창은 독립 표본이 아니다.','',
'|VSL−무제어 Δcomponent TTT [veh·h]|실측|기존|분포비 후보|','|---|---:|---:|---:|']
for name,x in summary['vsl_cost_deltas'].items():lines.append(f"|{name}|{x['actual']:+.4f}|{x['baseline']:+.4f}|{x['vsl_ratio']:+.4f}|")
lines += ['', 'component는 동일42본선셀+16connector의30초 재고 적분이며 Ω 전체와 다르다. early13은1650초 시작·DSD59–62의100→80, late23은2400초 시작·DSD51–58의100이다. 두 bank는 다른 위치·상태의 제어로 단순한 시간차 비교가 아니다.','',
'## VSL의 실제 반응: 유입 억제만으로 설명되지 않음','',
'seed23의 같은 시작 상태, 첫450초, 본선2번0–2000m:','',
'|측정|무제어|VSL|','|---|---:|---:|']
for key,label in [('speed_mean','평균 속도 km/h'),('pooled_speed_sd','시공간 표본을 합친 속도 표준편차 km/h'),('lane_changes_per1000veh_s','차로 변경/1000 차량·초'),('braking_steps_per1000veh_s','큰 감속 표본/1000 차량·초'),('crossings_link2_pos2000','2000m 통과 대수')]:
    lines.append(f"|{label}|{summary['native_zone']['s23_none'][key]:.2f}|{summary['native_zone']['s23_vsl'][key]:.2f}|")
lines += ['',
'속도 분산은 시간·공간을 합친 설명 지표이며 동일 시점 속도 동질성만을 뜻하지 않는다. 감속은1초간7.2km/h 초과 감소, 차로 변경은 같은 링크 내 lane index 변화이다. 낮은 표지 속도가 더 적은 통과량으로 직결되지 않았다는 관측이며, 단일seed의 이 표만으로 분산 감소가 혼잡 지연의 원인이라고 확정하거나 용량 증가식을 보정하지 않는다.',
'10681 안에서도1200–4500초에 차로 변경이 seed13 171회·seed23 237회 관측됐다. 따라서 차로를 완전히 독립 FIFO로 묶는 후보 역시 완전한 동역학이 아니다.','',
'## 코드와 채택 상태','',
'- 차로 후보를 기존 canonical component에 연결해 시험한 뒤, 충분한 정확도 개선이 없어 연결과 정본 수정을 제거했다. `physical_ramp_boundary.py`는 작업 전SHA256 `7b6d7feb3252bb8755021f8fce6588f211490332af4004e56c74812d4913296a`와 바이트 단위 일치한다.',
'- 후보 소스는 `lane_boundary_candidate.py`에 실험 근거로 보존한다. controller가 import하지 않는다. `replay_lane_candidate.py`는 기존 component에 임시 연결하고 finally로 복원하는 오프라인 재현 도구이며,8개 예측의 물리 출력이 원 시험과 정확히 일치한다.',
'- `lane_candidate_v1/tested_config.json.txt`는 당시 실험 설정의 보존본이다. 실행 가능한 현재 config로 사용하면 안 된다. 후보 상태는 `STATUS.json`에 명시했다.',
'- 후보 제거 후 기존 late23 무제어 예측 전체가 JSON 정규화 기준 동결 결과와 정확히 일치한다. 최초 비교 실패는 tuple/list 직렬화 차이였고 수치 차이가 아니었다.',
'- `mechanism_ablation_v1/v2`는 스키마 처리 오류로 결과 생성 전 중단된 준비 시도다. 완성 결과는v3뿐이며 실패를 성공 샘플로 세지 않는다.',
'- native 신호·DSD·수요·망·기존 결과를 변경하지 않았고 새로운 VISSIM 런도 시작하지 않았다. 통과한 모델 수정이 없어 같은 명령 실험을 반복할 근거가 없었다.','',
'## 다음 모델 수정의 구체적 범위','',
'10681 램프와 본선 합류부에 한정해 **대기 차로와 나머지 차로의 재고, 두 차로군 사이 이동, 본선 대상 차로의 수용·회복**을 보존식으로 연결해야 한다. 전체 망을 차로 단위로 확장하거나 단순히 merge계수를 키우는 것은 우선하지 않는다.','',
'- 램프 각 차로 재고: 다음 재고=현재+접근+차로 유입−head 통과−차로 유출. head 이후는 head 통과+차로 유입−실제 합류−차로 유출. 차로별 대기 비용을 모두 포함한다.',
'- 실제 합류=min(정지선 이후 도달 가능한 재고, 대상 차로의 수용). 대상 차로에 들어오는 본선 차량과 같은 공간·유량 예산을 사용해야 한다. 지금처럼 전체본선 평균밀도만으로3600대/h 상한을 계속 주면 안 된다.',
'- 초기 두 차로군의 상태는 관측으로 정하고 이후450초는 자체 보존식으로 전진한다. 미래 관측값으로 중간 상태를 덮어쓰지 않는다. 실측 방출량을 그대로 고정 용량으로 사용하지 않는다.',
'- VSL은 상류 차량군의 도착 시각·속도/차로 배분 변화가 이 합류·하류 병목 상태로 전달되는지를 먼저 검증한다. 혼잡 지속뿐 아니라 seed13 회복 상태에서 제한을 해제할 근거가 생기는지를 통과 기준으로 삼는다.',
'- 첫 검증은 저장된 동일 상태의 소수 명령 후보로 한다. RM 방출량·램프 대기·본선 방출·후보 비용 순위가 함께 개선된 모델만 실제 controller/VISSIM 비교로 진행한다.',
'','완료된 것은 원인 분리와 세 후보의 구현·기각이다. 새 최종 plant 또는 controller 성능 개선을 달성했다고 보고하지 않는다.','']
(HERE/'FOLLOWUP_MECHANISMS.md').write_text('\n'.join(lines),encoding='utf-8')
print(HERE/'FOLLOWUP_MECHANISMS.md')
