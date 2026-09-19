"""Source-backed decision report after all native and prediction checks finish."""
from datetime import datetime
from study import *

def table(header,rows):
    return ['|'+'|'.join(header)+'|','|'+'|'.join(['---']*len(header))+'|',*['|'+'|'.join(map(str,r))+'|' for r in rows]]

def main():
    bank=HERE/'native_s33_v1';fresh=e.load(bank/'predictions/results.json');verify=e.load(bank/'paired_verification.json')
    area=e.load(bank/'analysis/comparison.json')['arms'];installed=e.load(HERE/'installed_v1/results.json')
    base=e.load(HERE/'screen_v1/baseline.json')['scores'];phase=e.load(HERE/'phase_probe_v1/results.json')
    response_mae={m:statistics.mean(abs(sum(r['delta_east']['predicted'].values())-sum(r['delta_east']['actual'].values()))
        for a,r in rs.items() if a!='none') for m,rs in fresh['models'].items()}
    labels={'none':'무제어','rm_ramp':'RM','vsl':'VSL','both':'동시'}
    summary={'fresh_seed':fresh,'native_comparison':area,'paired_verification':{a:{k:r.get(k) for k in [
        'passed','event_readbacks','native_meter_samples_checked','paired_warmup_prefix','paired_native_signals_passed']} for a,r in verify.items()},
        'installed_checks':{k:v for k,v in installed.items() if k!='records'}}
    lines=['# 상태별 METANET·제어 응답 종합 검토 — 2026-09-19','',
      '상태별 relaxation·anticipation을 기존 정본 실행 경로에서 시험할 수 있도록 수정하고, 기존 자료의 구조 가설 비교와 새 seed33의 고정 명령 4조건 실런을 마쳤다. **제어 이득을 설명하는 plant 보정은 아직 미완료이며, 시험한 회복 계수 후보는 채택하지 않는다. 기본 모델도 교체하지 않았다.**','',
      f"새 seed의 동측 부분 영역 ΔTTT MAE는 기존 {response_mae['baseline']:.4f}→회복 후보 {response_mae['recovery']:.4f} veh·h로 악화됐다. 실제 고정 제어도 seed23의 이득을 반복하지 못했다. 특정 제어에 항상 이득이 생기도록 계수를 맞추면 이번 자료와 모순된다.",'',
      '## 실제 변경','',
      '- `freeway.state_response`에 방향별 가속/감속 relaxation 시간, 현재·하류 밀도차별 anticipation, 임계밀도 초과 시 계수 배율을 명시할 수 있다. 값은 config에만 둔다. 선택기는 새 보상 없이 기존 비용을 사용한다.',
      '- 보존식, 수요·경로, 실제 합류량을 쓰는 merge 항, 실제 차로 감소 지점의 lane-drop 항, 유한 on/off-ramp 저장 및 대기 비용을 유지했다. 별도 adapter나 임의 capacity gain/drop을 추가하지 않았다.',
      '- relaxation 분기는 희망속도와 현재속도의 비교다. 실제 가속도 부호나 적색→녹색 출발지연을 직접 측정한 계수가 아니다. METANET에서 τ는 anticipation 분모에도 들어가므로 순수 회복 지연만의 보정으로 해석하지 않는다. ramp 서비스 표에 이미 포함된 출발 손실을 중복 차감하지 않는다.',
      '- 34개 단위·기존 회귀 검사, 48개 설치식/독립 진단식의 상태·유량·램프 재현 비교, 기본 설정의 과거 8개 전체 예측 JSON 일치, 비대상 서측 불변을 확인했다. 파라미터 검사 PASS. 새 config들은 실험 후보이며 full GNE 승격본이 아니다.','',
      '## 검토한 가설과 기각 근거','',
      '기존 seed13·23에 대해 37개 변경 가설과 기준을 비교했다(반복 기준 포함 40행×16예측). 자유류·혼잡 전·혼잡·후기 상태와 동일 초기 상태의 제어 응답을 함께 사용했다. 모든 조합을 전수 탐색한 것은 아니다. seed23은 이미 본 개발 자료다.','',
      '- 고정 v_free·rho_crit·FD 형상·kappa, merge δ, 실제 lane-drop φ.',
      '- 하류 밀도차별 ν, rho_crit 전후 ν, 위/아래 방향 relaxation τ.',
      '- 실제 desired-speed 분포 평균 비율에 따른 VSL 희망속도 곡선 변화. vf를 r배, rho_crit을 r^(−γ)배로 두되 γ=0,0.5,1만 사용해 곡선상 용량 증가를 전제하지 않았다. 이 진단은 희망속도식의 변화이며 별도 램프 수용식을 재적합한 완전한 VSL FD 구현은 아니다.',
      '- 기존 일관된 two-branch FD. 임계밀도·VSL·혼잡 가지를 함께 바꾸고, 속도식만 교체하지 않았다.',
      '- 과거150초 경계 평균과 실제 미래 경계를 넣은 조건부 진단을 분리했다. 후자는 온라인 예측 성능이 아니다.','',
      'triangular FD의 일부 후보는 절대 오차를 낮췄지만 다른 seed의 제어 비용 차이는 악화됐다. VSL FD 변화도 초기 상태의 응답 적합은 좋아졌으나 후기 자료에서 악화됐다. 따라서 이 후보들을 정본으로 채택하지 않았다. two-branch 전용 τ·ν·공간별 FD의 전체 결합 보정까지 끝낸 것은 아니므로, FD 계열 자체가 불가능하다고 결론내리지는 않는다.','',
      '동측 본선+동측 on/off connector의 첫450초 ΔTTT [veh·h]. 음수가 개선이며 Ω 전체 값이 아니다.','']
    rows=[]
    for seed in ['13','23']:
        for a in ARMS[1:]:
            b=base[seed]['deltas'][a];r=installed['records']['recovery'][seed]['deltas'][a]
            rows.append([seed,labels[a],f"{b['observed_total']:+.4f}",f"{b['predicted_total']:+.4f}",f"{r['predicted_total']:+.4f}"])
    lines+=table(['seed','명령','VISSIM','기존 node 모델','회복 τ 후보'],rows)
    lines+=['','두 seed의 VSL 구간·시점·명령이 다르므로 이것만으로 seed 분산을 추정하지 않는다. 특히 후기 VSL100은 기존 모델에서 전후 궤적이 같았다. 평균속도 상한만으로 native desired-speed 분포 변경을 표현하는 한계다.','',
       '## 새 seed33 — 실행과 동일 초기 상태 검증','',
       '사용자 수정 가속 기하 + ramp DSD120, 동측 본선 input1098만 기존 기준의0.8배. 예전의 전역 고속도로80/도시50 조건과 다르다. 기존 seed23 입력과 randSeed 외 바이트가 같음을 확인했다. SimPeriod9001을 유지하고 SimBreak4500에서 종료했다.','',
       '0–2400초 동일 조건 후 10490/SC9107 RM을 g8→6→4로 제한하고 3300초부터 g6→8→10으로 해제했다. VSL은 E5 DSD51–58을 2400–3300초120→100, 이후120으로 복구했다. 나머지 신호·수요·경로·램프·VSL은 고정했다. 명령은 결과를 보기 전에 동결했다. ALINEA나 MPC의 새 폐루프 성능 실험은 아니다.','']
    execution=[]
    for a in ARMS:
        r=e.load(bank/f'run_{a}/run.json');v=verify[a]
        assert r['completed'] and v['passed']
        elapsed=(datetime.fromisoformat(r['finished'])-datetime.fromisoformat(r['started'])).total_seconds()
        execution.append([labels[a],4500,f'{elapsed:.1f}',v['event_readbacks'],v['native_meter_samples_checked']])
    lines+=table(['조건','종료초','런+검증 경과초','명령 readback','LDP 미터 표본'],execution)
    prefix=verify['rm_ramp']['paired_warmup_prefix']
    lines+=['',f'세 제어 조건 모두 2400초까지 전체 FZP 데이터가 무제어와 정확히 일치했다. prefix 증거: `{prefix}`. 초기 상태·실제 신호 전환·비대상 신호 동일성 및 VSL 적용 readback을 대조했다. LSA는 보존하되 사용자가 허용한 native LDP를 SG 실행 판정에 썼다.','',
       '## 새 seed의 실제 성능과 예측','',
       'Ω TTT는 고속도로+도시 protected network 내부 차량시간이다. TTD는 살아서 Ω 밖으로 이동한 사건과 정상 망 종단 출구 추정이며 내부 이동·미해결 소실·종료 잔여를 제외했다. 1초 궤적 사다리꼴 적분을 사용했다.','']
    rows=[]
    for a in ARMS:
        vals=[]
        for start,end in [(2400,2850),(2400,4500),(0,4500)]:
            value=next(w for w in area[a]['windows'] if w['start_s']==start and w['end_s']==end)['omega_ttt_veh_h']
            ref=next(w for w in area['none']['windows'] if w['start_s']==start and w['end_s']==end)['omega_ttt_veh_h']
            vals.append(f'{value-ref:+.3f}')
        full=next(w for w in area[a]['windows'] if w['start_s']==0 and w['end_s']==4500)
        rows.append([labels[a],*vals,full['omega_exit_events_observed_plus_terminal_inferred'],full['unresolved_inside_disappearances'],area[a]['native_removals'],area[a]['native_uninserted_at_end']])
    lines+=table(['조건','Ω ΔTTT 2400–2850','2400–4500','0–4500','TTD 0–4500','내부 미해결 소실','삭제 경고','종료 미삽입'],rows)
    lines+=['','무제어 Ω TTT는3688.809 veh·h이다. RM/VSL/동시는 각각0.228%/1.235%/1.103% 증가했고, TTD도 각각5/157/69대 감소했다. 미해결 소실과 native 삭제 경고는 범위가 달라 합산하지 않는다. 두 조건의 차이가 작은 경우 seed 변동과 입·출고 차이까지 분리해야 한다.','']
    rows=[]
    for a in ARMS[1:]:
        b=fresh['models']['baseline'][a];r=fresh['models']['recovery'][a]
        rows.append([labels[a],f"{sum(b['delta_east']['actual'].values()):+.4f}",f"{sum(b['delta_east']['predicted'].values()):+.4f}",
            f"{sum(r['delta_east']['predicted'].values()):+.4f}",
            f"{b['actual_component']['merges']['RM_C10490']:.0f} / {b['predicted_component']['merges']['RM_C10490']:.2f}"])
    lines+=['','같은450초 동측 부분 영역의 비용 차이와10490 합류량:','']+table(['명령','VISSIM ΔTTT','기존 예측','회복 후보 예측','실제/기존 예측 합류'],rows)
    lines+=['','삭제·미삽입이 남는 망에서 작은 ΔTTT 하나를 확정적 제어 이득으로 해석하지 않는다. 서로 다른 Ω/부분 영역,450초/2100초 결과도 섞지 않는다.','',
       '## 공간 전파와 대기 비용','',
       '같은 동측 물리 셀에서 2400초 이후 최초로120초 이상 v<40km/h가 이어진 구간의 시작초를 비교했다(30초 snapshot, N≥5). `없음`은4500초까지 이 기준에 해당하지 않는다는 뜻이며 순간 저속이나 더 짧은 정체를 배제하지 않는다. 2400초 표시는 시작 때 이미 저속일 수 있다. 셀 번호는0부터 시작한다.','']
    observed={a:e.ObservationData(bank/'observations'/a) for a in ARMS}
    def first_low(data,cell):
        run=[]
        for t,rs in sorted(data.cells.items()):
            if t<2400:continue
            r=next(r for r in rs if r['road']=='FW_E' and r['cell']==cell)
            if r['n_veh']>=5 and r['v_kmh'] is not None and r['v_kmh']<40:
                run.append(t)
                if t-run[0]>=120:return run[0]
            else:run=[]
        return '없음'
    spatial=[]
    for cell in [0,7,8,12,13,14]:
        g=next(c for c in observed['none'].geometry['cells'] if c['road']=='FW_E' and c['cell']==cell)
        spatial.append([cell,f"{g['start_m']:.0f}–{g['end_m']:.0f}",*[first_low(observed[a],cell) for a in ARMS]])
    lines+=table(['동측 셀','누적거리 m',*[labels[a] for a in ARMS]],spatial)
    costs=[]
    for a in ARMS[1:]:
        d=fresh['models']['baseline'][a]['delta_east']['actual']
        costs.append([labels[a],*[f'{d[k]:+.4f}' for k in ['mainline','on','off']]])
    lines+=['','첫450초 동측 체류시간 변화의 분해 [veh·h]:','']+table(['명령','본선','8개 중 동측 진입','동측 진출'],costs)
    lines+=['','이 seed에서 VSL의 첫450초 동측 부분 영역 −0.1958은 본선 예방 이득으로 해석할 수 없다. 본선 체류시간은 +0.1000이고 진출 connector 재고시간이 −0.2708로 줄었다. 같은 구간 Ω는 약+0.007로 거의 동일하다. 램프/도시 경계 간 재고 이동과 시차를 보존하지 않으면 부분 영역의 감소를 네트워크 효율 개선으로 오인할 수 있다.',
       '후기 저속 위치도 일관되게 개선되지 않았다. VSL은 동측 셀14의 지속 저속이 무제어3150초보다 이른2760초에 나타났고, 셀13도2820→2700초였다. RM은 셀13의 해당 저속 에피소드가 사라졌지만 셀14에서는2610초로 앞당겨졌다. 정체를 하나의 총량이나 단일 발생시각으로만 맞춰서는 이러한 상쇄를 놓친다.','']
    lines+=['',
       '## 시간 분포와 남은 구조 문제','',
       '램프 도착·진출 배수의150초 평균을 유지하면서 그 안의 과거30초 시간 분포를 반복하는 진단도 수행했다. 미래 관측을 쓰지 않고 총량을 보존했다. 망의 실제 신호 주기가 혼재하므로 이는 시간 정보 손실의 민감도 검사이며 검증된 native 신호 예측기로 채택하지 않는다.','']
    rows=[]
    for kind,seeds in phase['records'].items():
        for seed,r in seeds.items():rows.append([kind,seed,'FAIL' if r['invalid'] else 'PASS',f"{r['absolute_loss']:.3f}",f"{r['response_loss']:.3f}",*[f"{r['deltas'][a]['predicted_total']:+.4f}" for a in ARMS[1:]]])
    lines+=table(['시간 분포 대상','seed','수치 검증','절대 복합오차','응답 복합오차','RM ΔTTT','VSL','동시'],rows)
    lines+=['','## 다음 변경의 기준','',
       '1. 기본 계수와 상태별 계수만으로 비용 방향이 맞았다고 판정하지 않는다. 동일 시작 상태의 실제 합류 감소, 본선 차량시간 변화, 램프·진출 대기를 각각 맞혀야 한다.',
       '2. 공간 평균이 숨기는 합류 차로/통과 차로의 재고·속도 차이와 실제 병목 방출을 우선 조사한다. 필요하면 병목 부근만 두 차로군으로 나누되 관측 재고와 통과량으로 식별하고, 보상을 위한 capacity drop을 넣지 않는다.',
       '3. 경계의 경우 각 램프를 공급·배수하는 실제 신호와 이동 시간을 추적해야 한다. 고정 평균이나 모든 포트에150초 주기를 복사하는 방식으로 green/offset 효과까지 설명할 수 없다.',
       '4. 현재는 RM/VSL 부분 모델의 반응 검증이다. 전체 Ω 도시부 대기와 NP/NUF를 포함한 full follower game 완성, 새 MPC4500초 폐루프 개선,10% 개선은 달성했다고 주장하지 않는다.','',
       '## 근거와 재현','',
       '- `screen_v1..v3/`: 구조·계수 후보와 각 상태/제어 응답. `boundary_v1/`: 미래 경계 조건부 진단과 셀별 오류.',
       '- `installed_v1/`, `test_state_response.py`, `parameters_check.log`: 설치 검증과 실험 config.',
       '- `native_s33_v1/protocol.json`, `model_freeze.json`, `paired_verification.json`, `analysis/`, `observations/`, `predictions/`: 동결 조건·실행·사후 비교. 원시 FZP/LDP/오류 파일은 각run에 보존.',
       '- [Hegyi 등의 A1 연구](https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/03_001.pdf)는 밀도차에 따른 anticipation 구분과 충격파 억제를 다룬다. 해당 결과가 이 망에서도 자동으로 성립한다는 뜻은 아니다.',
       '- [Frejo 등의 VSL 모형 비교](https://research.tudelft.nl/en/publications/macroscopic-modeling-of-variable-speed-limits-on-freeways/)는 VSL에 따른 임계밀도·용량·준수도의 변화가 별도 식별 대상임을 보여준다. 본 검토의 γ 가설은 이 망의 실측으로 검증할 후보이며 문헌 계수의 이식이 아니다.','']
    if (HERE/'SUMMARY.json').exists():
        if e.load(HERE/'SUMMARY.json')!=summary:raise AssertionError('Existing summary data differs; use a new evidence version')
    else:e.save(HERE/'SUMMARY.json',summary)
    (HERE/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(HERE/'REPORT.md')

if __name__=='__main__':main()
