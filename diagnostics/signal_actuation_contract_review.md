# 신호 모델–writer 실현성 감사 및 미적용 patch

2026-09-10, 검토 시 HEAD `3299040`. 생산 adapter/VBS/runtime_setup은 변경하지 않았다. 현재 진행 중인 signal zero/green10/offset10 실험과 별개인 제안이다.

**신호 제어가 모델이 평가한 시간창으로 실행되지 않는 결함을 재현했다.** 녹색 상한, offset 부호, 현시 순서, 죽은 현시 clearance, 정수 초 event hold가 동시에 어긋난다. 여기에 local follower의 phase cache가 무신호 movement를 신호로 막는 결함이 있다. 이는 성능 개선의 보장이 아니라, 먼저 비용 모델과 물리 명령을 같은 대상으로 만들기 위한 수정이다.

## 확인한 원인

| 원인 | 실제 재현 | 소스 |
|---|---|---|
| 후보 상한 101 vs writer 상한 90 | SC109 `{p1:0,p2:20,p3:96.5,p4:24.5}`는 모델 주기150; CSV는 p3만90으로 잘라 주기143.5. JSON과 비용은96.5를 유지 | `vendor/NumSim-mine/src/models/state.py:515`, `evaluation/controllers/plant_cycle.py:85`, adapter `write_action_csv:11851` |
| offset 부호 | model `(t-offset)%cycle`; writer `FMod(t+offset,cycle)` | `urban_queue_model.py:718`, VBS `SignalCompositeStateAt:919` |
| 현시 순서 | 모델은 p1,p2,p3,p4; SC105 등 writer는 major=p2를 먼저 배치. SC1001 major=p1이라 이 문제만 우연히 없다 | `urban_queue_model.py:708`, `signal_group_plan.py:266` |
| 죽은 현시 clearance | 합법 SC109 0/20/90/31에서도 model은 죽은 p1 앞의3초를 삽입, writer는 생략 | `urban_queue_model.py:711`, `signal_group_plan.py:287` |
| 실행 시각 격자 | CSV는3자리, SG 창은6자리, VBS는 정수 초 상태를 검사하고 다음 event까지 유지. 연속 창 적분은 경계에서 같은 서비스율이 아니다 | adapter `write_action_csv:11874`, VBS `SignalGroupStateFromPlan:1993`, `FMod:5326` |
| local 무신호 cache | SC1001_W_to_onE, t900 첫5초: 기존 local gf=0, global gf=1. phase만 cache key로 써 같은 phase의 signalized 행을 복사 | `wu_faithful_follower.py:1544` |

첫 analytic audit(`signal_feasibility_audit.json`)의 SC109 수치 근거는 **첫 audit-affected n7의 t2100 frozen action**이다. pure n7 action이라고 해석하지 않는다. 그 audit는 부호·배치 결함 증거이며, 실제 정수 초 event 동일성은 아래 VBS oracle 결과로 별도 검증했다.

원래 SC109의 주기평균 p3는 모델96.5/150=0.643333, CSV90/143.5=0.627178이다. p2/p4도 분모가 바뀌므로 한 현시만의 오차가 아니다. writer 뒤에서 남는6.5초를 다른 현시에 주는 것만으로는 이미 계산한 최적화 비용이 바뀌므로 해결이 아니다.

## 제안하는 하나의 계약

`urban.physical_signal_contract: true`를 명시할 때만 켠다. flag가 없으면 기존 값을 그대로 반환하고 기존 함수로 위임한다.

