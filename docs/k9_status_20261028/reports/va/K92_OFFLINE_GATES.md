# K9-2 V-A OfflineGates: 새 동결본 FRZ_K92에서 보충 34 §5 오프라인 관문 — 결과

- 작성 2026-10-23 11:0x KST. 실행 2026-10-23 09:01:28 ~ 11:00:21 KST.
- **결론: 보충 34 §5.1이 정한 관문(FG·GB-7′·해시 A/B·GB-9′·S·G-H5′ 세 시드)이 모두 PASS입니다.** FAIL 0, 보류 0, INCOMPLETE 0.
- 이 결과만으로 발사하지 않습니다. 보충 34 §5.1 끝(`:238`)과 §6.1 발사 전제 (3)(`:280`)대로, 독립 검증 `VA/VERIFY_GATES_VA.md`가 pass = true여야 발사할 수 있습니다.
- 표시: **[실행]** 이번에 직접 돌리거나 파일을 읽어 확인, **[읽음]** 문서·코드에서 확인, **[추론]** 시험하지 않은 판단.
- 줄임말 (처음 한 번 풀어 씀)
  - SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`(이 단계 작업 폴더).
  - REPVA = 보고 사본 자리 `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`. OUTVA = 관문 출력 `REPVA/offline_gates`.
  - FRZ_K92 = 이번 동결본(얼린 사본) `D:/VISSIM-merge/frozen/sdmpc31_c20aff1d_202610230833`, `FREEZE.json` sha256 `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`, head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(K9-2-7). 읽기만 했습니다.
  - FRZ_K8b = 앞 동결본 `D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821`(읽기만). OUTH = FRZ_K8b 관문 출력 `D:/VISSIM_runs/20261001_v3c3/reports/k8/offline_gates_k8h`(읽기만, 자기 시험에만 씀).
  - GWT8 = 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`, 가지 `claude/k92-b1-20261016`, HEAD = 원격 = `c20aff1d…`. 커밋 0.
  - R-obs3 = 무제어 기록 런 `D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31`(v3c3-s31, 61결정, 읽기만).
  - RVA = V-A 런 자리(RunsRoot) `D:\VISSIM_runs\20261023_sdmpc31_k92`. RR = J1 런 자리 `D:/VISSIM_runs/20261004_sdmpc31_k8`(읽기만).
  - A = GB-7′ 허용 차이 목록 V ∪ A_K8(FRZ_K92 `gb7_allowed.py`, R2-12 포함, 목록 sha `a8148f38…7af1`). E_K92 = 보충 34 §5.2의 K9-2 선언 차이 네 경로(사용자 결정 D-K9-71).
  - SDMPC = 모형예측 리더 결정기. WMI = `Invoke-CimMethod Win32_Process Create`(세션과 떼어 띄움). S = 상시 관문(어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0).
- 근거 선언: 보충 34 `SP/K8_PREDECLARATION_AMENDMENT_34.md` sha256 `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e`(고정점 `VA/AMENDMENT34_FIXED.md` `fef58eca…c167`, 고정 목록 `VA/a34_pins.sha256` `4e447416…0403`, 시작 때 83/83 OK) [실행]. 관문 정의 §5.0 `:207-224`, 표 §5.1 `:226-239`, E_K92 §5.2 `:241-266`. 실행 방법 `SP/j1/og/OG_METHOD.md`(`8edf8673…`) §1–§5.
- **블라인드**: 재생의 목적값·예측값은 판정 코드가 메모리에서 같음/다름으로만 썼습니다. 화면·로그·이 보고에는 벽시계·개수·sha·참거짓·경로만 있습니다. V-A 성능 숫자(Ω·TTT·지표 ①–④·지연)는 V-A 런이 없어 존재하지 않고, J1 성능 숫자도 열지 않았습니다.

---

## 0. 판정표

