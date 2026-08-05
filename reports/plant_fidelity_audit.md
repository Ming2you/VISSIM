# VISSIM Rollout Plant 충실도 감사

생성일: 2026-08-05
기준 commit: `dc216be623abc3021963dd2735b4e485d01c6e68`
감사 branch: `codex/plant-fidelity-audit-20260805`
실제 NumSim: `vendor/NumSim-mine`, snapshot `35a5c82`, `src` 불일치 0건

## Plant의 목적과 목표

이 plant는 VISSIM의 차량 궤적을 미시적으로 완전히 복제하기 위한 모델이 아니다. VISSIM의 현재 상태를 누락·중복 없이 받아서 MPC의 60초~15분 후보 제어안을 빠르게 평가하는 controller-independent surrogate다.

따라서 목표는 다음 네 가지다.

- **상태 정합성:** 차량, queue, storage, 속도, 경계 유출입을 물리적 stock에 한 번씩만 투영한다.
- **동역학 정합성:** 동일 초기 상태·수요·신호에서 queue 성장·해소, spillback, freeway 전파를 VISSIM과 유사하게 예측한다.
- **제어효과 정합성:** green, offset, VSL, ramp metering의 효과 부호와 action 순위를 VISSIM과 같게 판단한다.
- **운영 정합성:** 실제 실행 소스와 검증 소스가 같고, 결과가 재현 가능하며, 한 제어주기 안에 계산을 끝낸다.

합격 기준은 차량 궤적의 완전 일치가 아니라 질량·신호·시간축이 물리적으로 맞고 controller가 잘못된 action을 고르지 않는 것이다.

## 판정

**종합 판정: 불가.** 현재 구현은 감사 가능한 계측 경로와 fail-closed 보호장치를 갖췄고, nominal seed 13의 상태 투영은 조건부로 지지할 수 있다. 그러나 현재 link assignment는 물리적 동률이 미해결이고, controlled signal은 보호 현시를 2상으로 축약하며, monitor movement-SG 귀속도 일부 추정이다. 실제 H=3 계산시간은 154.75초로 운영 gate를 넘었다. 3수요×3seed의 동적·action-ranking 검증도 아직 수행되지 않았다. 따라서 이 plant를 P-Stack/G6 성능의 근거 또는 실운영 rollout plant로 승격할 수 없다.

| 범위 | 판정 | 근거 |
|---|---|---|
| 실행 소스·입력 provenance | 지지 가능 | 실제 import 경로, NumSim snapshot, 입력·코드·`.sig` hash가 run별로 고정됨 |
| nominal seed 13 상태 투영 | 조건부 | 네 anchor residual 0.18~0.57%, clipping 0; 다른 수요·seed는 미검증 |
| 신호 명령 전달·지속 | 지지 가능 | immediate/post-step readback 10,448/10,448 일치 |
| 신호 물리·시간축 | 불가 | controlled protected phase 축약, monitor SG 추정, event oracle 없음 |
| 동역학·spillback·action ranking | 미평가 | VISSIM paired future trajectory와 3×3 matrix 미실행 |
| 실시간 운영 | 불가 | 실제 production adapter H=3 154.75초, 기준 p95 30초/hard 45초 초과 |

자동 정적·계약 감사는 `PASS 14 / FAIL 2 / NOT_EVALUATED 1`이었다. `FAIL`은 assignment tie와 runtime, `NOT_EVALUATED`는 signal event timing이다. 이 숫자는 미실행 동적 gate를 합격으로 간주하지 않는다.

## 치명 결함

### 1. 링크 귀속이 물리적으로 확정되지 않음

독립 파서가 동일 hop의 하류 terminal tie 33건과 ambiguous upstream tie 6건을 찾았다. 정렬은 결과의 결정성만 보장하며 어느 경로가 물리적으로 맞는지는 결정하지 않는다. legacy artifact의 `957 owned + 22 freeway + 226 exit`는 확정된 분할로 볼 수 없다. 진단용 signal-first 해석은 `973 + 6 + 226`으로 달라진다.

