import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

a=read(HERE/'assessment.json');protocol=read(HERE/'protocol.json')
executed=read(HERE/'executed_sources.json')
for p,h in executed.items():assert sha(Path(p))==h,p
stop=Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
assert sha(stop)==protocol['stop_sha256']
assert a['full_forecasts']==6 and a['max_mass_residual']<1e-7
assert a['max_route_residual']<1e-7 and a['max_resource_exceedance']<1e-7
assert 'Ran 37 tests' in (HERE/'tests.log').read_text(encoding='utf8')

# These are the two exact files owned by this bounded trial. Check all current
# executed pins before restoring, and retain both candidate code and tests.
restored={}
for name in ('physical_urban_transport.py','lane_plant_runtime.py'):
    source=ROOT/'evaluation/controllers'/name
    archived=HERE/(name+'.executed.txt');assert not archived.exists()
    archived.write_bytes(source.read_bytes())
    source.write_bytes((HERE/(name+'.before')).read_bytes())
    restored[str(source)]=sha(source)
for p,h in protocol['source_pins'].items():assert sha(Path(p))==h,p
test=HERE/'test_candidate.py';archived=HERE/'test_candidate.py.executed.txt'
assert not archived.exists();test.rename(archived)
save(HERE/'completion.json',dict(status='completed_partial_improvement_not_adopted',review=46,
    adoption=False,candidate_runnable_with_current_source=False,
    decision='47hold drainage error falls by7.45veh, but independent43 overdrain grows0.47veh and47 city-selection drainage response remains wrong. Preserve candidate as evidence, no production promotion or rate grid.',
    full_forecasts=6,compute_sec=a['wall_sec'],sessions={'84521':'EXIT0','46288':'EXIT0','51879':'postprocess_EXIT0'},
    tests=37,new_native=0,new_fzp_scans=0,past_only_coefficient_fits=1,coefficient_grids=0,new_push=0,
    production_restored=restored,production7_unchanged=protocol['source_pins'],stop_sha256=sha(stop),
    goal_complete=False))

table=[]
for seed,arm in [('47','hold'),('47','selected'),('43','nc'),('43','rm'),('43','vsl'),('43','both')]:
    p=a['cases'][seed][arm]['ports']['10643']
    table.append('|'+seed+' '+arm+'|'+ '|'.join(f"{p[s][field]:.2f}" for field in ('drain','final_stock') for s in ('native','before','after'))+'|')
