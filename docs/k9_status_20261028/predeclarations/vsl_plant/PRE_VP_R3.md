# PRE_VP_R3 — 고침 r3 (데이터 뒤) : R1 목적값 허용 · 큐 멈춤 점검 · 바깥 핀 (2026-10-27 KST)

- **데이터 뒤 고침입니다.** 탐침 자료 일부가 나온 뒤에 사용자 결정으로 고칩니다(§4 에 그때까지 나온 자료를 적음).
- 정본 관계: 이 문서는 `VP/PRE_VP_FIXED.md`(r2, sha256 `33e71ac36b316e702006b2259ab7438233382de78a172b2f2340be813d7755f1`)를 **아래 §1 의 여섯 곳에서만** 바꿉니다. 나머지는 r2 그대로 정본입니다. 둘이 다르면 이 문서가 앞섭니다.
- 근거: 사용자 결정 D-K9-108·109 (`SP/K9_1_J1_NOTES_20261013.md` sha256 `64f202943502971c686de485c903c4d5ca2d58d0f2d5153fbd8a4de9827c1753`, 361–367 줄) [실행 sha 다시 셈]. 멈춤 보고 `VP/P1_REPORT.md`(c28c9178…), `VP/QV3_REPORT.md`(7e196d9f…), 멈춤 표지 `VP/STOP_VP`(ebd85663…).
- 표시: **[실행]** 돌려서 확인 · **[읽음]** 파일·코드를 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 산술. 판정 낱말은 쓰지 않습니다.
- 경로 줄임(r2 와 같음): SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, VP = `SP/vsl_plant`, GT = `D:/VISSIM-merge/k8_gate_trees/vsl_plant`, RVP = `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant`.

## 0. 줄임말 (처음 한 번)

- R1 = 기록된 선택 계획을 AD 경로(미분을 함께 내는 작업자 굴림)로 다시 굴려, 목적값 J 와 소유자별 비용 20개를 결정 기록과 대조하는 점검(PRE_VP_FIXED §3.4). S-R1 = R1 이 어긋날 때의 멈춤 규칙.
- ULP = 그 크기의 부동소수점 수에서 마지막 자리 한 칸. 428.7 근처에서 1 ULP = 5.68 × 10⁻¹⁴ [계산].
- STOP_VP = 멈춤 규칙에 걸리면 큐가 쓰는 표지 파일. 큐는 이 파일이 있으면 다음 일을 하지 않습니다.
- 잠금 = 무거운 일을 차례로 돌리려고 여러 워크플로가 함께 쓰는 배타 파일 `D:/VISSIM-merge/k8_gate_trees/heavy.lock`.
- 핀 = 도구·선언 파일의 sha256 목록. VP 핀 = VP 안 상대 경로 목록, EXT 핀(바깥 핀) = VP 밖 절대 경로 목록.
- `code_va.tree.json` = 코드 사본(GT/code_va)이 동결 트리와 같은지 대조한 기록. H0(`vp_tree.py verify`)가 돌 때마다 새로 써집니다.

## 1. 바꾼 것 (이것뿐)

