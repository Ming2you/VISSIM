"""Save bounded motion verification and handoff without another computation."""
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def functions(p):
    found={}
    def walk(node,prefix=''):
        for n in ast.iter_child_nodes(node):
            if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                key=prefix+n.name
                if not isinstance(n,ast.ClassDef):found[key]=ast.dump(n,include_attributes=False)
                walk(n,key+'.')
            else:walk(n,prefix)
    walk(ast.parse(p.read_text(encoding='utf-8-sig')))
    return found

stages=['ordinary_v3','cumulative_v1','local_upstream_v1']
results={s:read(HERE/('distance_'+s+'_result.json')) for s in stages}
assert all(r['scalar_response_and_trajectory_exact'] and r['max_state_error']==0 and
           r['initial_state_error']==0 and r['full_omega_scoring_rejected'] for r in results.values())
latest=results[stages[-1]]
pins={k:sha(Path(k))==v for k,v in latest['pins'].items()}
assert all(pins.values())
plan=read(HERE/'plan.json')
core={k:sha(Path(k))==v for k,v in plan['source_before'].items()};assert all(core.values())
changes={}
for name in ['lane_plant_runtime','lane_urban_runtime','lane_offramp_runtime','native_internal_input','urban_flow_accounting']:
    suffix='.py.before_distance.txt' if name in ('lane_plant_runtime','urban_flow_accounting') else '.before_distance.txt'
    before=functions(HERE/'before'/(name+suffix))
    after=functions(Path('evaluation/controllers')/(name+'.py'))
    changes[name]=dict(changed=[k for k in before if before[k]!=after.get(k)],
        added=sorted(set(after)-set(before)),unchanged=sum(before[k]==after.get(k) for k in before))
verification=dict(stage='urban_motion_verified_full_omega_objective_pending',
    fixed_command_comparisons={s:dict(trajectory_and_flow_exact=True,ttt=r['ttt_omega_veh_h'],
        baseline_seconds=r['baseline_seconds'],observer_seconds=r['observed_seconds'],
        covered_subtotal_veh_km=r['receipt']['covered_subtotal_veh_km']) for s,r in results.items()},
    new_fixed_command_forecasts_in_these_comparisons=6,optimizer_iterations=0,
    earlier_ordinary_audit='distance_ordinary_audit_result.json',
    tests=55,latest_source_pins_unchanged=pins,objective_core_unchanged=core,
    ast_function_changes=changes,cumulative_lanes=latest['cumulative_motion'],
    local_upstream_initial_reservations=latest['native_motion']['initial_reservations']['local_upstream'],
    geometric_distance_bound_width_veh_km=sum(b-a for a,b in latest['native_motion']['geometry_bounds_by_provider_stock'].values()),
    unresolved_stock_labels_by_prefix=dict(Counter(k.split(':')[0] for k in latest['receipt']['unresolved_positive_stocks'])),
    unresolved_scope=['Generic initial urban and initial1102 gate travel with aggregate ETA/physical assignment ambiguity',
        'Inside gate in_SC1_W future transport','Final all-provider coverage/ownership/AD/final-command score binding'],
    stopped_movement_queue_note='162movement labels are mostly stationary point queues, not162 missing roads; native inter-head moving subset already recorded separately.',
    native_predecessor='../analysis/summary.json',
    new_native_runs=0,pushed=False,goal='ACTIVE/NOT_QUALIFIED')
