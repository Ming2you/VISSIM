"""Summarize completed four-arm native evidence; no simulator calls."""
import csv
from datetime import datetime
import json
from pathlib import Path
import statistics

HERE=Path(__file__).resolve().parent/'rules_v1'
ARMS=('none','rm','vsl','both')
NAMES={'none':'무제어','rm':'ALINEA RM','vsl':'규칙 VSL','both':'RM + VSL'}


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def table(headers,rows):
    return ['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows]


def main():
    analysis=HERE/'analysis'; comparison=load(analysis/'comparison.json')['arms']
    verification=load(HERE/'verification.json')
    assert verification['instrumentation_continuous_execution_equivalence']['passed']
    result={}
    for arm in ARMS:
        stats=comparison[arm]; area=csvrows(analysis/arm/'area_timeseries.csv'); stocks=csvrows(analysis/arm/'stocks_1s.csv')
        policy=load(HERE/f'prepared_{arm}/rule_policy.json')
        decisions=[load(HERE/f'run_{arm}/decision_{s}.json') for s in range(900,3000,150)]
        receipt=load(HERE/f'run_{arm}/run.json')
        def integral(key):
            vals=[float(r[key]) for r in stocks[899:3000]]
            return (sum(vals)-(vals[0]+vals[-1])/2)/3600
        exposure={mid:{'minimum_green_sec':min(d['meters'][mid]['green_sec'] for d in decisions),
            'first_restriction_sec':next((d['sec'] for d in decisions if d['meters'][mid]['green_sec']<10),None),
            'restricted_seconds':sum(150 for d in decisions if d['meters'][mid]['green_sec']<10),
            'max_downstream_occ_pct':max(d['observations'][mid]['occupancy_pct'] for d in decisions)} for mid in policy['meters']}
        vsl={zone:{'minimum_distribution_id':min(d['history']['vsl'].get(str(ids[0]),120) for d in decisions),
            'restricted_seconds':sum(150 for d in decisions if d['history']['vsl'].get(str(ids[0]),120)<120)} for zone,ids in policy['zone_dsds'].items()}
        total=next(w for w in stats['windows'] if (w['start_s'],w['end_s'])==(0,3000))
        controlled=next(w for w in stats['windows'] if (w['start_s'],w['end_s'])==(900,3000))
        freeway={d:integral(d+'_n') for d in ('FW_E','FW_W')}
        ramps=sum(integral('ramp_'+str(m['connector'])+'_n') for m in policy['meters'].values())
        result[arm]={'total':total,'controlled':controlled,'freeway_ttt_900_3000':freeway,
            'ramp_connector_ttt_900_3000':ramps,
            'remaining_omega_ttt_900_3000':controlled['omega_ttt_veh_h']-sum(freeway.values())-ramps,
            'end_omega_n':int(area[-1]['inside_vehicles']), 'native_removals':stats['native_removals'],
            'uninserted':stats['native_uninserted_at_end'],'rm_exposure':exposure,'vsl_exposure':vsl,
            'wall_seconds':(datetime.fromisoformat(receipt['finished'])-datetime.fromisoformat(receipt['started'])).total_seconds(),
            'first_progress_after_seconds':(datetime.fromisoformat(receipt['first_native_progress']['at'])-datetime.fromisoformat(receipt['started'])).total_seconds(),
            'vehicle_queries':0,'policy_decisions':len(decisions),
            'detector_value_reads':3*len(decisions)*sum(len(s['measurement_ids']) for s in policy['detectors']['stations'])}
    for arm,r in result.items():
        r['ttt_improvement_pct']=100*(1-r['total']['omega_ttt_veh_h']/result['none']['total']['omega_ttt_veh_h'])
        r['controlled_ttt_improvement_pct']=100*(1-r['controlled']['omega_ttt_veh_h']/result['none']['controlled']['omega_ttt_veh_h'])
    (HERE/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    text=['# 새 가속거리·램프 DSD 망: ALINEA / 규칙 VSL 4조건','',
        '동일 사용자 수정 망·수요·seed 13. SimPeriod=9001 유지, 3000초에서 정지. 0–900초 native 무제어, 900–3000초 정책 적용.',
        '본선 및 램프 기준 속도분포 ID120 유지. VSL은 기존 결정 트리의 기준 명령만120으로 변경한60/80/120이며, 분포 ID는 모든 차량의 고정 주행속도가 아니다.',
        'ALINEA: 8개 독립 미터, 새 합류점50m 하류 전체 차로 평균 점유율, 목표15%, gain70veh/h/percentage-point/lane. 150초 갱신, 적·녹10초 주기, 최소녹색2초 및 직전 녹색 대비±2초. 서비스 표는 이전 규칙 실험과 동일하며 새 망의 실측 용량으로 재보정한 값은 아니다.',
        '도시 신호·수요·경로·기하·램프 DSD는 네 조건에서 동일하다. 비RM 조건은 native OFF, RM은900초부터 COM으로 제어하므로 OFF와g10의 등가성을 가정하지 않았다.','',
        'RM은 실제 본선 혼잡을 줄였다. 다만 동측 이득을 램프·도시부 대기 증가가 대부분 상쇄해 Ω 전체 개선은0.21%다. VSL과 동시 제어는 각각0.76%,0.88% 악화했다. 0.21%는 단일 seed의 작은 차이이고 미확인 소실도 달라, 확실한 순개선으로 판정하지 않는다.','',
        '## 결과','',
        *table(['조건','Ω TTT 0–3000 [veh·h]','개선율','900–3000 개선율','TTD [사건]','종료 Ω 차량'],[
            [NAMES[a],f"{r['total']['omega_ttt_veh_h']:.2f}",f"{r['ttt_improvement_pct']:+.2f}%",f"{r['controlled_ttt_improvement_pct']:+.2f}%",r['total']['omega_exit_events_observed_plus_terminal_inferred'],r['end_omega_n']] for a,r in result.items()]),'',
        'TTT는 Ω=고속도로+도시 protected network 안의 차량시간이다. TTD는 살아서 Ω 밖으로 이동한 사건과 물리적 말단 유출 추정이며, 종료 잔여·비정상 소실은 제외했다. 동일 차량의 재진입 후 재유출은 사건으로 다시 센다.','',
        *table(['조건','동측 본선 TTT','서측 본선 TTT','8개 진입 connector TTT','나머지 Ω TTT'],[
            [NAMES[a],*[f'{v:.2f}' for v in (r['freeway_ttt_900_3000']['FW_E'],r['freeway_ttt_900_3000']['FW_W'],r['ramp_connector_ttt_900_3000'],r['remaining_omega_ttt_900_3000'])]] for a,r in result.items()]),
        '위 분해는900–3000초 [veh·h]. 램프 connector 외 접근도로는 혼합 목적지이므로 모두 램프 대기열로 세지 않았다.','',
        '## 혼잡과 방출 반응','',
        '무제어 동측은 하류10702에서 저속이 나타난 뒤119·10613·2로 상류 저속 구간이 확대됐다. 2250–2400초 평균속도는119가24.0km/h, 그 상류10613이33.4km/h였다. RM에서는 같은 시간 각각32.1·100.6km/h이며,2700–2850초119는72.9km/h로 회복했다(무제어24.7). 하류10702는RM에서도 낮은 속도가 남았다. 이는 링크 평균에 근거한 전파 패턴이며 차량별 병목 원인 분류는 아니다.',
        '900–3000초10490 실제 합류는445→351대, connector 유입은446→380대로 감소했다. 정지 차량시간(<5km/h)은0.38→5.26veh·h, 최대 connector 재고는16→40대로 증가했다. 설정 수요는 같으며, 관측 도착 감소를 희망 수요 감소로 해석하지 않는다.',
        'RM의 동측 본선 이득은20.28veh·h(4.65%)지만,8개 connector에서6.47, 나머지Ω에서7.15, 서측 본선에서1.74veh·h가 증가해 전체 이득은4.91veh·h만 남았다. 본선만 보면 효과가 있고, Ω 전체 대기 비용까지 보면 현재 정책의 순효과가 작다.',
        'VSL은 동측 하류 저속 발생을 늦췄지만 입력부 저속 구간을 넓혔다. 서측 본선 TTT가248.63→273.72veh·h로 증가해 동측 일부 구간의 개선만으로 전체 이득이 되지 않았다. 동시 제어10490 제한 시작은2400초로RM 단독1800초보다 늦었으며, 단독 효과가 단순 합산되지 않았다.','',
        '## 실제 제어 노출','']
    for arm in ('rm','both'):
        text += [f'### {NAMES[arm]}','',*table(['램프','최소녹색/10초','첫 제한 [s]','제한시간 [s]','최대 하류 점유율 [%]'],[
            [mid,r['minimum_green_sec'],r['first_restriction_sec'],r['restricted_seconds'],f"{r['max_downstream_occ_pct']:.2f}"] for mid,r in result[arm]['rm_exposure'].items()]),'']
    for arm in ('vsl','both'):
        text += [f'### {NAMES[arm]} VSL','',*table(['구간','최소 분포 ID','제한시간 [s]'],[
            [zone,r['minimum_distribution_id'],r['restricted_seconds']] for zone,r in result[arm]['vsl_exposure'].items()]),'']
    text += ['## VSL 검지 위치에 대한 해석 제한','',
        '두 VSL 조건 모두 동·서측seg0만900초부터60 명령을 유지했고, 나머지6개 구간은120을 유지했다. seg0 검지기는 본선 입력 링크74·26의40m 지점이다. 입력1098·1099의 차량 구성1은 승용/기타 분포40, 중차량 분포30이며, 최초 본선 DSD120 통과 후 가속 과정도 이 검지값에 섞인다.',
        '900초 결정의 직전150초 검지값은 동측34.29km/h·27.41%, 서측27.59km/h·36.52%였다. 별도 무제어 FZP 공간 점검(750–900초)에서 동측0–100m 평균26.35km/h가600–700m에서96.59km/h로 높아졌다. 서측은500–600m41.59km/h,1100–1200m72.46km/h로 저속 구간이 더 길었다. 공간 평균은 차량시간 가중이며 검지점 통과차량 평균과 같은 통계량은 아니다.',
        '따라서 이 VSL 결과는 현재 검지기 배치의 규칙 정책 결과다. 합류 병목 예방을 충분히 시험했거나 VSL 자체의 잠재력을 판정한 것으로 볼 수 없다. 초기 가속·입력부 혼잡·하류 병목을 구분해 검지 위치를 재선정하는 것이 다음 검토 대상이며, 이번4조건 중간에는 위치·수요를 바꾸지 않았다. 근거:entry_acceleration_750_900.json 및 각decision_900.json.','',
        '## 삭제·미삽입과 검증','',*table(['조건','native 차로변경 삭제 경고','Ω 미확인 소실','종료 미삽입','전체 실행 경과 [s]'],[
        [NAMES[a],r['native_removals'],r['total']['unresolved_inside_disappearances'],r['uninserted'],f"{r['wall_seconds']:.1f}"] for a,r in result.items()]),'',
        '삭제 경고와 미확인 소실은 겹칠 수 있어 합산하지 않는다. 미삽입 차량은 Ω TTT에 포함되지 않으므로 지표만 낮아진 것을 자동으로 개선이라 판단하지 않는다.',
        '4조건의0–900초 전체 FZP 데이터 행 일치, 비대상 신호 LDP 일치, 모든 RM 실행 전환 및 VSL 적용 readback 검증 PASS. 입력 검지값에서 정책 결정을 재계산한 결과와 실행 명령표도 정확히 일치했다.',
        '새 무제어의0–2250초 전체 FZP는 앞선 DSD 무제어 결과와 정확히 일치해, 검지기 추가와 연속 실행 중간 정지가 기준 교통 결과를 바꾸지 않음을 확인했다.',
        'LSA는 보존했으나 COM 전환 누락 문제로 승인된 LDP를 실행 기준으로 사용했다. 초기 상태는 적용 전 readback 및 첫 native LDP 프레임으로 보존했다.',
        '차량 전수 COM 조회·MPC 초기화·예측·GNE 계산은0회. 갱신마다 native 검지 결과만 읽고 명령이 바뀔 때 쓰며, 전환 시점 사이를 RunContinuous로 진행했다. 표의 경과시간은 로딩·시뮬레이션·정책·실행검증을 포함하며 사후 FZP 분석은 제외한다. 순수 시뮬레이션 가속률로 해석하지 않는다.',
        '기존 정책 테스트9개 및 합성4조건의 활성화·녹색 trust region·66개 본선 DSD 주소 검사 PASS.',
        'VSL 단독의 최초 검증은 명령 ID60.0과 readback60의 문자열 비교 때문에 실패했다. 84개 적용값이 모두 수치상 동일함을 확인하고 정수 ID 비교를 수정해 재검증했다. 최초 실패 receipt·검증 출력은run_vsl/initial_failure_*에 보존했고, 교통 결과나 정책을 변경하지 않았다.',
        '단일 seed·3000초 초기 비교다. 장기 회복·다중 seed 유의성·최적 제어 성능·plant 예측 정확도를 입증하지 않는다.','',
        '다음 우선순위는 입구 가속 구간과 병목 상태를 구분하는VSL 검지 배치를 확정하는 것이다. RM은10490의 실제 방출·본선 이득·대기 비용을 함께 재현하는지 plant를 점검할 근거가 생겼다. 현재 결과만으로RM이 무효이거나VSL의 물리적 이득이 없다고 결론내리지 않는다.','',
        '![재고 변화](stocks.png)','', '![고속도로 혼잡](freeway_speed.png)','',
        '원자료: `analysis/*/area_timeseries.csv`, `ramp_150s.csv`, `merge_events.csv`, `freeway_links_150s.csv`; 실행검증: `verification.json`, 각 run의`fixed_validation.json`, `decision_*.json`.']
    (HERE/'REPORT.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    plot(analysis)
    print(json.dumps({a:{k:r[k] for k in ('ttt_improvement_pct','controlled_ttt_improvement_pct','end_omega_n','wall_seconds')} for a,r in result.items()},indent=2))


def plot(analysis,terminal=3000):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'.review-deps'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(3,1,figsize=(12,10),sharex=True)
    for arm in ARMS:
        rows=csvrows(analysis/arm/'stocks_1s.csv');area=csvrows(analysis/arm/'area_timeseries.csv')
        axes[0].plot([float(r['sim_sec'])/60 for r in area],[int(r['inside_vehicles']) for r in area],label=arm)
        for ax,key in zip(axes[1:],('FW_E_n','FW_W_n')):
            ax.plot([float(r['time_s'])/60 for r in rows],[int(r[key]) for r in rows],label=arm)
    for ax,title in zip(axes,('Omega inventory','East mainline inventory','West mainline inventory')):
        ax.set_ylabel('vehicles');ax.set_title(title);ax.axvline(15,color='gray',ls='--');ax.grid(alpha=.25);ax.legend()
        if terminal==4500:ax.axvline(37.5,color='gray',ls=':',label='2250s')
    axes[-1].set_xlabel('Simulation time [min]');fig.tight_layout();fig.savefig(HERE/'stocks.png',dpi=160);plt.close(fig)
    data={a:csvrows(analysis/a/'freeway_links_150s.csv') for a in ARMS}
    geometry=load(HERE.parents[1]/'user_native_20260914/native_fixed_profile_v3/analysis/results_v1/none/observations/geometry.json')
    fig,axes=plt.subplots(4,2,figsize=(14,13),sharex=True)
    for i,arm in enumerate(ARMS):
        for j,direction in enumerate(('FW_E','FW_W')):
            links=[str(r['link']) for r in geometry['chains'][direction]]
            values={(r['link'],int(r['start_s'])):float(r['mean_speed_kmh']) if r['mean_speed_kmh'] else np.nan for r in data[arm]}
            z=np.array([[values.get((link,t),np.nan) for t in range(0,terminal,150)] for link in links])
            ax=axes[i,j];im=ax.imshow(z,aspect='auto',vmin=0,vmax=120,cmap='RdYlGn',extent=[0,terminal/60,len(links)-.5,-.5])
            ax.set_yticks(range(len(links)),links);ax.set_title(f'{arm} / {direction}');ax.axvline(15,color='black',ls='--');ax.set_ylabel('Mainline link')
            if terminal==4500:ax.axvline(37.5,color='black',ls=':')
            if i==3:ax.set_xlabel('Simulation time [min]')
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Vehicle-time weighted speed [km/h]',shrink=.8)
    fig.savefig(HERE/'freeway_speed.png',dpi=160,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':main()
