# B1a Slice 3B fix round 7 보고서

- 일자: 2026-08-07
- 기준: `plant-fidelity-v2-1` @ `b3794d0`
- 대응 검토: `task-b1a-slice3b-fix6-rereview-and-task5-review.md` (fix6 CHANGES_REQUIRED, Task 5 CHANGES_REQUIRED)
- 상태: **IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW**

## 라운드 상한에 대한 기록

Slice 3B 는 규약상 5라운드 상한을 넘어 fix7 에 이르렀다. 근거를 남긴다.

fix1~fix5 는 서로 다른 결함을 순차로 닫았고, fix6 은 fix5 가 **엉뚱한 자리에** 넣은 검사를
제자리로 되돌린 것이다. fix7 의 4건은 같은 버그에 대한 재시도가 아니라 서로 독립적인 결함이며,
그중 3건(B2·B3·B4)은 fix6 과 무관하게 브랜치에 잠복해 있던 것이 전브랜치 검토에서 처음 드러났다.
"세 번 실패하면 아키텍처 문제" 규칙의 대상은 **동일 증상에 대한 반복 시도**이므로 여기에 해당하지 않는다.
다만 규약 이탈은 이탈이므로 이 문단으로 기록을 남긴다.

## 수정

### F1 — 루트 `stopped_vehicles` 항등식을 projection 판정기에 심는다 (검토 B1)

`plant/src/vissim_strict/physical_projection.py` — `normalize_vehicle_records` 의
`total_vehicles` 항등식 바로 옆에 루트 `stopped_vehicles` 항등식을 추가했다.
records 에서 재유도한 정지 대수와 일치하지 않거나, `int` 가 아니거나, `bool` 이면
`state_stopped_mismatch` 를 낸다.

**검토가 제시한 두 안 중 하류 미러링을 택했다.** 다른 안(`validate_state_projection_v2_1.py:451`
호출에 `require_vehicle_records` 전달)은 fix6 이 방금 푼 두 호출부의 계약 결합을 되살리고,
`normalize_vehicle_records` 와 겹치는 이중 검증을 만들며, 봉투 부재 경로의 reason 집합을 넓혀
sidecar 의미 해시를 흔든다. `normalize_vehicle_records` 를 실제로 대조해 보니 링크 카운트 맵,
스칼라 카운트, 루트 `total_vehicles` 항등식이 이미 있고 **빠진 것은 정확히 한 필드**였다.

부수 효과로 이 검사는 `required_vehicle_records` 와 무관하게 모든 state 에 적용된다. 이것이 옳다 —
어댑터(`vissim_stackelberg_adapter.py:3929`)는 필수 여부와 무관하게 이 필드를 읽는다.

**픽스처 정렬 2건.** `plant/tests/test_vissim_strict_physical_projection.py` 의 `state_fixture` 와
`scripts/tests/test_b1a_vbs_capture_helpers_behavior.py:447` 의 인라인 state 가 봉투를 만들면서
루트 `stopped_vehicles` 를 넣지 않았다. 실제 생산자
(`run_real_world_stackelberg_controller.vbs:1517,1525`)가 두 루트 카운트를 나란히 쓰는 것을 확인한
뒤 픽스처를 그 계약에 맞췄다. 테스트를 약화한 것이 아니라 실물과 어긋나 있던 픽스처를 고친 것이다.

### F2 — audit 의 state 발견에서 sidecar 를 배제한다 (검토 B2)

`scripts/audit_plant_fidelity.py` — 모듈 상수 `STATE_SIDECAR_SUFFIXES` 를 추가하고
`rglob("state_*.json")` 결과에서 해당 접미사를 배제했다.

이 모듈은 "표준 라이브러리만 쓴다"는 자체 계약이 있어 생산자에서 import 하지 않고 접미사를
복제했다. 복제로 인한 분기 위험은 **동작 기반 일치 테스트**로 닫았다 —
`projection_sidecar_path()` 와 `vehicle_capture_sidecar_path()` 를 실제로 호출해 그 산출 이름이
상수에 덮이는지 강제한다. 소스 문자열 매칭이 아니다.

### F3 — 템플릿 직렬화기를 하나로 합친다 (검토 B3)

`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1` — `ConvertTo-B1aTemplateJson`
하나를 만들어 발행 경로(`Write-B1aJsonTemplate`)와 dry-run 경로
(`Invoke-B1aTemplateValidationNoWrite`)가 같은 `allowed_capture_times` 정규화를 공유하게 했다.

파일은 순수 ASCII 를 유지한다(비-ASCII 바이트 0). 새 함수는 테스트 하네스가 추출하는 구간
(`Get-B1aWorkspaceRelativeFile` ~ `if ($B1aRequired)`) 안에 있다.

### F4 — 검토 원장이 git 추적망에 남게 한다 (검토 B4)