새 assignment 도구는 기본 `--tie-policy error`로 artifact 생성을 중단하고, generator도 `tie_status=CLEAR` 또는 hash-bound 승인 없이는 live artifact 생성을 거부한다. 이는 결함의 전파를 막지만 결함 자체를 해결한 것은 아니다.

### 2. 신호 readback은 맞지만 신호 물리가 아직 틀릴 수 있음

controlled 15개 SC의 runtime 함수는 이름에 EB/WB가 있으면 모두 major, NB/SB면 모두 minor 상태를 적용한다. 예를 들어 native VISSIG에 직진과 보호좌회전이 분리되어 있어도 같은 방향의 SG가 동시에 green이 될 수 있다. 따라서 readback 100%는 VBS가 요청한 축약 상태가 COM에 유지됐다는 뜻이지 native conflict·보호 현시를 재현했다는 뜻이 아니다.

monitor 26개에는 fixed `.sig` replay를 구현해 항상-green 결함을 제거했다. 26 schedule과 716 movement가 생성되고 영구 always-green/permanent-red movement는 0건이다. 다만 진단상 375 movement가 angle/phase fallback을 사용하고 425 movement가 복수 SG union으로 계산되며, exact origin으로 단일 SG에 연결된 것은 약 145개다. 이 수치는 서로 독립 분류가 아니며, lane/turn 기반 검증이 필요하다.

### 3. 동역학 및 action effect 증거가 없음

현재 live evidence는 nominal seed 13의 fixed/no-control 한 런, 짧은 signal readback 런, anchor 2100의 H=3 계산 한 번이다. 저·현행·혼잡 수요와 seed 13/29/47을 조합한 paired VISSIM future, H=1/3/5/10/15 오차, lever low/base/high, action ranking, balanced spillback 표본은 아직 없다. 정적 mass conservation은 동역학 정확도를 대신하지 않는다.

### 4. 운영시간 gate 실패

production `pstack-flagship` adapter가 anchor 2100에서 H=3, 131 price rollout을 계산하는 데 `decision_wall_sec=154.746`초가 걸렸다. p95 30초와 hard timeout 45초를 모두 초과한다. 과거 60.6~77초 기록은 현재 소스·상태에 대한 운영 근거로 사용할 수 없다.

## 정량 오차

### 구조와 관측

| 항목 | 현재 증거 | 판정 |
|---|---:|---|
| XML link | 1,219 = regular 448 + connector 771 | 지지 가능 |
| active SC | raw 50 = urban eligible 42 + artificial ramp-meter 8 | 지지 가능 |
| model SC | 41, SC9004 제외·head reference 0 | 지지 가능 |
| legacy partition | 957 owned + 22 freeway + 226 exit = 1,205 | 조건부 |
| assignment tie | downstream 33, upstream 6 | 불가 |
| monitor schedule | 26/26, movement 716 | 조건부 |
| signal readback | 10,448/10,448 일치; immediate 2,432, post-step 8,016 | 지지 가능 |
| event timing 오차 | transition oracle 없음 | 미평가 |

### nominal seed 13 상태 투영

질량식은 `total = represented + exit + unobservable + residual`과 `input = represented + exit + unrepresented`를 모두 검사했다.

| Anchor (s) | VISSIM total | Observed / unobservable | Represented | Exit | Residual | Residual / total | Clipping |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 900 | 2,193 | 2,159 / 34 | 2,010.6 | 136 | 12.4 | 0.565% | 0 |
| 1,500 | 3,365 | 3,304 / 61 | 3,157.9 | 137 | 9.1 | 0.270% | 0 |
| 2,100 | 3,776 | 3,708 / 68 | 3,554.2 | 144 | 9.8 | 0.260% | 0 |
| 2,700 | 4,088 | 4,020 / 68 | 3,841.5 | 171 | 7.5 | 0.183% | 0 |

