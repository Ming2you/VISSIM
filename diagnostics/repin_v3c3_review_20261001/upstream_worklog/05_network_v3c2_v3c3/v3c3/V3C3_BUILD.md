# 망 v3c3 구축·prepare·GB-1 사전 선언 보고 (2026-10-01)

- 표기: **[실행]** 이번에 명령으로 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단
- 경로 기준: `D:/VISSIM_runs/20261001_v3c3/`
- 근거
  - 사용자 승인(2026-10-01): `D:/VISSIM_runs/20260930_v3c2/reports/repin/REPIN_V3C2_PLAN.md`(sha `d4b70c02…`)의 U1–U12 권고값
  - 검토 수정: `REPIN_V3C2_PLAN_REVIEW.md`(sha `bc08f3df…`)
  - 이번 단계에 해당하는 절: 계획 §2.2–2.4, GB-0·GB-1, 검토 N8·N9·N12·N19·N20

## 요약

1. **v3c3 를 깨끗하게 만들었습니다(STOP 아님).** v3c2 대비 바뀐 곳은 분포 블록 3개 삽입뿐입니다 [실행 `reports/v3c3_build_checks.json`, 검사 21개 모두 참].
   - 분포 80/90/100 을 닫는 행 바로 뒤, 즉 v3c2 5000/5015/5025 행 앞에 81(80–82)·91(90–92)·101(100–102)을 넣었습니다.
   - 크기는 217/217/221 B, 합계 +655 B, +18 행입니다. 그 밖의 바이트는 같습니다.
2. **블록 바이트가 N1F 2단계 망과 같습니다.**
   - 비교한 파일: N1F 2단계 망 16개(4시드 × 2팔 × source/prepared). 1단계 망 8개의 분포 91 도 같습니다.
   - N1F 자체도 N1 망에 같은 오프셋(805021/805613/806042)·같은 행에 순수 삽입한 것입니다. 블록을 빼면 N1 망과 바이트가 같습니다 [실행].
3. **여섯 시드의 sha 가 계획의 메모리 재현(e3)과 모두 같습니다.** s31 은 `3de889f0…` 입니다. 시드 파일끼리는 randSeed 행(31013 = 30995 + 18)만 다릅니다 [실행].
4. **repin 도구로 교차 확인했습니다** [실행 `reports/v3c3_repo_tool_check.json`]. 저장소 HEAD `9ed2ef0`, porcelain 0줄은 실행 전후 같았습니다.
   - `section_diff`: desSpeedDistributions 에 81/91/101 이 추가된 것 하나뿐입니다.
   - `added_block_audit`: v3c1 결정 블록(1159 뒤 9293 B, `2b77ab01`)이 그대로입니다(검토 N20).
   - `runner_config_check`(81,91,101,110): v3c3 는 통과하고, v3c2 는 `[81, 91, 101]` 부재로 거부합니다.
5. **prepare 와 건식 점검이 여섯 시드 모두 통과했습니다** [실행 `reports/v3c3_prepare_checks.json`, 19개 OK].
   - 러너 프로필은 v3c2 NC 와 같습니다: SimRes 10, FZP 전용 5 s, 9000 s, 수요 쓰기 없음.
   - `launch_lines_nc.txt` 를 만들었고 **발사는 하지 않았습니다.**
6. **GB-1 을 런 전에 동결했습니다.** `reports/gb1_predeclaration.md`, sha `02457383…`, 10:25:14 KST.
   - 판정 도구 `scripts/gb1_identity.py`(sha `6e19cad0…`)와 v3c2 기준값 `reports/gb1_v3c2_reference.json`(sha `50b41929…`)을 함께 고정했습니다.
   - 도구의 payload 정의는 기존 추출 영수증 5개의 payload·file sha·행 수를 그대로 재현합니다 [실행].

## 1. 입력과 고정값 [실행]

