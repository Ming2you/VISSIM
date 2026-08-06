# B1a Slice 3B fix6 독립 재검토 + Task 5 전브랜치 검토

- 일자: 2026-08-06 ~ 2026-08-07
- 대상: `plant-fidelity-v2-1` @ `b3794d0`
- 계보: `cb3c44d`(baseline) → `a947317`(계획 v2.1) → `0d7c4fc`(S1) → `0ef76ad`(S0R) → `fb0d67d`(A1/A2) → `2778f54`(B1a) → `b3794d0`(fix6)

## 판정

| 대상 | 판정 |
|---|---|
| Slice 3B fix6 | **CHANGES_REQUIRED** — Important 1 |
| Task 5 전브랜치 | **CHANGES_REQUIRED** — Important 3 추가 |

fix6 의 **방향은 옳다.** 되돌릴 필요 없이 판정을 목적지에 심는 것으로 닫힌다.

## 방법

읽기 전용 렌즈 8개를 병렬로 돌렸다. 저장소 수정·VISSIM/cscript 실행·pytest 실행을 모두 금지했고,
모든 지적은 파일:줄 인용을 요구했다.

- fix6 렌즈 3개 — 지적 종결 검증 / 적대적 탈출 경로 / 파급 범위·계약 일관성
- 전브랜치 렌즈 5개 — 계획 대 구현 추적성 / 슬라이스 간 이음매 / 원장 정직성 / 증거 재현성 / 위생

Critical·Important 지적은 각각 **독립 반증자**에게 넘겼다. 반증자의 기본 자세는 "지적이 틀렸다"이며,
계획이 `NOT_EVALUATED` 로 명시한 공백을 결함으로 둔갑시킨 지적은 반증하도록 지시했다.

| | 생존 | 반증됨 |
|---|---|---|
| fix6 | 2 (병합 후 1) | 0 |
| 전브랜치 | 8 (병합 후 3) | 20 |

전브랜치 렌즈가 올린 Critical 8건 중 다수가 반증에 무너졌다. 대부분 계획이 선언한 미평가 공백을
결함으로 옮긴 것이었다. 특히 v2.2 생산자 2개의 부재는
`task-b1a-watchdog-attempt-launch-slice-report.md:106-110` 이 의도적 fail-closed 로 명시했고
해당 슬라이스는 독립 승인을 받았다.

**생존 지적 4건은 전부 저자(Claude)가 코드를 직접 열어 재확인했다.** 아래 근거는 에이전트 보고의
전재가 아니라 재확인 결과다.

## 차단 지적

### B1. 루트 `stopped_vehicles` 가 manifest→projection 경로 전체에서 무검증 (Important)

fix6 이 제거한 인자가 켜던 `build_state_manifest_v2_1.py:590-591` 이 저장소에서 이 필드를
검사하는 **유일한 코드**였다.

- 하류는 대신하지 않는다. `validate_state_projection_v2_1.py:451` 은 인자 없이 호출한다.
  `required_vehicle_records` 를 보는 `:469` 는 `:466` 의 `if "vehicle_records" not in state:`
  분기 안에만 있어 **봉투 부재에만** 적용된다.
- 봉투가 존재하되 변조된 경우의 판정자는 `:492` `normalize_vehicle_records` 인데,
  `physical_projection.py:1145-1147` 은 `total_vehicles` 만 재유도한다.
- `git grep stopped_vehicles -- plant/src/ scripts/validate_state_projection_v2_1.py` → **0건**.

**결과** — records 는 그대로 두고 루트 `stopped_vehicles` 만 바꾼 필수 state 가
`build_manifest` exit 0 을 받고 projection sidecar 도 PASS 로 발행된다. 변조 후 파일로 해시를
계산하므로 해시 결속도 막지 못한다. `2778f54`(fix5)에서는 같은 입력이 exit 1 이었다.

**장식이 아니다** — `evaluation/controllers/vissim_stackelberg_adapter.py:3929` 가 램프 방류
가드에, `scripts/audit_plant_fidelity.py:673` 이 감사에 그대로 먹인다.

라이브 캡처는 VBS 가 rename 전에 CLI(`:1306`, `True`)를 부르므로 보호된다. 재생·수동 구성·
rename 이후 변조 state 는 보호되지 않는다.

### B2. sidecar 파일명이 audit 의 state 발견 glob 과 충돌 (Important)

두 sidecar 모두 state 의 형제로 `state_` 접두사를 물려받는다.

- `plant/src/vissim_strict/physical_projection.py:454` → `{stem}.physical_projection_v2_1.json`
- `scripts/build_state_manifest_v2_1.py:301` → `{stem}.vehicle_capture_v2_1.json`
- `scripts/audit_plant_fidelity.py:1297` → `rglob("state_*.json")` 이 **둘 다 매칭한다**

sidecar 는 JSON object 이므로 valid 집합에 들어가지만 link counts 가 없어
`missing_link_counts_count` 가 증가하고 `state_observation_contract_gate` 가 FAIL 한다.
이 게이트는 `run_plant_fidelity_matrix.ps1` 에서 필수로 지정돼 매트릭스를 죽인다.
보고 문구가 "missing counts, speeds, or stopped counts" 라 **실제 원인과 전혀 다른 곳을 가리킨다.**

### B3. dry-run 템플릿 직렬화기가 발행 경로의 정규화를 생략 (Important)

같은 템플릿을 두 직렬화기가 다르게 내보낸다.

- 발행 `Write-B1aJsonTemplate` 은 `allowed_capture_times` 를 JSON double 로 다시 쓰고,
  치환이 정확히 1회가 아니면 throw 한다 — 저자 스스로 계약으로 못박았다.
