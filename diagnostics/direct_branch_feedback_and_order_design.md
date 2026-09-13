# 10682 피드백 누락과 F_E 합류·분류 순서: 진단 및 다음 인터페이스

2026-09-10. 생산 파일 미변경. 임의 ratio 0/.5/1 실험, 신규 capacity/κ/φ, two-branch FD, 셀 번호 수정은 시행하지 않았다.

**두 가지 서로 다른 한계가 있다.** 10682의 점유는 W_out으로 합쳐져 독립적인 피드백 상태가 사라진다. 또한 10639→10682의 물리 순서가 대표 셀 집계에서 뒤집힌다. 회계·신호 시간창 정합 수정은 이 두 상태/공간 자유도를 추가하지 않는다. 어느 하나가 빠른 회복 오차의 전부라는 인과 결론은 아직 없다.

## 실제 위치와 실제 계산

| 물리 connector | 동작 | FW_E chain 위치(m) | 실제 셀 | 현재 모델 셀 |
|---|---|---:|---:|---:|
| 10643 | 신호쪽 분류 | 4386.333040 | 8 | OR_F_E:8 |
| 10639 | 합류, 1차로 | 4610.818592 | 8 | R_F_E:9 |
| 10682 | 직행 분류, 1차로 | 4746.884465 | 9 | OR_F_E:8 |
| 10681 | 합류, 2차로 | 4899.955753 | 9 | R_F_E:9 |

근거는 원본 Ver2 INPX endpoint와 실제 `control_mapping_ver2n21.json`의 chain offset/bounds다. E8=[4108.201,4621.726), E9=[4621.726,5135.252). scalar 모델 경계와 약0.76m 차이가 있지만 위 셀 판정은 동일하다. 10639→10682 간격은 **136.065873m**다. 둘 모두 mainline link2의 첫 차로에 붙는다.

현재는 두 OR_F_E 분류를 E8에서 먼저 빼고, 두 R_F_E 합류를 E9에 나중에 더한다. `generate_real_world_control_mapping.py:545`의 merge 대표는 관측유량 가중이고 `:584`의 off-ramp 대표는 동일 가중/상류 tie-break이다. mapping은 `segment_straddle` 근사를 명시한다. 같은 VSL zone이라는 이유는 같은 합류·분류 순서라는 근거가 아니다.

`direct_branch_order_audit.json`의 실제 final635/SC2001/shared69 fixture, 기존 action/current-rate forecast, global endpoint trace:

| 초기 시각 | 첫10초 R_F_E actual release(vph) | E8 ramp input | E9 ramp input | 초기 branch 재고 |
|---:|---:|---:|---:|---|
|1200|1080.000|0|1080.000|10639=2, 10681=1 → group3|
|3300|587.868329|0|587.868329|10639=7, 10681=0 → group7|

두 시각 각각15개10초 substep 전체에서 E8=0/E9=전량을 확인했고, 실제 accepted-flow 회계 mass closure도 PASS했다. 즉 차량 총량이 보존되어도 주입 위치·순서가 정확하다는 뜻은 아니다. 이 vph는 **모델의 실제 queue 출발 receipt**를 T_f로 환산한 값이며 VISSIM 실측 처리량이 아니다.

## 10682 관측은 있으나 현재 dynamic branch 상태는 없다

| 초기 시각 | 10682 재차/정지 | 가장 상류 정지차 위치 | 평균 속도(km/h) | 모델 투영 |
|---:|---:|---:|---:|---|
|1200|20/3|93.941m|11.81|W_out에20; 121의11도 같은 W_out|
|3300|21/8|21.968m|8.67|W_out에21; 121의17도 같은 W_out|
|4050|28/16|3.751m|3.41|동일 집계 구조|
|5250|36/29|2.755m|1.08|동일 집계 구조|

정지는 기존 capture threshold1km/h를 사용했다. 길이226.524m×1차로와 기존 평균 차두공간6m에서37.754veh라는 기하 참조는 계산되지만, 이를 신규 식별된 저장용량이나 lane-feedback capacity로 설치하지 않았다. upstreammost stopped 위치는 queue envelope이지 연속 정지대가 입구까지 찼다는 증명이 아니다. 특히1200초에는 정지차가 입구에서93.94m 떨어져 있으므로 초기 E8 붕괴를 직접 spillback 탓으로 확정할 수 없다.

`offramp_feedback_trace.json`에서 OR_F_E의 λ는10643 전용 `OR_F_E_storage`(초기1veh/cap106.33)만 읽는다. direct10682는 `SC1004_W_out` cap220으로121 등과 섞이며 `landing_storage_spec={}`다. `metanet.effective_lane_profile:189`와 local `_local_lane_profile:101` 모두 off-ramp의 signal storage만 소비한다. `LocalLandingState.occupancy:133`도 signal storage+그 origin의 point queue만 반환한다.