| 입력 | 경로 | sha256 |
|---|---|---|
| v3c2 망 6개 | `D:/VISSIM_runs/20260930_v3c2/source/baseline_s<S>_v3c2nc.inpx` | 영수증과 같음 (s31 `597191ac…`) |
| v3c2 영수증 / 정적 검사 | `…/20260930_v3c2/v3c2_edit_receipt.json`, `reports/v3c2_build_checks.json` | `cf8b0cb2…` / `5961e92c…` |
| v3c2 스크립트(틀) | `…/20260930_v3c2/scripts/v3c2_build.py`, `v3c2_prepare.py` | `5dae8984…` / `b91153fc…` |
| N1F 2단계 계획(`dsd_blocks`) | `D:/VISSIM_runs/20260928_n1f_vsl_stage2/plan/n1f_plan_stage2_v1.json` | `d0e8fdba…` |
| N1F 1단계 계획 | `D:/VISSIM_runs/20260928_n1f_vsl/plan/n1f_plan_v1.json` | `3e27ac15…` |
| N1F 2단계 망 16개 | `…_stage2/s{41,43,47,53}_{c100f,c80f}/{source,prepared/network}/n1f2_*.inpx` | 계획의 `n1f2_sha256` 과 같음 (s41 `ea59687a…`) |
| N1 망(N1F 의 바탕) | `D:/VISSIM_runs/20260927_n1_vsl/s<S>_c100/source/n1_s<S>_c100.inpx` | 계획의 `n1_sha256` 과 같음 |
| 예상 sha | `…/20260930_v3c2/reports/repin/_evidence/e3_v3c3_preview.json` | `7bcafd84…` |

- v3c2 쪽 사실
  - 분포 44개이고, 81/91/101 은 비어 있습니다.
  - 분포 번호를 가리키는 속성은 `desSpeedDistr` 하나뿐입니다(`vehClassDesSpeedDistribution`, `vehicleCompositionRelativeFlow`, `pedestrianCompositionRelativeFlow`). 그 값 가운데 80/90/100/110 대역에 드는 것은 110 뿐입니다(304 + 3).
  - v3c2 와 N1 s41 은 처음 842,780 B(5,405 행)가 같습니다. 그래서 세 삽입 지점의 앞뒤 문맥이 N1F 와 바이트 단위로 같습니다.

## 2. 무엇을 바꿨나 (`v3c3_edit_receipt.json`, sha `b1bd1fd5…`)

| 분포 | 점(fx, x) | 바이트 | 블록 sha256 | v3c2 오프셋 / 행 앞 | v3c3 행 |
|---|---|---:|---|---|---|
| 81 "81 km/h" | (0, 80), (1, 82) | 217 | `ae06360d…` | 805021 / 5000 (80 뒤, 85 앞) | 5000–5005 |
| 91 "91 km/h" | (0, 90), (1, 92) | 217 | `fbb7066f…` | 805613 / 5015 (90 뒤, 100 앞) | 5021–5026 |
| 101 "101 km/h" | (0, 100), (1, 102) | 221 | `f3d776c2…` | 806042 / 5025 (100 뒤, 110 앞) | 5037–5042 |

- 영수증 `edits.desSpeedDistributions_inserted` 에 각 블록의 정확한 텍스트와 16진 바이트(`hex`), 오프셋, 행을 적었습니다.
- 편집 방식: 바이트 보존 텍스트 삽입(`scripts/v3c3_build.py` `text_insert`)입니다. XML 을 다시 직렬화하지 않았습니다.
- 바꾸지 않은 것: 수요, 경로, 구성(14 포함), 입력 1098/1099, 기하, 신호, 검지기, desSpeedDecision, 시드, DSD 110(98–140)

| 시드 | 역할 | v3c2 sha | v3c3 sha | e3 예상과 같음 |
|---|---|---|---|---|
| 31 | fit | 597191ac | **3de889f0** | 예 |
| 41 | fit | 2b15d51e | 726af589 | 예 |
| 43 | fit | e11d19f2 | 51478c39 | 예 |
| 47 | fit | 99689b7f | 1895ca30 | 예 |
| 53 | fit | c2dd1a48 | 095fb701 | 예 |
| 37 | 봉인 | f6b0b7d6 | 7edf0f7a | 예 |