- dry-run `Invoke-B1aTemplateValidationNoWrite` 는 `ConvertTo-Json -Compress` 만 쓴다.
- 소비자 `plant/src/vissim_strict/run_evidence.py:718` 은 정수를 거부한다.

**추론이 아니라 실측이다.** 압축 경로 산출물을 파싱해 보니 `allowed_capture_times` 원소가
`float` 이 아니었다. dry-run 이 항상 죽거나, 통과하더라도 실제 발행 바이트와 다른 것을 검증한다.

### B4. `.superpowers/sdd/.gitignore` 가 `*` 라 앞으로의 원장이 추적망에서 사라진다 (Important)

파일 내용이 `*` 한 줄뿐이고 부정 규칙이 없다. 현재 105개가 추적 중인 것은 강제 추가했기 때문이지
규칙이 허용해서가 아니다. 다음 라운드가 재검토 문서를 쓰면 `git status` 에 뜨지 않고
`git add .` 로도 안 잡혀, 커밋 없이 세션이 끝나면 클린 클론에서 **판정 근거가 소실된다.**

## 비차단 (원장 반영 대상)

- `progress.md:61` 의 "봉투 판정은 이미 하류에 있다" 서술이 부분적으로만 참이다. `:469` 는 봉투
  부재만 다룬다. 문구를 정정해야 다음 세션이 B1 을 재발견하지 못하는 일이 없다.
- 같은 줄의 `build_state_manifest_v2_1.py:1116` 인용이 한 줄 어긋났다. 실제 kwarg 은 `:1117` 이었다.
- `require_vehicle_records` 기본값이 `False` 라 fail-open 이다. 키워드 전용 필수 인자로 바꾸면
  5개 호출부가 각자의 계약을 코드에 명시하게 된다.
- producer(`:635`)·재사용 validator(`:742`)의 `require_vehicle_records=True` 는 바로 다음 줄의
  무조건 `_state_records_by_no` 호출 때문에 거부에 기여하지 않는 중복이고, 8 MiB state 를 2회 검증한다.
  fix6 커밋 메시지가 "세 경로 모두 즉시 거부" 라 한 것은 실제로 CLI(`:1306`) 하나뿐이다.
- 오프라인 state 로드 2곳(`build_state_manifest_v2_1.py:1079`,
  `validate_state_projection_v2_1.py:428`)이 `strict_load_json` 을 `max_bytes` 없이 부른다.
  나머지 필수 경로는 fix2/fix3 에서 `_strict_load_json_no_bom(..., max_bytes=MAX_STATE_BYTES)` 로 닫혔다.
- `BoundedJsonSnapshot.value` 재귀 미동결(`physical_projection.py:355-362`). 슬라이스 2 가
  최종 검토로 미룬 Minor 이며 지금도 유효하다.
- `.ps1` 11개에 비-ASCII 바이트가 있다(`run_g6_branch_grid.ps1` 2,862 등). 이번 브랜치가 만든
  파일은 아니다. `run_real_world_single_watchdog_distributed_core15n41.ps1` 은 순수 ASCII 다.
- 5라운드 상한을 넘긴 근거를 `progress.md:28` 과 같은 형식으로 기록해야 한다.

## NOT_EVALUATED (계획이 선언한 공백 — 차단 사유 아님)

- 실 VISSIM COM 실행과 readback. runtime p95 및 결합 타이밍 영수증.
- `build_run_artifact_manifest_v2_2.py` / `build_projection_live_evidence_v2_2.py` 부재로 인한
  B1a required·dry-run 경로 차단. 슬라이스 리포트가 의도적 fail-closed 로 명시했다.
- S1-2 active-program 런타임 readback, compound closure 종료 조건.
- S0R-3 실측 baseline 스냅샷. 3600초 실 COM 런이 선행조건이다.
- post-run v2.2 아티팩트 매니페스트와 live evidence replay.
- 라이브 커넥터·다차로 실표본 커버리지.
- B1b 이후 B 작업, 그리고 C/D/E/G/H/I/J/K/X 전 구간.
- `state-selection-v2.1` 생산자와 3B 판정 단계 오케스트레이터.

## 저자 판단 (에이전트 제안과 다른 부분)

B1 에 대해 재검토는 두 안을 제시했다. **저자는 두 번째 안을 택했다.**

- 안 A — `validate_state_projection_v2_1.py:451` 호출에 `require_vehicle_records` 를 넘긴다.
- 안 B — `physical_projection.py:1145` 의 `total_vehicles` 항등식 옆에 루트 `stopped_vehicles`
  항등식을 미러링한다.

**안 B 를 택한 이유.** `normalize_vehicle_records` 가 강제하는 항등식을 실제로 대조해 보니
링크 카운트 맵(`:1127`), 스칼라 카운트(`:1137`), 루트 `total_vehicles`(`:1145`)가 이미 있고
**빠진 것은 정확히 한 필드**였다. 안 A 는 fix6 이 방금 푼 두 호출부의 계약 결합을 되살리고,
`normalize_vehicle_records` 와 겹치는 이중 검증을 만들며, 봉투 부재 경로의 reason 집합을 넓혀
sidecar 의미 해시를 흔든다. 확인된 구멍이 한 필드이므로 그 필드만 형제 항등식 옆에 놓는다.

부수 효과로 안 B 는 `required_vehicle_records` 와 무관하게 **모든** state 에 적용된다. 이것이 옳다.
어댑터는 필수 여부와 무관하게 이 필드를 읽는다.
