# Plant 충실도 감사 요청 (Codex)

작성 2026-08-05. 대상 리뷰어: Codex.

## 0. 왜 지금 이걸 요청하는가

우리는 MPC 기반 Stackelberg 신호제어기를 PTV Vissim 2020 플랜트에 얹으려 한다.
그런데 **G6 채점도 캘리브레이션도 그 아래 깔린 "모델이 VISSIM 네트워크를 얼마나 정확히
모사하는가"가 성립해야 의미가 있다.** rollout 이 틀린 네트워크 위에서 돌면 lever 를 아무리
움직여도 해석이 불가능하다.

지난 며칠간 모델(이하 plant 모사층)을 여러 번 고쳤고, 그때마다 **우리가 이전에 옳다고
보고했던 진단이 뒤집혔다.** 그래서 자체 검증만으로는 신뢰가 부족하다.

**요청: 아래 구현이 실제 VISSIM 네트워크를 얼마나 정확히 모사하는지 독립 감사해 달라.**
개선 제안보다 **반증**을 우선한다. "이 수치는 이런 이유로 틀렸다"가 가장 가치 있다.

---

## 1. 시스템 구조

```
PTV Vissim 2020 (SP14)              ← 진짜 플랜트
   └ network/real_world_gaepo_modi/modi_eval_rw_control.inpx
        ↕ COM
   scripts/run_real_world_stackelberg_controller.vbs      ← 관측 수집 + 신호 기입
        ↕ state JSON / action JSON
   evaluation/controllers/vissim_stackelberg_adapter.py   ← 관측 → 모델 상태 투영
        ↕
   ../NumSim-mine/src/                                    ← 모델(rollout) + 컨트롤러
```

레포 두 개다.
- `VISSIM/` — 하네스, 네트워크, 스크립트, 설정, 어댑터
- `NumSim-mine/` — 교통 모델(`src/models/`), 컨트롤러(`src/controllers/`)

핵심 진입점.
- 관측: `run_real_world_stackelberg_controller.vbs` 의 `ReadVehicleLanePosSpeed`(2172행)가
  `Vissim.Net.Vehicles.GetMultiAttValues("Lane"/"Pos"/"Speed")` 로 **전 차량**을 읽는다.
- 투영: `vissim_stackelberg_adapter.py:540~` 이 `link_counts` 를 모델 저류/movement 큐로 나눈다.
- 모델: `NumSim-mine/src/models/grid_topology.py` 가 leg 인접에서 movement 와 내부 링크를 유도,
  `src/models/urban_queue_model.py` 가 substep 동역학을 돈다.

---

## 2. 현재 네트워크와 모델의 규모

| | VISSIM 실측 | 모델 |
|---|---:|---:|
| 링크 | 1,219 (일반 448 + 커넥터 770) | — |
| 신호제어기 | 50개 (active 42) | 41노드 (통제 15 + 모니터 26) |
| 도시부 링크(분할 대상) | 1,205 | — |
| movement | — | 1,422 |
| 링크 저류 | — | 302 |

`active 42` 중 모델 41 — 빠진 것은 `SC9004` 하나이고 신호두 0개·링크 0개·좌표 없는
빈 중복 레코드다(이름이 SC109 와 같다).

---

## 3. 지금까지 한 작업 (전부 2026-08-04 ~ 08-05)

각 항목은 **왜 했는지 → 무엇을 바꿨는지 → 측정 결과** 순이다.
감사 시 "그 근거가 실제로 성립하는가"를 봐 달라.

### 3.1 링크를 플레이어에 **분할** 귀속 (`scripts/assign_links_to_players.py`)

규칙(사용자 확정): **한 링크는 정확히 한 플레이어에만 귀속되고, 빠지는 링크는 없다.**
귀속 기준은 "하류로 훑어 처음 만나는 것"이다.

| 처음 만나는 것 | 귀속 |
|---|---|
| 신호 정지선 | 그 플레이어의 approach queue |
| 고속도로 링크 | freeway follower |
| 아무것도 없음(종단) | 출구 — 모니터링만, 플레이어 귀속 없음 |

결과: 1,205 = 귀속 957 + freeway 22 + 출구 226. 중복 0, 누락 0.

**커넥터를 포함한다.** VBS 가 `RW_CLASSIFY_UNMATCHED_AS_URBAN=True` 로 커넥터 위 차량도
`urban_vehicles` 분모에 넣기 때문이다. 제외하면 분모에는 있고 분자에는 없는 항목이 생긴다
(실측 426개 커넥터에 359대 = 도시부의 8.7%).