## 3. 검증 [실행]

### 3.1 구성법 네 가지가 여섯 시드 모두 바이트까지 같습니다
- (a) 계획 JSON 블록 텍스트를 삽입
- (b) ElementTree 편집: N1F 2단계 망(같은 시드, s31·s37 은 s41)의 파싱 트리에서 요소를 깊은 복사해 80/90/100 뒤에 넣음
- (c) s31 v3c3 의 randSeed 교체
- (d) N1F 망 파일에서 잘라낸 블록 바이트를 삽입

### 3.2 차이
- 행 단위
  - 예상 행 목록과 정확히 같습니다. 5000/5015/5025 행 앞에 6행씩 넣은 것과 같습니다.
  - `difflib` 는 삽입 18행, 삭제 0 입니다.
  - 주의: `difflib` 는 101 블록을 5023 행 앞에 넣은 것처럼 정렬합니다. 블록 끝 두 줄이 앞 분포의 닫는 두 줄과 같아서 생기는 표시상 모호함입니다. 위치 판정은 예상 행 목록 비교로 합니다.
- 통합 diff 는 `+18 −0`, 세 덩어리입니다(`reports/v3c3_vs_v3c2_s31.diff`, `e2154c7d…`).
- 바이트 단위: v3c3 에서 삽입 구간 세 개를 빼면 v3c2 와 바이트가 같습니다. +655 B 입니다.

### 3.3 분포와 절
- 분포가 44 → 47 개가 됐습니다.
  - 순서는 80, **81**, 85 / 90, **91**, 100 / 100, **101**, 110 입니다.
  - 새 요소의 이름·점·속성 순서(name, no)가 계획과 같습니다.
  - 기존 44개는 ElementTree 로 v3c2 와 같습니다.
- 최상위 절 46개 가운데 다른 것은 `desSpeedDistributions` 하나입니다.
- 역편집 확인: ElementTree 로 81/91/101 을 지우고 직렬화하면 v3c2 와 바이트가 같습니다.
- 정적 참조
  - 81/91/101 을 가리키는 `desSpeedDistr` 속성은 0개입니다.
  - 110 참조 307개와 속성 이름 집합은 그대로입니다.
- 번호 겹침(검토 N12)
  - desSpeedDecision 81/91/101(FW_W)은 새 분포와 번호가 같습니다. 종류가 다른 객체이고 바뀌지 않았습니다.
  - CSV 에서 `dsd_no=91,…,speed_kph=91` 처럼 보일 수 있다는 점은 K5/CONTRACT 쪽 몫입니다.
- 왕복 확인: ElementTree 왕복과 `fzp_only` 재작성이 항등입니다. 그래서 prepared 스냅샷이 원본과 바이트가 같습니다.
- 재파싱(`netv3_common.parse_inpx`)
  - 결정 138개, 링크, simulation 속성이 같습니다.
  - 결정과 링크의 위치는 모두 (+18 행, +655 B) 만큼 밀렸습니다. simulation 행은 30995 → 31013 입니다.

### 3.4 N1F 동일성
- N1F 2단계 16개 파일에서 확인한 것
  - 81/91/101 블록 바이트 = 계획 블록
  - 파일 sha = 계획
  - 블록을 빼면 N1 망
  - 삽입 오프셋 [805021, 805613, 806042]·행 [5000, 5015, 5025] = 계획 = v3c3
- N1F 1단계 8개 파일의 분포 91 블록은 2단계 블록 91 과 같습니다(계획의 "stage-1 91 과 바이트 동일" 주장 확인).

### 3.5 repin 도구 교차 확인 (`scripts/v3c3_repo_tool_check.py`)
- 대상: `D:/VISSIM-merge/sim3-n31-v3c1` @ `9ed2ef0`의 `repin_scenario_v2.py`(`3859e22d…`)
  - `python -B` 로 읽기 전용 import 했습니다. e1 증거와 같은 방식입니다.
  - git HEAD, porcelain, 가져온 저장소 모듈 2개의 .pyc 상태가 실행 전후 같았습니다.