| # | 결정 | r2 (PRE_VP_FIXED) | r3 (이 문서) | 도구 |
|---|---|---|---|---|
| X1 | D-K9-108 | §3.4 R1: 목적값은 기록과 **비트까지 같음**, 비용 20개는 차 ≤ 1e-9 veh·h. §7 S-R1 도 같은 뜻 | R1: 목적값도 **\|재생 − 기록\| ≤ 1e-9 veh·h** (비용과 같은 허용). 비용 규칙은 그대로(키 같음 + 차 ≤ 1e-9). 목적값 비트 같음은 `R1_objective_bit_equal` 로 계속 적지만 **보고만**(R0 처럼). 재현 확인 런은 하지 않음(사용자 결정) | `vp_probe.py`, `vp_jobcheck.py` |
| X2 | D-K9-109 (1) | — | v3c3-s31 T = 3,450 (탐침 A 의 A2 상태)은 STOP_VP(17:49:46) 뒤 17:50:05 에 시작했음(+19 s). 그 일의 점검은 모두 통과 [실행 읽음 `jobcheck.json` e9e913f6… 걸림 0]. **표시하고 그대로 씀**: 보고·표에서 이 상태 줄에 "STOP_VP 뒤 시작(+19 s), D-K9-109 (1)" 을 붙임. 기계용 기록 `decl/R3_MARKS.json` | (선언 파일) |
| X3 | D-K9-109 (2) | 큐는 잠금을 기다리기 **전에만** STOP_VP 를 봄(`vp_queue_r2.py`:38–47) | 큐는 잠금을 잡은 **바로 뒤에도** STOP_VP 를 봄. 있으면 잠금을 풀고, 일을 돌리지 않고, `.done` 을 쓰지 않고 멈춤 | `vp_queue.py` |
| X4 | D-K9-109 (3) | EXT 핀에 `GT/code_va.tree.json` 의 sha(53e4403f…, 16:16 기록) 한 줄 | 그 줄을 EXT 핀에서 뺌(시각 칸 `checked_kst` 때문에 H0 마다 sha 가 바뀜; 지금 기록 67e6681e…). 대신 L0 에서 `vp_treefields.py` 로 칸을 대조: schema = `vp-tree/1`, ok = 참(bool), freeze_sha256 = `011f5be2…`(FREEZE.json, EXT 핀에 있음), files_expected = 10,569, missing_n = 0, differs_n = 0, missing·differs 목록 빔. `checked_kst` 는 보지 않음. `vp_job.py` 의 ok 칸 점검은 그대로 | `vp_treefields.py`(새 파일) |
| X5 | D-K9-108, PRE_VP_FIXED §8 | 끊긴 일의 출력은 `*_interrupted_*` 로 옮긴 뒤 다시 | 멈춘 P1 일(v3c3-s31 T = 1,800)을 옮김: 일 폴더 → `GT/out/interrupted/plant_P/v3c3-s31_T001800_interrupted_r2stop_<KST 시각>`, 로그 `VP/logs/plantP/` 의 `P_v3c3-s31_T001800.done`·`.out.txt`·`.check.txt` → 같은 폴더 안 `P_v3c3-s31_T001800_interrupted_r2stop_<KST 시각>.{done,out.txt,check.txt}`. 폴더를 `plant_P` **밖**으로 옮기는 까닭: 표 도구가 `plant_P` 안의 모든 폴더를 P 상태로 읽음 [읽음 `vp_analyze.py`:170–171]. 이 상태는 다음 실행에서 r3 도구로 처음부터 다시 굴림 | (파일 이동) |
| X6 | D-K9-109 (4) | — | r3 핀을 LOG 에 적은 뒤 STOP_VP 를 지움. 지우기 전 바이트 사본 `VP/review_r3/STOP_VP_r2.json` (sha 가 ebd85663… 와 같아야 함) | (파일) |

### 1.1 X1 을 표 도구가 읽는 법 (도구는 그대로)

- 이번 고침에서 코드를 바꾼 도구는 `vp_probe.py`·`vp_jobcheck.py`·`vp_queue.py` 셋뿐입니다(지시 범위). 표 도구 `vp_analyze.py`(sha `a3638816…`, r2 그대로)는 바꾸지 않았습니다.
- [읽음 `vp_analyze.py`:257–263, :581–586, :743–748, :762] 표 도구는 `R1_objective_bit_equal` 이 참이 아니면 그 상태를 "멈춤 규칙 걸림" 목록에 `{"check": "R1_objective_bit_equal", "value": false}` 로 적고, 표 A1 의 "R1" 칸에도 이 비트 같음 값을 씁니다. 그 상태의 표 값 계산은 이 항목 때문에 빠지지 않습니다(행 계산이 이어짐).
- r3 에서 이 항목을 읽는 법: 같은 상태의 `jobcheck.json` 에 S-R1 걸림이 없고 `r1_objective_ok` 가 참이면, 이 항목은 **R1 비트 보고**이지 멈춤 규칙 걸림이 아닙니다. 그 상태의 표 값은 씁니다. 보고에서는 그 상태에 "R1 목적값 비트 다름(차 ≤ 1e-9)" 과 차 값을 함께 적습니다. 이것은 X1 규칙을 표 칸에 적용한 것이고 새 규칙이 아닙니다. 다른 항목(R3, null, 훅, 셀 경계, 도달)의 읽는 법은 r2 그대로입니다.
- 표 도구 코드를 이 뜻에 맞게 고칠지는 사용자 선택지로 남깁니다(§6).

### 1.2 도구 차이 (r2 → r3)