doc='''# 10643 하류 목적지 미배정 차량의 차로 이용 후보

한 후보를450초 자율 예측6회로 검증했다. seed47 배수 오차 일부는 줄었지만 독립seed43 개선은 확인되지 않아 **정본 반영은 보류**했다. 실험 코드·출력은 보존하고 두 생산 파일은 실행 전 바이트로 복구했다. 기존7개 소스 SHA와9000초STOP 모두 동일하다.

## 바꾼 물리적 동작

링크71에서 현재 목적지가 미배정된 연속 주행 차량만, 더 많은 공간을 받는 인접 차로로 이동할 수 있게 했다. 기존 목적지가 있는 차량에는 적용하지 않았다. 목적지와 차량 질량을 보존하며 출구 선택은 현 위치에서 접근 가능한 기존 ALL 커넥터 규칙을 따른다. 관측 출구 비율이나 특정 제어 명령에 따른 보너스는 없다.

단일 계수0.12846556/s는 seed47의2550.1–2695.1초에 관측된3개 차로 이동과 수용 공간 노출량에서 얻었다. 5초 표본과3개 사건만으로 추정한 값이라 불확실성이 크다. 이후 자료는 검증에만 썼다. 계수 격자는 탐색하지 않았다. 전에 시험한 **지정 목적지 차로 사이 이동**과는 적용 집단이 다르다.

고속도로 FD·METANET 계수·유입 수요·신호·제어 명령·시간 간격·목적함수는 바꾸지 않았다. 후보의 compiled/AD 구현은 검증되지 않아 활성화 시 명시적으로 실패하도록 했다.

## 10643 결과: 본선에서 램프로 들어온 뒤 도시부로 배수

| 상태 | 실측 배수 | 기존 배수 | 후보 배수 | 실측 잔여 | 기존 잔여 | 후보 잔여 |
|---|---:|---:|---:|---:|---:|---:|
'''+ '\n'.join(table)+'''

단위는 대, 기간은450초다. seed47 hold의 본선→10643 진입은 실측96대/후보80.29대로 여전히 부족하다. 이 후보만으로 배수·잔여 오차 전체를 설명하지 못한다.

seed47의 도시 신호 선택에 따른 배수 변화는 실측−10대, 기존+14.31대, 후보+5.66대다. 차이는 줄었지만 방향은 여전히 틀린다. 이 비교는 **RM 단독 유지/완화 실험이 아니다**.

seed43의 Ω TTT 변화(무제어 대비, 차량·시간)는 RM 실측−1.547/후보−0.096, VSL 실측+0.777/후보−0.382, 병행 실측−1.453/후보−0.465다. 작은 손익 부호만으로 후보를 폐기하는 것은 아니지만, 제어 효과를 구별하는 개선 증거도 생기지 않았다.

## 채택 판단과 다음 순서

목적지 미배정 차량의 차로 사용 누락은 실제 자료의 근거가 있고, 혼잡 상태 배수도 일부 개선됐다. 그러나 이 간단한 공간 차이 법칙이 다른 상태에서도 올바른 배수 반응을 만든다는 근거가 부족하다. 이를 해결됐다고 보고 고속도로 계수로 남은 오류를 흡수하지 않는다. 더 많은 동일 계수 탐색은 하지 않는다.

우선8개off-ramp의 본선 진입·도시부 배수·재고를 함께 확인한다. 10643은 진입96/80대와 하류 과대 대기가 함께 남았고,10682는 seed47 진입147/146.89대로 맞지만 seed43에서는113/140.46대로 과다하다. 이처럼 상태별 경계 오류를 먼저 구분해야 한다. 그 뒤 영향을 받는 본선 셀만 제한적으로 보정하고, 같은 초기 상태의 NC/RM/VSL/병행 및 독립 상태에서 손익과 순위를 비교한다. 완벽한 궤적 일치를 기준으로 삼지는 않는다.

## 검증 및 재현 상태

- 새 후보10개+기존 보존·FIFO·신호 계약27개, 총37시험 통과. 비활성 후보120스텝은 이전 소스와 전이·재고·방출이 정확히 같다.
- 자율 예측6회, 초기 상태·기존 명령 동일, 미래 실측 입력 없음. 계산시간 합계223.736초이며 병렬 실행의 실제 경과시간과 다르다.
- 최대 질량 오차4.55e−13대, 경로 재고 오차2.09e−12대, 공유 수용량 초과1.72e−15대.
- 새 VISSIM/FZP 재스캔/push 없음. 완료된 두 실행 세션과 사후 처리 세션은 모두EXIT0.
- `candidate_config.json`은 보존된 실험 명세다. 현재 복구된 생산 코드에서 후보가 적용된 것처럼 재실행하면 안 된다. 적용된 정확한 두 소스와 시험은 `.executed.txt`로 보존했다.

관련 근거: `assessment.json`, `fit.json`, `protocol.json`, `completion.json`. 미래 도착을 넣은 원인 분리 재생은 별도 `../urban10643_conditional/README.md`에 있으며 자율 예측 결과와 혼합하지 않았다.
'''
target=HERE/'README.md';assert not target.exists();target.write_text(doc,encoding='utf8')
history=HERE.parent/'REVIEW.md'
with history.open('a',encoding='utf8') as stream:
    stream.write('\n\n## REVIEW46 — 10643 conditional source/route-free lane response\n\n'
        'Completed eight retrospective local replays (future native arrivals, NOT autonomous): normal discharge163–165 versus native mass-balance212, relaxing exit receiving changes nothing; delayed ERR2 removals separately accounted. Native route-free52 includes21 observed10642 exits. See urban10643_conditional/README.md.\n\n'
        'One past-only route-free71 pressure coefficient,37testsPASS,6 autonomous450 forecasts223.736compute seconds.47hold off10643drain61.04->68.49/native94,stock32.16->24.79/native15;43NCdrain73.91->74.38/native67 slightlyworse.47citydrainDelta+14.31->+5.66/native-10 stillwrong. Partial improvement, NOT adopted or gainqualified. Two source files restored byte-exact;7pins/STOP verified. Archivedcandidate, no further rategrid/native/FZP/push. Follow user order:8off entry/drain/storage first, neededcell calibration next, then common-state/independent control gains.\n')
agents=ROOT/'AGENTS.md'
note=('CURRENT UNROUTED71 (2026-10-02): PROGRESS ACTIVE/NOT_QUALIFIED REVIEW46. Eight conditional445s replays using existingnativecache,actualarrival/green diagnosticONLY; relaxingexitroom nochange,163-165normalout vsnative212 massbalance;2delayedERRremovals excluded.52unroutednative21direct10642exit, absent modeledlaneaccess. Onepast-onlyalpha.12846556/s from3events2550-2695;37testsPASS,6autonomous450223.736compute secs,84521/46288/51879 EXIT0 NO LIVE OWNED JOB.47hold10643drain61.04->68.49(native94),stock32.16->24.79(native15);43NC74.38(native67)slightlyworse;47cityDelta+5.66(native-10)stillwrong. Partial improvement NOTADOPTED;2sourcebytes+7pins+STOPexact restored, archivedcode/tests. DoNOTrepeat rate/FD grids orclaimgainqualified. First8off entry/drain/storage (10643entry80/native96;10682seed43entry140/native113) thenneededcellfit thensame-stateNC/RM/VSL/both andindependentgain. No native/FZP/push. CTGseparate. Readunrouted71/completion+README andurban10643_conditional/README.\n\n')
agents.write_bytes(note.encode('utf8')+agents.read_bytes())
print('Completed, archived candidate, restored all seven source pins and STOP, reports saved.')