함정 하나 — `downstream` 그래프를 `from-link -> to-link` 로 만들면 커넥터에 진입 간선이
없어 BFS 가 즉시 끊긴다(그 상태로 836개가 전부 '출구'로 분류됐다). 커넥터를 **노드로**
넣어야 한다.

### 3.2 상류 SC 유도 (같은 파일, `link_upstream`)

모델의 방향성 저류 `SCa_to_SCb` 를 만들려면 상류 a 가 필요하다.
처음엔 leg 방위로 인접표와 조인했는데 **성공률 126쌍 중 79쌍(63%)** 이었다.
원인: 인접표는 교차로-교차로 벡터로, 배정은 링크 기하로 방위를 **따로** 계산한다.
굽거나 편심인 접근로에서 어긋난다.

수정: owner 를 구한 **같은 커넥터 그래프를 뒤집어** 상류를 직접 찾는다. 방위를 경유하지 않는다.
결과 714/957 확정(나머지는 유입 경계).

### 3.3 저류 용량·길이 실측 유도 (`scripts/derive_urban_storage_capacity.py`)

기존엔 상수였다(경계 220, 내부 220, 램프큐 180, 오프램프 120).
jam density 를 정체 표본(속도<3kph, 정지차 절반 이상)의 p90 으로 역산 = **140.5 veh/km/lane**
(표본 177개, 중앙 48.9 / p75 104.1 / 최대 186.7).

`capacity = Σ(길이_km × 차로수) × jam_density`, 링크 분할이 중복 없으므로 합산에 중복 없음.
결과: 저류 182개(내부 114 + 경계 68), 총 길이 82.7 km.
인접표의 내부 pair 94개와 **독립 대조: 85개 일치(90%)**.

### 3.4 8방위 확장과 `NS_AXIS` 정정 (`NumSim-mine/src/models/grid_topology.py`)

실제 도로망이 격자가 아니라 한 방위에 이웃이 둘 이상 붙는다. 4방위로는 116쌍 중 95쌍만
표현됐다. 8방위 + `방위_이웃` 복합 키(`N_SC1002`)로 **116/116 = 100%** 보존.

그 과정에서 `NS_AXIS = {"N","S","NE","SW"}` 로 넣었는데 **부호가 반대였다.**
개포동 격자가 좌표축에서 15~37° 돌아가 있어 실측 축각이 NE 35.3° / SW 38.0°(동서축),
NW 122.0° / SE 121.5°(남북축)다. 코드 자신의 기준([45,135)=남북축)을 실제 방위각에 적용하면
**현행이 맞는 대각 leg 0개, 뒤집으면 76개.**

`{"N","S","NW","SE"}` 로 고쳤고 movement 287개(20.4%)가 phase 를 옮겼다.
검증은 `scripts/verify_phase_axis_assignment.py` 로 남겼다(현재 123/123 = 100% PASS,
되돌리면 34.5% FAIL).

### 3.5 관측 링크 → 모델 저류 **권위 라우팅** (`scripts/generate_real_world_distributed_players.py`)

기존엔 소유 링크마다 `{sid}_{leg}_out` 을 **N/S/E/W 네 개 전부** 박았다(기하 무관 살포,
전부 경계 sink). 실측: 경계 sink 로 가는 관측 링크 66개 중 65개가 배정 링크였고,
그중 53개는 모델에 내부 링크가 멀쩡히 있는데도 샜다.
SC15/SC107/SC9002/SC2 → SC1 네 접근로가 전부 `SC1_N_out` 하나로 접혔다(복합 키가 맨 방위로 접힘).

리더는 경계 leg 를 **설계대로** 목적함수에서 뺀다(`NumSim-mine/src/controllers/leader.py`
`_state_accumulation_base`). 그래서 제어 가능한 approach queue 651대가 목적함수 밖으로 나갔다.

수정: `SC{상류}_to_SC{owner}`, 상류가 없으면 `SC{owner}_{leg}_out`. 957개 전부 라우팅, 탈락 0.

### 3.6 어댑터 투영의 큐분 증발 (`vissim_stackelberg_adapter.py:540~`)

투영은 링크 대수를 저류분/큐분으로 쪼개고 큐분을 `link_to_movements` 로 배분한다.
매핑이 없는 링크는 그 루프를 **아예 안 돈다.** 실측: 관측된 배정 링크 952개 중
**882개가 매핑 없음, 1,415대**의 큐분이 사라졌다.
그 882개는 신호두 링크가 아니라 링크 본체라 물리적으로도 저류가 맞다 →
매핑이 없으면 `storage_fraction = 1.0`.

### 3.7 고속도로 본선이 도시부 저류로 유입