- 여섯 시드 모두 R1–R3 통과입니다.
- R4(대조) `characterize_changes(fcb349d3 → v3c3)` 는 vehicleCompositions 때문에 거부됩니다. 계획 §0-2 그대로이고 K7 의 열거표가 풀 일입니다.
  - 검토 N8: CHANGE_RULES 의 `desSpeedDistributions: added` 를 열거로 좁히는 것도 K7 몫입니다. 이번 단계는 도구를 바꾸지 않았습니다.

### 3.6 계획 GB-0 항목 대응

| GB-0 항목 | 결과 |
|---|---|
| 순수 삽입 18줄 | 통과 (3.2) |
| 블록 바이트·sha = N1F 계획 | 통과 (3.4) |
| 분포 44 → 47, 새 번호는 이전에 없던 것, 정적 참조 0 | 통과 (3.3) |
| 순서 80,81,85 / 90,91,100 / 100,101,110 | 통과 |
| 시드 간 randSeed 한 줄 | 통과 (31013 행) |
| ET 왕복·fzp_only 재작성 항등 | 통과 |
| sha = §2.3 표 | 통과 (6/6) |
| prepared 미러 키가 v3c2 와 같음 | 통과 (4) |
| 드라이런 exit 0 | 통과 (6/6, 발사 형식 포함) |
| (N20) v3c3 후보의 `added_block_audit` | 통과 (3.5) |

- 다시 확인했습니다: `v3c3_build.py recheck` → ok = True(`work/v3c3_build_recheck_20261001T101229.json`).

## 4. prepare·건식 점검·발사 줄 [실행]

- `scripts/v3c3_prepare.py` 는 `v3c2_prepare.py`(`b91153fc…`)에서 파생했습니다. 경로·태그·영수증·변형 이름만 바꿨습니다.
  - prepare 호출: `fast_nc_prepare.prepare_native_preserve(net, out, 9000, recording_interval_sec=5, fzp_only=True)`
  - 러너 sha 는 v3c2 NC 와 같습니다: prepare `eb1bd0f0…`, run.ps1 `269345da…`, vbs `bf07acda…`. v3c2 fit 5시드 run.json 의 `runner_sha256` 도 모두 `bf07acda…` 입니다.
- **같은 시드 v3c2 prepared.json 과의 대조**(v3c2 prepare verify 가 기록한 sha 로 고정)
  - mirror 키 12개가 같습니다: simRes 10, simPeriod 9001, 기록 5 s, fzp_only, terminal 9000, demand_rows 0 등.
  - `native_simulation.csv`·`vehicle_recording.csv` 의 바이트와 자산 43개가 같습니다.
  - 다른 키는 경로·sha·변형 이름 7개뿐입니다. 경로와 sha 를 바꿔 넣으면 network_variant 를 빼고 전부 같습니다.
  - `network_variant.base_variant` 에는 v3c2 의 기록 사슬을 그대로 넣었습니다.