1. 실제 selector가 고른 plan, runner clearance, SC별 live phases/cycle/budget을 cfg에 저장한다. worker가 같은 cfg를 받아 hook만 재설치한다. 전역의 마지막 cfg/plan을 사용하는 방식은 없다.
2. 물리 feasible set은 `sum(g)=budget`, live `max(model_min,5) <= g <= min(derived_max,90)`, dead `g=0`이다. `N*lower <= budget <= N*upper`를 먼저 확인한다. `lower*(N-1)+upper == budget`는 물리 cap이 추가된 상자에 필요한 조건이 아니다.
3. scalar 후보, phase-vector 확장, pair-exchange, 가격 방향을 **채점 전에** 물리 상자와 CSV 0.001초 격자에 놓는다. 정수 녹색 강제는 하지 않는다. 반올림 잔차만 같은 예산 안에서 보정한다.
4. 이전 action의 첫 seed는 복사 후 명시적으로 투영하고 최대 변경량을 diagnostic에 남긴다. 예시 SC109는 0/23.25/90/27.75가 된다. 이는 한 가지 일관된 bounded-simplex 투영이며, 과거 행동을 물리적으로 그대로 재생했다는 뜻이 아니다.
5. 모델 창은 기존 `signal_group_plan.plan_windows`를 재사용한다. 실제 writer의 `t+offset`, live-only clearance, major-first 순서, 정수 초 event hold와 같은 계산을 한다. Python `%` 대신 실제 VBS FMod 식을 써 소수 주기 경계의 부동소수 표현도 대조한다.
6. offset은 기존 `offset_promotion.written_offset_sec`가 허용한 값만 모델에서도 사용한다. intent_only이면0, test_only이면 강제 표/강제 scalar이다. 승격 evidence를 생성하거나 PASS로 바꾸지 않는다.
7. local green cache key에 unsignalized 여부를 포함한다. service 함수는 global과 같은 함수 하나를 호출한다. 현재 mainline plan은 활성 SG122개가 모두 phase의 [0,1] 창이라 나머지 phase cache는 공유할 수 있다. partial SG plan은 movement cache가 필요하므로 이 patch는 명시적으로 거부한다.
8. writer 직전에는 같은 벡터·선택 plan·offset 권한인지 **검증만** 한다. writer에서 다시 배분하지 않는다. legacy 두 축만 덮어쓰는 `signal_green_freeze`와 이 계약의 동시 활성화는 거부한다.

## 산출물과 검증

- `signal_actuation_contract.patch`: 새 helper + canonical adapter + shared runtime initializer/worker의 최소 integration hunk. 아직 적용하지 않았다.
- `signal_actuation_contract_candidate.py`: 검토 가능한 helper 원문. live adapter에서 import하지 않는다.
- `build_signal_contract_patch.py`: 현재 소스에서 patch를 재생성하는 진단 도구. 생산에서 AST 실행은 추가하지 않는다.
- `test_signal_actuation_contract.py`: source-derived 실제 초기화 함수, 실제 후보 함수, 실제 CSV writer 및 VBS 함수 oracle 검증.
- `native_fixed_selector.patch`: 아래 별도 alias 결함 수정.

최종 전체10 tests PASS(13.256초, scalar 후보 정밀도 guard 포함). 최종 재생성한 두 patch의 `git apply --check`도 모두 PASS.

`signal_contract_regression.json`: pure n7 저장 action37개 ×17SC × 상대offset −20/−10/0/+10/+20 × 모든4phase ×5초 구간 총465,460건, model–CSV event fraction 최대 오차0. 이 검증은 **투영한 후보**를 측정한다. 전체 phase값 중1,617개가 변경됐고, 2ms 초과 변경105개, 최대6.5초다. 따라서 과거 n7과 비트 동일한 새로운 제어 run이라고 해석하면 안 된다.

`signal_contract_vbs_oracle.json`: 실제 VBS 원문 `SignalGroupStateFromPlan`, `FMod` 등을 그대로 추출해 10,395건 대조 PASS. 17SC, ±10/20, 주기150/150.001/149.999, 150000초 부근 경계를 포함한다. COM 객체와 VISSIM은 생성하지 않는다. native ownership/물리 green readback의 대체 검증은 아니다.

