# SDMPC 결정 시간 — 마지막 squeeze (2026-09-23)

## 결과

| 수정 | 파일 | 결정당 | 결정 영향 | 검증 |
|---|---|---|---|---|
| 중앙 Jacobian 가지치기 | `sdmpc_tangent_constraints.py` | 36~46 s | 중립 | 실제 테이프 2개 비트동일, NaN 대체경로 포함 |
| Dual 연산자 융합 | `sdmpc_tangent_summary.py` | 36~42 s | 중립 | 실제 롤아웃 1회 양팔, 테이프 20항목 비트동일 |
| Jacobian 깊은 복사 제거 | `sdmpc_tangent_surrogate.py` | ~2.6 s | 중립 | 소비자 전부 읽기 전용 |

**통합 검증**: 저장된 900 s 상태로 결정을 오프라인 재현해 이전 재현과 비교
(`tools/diff_decisions.py`). 명령 7종(`N_P_star`, `N_UF_star`, `ramp_metering`, `vsl`,
`green_times`, `offsets`, `inflow_outflow_allocation`) **바이트 동일**. 차이 44개는 전부
출처 토큰(바꾼 파일 3개의 sha256 과 그것을 담는 `request_sha256`·`frozen_context_token`·
`response_token`) 42개와 출력 경로 2개. 수치 차이 0.

**결정 시간**: native 900 s 결정 600.5 s → 504.7 s (−95.8 s, −16%). 비교 기준을 native
런으로 잡은 이유: 이전 오프라인 재현(730.2 s)은 워크플로 에이전트가 동시에 돌던 부하
상태라 −31% 는 과장이다.

## 1. 중앙 Jacobian 가지치기

배포 코드는 231개 축마다 테이프 전체(14,138,815 노드)를 훑었다. 세 겹의 정확한 축소:

1. **조상 압축** — 출력의 조상 노드만(4,387,387개, 31%). 부모가 자식보다 앞서므로 조상
   집합은 부모에 대해 닫혀 있고, 같은 순서로 같은 부동소수점 연산을 한다.
2. **죽은 축** — 시드가 조상에 없는 축 33개는 출력이 전부 +0.0 (`x += -0.0` 은 +0.0).
3. **첫 사용** — 축의 첫 시드 노드 이전은 전부 정확히 0.0.

2와 3은 둘 다 `0*w == 0` 에 기대는데 **`0*inf` 는 NaN** 이다. 그래서 압축된 가중치에
비유한 값이 하나라도 있으면 **죽은 축을 포함한 모든 축을 노드 1부터** 압축 테이프 위에서
돌린다. 처음 구현은 살아있는 축만 되돌렸고, 가중치 하나에 inf 를 심는 테스트가
불일치(NaN 셀 46,662개)를 잡았다. 수정 후 NaN 패턴까지 일치.

`tools/verify_central_prune.py`: 두 테이프에서 저장된 배포 행렬과·새 전체 스윕과 모두
`array_equal` 이면서 원시 바이트까지 동일. 12.0 s → 3.1 s (8 워커, 안정 상태).
`method` 문자열은 `forward_columns_on_existing_reverse_tape` 유지
(`test_sdmpc_central.py:78`). 새 영수증 필드 `forward_pruning`.

## 2. Dual 연산자 융합

테이프 롤아웃 1회에 Dual 연산 ~2,600만 개. 각각이 Dual 메서드 → `primal()` →
`trace.operation` 조회 → `checked_operation` 의 isinstance 두 번을 거쳤다. reverse Dual,
float, int 피연산자에 대해 `checked_operation` 본문을 `a=self` 로 고정해 직접 실행한다.
다른 타입은 원래 메서드로 넘어간다.