따라서 10682 count를10643 capacity106.33 또는 큰 W_out220으로 나누어 넣으면 다른 물리 support를 혼합한다. tail extent/length로 바꾸는 것도 기존 occ/cap의 관측 정의를 바꾸는 것이므로 순수 배선 수정이 아니다. 미래에 direct 피드백이 생겨도 실제10682의 E9에 적용해야 한다. E8 λ를 강제로 낮추는 보상은 하지 않는다.

## 4개 group 제어를 유지하면서 필요한 최소 인터페이스

| 단계 | 현재 확보한 정보/접점 | 추가로 보존할 정보 |
|---|---|---|
|초기 ramp projection|physical assignment가10639/10681를 각각 관측한 뒤 `ramp:R_F_E`로 합산|`ramp_branch_queue[connector]`, 합이 기존 group queue. TTT/Ω에서 group과 branch를 중복 계상하지 않음|
|urban→ramp 입고|`urban_flow_accounting.py:324`의 movement별 actual; `:574`의 `(W_out,ramp,allowed)` receipt가 합산 전에 존재|movement/physical route→connector join. SC1004_W_to_onE는10639, W_out의R_F_E 분기는10681. 미래 transit buffer도 같은 branch label 유지|
|meter 출고|`:287`에서 group `before/requested/actual`로 꺼낸 뒤 group receipt만 기록; `coupling._actual_ramp_release_flows:117`가 T_f 합산|`accepted_ramp_receipt(connector,group,from_stock,merge_cell,vehicles,t0,t1)`. 요청/command rate가 아니라 branch queue에서 실제 빠진 수. Σbranch=group actual|
|FW 합류|`area_freeway_accounting.py:71`, local model `ramp_merge_idx`에 group당 한 cell|branch receipt를 실제cell에 합산 주입. 동일 receipt로 receiving 공간 예약·continuity·Ω handoff를 갱신. 단순 density나 index만 이동하지 않음|
|FW 분류|cell8 `normal_off_total/effective_off_total` 하나를 계산하고 `schedule_offramp_arrivals_accounted:627`에서 signal/direct로 나눔|branch별 desired/accepted receipt를 자기cell에서 생성. mainline sending의 off 비율과 q_inter도 같은 branch 위치를 소비해야 함|
|direct 저류/피드백|10682와121이 같은 W_out으로 투영되어 후속 재차 분해 불가|`direct_branch_occupancy[10682]`와 connector→121 transfer/queue 위치 또는 명시적인 이동시간 상태. W_out 차량을 비율로 나눠 connector 재차라고 부르지 않음|

최종 branch meter receipt는 현재 group queue에서 이미 정보가 지워져 복원할 수 없다. 예를 들어 Q10639=7/Q10681=0인 상태와 반대 상태가 group Q=7로 같아지지만, 실제 merge cell과 physical meter pulse는 다르다. 이전 창의 실측 통과 비율로 나누는 것은 외생 persistence 가정이지 후보별 반사실적 accepted flow의 복원이 아니다.

4개 group command는 유지할 수 있다. 다만 모델과 writer가 같은 명시적인 physical branch command 배분 계약을 사용해야 한다. branch별 queue, 실제 physical green pulse, 기존 physical command capacity를 소비해 각 actual receipt를 계산한 뒤 합쳐야 한다. 현재 `_measured_meter_allocation` diagnostics cache를 읽어 group 출고를 뒤늦게 쪼개는 방식은 피한다. 신규 branch storage capacity가 필요한 단계에서는 기존 canonical 값의 존재를 먼저 확인하고, 없으면 식별 과제로 남긴다.

분류는 더 큰 구조 변경이다. 기존 β_OR=0.2 및 direct share0.484를 서로 다른 cell의 전체 q에 그대로 각각 곱하면 upstream 분류 후 남은 차량과 중간10639 합류 차량의 route eligibility를 혼합한다. 단순히 `(1-share)*old_actual`, `share*old_actual`을 다른 cell에서 빼도 cell8의 mainline sending이 이미 전체off몫을 뺀 상태라 continuity가 틀어진다. route 의도 cohort 또는 명시적으로 정당화한 conditional branch-demand 모델이 필요하다. aggregate desired flow를 사후 위치만 옮겨서는 해결되지 않는다.

## 후속 회귀 경계

branch 상태 도입 때는 같은 group total·다른 branch 분해가 서로 다른 정확한 cell receipt를 만드는지, Σbranch=group과 후보 copy 격리, queue0인 branch 출고0, physical pulse 및 receiving 한계, global/local 같은 receipt, SG/FD 계수 불변, Ω 중복계상0을 확인한다. 나중에 feedback 정의가 검증되면 별도 flag로 branch 점유→기존 λ식 경로만 추가한다. 그 전에는 양수 ratio/새capacity를 강제로 넣지 않는다.

이번에 완료한 것은 관측·geometry·실제 실행 frame 추적과 설계 경계 확정이다. 새로운 branch 동역학이나 제어 성능 승격은 아니다.

재현: `python diagnostics/probe_direct_branch_order.py` → JSON/CSV 및 두 실제150초 endpoint trace. 입력 network/mapping SHA와 전체 관측표는 `direct_branch_order_audit.json`, 원본 피드백 trace는 `offramp_feedback_trace.json`에 있다.