`internal_link_members` 는 커넥터 **경로 기반**이라 SC 사이 경로가 고속도로를 타면 본선
링크까지 멤버로 넣는다(`SC1001_to_SC1004` 멤버 = 2, 26, 31, 70 — 2·26이 고속도로).
3.6 을 고치자 링크 2(178대)·26(510대)의 688대가 도시부 저류로 쏟아져 포착률이
**114.6%** 로 100%를 넘었다. 도시부 분할 밖 링크의 origin 을 제거해 해결.
**100% 초과가 아니었으면 못 잡았을 결함이다.**

### 3.8 전 링크 관측

`RW_LOCAL_OBSERVABLE_LINKS` 는 허용목록이고 그 목록이 생성물이다. 예전엔 175개였다.
지금은 1,207개라 도시부 링크 전부가 나온다. VBS 코드 변경은 불필요했다.

### 3.9 램프 큐 상한을 램프별로 (`scripts/derive_ramp_queue_capacity.py` + 모델 5파일)

사용자가 램프미터 신호두를 램프 **시작 → 끝**(길이의 98~99%)으로 옮겨, 큐가 커넥터 전체에
쌓이게 됐다. 커넥터 기하에서 유도하면 93.0~145.9 인데 모델은 스칼라 180 이었다.

이 스칼라는 리더 압력항만이 아니라 **팔로워의 큐 상한 = 물리 자체**를 지배한다
(`f1_wu_faithful_follower:517`, `freeway_follower:432`). 리더만 고치면 리더는 93에서
꽉 찼다고 보는데 팔로워는 180까지 채우는 불일치가 난다.

`NetworkConfig.ramp_queue_max_veh_by_ramp` + `ramp_queue_cap(ramp)` 헬퍼를 만들고
ramp 키가 스코프에 있는 곳 14군데를 바꿨다. **매핑이 비면 스칼라 폴백이라 기존 비트 동일.**

---

## 4. 현재 측정치 (state_002700, `evaluation/runs/capture_n41_20260805/`)

플랜트 실측 urban 2,657 / freeway 980 / ramp 56. `link_counts` 1,207개 링크, 합 3,623.
분모 = urban − 출구 168 = **2,489**(귀속 기준. 출구는 사용자 결정으로 플레이어 귀속 없음).

| 지표 | 값 |
|---|---:|
| 도시부 포착률 (목적함수 기준) | **76.8 %** |
| 도시부 포착률 (투영 기준, 경계 포함) | **96.3 %** |
| 고속도로 포착률 | **100.0 %** |

포착률 경과: 20.2 → 40.4 → 50.7 → 83.5 → 76.8 %.
마지막 하락은 퇴행이 아니라 사용자가 신호 5개(SC2001~2005)를 새로 넣어 네트워크가 바뀐 것이다.

고속도로 100%는 세그먼트 `count → density → count` 왕복이라, **100%에서 벗어나면 관측
누락이 아니라 길이·차로 프로파일 불일치**를 뜻한다. 도시부와 의미가 다르다.

---

## 5. 감사해 달라는 것

### A. 분할과 귀속이 물리적으로 옳은가

1. "하류 첫 정지선이 소유자" 규칙이 **교차로 내부 커넥터**에 적용될 때, 차가 물리적으로
   교차로 X 안에 있는데 다음 교차로 Y 의 approach 로 세는 것이 타당한가.
   (사용자는 타당하다고 판단했다. 반증 근거가 있으면 제시해 달라.)
2. BFS 가 비결정적일 여지가 있는가. `downstream` 이 `set` 이라 순회 순서가 실행마다 다를 수
   있다. 같은 홉 수에 정지선이 둘이면 소유자가 흔들리는가. 흔들린다면 얼마나.
3. 출구 226개(도시부 차량의 5.1%)를 어느 플레이어에도 귀속하지 않는 것이 목적함수에
   편향을 만드는가.

### B. 저류 용량 유도가 타당한가

4. jam density 140.5 veh/km/lane 이 개포동 실측으로 타당한가.
   정체 표본 정의(속도<3kph & 정지차≥50%)의 p90 이 적절한가. 표본이 177개다.
   **주의: 이 값은 관측 런의 혼잡도에 따라 흔들린다** — 저수요 런에서는 99.1 이 나왔다.
   물리 상수여야 하는 값이 관측 의존적인 것이 문제인가, 아니면 이 정도는 허용인가.
5. `capacity = Σ(길이 × 차로) × jam` 이 **직렬 가정**이다. 한 (SC, leg) 에 여러 링크가
   병렬로 붙으면 과대평가된다. 실제로 병렬인 경우가 얼마나 되는가.
