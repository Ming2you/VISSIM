# GA 사전 선언 보충 1 — Root에 따라 바뀌는 metadata 경로 3개와 git 필드 정정

- 작성 2026-10-01. **GA 재생을 하나도 돌리기 전**에 고정합니다. 고정 수단은 `GA_PREDECLARATION_ADDENDUM_1.md.sha256`입니다.
- 원 선언 `GA_PREDECLARATION.md`(sha256 `34cc48ee…`)는 고치지 않았습니다. 이 보충은 §2.3(B1 열거)에 **추가**만 합니다. 그 밖의 조건은 그대로입니다.

## 왜 생겼나

- K6 커밋 뒤에 개발용 점검(smoke)을 한 번 돌렸습니다. GA 관문이 아닙니다.
  - 대상: R-obs 4050 무제어 결정을 W(`D:/VISSIM-merge/sim3-n31-v3c3` @ `54d821c1`, Root = W)에서 재생
  - 결과: `reports/k1k6/smoke/T004050_54d821c1.summary.json` [실행]
- 그 diff에서 원 선언 §2.3이 열거하지 않은 차이가 2개 나왔습니다. 둘 다 `run_provenance` 밖에 있는 **절대 경로 문자열**이고, 재생 Root가 바뀌면 K 코드와 무관하게 바뀝니다.
- 그래서 61개 R-obs 결정 전체에서 FRZ_OLD 경로를 담은 문자열 리프를 `run_provenance` 밖에서 모두 찾았습니다 [실행]. 결과는 3개 경로, 각각 61/61입니다.

## 추가 열거 (B1, 양성 조건 포함)

| 필드 (action JSON) | 원본 | 재생에서 허용하는 값 |
|---|---|---|
| `metadata.detector_mapping_resolved_path` | `FRZ_OLD\evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json` | 같은 상대 경로로 `<Root>` 아래(smoke에서 확인), 또는 원본 그대로 |
| `metadata.native_phase_share_map_path` | `FRZ_OLD\outputs\movement_signal_group_map_v3.json` | 같은 상대 경로로 `<Root>` 아래(smoke에서 확인), 또는 원본 그대로 |
| `metadata.shared_approach.demand_profile.path` | FRZ_OLD 아래 경로 | 원본 그대로(smoke에서 바뀌지 않음), 또는 같은 상대 경로로 `<Root>` 아래 |

- 위 세 필드 말고 FRZ_OLD나 `sim3-n31-v3c1`을 가리키는 문자열이 재생 JSON에 새로 나타나면 선언 밖 차이입니다.

## 정정 (원 선언 §2.3 "바뀌지 않아야 하는 필드" 문단)

- `numsim_git_commit`: Root가 git 작업 트리여도 **빈 값('')으로 남습니다**. smoke에서 W Root인데 ''였습니다 [실행]. 그래서 GWT Root의 기대값은 K6 해시가 아니라 **''**입니다.
- `workspace_git_commit`: FRZ_K6 Root에서는 '', GWT Root에서는 K6 해시입니다. 원 선언과 같습니다. smoke(W Root)에서는 W HEAD `54d821c1…`이었습니다.

## smoke에서 함께 본 것 (참고, 관문 아님)

- prepare, ps1, compare(비-tuning)가 모두 exit 0이고 판정은 IDENTICAL입니다. CSV 바이트도 같습니다.
- 새 metadata 키 3개는 원 선언 §2.2의 값과 정확히 같았습니다.
- 4필드 ulp 거리
  - `state_summary.off_ramp_storage_veh` 1
  - `calibrated_state_summary.off_ramp_storage_veh` 1
  - `terminal_features.ramp_vehicles` 1
  - `terminal_features.stopped_vehicles` 2
  - 모두 선언한 ≤ 2 ulp 안입니다.
- `run_provenance` 차이: `imported_modules` 31(경로 30 + state.py sha), `inputs` 16(경로 15 + adapter sha), `workspace_root`, `numsim_repo_root`, `numsim_src_sha256`, `execution_fingerprint_sha256`, `workspace_git_commit`. `metadata.run_provenance`에 같은 사본이 있습니다. 원 선언 §2.3 열거와 같습니다.