| 관문 | 정의 출처 | 값 | 문턱 | 판정 |
|---|---|---|---|---|
| 시작 조준·목록 검사 (guard) | 보충 34 §5.0 `:210` | `FREEZE.json` sha `011f5be2…` = §4.2 기록, `git.head` = GWT8 HEAD = `c20aff1d…`, GWT8 `status --porcelain --ignored`(캐시 제외) 0줄, GWT8 바이트 대 FRZ_K92 표 바뀜·없음·더함 0/0/0, `gb7_allowed.py` 파일 sha `61c70c22…f319` = K9-2-7 blob 바이트, `list_sha256()` `a8148f38…7af1`, A_K8 35, V 7, E_K92 함수 sha `d15e9cc0…fb11`, FRZ_K8b `FREEZE.json` `6143d3eb…` 그대로 [실행 `judge/guard_20261023_090149.json`] | 모두 참 | **참** |
| FG 동결·커밋 정합 | §5.1 `:230` | FG-1 = {M CFG, M `gb7_allowed.py`}; FG-2 출력 0 B(exit 0); FG-3 바뀜·더함·없음 12/21/0 = `git diff b9734abe c20aff1d` M/A/D, 33경로 FRZ blob = ls-tree blob 33/33, FRZ sha = 표 sha; FG-4 재생 도구 `4adf41cf…`·`5d34109f…` = FRZ_K8b 사본 [실행 `judge/fg_result.json`] | FG-1–4 모두 참 | **PASS** |
| 1 GB-7′ T5 재생 61결정 | §5.1 `:231`, OG_METHOD §2, §5.2 | 61/61. 조건 1–8 각 61/61(조건 7 = A ∪ E_K92), 제어 7필드 같음 61/61, CSV 같음 61/61 [실행 `judge/gb7_result.json`] | 61/61 + 제어 7필드 61 | **PASS** |
| └ 선언 목록 A만의 조건 7 (보고만) | §5.1 `:231`, §9.1-6 `:470` | `c7_declared_A` 0/61 (61결정 모두 거짓). A 밖 경로 = 정확히 E_K92 네 경로 [실행] | 보고만 (0/61 거짓이 예상, §2.1) | 보고 |
| 2 해시 A/B 9회 | §5.1 `:232`, OG_METHOD §3 | 9/9: 조건 1–8 참(조건 7 = A ∪ E_K92, 1번과 같은 함수·이름·Root), 제어 7필드 같음, 환경 `PYTHONHASHSEED` 의도대로; 미설정 대 0·2 짝 6개 V 밖 차이 0, CSV 같음 [실행 `judge/hash_result.json`] | 9/9, 짝 차이 0 | **PASS** |
| 3 GB-9′ 반사실 SDMPC 4결정 | §5.1 `:233`, OG_METHOD §4 | 4/4: S·유효성 참. 벽시계 (가)/(나) s: 900 722.8/710.48, 2700 752.1/738.45, 4950 701.4/687.62, 6300 684.3/671.06 [실행 `judge/gb9_result.json`] | (가) ≤ 1005.0/859.95/996.0/974.4, (나) ≤ 985.644/841.083/975.748/955.379 | **PASS** |
| 4 상시 관문 S | §5.1 `:234`, OG_METHOD §5 | 74/74 (GB-7′ 61 + 해시 9 + GB-9′ 4), 실패 0 [실행 `judge/s_result.json`] | 74/74 | **PASS** |
| 5 G-H5′ 발사 출처 v3c3-s31 | §5.1 `:235` | 조건 1–7 참(12키 모두 참), 조건 8 RVA에 `sdmpc31_v3c3_k92va_s31` 없음 [실행 `judge/gh5_s31_result.json`] | 1–8 모두 참 | **PASS** |
| 5 G-H5′ v3c3-s41 | §5.1 `:235` | 조건 1–8 참 [실행 `judge/gh5_s41_result.json`] | 1–8 모두 참 | **PASS** |
| 5 G-H5′ v3c3-s43 | §5.1 `:235` | 조건 1–8 참 [실행 `judge/gh5_s43_result.json`] | 1–8 모두 참 | **PASS** |
| 판정기 자기 시험 (i)(ii)(iii) | §5.0 `:214` | (i) K8b 판정 재현, (ii) 합성 변조 기대대로, (iii) E_K92 자기 시험 표준 출력 = 고정 출력 `666cbac3…1110` 바이트 같음 [실행, §1.3] | 모두 기대대로 | **참** |
| 읽기 전용 감시 | §5.0 R4 항목 6 `:221` | 단계 끝마다 8회 대조(FG·A·H·B·G-H5′ 세 시드·after), 변화 0 [실행 `logs/g_driver.log`, `snap/after_*.json`] | 변화 0 (G-H5′ 뒤 `_preflight` 새 폴더 셋만) | **참** |

- 단계 기록 `OUTVA/judge/stages.json` sha256 `447155b8caadd8cdce0f06971e8d75c8c0fe90d122cc3379e48cd9d85d4dd952`: FG PASS(09:02:01), GB-7′ PASS(09:59:49), 해시 A/B PASS(10:08:24), GB-9′ PASS(10:58:14), S PASS(10:58:14), G-H5′ PASS(10:59:56) [실행].
- **pass = true 조건**(과제 글): 모든 관문 PASS, INCOMPLETE·보류 없음 → 충족.

---

## 1. 실행 방식 [실행]

### 1.1 판정기를 데이터 전에 고정

- 판정기 = `VA/gates/`에 K8b 도구(`SP/j1/fix/gates/`)를 복사해 고친 사본입니다. 원본 9개를 `VA/gates/k8b_orig/`에 바이트 그대로 두었고(sha = K8b 고정값), 원본 대 사본 차이를 `VA/gates/copy_diffs/*.diff`로 남겼습니다.
- 고정: 첫 관문 재생 전 09:00:25 KST에 `VA/gates/va_gates_pins.sha256`(sha256 `6af36e7bd77dcc122886e56d30f0dae5ff76f75c72a74d2f6d9c33efeadfb669`, 31줄)과 LOG에 적었습니다. 구동기 발사는 09:01:28입니다. 끝난 뒤 `sha256sum -c` 31/31 OK입니다. **고정 뒤 판정기를 고친 일은 없습니다**(S-A34-4 해당 없음).

