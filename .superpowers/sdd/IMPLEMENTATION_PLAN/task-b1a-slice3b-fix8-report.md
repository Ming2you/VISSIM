# B1a Slice 3B fix round 8 보고서

- 일자: 2026-08-07
- 기준: `plant-fidelity-v2-1` @ `a9f6dea`
- 대응 검토: fix7 독립 재검토 (CHANGES_REQUIRED, Important 2 + Minor 9)
- 상태: **IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW**

## 재검토 판정 수용

fix7 재검토는 F1·F3·F4 를 닫힌 것으로, **F2 를 절반만 닫힌 것으로** 판정했고
F3 의 되돌림 증명 주장이 성립하지 않는다고 지적했다. 두 지적 모두 저자가 코드로
재확인한 결과 **사실이다.** 수용한다.

## 수정

### F5 — sidecar 배제를 baseline 검증에도 넣는다 (재검토 Important 1)

`scripts/validate_baseline_snapshot.py` 두 곳.

- `:780-787` 이 audit 의 `state_file_count` / `state_files` 와 **정확히 대조**한다.
  audit 만 sidecar 를 거르면 두 목록이 어긋나 `"audit action JSON inventory/count/status
  differs from baseline"` 으로 FAIL 한다. F2 가 겨냥한 조건에서 실패 이유만 바뀐 셈이다.
- `:1250` 의 `discovered` 도 무필터라 sidecar 가 `unexpected` 로 분류돼 FAIL 한다.

접미사는 `_current_auditor().STATE_SIDECAR_SUFFIXES` 로 참조한다. 이 파일은 이미
`_current_auditor()` 로 audit 모듈을 로드하므로 **접미사가 한 곳에만 존재**하게 되어
복제로 인한 분기 위험이 사라진다.

### F6 — dry-run 호출부를 테스트로 고정한다 (재검토 Important 2)

**재검토 지적이 옳다.** fix7 의 되돌림 증명은 *하네스의 직렬화*를 되돌린 것이라
결함의 실재는 보였지만 `.ps1` 호출부를 지키지는 못했다. 저장소 전체에서
`Invoke-B1aTemplateValidationNoWrite` 를 태우는 테스트는 **하나도 없었다.**

`test_dry_run_path_uses_the_shared_template_serializer` 를 추가해 두 호출부의
함수 본문을 소스로 고정한다 — 공유 직렬화기 호출이 있어야 하고, 그 본문에
`ConvertTo-Json` 직접 호출이 **없어야** 한다.

#### 채택하지 않은 방식과 그 이유

먼저 하네스가 `Invoke-B1aTemplateValidationNoWrite` 를 **실제로 호출**하게 만들었다.
두 단계로 막혔다.

1. 한글 저장소 경로가 CP949 로 깨졌다(`can't open file '...?숈닠...'`). 하네스 `.ps1` 을
   BOM 있는 UTF-8 로 쓰면 해결된다.
2. 그래도 생산자가 **출력 한 글자 없이** 비영 종료했다. Bash 도구에서는 5/5 통과(7.5초),
   PowerShell 도구에서는 3/3 실패(1.2초)로 재현된다. 샌드박스 가설을 세우고
   `dangerouslyDisableSandbox` 로 시험해 **반증**했다. 원인은 특정하지 못했다.

원인 미상의 환경 의존 테스트를 남기면 다음 세션이 같은 함정에 빠진다. 재검토가 제시한
대체안(소스 고정)이 결정적이고 환경 독립적이므로 그쪽을 택했다. 하네스 추출 구간 확장과
BOM 변경은 필요 없어져 되돌렸다.

### Minor 처리