target=HERE/'urban_motion_verification_v2.json';assert not target.exists()
target.write_text(json.dumps(verification,indent=2,ensure_ascii=False),encoding='utf8')
text='''
## 후속 검증: 도시부 거리와 기존9000초 결과

기존 seed29 SDMPC9000은 정상 완료됐고 사후 비교도 한 번 마쳤다. `../ANALYSIS_9000.md`와 `../analysis/summary.json` 참고. 전체 Ω TTT는 NC7263.267→SDMPC7589.973veh·h(+4.498%). 전체 Ω 거리의5초 속도 적분은359189.136→358933.832veh·km다.54주기 모두 RMg10, VSL 제한21주기, SDMPC 수렴0/54(각최대2회 예산). LDP/VSL 실행·제어 전FZP431233행 동일 검증은 통과했으나 이득은 없다. 삭제243→367, 미분류 Ω 소실751→843을 보존한다. 기존 런을 개선 성공으로 표시하거나 목적항 효과를 단정하지 않는다.

일반 도시 movement·내부 생성6입력·경계 출구·70/10637/10640/10776 이동을 기존 accepted amount/ETA에 연결했다. 초기 local12대와 이후 실제 수락 이동을 기록하며, 기하 메타데이터 이외의 모델 식은 바꾸지 않았다. 도시 평행 경로가 하나로 정해지지 않으면 이동거리 상·하한과 중앙값 근사를 기록한다. 이번450초의 기하 모호 범위 폭 합은0.56847veh·km로, 매우 작은 이득의 부호를 판정할 근거로 쓰지 않는다.

10643·10700은 기존 삼각FD의 초기 밀도·누적 진입·방출 곡선으로 내부 통과량을 복원해 공간 적분했다.1초 경계 유량 선형 보간과2m 이내 공간 적분은 거리 관측 근사이며 물리 유량을 바꾸지 않는다. 현재 양의10643 두 차로에서1m로 세분한 차이는각1.46e-6/4.26e-7veh·km다.10700은 이 상태에서 비어 있으므로 양의10700 실상태 검증으로 주장하지 않는다. 첫 단위시험의 rigid-packet 가정은 삼각FD 초기 jam-density packet과 맞지 않아 해석값을 고쳤으며 실패 로그도 보존했다. 정지 jam 재고·부분 Ω·부분 시간·사전 방출 없는 이동 시험은 통과했다.

세 차례의450초 ON/OFF 비교(6예측)에서 **모든 기존 상태·유량·TTT가 정확히 일치**했다. TTT517.5983935981086veh·h, 최근 baseline20.05s/observer22.64s는 고정 명령 예측 시간이며 optimizer 반복이나 native 런 시간은 아니다.55단위/회귀 시험 통과. `urban_motion_verification_v2.json`에 새 함수 범위와5개 목적함수 코어의 원본 해시 일치를 저장했다.

**전체 Ω 주행거리 목적함수는 아직 비활성/미완료**다. 일반 초기 도시 이동의 물리 링크와 집계 ETA 대응, 초기1102 목적지 태그, in_SC1_W의 미래 이동, 전체 공급자 커버리지와 주체별 비용/AD/final gate가 남았다. 미분류224stock labels를224개 누락 도로로 오해하지 말 것:162는 대부분 정지 movement queue,57storage,4미소 merge_pending,1gate transit이다. 초기 이동 중 명령과 무관하게 이미 예약된 부분은 후보 공통 상수인지 따로 입증할 수 있으나, 현재 이를 가정하여 전체 범위 완료로 처리하지 않았다.

이번 결과만으로 근거 있는 공통 소규모 동역학 수정은 없으므로 expanded036 유지. CTG 강한RM/회복 제한 검증도 남았다. 다음두9000은 아직 시작하지 않았다. 거리 가중치 답변 대기, 기존 STOP 유지, push 없음. 세후속비교 세션37712/39347/12593 및 사후분석22371은 모두 exit0. postprocess_plan은completed이므로 FZP 재분석 금지.
'''
with (HERE/'README.md').open('a',encoding='utf8') as f:f.write(text)
plan.update(implementation_status='55tests PASS; ordinary/native-simple/local-upstream and cumulative-lane distance verified. Three450 ON/OFF pairs ALL states/flows/TTT EXACT. Initial aggregate urban/gate travel, inside gate future path and complete objective/owner/AD/final gate remain. FullOmega scoring disabled. Predecessor9000 complete and analyzed once: OmegaTTT+4.498%, no gain. No new native run.',
    implementation_verification='urban_motion_verification_v2.json')
plan['distance_options']['status']='ordinary_local_cumulative_motion_verified_full_scope_pending'
(HERE/'plan.json').write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding='utf8')
note='CURRENT FOLLOW-UP (2026-09-30): E/ANALYSIS_9000.md + E/objective_pair/urban_motion_verification_v2.json. R2 normal9000 COMPLETED/owned processesclosed; postprocess22371exit0 ONCE,postprocess_planCOMPLETED,no FZPre-scan. OmegaTTT NC7263.267->SDMPC7589.973(+4.498pct), sampledOmegaDistance359189.136->358933.832;prefix431233rowsEXACT,LDP/VSLPASS,LSAFAILpreserved. RMall10/54,VSLrestricted21,SDMPCconverged0/54(max2). removals243->367,unresolvedOmega751->843;NOTgainqualification. No evidence-backed common dynamics correction,retainexpanded036. FullOmega distance:55tests,ordinary/native-simple/local-upstream+cumulative10643/10700. Three450pairs6forecasts ALLstate/flow/TTT517.5983935981086EXACT;latest20.05/22.64s fixedrollout,nooptimizer. localinitial12;10643distance26.470005vehkm,2mvs1m diff<1.5e-6 each;10700zero inthisstate. FULLscoreOFF:initialaggregateurban/gate,insidegatein_SC1_W future,fullcoverage/owner/AD/finalgatepending;224stocklabelsNOTroads(162stationarymovement,57storage,4merge,1transit). Weightpending,CTGstrongRM/recoverypending;TWO future9000 notstarted. Fiveobjectivecores/STOPunchanged,newnative0,push0. Sessions37712/39347/12593TERMINAL0. GoalACTIVE/NOT_QUALIFIED; do not restart predecessor or mark objective complete.\r\n\r\n'
agents=Path('AGENTS.md');agents.write_bytes(note.encode('utf8')+agents.read_bytes())
print(json.dumps(dict(verification=str(target),tests=55,core_unchanged=all(core.values()),new_native_runs=0)))