모든 mass identity는 부동소수점 허용오차 안에서 일치했다. anchor 2100에서는 양의 속도가 관측된 link가 314개, 차량가중 평균속도가 약 47.44 km/h였다. 다만 이 속도는 현재 주로 진단과 freeway 초기화에 쓰이며 urban travel-time delay를 실시간으로 대체하지 않는다.

### 미측정 동적 지표

1-step urban queue/storage 오차, freeway speed MAPE, count MAE, H별 bias·오차 증가율, spillback onset/release, Spearman ranking, top-action pairwise 정확도는 모두 **미평가**다. 과거 gate 결과는 현재 source·mapping·projection의 근거로 재사용하지 않았다.

## A-1~E-15 답변

### A. 구조와 귀속

**A-1. 하류 첫 정지선 규칙은 타당한가? — 조건부.** Approach queue owner를 고르는 규칙으로는 합리적이지만, 교차로 X 내부 차량을 다음 Y approach에 즉시 귀속하면 X의 conflict occupancy와 내부 travel time을 숨길 수 있다. 일반 링크·connector·내부 링크별 stopline 거리와 실제 route를 함께 써야 한다. 현재 tie 33건 때문에 전역 적용은 지지할 수 없다.

**A-2. BFS 비결정성 또는 tie가 있는가? — 불가.** 입력 순서 정렬로 hash 결정성은 확보했지만 하류 33건, 상류 6건의 물리적 tie가 남았다. 정렬된 최소 ID 선택은 재현성 규칙일 뿐 물리 규칙이 아니다. 현재 도구는 이를 fail-closed로 차단한다.

**A-3. exit 226개 제외가 물리에 영향을 주는가? — 조건부.** Player objective에서 제외할 수는 있지만 physical downstream stock, supply, backpressure까지 제거하면 upstream action이 과도하게 유리해진다. exit는 plant 상태에 남기고 objective만 포함/제외 두 버전으로 병렬 보고해야 한다.

### B. 파라미터와 네트워크 구성

**B-4. jam density 140.543은 검증됐는가? — 불가.** 현재 값은 과거 관측 기반 calibration이며 VISSIM 차량길이+정지간격의 geometry prior와 독립 holdout으로 검증되지 않았다. 저수요 추정치 99.1과 비교하면 현재 값은 약 41.8% 높다. calibration과 validation run을 분리해야 한다.

**B-5. `sum(length × lanes) × jam density`가 직렬·병렬을 구분하는가? — 미평가.** partition 중복 0은 lane connectivity의 직렬/병렬 합산이 맞다는 증거가 아니다. 병렬 접근로를 한 storage로 합치면 capacity가 과대 산정될 수 있다. lane graph와 공통 queue-tail 여부로 186개 storage를 재분류해야 한다.

**B-6. adjacency가 물리 route와 맞는가? — 미평가.** 현재 artifact는 adjacency 123쌍, internal 94쌍, internal member reference 199개/unique 146개다. 기존의 `85/94 일치, 9 불일치, 유도-only 29`는 현 코드로 route-level 재검증되지 않았다. single-path 선택도 일부 tie에서 임의적일 수 있다.

### C. 신호와 시간축

**C-7. monitor 26개의 항상-green 문제는 해결됐는가? — 조건부.** `.sig` fixed timing replay 자체는 구현됐고 schedule 26/26, no-green 0이다. 그러나 movement-SG 연결에 lane/turn 정보가 없고 angular/phase fallback과 multi-SG union이 많다. Queue/TTT A/B를 통과하기 전에는 충실도 해결로 판정할 수 없다.

**C-8. controlled 15개의 2-phase overwrite가 안전한가? — 불가.** EB/WB와 NB/SB만으로 SG를 묶으므로 보호좌회전, 비대칭 saturation flow, 보행·혼합 SG를 보존하지 않는다. COM readback 100%는 이 축약의 실행만 증명한다. native `.sig` conflict를 보존하는 action transform이나 SG별 안전한 명시 계획이 필요하다.

