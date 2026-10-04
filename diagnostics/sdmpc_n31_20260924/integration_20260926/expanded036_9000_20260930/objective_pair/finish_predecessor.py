"""Record completed native evidence; do not rerun, fit, launch or publish."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
E=HERE.parent
def read(p):return json.loads(p.read_bytes())
def write(p,r):p.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf8')
summary=read(E/'analysis/summary.json')
closure=read(E/'owned_closure_and_postprocess.json')
assert closure['status_stage']=='requested_native_arms_complete_unanalyzed'
assert closure['observed_remaining']==[] and closure['postprocess_exit_code']==0
assert summary['paired_prefix_exact'] and all(x['native_execution_passed'] for x in summary['arms'].values())
rows=read(E/'analysis/sdmpc_decisions.json')['decisions']
assert len(rows)==54 and all(r['written_command_binding_passed'] and r['command_bounds_and_slew_passed'] for r in rows)
a,b=summary['arms']['nc'],summary['arms']['sdmpc']
comparisons=[('전체 Ω TTT [veh·h]','TTT_0_9000_veh_h'),('제어 시작 후 Ω TTT [veh·h]','TTT_900p1_9000_veh_h'),
 ('Ω 주행거리, 5초 속도 적분 [veh·km]','sampled_TVD_Omega_veh_km'),('확인된 정상 Ω 유출 사건 [veh]','Omega_TTD_events'),
 ('Ω 종료 잔여 [veh]','Omega_end_vehicles'),('전체 망 비정상 삭제 [veh]','native_removals'),
 ('종료 미삽입, native 집계 [veh]','native_uninserted_at_end'),('전체 망+미삽입 시간 [veh·h]','native_total_time_including_uninserted_veh_h')]
report=['# expanded036 seed29 SDMPC9000 완료 비교','',
 '정상 실행은 완료됐으나 제어 이득은 확인되지 않았다. 기존 모델의 Ω TTT 목적함수만 사용한 런이며, 이번에 준비하는 cost-to-go/주행거리 항은 적용되지 않았다.','',
 '|지표|무제어|SDMPC|차이(SDMPC−NC)|','|---|---:|---:|---:|']
for label,key in comparisons:report.append(f'|{label}|{a[key]:,.3f}|{b[key]:,.3f}|{b[key]-a[key]:+,.3f}|')
report += ['',f"전체9000초 Ω TTT **{100*(b['TTT_0_9000_veh_h']/a['TTT_0_9000_veh_h']-1):.3f}% 증가**. 제어 시작 후는 {100*(b['TTT_900p1_9000_veh_h']/a['TTT_900p1_9000_veh_h']-1):.3f}% 증가했다.",'',
 '## 검증 범위','',
 '- 제어 전431,233개 FZP 데이터 행 해시가 동일하다. 동일 seed29·선택망·수요 이력 비교다.',
 '- 실제 신호/RM은 사용자 승인 LDP 기준, VSL은 적용 readback으로 검증했다. LSA COM 누락은 계속 FAIL이며 LDP 통과와 구분한다.',
 '- 원래 실행 검증기의 process_exit/completion 필드는 일반 러너 영수증이 없어false다. 별도 owned_closure_and_postprocess.json에 이번 소유 PID/생성시각 대조 및 정상 종료를 기록했다. 원본 검증 JSON을 덮어쓰지 않았다.',
 '- 5초 관측에서 마지막4.9초는 마지막 재고/속도를 유지한 추정이다. 거리도 표본 속도 적분이며 정밀 개별 궤적 길이와 같다고 주장하지 않는다.',
 f"- Ω 내 기록 소실 미분류 사건은 NC {a['unresolved_Omega_disappearances']}, SDMPC {b['unresolved_Omega_disappearances']}개다. 정상 유출 사건 수는 확인된 사건만이며, 삭제·미분류를 완료 차량으로 합산하지 않는다.",'',
 '## 제어 및 해석','',
 f"54주기 중 RM 제한 선택은 {sum(bool(r['restricted_meters']) for r in rows)}회, VSL 제한은 {sum(bool(r['restricted_vsl']) for r in rows)}회다. 도시 신호도 함께 제어했으므로 악화를 VSL 하나에 귀속하지 않는다.",
 f"PFO/SDMPC 각 최대2회 반복 예산을 사용했고 SDMPC 수렴 판정은 {sum(r['sdmpc_converged'] for r in rows)}/54다. 실행 가능 후보 선택과 수렴은 다르다. 기록된 PFO+후속 SDMPC 계산시간 합은 {sum(r['pfo']['seconds']+r['sdmpc_after_pfo_seconds'] for r in rows)/3600:.3f}시간이며 native simulation 전체 경과시간이 아니다.",
 '서로 다른 초기 상태에서 계산한 예측 개선량들을 합해 실제 이득으로 해석하지 않는다. 이 결과만으로 terminal cost나 거리 보상이 악화를 해결한다고 판단할 수 없다.','',
 '## 다음 두 실험','',
 '이번 완료 결과만으로 정당화되는 소규모 동역학 수정은 아직 없다. 임의 계수 보정 없이 expanded036을 공통 기준으로 유지한다. 거리 계측은 물리 동역학을 바꾸지 않는다.',
 '전체 Ω 거리의 미지원 이동·초기 재고와 owner/AD/final gate를 검증한 뒤 CTG-only, TVD-only9000초를 동일 조건으로 실행한다. 거리 가중치는 아직 사용자 답변 대기다. 새 런은 이 문서 작성 시점에 시작하지 않았다.','',
 '근거: analysis/summary.json, analysis/sdmpc_decisions.json, 각 arm의execution.json/area_metrics.json/native_errors.json. 원본을 보존했다.','']
report_path=E/'ANALYSIS_9000.md';assert not report_path.exists();report_path.write_text('\n'.join(report),encoding='utf8')
post=read(E/'postprocess_plan.json');post.update(stage='completed',execution_session=22371,exit_code=0,
 result='analysis/summary.json',result_sha256=hashlib.sha256((E/'analysis/summary.json').read_bytes()).hexdigest(),
 execution_receipt='owned_closure_and_postprocess.json',repeat_analysis=False)
write(E/'postprocess_plan.json',post)
plan=read(HERE/'plan.json');plan.update(current_native_actual_sec_at_least=9000,
 predecessor_completed_and_analyzed=True,predecessor_result='../analysis/summary.json',
 common_correction_decision='No evidence-backed small dynamics correction adopted; keep expanded036 common to both future arms. Distance accounting is passive and must not alter dynamics.')
plan['distance_options']['scope_authorization']='도시부 포함 전체 Ω 주행거리부터 구현'
write(HERE/'plan.json',plan)
print(report_path)
