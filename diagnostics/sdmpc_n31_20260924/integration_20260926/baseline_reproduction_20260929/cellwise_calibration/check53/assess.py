"""Report frozen checks and conditional diagnostics; never launch simulations."""
import csv
import gzip
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
I=HERE.parents[2]
spec=importlib.util.spec_from_file_location('replay_assessment',I/'replay_congested_component.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)


def main():
    from evaluation.controllers import lane_plant_runtime as lpr
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.boundary_factory import ObservationData
    result=h.load(HERE/'summary.json');admission=h.load(HERE.parent/'additional_admission_s53.json')
    assert h.load(HERE/'status.json')['stage']=='complete_frozen_check'
    for path,digest in admission['pins'].items():assert h.sha(path)==digest
    protocol=h.load(HERE/'protocol.json')
    for path,digest in protocol['core_pins'].items():assert h.sha(I.parents[2]/path)==digest
    prior=result['versions']['prior'];joint=result['versions']['joint']
    conditioned=h.load(HERE/'arrival_diagnostic/summary.json');assert conditioned['conditional_only']
    model=lpr.load_sources(conditioned['manifest'])['component'];conditional_rows=[];port_rows=[];source_pins={}
    for record in admission['records']:
        if record['arm'] not in ('hold','release'):continue
        path=HERE/'arrival_diagnostic'/(record['arm']+'_prediction.json.gz');source_pins[str(path)]=h.sha(path)
        with gzip.open(path,'rt',encoding='utf-8') as f:pred=json.load(f)
        truth=ObservationData(record['truth']);conditional_rows.append(h._cellwise_measure(model,pred,record,truth))
        for connector in ('10639','10681','10490','10484'):
            rows=[truth.ports[round(2670.1+30*j,6),connector] for j in range(1,16)]
            assert all(float(r['unresolved_absences_veh'])==0 for r in rows)
            assert all(abs(float(r['end_n_veh'])-float(r['start_n_veh'])-float(r['arrivals_veh'])+float(r['departures_veh']))<1e-9 for r in rows)
            volume={k:sum(float(r[k]) for r in rows) for k in ('arrivals_veh','departures_veh')}
            weighted={k:sum(float(r[k])*(450-30*j+15)/3600 for j,r in enumerate(rows,1)) for k in volume}
            port_rows.append(dict(arm=record['arm'],connector=connector,volume=volume,weighted=weighted))
    def deltas(rows):
        a=next(r for r in rows if r['arm']=='hold');b=next(r for r in rows if r['arm']=='release')
        return {version:{k:b[version][k]-a[version][k] for k in ('ttt','mainline_ttt','ramp_ttt','off_ttt','exits')}
                for version in ('actual','predicted')}
    audit=dict(prior=deltas(prior['rows']),joint=deltas(joint['rows']),conditional=deltas(conditional_rows),native_ports=port_rows,
        conditional_not_qualification=True,source_pins=source_pins,new_rollouts=0)
    h.save(HERE/'response_decomposition.json',audit)
    # A literature scale check on existing observed states, not a new forecast.
    path=I/'closedloop9000_d4e2_analysis/recovery_flow_audit/native10484/receiving_screen/snapshots.csv'
    with path.open(encoding='utf-8-sig') as f:snapshots=list(csv.DictReader(f))
    supply=[]
    for arm in ('hold','release'):
        rows=[r for r in snapshots if r['arm']==arm];values=[]
        for r in rows:
            old=float(r['aggregate_current']);rho=float(r['rho23_avg'])
            new=min(old,1800*min(1.,max(0.,(180-rho)/(180-39.2))))
            values.append((float(r['time_s']),old,new))
        integral=lambda i:sum((a[i]+b[i])*(b[0]-a[0])/7200 for a,b in zip(values,values[1:]))
        supply.append(dict(arm=arm,samples=len(values),changed_samples=sum(abs(a-b)>1e-9 for _,a,b in values),old_opportunity_veh=integral(1),local_ramp_scaled_opportunity_veh=integral(2)))
    h.save(HERE/'origin_supply_scale_screen.json',dict(source=str(path),sha256=h.sha(path),rows=supply,
        formula='min(existing gap/cap budget,1800*clip((180-rho_cell23_mean)/(180-39.2),0,1))',
        literature='Hegyi et al.2005 Eq5: origin receiving scale Qo is on-ramp free-flow capacity. https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/03_016.pdf',
        qualification=False,conditional_observed_state=True,new_rollouts=0))
    gap=h.load(HERE.parents[1]/'local_ramp_gap10484/summary.json')
    lines=['# 셀별 보정의 seed53 확인과 램프 방출 진단','',
        '기존/159변수 공동 보정 모델의 자율450초 예측8회, 관측 미래 유입을 넣은 원인 분리2회, 별도의10484 gap계수 후보8회로 총18회 완료했다. 새 VISSIM·production 채택·push는 없다. 미래 유입 진단2회를 자율 예측 성능에 포함하지 않는다.','',
        '평가 범위는 동측31셀+8connector,2670.1–3120.1초, 동일30초 재고 사다리꼴 적분이다. Ω 전체가 아니다. seed53은 이번 계수 학습에는 쓰지 않았지만 예전 구조 진단에서 본 자료이므로 완전한 blind holdout은 아니다. 구성요소 삭제는0, 도시부 삭제는25/25/24/25여서 이 결과만으로 전체망 개선을 판정하지 않는다.','',
        '| 비교 | 실측 ΔTTT | 기존 | 셀별 공동 보정 |','|---|---:|---:|---:|']
    for old,new in zip(prior['all_pairs'],joint['all_pairs']):
        if old['base']!='hold':continue
        lines.append(f"| {old['arm']} − hold | {old['actual_delta']:+.3f} | {old['predicted_delta']:+.3f} | {new['predicted_delta']:+.3f} |")
    lines+=['',f"단위veh·h. 큰 RM 완화 손해 방향은 두 모델 모두 맞췄다. 공동 보정의 반응 손실은 {prior['loss']['response']:.5f}→{joint['loss']['response']:.5f}, 약{100*(1-joint['loss']['response']/prior['loss']['response']):.1f}% 감소했다. 작은 VSL 차이는 일관되게 맞추지 못했으며, 앞선 seed43 실패를 취소하지 않는다.",'',
        '## RM 완화 손해를 작게 보는 위치','',
        '| 부분 | 실측 | 공동 보정 자율 | 미래 유입을 알려준 진단 |','|---|---:|---:|---:|']
    for k,label in [('mainline_ttt','본선'),('ramp_ttt','진입 connector'),('off_ttt','진출 connector'),('ttt','합계')]:
        lines.append(f"| {label} | {audit['joint']['actual'][k]:+.3f} | {audit['joint']['predicted'][k]:+.3f} | {audit['conditional']['predicted'][k]:+.3f} |")
    lines+=['',
        'RM 완화의 본선 손해는 자율7.637 대·시간으로 실측8.767의 대부분을 설명하지만, 램프 대기 감소를 과대평가한다. 실제로는10639로26대,10484로15대가 더 도착했다. 다른 두 램프는 합계9대 감소해 순증가32대다. 고정된 도착 예측에서는 네 램프 모두 제어 간 도착 변화가0이었다. 이 차이가 모두 spillback 완화 때문이라고 단정하지 않는다.','',
        '실제 미래 본선·차로별 램프 유입을 공급한 조건부 진단에서는 합계 손해가1.406→2.999로 증가했다. 여전히 실측5.929보다 작다. hold의10484합류는45.30대(실측45)로 맞지만 release는108대(실측91)로 많다. 따라서 도착량 예측만의 문제도 아니며, 램프별 방출 시점과 수용 반응이 남는다. 이 진단은 미래 입력이므로 운용 예측이나 검증 통과 근거가 아니다.','',
        '## 작은 수용계수 보정: 채택하지 않음','',
        '기존 모델의10484 critical gap만2→2.5/3초로 바꾸고, follow-up1.5초·head 서비스·셀별 계수는 유지했다. 두 후보를 seed29 후기4조건으로 먼저 평가했으며, 다른 상태의 결과로 후보를 고르지 않았다.','',
        f"최선2.5초도 기존 대비 반응 손실이{abs(gap['training_improvement'])*100:.1f}% 증가해 사전 기준을 통과하지 못했다. 8회로 종료했고 추가12개 확인 예측은 실행하지 않았다. 3초에서 램프 대기 차이는 가까워지지만 본선 방출 손실이 더 작아져 전체 제어 반응이 나빠졌다. 단순한 서비스 상한 하향을 성공으로 채택하지 않는다.",'',
        '첫 준비는 config 최상위 구조를 잘못 참조해 rollout 전에 실패했다. local_ramp_gap10484.log를 보존하고 구조 접근만 수정했으며, 실행 결과는 retry 로그와 각 후보 폴더에 보존했다.','',
        'Hegyi et al.(2005) 식5의 수용 유량은 본선 전체 용량이 아닌 진입램프 자유류 용량 Qo를 사용한다. [원문 식5](https://www.dcsc.tudelft.nl/~bdeschutter/pub/rep/03_016.pdf). 이 차이도 기존 seed53 관측 상태182개에서 검사했지만, 국소 임계밀도39.2·램프 용량1800을 적용해도 기존 gap 상한이 더 낮아 기회량이 바뀌지 않았다. 이는 조건부 식 검사이며 전체 자율 예측에 대한 불가능성 증명은 아니다. 기존 식을 교체하지 않았다.','',
        '## 다음 단계','',
        '셀별 계수 보정은 일부 다른 상태에도 개선을 전달하지만, 모든 순이득 오류를 본선 계수로 흡수하면 안 된다. 다음에는 기존 coupled plant에서 RM 변화에 따른 도시→램프 도착·접근부 대기 응답을 확인하고, connector 내부 방출·posthead 대기를 분리한다. 본선에서 남는 누적 방출 오류도 함께 유지한다. 이전 RM 통과량 감소·대기 비용·동적 off-ramp 저장·배수는 보존한다. 전체 Ω와 SDMPC 선택의 검증은 완료되지 않았다.']
    (HERE/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(response_improvement=1-joint['loss']['response']/prior['loss']['response'],delta_ttt_actual=audit['joint']['actual']['ttt'],autonomous=audit['joint']['predicted']['ttt'],conditional=audit['conditional']['predicted']['ttt'],gap_improvement=gap['training_improvement'],new_rollouts_total=18)))


if __name__=='__main__':main()