- `vp_probe.py` [읽음 차이 파일 `review_r3/diff_vp_probe_r2_r3.txt`]: `R1_objective_within_1e-9` = (차가 유한) 그리고 (\|차\| ≤ 1e-9) 칸을 더 적음. 멈춤 조건이 `R1_objective_bit_equal` 대신 이 칸을 씀. 멈춤 글이 "within 1e-9" 로 바뀜. 설명 글 고침. **plant 굴림·계획·요청 바이트에 닿는 줄은 없음** — 그래서 r2 탐침으로 끝난 두 상태(s31 T = 3,300·3,450)와 r3 탐침으로 굴릴 상태는 같은 굴림 경로입니다 [읽음 차이].
- `vp_jobcheck.py` [읽음 `review_r3/diff_vp_jobcheck_r2_r3.txt`]: R1 목적값 판단 함수 `r1_objective_ok` — r3 probe 의 bool 칸이 있으면 그것, 없으면(r2 꼴 probe.json) `R1_objective_diff` 로 \|차\| ≤ 1e-9; 칸 없음·NaN·무한·bool 은 거짓. 출력에 `r1_rule`, `r1_objective_ok` 를 더 적음. 다른 점검(S-ERR, probe stop 칸의 S-R1, S-R3, S-NULL, S-HOOK, S-MAP, S-REACH)은 그대로.
- `vp_queue.py` [읽음 `review_r3/diff_vp_queue_r2_r3.txt`]: 잠금을 잡은 뒤 `STOP_VP present after LOCK` 를 적고 잠금을 풀고 멈추는 가지. 설명 글 고침.
- 차이 글 전체는 LOG 18:18 항목에 그대로 있습니다.

## 2. 바꾸지 않은 것

- 상태 목록(탐침 A·B 12, P1 9), 팔(110·101·100·90), 계획(REC·REPACK·ARM·EXEC), 지표, 편향 정의, 창, 후보 C1–C9 와 절제 값, 줄임 비율 R, 가리킴 규칙, 띠, 방향 칸, 표, 순서(§8), 잠금 규칙(배타 생성, 자기 것만 지움, 우리 해제 + 20 s 쉼), 워치독, 금지 목록, 봉인 시드 규칙.
- R0(보고만), R2(보고만), **R3 비트 같음**, **S-NULL 비트 같음**, S-HOOK, S-MAP, S-REACH, S-ERR, S-BLIND 는 r2 그대로입니다. D-K9-108 은 R1 목적값만 다룹니다.
- 탐침 A·B 의 남은 10상태, P1 9상태(1,800 다시 포함)는 같은 명세(`decl/specs/jobs_A.json` b68e18f2…, `GT/out/p1_specs/jobs_P.json` b6c75af5…)로 이어 갑니다. 끝난 두 상태(s31 T = 3,300·3,450)는 `.done` 이 있어 큐가 건너뜁니다.

## 3. 시험과 핀 (이 문서와 함께 고정)

- [실행] 고침 시험 `VP/review_r3/r3_patchtest.py`(sha `7c480d07d2b7f57d60c66ab5b22f2a71310e2c2bb5ac93b15c80ed8e2d5d08a5`) → `review_r3/r3_patchtest.json`(`9e5d45770dd2e6d572e4d309e48826380d6cda6181b89b44647e547e48c5f5ec`): **30/30 참**. 합성 입력만(PID 붙은 임시 폴더, 끝에 지움). 실제 잠금·실제 STOP_VP·plant 코드·VISSIM 손대지 않음. 무엇을 봤는지는 LOG 18:18 항목. 요지: 2 ULP 차는 S-R1 아님, 2 × 10⁻⁹ 는 S-R1; 잠금 기다리는 중 STOP_VP 가 생기면 r3 큐는 일 0, r2 큐는 일 1(틈 재현); `vp_treefields.py` 는 시각 칸만 다른 기록을 받아들이고 ok·개수·freeze sha 가 다르면 거절.
- [실행] 자체 시험 다시 `tools/vp_selftest.py` → `selftest/selftest_amend_r3.json`(`9df60af4c6f67bb5679ddea056dd1d66ad6b7dd4e4e18ebc7c7002f0204a8de6`): **65/65 참**. r2 기록(48efab47…)과 다른 칸은 잠금 쉼 시험의 잰 시간뿐(0.997 s 대 1.005 s, 문턱 0.9 s).
- [실행] 핀 r3 (`tools/vp_pin_r3.sh` 가 씀, 18:16:54 KST):
  - `VP/SHA256SUMS_VP_r3.txt` sha256 **`87a214065222626b4b312671c5668167946eb0a798fc48854e0baa37fb898720`** — 54줄, `sha256sum -c` 54/54 OK.
  - `VP/SHA256SUMS_VP_EXT_r3.txt` sha256 **`217c0538bbd9e3491cef184f1bd0c6cfe86d4c3b30e58200937f3a5016933227`** — 14줄, 14/14 OK. r2 EXT 목록에서 `code_va.tree.json` 한 줄만 뺀 것과 바이트까지 같은 줄들 [실행 diff].
  - r2 목록(`SHA256SUMS_VP.txt` 51f9f38b…, `SHA256SUMS_VP_EXT.txt` 5e84baf4…)은 고치지 않고 기록으로 둡니다(r3 VP 목록 안에 있음). r3 뒤로 L0 는 r2 목록을 쓰지 않습니다(고친 도구 셋에서 맞지 않는 것이 정상).