| 파일 | sha256 | K8b 대비 |
|---|---|---|
| `gcommon.py` | `9f59ae2dd2a147f6f7ad61db676f66717a14fc706088fb76a3b14f2139b50b0e` | 기대값·자기 시험 프로필 상수(§1.2) |
| `gprep.py` | `0482a53868fd3ee644724dab2dcb6af2c56d749708ccec5242f6b3549ae26f22` | 바이트 같음 |
| `greplay.py` | `a879650597cea1bc7b013269023084f9013ab7534d47d1c098d672626a858370` | 바이트 같음 |
| `gjudge.py` | `5a46236eaf7e1aad150757af55583fc495ef7478879abd451588a98ed3818525` | R4 항목 1·2·3·4·5·7 |
| `g_driver.py` | `73d3cf2c2c0db8a1c1f2d537fe1d0eba12294d65a8a3e7097639293ee007817d` | R4 항목 1·5·6 |
| `launch.ps1` | `a2c4d52a40cbc7b6da0ad46f8806de2c472b2221fb19513d8f38e68f58ee124c` | 로그 폴더 = OUTVA |
| `gh5_check.py` | `29324dc6b3ad1fa6b6ece87f10574094a80707c7c14015e36748e2103dc96e19` | 런 이름·시드·RVA (기대값) |
| `gb7_report.py` | `b492dd84b591a71fa469a128f8d615dd306d7e9239a63b18db57f0abcd72de02` | OUTVA·FRZ_K92 (기대값) |
| `gh5_launch.ps1` | `8644280059d9f21065db63a3abb3bfda6f6f5abba3325ae95cef0a6685d20a8e` | FRZ_K92·RVA·이름·시드·출력 (기대값; 공개 §2-2) |
| `gb7_k92decl.py` (E_K92 판정 함수) | `d15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11` | 보충 34 고정값 그대로 |
| `gb7_k92decl_selftest.py` (v2) | `e15b60a18c633e2730c6ac2a272c1d1947759eb681fc6ad3db0ec912f2219765` | 보충 34 고정값 그대로 |
| `va_gates_selftest.py` (새, 판정 아님) | `0b4f437479786e75f791ab4b6721c3b27cd53324836dac68ba45d66699b2a67e` | 자기 시험 (i)(ii)(iv) |
| `va_gates_report.py` (새, 보고만) | `55c7f4f0e78c02aad1c2482c6560f86f06595370971d565c0ec1fb8c973febbf` | §5.1 "보고만" 칸 모음 |

### 1.2 사본이 K8b 도구와 다른 곳 (보충 34 §5.0 R4 닫힌 목록 `:215-222`에 맞춤)

- **항목 1 기대값**: FRZ = FRZ_K92, `FREEZE.json` sha `011f5be2…`, HEAD `c20aff1d…`, 튜닝 `c8e3ee2c…1866`, 목록 파일 sha `61c70c22…f319`, 목록 sha `a8148f38…7af1`, 출력 OUTVA. FRZ7(R-obs3 기록 루트)·K7 GB-9 벽시계 기준값·R-obs3 경로는 그대로. 구동기 guard의 문서 sha 목록도 기대값으로 바꿨습니다(보충 34·고정점·결정 기록 `6b76cc09…`·보충 21/22/23·OG_METHOD).
- **항목 2 조건 7 연결**: `gb7_row`가 `gb7_k92decl.judge_cond7(a, b, G, Root, floor_key='head_discharge_floor_173_p4_e36d6761cfeac634')`를 부르고, `c7_diff_in_A` = `c7_A_or_EK92`(판정), `c7_declared_A`·`diff_outside_A`·`diff_outside_A_EK92`·`ek92`(보고)를 적습니다. 적중 수는 `gb7_k92decl.which`로 셉니다. 해시 A/B도 같은 `gb7_row`입니다.
- **항목 3**: GB-7′ PASS = 61행 + 행마다 조건 1–8 + `control_fields_equal_count` = 61. 해시 A/B는 9회 각각 `control_fields_equal` 참을 더함.
- **항목 4**: D-K9-12 분기(`PROGRESS_DK912`)·`DK912_PATH`를 뺌. 그 분기만 쓰던 `raw_get`도 함께 빠졌습니다.
- **항목 5**: 구동기 단계 = guard → FG → A → H → B → S → GH5(G-H5′ 세 시드) → after. K8b의 D·GH1·R1·R2 단계, `cmp21`·`judge_pairs`·`gh2*_pairs`는 없습니다. `gh1*.py`·`gr.py`·`gtree.py`·`cmp21.py`·`gh4_confirm.py`는 사본에 두지 않았습니다. 이에 따라 `gcommon.py`에서 그 단계만 쓰던 상수(`TREES`·`TREE74`·`K89`·`HEAD74`·`FREEZE8_SHA`·`TUNING74_SHA`·`J1_DEC`·`OUT8`)를 뺐습니다.
- **항목 6 읽기 전용 감시**: FRZ_K92(캐시 포함), FRZ_K8b, `frozen/` 최상위, R-obs3, J1 런 폴더 넷(`sdmpc31_v3c3_k8j1r_s31`·`k8j1_s31`·`k8j1_s41`·`k8j1_s43`), RR 최상위, RVA 최상위와 `RVA\_preflight`, GWT8 HEAD. 단계마다 대조하고 변화가 있으면 멈춥니다.
- **항목 7**: 자기 시험용 K8b 프로필(FRZ_K8b·`b9734abe`·`d0f9ef39…`·목록 `f954c2b0…`·OUTH, E_K92 증거 Root = FRZ_K8b). 두 프로필이 다른 목록을 쓰므로 목록 모듈을 전역 변수 대신 프로필 칸(`P['G']`)으로 두었고, `gcommon.load_allowed`가 동결본·파일 sha·목록 sha·항목 수를 인자로 받습니다.

### 1.3 판정기 자기 시험 (데이터 전) [실행]