추가 회귀는 OFF 원본 값·객체 동일성, cap90/죽은현시/예산/비유한값 거부, 실제 scalar/교환/가격 방향 후보, actual local/global movement별 gf, selected plan 사용, shared initializer와 worker 재설치·deepcopy를 포함한다.

실행:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest diagnostics.test_signal_actuation_contract
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' diagnostics/build_signal_contract_patch.py
git apply --check diagnostics/signal_actuation_contract.patch
git apply --check diagnostics/native_fixed_selector.patch
```

VBS 함수 oracle는 Windows Script Host 설정 읽기 때문에 sandbox 밖 테스트 실행이 필요했다. VISSIM 실런 권한이나 생산 파일 수정은 사용하지 않았다.

## native-fixed의 출처와 의미

`native_fixed_control`은 raw `signal_group_actuation_plan_v3.json`을 하드코딩한다(adapter:11460). 실제 n7 selector는 mainline plan이다. raw/selected의 axis green은 SC5 `97/23/101/25` 대 `43/23/47/25`, SC7 `91/90/0/24` 대 `67/90/0/24`로 다르다.

별도 patch는 `signal_group_actuation_plan_path()`와 `load_signal_group_actuation_plan()`을 사용하고 누락을 거부하며 출처와 `native_fixed_native_program_replay=0`을 기록한다. 기존 CLI alias는 호환성을 위해 유지하되 설명을 **선택 계획의 native-derived axis green seed**로 바로잡는다.

이 source 수정만으로 native replay가 되지는 않는다. mainline SC7은 native120초지만 겹치는 축 union을 순차화하면190초, SC16은 native150초지만 gap을 압축하면116초다. 게다가 이 alias는 downstream policy guard를 우회하지 않는다. 원본 native 기준선은 실제 .sig를 native ownership으로 구동한 no-control이며, 고정 signal profile은 별도의 합성 시간창 대조군이다.

## 통합 전 남은 범위

현재 patch는 작동 함수와 명시 candidate 경계의 회귀를 통과한 제안이며, 완전한 wu-link decision/성능 승격 결과는 아니다. live3개 signal arm 종료 후 대표 n7 관측의 실제 offline decision을 끝까지 실행해 예외·post-policy 후보·가격 worker·예측 endpoint의 일관성과 계산 시간을 확인해야 한다. 기존 교통/FD 계수는 바꾸지 않았다. phase-fraction의 step=None은 정수 event 격자 유리수 superperiod의 평균이며, 유한 horizon 검증은 명시 absolute-step 경로로 했다.

SC105 고정 profile의 현재 CSV cycle150.001도 지원 가능한 표현이다. 다만 과거 profile을 모델로 replay할 때는 그 CSV 벡터에 맞는 cycle/budget을 cfg에 명시해야 한다. 본 proposed optimizer는 모델의150초 예산을 보존해 후보를 만들기 때문에 과거138.001초 녹색합을 조용히150초 모델로 평가하지 않는다.

## E8 예측 충실도 독립 sanity check

부모 `measure_prediction_fidelity.py`와 CSV를 읽고 숫자를 재계산했다. E8의 초기 speed/density는 관측과 <5e-7 차이로 같으므로, +30/+150초 복구 오예측을 초기 projection 차이로 설명할 수 없다. 정체 후27구간 +150초 speed bias +20.03807km/h, density bias −46.54098veh/km/lane와 t1200/t3300 예시가 일치한다. 실제 action JSON/current-rate persistence demand/현행 coupled endpoint의 **복합 예측오차**라는 한계가 타당하며, 순수 FD 오차로 분해한 자료는 아니다.

전체망으로 확장할 때는 FW_W cell14/16의 초기 density가 관측의0.75인 별도 차이를 구분해야 한다(최대7.95418veh/km/lane). E8에는 해당하지 않는다. 재현성을 위해 config, 선택 plan, shared runtime 및 관련 model module SHA도 provenance에 추가하는 것이 좋다.