- 주요 sha (r3 에서 바뀌거나 새로 생긴 것은 ★):
  - ★ `tools/vp_probe.py` `81925375151d5eb4b5129c3999e3fdc5e1975bbe01ad485be4a664ce9e209dae` (r2 1c08ad5b…, r2 바이트 `tools/vp_probe_r2.py`)
  - ★ `tools/vp_jobcheck.py` `a664ab99dbcd7766049533dcaaf44c6ca952006c0f740b65915300b885305b24` (r2 a922ab6d…, `tools/vp_jobcheck_r2.py`)
  - ★ `tools/vp_queue.py` `9145bd3592f566257c1bcfdfa4b530a5c5149cc43fd41831822b59dbc0d40d7c` (r2 53efbad4…, `tools/vp_queue_r2.py`)
  - ★ `tools/vp_treefields.py` `e864fcf8a6587ae138a232e860fc2e9a3fb11607ccf5333b564ab3477dc18f55` (새 파일, X4)
  - ★ `tools/vp_pin_r3.sh` `5e044494e6a088fada20b69a015a43f94a08ab3aa7664a1749e0ce6f961a8109` (새 파일; r2 `vp_pin.sh` 5325b9dd… 그대로 둠)
  - ★ `decl/R3_MARKS.json` `e3c08da0acc9b5a058c77d492c84238c73ed1df9e4d39507f354c8b84b6f77ad` (X2 표시, 끝난 두 상태와 멈춘 상태의 sha)
  - ★ 차이 파일 `review_r3/diff_vp_probe_r2_r3.txt` e47a6686…, `diff_vp_jobcheck_r2_r3.txt` f960c3fc…, `diff_vp_queue_r2_r3.txt` 9a477020…
  - 그대로: `vp_analyze.py` a3638816…, `vp_hooks/sitecustomize.py` b498eee0…, `vp_job.py` 2164f97e…, `vp_common.py` a8cdeff5…, `vp_launch.ps1` efbc4ebf…, `vp_selftest.py` 8d3e33fb…, 선언 파일 전부, `PRE_VP_FIXED.md` 33e71ac3…, `PRE_VP_r1.md` 4147f859….

### 3.1 r3 뒤 L0 (PRE_VP_FIXED §8 의 L0 를 이것으로 바꿈)

1. `PRE_VP_R3.md` 의 sha 가 `PRE_VP_R3.md.sha256` 과 같음.
2. VP 에서 `sha256sum -c SHA256SUMS_VP_r3.txt`(54/54)와 `sha256sum -c SHA256SUMS_VP_EXT_r3.txt`(14/14).
3. `python -B tools/vp_treefields.py` 종료 0 (X4 의 칸 대조).
4. `python -B tools/vp_selftest.py <새 출력 이름>` 65/65 참.
5. 하나라도 어긋나면 S-ERR(무거운 일 0, 보고). 고침 시험 `review_r3/r3_patchtest.py` 는 다시 돌려도 되지만(합성 입력, 30/30) L0 필수는 아닙니다.

## 4. 이 고침 전에 이미 나온 자료 (데이터 뒤라는 뜻)