**C-9. midblock 9개의 fixed plan/slaving/offset은 검증됐는가? — 미평가.** monitor fixed replay로 항상-green은 제거됐지만, 원래 `.sig`와 corridor travel-time slaving의 A/B, COM offset 부호, 적용 cycle boundary는 검증하지 않았다. offset 제어 실험은 이 gate 이후에만 허용한다.

**C-10. link speed와 부분 step 시간축이 rollout에 반영되는가? — 조건부.** VBS가 link speed, stopped count, queue-tail을 내보내고 `_phase_green_fraction`은 절대 urban step 시작시각과 interval overlap을 사용한다. 그러나 urban 유입 travel-time은 여전히 고정 평균속도 경로가 남아 있고, same-substep zero-delay 방지 및 0.5초 event oracle 비교는 미평가다.

### D. 상태 투영

**D-11. storage fraction 0.35/0.50은 검증됐는가? — 불가.** unmapped link를 storage 1.0으로 보존해 질량 증발은 줄였지만, 0.35/0.50을 training/holdout으로 분리 검증하지 않았다. 낮은 residual은 분할 계수의 동역학적 타당성을 증명하지 않는다.

**D-12. capacity clipping이 질량오차를 숨기는가? — 조건부.** nominal seed 13의 네 anchor에서는 clipping 0이고 두 질량식이 모두 맞았다. 혼잡 수요와 seed 29/47에서 재검사하지 않았으므로 전역 합격은 아니다. 감사기는 설명 없는 clipping을 즉시 실패 처리한다.

**D-13. 기존 projection 96.3%의 나머지 3.7%는 설명됐는가? — 조건부.** 현재 anchor residual은 0.183~0.565%이고, 별도로 unobservable 34/61/68/68대와 exit 136/137/144/171대를 기록했다. 기존 3.7%는 목적함수 포착률, 관측불가 차량, exit, 물리 투영률을 섞은 과거 aggregate라서 현재 기준으로 직접 비교할 수 없다.

### E. Ramp와 freeway

**E-14. 병렬 ramp connector 두 개를 합산해도 되는가? — 미평가.** 독립 origin stream이 같은 modeled ramp와 merge point를 공유한다면 inflow는 합산할 수 있다. 그러나 queue cap은 connector별 queue tail을 유지하거나 실제 공통 queue임을 증명해야 한다. 93.0~145.9 veh cap과 실제 tail의 비교가 아직 없다.

**E-15. freeway 100% capture가 충실도를 뜻하는가? — 불가.** Count reconstruction은 상태 보존과 profiling에는 유용하지만 segment density, speed, travel time, ramp/off-ramp flux의 동역학 정확도를 보장하지 않는다. 각 anchor에서 VISSIM future와 H별 비교가 필요하다.

## 기존 보고의 오류

- connector 수를 770으로 적은 기록은 틀렸다. 원본 XML은 regular 448 + connector 771 = link 1,219다.
- `957/22/226`을 확정된 물리 분할로 표현한 것은 과도했다. 현재 독립 분석은 unresolved tie 33+6건을 찾았고 diagnostic signal-first 결과는 `973/6/226`으로 달라진다.
- monitor fixed schedule을 구현했다는 사실만으로 26개가 완전히 해결됐다고 한 해석은 틀리다. movement-SG fallback과 multi-SG union의 물리 검증이 남았다.
- `10,448/10,448 readback`은 write/persistence 계약의 증거다. protected turn, conflict, offset 부호, event timing 정확도의 증거가 아니다.
- 과거 projection 96.3%와 objective capture 76.8%는 같은 지표가 아니다. 현재는 total/input 질량식, unobservable, exit, residual을 분리 보고해야 한다.
- 과거 60.6~77초 runtime은 현재 기준이 아니다. production H=3 실측은 154.75초다.
- 단일 label 표본에서 spillback F1=1.0을 합격으로 해석한 것은 무효다. positive·negative 각 20개가 없으면 `미평가`다.
- 과거 G6 점수와 TTT 개선률은 현재 assignment·signal·projection으로 다시 paired 실행하기 전에는 plant의 근거가 아니다.

## 권고 순서

### P0. 물리 계약 복구

