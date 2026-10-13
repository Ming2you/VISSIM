"""Preserve a qualified local improvement without declaring control gain solved."""
import datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;H=HERE.parent
read=lambda p:json.loads(p.read_bytes())
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'completion.json').exists()
c=read(HERE/'comparison.json');assert not c['ad_retention_gate']
for p,d in read(HERE/'plan.json')['source_pins'].items():assert sha(Path(p))==d,p
for folder in ('forecast2400_corrected','forecast3300'):assert read(HERE/folder/'completion.json')['status']=='complete'
assert not (HERE/'ad2400').exists()
s=read(HERE/'forecast2400_corrected/summary.json')['results']
e=next(r for r in c['source_heads3300'] if r['group']=='SC16_E')
record=dict(status='complete_local_head_improvement_joint_control_gain_unqualified',time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    tests=107,completed_fixed_forecasts=3,partial_failed_forecasts_preserved=2,new_ad_sweeps=0,new_selections=0,new_native=0,
    local_physical_support_retained=True,control_config_promoted=False,
    delta_omega=c['delta_omega_veh_h'],heldout_SC16_E=e,
    hold_shared_constraints=s['hold']['shared_constraints'],selected_shared_constraints=s['selected']['shared_constraints'],
    ad_skip_reason='Same-cap held action is infeasible under increased boundary entry; joint gain direction remains wrong. Candidate kept as local physical evidence only.',
    no_tiny_gain_sign_refit=True,calibration_control_gate_passed=False,full_wall_benchmark_launched=False,
    source_pins={str(HERE/n):sha(HERE/n) for n in ('comparison.json','assess.py','preflight.json','debit_failure_evidence.json','README.md')})
save(HERE/'completion.json',record)
p=read(HERE/'plan.json');p['status']=record['status'];p['completion']='completion.json';p['next']='Use existing results to locate remaining urban gain/source error; no same-rate search or automatic native adoption.';save(HERE/'plan.json',p)
p=read(H/'plan.json');p['sc16_supply']=dict(status=record['status'],path='sc16_supply/completion.json',tests=107,forecasts=3,ad=0,
    local_physical_improvement=True,joint_gain_qualified=False,calibration_control_gate_passed=False)
p['previous_goal_turn']=dict(time_utc=record['time_utc'],classification='progress',completed=[
    'SC16 east shared single-lane service inferred from past only; three turn budgets unified across finite receivers.',
    '107 tests and three fixed forecasts passed physical conservation/writer checks. SC16E native20-27 predicted7-9 becomes20-24; unused3300actual25 becomes23.19 from10.84.',
    'Captured/fixed Python3.12 compensated-sum versus sequential debit roundoff5.55e-17; preserved both failed partial traces.',
    'Whole joint Omega delta still wrong: native+4.1931 versus candidate-6.4315; unchanged merge84.53 versus84. Hold NP cap exceeds33.12vehicles; selected feasible. No AD/native promotion.'],
    next='Keep calibration/control-response validation first. Trace remaining source/arrival and urban-cost errors from existing evidence, not another SC16 rate fit. Only after qualification run pinned full SDMPC wall equivalence with unchanged horizon/budget.')
p['runtime_priority']['calibration_then_wall']=True;p['runtime_priority']['full_wall_comparison_launched']=False
save(H/'plan.json',p)
with (H/'README.md').open('a',encoding='utf8') as f:
    f.write('\n\n### SC16 동측 공유 방출 검증 (2026-10-09)\n\n')
    f.write('`sc16_supply/README.md` 참조. 과거 통과량으로 한 차로의 세 방향 공유 방출을 검토했다. 107시험·고정 명령 3예측 완료. 실측20–27대/150초에 기존7–9대→20–24대, 미사용3300초 실측25대에10.84→23.19대로 국소 개선. 전체 공동 Ω 손익은 실측+4.1931/예측−6.4315대·시로 여전히 반대이고 유지 명령 N_P도33.12대 초과한다. 물리 개선 근거는 보존하되 제어 설정 승격·추가 AD/native 실행은 하지 않았다. Python3.12 합산 반올림 오탐만 수정했고 실패 자료는 보존했다. 보정·큰 제어 손익 확인을 마친 다음 같은450초 지평·후보 예산의 전체 SDMPC wall time 최적화를 진행한다.\n')
print(json.dumps({k:record[k] for k in ('status','tests','completed_fixed_forecasts','new_ad_sweeps','new_native','full_wall_benchmark_launched')}))
