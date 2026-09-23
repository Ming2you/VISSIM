# ① 스퀴즈 적용 + ⑤ native 런 준비 — 2026-09-23

## 1. 결정 시간 예산은 관문이 아니었다

`decision_time_budget_sec = 120`, 결정은 544.5초. 처음엔 관문으로 봤으나 틀렸다.

- `area_follower_objective.py:1249-1251` — `unlimited_time` 이면 `remaining()` 이 `math.inf`,
  따라서 `check()` 가 절대 안 터진다.
- `vissim_stackelberg_adapter.py:12931-12934` — native 경로가
  `unlimited_time=joint_options.get('ignore_wall_time_limits', False)` 를 전달한다.
- `config_candidate.json` 에 `ignore_wall_time_limits = True` 가 **이미** 있다.

검증기는 `0 < decision_time_budget_sec < T_c_sec(=150)` 을 강제하므로 예산을 545초로
**올릴 수는 없다**. 설계된 탈출구가 `ignore_wall_time_limits` 다.

곁가지로 확인한 사실: 마감이 터지면 `vissim_stackelberg_adapter.py:13509-13511` 이
영수증에 적고 **다시 던진다**. VBS `:1143` 는 그걸 `decisionsFailed` 로 세고 런을
계속한다 — 즉 예산이 모자라면 런이 죽는 게 아니라 **조용히 무제어로 완주**한다.
`DECISIONS_FAILED` 요약행을 반드시 봐야 하는 이유.

VISSIM 은 결정 중 멈춰 있다(`RunCapture3` 의 `Do While exec.Status = 0` 스핀대기,
`scripts/run_real_world_stackelberg_controller.vbs:4962-4966`). 결정 호출에는 VBS
타임아웃이 없다(`:1136` 은 `RunCapture3`, 타임아웃 변형이 아니다). 따라서 벽시계
초과가 시뮬레이션을 어긋나게 하지 않는다 — 비용은 벽시계뿐이다.

## 2. 적용한 스퀴즈 (셋 다 무손실)

| 레버 | 파일 | 내용 |
|---|---|---|
| A | `sdmpc_tangent_runtime.py` | AST 변환 코드 객체 marshal 캐시 |
| B | `sdmpc_tangent_reverse.py` | `Trace.branch` 본문 인라인 |
| C | `sdmpc_tangent_reverse.py` | 2인자 max/min 직행 진입점 |

캐시 키 = sha256(소스) + sha256(runtime 자기 소스) + 인터프리터 태그 + **파일명**.
파일명이 빠지면 바이트 동일한 소스(빈 `__init__.py`)끼리 항목을 공유해 트레이스백이
깨진다. 미스·손상·쓰기불가는 전부 in-process 컴파일로 폴백하므로 캐시는 빨라지게만
할 수 있고 무엇이 도는지는 못 바꾼다.

B 에서 두 술어를 **일부러 분리해 유지**했다. 역방향 `Dual` 만 `.support` 를 갖고,
`primal()` 은 아무 `forward.Dual` 에서나 `.value` 를 읽는다. 합치면 맨 forward Dual 의
정확일치 판정이 조용히 바뀐다.

C 에서 `branch()` 호출은 `_two_argument` 안에 **남겨뒀다**. 완전 인라인이 호출당
약 170 ns 더 벌지만 증거 기록이 두 군데로 갈라진다. 한 군데를 택했다.

### 검증

- `python -B -m unittest` 10개 모듈 **111 테스트, 적용 전후 모두 OK**
- 무작위 동등성 6,000 케이스 **불일치 0**
  (`tools/equiv_squeeze.py` — 구 모듈을 나란히 올려 비교)
  피연산자 4종(역Dual/순Dual/float/int) 전조합 × max·min·branch ×
  `FAST_PRIMITIVES` 양쪽 × `discrete` 양쪽 × 시퀀스형(1·2·3·5인자, `*args`, `key=`).
  선택된 피연산자의 **동일성**(`is`), 값, `counts`, `exact_support`,
  `discrete_support`, 그리고 발생 예외까지 비교.

### 실측 절감 (`tools/bench_squeeze.py`)

| 항목 | 호출당 | 롤아웃당 | 결정당(직렬 5배치) |
|---|---|---|---|
| marshal 캐시 | — | 2.92 s/스폰 | ~14.6 s |
| `branch` (plain/tie/discrete) | 194 / 207 / 207 ns | 1.73 s | ~6.9 s |
| 2인자 max/min | 540 ns | ≤4.32 s | ~17.3 s |

**합계 약 22~39초 (544.5초의 4~7%).** 54개 결정이면 20~35분.
워크플로 추정(45~70초)보다 보수적이다 — C 에서 완전 인라인을 포기했고,
이 트리의 계측 모듈이 97개가 아니라 88개다.

## 3. 아카이브 앵커는 병합 트리에 못 쓴다

`diagnostics/sdmpc_stream_summary_20260922/hotpath_h3_v1/request.pickle` 로 결정을
재보려다 `AttributeError: 'PhysicalLaneGroups' object has no attribute 'hadi'` 로 죽었다.

원인: 그 피클이 **병합 전 스냅샷**이다. 원바이트 검사 결과 `PhysicalLaneGroups`(1건),
`widths`, `partitions` 는 있는데 `hadi` · `vsl_fd_response` ·
`receiving_speed_response` · `port_response` · `freeway_hadiuzzaman` 은 **전부 0건**.
`__setstate__`(`physical_lane_groups.py:165-173`)는 `__dict__.update` 만 하므로
`__init__` 이 세우는 신규 속성이 복원되지 않는다. 트리 안의 `request.pickle` 4개가
전부 같다.