6. 인접표 94쌍 대비 85개 일치(90%)에서 **불일치 9개 + 유도에만 29개**의 정체는 무엇인가.

### C. 모델 동역학이 VISSIM 을 모사하는가

7. **가장 중요.** 모니터 전용 26개 SC 의 movement 는 `phase=''` 이고,
   `urban_queue_model.py:541` `_phase_green_fraction` 이 phase 가 비면 **1.0(항상 녹색)** 을
   돌려준다. 즉 **모델의 26개 교차로는 절대 빨간불이 없다.** 실측으로 movement 1,422개 중
   672개(47.8%), 관측 차량의 40.7%가 여기 걸린다.
   - 이게 얼마나 큰 오차인가. 정량화할 방법이 있는가.
   - 최종 목표가 "통제 교차로 TTT 절감 vs 인접 비통제 TTT 증가" 비교인데, 인접이 빨간불이
     없으면 증가분이 원리적으로 안 잡힌다. 맞는가.
   - 고치는 방향: 비통제 노드에 플랜트의 fixed-time 시간표(phase + 고정 녹색 + offset)를
     심되 리더가 못 바꾸게. 이 설계에 결함이 있는가.
8. 2-phase(NS/EW) 가정이 VISSIM 의 실제 신호그룹 구성과 얼마나 어긋나는가.
   참고: VBS `SignalStateForGroup`(893~907행)이 EB*/WB* 를 전부 major, NB*/SB* 를 전부 minor 로
   보내 **런타임에 2그룹으로 덮는다.** 즉 모델의 2-phase 는 플랜트에 실제 적용되는 제어를
   반영한 것이다. 그럼에도 남는 비대칭은 무엇인가.
   (플랜트 .inpx 에 conflictArea 가 1,819개인데 모델에는 상충 표현이 0이다.)
9. 미드블록/보행 신호 9개는 배정 leg 가 한 축뿐이라 2-phase 중 한쪽에 차량 movement 가 0이다.
   현재 처리(비통제, 항상 녹색)가 만드는 오차의 크기는?
10. 도시부 이동시간이 링크 길이 기반 지연 스텝으로 계산되는데, 실시간 속도가 아직 관측에
    올라오지 않는다(VBS 에 `linkSpeedSums` 는 있으나 `link_speeds` 로 내보내지 않음).
    이게 rollout 정확도에 얼마나 영향을 주는가.

### D. 관측 → 투영 경로

11. `storage_fraction` 분할(저류분 vs 큐분)의 캘리브레이션 근거가 무엇인지 추적해 달라.
    `_link_storage_split_fraction` 과 `_observation_split_parameters` 를 봐야 한다.
    3.6 에서 "매핑 없으면 1.0" 으로 바꾼 것이 이 캘리브레이션과 충돌하는가.
12. `min(capacity, current + share)` 절단(어댑터 566~570행)이 현재 상태에서 실제로 발동하는가.
    직전 측정에서는 포화 저류 0개였으나 고수요에서는 다를 수 있다.
13. 투영 기준 96.3% 에서 나머지 3.7% 는 어디로 새는가.

### E. 램프·고속도로 결합

14. 램프 커넥터 2개가 모델 램프 1개에 붙는데 실측 **병렬**로 판정했다(각각 다른 도시부
    링크에서 진입). 합산이 옳은가.
15. 고속도로 포착률 100%가 왕복 항등이라 무의미한 지표인가, 아니면 프로파일 정합을
    검증하는 유효한 지표인가.

---

## 6. 알려진 미해결 (다시 발견하는 데 시간 쓰지 말 것)

| # | 항목 | 상태 |
|---|---|---|
| 1 | 모니터 26 SC 가 항상 녹색 (phase='') | **미해결. 5-C-7 참조** |
| 2 | `boundary_in` 큐 122.7대가 목적함수 밖 | 설계 판단 대기 |
| 3 | H=1 지평 퇴행 — rho 0.4378, pairwise **0.000** (H=5/10/15는 0.985/0.921/0.862) | 미해결. MPC 는 첫 구간만 집행하므로 폐루프를 좌우 |
| 4 | solve 시간 60.6~77s > 제어주기 60s. 프로파일상 **77%가 가격 갱신**(전역 롤아웃 83회), 리더 탐색은 19% | 미해결 |
| 5 | G6 게이트 FAIL — `top_action_pairwise` 0.75 < 0.80 | 미해결 |
| 6 | spillback F1 = 1.000 은 인공물 (TP=72, TN=FP=FN=0 상수 라벨) | 미해결 |
| 7 | 유령 저류 29개(구 6노드 격자 잔존) | 참조 0개로 무해 확인 |
| 8 | 기존 테스트 실패 15개 (`test_forecast_awareness` 5, `test_constraints` 4 등) | 이번 작업과 무관함을 되돌리기로 확인 |
| 9 | 테스트 스위트가 55분 timeout 에도 85%에서 안 끝남 | 미해결 |
| 10 | `_phase_green_fraction` 612만 회 호출 (메모이제이션 여지) | 미적용 |

