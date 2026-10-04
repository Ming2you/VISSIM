# GB-1 사전 선언 — v3c3 무제어(NC) 궤적이 v3c2 와 같은가

- 동결: 2026-10-01 KST(+0900), v3c3 런 발사 전. 이 파일의 sha256 은 같은 폴더 `gb1_predeclaration.md.sha256` 에 적습니다.
- 동결 시점 상태 [실행]
  - 여섯 시드(s31/41/43/47/53/37) 모두 `run\` 과 `launch.log` 가 없습니다.
  - VISSIM·cscript 프로세스는 0개입니다(`reports/v3c3_prepare_checks.json` running_vissim_cscript_count).
- 근거
  - 사용자 승인(2026-10-01): `REPIN_V3C2_PLAN.md`(sha `d4b70c02…`)의 권고값 U1–U12 와 검토 수정(`REPIN_V3C2_PLAN_REVIEW.md`, sha `bc08f3df…`)
  - 계획 §2.4(GB-1 정의, 실패 시 STOP), U2-a(fit 5시드 전부), U2-c(봉인 s37 은 해시 전용 도구 허용)
  - 검토 N9(`.err` 세 개, `runner_sha256` 과 VISSIM 빌드를 전제 조건으로)
- 표기: **[실행]** 명령으로 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단

## 0. 고정 자료

| 항목 | 경로(`D:/VISSIM_runs/20261001_v3c3/` 기준) | sha256 |
|---|---|---|
| 편집 영수증 | `v3c3_edit_receipt.json` | `b1bd1fd5d6b80ce95eefcfb1c2e45afed1ffe1284439098b9fea05156c108b0f` |
| 정적 검사 21개(전부 참) | `reports/v3c3_build_checks.json` | `f5a16d4be277c90d089dbb04c9df6cfeec606849e942f55481c65ea074f35555` |
| repin 도구 교차 확인 | `reports/v3c3_repo_tool_check.json` | `e94ae14434ebf2b8e113eaeefabbf3c7031334e7d90538ea1499d3516a33e8a2` |
| prepare 검사 19개(전부 OK) | `reports/v3c3_prepare_checks.json` | `81be10264ac36afbdabf30afa4e916dcfb25a425bad5b60537f58291b1e5796b` |
| 발사 줄(발사 안 함) | `launch_lines_nc.txt` | `914ecfb8e513cc99ada15db4624b0b448e4f720fe76b4146454d882309882ddd` |
| **판정 도구** | `scripts/gb1_identity.py` | `6e19cad0bf403da6e286895e57705be3611d9c3f4bee0ef729ddafbc3b148c16` |
| **v3c2 기준값** | `reports/gb1_v3c2_reference.json` | `50b419293ed0b5a960e9840bb78f10135e97108a647599e1b28e43fa05954150` |

| 시드 | 역할 | v3c2 망 sha | v3c3 망 sha(= 계획 e3 의 메모리 재현) |
|---|---|---|---|
| 31 | fit | `597191ac…` | `3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e` |
| 41 | fit | `2b15d51e…` | `726af589bddb8c7267654bda446d2f1a4378451f51e1593857062fca0d32587e` |
| 43 | fit | `e11d19f2…` | `51478c397b3a2570fc2254a9fa8120a2415304942589f5fb5c2eb1b6858f2dda` |
| 47 | fit | `99689b7f…` | `1895ca30542cd50542a9376d5e3c77ff184d65a009d97dbe55a65f0b31bbced0` |
| 53 | fit | `c2dd1a48…` | `095fb7014cb750aee8ac1b071549fbc98eb48a8e57436bd0f01ac3d79a69248e` |
| 37 | 봉인 | `f6b0b7d6…` | `7edf0f7ad44a9ef630a2396e88938977533d8a45662e2c710665f7af5d131327` |

- 비교 대상은 v3c2 NC 같은 시드입니다: `D:/VISSIM_runs/20260930_v3c2/s<S>_v3c2nc`(읽기만 함).
- 두 망의 차이는 쓰이지 않는 분포 블록 3개(+655 B)뿐입니다. 그래서 같은 시드는 **짝**이고, 바이트 동일을 기대합니다. v3c1↔v3c2 처럼 망이 달라 20–35 s 만에 갈라지는 경우가 아닙니다.

## 1. 사전 노출

- v3c3 결과는 아직 없으므로 본 적이 없습니다.
- 이 선언을 쓰려고 v3c2 **fit 시드**(31/41/43/47/53) 출력에서 읽은 것은 다음뿐입니다 [실행].
  - (a) s31 FZP 의 머리 약 35줄(헤더 형식 확인용)
  - (b) 5개 FZP 의 전체 스트리밍 해시: payload sha, 가린 헤더 sha, 행 수. 내용 분석은 하지 않았습니다.
  - (c) `.err` 세 종류
    - sha256 과 크기
    - 경로·날짜 토큰 개수: `v3c2`, `VISSIM_runs`, 날짜·시각 패턴 모두 0
    - 본문은 읽지 않았습니다.
  - (d) fit 시드 `run.json`
  - (e) `reports/nc_analysis/eo/s<S>_v3c2nc_extraction_receipt.json` 의 fzp 필드
- 사전 근거로 N1F 2단계 `s41_c80f/g0.json` 도 읽었습니다: 2,700 s 까지 NC 와 FZP 가 같음(IDENTICAL) [읽음].
- **s37**
  - v3c2-s37 과 v3c3-s37 의 출력은 하나도 열지 않았습니다.
  - prepare 입력으로 v3c2-s37 의 `prepared.json`, `native_simulation.csv`, `vehicle_recording.csv`, `dryrun_check.txt` 만 읽었습니다. `prepared/network/` 와 `run/` 은 읽지도 훑지도 않았습니다.

## 2. 정의 (구속)

판정 도구는 `scripts/gb1_identity.py`(sha `6e19cad0…`)입니다. 아래 정의를 그대로 구현합니다.

### 2.1 FZP payload — 무엇을 빼는가
- 파일: `<run>/vissim_eval/baseline_s<S>_<tag>_001.fzp`. `vissim_eval/` 안의 `*.fzp` 는 정확히 이것 하나여야 합니다.
- **헤더(빼는 부분)**
  - 범위: 파일 첫 바이트부터, `$VEHICLE:` 로 시작하는 **첫** 줄의 끝(CR LF 포함)까지
  - v3c2 fit 5시드 모두 38줄, 4,028 B 입니다 [실행]
  - 여기에 망 경로를 담은 `* File: …` 줄과 실행 시각을 담은 `* Date: …` 줄이 들어 있습니다.
- **payload(비교하는 부분)**
  - 범위: 헤더 바로 다음 바이트부터 EOF 까지 전부
  - 기존 정의와 같습니다: `analyze_no_control_corridors.native_frames`(`D:/VISSIM-merge/sim3/diagnostics/analyze_no_control_corridors.py:94-141`, 파일 sha `f2379c33…`)가 `payload_sha256` 로 해시하는 바이트 [읽음]
  - 확인: 도구 값이 v3c2 추출 영수증 5개의 `payload_sha256`·`file_sha256`·`bytes`·`rows` 와 모두 같습니다 [실행]
- **가린 헤더(함께 비교)**
  - 헤더에서 `* File: ` 로 시작하는 줄과 `* Date: ` 로 시작하는 줄을 **정확히 하나씩** 지운 나머지입니다. 나머지는 바이트까지 같아야 합니다.
  - 이 나머지에 `$VISION`, `* Comment:`, `* PTV Vissim: 2020.00 [14]`(빌드), 표·열 설명, `$VEHICLE:` 열 목록 줄이 들어 있습니다.
  - v3c2 fit 5시드의 값은 모두 `412835b501ef…` 로 같습니다.
- **File 줄 양성 확인**
  - v3c3 런의 `* File: ` 줄은 정확히 `* File: D:\VISSIM_runs\20261001_v3c3\s<S>_v3c3nc\prepared\network\baseline_s<S>_v3c3nc.inpx` 여야 합니다.
  - 그래야 런이 v3c3 파일을 불러왔다고 말할 수 있습니다.

### 2.2 `.err` (검토 N9)
- 아래 셋이 v3c3 와 v3c2 같은 시드에서 바이트가 같아야 합니다.
  - `ERR_LOAD`: `run/<net>.err`. 로드 경고이고, v3c2 는 5시드 모두 200 B `d1ee825c…`
  - `ERR_SIM`: `run/<net>_001.err`. 시뮬 경고·차량 번호가 들어 있고 약 300 KB
  - `ERR_DLL`: `prepared/network/VISSIG_Controller.dll.err`. v3c2 는 464 B `f144ab0c…`
- `ERR_COPIES`: 각 런 안에서 `prepared/network/<net>.err` 와 `<net>_001.err` 가 run/ 사본과 같아야 합니다.
- 세 파일에는 경로나 시각이 없어서, 파일 이름이 달라도 내용을 바이트로 비교할 수 있습니다 [실행 토큰 0].

### 2.3 run.json
- `RUN_JSON_V3C3`(v3c3 런), `RUN_JSON_V3C2`(v3c2 런) 모두 아래를 만족해야 합니다.
  - `completed` true, `error` null, `exit_code` 0
  - `terminal_sec` = `requested_terminal_sec` = 9000
  - `seed` = S, `network` = 그 런의 prepared 망
  - `native_preserve` true, `fzp_only` true, `owned_native_alive` false
  - `native_files` = [`<net>_001.fzp`], `error_files` = [`<net>.err`, `<net>_001.err`]

### 2.4 전제 조건 — 하나라도 깨지면 비교는 무효입니다. 차이를 망 탓으로 돌리지 않습니다
- `RUNNER_SHA`: 두 run.json 의 `runner_sha256` 이 서로 같고, `bf07acdaaa678d764ccbd0fd237a5aad85c3419f0628790358dd478ffc5e2cf1` 이어야 합니다.
- **VISSIM 빌드**
  - FZP 헤더의 `* PTV Vissim: 2020.00 [14]` 줄이 같아야 합니다. 이 줄은 가린 헤더에 포함됩니다.
  - `ENVIRONMENT_UNCHANGED`: 판정 시점의 `VISSIM200.exe` 가 선언 때와 같아야 합니다. FileVersion `2020.00-14`, sha256 `c6f549cf5778c33e377023e2bbed346a6361414f9b91656b78847708953cf2de`, 3,712,000 B.
  - 같은 항목에서 sim3 러너 3개의 핀도 확인합니다: prepare `eb1bd0f0…`, run.ps1 `269345da…`, vbs `bf07acda…`
- `NETWORK_PIN`: 각 런의 prepared 망 sha 가 영수증과 같아야 합니다. v3c3 는 §0 표, v3c2 는 `v3c2_edit_receipt.json`.
- `V3C2_UNCHANGED_SINCE_DECLARATION`(fit 시드만): 판정 시점의 v3c2 값이 `gb1_v3c2_reference.json` 과 같아야 합니다. 대상은 payload, 가린 헤더, `.err`, run.json 필드입니다.

## 3. 판정

### 3.1 fit 5시드(구속, U2-a)
- 명령: `python -B scripts/gb1_identity.py judge --seed <S>`
  - 결과는 `reports/gb1_result_s<S>.json` 에 씁니다. 해시를 출력합니다.
- 통과: 위 항목 13개가 모두 참이어야 합니다.
  - RUN_JSON_V3C3, RUN_JSON_V3C2, RUNNER_SHA, NETWORK_PIN, FZP_PAYLOAD, FZP_HEADER_MASKED, FZP_FILE_LINE
  - ERR_LOAD, ERR_SIM, ERR_DLL, ERR_COPIES
  - V3C2_UNCHANGED_SINCE_DECLARATION, ENVIRONMENT_UNCHANGED
- 기대값(v3c2, 고정) [실행 `gb1_v3c2_reference.json`]:

| 시드 | FZP payload sha256 | payload 행 | ERR_SIM sha256 |
|---|---|---:|---|
| 31 | `8be8b27411a9583c8597911be59fb74ddd3e8eb49e53b63e1a4579c6aea9fbf6` | 6,654,249 | `ff32fdd445b6d195…` |
| 41 | `cc8fb77b10506e844cee8a67d25485528c8a388c5baf555f25d2c9205e87c414` | 6,982,614 | `0e390798328f87fc…` |
| 43 | `ddd835236034aee8a2e83aff6c7fde77dab6bd98577c2353926f503f8544593c` | 6,829,846 | `4a83fcf5d027eb47…` |
| 47 | `daf99b101797bde3bb4ac3a72544a21869ebf7cdc3e143de3552ccc036eece14` | 6,631,530 | `937163bb03cca8b5…` |
| 53 | `72385aa56163e46ff01f75088c24557b635f90ce32fbb49fbca4cd6cb8330cd4` | 6,850,613 | `3f0088c358699f06…` |

- 공통값: ERR_LOAD `d1ee825c…`, ERR_DLL `f144ab0c…`, 가린 헤더 `412835b501ef…`

### 3.2 봉인 s37(U2-c, 해시 전용)
- 명령: `python -B scripts/gb1_identity.py sealed`
  - 메모리 안에서 v3c3-s37 과 v3c2-s37 을 같은 항목으로 비교합니다. 단 V3C2_UNCHANGED 는 없습니다. 고정 기준값을 만들면 봉인을 여는 것이기 때문입니다.
- 출력
  - 형식: `<항목>: <단어>` 줄뿐입니다. 단어는 EQUAL / DIFFERENT / MISSING / ERROR / OK / NOT_OK / PASS / FAIL 가운데 하나입니다.
  - 마지막 줄은 `GB1_S37: PASS|FAIL` 입니다.
  - 해시·크기·행 수·경로·예외 문구·내용은 출력하지도 저장하지도 않습니다. 예외는 문구 없이 ERROR 로만 바뀝니다.
  - `reports/gb1_result_s37_sealed.json` 에도 같은 단어만 저장합니다.
- 자체 시험 [실행]: 합성 사례 11개(`selftest`)에서 판정이 기대와 같았습니다. 봉인 출력이 단어 줄뿐이고 8자 이상 16진 문자열이 없음도 확인했습니다.
- 메인 세션은 s37 의 run.json 에서 `completed`·`exit_code` 두 필드만 읽습니다. 다른 s37 출력은 열지 않습니다.
- 공개: 검토 N19 는 이 도구를 **허용하지 않기**를 권했습니다. 계획 U2-c 권고와 2026-10-01 승인은 허용입니다. 이 선언은 승인을 따릅니다.
  - 사용자가 N19 를 택하면 `sealed` 를 돌리지 않습니다. 그때 s37 은 run.json 두 필드로만 확인하고, §3.3 의 s37 조건은 "completed true·exit_code 0" 으로 대체합니다.
  - 이 대체는 s37 결과를 보기 전에만 할 수 있습니다.

### 3.3 GB-1 전체
- 명령: `python -B scripts/gb1_identity.py verdict` → `reports/gb1_verdict.json`
- **GB-1 PASS = fit 5시드 모두 PASS 그리고 s37 봉인 판정 PASS** 입니다.
  - s37 을 구속에 넣은 이유: s37 NC 는 RM s37 의 짝입니다. 같은 망 변경이 s37 에서만 궤적을 바꿨다면 그 짝도 의심해야 합니다.
- 판정 순서: 런마다 끝나는 대로 `judge` 를 돌려도 됩니다. 판정 결과는 다른 런의 발사·감시에 쓰지 않습니다.

## 4. 실패하면 (계획 §2.4·§5.3)
- **STOP 합니다.**
  - 재핀 K7 파생(RA-1 추출 등), RM 팔, R-obs 는 발사하지도 시작하지도 않습니다.
  - 떨어진 항목과 시드를 그대로 보고하고 사용자 결정을 받습니다(위험 R1: v3c3 NC 5런을 새 기준으로 삼을지).
- 전제 조건 항목(RUNNER_SHA, ENVIRONMENT_UNCHANGED, NETWORK_PIN, V3C2_UNCHANGED_SINCE_DECLARATION, RUN_JSON_V3C2)이 떨어지면, 그 비교는 망 효과의 증거가 아닙니다. 원인을 따로 보고합니다.
- s37 이 FAIL 이어도 내용은 열지 않습니다. 단어 판정만 보고하고, 봉인 해제는 사용자가 정합니다.
- 런이 비정상 종료하면(`RUN_JSON_V3C3` NOT_OK) 감시 정책대로 소유 PID 만 정리하고 다시 띄울 수 있습니다. 판정은 완료된 런으로만 합니다. 다시 띄운 사실은 결과에 적습니다.

## 5. 이 선언을 바꿀 때
- v3c3 런이 하나라도 시작된 뒤에는 이 파일을 바꾸지 않습니다.
- 바꿀 일이 생기면 `reports/AMENDMENT_gb1.md` 에 적습니다: 바뀐 부분, 이유, 결과를 본 전인지 뒤인지, 새 sha.
- 결과를 본 뒤 바꾼 기준은 판정에 쓰지 않습니다. 원래 선언으로 낸 판정을 함께 보고합니다.

## 6. 기대 [추론]
- 모든 항목이 EQUAL/OK 일 것으로 봅니다. 근거는 세 가지입니다.
  - 새 분포 81/91/101 은 정적 요소가 하나도 참조하지 않습니다 [실행]. NC 런은 분포 번호를 쓰지 않습니다.
  - N1F 는 v3b 에 같은 블록을 넣은 8런에서, 첫 VSL 명령 전(2,700 s)까지 NC 와 FZP 가 같았습니다(G0 8/8) [읽음].
  - 그러나 9,000 s 전체에서 확인한 적은 없습니다. 그래서 이 관문이 필요합니다.