따라서:

1. **544.5초와 ① 레버 수치는 전부 "구 plant" 에서 나온 값이다.** 새 plant 가
   예측마다 하는 추가 일(Hadi CTM, VSL FD 응답, 포트 응답, 수용속도 응답)은 들어 있지
   않다. 544.5초는 병합 시스템의 **하한**이다.
2. 병합 시스템의 결정 시간은 **native 런이 나오기 전엔 알 수 없다.**

반쪽 객체를 억지로 돌리지 않았다. 남은 무손실 레버(중앙 Jacobian 생략 ~29 s,
forward 열 블로킹 12~28 s, 감사 레코드 지연화 11 s)는 실제 앵커가 생긴 뒤에
측정과 함께 하는 게 맞다.

## 4. 병합이 미추적 파일 1,186개를 놓쳤다

스냅샷 커밋 `96ea2a5` 는 **추적 중인 수정**만 담았다. controller 워크트리가 만든
미추적 산출물은 sim3 에 오지 않았고, 런은 그중 처음 필요한 하나에서 죽는다
(`diagnostics/lane_plant_20260921/plant.json`).

- config 참조 파일 58개 중 **21개**가 sim3 에만 없었다 (`tools/audit_config_paths.py`)
- 전수조사: 미추적 1,361개 중 **1,186개** 누락
- sim3 에 **없는 것만** 채웠다(7.36 GB, 1,183개). plant 쪽 덮어쓰기 0건.
  (`tools/fill_untracked.py`)

같은 계열의 다른 누락도 하나 고쳤다: item-3 수정(다중 budget numpy 타입 누출)이
sim3 에 없어 이식했다. 반대로 `vissim_stackelberg_adapter.py` 의 차이는
**sim3 가 맞다** — `freeway_fd.cell_state_response` 를 쓰는 plant 병합 결과다.

## 5. ⑤ native 런 구성 (정본 레시피)

plant 브랜치 자체 런처 `diagnostics/run_selected_control_trial.ps1:58-66` 에서 뽑았다.

```
Network            prepared/network/baseline.inpx   (sha256 22c36aa9… = CURRENT_SCENARIO 의 native_prepared_network_sha256)
Tuning             diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json
Calibration        evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json
Mapping            evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json
VbsConfig          evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs
Controller         wu-link          WarmupController  no-control
ControlIntervalSec 150              ControlStartSec   900
StateLogIntervalSec 5               Seed              23
StallSec 2400   StartupStallSec 300   MaxAttempts 1   NoGlobalKill
```

**`-VbsConfig` 가 제일 위험한 인자다.** 그게 플랜트가 *무엇을 기록하는지*
(`RW_LOCAL_OBSERVABLE_LINKS`)를 정한다.

| 출처 | 관측 링크 |
|---|---|
| VBS 자체 기본값 (`:249`) | 18 |
| base 생성 설정 | 22 |
| **ver2n21 설정** | **680** |
| ver2 검지 매핑(컨트롤러 투영 대상) | **680** |

base 를 쓰면 97%가 데이터 없이 채점된다 — `run_real_world_single_watchdog.ps1:89-94`
가 기록한 2026-08-04 사건(도시 차량의 1.4%만 포착, 모든 도시축 후보가 부호 반대로
채점)이 그대로 재현된다. ver2n21 을 쓰면 680 대 680 으로 맞는다.

확인한 것 둘:
- ver2n21 매핑의 `signals` 는 **17개**다. 메모리의 "ver2 매핑 signals 가 1개뿐이라
  조용히 무제어" 결함은 **n21 변형에는 없다.**
- `ramp_meters` 8개(`RM_C10480/10482/10646/10644/10639/10681/10490/10484`)로
  핸드오프 ⑤의 "8개 물리 meter" 및 사용자가 준 `heads.json` 과 일치.

`run_selected_control_trial.ps1` 자체는 못 썼다 —
`prepare_selected_control_demand.py:130` 이 **시드 13 / 종단 5400초** NC 증거만 받는데
`CURRENT_SCENARIO.json`(2026-09-22 15:15 사용자 선택)은 시드 23 / 9000초다.
그래서 같은 인자로 워치독
(`scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`)을 직접 부른다.
그 워치독은 `$ExistingIds` 로 기존 VISSIM PID 를 제외하므로 s31_rm 과 동시 실행해도
창 제목 귀속이 안 깨진다.

첫 런은 **짧게**(핸드오프 ⑤ "짧은 native 적용 검증"): `SimPeriod 1500` → 결정 4개
(900·1050·1200·1350). 연속 결정이 나오면 **④(다음 interval 재초기화)도 같이 닫힌다.**

## 6. 남은 것

- ⑤ 결과 판독: `DECISIONS_OK`/`DECISIONS_FAILED`, green/offset/VSL/미터 명령과 적용
  영수증, `previous_budget_reused=false`, 가격 이어받기 경로
- ④ 는 ⑤ 의 연속 결정으로 마무리
- 실제 앵커가 생기면 남은 무손실 레버 측정 후 적용
- ⑥ 전장 런(9000초 = 결정 54개)