- **(i)(ii)(iv)** `va_gates_selftest.py`, 고정 바이트로 09:00:33 1회. BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, 자식 프로세스 0. exit 0, **CHECKS 24/24, ALL_OK**, 오류 출력 0 B. 표준 출력 `VA/gates/va_gates_selftest.out.txt` `a45b5ecb…663b`, 결과 `OUTVA/selftest_gjudge/va_gates_selftest.json` `9cdd6de1…4d58`. 기대는 실행 전에 도구 docstring에 적었습니다.
  - (i) K8b 출력(OUTH)으로 K8b 판정 재현: GB-7′ FAIL, 61개, 실패 T = {1}, 60/61, 조건별 참 61(조건 7만 60), 제어 7필드 61, T=1 A 밖 = A ∪ E_K92 밖 = {`/diagnostics/leg_ramp_split_len_SC1001_W_out`}, 모든 행 `c7_A_or_EK92` = `c7_declared_A`(E_K92 적중 0); 해시 PASS(제어 7필드 9/9); GB-9′ PASS; S 74/74. = K8b 판정(`GATES_K8b.md` §0)과 같음.
  - (ii) K8b GB-7′ T=750 묶음 사본으로 합성 변조: 사본 그대로 → 참; 재생 metadata에 새 키 → 조건 7 거짓; 재생 CSV에 1바이트 → 조건 8 거짓; 요약의 튜닝 sha → 조건 5 거짓; E_K92 네 키를 선언 값으로 더함(증거 Root = FRZ_K92) → 조건 7 참·선언 A 거짓·E1–E4 적중 각 1; 하한 값 1 ulp 큼 → 조건 7 거짓. 모두 기대대로.
  - (iv) `gh5_check`(시드 31)를 PushFreeze 무제어 사전점검 캡처(`VA/freeze/k92_freeze_preflight.out`)에 적용: `2_plan_detail_line`(제어기 no-control)·`7_exit_code_0`(다른 런 이름)만 거짓, 상태 FAIL, 런 폴더 없음. 기대대로(K8b `selftest/gh5_on_k8r.json`과 같은 꼴). 결과 `OUTVA/selftest_gh5/gh5_on_k92pre_s31.json` `61a12659…628d`.
- **(iii)** `gb7_k92decl_selftest.py --out OUTVA/selftest_ek92`, 09:01:03. 보충 34 §5.0 `:214` 꼴 그대로: `cmd /c start /belownormal /b /wait python -B …`, `PYTHONHASHSEED=0`, `PYTHONIOENCODING=utf-8:surrogateescape`, `PYTHONUTF8` 미설정, 표준 출력 파일. exit 0, 오류 출력 0 B. **표준 출력 sha256 `666cbac34ace9b76025c66fc655468e733935a7e69e2fc93519c62a20f3c1110` = Declare 고정 출력**(`fc /b` 차이 없음), JSON `0601efdd…6bf6` = 고정값. 끝 줄 `ALL_OK`, 목록 sha `a8148f38…7af1`. S-A34-11 해당 없음.

### 1.4 구동기

- `VA/gates/launch.ps1` → WMI, 09:01:28 KST, ReturnValue 0, cmd PID 23172(내가 띄움) → python 14080, BelowNormal(16384), `PYTHONHASHSEED=0`(해시 A/B만 선언대로 미설정/0/2), `python -B`, `PYTHONDONTWRITEBYTECODE=1`, 스레드 1, `NUMBA_CACHE_DIR = OUTVA/numba_cache`. 그때 VISSIM 0·python 0. 11:00:21 `G_DRIVER_DONE`, cmd는 스스로 끝남. 무거운 Python은 한 번에 하나였습니다. 다른 프로세스를 끄지 않았습니다.
- 확인 간격: 9분 이하의 짧은 대기(조건 만족 또는 약 8.5분)로 로그만 읽었습니다(블라인드 줄: 종료 코드·판정·벽시계).
- 재생 준비는 sha 확인 사본 + F17b 이력 사본(OG_METHOD §1) 그대로입니다(`gprep.py`·`greplay.py` K8b 바이트 같음).

---

## 2. 알릴 것 (공개)