---

## 7. 검증에 쓸 수 있는 도구

이미 만들어 둔 것.

```bash
# 분할 (중복/누락 검사 포함)
python scripts/assign_links_to_players.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx

# 인접 (복합 키 보존율 리포트)
python scripts/derive_intersection_adjacency.py --network <inpx> --json-out <out>

# 저류 용량 (jam density 역산 + 인접표 대조)
python scripts/derive_urban_storage_capacity.py --links-csv <bottleneck_links.csv> --json-out <out>

# 램프 큐 용량
python scripts/derive_ramp_queue_capacity.py --capacity-json <out>

# phase 축 배정 검증 (실측 방위각 대조)
python scripts/verify_phase_axis_assignment.py --adjacency <out>

# 포착률 + 고속도로 포착률
python scripts/verify_urban_topology_merge.py --state-json <state.json> \
    --link-assignment-json outputs/link_player_assignment_20260805.json --case "<label>:<tuning>:<mapping>:<detector>"
```

플랜트 런(VISSIM 필요, **동시에 하나만** — 워치독이 모든 VISSIM200/cscript 를 죽인다):
```bash
powershell -File scripts/run_real_world_single_watchdog_distributed_core15n41.ps1 \
    -Name <run> -Controller diagnostic-fixed57 -Seed 13 -SimPeriod 3000 -StateLogIntervalSec 300 -OutDir <dir>
```

**런이 이상하면 `network/real_world_gaepo_modi/modi_eval_rw_control.err` 를 먼저 읽어라.**
오늘 한 번, 정적 경로 하나가 끊겨(`Static Vehicle Route 1157 - 3 is not complete`) VISSIM 이
시뮬을 시작 직후 중단·리셋했다. 증상은 `actual_sim_sec=0` 고정 + `FAILED_SET_SIGSTATE` 28,056건인데
**그 신호 오류들은 원인이 아니라 결과였다.**

---

## 8. 우리가 자주 틀린 방식 (같은 함정을 피하도록)

이번 작업에서 실제로 저지른 오류들이다.

1. **방향을 뒤집어 재기.** `SC1001_to_SC1004` 를 "물리 8,896대 vs 모델 120대"라고 보고했는데,
   8,896은 반대 방향 회랑이었다. 실제 접근로는 421 m, 143.5대로 모델과 거의 같았다.
2. **증상을 원인으로 보고.** 신호 COM 실패 28,056건을 원인으로 의심했으나 시뮬이 안 도는
   것의 결과였다.
3. **에이전트/도구 진단을 확인 없이 전달.** "유령링크가 spillback F1 의 원인"이라는 진단을
   검증 없이 옮겼다가, 이미 적용돼 있고 효과가 없었음이 드러났다.
4. **정상 결과처럼 보이는 조인 실패.** "인접 없는 방위 47개"라고 보고한 것이 실은 63% 조인
   실패의 증상이었다.
5. **잘못된 입력 파일.** glob 으로 네트워크를 잡다가 엉뚱한 `.inpx` 를 파싱해 "커넥터 8.7%"
   결론이 뒤집혔다.

**그래서 수치를 인용할 때는 어느 파일·어느 런·어느 함수에서 나왔는지 같이 적어 달라.**

---

## 9. 산출 형식

`reports/plant_fidelity_audit.md` 에 아래 구조로.

```md
# Plant 충실도 감사

## 판정
플랜트 모사가 rollout/lever 실험을 지지할 만한가: 지지 가능 / 조건부 / 불가

## 치명 결함
(모사 자체가 틀린 것. 파일:행 + 재현 명령 + 정량 근거)

## 정량 오차
(모사는 맞으나 오차가 큰 것. 크기를 수치로)

## 5장 질문별 답변
A-1 ~ E-15

## 우리 보고가 틀린 부분
(3장·4장 서술 중 사실과 다른 것)

## 권고 순서
(무엇부터 고쳐야 rollout 이 신뢰 가능해지는가)
```

**모든 발견은 파일·행·명령·산출물을 인용한다. 구두 주장은 근거로 인정하지 않는다.**
