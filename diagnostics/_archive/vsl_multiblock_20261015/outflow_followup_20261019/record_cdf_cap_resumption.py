"""Record the completed bounded probe and cached residual audit; no model execution."""
import datetime
import hashlib
import json
import math
from pathlib import Path

A = Path(__file__).resolve().parent
V = A.parent
O = A / 'cdf_cap_candidate'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def main():
    marker = O / 'resumption_recorded.json'
    assert not marker.exists()
    done = read(O / 'completion.json')
    assessment = read(O / 'assessment.json')
    residual = read(O / 'residual_localization.json')
    assert done['new_forecasts'] == 2 and assessment['status'] == 'not_sufficient_response_correction'
    for doc in (done, assessment, residual):
        for p, digest in doc['source_pins'].items():
            assert sha(p) == digest, p
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    compact = {}
    for case, report in assessment['reports'].items():
        last = report['rows'][-1]
        costs = report['regional_model_cost_deltas']
        grouped = dict(east_mainline=costs['freeway:FW_E'], west_mainline=costs['freeway:FW_W'],
            ramp_stock=math.fsum(v for k,v in costs.items() if k.startswith('ramp:')),
            remaining_area_components=math.fsum(v for k,v in costs.items() if not k.startswith(('ramp:','freeway:'))))
        assert abs(math.fsum(grouped.values()) - last['candidate_omega_delta']) < 1e-7
        compact[case] = dict(rows=report['rows'], physical_constraints=report['physical_constraints'],
            forecast_seconds=report['seconds'], final_flow_error_reduction_percent=100*(1-abs(last['candidate_flow_delta']-last['native_flow_delta'])/abs(last['original_flow_delta']-last['native_flow_delta'])),
            model_cost_deltas_veh_h=grouped, model_outside_cost_delta_veh_h=math.fsum(report['outside_model_cost_deltas'].values()))
    lane = []
    for i in (1,2,3,4):
        rows = [r for r in residual['contrasts'] if r['case']=='selected' and r['cell']==18 and r['lane']==i]
        lane.append(dict(lane=i, cumulative_transport_proxy_delta_veh=math.fsum(r['transport_proxy_delta_veh'] for r in rows)))
    next_work = ('Use the saved native/model baseline and lane transition evidence to identify why the model smooths the cell18 congestion/recovery response. '
                 'The CDF cap largely removes false VSL braking but is not a sufficient gain model. Do not repeat its two forecasts or promote it. '
                 'Inspect active lane-exchange/speed-recovery closure and independent baseline evidence before proposing one bounded correction; '
                 'do not invent a VSL capacity bonus or introduce future observations. No new native, coefficient grid, full optimization, package copy or push.')
    result = dict(status='completed_unadopted_missing_recovery_response', updated_utc=now,
        resumed_by_user=True, prior_approval_capacity_block_resolved=True,
        new_forecasts=2, new_native=0, new_fzp_scans=0, new_fits=0, new_full_optimizations=0, production_edits=0,
        forecast_budget_consumed=2, forecast_budget_remaining=0, candidate_adopted=False, goal_complete=False,
        cases=compact, native_lane_transport_localization=lane,
        owner_closure=dict(pid=14028, creation_utc='2026-10-19T09:11:44.1512760Z',
            entrypoint_session=97921, observed_entrypoint_exit_code=0, process_absent_after_completion=True,
            evidence='exec session exit0 and subsequent Get-Process -Id14028 returned no process; no termination action'),
        interpretation=[
          'Two-zone450 throughput response -28.868 -> -0.223 vehicles versus native +31. This reduces the absolute error by about48%, but misses the observed release.',
          'Candidate regional stock response +0.218 versus native -30; Omega delta +0.005406 versus native -0.045833vehh. Near-zero total cost is not dynamic validation.',
          'At2550 cell18 native speeds hold31.72/twozone75.45 while model hold58.40/twozone58.32kmh. Baseline congestion and controlled recovery are both missed.',
          'Native cumulative cell18 Nv/L contrast +31.472 is on lanes2..4; it is a transport proxy, not lane exit counts or proof of a unique cause.',
          'The broad storage cleanup preserved source/cache bytes: all forecast, assessment and residual input pins verified.'],
        limitations=assessment['limitations'] + residual['limitations'],
        app_goal_status='blocked',
        app_goal_note='Actual get_goal remains BLOCKED from the earlier external review outage. User resumed work successfully; the outage is no longer blocking analysis. Goal is incomplete; this API cannot set status ACTIVE.',
        next=next_work,
        source_pins={str(p):sha(p) for p in (O/'completion.json',O/'assessment.json',O/'residual_localization.json',A/'audit_cdf_cap_residual.py')})
    old = read(O / 'decision.json')
    save(O / 'decision_before_resumption.json', old)
    save(O / 'decision.json', result)
    for name in ('plan.json','summary.json'):
        path = V / name
        doc = read(path)
        save(O / (name.removesuffix('.json') + '_before_resumption.json'), doc)
        doc.update(status='offline_vsl_response_calibration_incomplete', updated_utc=now, next=next_work)
        doc['cdf_cap_hypothesis_20261019'] = dict(status=result['status'], decision=str(O/'decision.json'),
            new_forecasts=2, candidate_adopted=False, prior_approval_block_resolved=True,
            cached_lane_residual_audit=str(O/'residual_localization.json'))
        doc['analysis_resume_20261019'] = dict(status='completed_bounded_probe_goal_incomplete',
            app_goal_status='blocked', app_goal_note=result['app_goal_note'], source_pin_checks='PASS', native_runs_added=0)
        save(path, doc)
    text = '''

## 2026-10-19 사용자 재개: CDF 혼잡 제한 2예측 완료, 미채택

저장공간 정리 후 기존 코드·입력 해시를 확인하고 준비된 단일90/두 구역90의450초 예측 두 건을 한 번 실행했다. 과거 자동 승인 검토 장애는 해소됐다. 새 native·FZP 스캔·계수 보정·전체 최적화·생산 수정은0이다. Python14028의 생성시각과 정상 entrypoint exit0/소유 종료를 확인했고, 차량 보존·초기 상태·도시/RM 명령 동일성·조건부 물리 제약을 통과했다. 계산은 예측 자체만 각각6.05/6.22초이며 전체 SDMPC 결정 시간이 아니다. 초기화와 자료 읽기 시간은 별도다.

450초 변화(각110 기준):

| 조건·지표 | 실측 | 기존 모델 | CDF 후보 |
|---|---:|---:|---:|
| 단일90 통과량 [대] | +6 | −20.89 | −0.23 |
| 두 구역90 통과량 [대] | +31 | −28.87 | −0.22 |
| 두 구역90 관심영역 잔여 [대] | −30 | +26.05 | +0.22 |
| 두 구역90 ΩTTT [대·시간] | −0.04583 | +1.11133 | +0.00541 |

과도한 감속/손실 예측은 줄었으나 실제 방출 증가와 재고 감소는 재현하지 못했다. 두 구역 통과량 변화의 절대 오차는 약48% 감소했지만, 작은 전체 TTT 부호만으로 성공을 판정하지 않는다. 새 법칙은 미채택이며 독립 검증/AD/NP·NUF 최적화 검증으로 승격하지 않았다.

저장된5초 기록만 추가로 분해한 결과18번 셀의 누적 Nv/L 변화는 차로1/2/3/4에서−0.003/+11.681/+10.913/+8.882대였다. 합+31.472는 기존 수송 적분과 일치한다. 이는 차로별 출구 통과량이 아니며, 차량 수/속도의 대칭 분해도 인과효과 분해가 아니다. 같은 차량의 관측 차로변경 빈도 차이는 설명적 근거로만 보존했다.

2550초18번 셀의 실측 평균속도는110일 때31.72, 두 구역90일 때75.45km/h지만 모델은58.40/58.32다. 모델이 무제어 혼잡과 VSL하의 회복을 모두 평탄하게 예측하는 오차가 남는다. 다음은 이 구간의 활성 차로교환·속도 회복 식과 독립 기준선 자료로 원인을 좁히는 작업이다. 충분한 근거 없이 VSL 용량 보너스를 넣거나 추가 격자/실런을 하지 않는다.

상세: [완료 판정](outflow_followup_20261019/cdf_cap_candidate/decision.json), [차로별 잔차](outflow_followup_20261019/cdf_cap_candidate/residual_localization.json). 앱 목표 메타데이터는 과거BLOCKED 상태로 남아 있지만 분석은 사용자 요청에 따라 재개됐고, 보정 목표는 미완료다. 기존 실패/STOP/결과는 보존했다.
'''
    with (V/'README.md').open('a',encoding='utf8') as f:
        f.write(text)
    save(marker, dict(status='complete', updated_utc=now, decision_sha256=sha(O/'decision.json'),
        plan_sha256=sha(V/'plan.json'), summary_sha256=sha(V/'summary.json'),
        readme_sha256=sha(V/'README.md'), goal_complete=False))
    print(json.dumps({'status':result['status'], 'forecasts':2, 'source_pins':'PASS', 'native':0}))


if __name__ == '__main__':
    main()