- **건식 점검**(`-Execute` 없이, 발사 형식 명령도 함께)
  - 여섯 시드 모두 exit 0 입니다.
  - v3c2 `dryrun_check.txt` 와 다른 필드는 `arguments` 뿐입니다.
  - `run\` 이나 `launch.log` 는 생기지 않았습니다.
- 스크래치패드 리허설(`scratchpad/v3c3/prep_rehearsal`)도 같은 19개가 모두 OK 였습니다. 리허설 사본은 그대로 두었습니다.
- **`launch_lines_nc.txt`**(sha `914ecfb8…`)
  - 순서: 묶음 A = s31, s41, s43, s47(좌석 4), 묶음 B = s53, s37
  - 각 줄은 v3c2 `launch_lines_nc.txt` 같은 시드 줄에서 경로만 바꾼 것과 같습니다(검사로 확인).
  - WMI `Invoke-CimMethod … Win32_Process Create`, CurrentDirectory `D:\VISSIM_runs\20261001_v3c3`
- 경계 확인
  - 읽은 v3c2 파일(영수증, prepare 검사·스크립트, 발사 줄, 망 6개, prepared.json 6개, dryrun 6개)의 sha 가 바뀌지 않았습니다.
  - v3c2 트리 676개 파일(s37_* 제외) 가운데 v3c3 영수증 뒤에 바뀐 것은 0개입니다.
  - sim3 러너 파일은 바뀌지 않았고, `scripts/` 에 `__pycache__` 가 없습니다.
  - 보고 직전에 다시 확인했습니다: v3c2·v3c1·N1F 두 루트·N1 루트에서 10:05 이후 바뀐 파일 0개, v3c1 작업 트리 porcelain 0줄.

## 5. GB-1 사전 선언 (`reports/gb1_predeclaration.md`, sha `024573832b232763dd2f910e1d1eac5ba4a82da110b3a3e5cbb797dd9cb17929`, 해시 파일 `gb1_predeclaration.md.sha256`)

- **payload 정의**
  - 빼는 부분: FZP 의 처음부터 `$VEHICLE:` 로 시작하는 첫 줄 끝(CR LF 포함)까지. v3c2 기준 38줄, 4,028 B 입니다.
  - 이 헤더에 `* File: <망 경로>` 줄과 `* Date: <시각>` 줄이 들어 있습니다.
  - 비교하는 부분: 그 뒤 EOF 까지 전부. 기존 `native_frames` 의 `payload_sha256` 과 같은 바이트입니다.
- **가린 헤더**: 헤더에서 File·Date 두 줄만 지우고 나머지를 바이트로 비교합니다. VISSIM 빌드 줄 `* PTV Vissim: 2020.00 [14]` 도 여기 들어갑니다.
- **File 줄 양성 확인**: v3c3 런은 v3c3 prepared 망을 불러와야 합니다.
- **.err(N9)**: `run/<net>.err`, `run/<net>_001.err`, `prepared/network/VISSIG_Controller.dll.err` 가 v3c2 같은 시드와 바이트가 같아야 합니다. prepared 사본도 run/ 사본과 같아야 합니다.
- **run.json**: completed, exit 0, 9000 s 등이 맞아야 합니다.
- **전제 조건**(깨지면 비교 무효, STOP)
  - `runner_sha256` = `bf07acda…` 이고 v3c2 와 같음
  - VISSIM200.exe FileVersion `2020.00-14`, sha `c6f549cf…`
  - 망 핀, v3c2 기준값 불변
- **판정 범위**
  - fit 5시드 모두(U2-a): `judge --seed S`
  - 봉인 s37(U2-c): `sealed`. 출력은 단어뿐입니다. 자체 시험 11사례에서 단어 줄뿐이고 16진 문자열이 없음을 확인했습니다.
  - GB-1 PASS = 6/6 PASS 입니다.
- **실패하면** STOP 합니다. 재핀·RM·R-obs 를 발사하지 않고 사용자에게 보고합니다.

## 6. 공개와 주의

- **U2-c 와 검토 N19 가 다릅니다.**
  - N19 는 s37 해시 도구를 허용하지 않기를 권했습니다. 계획 U2-c 권고와 승인 지시는 허용입니다.
  - 선언은 허용을 따르고 출력을 단어로 제한했습니다.
  - 사용자가 N19 를 택하면 `sealed` 를 돌리지 않습니다. 그때 s37 판정은 run.json 두 필드로 대체하며, s37 결과를 보기 전에만 바꿀 수 있습니다(선언 §3.2).
- **s37 을 GB-1 구속에 넣었습니다.** 계획 표는 s37 을 run.json 확인으로 적었습니다. U2-c 허용에 따라 해시 판정도 구속으로 했습니다. 이유는 RM s37 의 짝이기 때문입니다.
- **같은 루트를 쓰는 다른 세션이 있습니다.** `reports/k1k6/`(GA 사전 선언 등)은 10:11 에 다른 세션이 만든 것입니다. 이 단계는 그 폴더를 읽지도 고치지도 않았습니다.
- **경계 검사 규칙을 바꿨습니다.** v3c2 의 경계 검사는 부모 트리 전체의 새 파일을 실패로 봤습니다. 이번에는 `20260930_v3c2/reports/` 아래 새 파일을 정보로만 기록합니다. 다른 세션이 분석을 거기에 쓰기 때문입니다. 이번 실행에서 해당 파일은 0개였습니다.
- **사전 노출.** 선언 §1 에 적은 v3c2 fit 시드 출력을 읽었습니다.
  - FZP 머리 약 35줄
  - 전체 FZP 스트리밍 해시
  - .err 의 sha 와 토큰 수
  - run.json
  - 추출 영수증
- **s37**
  - v3c2-s37 과 v3c3-s37 의 출력은 열지 않았습니다.
  - prepare 입력(prepared.json, csv 2개, dryrun_check.txt)만 읽었습니다. `s37_*` 폴더는 훑지 않았습니다.
- **하지 않은 것**
  - VISSIM·cscript 시작이나 종료, 발사, git 쓰기, 커밋, 저장소·작업 트리 코드 변경, `D:/VISSIM-merge/frozen/*` 접근
  - 금지 시험 7종 실행, s37/59/61/67 결과 열람
- Python 은 모두 `-B` 와 BELOW_NORMAL(0x4000, 되읽기 확인)로 돌렸습니다. 기존 런 폴더에는 쓰지 않았습니다(루트 가드, 경계 확인).

## 7. 파일

| 파일 | sha256 (앞 16자) |
|---|---|
| `scripts/v3c3_build.py` | 0f56347fe23b9049 |
| `scripts/v3c3_prepare.py` | 0642d8fdc1b1cf16 |
| `scripts/v3c3_repo_tool_check.py` | d7082f8f76ac5f56 |
| `scripts/gb1_identity.py` | 6e19cad0bf403da6 |
| `scripts/v3c_lib/netv3_common.py`, `v3c_checks.py` (v3c2 바이트 사본) | 88c6c5565d255a42, cc3fc895d65140bd |
| `v3c3_edit_receipt.json` | b1bd1fd5d6b80ce9 |
| `reports/v3c3_build_checks.json` | f5a16d4be277c90d |
| `reports/v3c3_vs_v3c2_s31.diff` | e2154c7ddbfdbf6a |
| `reports/v3c3_repo_tool_check.json` | e94ae14434ebf2b8 |
| `reports/v3c3_prepare_checks.json` | 81be10264ac36afb |
| `reports/gb1_v3c2_reference.json` | 50b419293ed0b5a9 |
| `reports/gb1_predeclaration.md` (+ `.md.sha256`) | 024573832b232763 |
| `launch_lines_nc.txt` | 914ecfb8e513cc99 |
| `source/` | 망 6개 + 자산 43개(v3c2 바이트 사본) |
| `s<S>_v3c3nc/prepared/`, `s<S>_v3c3nc/dryrun_check.txt` | 여섯 시드 |
| `work/` | 단계 기록, recheck |

## 8. 다음 단계 (메인 세션)

1. 다른 VISSIM 이 0개인지 확인합니다. 그다음 `launch_lines_nc.txt` 묶음 A(s31, s41, s43, s47)를 WMI 로 발사합니다.
2. 좌석이 비면 묶음 B(s53, s37)를 발사합니다. 발사 전에 각 시드에 `run\`·`launch.log` 가 없고 D: 여유가 8 GiB 이상인지 봅니다.
3. fit 시드가 끝날 때마다 `python -B scripts/gb1_identity.py judge --seed <S>` 를 돌립니다.
4. s37 이 끝나면 run.json 의 `completed`·`exit_code` 만 읽고 `python -B scripts/gb1_identity.py sealed` 를 돌립니다.
5. 마지막으로 `python -B scripts/gb1_identity.py verdict` 를 돌립니다. PASS 면 계획 P4(RM 빌드)와 K7 파생(RA-1)으로 갑니다. FAIL 이면 STOP 하고 사용자에게 보고합니다.