`.superpowers/sdd/.gitignore` 에 `!IMPLEMENTATION_PLAN/` 과 `!IMPLEMENTATION_PLAN/*.md` 부정 규칙을
추가했다. `sdd/` 아래 비-md 는 계속 무시된다.

## 검증

### 되돌림 증명 (write → PASS → revert → **must FAIL** → restore → PASS)

| 수정 | 되돌렸을 때 실제 결과 |
|---|---|
| F1 | `validate()` 가 1 이 아닌 **2** 를 반환하고 stdout 에 `status=PASS states=1`. 위조된 필수 state 가 PASS sidecar 를 받았다. |
| F2 | `state_file_count` 가 1 이 아닌 **3**. sidecar 2개가 state 로 집계됐다. |
| F3 | 압축 직렬화 산출물의 `allowed_capture_times` 원소가 `float` 이 아니었다. **추론이 아니라 실측이다.** |
| F4 | 프로브 `.md` 가 `git status` 에 뜨지 않는다. 수정 후 `??` 로 뜨는 것을 확인했다. |

F1 은 RED→GREEN 순서로 진행했으므로 되돌림 증명이 구현 이전에 이미 성립했다.

### 회귀

| 대상 | 결과 |
|---|---|
| `plant/tests` (cwd=`plant`, `PYTHONPATH`=저장소 루트) | **132/132 PASS** |
| `scripts/tests` + `tests` | **248 passed / 1 failed** |
| 봉투 생성 4개 파일 집중 | **74/74 PASS** |
| `git diff --check` | PASS (줄바꿈 경고만) |

**남은 1건은 기존 결함이다.** `tests/test_vissim_stackelberg_adapter_fidelity.py::
PlantFidelityProjectionTests::test_run_provenance_marks_missing_inputs` 는 `git stash` 로 모든
로컬 변경을 제거하고 HEAD `b3794d0` 상태에서 실행해도 동일하게 실패하는 것을 확인했다.
실패 지점은 `evaluation/controllers/vissim_stackelberg_adapter.py:1129` 의 `_git_commit` 이며
이번 수정이 건드리지 않은 파일이다.

이 테스트는 실행 방식에 따라 두 가지로 깨진다. 단독 실행에서는 한글 경로에서 `subprocess` 출력
디코딩이 실패해 `stdout` 이 `None` 이 되고(`PytestUnhandledThreadExceptionWarning`),
`scripts/tests` 와 함께 한 프로세스에서 실행하면 `sys.modules['src']` 가 `plant/src` 로 선점돼
`imported src from plant/src, expected under vendor/NumSim-mine` 로 깨진다. 둘 다 이번 변경과 무관하다.

### 이전 기록 정정

직전 라운드 보고가 "한글 경로 CP949 로 기존 실패 8건" 이라고 적었으나 **재현되지 않는다.**
현재 재현되는 기존 실패는 위 1건뿐이고, `scripts/tests/test_run_plant_fidelity_matrix.py` 는
11/11 PASS 다. `PYTHONPATH` 설정 여부가 원인이라는 가설을 직접 시험했으나 양쪽 모두 11/11 PASS 로
반증됐다. 8건이 관측된 환경 조건은 특정하지 못했으므로 메커니즘을 주장하지 않고,
재현되는 측정값만 기록한다.

## 변경 파일

```
.superpowers/sdd/.gitignore
plant/src/vissim_strict/physical_projection.py
plant/tests/test_vissim_strict_physical_projection.py
scripts/audit_plant_fidelity.py
scripts/run_real_world_single_watchdog_distributed_core15n41.ps1
scripts/tests/test_audit_plant_fidelity.py
scripts/tests/test_b1a_core_provenance.py
scripts/tests/test_b1a_run_manifest_slice.py
scripts/tests/test_b1a_vbs_capture_helpers_behavior.py
```

미커밋 07-31 산출물 11개는 이번 커밋에 **포함하지 않는다.** 별건이며 이전 라운드에서 `git add -A` 로
휩쓸었다가 되돌린 전례가 있다.

## 미해결 (검토가 비차단으로 분류)

- `require_vehicle_records` 기본값 `False` 의 fail-open 성격과 키워드 전용 필수 인자 전환.
- producer(`:635`)·재사용 validator(`:742`)의 중복 검증 제거 또는 문구 정정.
- 오프라인 state 로드 2곳의 `max_bytes` 계약 통일.
- `BoundedJsonSnapshot.value` 재귀 미동결 Minor.
- 비-ASCII `.ps1` 11개(이번 브랜치 산물 아님).

## NOT_EVALUATED

live COM, 지원 버전 실 readback, 라이브 커넥터·다차로 실표본, 결합 타이밍·p95,
post-run v2.2·replay, B1b 이후 전 구간은 변동 없이 미평가다.