1. 33 downstream/6 upstream tie를 connector route, static route `relFlow`, stopline 거리로 해소하고 `tie_status=CLEAR` assignment를 생성한다.
2. signal head의 lane/turn을 movement에 직접 연결한다. controlled 15개는 native 보호 현시와 conflict를 보존하는 SG별 action transform으로 바꾼다.
3. expected `.sig` transition oracle를 만들어 immediate/post-step readback과 0.5초 이내로 비교하고 offset 부호·cycle boundary를 검증한다.
4. exit stock과 downstream supply를 plant에 유지하고 boundary objective 포함/제외 결과를 함께 기록한다.

### P1. 관측과 파라미터 검증

1. 실시간 `link_speeds`를 urban travel-time delay에 사용하고 same-substep zero-delay를 단위시험·VISSIM A/B로 제거한다.
2. storage 186개를 lane connectivity로 직렬/병렬 분류하고 jam density, storage fraction, ramp cap을 training/holdout으로 재추정한다.
3. adjacency 123쌍을 실제 connector route로 분류하고 임의 single-path tie를 제거한다.

### P2. 동적 검증

1. 구현된 matrix runner로 demand 0.75/1.0/1.25 × seed 13/29/47의 3,600초 baseline을 순차 실행하고 anchor 900/1500/2100/2700을 고정한다.
2. 각 anchor에서 H=1/3/5/10/15의 VISSIM paired future를 만들고 count, queue, storage, speed, flux, TTT, spillback onset/release를 비교한다.
3. green/VSL/ramp의 low/base/high를 paired 실행하고 offset은 P0 signal gate 후 추가한다. Spearman ≥0.70, top-action pairwise ≥0.80, 반복 부호 반전 0을 요구한다.

### P3. 운영 최적화와 승격

1. price refresh와 phase fraction 계산을 profile하고 동일 production `decide_with_info` H=3의 p95 ≤30초, max ≤45초를 맞춘다.
2. 전체 audit를 새 hash/run ID로 다시 실행한다. nominal·혼잡의 모든 seed가 통과한 뒤에만 P-Stack/G6 성능을 plant 근거로 사용한다.

## 구현된 감사 장치

- state schema v2: link count/speed/stopped/queue tail, 관측불가 차량, run provenance.
- adapter diagnostics: represented/exit/unobservable/residual, clipping, 실제 NumSim module path/hash.
- action CSV two-pass validation: VSL 71, ramp 8, signal 15의 exact inventory와 numeric/header 검증.
- signal trace: `immediate` write/readback과 `post_step` persistence를 별도 기록.
- watchdog: input/code/`.sig` hash, run ID, manifest, `.err`, anchor 보존.
- generator: unresolved assignment fail-closed 및 hash-bound explicit approval.
- matrix runner: VISSIM을 한 번에 하나씩 실행하는 3 demand × 3 seed harness.
- audit CLI: 구조·질량·provenance·runtime·signal gate와 evidence manifest 생성.

## 증거 위치

- 자동 요약: `reports/plant_fidelity_audit_summary.md`
- machine-readable manifest: `reports/plant_fidelity_evidence_manifest.json`
- tie 전체 목록: `reports/link_assignment_ties.json`
- live run evidence: `evaluation/runs/plant_fidelity_audit_final_v10_20260805` (git ignored)
- controlled 2-phase 규칙: `scripts/run_real_world_stackelberg_controller.vbs:1085`
- monitor movement-SG 규칙: `evaluation/controllers/fixed_signal_schedule.py:68`
- projection mass diagnostics: `evaluation/controllers/vissim_stackelberg_adapter.py:992`
- fail-closed generator: `scripts/generate_real_world_distributed_players.py:87`
- sequential matrix runner: `scripts/run_plant_fidelity_matrix.ps1:28`

감사는 세 독립 검토 축으로 수행했다. 질량·provenance, 신호·action 계약, signal trace·anchor 계측을 각각 검토한 뒤 실제 VISSIM run과 회귀시험으로 서로의 결론을 교차 확인했다.