대조 방법: 시제품을 믿지 않고 **런타임에 실제로 붙는 메서드**(역방향 Dual 이 전부
재정의하므로 순방향의 `return self` 지름길은 적용되지 않음)와 한 줄씩 대조. 부모 순서,
가중치 식(`d**2` 까지), 상수 피연산자 가중치를 w2 에 기록하는 것, 비교 연산의
`branch(self, other)` 호출이 모두 일치. `Trace.operation` 을 바꾸는 곳은 원본과
`checked_operation` 둘뿐이고 Dual 산술을 패치하는 코드는 없다(우회할 가로채기 없음).

설치는 `checked_operation` 과 같은 파일, 같은 `install()` 안에서만. 기존 가드
(`Stream summary already installed`)로 프로세스당 1회.

`tools/verify_fused.py`: 병합 트리의 실제 요청으로 양팔을 새 프로세스에서 동시에
(`PYTHONHASHSEED=0`) — 테이프 배열 7개 sha256, 카운터, support, 비용, 자원, Jacobian 3종,
응답 토큰, tie/discrete 축, 이벤트 수, 연산 수 **20항목 전부 동일**.
`tangent_sec` 103.71 → 92.64 s (−10.7%).

## 3. 깊은 복사 제거

`SurrogateQuery.derivative` 가 5169×231 리스트를 매번 deepcopy 했다(~0.45 s × 6회). 유일한
소비자 `sdmpc_central.recover` 는 `rows.extend(...)` 직후 `np.asarray(rows)` 로 새 배열에
복사하고 그 뒤 `C` 만 쓴다. memo 로 공유.

## 하지 않은 것과 이유

**결정 중립이지만 이번엔 안 함** (합계 20~25 s, 9000 s 런에서 18~22분): 사전 기동 워커,
스칼라 예측 AST 계측 생략, 중앙 Jacobian 2단계. 셋 다 프로세스 수명·격리·실패 의미론을
건드려 구현·검증에 몇 시간 — 이번 런에선 늦어지는 시간이 아끼는 시간보다 크다.

**결정을 바꿈 — 사용자가 "중립만" 선택**:

| 선택지 | 결정당 | 비용 |
|---|---|---|
| `sdmpc.max_iterations` 2→1 | 116~121 s | 예측 +0.485 veh·h (SDMPC 이득의 30%) |
| mlc=1 일 때 중앙 Jacobian·복원 생략 | 14~21 s | 행동 불변, `central_multiplier` 영수증 소실 |
| 읽기 전용 검사 14개 untape | ~40 s | 행동 불변, `primal_comparisons` −14%, `exact_primal_ties` −54% |
| `central-reuse-v2` 복귀 | 233~255 s | +2.436 veh·h, 09-22 합의 번복 |

**기각**:
- 선형탐색 1단계 — SDMPC 반복 0의 전체 스텝이 이동 한계에서 0.001 s 초과로 디코딩
  실패(`SC105_p4 green delta −6.001 vs limit 6.0`)하므로 SDMPC 가 유일한 스텝을 잃는다.
  +1.62 veh·h.
- 지평 2블록 — N_P/N_UF 가 450 s 양으로 합의됨. 재합의 필요.
- 다섯 개 `sdmpc_*` 고속경로 — 전부 이전에 속도 기각(`vissim-sdmpc-flags-rejected-not-unpromoted`).

## 정정 기록

- "선형탐색에서 전체 스텝이 항상 이긴다"는 **틀렸다**. trial 행에는 디코딩된 것만 남아
  첫 행을 전체 스텝으로 오독했다. SDMPC 반복 0에서 채택된 건 절반 스텝.
  `tools/pfo_line_search.py` 도 같은 함정.
- "PFO 370 s 가 아무것도 안 산다"는 **틀렸다**. PFO 가 결정 개선의 81%(6.78/8.40 veh·h)를
  시간의 68%로 산다. 초당 효율이 SDMPC 단계의 약 2배.
- `decision_mlc3`(후보 3개)의 최종 목적함수는 후보 1개와 소수점 끝자리까지 같다
  (393.91612458424544). 추가 후보 2개가 653 s 를 쓰고 0 을 샀다.
