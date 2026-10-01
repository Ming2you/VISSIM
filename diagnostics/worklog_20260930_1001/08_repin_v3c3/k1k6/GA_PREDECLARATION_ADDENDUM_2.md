# GA 사전 선언 보충 2 — SDMPC 결정의 `transformed_source_sha256` 키

- 작성 2026-10-01. **GA 재생을 하나도 돌리기 전**에 고정합니다. 고정 수단은 `GA_PREDECLARATION_ADDENDUM_2.md.sha256`입니다.
- 원 선언 `GA_PREDECLARATION.md`(`34cc48ee…`)와 보충 1(`607a2eb5…`)은 그대로 둡니다. 이 보충은 SDMPC 결정(GA-2의 900, GA-3, GA-4)의 B1 열거에 항목 하나를 **추가**합니다.

## 왜 생겼나

- 개발용 점검을 했습니다. GA 관문이 아닙니다.
  - 대상: R-obs 900 반사실 SDMPC(wu-link)
  - Root = W @ `54d821c1`, 도구 = W
  - 결과: `reports/k1k6/smoke/S000900_54d821c1.summary.json` [실행]
- 비교 상대는 T5-B 기록 `T000900_r1`(5323faa4, Root `D:/VISSIM-merge/sim3-n31-v3c1`)입니다.
- 판정 필드는 모두 같았습니다.
  - CSV 바이트
  - progress `objective`/`held_objective` repr
  - CONTROL_FIELDS 7개
  - 탄젠트 트레이스(시간 키 제외)
  - 4필드: 차이 0
- 차이가 난 곳
  - 열거되지 않은 차이 384개가 **모두** `metadata.joint_leader_selection.tangent_derivatives[i].transformed_source_sha256`에 있었습니다. 이 dict는 계측된 모듈마다 **절대 경로 키** → 원본 sha 값입니다.
  - Root가 바뀌면 키 97개(탄젠트 호출 2회 × 97)가 모두 "only in original"/"only in replay"로 나옵니다.
  - 그 밖의 차이는 보충 1의 경로 2개, state_json, 새 metadata 키 3개, §2.3 provenance뿐이었습니다.

## 추가 열거 (B1, 양성 조건)

| 필드 | 허용 조건 |
|---|---|
| `metadata.joint_leader_selection.tangent_derivatives[i].transformed_source_sha256` | (1) 각 i에서 키의 Root 접두를 떼어 낸 **상대 경로 집합이 원본과 같음**. (2) 키는 모두 그 재생의 Root 아래. (3) sha 값은 상대 경로가 `git diff --name-only 9ed2ef0 <K6>`에 있는 파일에서만 다르고, 나머지는 원본과 같음 |

- smoke에서 측정한 값 [실행]
  - 키 수: 97 / 97, 상대 경로 집합 같음
  - sha가 다른 파일 5개: `evaluation/controllers/freeway_fd.py`, `physical_ramp_branches.py`, `runtime_setup.py`, `vissim_stackelberg_adapter.py`, `vendor/NumSim-mine/src/models/state.py`
  - 이 5개는 모두 K1–K6 diff 안에 있습니다. `lane_plant_runtime.py`, `obs150_contract.py`, `vsl_command_distribution.py`는 탄젠트 워커가 import하지 않아 이 dict에 없습니다.
- 이 필드는 K 코드가 **실제로 계측·실행됐다는 양성 증거**로도 씁니다(B2). 다섯 파일의 sha가 K6 트리 파일의 sha와 같아야 합니다.

## 정리 (SDMPC 결정의 전체 허용 목록)

- V(SDMPC 규칙: 시간 키, pickle 토큰, state_json)
- 원 선언 §2.3 provenance 열거와 보충 1의 정정
- 보충 1의 Root 경로 metadata 3개
- 이 보충의 `transformed_source_sha256`
- §2.2 새 metadata 키 3개
- 4필드 이름 리프 ≤ 2 ulp

이 목록 밖의 차이는 선언 밖입니다.