- P1(Q-V4): 첫 상태 v3c3-s31 T = 1,800 의 R1 값만 — 기록 428.70567665096473, 재생 428.70567665096485, 차 +1.1368683772161603 × 10⁻¹³ veh·h (2 ULP), 비용 20개 키 같음·최대 차 3.55 × 10⁻¹⁵ [실행 읽음 `probe.json` 46e85a2f… `checks`]. 스칼라 묶음·절제(null, C1–C9) 0, 편향·R 값 0.
- Q-V3(탐침 A·B): v3c3-s31 T = 3,300 (A1)·3,450 (A2) 두 상태의 전체 출력과 부분 표(`QV3_REPORT.md`, `vp_tables_qv3_stop.*`). 같은 시드 T = 3,300 의 R2 − R1 = +1.137 × 10⁻¹³ (스칼라 대 AD, 보고만).
- 바꾼 허용 1e-9 veh·h 는 r2 가 비용에 데이터 전에 정한 값 그대로이고(PRE_VP_FIXED §3.4, smoke v1 의 1.4e-14 를 보고 정함), 사용자가 고른 값입니다. 지표·문턱·후보·상태는 바꾸지 않았습니다. 그래서 이 고침이 위 자료의 값에 맞춘 것은 아닙니다 [추론].
- [실행 읽음, 데이터 뒤] r3 규칙을 기존 기록에 대 보면: P1 s31 T = 1,800 은 R1 목적값 참·비용 참, s31 T = 3,300·3,450 은 참·참(r2 에서도 비트 같음) (`r3_patchtest.json` `existing_records_r3_rule`).

## 5. 남은 위험 (데이터 뒤, [추론], 고치지 않음)

- **S-NULL 이 같은 꼴로 걸릴 수 있음.** null 절제(P1 만)는 따로 Query·작업자 프로세스로 EXEC 와 같은 계획을 굴리고 J·비용의 **비트 같음**을 봅니다(r2 그대로). R1 의 2 ULP 가 프로세스·합산 순서 차이에서 왔다면 null 도 마지막 자리가 갈릴 수 있습니다. 근거: smoke v1–v5 에서는 null 이 비트 같았음 [실행 기록, PRE_VP_FIXED §1.3–1.4]; T = 3,300 의 R2 − R1(다른 경로)은 2 ULP 였음. 걸리면 큐가 다시 멈추고(STOP_VP) 사용자가 정합니다. D-K9-108 범위 밖이라 이번에 바꾸지 않았습니다.
- R3 는 REPACK 토큰이 REC 토큰과 같으면 같은 캐시 항목이라 구조상 비트 같음입니다(PRE_VP_FIXED §R-1). 토큰이 다르면 따로 굴러가 같은 위험이 있습니다.
- 표 도구는 §1.1 대로 R1 비트 다름을 "멈춤 규칙 걸림" 목록에 계속 적습니다(읽는 법으로 처리).

## 6. 사용자에게 남는 선택지 (이 고침에서 정하지 않음)

- O1: 표 도구 `vp_analyze.py` 의 R1 칸을 X1 에 맞게 코드로 고칠지(지금은 §1.1 읽는 법).
- O2: S-NULL 이 2 ULP 꼴로 걸리면 null 에도 같은 허용을 줄지(그때 결정).

## 7. 이 문서 고정 뒤 할 일 (순서, 무거운 일 0)

1. LOG 에 이 문서 sha 를 적음(핀 r3 는 18:18 항목에 이미 적음).
2. X5 이동(폴더 + `.done`·`.out.txt`·`.check.txt`), 이동 기록을 LOG 에.
3. X6: STOP_VP 바이트 사본을 `review_r3/STOP_VP_r2.json` 으로, sha 대조 뒤 STOP_VP 지움.
4. 핀 r3 다시 대조(이동·지움이 핀에 닿지 않음을 확인), 보고 사본 RVP.
- 탐침 굴림·FZP 스캔·P1 입력 계산·VISSIM·COM·러너·동결 0. GWT8 손대지 않음(c20aff1d 그대로). 남의 프로세스 손대지 않음.

## 8. 변경 기록

- r1 (16:54 KST): `PRE_VP.md` 4147f859….
- r2 (17:28 KST): `PRE_VP_FIXED.md` 33e71ac3….
- r3 (2026-10-27 18:20 KST, 데이터 뒤): 이 문서. X1–X6. 바뀐 도구 `vp_probe.py`·`vp_jobcheck.py`·`vp_queue.py`, 새 파일 `vp_treefields.py`·`vp_pin_r3.sh`·`decl/R3_MARKS.json`·`review_r3/*`, 새 핀 목록 `SHA256SUMS_VP_r3.txt`·`SHA256SUMS_VP_EXT_r3.txt`.