| 지적 | 처리 |
|---|---|
| `state_stopped_mismatch` 가 closed reason vocabulary 에 없음 | `task-b1a-brief.md:469` 에 추가 |
| stopped 항등식 모집단이 total 과 다름 | 주석 정정. total 은 `raw_count`, stopped 는 검증 통과 레코드만 센다. 레코드가 탈락하면 이미 FAIL 이라 오탐 PASS 는 없다 |
| plant/tests 가 새 항등식을 덮지 않음 | `wrong_stopped`(값 불일치)와 `missing_stopped`(필드 부재) 음성 케이스 2개 추가 |
| 감사 인용 `:673` 오류, 소비 수준 과장 | 주석 정정. 루트 stopped 를 읽는 곳은 `:685` 이고 `:912` 는 `total_vehicles` 만 꺼낸다. **감사는 기록만 하고 판정하지 않는다** |
| `.gitignore` 부정 규칙이 하위 디렉터리·비-md 를 못 살림 | `!IMPLEMENTATION_PLAN/**` 로 확장. 프로브로 양방향 확인 |
| F3 동등성 비교가 int/float 갈림을 못 잡음 | `assert_same_json_types` 재귀 타입 대조 추가. `assertEqual` 은 `1 == 1.0` 이라 못 잡는다 |

### 수용하되 이번에 고치지 않은 것

- **F1 은 사후 증거 경로만 닫는다.** 라이브 결정 루프는 `normalize_vehicle_records` 를
  타지 않는다(어댑터의 호출 지점은 `--projection-only` 분기 안이다). 변조된 값은 그 스텝의
  `floor_ratio` 를 실제로 움직인 뒤 나중 projection 에서 드러난다. 이 문서로 정정하며,
  라이브 경로 차단은 B1b 이후 소관이다.
- **커밋 `1b00e2f` 이 독립 결함 2건(F1/F2)을 묶었다.** 이미 푸시된 커밋이라 이력을
  다시 쓰지 않는다. 이번 라운드는 F5/F6/Minor 를 성격별로 나눠 커밋한다.
- **동종 무필터 glob 4곳**(`replay_discharge_hypothesis.py:48` 등)은 fidelity 게이트
  경로가 아니어서 이번 범위 밖으로 둔다.

## 검증

### 되돌림 증명

| 수정 | 되돌렸을 때 실제 결과 |
|---|---|
| F5 | baseline 스냅샷 전체 `status` 가 `FAIL` |
| F6 | `.ps1` 호출부 한 줄만 되돌려도 `ConvertTo-B1aTemplateJson $Template $true' not found` |

### 회귀

| 대상 | 결과 |
|---|---|
| `plant/tests` | **132/132 PASS** |
| `scripts/tests` + `tests` (PowerShell) | 아래 "실행 쉘" 참조 |

### 실행 쉘이 결과를 바꾼다 (이번 라운드에서 확정)

`scripts/tests` 는 **PowerShell 에서** 돌려야 한다. Bash 에서 돌리면
`test_run_plant_fidelity_matrix.py` 가 11건 중 7건 실패한다 — 이 테스트들이
`run_plant_fidelity_matrix.ps1` 을 자식으로 띄우기 때문이다. PowerShell 에서는 11/11 PASS 다.
`git stash` 로 로컬 변경을 모두 없앤 HEAD `a9f6dea` 에서도 Bash 실패 7건이 동일하게
재현되므로 코드 결함이 아니다.

이것이 fix7 보고서가 정정한 "CP949 8건" 의 실체다. 그 숫자는 **Bash 에서 측정된 것**이었고,
fix7 이 PowerShell 에서 재보니 1건이었다. 어느 쪽도 틀리지 않았고 쉘이 달랐다.
fix7 보고서의 "재현되지 않는다" 는 서술을 이 문단으로 보완한다.

`plant/tests` 는 양쪽 모두 132/132 다.

## 변경 파일

```
.superpowers/sdd/.gitignore
.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-brief.md
plant/src/vissim_strict/physical_projection.py
plant/tests/test_vissim_strict_physical_projection.py
scripts/tests/test_b1a_run_manifest_slice.py
scripts/tests/test_validate_baseline_snapshot.py
scripts/validate_baseline_snapshot.py
```

## NOT_EVALUATED

live COM, 지원 버전 실 readback, 라이브 커넥터·다차로 실표본, 결합 타이밍·p95,
post-run v2.2·replay, B1b 이후 전 구간은 변동 없이 미평가다.