1. **보고서 이름 둘**. 보충 34 §5.1 `:239`는 `VA/K92_VA_OFFLINE_GATES.md`, 과제 글은 `VA/K92_OFFLINE_GATES.md`입니다. 같은 바이트로 둘 다 두었습니다(VerifyPromote 때 `VERIFY_PROMOTE_r1.md` = `VERIFY_PROMOTE_VA.md` 선례).
2. **`gh5_launch.ps1` 사본**. §5.0이 이름으로 든 사본은 8개(`gcommon`·`gprep`·`greplay`·`gjudge`·`g_driver`·`launch.ps1`·`gh5_check`·`gb7_report`)입니다. R4 항목 5가 G-H5′를 구동기 단계에 넣었으므로, K8b의 G-H5 발사 스크립트(`gh5_launch.ps1`, K8b `gates_files_later.sha256` `15d3abb0…`)를 기대값만 바꿔(FRZ_K92·RVA·런 이름·시드·출력 OUTVA) 9번째 사본으로 두었습니다. 발사 명령 글은 §5.1 `:235` 그대로입니다. 판정 로직은 없습니다. 같은 고정 목록에 들어 있습니다.
3. **G-H5′ 조건 8의 판정 자리**. K8b `gh5_check.py`는 런 이름 폴더 유무를 `report.run_name_folder_exists`로 보고만 했습니다. §5.1 `:235`는 이것을 통과 조건 8로 정합니다. `gh5_check.py` 사본은 기대값만 바꿨고, 조건 8은 구동기의 G-H5′ 단계(항목 5)가 그 보고 칸이 거짓인지로 판정합니다. 세 시드 모두 거짓(폴더 없음)이었습니다.
4. **새 도구 둘(판정기 아님)**. `va_gates_selftest.py`(자기 시험 (i)(ii)와 (iv) `gh5_check` 구문 확인)와 `va_gates_report.py`(§5.1 "보고만" 칸 모음)를 썼고, 판정기와 같은 고정 목록에 데이터 전 고정했습니다. 관문 상태를 바꾸지 않습니다.
5. **개발용 자기 시험 1회(고정 전)**. 판정기를 고정하기 전 08:58에 같은 자기 시험을 한 번 돌렸습니다(`VA/gates/dev/selftest_dev1.out.txt`). 읽은 것은 K8b 출력·PushFreeze 사전점검 캡처·FRZ_K92 증거 바이트뿐이고 V-A 관문 자료는 0입니다. 그 뒤 판정기는 바꾸지 않았고, 고정 뒤 공식 실행의 표준 출력은 개발 실행과 바이트 같습니다(`a45b5ecb…`). 같은 때 구동기 도우미 함수(`exit_line`·`process_done`·`preflight_rule`)를 단계 실행 없이 확인했고, 두 `.ps1`은 구문 분석만 했습니다(실행 0).
6. **자기 시험 (ii)의 T**. 합성 변조는 T=750 묶음으로 했습니다. R-obs3는 (173, p4) 하한 키가 T=900부터만 있어(보충 34 §2.1 `:97`), T ≥ 900 묶음에서는 E4 "재생 쪽에만" 사례를 만들 수 없기 때문입니다.
7. **`gb7_report.json`의 최대 |Δ| 칸은 열지 않았습니다**. K8b 꼴 그대로 항목별 숫자 리프 최대 |Δ| 칸이 있습니다. B1 키가 R2-02(`/prediction/...`) 값을 바꾸므로 예측 값 차이가 들어 있을 수 있습니다 [추론]. 블라인드를 위해 이 칸은 읽지 않았고, 이 보고는 OG_METHOD §2 (a)(b)와 항목별 경로·결정 수만 씁니다.
8. **G-H5′ 사전점검 시간**. 세 시드 각 약 26 s(K8b 약 2분 20초)였습니다. 동결 확인(FREEZE_VERIFIED) 단계가 20 s 안에 끝났습니다. 디스크 캐시 때문으로 봅니다 [추론]. 판정 조건이 아닙니다. 구동기 로그의 `wall=30.0`은 10 s 확인 간격 단위입니다.
9. **GB-9′ T=2700의 벽시계 비**가 가장 높습니다: (가) 752.1/573.3 = 1.312, (나) 738.45/560.72 = 1.317(문턱 1.5). K8b(1.294/1.299)와 비슷합니다.
10. **FRZ_K8b의 `__pycache__` 11개**는 감시 시작 전부터 있었습니다(2026-10-15 03:26–11:56, J1 v3c3-s31 재실행이 만든 것 [추론: 시각]). 감시 기준선에 들어 있고 변화 0입니다. FRZ_K92의 캐시는 시작·끝 모두 0입니다.
11. **GWT8 탄젠트 캐시**. GB-9′가 GWT8에 새 탄젠트 캐시 3개를 만들었고, after 단계가 `OUTVA/moved_tangentcache_gwt8/`로 옮겼습니다(목록 `moved_tangentcache_gwt8_list_gates.csv` `1975f03d…`). 원래 135개는 그대로이고, 끝난 뒤 GWT8 조준은 참(0/0/0), `status --porcelain` 0줄입니다.
12. **RVA 변화**. G-H5′가 `RVA\_preflight\` 아래에 `sdmpc31_v3c3_k92va_s31_20261023_105836`·`…_s41_20261023_105910`·`…_s43_20261023_105943` 셋을 만들었습니다. 런 이름 폴더 `sdmpc31_v3c3_k92va_s{31,41,43}`은 생기지 않았습니다(이름 미소모). RVA 최상위는 `_preflight` 하나 그대로입니다.
13. 해시 A/B 9회의 E_K92 적중은 E1·E2·E3만입니다(T = 4,050·4,500·9,000 ≥ 900이라 하한 키는 양쪽 같아 차이로 나오지 않음, §5.2-3 `:256` 예상과 같음) [실행].

---

## 3. 관문별 세부

### 3.1 FG [실행 `judge/fg_result.json` `e1aec788…b7ca`]

- FG-1: `git diff --name-status --no-renames e27ceac8 c20aff1d` = `M diagnostics/sdmpc_n31_20260924/config_n31_v2.json`, `M diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py`. 참.
- FG-2: `git diff e27ceac8 c20aff1d -- evaluation vendor plant scripts` exit 0, 출력 0 B. 참. 런타임 코드 = K9-2 관문·V-B가 본 K9-2-5 코드.
- FG-3: FRZ_K92 대 FRZ_K8b `FREEZE.json` 표 바뀜 12·더함 21·없음 0 = `git diff --name-status b9734abe c20aff1d` M 12·A 21·D 0, 그 밖 0. 33경로 FRZ_K92 `git hash-object --no-filters` = `git ls-tree c20aff1d` blob 33/33, FRZ sha256 = 표 sha 33/33. 참. (PushFreeze `check_freeze_k92.json` c10과 같은 결과.)
- FG-4: FRZ_K92 `make_replay_state_v2.py` `4adf41cf…0714`, `replay_decision_n31.ps1` `5d34109f…99c9` = FRZ_K8b 사본 = 고정값. 참.

### 3.2 GB-7′ 61결정 [실행 `judge/gb7_result.json` `60e7e600…7c45`]

- 재생: R-obs3 61결정(T = 1, 150, …, 9,000), Root = FRZ_K92, 무제어, 튜닝 = ps1이 R-obs3 provenance 경로를 FRZ_K92로 옮긴 CFG(`c8e3ee2c…`). 09:02–09:59, 어댑터 벽시계 27.3–34.4 s. 61결정 모두 ps1 exit 0 `IDENTICAL`, `--tuning` 없는 compare `IDENTICAL`, 어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0.
- 조건별 참 개수(61 중): 1 준비 61, 2 ps1·compare 61, 3 `FREEZE_VERIFIED … head=c20aff1d…` 61, 4 루트(root FRZ_K92·run_root FRZ_K7·rebased·`REBASE` 줄·`workspace_root` FRZ_K92) 61, 5 튜닝 `c8e3ee2c…`(인자·provenance) 61, 6 S 61, **7 A ∪ E_K92 안 61**, 8 CSV 바이트 61. 제어 7필드 같음 61.
- **선언 목록 A만의 조건 7(보고만)**: 0/61 참(61결정 모두 거짓). 보충 34 §2.1·§9.1-6이 데이터 전에 예상한 결과입니다.
- A 밖 경로(값 없음, 모두 종류 `presence` = 재생 쪽에만) [실행 `judge/va_gates_report.json` `fd073601…6fff`]:

| 경로 | E_K92 항목 | 결정 수 | T 범위 |
|---|---|---|---|
| `/metadata/k92_w` | E1 | 61 | 1 … 9,000 |
| `/metadata/k92_hb` | E2 | 61 | 1 … 9,000 |
| `/metadata/k92_hb_seed_binding` | E3 | 61 | 1 … 9,000 |
| `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634` | E4 | 6 | 1 … 750 |

- **A ∪ E_K92 밖 경로: 0개.**
- E_K92 조건별 참·거짓(그 경로가 차이로 나온 결정마다): E1 61결정 — `kind_is_presence`·`replay_only`·`is_dict`·`evidence_sha256_is_fixed`·`evidence_sha256_is_root_file`·`u4_sha256_is_fixed`·`after_float_repr_5209_8` 모두 61 참, 거짓 0. E2 61결정 — `evidence_sha256_is_fixed`·`evidence_sha256_is_root_file`·`rule_code_sha256_is_fixed` 등 모두 61 참. E3 61결정 — `float_0_or_1` 61 참. E4 6결정 — `float_repr_is_seed`·`binding_is_float_1` 6 참. 거짓 0. T ≥ 900에서 하한 키는 차이로 나오지 않았습니다(§5.2-3 `:256` 예상과 같음).
- A 항목별 적중(경로 수/결정 수, 판정기 `hits_by_item`): V 427/61, R1-01 427/61, R1-02…R1-08 각 61/61, R1-09 732/61, R1-10 305/61, R1-12 305/61, R1-13 976/61, R2-02 9,508/61, R2-03 830/60, R2-05 114/60, R2-07 2,068/61, R2-10 8/8, R2-11 393/61, **R2-12 1/1**, R3-01 122/61, R3-02 3,660/61, R3-03 366/61, R3-04 244/61, R3-05 1,830/61, R3-06 122/61; E1 61/61, E2 61/61, E3 61/61, E4 6/6.
- OG_METHOD §2 보고만 [실행 `gb7_report.py` 11:00:52, `judge/gb7_report.json` `333d0490…492e`]: (a) R3-04·05·06 차이 2,196개 모두 FRZ_K7 → FRZ_K92 접두 치환으로 같음. (b) R3-03 입력 이름 = {`adapter_py`, `main_vbs_runner`, `tuning_json`}, 기대 밖 0. (이 도구의 'OUTSIDE' 189경로 = 61×3 + 6 = 위 E_K92 경로뿐입니다. 이 도구는 A 항목만 셉니다.)

### 3.3 해시 A/B 9회 [실행 `judge/hash_result.json` `6df9bf54…d179`]

| T | 미설정 / 0 / 2: 조건 1–8·제어 7필드 | 환경 `PYTHONHASHSEED` | 선언 A만 조건 7 (보고) | E_K92 적중 | 미설정 대 0 / 대 2: V 밖 차이 · CSV |
|---|---|---|---|---|---|
| 4,050 | 참 / 참 / 참 | 키 없음 / 0 / 2 | 거짓 / 거짓 / 거짓 | E1·E2·E3 | 0·같음 / 0·같음 |
| 4,500 | 참 / 참 / 참 | 같음 | 거짓 ×3 | E1·E2·E3 | 0·같음 / 0·같음 |
| 9,000 | 참 / 참 / 참 | 같음 | 거짓 ×3 | E1·E2·E3 | 0·같음 / 0·같음 |

- 9회 모두 A ∪ E_K92 밖 경로 0, ps1 exit 0 `IDENTICAL`, 어댑터 벽시계 30.3–31.4 s.

### 3.4 GB-9′ 4결정 [실행 `judge/gb9_result.json` `9b938afa…757f`]

- 상태 T ∈ {900, 2,700, 4,950, 6,300}, wu-link, `PYTHONHASHSEED=0`, 직전 행동 = R-obs3 `action_<T−150>`, Root = GWT8 @ K9-2-7(결정 전마다 조준 참: HEAD `c20aff1d…`, `status` 0줄, 0/0/0), 도구 = FRZ_K92. ps1 exit 2 4/4(무제어 기록과 구성상 다름, 허용 0·2).
- 조건 1(S): 준비 참, 어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0(ps1·stdout·stderr) — 4/4. 조건 2(유효성): `replay_run.controller` wu-link, `sdmpc_active` 참, 튜닝 인자 sha·provenance `inputs.tuning_json.sha256` = `c8e3ee2c…`, `workspace_root` = GWT8, `workspace_git_commit` = `c20aff1d…` — 4/4.
- 조건 3(벽시계, 문턱 = K7 GB-9 r1 × 1.5, OG_METHOD §4 표 그대로):

| T | (가) `replay_run.json wall_sec` / 문턱 / 비 | (나) `metadata.decision_wall_sec` / 문턱 / 비 |
|---|---|---|
| 900 | 722.8 / 1005.0 / 1.079 | 710.485 / 985.644 / 1.081 |
| 2,700 | 752.1 / 859.95 / 1.312 | 738.452 / 841.083 / 1.317 |
| 4,950 | 701.4 / 996.0 / 1.056 | 687.623 / 975.748 / 1.057 |
| 6,300 | 684.3 / 974.4 / 1.053 | 671.060 / 955.379 / 1.054 |

- 보고만(§5.1 `:233`) [실행 `va_gates_report.py`]: 네 상태 모두 action metadata에 `k92_w`·`k92_hb` 있음, `k92_hb_seed_binding` = `0.0`, `head_discharge_floor_173_p4_*` 키 1개이고 이름 = R-obs3 v3c3-s31 이름(`e36d6761cfeac634`). 목적값·예측값·선택 명령은 내지 않았습니다(블라인드).

### 3.5 상시 관문 S [실행 `judge/s_result.json` `b6d174d4…0a4a`]

- 74/74(GB-7′ 61 + 해시 9 + GB-9′ 4): 어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0. GB-9′는 ps1 exit 0 또는 2.

### 3.6 G-H5′ 세 시드 [실행 `judge/gh5_result.json` `05817f9d…c894`]

- 명령(§5.1 `:235` 그대로, `-Freeze` 없음, CurrentDirectory = FRZ_K92, WMI, BelowNormal): `cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 -Name sdmpc31_v3c3_k92va_s<S> > "<OUTVA>\gh5\gh5_preflight_k92va_s<S>.out" 2>&1`. 발사 줄 `OUTVA/gh5/wmi_launch_lines.txt`(`cadb623c…`)·`VA/gates/wmi_launch_lines.txt`.
- 발사: s31 10:58:15 RV 0 cmd PID 4876, s41 10:58:49 RV 0 PID 15288, s43 10:59:23 RV 0 PID 14552. 모두 내가 띄웠고 스스로 끝났습니다. 그때 VISSIM 0. VISSIM은 뜨지 않았습니다(`-PreflightOnly`).

| # | 조건 | s31 | s41 | s43 |
|---|---|---|---|---|
| 1 | `FREEZE_VERIFIED … sha256=011f5be2… head=c20aff1d…` 1줄 | 참 | 참 | 참 |
| 2 | `LAUNCH_PLAN_DETAIL … network_sha=3de889f0 … controller=wu-link sim_period=9000 seed=<S>` 1줄, plan `tuning.sha256` = `c8e3ee2c…`, `warnings []` | 참 | 참 | 참 |
| 3 | `NETWORK_COPY_OK … 3de889f0…`, `NETWORK_OK` | 참 | 참 | 참 |
| 4 | `PREFLIGHT PROVENANCE_OK … freeze=011f5be2…` 1줄 | 참 | 참 | 참 |
| 5 | provenance `env.RW_DECISION_ERROR_POLICY` = plan `expected_env` = `hold_previous_on_exception` | 참 | 참 | 참 |
| 6 | WD 줄 `RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)` 정확히 1개 | 참 | 참 | 참 |
| 7 | `PREFLIGHT_ONLY done; no VISSIM started`, `EXIT sdmpc31_v3c3_k92va_s<S> code=0` | 참 | 참 | 참 |
| 8 | RVA에 `sdmpc31_v3c3_k92va_s<S>` 런 폴더 없음 | 참 | 참 | 참 |

- 보고: plan sha256 s31 `0ccd5613…d6cb` / s41 `35b7d437…e1c9` / s43 `cda87fae…90dc`; provenance run_id s31 `24b47ea086ad4f40940308f7273e08c0` / s41 `8a2d5457791b44db9cf734c6f01dd0fe` / s43 `5116fa7fc2a84f76be8fffcd26e84353`; plan 제어기 wu-link, 시드 = S; `REFUSED` 줄 0; 캡처 출력 sha s31 `6588cb5d…5cc5` / s41 `9349f549…fdaa` / s43 `2ce82b34…aab7`(각 22줄).

### 3.7 읽기 전용 감시 [실행 `logs/g_driver.log` `bb3f9bf4…dd2c`]

| 시점 | 결과 |
|---|---|
| FG 뒤 09:02:01 · A 뒤 09:59:42 · H 뒤 10:08:23 · B 뒤 10:58:08 | 변화 0 (FRZ_K92 캐시 0, `_preflight` 새 폴더 0) |
| G-H5′ s31·s41·s43 뒤 10:58:48 · 10:59:22 · 10:59:56 | 변화 0, `_preflight` 새 폴더 = 그때까지 시드마다 하나씩(1·2·3) |
| after 11:00:21 | 변화 0, GWT8 탄젠트 캐시 135(옮긴 뒤) |

- 시작 기준선(`snap/before_brief.json` `a52fe3b9…`): FRZ_K92 10,570파일(`FREEZE.json` 포함)·캐시 파일 0, FRZ_K8b 10,549파일·캐시 파일 229(`__pycache__` 11폴더, §2-10), `frozen/` 36항목, R-obs3 618파일, J1 런 폴더 넷(k8j1r_s31 1,015·k8j1_s31 874·k8j1_s41 1,015·k8j1_s43 1,015파일), RR 최상위 26항목, RVA 최상위 `_preflight` 하나·`_preflight` 아래 1개(PushFreeze 사전점검 `sdmpc31_v3c3_k92pre_s31_20261023_083822`), GWT8 탄젠트 캐시 135, GWT8 HEAD `c20aff1d…`. 끝(`snap/final_brief.json`): FRZ_K92 캐시 0, FRZ_K8b 캐시 229 그대로, `_preflight` 아래 4개(기존 1 + G-H5′ 3).
- 끝 확인 [실행 11:0x]: FRZ_K92 `FREEZE.json` `011f5be2…`·캐시 폴더 0, FRZ_K8b `FREEZE.json` `6143d3eb…`, `frozen/` 36항목, GWT8 HEAD `c20aff1d…`·`status --porcelain` 0줄, K8 가지 로컬·원격 `b9734abe…`, 원격 `claude/k92-b1-20261016` = `c20aff1d…`, python·VISSIM·cscript 0, C: 39.5 GB·D: 365.8 GB.

---

## 4. 하지 않은 일

- 커밋·푸시·동결·GWT8 추적 파일 수정 0. `frozen/*`·J1 런 폴더·NC3·R-obs3 쓰기 0(재생 준비는 복사). FRZ_K92 캐시 0 그대로.
- VISSIM 시작·종료 0. V-A 런 발사 0. 내가 띄우지 않은 프로세스를 끈 일 0. 이름으로 끈 일 0.
- 금지 시험 0(시험(test) 실행 자체 0). 봉인 시드 37·59·61·67 자료 열기 0, codex 64cf 숫자 0, v3c3-s47 자료 0.
- 판정 정의·문턱·목록·E_K92 변경 0. 고정 뒤 판정기 수정 0.
- 목적값·예측값·성능 숫자 열람 0(`gb7_report.json` 최대 |Δ| 칸 포함, §2-7).
- 튜닝·증거 파일 쓰기 0(경로 문자열을 그런 파일에 넣지 않음). 자식 프로세스에 긴 목록을 명령 줄로 넘긴 일 0.

## 5. 다음

- 보충 34 §5.0 `:224`·§5.1 `:238`: 독립 검증 VerifyGates(`VA/vgates/v_*.py`, 판정기·`gb7_k92decl.py`를 import하지 않고 E_K92도 §5.2 글에서 따로 다시 짬, 첫 관문 출력을 읽기 전에 sha 고정) → `VA/VERIFY_GATES_VA.md` pass = true.
- 그 뒤 §6.1 발사 전제 (4)(5)(분석 도구·감시 도구 고정)를 채우고 발사(v3c3-s31·s41·s43 9,000 s, CurrentDirectory = FRZ_K92, WMI, VISSIM PC 전체 4대 이하).

## 6. 산출물 경로와 sha256

- 이 보고서: `VA/K92_OFFLINE_GATES.md` = `VA/K92_VA_OFFLINE_GATES.md`(같은 바이트; sha256은 LOG.md와 사본 폴더 `SHA256SUMS_OFFLINE_GATES.txt`).
- 사본: `REPVA/offline_gates_report/`(이 보고서 두 이름 + `gates/` 하네스 사본 + `SHA256SUMS_OFFLINE_GATES.txt`).
- 관문 출력 전체 목록: `OUTVA/SHA256SUMS_gates.txt` (4,441줄) sha256 `40e9e58ac870b9aec12bf8155f836dd77591f51beed4951976327bca6b65edae`.
- 판정 (`OUTVA/judge/`, sha256 64자리): `fg_result.json` `e1aec788f93ec72761884eff3eb5042e2b07dd1d68ff89b7f834a5c2b1e9b7ca`, `gb7_result.json` `60e7e600c574daa3d5ac5692d2300be1680f92ffac40ca94a30fb94ac73f7c45`, `hash_result.json` `6df9bf545a9d2630866eaea0bf0da877ec68c2d3bca0251e665812144bc7d179`, `gb9_result.json` `9b938afacda81ba5eb49abd496ff14f38420a6fbac52ebb2a4df4f7b1f1e757f`, `s_result.json` `b6d174d4f282c25ff9e239b1eedf3a946fe4510c12c978c41fb0e0ea677b0a4a`, `gh5_result.json` `05817f9db4b40938b22819565cbbfb7315cff65be665a5d59ebc392c6da4c894`, `stages.json` `447155b8caadd8cdce0f06971e8d75c8c0fe90d122cc3379e48cd9d85d4dd952`, `gb7_report.json` `333d049010f4dad76c48bac30ac543d4cba5d082276f292bc22148385951492e`, `va_gates_report.json` `fd0736017b58d6de737f0db8a51357aad19d93f9c328e27d5733e652c6477fff`; 앞 16자리 `gh5_s31_result.json` `3c43c135aef03561`, `gh5_s41_result.json` `16ff708a41236b53`, `gh5_s43_result.json` `7ff927cc838f9ad4`, `guard_20261023_090149.json` `281b46e605bb99f3`.
- 로그: `OUTVA/logs/g_driver.log` `bb3f9bf4bf3c1775468d075f145ae00841befe9bbfe11110b17bb8866395dd2c`, `g_driver_1.txt` `1dbfe761bc47caf2…`; 스냅숏 `OUTVA/snap/before_brief.json` `a52fe3b91dfeac39…`, `final_brief.json` `855b6c41b12bd418…`.
- 하네스: `VA/gates/`(`va_gates_pins.sha256` `6af36e7b…b33f`, `k8b_orig/`, `copy_diffs/`, `wmi_launch_lines.txt` `7d3f3bf6…69dc`, 자기 시험 출력 `va_gates_selftest.out.txt` `a45b5ecb…663b`, `gb7_k92decl_selftest_gates.out.txt` `666cbac3…1110`, 보고 도구 출력 `gb7_report.out.txt` `5e5382b2…7d11`, `va_gates_report.out.txt` `ba1bd7ad…3f61`).
- 기록: `VA/LOG.md` "[OfflineGates]" 줄들.
