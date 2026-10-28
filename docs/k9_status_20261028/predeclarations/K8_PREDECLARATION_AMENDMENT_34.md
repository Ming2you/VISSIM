# K8 보충 34 — V-A 폐루프 3시드: 승격 K9-2-6, GB-7′ 목록 K9-2-7, 푸시·동결, 오프라인 관문(E_K92 포함), 발사, 유효성·STOP, 분석 방법 (2026-10-23)

- **상태: 검토판(ReviewDeclare, 2026-10-23).** 검토 전 판(Declare 마무리 선언판)은 `SP/K8_PREDECLARATION_AMENDMENT_34_r1.md`(sha256 `37180bedab832183453b684e70f83e3be7c58d182fa4f5248e553f2f97f9a01c`)로 보관했습니다. 검토가 바꾼 곳은 모두 §14에 적었습니다(R1–R18, V-A 데이터 0개 상태). 아래 머리 글의 "선언판" 설명은 Declare 마무리 때 글입니다.
- (Declare 마무리 때 상태 글) 첫 Declare는 V-A 데이터 0개 상태에서 막힘 둘(§2)을 찾고 초안 `VA/K8_PREDECLARATION_AMENDMENT_34_DRAFT.md`(sha256 `9ac1828e1599756867e0bcaa9a3227a20907aea9c6306c2f0a271c0908a7ab2a`)로 멈췄습니다. 사용자가 D-K9-71(GB-7′·해시 A/B에 선언 차이 E_K92 추가)과 D-K9-72(make_config 점검을 승격 전으로)를 정했습니다(§1, §10). 이 판은 그 두 결정을 §3.1·§5에 넣고, 결정 칸을 모두 채운 판입니다. 초안에서 바뀐 곳은 §13에 모두 적었습니다.
- 고정: 이 파일의 sha256은 같은 폴더 `K8_PREDECLARATION_AMENDMENT_34.md.sha256`, `VA/LOG.md`, **고정점 `VA/AMENDMENT34_FIXED.md`**(64자)에 적고, 고정 목록은 `VA/a34_pins.sha256`(§9.3; 검토가 1행을 이 판 sha로 바꾸고 검토 산출 줄을 더함, 검토 전 목록은 `VA/a34_pins_r1.sha256` 보관)에 적습니다. 그 뒤로 이 글을 고치지 않습니다. 바꿔야 하면 새 보충에 까닭을 적습니다.
- 이 글이 고정되기 전에는 어떤 단계도 하지 않았습니다(커밋·푸시·동결·관문·VISSIM 0). 이 글에는 비워 둔 칸이 없습니다. 실행 중에만 알 수 있는 값(커밋 sha, 새 동결본 이름과 `FREEZE.json` sha, 런 `run_id`)은 "그 단계 기록에서 읽어 다음 단계 기대값으로 쓴다"는 규칙으로 정했습니다(보충 22 머리와 같은 꼴).
- 구속: 보충 1–33의 규칙·식·값·문턱·관문은 이 글이 적은 자리 말고는 **모두 그대로** 구속합니다. 이 글은 V-A(보충 24 §14.2, D-K9-37·67)의 승격·동결·관문·발사·유효성·분석만 다룹니다.
- 표시: [실행] 이번에 읽기 전용 명령·작은 스크립트로 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 글은 판정 말(이기다·지다·낫다·개선 등)을 쓰지 않습니다. 관문 결과는 PASS / FAIL / 보류 / INCOMPLETE와 숫자로만 적습니다. "대기 이전"·"같은 방향"은 §8.4의 미리 정한 규칙으로만 씁니다.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`(이 단계 작업 폴더). KB = `SP/k92/bundle1`. REPVA = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`(보고 사본 자리). OUTVA = `REPVA/offline_gates`(관문 출력).
- GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, 브랜치 `claude/k92-b1-20261016`. K8 브랜치 `claude/k8-sc1001eb-defects-20261004` = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`(건드리지 않음).
- K9-2-5 = 지금 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`. K9-2-6 = 승격 커밋(§3.1). K9-2-7 = GB-7′ 목록 보충 커밋(§3.2). 둘 다 아직 없음.
- A = GB-7′ 허용 차이 경로 목록 V ∪ A_K8(K9-2-7의 `gb7_allowed.py`, R2-12 포함, 목록 sha `a8148f38…7af1`). E_K92 = 이 보충이 GB-7′ 조건 7·해시 A/B 조건 1 판정에 더하는 K9-2 선언 차이 네 경로(§5.2, D-K9-71). VBT = V-B 트리 `D:/VISSIM-merge/k8_gate_trees/k92b1/vb2_e27ceac8`(읽기만).
- FRZ_K8b = `D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821`(`FREEZE.json` sha256 `6143d3eb0d455e5fde46b190b4d4d8c2a7068a96c7fc9178126b922af937c7b6`). FRZ_K92 = K9-2-7 head로 새로 만들 동결본(이름은 도구가 `sdmpc31_<head 8자리>_<12자리 시각>` 꼴로 정함).
- CFG = `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`(지금 배포 튜닝, sha256 `d0f9ef39…aec6`, blob `268ae471…`). CFG-B1 = 묶음 1 팔 파일 `diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json`(sha256 `c8e3ee2c…1866`, blob `b6ccd50d…`).
- W = SC109 서측 직진 용량 키 `urban.sc109w_through_saturation`(값 5,209.8). H-b = (173, p4) 좌회전 헤드 하한 씨앗 키 `urban.capacity.head_floor_seed`(값 s = 1045.1612903225805). B1 = W + H-b 묶음.
- R-obs3 = `D:/VISSIM_runs/20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s31`(무제어 61결정, 읽기만). NC3 = 같은 시드 무제어 v3c3 런 `D:/VISSIM_runs/20261001_v3c3/s<S>_v3c3nc/run`. [검토 R16] NC3는 J1 정의 그대로입니다(`SP/j1/analysis/ANALYSIS_METHOD.md:9`, `:20-22`). `20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s<S>`는 러너로 돈 무제어 R-obs 런 묶음이고(s31·s43 폴더만 있음, s41 폴더 없음 [실행 2026-10-23]) NC3가 아닙니다. 이 보충에서 그 묶음은 R-obs3(v3c3-s31) 하나만 씁니다.
- J1 런(RR = `D:/VISSIM_runs/20261004_sdmpc31_k8`): v3c3-s31 = `sdmpc31_v3c3_k8j1r_s31`(재실행, FRZ_K8b `b9734abe`, 튜닝 `d0f9ef39…`, 유지 정책 켜짐), v3c3-s41 = `sdmpc31_v3c3_k8j1_s41`, v3c3-s43 = `sdmpc31_v3c3_k8j1_s43`(둘 다 FRZ_K8 `74cd495f`, 튜닝 `5f0d0e40…`, 유지 장치 없음).
- V-A = 묶음 B1을 배포한 폐루프 VISSIM 3시드 런. RVA = V-A RunsRoot `D:\VISSIM_runs\20261023_sdmpc31_k92`(§6.1).
- Ω = 제어 영역 635링크 총 통행시간(veh·h). ①–④ = K8 §5.5 네 지표. Ω 밖 = ④ − ③ 쪽. 미삽입 = 입력에서 생겼지만 망에 못 들어간 차량의 대기(재구성). remain = 런 끝 남은 그런 차량 수.
- 유지(hold) = 결정이 예외로 죽으면 직전 명령을 다시 쓰는 장치(보충 21). J1-A = 런 유효성 조건(보충 21 §4.1 개정판). H-A = 유지 감사(보충 21 §4.2).
- WD = 감시 러너 `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`. WMI = `Invoke-CimMethod -ClassName Win32_Process -MethodName Create`(세션과 떼어 띄움).
- 시드는 망 접두어를 붙여 v3c3-s31처럼 적습니다.

---

## 0. 근거 문서 [실행: sha256, 2026-10-23 06:4x–07:2x KST, 마무리 때 07:1x–07:4x KST 다시 확인·추가]

| 문서·파일 | sha256 |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` — 지금 판(D-K9-71·72까지, 232줄, D-K9-71·72 :226-232) | `6b76cc09cc0bc0ea568f219dce16900799e3b1095b0d850ecc1d442720e6af88` [실행 마무리 때] |
| 같은 파일 — 첫 Declare 때 판(D-K9-67~70, 224줄) | `d26615470469ac7264d3e01efc29b0bc6c4b7751697086ae9faad2cbe36ee49c` |
| 첫 Declare 초안 `VA/K8_PREDECLARATION_AMENDMENT_34_DRAFT.md`(+ `.sha256`, 사본 `REPVA/declare/`) | `9ac1828e1599756867e0bcaa9a3227a20907aea9c6306c2f0a271c0908a7ab2a` [실행 마무리 시작 때] |
| K8 선언 `SP/K8_PREDECLARATION.md`(§4·§5·§6) | `3330535b51a5bb3c9ea91b1ca2ccba412a891b009ecb63c111125fe5fe85b5ff` |
| 보충 21 / 22 / 23 | `ca369954977fc5f98e19b84d08932202847d37e36e26f243caa25df2d135d176` / `81cba5ae85e8d17e0b8bcd7c2f2e522c86a8bc2f2b4e19f4de3bb9de36bb459d` / `336cb9e7cce4c40fcae79f9e947aa759107e698d11089fc899ed55d9a66d9b97` |
| 보충 24(= 고정점 `KB/AMENDMENT24_FIXED.md` `fbc3d59f…` 안 값) | `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc` |
| 보충 33(= 고정점 `KB/AMENDMENT33_FIXED.md` `9254e279…` 안 값) | `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea` |
| 기존 관문 방법 `SP/j1/og/OG_METHOD.md` | `8edf86736c88b796dcc542538dadf228589fc996533379d71090c026fc2d475d` |
| J1 동결 보고 `SP/j1/FREEZE_PUSH.md` / K8b `SP/j1/fix/FREEZE_PUSH_K8b.md` | `0165b9d8cbf5710bb5ca135098a6be1bb9d4a86881c682c30d83393bfffc1d21` / `af9dfdb110894950636e262975a7143894ada64a44fcdbeb7dfef82969b50a00` |
| 관문 보고 `SP/j1/K8_OFFLINE_GATES.md` / `SP/j1/VERIFY_GATES.md` / `SP/j1/fix/GATES_K8b.md` | `e5587eff84445838ce3bbd37df7938542653a0dd5f65c2ac7a0b72afcc14ce8b` / `378945cc4b47a4ce8340c01c79d06412789eabbeef272ef064051567f3bd3282` / `733f68027a89a66fdad896633032473e51cb40bd30343a11a4622796012f34c4` |
| 발사 보고 `SP/j1/J1_LAUNCH.md` / `SP/j1/fix/S31_RERUN_LAUNCH.md` | `4b3cc4af116d0caa3954bc60cdb3075ed52a5c911eb9bb373f454db9457e9165` / `cbf479274e1db0ff6f63a027129baf769cecdca3754b2136d5ad67b311f8d41a` |
| J1 분석 `SP/j1/analysis/ANALYSIS_METHOD.md` / `J1_REPORT.md` / `VALIDITY.md` / `VERIFY_ANALYSIS.md` | `7c5ef78fbadb0084d893a6a29976f52bd255203d33cb75301e0521274b67e414` / `4bf31b134845401524c2a04032e79b41772cb0f6a8f7aef7b2d9e94d41f0bc52` / `352fa5bda12a5b60d0da317a1227d1a3c7dfcf1488ba9d3d9d0f390ddc8c7e5d` / `573ded29073f296f1f5d93c211236ce8905d8d3f791808f795a0c6bce6c1bfdc` |
| J1 단서 덧붙임 `SP/j1/J1_CAVEAT_ADDENDUM.md` | `b34849374a5fa49dab493f84c3d653e3fbe9e9cff27f97d1dc42cd224bca083b` |
| 원인 분석 `SP/j1/causes/CAUSES.md` r2 / `lens_link174.md` | `0d86ead8d4c9743f20d279c9b035478dc7939ce12e41ea79c695bb55c9ce05e0` / `ab3d5c22cb023148c555e45420b1db67d314d51eadd2859e7d540b793ce365e1` |
| K9-2 관문 `KB/GATES_K92B1.md` / `_A30` / `_A31` / `VERIFY_GATES_K92B1_r3.md` | `449b361e…0792` / `167e9e18…3556` / `e2b30183…2885` / `6fb66ac5b8de8bbd00df420bc3b1bf5364e5f95148574dd2834204e3df3ac189` |
| V-B 보고 `KB/k92_vb/K92_VB_REPORT.md` r3 / `VERIFY_VB.md` | `08bd9238ecce3c001132d6371eab0367a74373f9622457f051474921aefa1241` / `c5e0ba587df83029b6b46befa464a09f6dacbf7af266ec384bcf44bc77b40b76` |
| 설계 `KB/K9_2_DESIGN.md` r2 | `1100f7af519839beb0bd1345f8d576e2ce64d6bb01162b03eea27830d5d7ad2a` |
| GWT8 K9-2-5 파일: CFG / CFG-B1 / `k8_gates/gb7_allowed.py` / SAF-K91 | `d0f9ef39…aec6`(blob `268ae47132443a4a97e87ffa51ca7f7f0c878586`, 278,142 B) / `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`(blob `b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`, 278,607 B) / `c6f9ca1cbf1e1ac49f1bc7adf44e33add289fea5858be8f5884c7225753894c8`(blob `9fd7d5194081a089298444351072a2d058af5aef`, 11,304 B) / `5f0d0e40…3341`(blob `7b641186…`) [실행; 셋 모두 `-text`, 색인·작업 줄 끝 LF `git ls-files --eol`] |
| 러너·동결·망 도구 `D:/VISSIM-merge/tools/run_sdmpc_n31.ps1` / `freeze_worktree.ps1` / `prepare_sdmpc31_network.py` | `600423f6d751f40e269e2382d6cd93a9bd1207b63e9736ad7d2a98541e0e5100` / `d5f3c024c4efa9544a812fefc396a2488140ea32eb5279b15afd16fc675b010b` / `a4e506c33ecd88252a411ade41effe7bd42f6a019d4d58ee4cb0e52fc50b3c1a`(K8b 때와 같음) |
| 재생 도구(FRZ_K8b 사본) `make_replay_state_v2.py` / `replay_decision_n31.ps1` | 앞 16자 `4adf41cfa7569047` / `5d34109fdd61deca`(OG_METHOD §1 값과 같음; `b9734abe..e27ceac8`에서 `diagnostics/sdmpc_n31_20260924/tools/` 변경 0) |
| stage1 도구 `D:/VISSIM-merge/tools/stage1/` common / scan / uninserted / report | `e000c69e…fdae` / `651c4f51…625f` / `19eba94e…cd1` / `cb4ccc3a…b1d2`(K7 §3.6 값과 같음) |
| K8b 관문 도구 `SP/j1/fix/gates/g_driver.py` / `gjudge.py` / J1 건강 점검 `SP/j1/launch/l_health.py` | `4d4131e5…4a96` / `b9daf7cd…e8f1` / `caf9fad6…da09` |
| 이 단계 사전 점검 도구·출력 `VA/work/a34_gb7_keyon_probe.py` / `.out.txt` | `6a08c8b8a4fc6180470a0728d045046686860d1feb8bcc1320fdacd0f9580d80` / `6edf44561cb15d08932cfa1c3009cac104d3e688ca1de62addcdf74cdef4a915` |
| 이 단계 승격 전 점검 출력 `VA/work/pre_mkcfg_k92b1_check.out.txt` / `pre_obs150_arm_check.out.txt` | `41a9020a20696886ced1355cb3a3ed3b4276ed99390f183aa18ea6ae91b00963` / `7e6191adb9868ad906b89bce23c026bb2ffa7f1020fa265225a3eee0cb3345e4` |
| [마무리] 사실 확인 도구·출력 `VA/work/a34f_facts.py` / `.out.txt`(오류 출력 0 B) | `f56cf41b309299441f5a3b4079181f70413b4d5c2ab9c3342d033906474e2bd1` / `dd990bca04b34ac469076aba1b3dad8c083207a7db1734bca47e51070eec7835` |
| [마무리] **E_K92 판정 함수** `VA/gates/gb7_k92decl.py`(8,225 B) | **`d15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11`** |
| [마무리] E_K92 자기 시험·V-B 마른 점검 `VA/gates/gb7_k92decl_selftest.py`(v2, 고정판) / 출력 `gb7_k92decl_selftest_v2.out.txt` / `selftest_v2/gb7_k92decl_selftest.json`(오류 출력 0 B). v1 출력 `gb7_k92decl_selftest.out.txt`·`selftest/gb7_k92decl_selftest.json`과 바이트 같음 [실행 `fc /b`] | `e15b60a18c633e2730c6ac2a272c1d1947759eb681fc6ad3db0ec912f2219765` / `666cbac34ace9b76025c66fc655468e733935a7e69e2fc93519c62a20f3c1110` / `0601efdd1e005db899aee5ebf3efad4cb430c92ab0eefbe02f5943fb04906bf6` |
| [마무리] K9-2 증거 파일(GWT8 K9-2-5 = VBT 바이트) `diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json` / `…/k92/head_floor_seed_v3c3_robs_20261016.json` | `b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712`(blob `0399c3699c626e8bc33adc4180ce716873d8e4a1`) / `b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee`(blob `6ed42f162c71d87520fa1849c70fc80b385646a3`) [실행; 둘 다 `-text`, `i/lf w/lf`] |
| [마무리] 하한 키 기대 이름 표 `KB/a25decl/data/K92_VALUES.json` `/p0_2/f_expected_floor_keys` | `296c659562e45528606599aa4df99535faa694a86533ffca6bb2fbcde7db975a` |

- 첫 Declare 때 상태 [실행 2026-10-23 06:41–07:2x KST]: GWT8 head `e27ceac8…`, 브랜치 `claude/k92-b1-20261016`, K8 브랜치 `b9734abe…`, `git status --porcelain` 0줄, 원격 `refs/heads/claude/k92*` 0개(푸시 0), `D:/VISSIM-merge/frozen/`에 K9-2 동결 없음, RVA 없음, VISSIM·python·cscript 0개, C: 39.5 GB·D: 368.9 GB.
- 마무리 때 상태 [실행 2026-10-23 07:16–07:4x KST]: 위와 같음 — GWT8 head `e27ceac8…`, `git log b9734abe..HEAD` = K9-2-5 … K9-2-0 6개, `status --porcelain` 0줄, 원격 `claude/k92*` 0개, 원격 K8 가지 `b9734abe…`, `frozen/` 최상위에 K9-2 동결(`sdmpc31_e27ceac8_*` 또는 그 뒤 head 이름) 없음 — [검토 R1 정정] 마무리 판의 "`sdmpc31_*`는 FRZ_K7·FRZ_K8·FRZ_K8b 셋뿐"은 틀린 글이었습니다. 실제 `frozen/` 최상위는 `sdmpc31_*` 폴더 17개와 그 robocopy 로그 17개(34항목)이고 가장 늦은 것이 FRZ_K8b `sdmpc31_b9734abe_202610141821`입니다 [실행 2026-10-23 `Get-ChildItem`]. 판정 정의에는 영향이 없습니다(§4.2-11은 앞뒤 목록 차이로 셈). RVA 없음, REPVA에는 `declare/` 사본뿐, 시작 때 VISSIM·python·cscript 0개, C: 39.5 GB·D: 368.9 GB.
- **V-A 데이터는 0개입니다.** V-A 런·관문·동결이 없습니다.

---

## 1. 사용자 결정 원문 [읽음 결정 기록 :216-224·:226-232, 표 행 그대로]

| # | 질문 | 사용자 답 | 효과 |
|---|---|---|---|
| D-K9-67 | V-A 진행? | **V-A 진행 (Recommended)** | 보충 34 로 V-A 관문·분석 방법(J1 꼴: J1-A 유효성·보충 21 유지 결정 따로 셈·시드별 STOP 규칙·GB-7′ A = V ∪ A_K8 ∪ R2-12·해시 A/B·GB-9′·관문 S; 분석은 NC3 짝 d, Ω 는 ④·Ω 밖과 함께, 승패 말 없음; V-B §6 볼 것 포함)을 데이터 전 고정 → 승격·GB-7′ 목록 보충 커밋 → 새 동결 → 오프라인 관문 → v3c3-s31·s41·s43 9,000 s WMI 분리 발사(VISSIM ≤ 4) |
| D-K9-68 | 푸시 시점? | **동결 커밋 뒤 푸시 (Recommended)** | GB-7′ 목록 보충 커밋까지 만든 뒤, 폐루프 발사 전에 claude/k92-b1-20261016 푸시 |
| D-K9-69 | no_match 2결정? | **기록만, V-A 그대로 (Recommended)** | 기록으로 두고 V-A 분석에서 '직전 계획 유지' 결정이 폐루프에서도 나오는지 함께 봄 |
| D-K9-70 | V-B·검증 공개 사항 | **수용 (Recommended)** | 고정 전 요약 수치 노출, 데이터 뒤 보고용 도구 셋, 자기 시험 재실행 대신 고정 출력 확인(E1), 효과 없는 잘못 섞인 명령(E3), run_bn.py 우선순위 설정 실패(P14) 등을 기록으로 수용 |
| D-K9-71 | GB-7′·해시 A/B 의 K9-2 표지 4개는? | **판정에 선언 차이 E_K92 추가 (Recommended)** | gb7_allowed.py 는 보충 24 §14.3 그대로(R2-12 하나). 판정에 데이터 전 E_K92(보충 24 §4.2 A_K92-M·H5 꼴): 경로 4개만, 재생 쪽에만 있을 때만, 증거·u4·rule sha 조건, 하한 키는 이름·값 s(1045.1612903225805)·묶임 1.0. 그 밖 차이는 그대로 STOP |
| D-K9-72 | make_config 점검 순서는? | **점검을 승격 전으로 옮김 (Recommended)** | 승격 전 깨끗한 트리에서 make_config_n31.py --k92b1 --check(c8e3ee2c… 기대) → 팔 바이트 복사로 승격(K8-7 과 같은 길) → obs150 --check·blob·두 경로·diff 범위 점검 |

- D-K9-71·72의 근거 줄(결정 기록 :227): 초안 `9ac1828e…`의 B-1·B-2(이 글 §2). 이 보충은 D-K9-71을 §5.2에, D-K9-72를 §3.1에 넣었습니다.

---

## 2. 첫 Declare에서 찾은 막힘과 처리 (첫 Declare가 초안에서 멈춘 까닭; V-A 데이터 0)

### 2.1 막힘 B-1: GB-7′(A = V ∪ A_K8 ∪ R2-12)는 B1 배포 동결본에서 구조적으로 떨어집니다

- 사실 1 [읽음]: 키가 있으면 런타임이 **모든 결정**(무제어 포함)의 `metadata`에 `k92_w`(`evaluation/controllers/runtime_setup.py:283`, `:423`)와 `k92_hb`·`k92_hb_seed_binding`(`signal_head_observation.py:215`, `:260`, `:325`; `runtime_setup.py:415`)을 씁니다. 씨앗은 창이 없는 결정에도 (173, p4) 하한 키 `head_discharge_floor_173_p4_<해시16>`을 씁니다(보충 24 §2.2 "[검토] 나르기 판단 계수에 생기는 선언된 결과").
- 사실 2 [실행 `VA/work/a34_gb7_keyon_probe.py` → `.out.txt`]: 이미 보고가 끝난 V-B 출력에서, 같은 상태·같은 코드로 키만 다른 무제어 결정 6개(VB-41w T = 1, 150, …, 750)의 B1 대 OFF 차이를 `og_common.deep_diff`와 같은 규칙으로 내고, R2-12를 넣은 목록(메모리 안; 목록 sha `a8148f38…7af1` = 보충 24 RG-9 기대값, A_K8 35 = R1 16·R2 12·R3 7, R2-12 판정 표 6행 = 보충 24 §14.3 표)으로 나눴습니다. A 밖 경로는 다음과 같습니다(6결정 중 나온 결정 수).

| A 밖 경로 | 종류 | 결정 수 | GB-7′(R-obs3 원본 대 재생)에서 |
|---|---|---|---|
| `/metadata/k92_w` | 재생 쪽에만 | 6/6 | 61/61 결정에서 같은 꼴로 나옴 [추론: 키가 있으면 늘 씀, 원본 R-obs3는 FRZ_K7 코드라 키 없음] |
| `/metadata/k92_hb` | 재생 쪽에만 | 6/6 | 61/61 [추론, 같은 근거] |
| `/metadata/k92_hb_seed_binding` | 재생 쪽에만 | 6/6 | 61/61 [추론, 같은 근거] |
| `/metadata/head_discharge_floor_173_p4_<해시16>` | 재생 쪽에만 | 6/6 | R-obs3 v3c3-s31 원본은 이 키가 T = 900부터만 있음(이름 `head_discharge_floor_173_p4_e36d6761cfeac634` 하나, T = 900 … 9,000의 55결정 [실행 마무리 `a34f_facts.out.txt`]). 그래서 T = 1 … 750 여섯 결정에서 재생 쪽에만 나옴 [추론]. T ≥ 900은 원본 값 ≥ s이면 같음(보충 24 §5.2 :330 "씨앗이 묶이는 … R-obs3 61 중 v3c3-s31 T ≤ 750") |
| `/metadata/head_observation_groups_carried`, `/metadata/head_observation_prior_discarded` | 값 | 4/6, 1/6 | V-B **사슬**(직전 행동이 B1 앞 결정)에서만 생긴 것. GB-7′ 한 결정 재생은 직전 행동이 R-obs3 기록이라 생기지 않음(보충 24 §2.2 "한 결정 재생 … 이 일이 생기지 않습니다") [추론] |
| `/metadata/n31_binding/vsl_cohort_initialization/{sha256,source}`, `/prediction_error/source_action_json` | 값 | 5/6 | V-B 사슬의 직전 파일 경로 인공물(보충 32 닫힌 목록 꼴). GB-7′와 무관 [추론] |

- 사실 3 [실행]: 같은 6결정에서 A 안에 든 차이는 V 7, R2-02 18, R2-03 29, R2-05 3, R3-01·03·05 각 2였습니다. 즉 W·씨앗이 무제어 결정에서 바꾸는 계산 값은 이미 A의 R2 항목에 들어 있고, A 밖은 위 새 메타 키 넷(+ 사슬 인공물)뿐이었습니다.
- 결론 [추론, 근거 위]: OG_METHOD §2 조건 7(`gb7_allowed.outside(paths) == []`, `OG_METHOD.md:52`)은 FRZ_K92에서 **61결정 모두 거짓**이 됩니다. 해시 A/B 조건 1(9회 모두 GB-7′ 조건 1–8)도 같은 까닭으로 거짓입니다. D-K9-67 글자 그대로 고정하면 오프라인 관문 단계에서 반드시 STOP합니다(푸시·동결을 한 뒤).
- 보충 24 §14.3은 "R2-12 한 항목만" 더하도록 정했고 S-K17이 다른 보충을 막습니다. 보충 24·설계 r2는 T=1 길이 키 사건만 예상했고, 이 새 메타 키는 다루지 않았습니다(`K9_2_DESIGN.md:532`, `:554`) [읽음].
- 이것을 데이터 전에 고치는 길은 판정 정의를 바꾸는 일이라 첫 Declare가 고를 수 없었습니다(D-K9-67이 A를 글로 정함). → 질문 Q-A34-1 → **사용자 결정 D-K9-71**: 목록 파일은 §14.3 그대로 두고, 판정에 선언 차이 E_K92를 데이터 전에 더함. 정의·판정 함수·자기 시험은 **§5.2**.

### 2.2 막힘 B-2: K8-7 선례의 make_config 점검을 승격 뒤에 그대로 돌릴 수 없습니다

- K8-7 선례 [읽음 `git show dad555ba` 메시지]: 작업 트리에서 CFG를 팔 바이트로 바꾼 뒤, 커밋 전에 (1) `make_config_n31.py … --k91 --check`(팔 파일이 생성기 출력 그대로) (2) `scripts/build_obs150_detectors.py --tuning …/config_n31_v2.json --check`를 돌렸습니다. K9-1 팔은 `build()`에서 만들어져 CFG를 읽지 않았습니다.
- K9-2 팔 생성기는 CFG 자체를 읽습니다: `cfg_document()`가 CFG 바이트를 읽고(`make_config_n31.py:643-649`), `apply_k92b1`은 두 키가 이미 있으면 `ValueError('the K9-2 keys are already present')`를 냅니다(`:652-658`, 호출 `:723`) [읽음].
- [실행] 오늘 깨끗한 K9-2-5 트리에서 `python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --k92b1 --check` = `CONFIG_N31_K92B1_OK family=single_value sha256=c8e3ee2c…1866`. 그리고 CFG-B1 바이트(= 승격 뒤 CFG 바이트)에 `apply_k92b1`을 메모리 안에서 부르면 `ValueError the K9-2 keys are already present`입니다. 따라서 K8-7처럼 "편집 뒤·커밋 전"에 이 점검을 돌리면 반드시 오류로 끝납니다. 승격 뒤 head에서도 이 명령은 영영 오류입니다.
- [실행] 둘째 점검은 막히지 않습니다: `python -B scripts/build_obs150_detectors.py --tuning diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json --check` = `OBS150_DETECTORS_OK rows=294 sha256=108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc …`(쓰기 0; 실행 전후 GWT8 `status --porcelain` 0줄, 새 `.pyc` 0개).
- 과제 글은 "선례를 따를 수 없으면 STOP하고 선택지를 보고, 다른 승격 길을 지어내지 말라"고 정합니다. 점검 순서를 바꾸는 것도 선례와 다르므로 → 질문 Q-A34-2 → **사용자 결정 D-K9-72**: 승격 길(팔 바이트 복사)은 K8-7 그대로, make_config 점검만 바이트 복사 **전** 깨끗한 트리에서. 절차는 **§3.1**.
- 알려진 기존 실패 `test_stopline_wiring.py` ConfigFlagTests 2건(D-K9-59, 원인 = K8-7·K8-10이 CFG를 손으로 고쳐 `build()`가 재생산 못 함)은 K8-7 선례 점검이 아니라서 승격 점검에 넣지 않습니다(공개 §9-8).

---

## 3. (1) 승격 방법 — K9-2-6, K9-2-7

### 3.1 K9-2-6 승격 (K8-7·K8-10 선례: 판정한 팔 바이트를 CFG로 복사, 런타임 불변)

- 부모 = K9-2-5 `e27ceac8`. 브랜치 앞 확인(보충 24 §4.1 꼴): K8 브랜치 = `b9734abe…`, GWT8 `status --porcelain` 0줄, `git log --format=%s b9734abe..HEAD` = K9-2-5 … K9-2-0(6개, 이 순서), 원격 `claude/k92*` 없음. 하나라도 거짓이면 STOP.
- 바꾸는 파일 = **`diagnostics/sdmpc_n31_20260924/config_n31_v2.json` 하나**. 내용 = CFG-B1 바이트 복사(`Copy-Item` 또는 바이트 복사; 줄 끝 바꿈 없음).
- 기대값(지금 고정) [실행]:
  - 바뀐 뒤 CFG: sha256 **`c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`**, git blob **`b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`**, 278,607 B, LF(`-text`).
  - 바뀌기 전 CFG: sha256 `d0f9ef39…aec6`, blob `268ae471…`, 278,142 B.
  - CFG-B1 − 지금 CFG(JSON 값 차이) = 정확히 `/urban/sc109w_through_saturation`, `/urban/capacity/head_floor_seed` 두 경로(둘 다 CFG-B1 쪽에만) [실행 오늘]. 두 값 = `{evidence: diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json, evidence_sha256: b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712}`, `{evidence: …/k92/head_floor_seed_v3c3_robs_20261016.json, evidence_sha256: b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee}` [실행]. 증거 sha = 그 증거 파일 바이트 sha(커밋 때 다시 계산).
  - 유지 정책 키 `runtime.decision_error_policy` = `"hold_previous_on_exception"`이 CFG와 CFG-B1 모두에 있음 [실행].
- **순서 (D-K9-72; 하나라도 거짓이면 STOP)**. 승격 길(팔 바이트 복사)은 K8-7·K8-10과 같고, 바뀐 것은 make_config 점검의 시점뿐입니다. 출력은 `VA/promote/`에 파일로 남기고 LOG에 sha를 적습니다.
  1. **편집 전 make_config 점검 (깨끗한 K9-2-5 트리)**. 전: GWT8 HEAD = `e27ceac8…`, `status --porcelain` 0줄, 작업 CFG `git hash-object --no-filters` = `268ae471…` = HEAD blob, CFG-B1 sha256 = `c8e3ee2c…1866`. 실행: CurrentDirectory = GWT8, BELOW_NORMAL, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --k92b1 --check` → `VA/promote/pre_edit_mkcfg_k92b1_check.out.txt`·`.err.txt`. 참 조건: exit 0, 표준 출력이 정확히 한 줄 `CONFIG_N31_K92B1_OK family=single_value sha256=c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`(첫 Declare 때 같은 명령의 출력 `VA/work/pre_mkcfg_k92b1_check.out.txt` `41a9020a…`와 같은 글), 오류 출력 0 B, 실행 뒤 `status --porcelain` 0줄·새 `.pyc` 0개·CFG와 CFG-B1 바이트 그대로. 거짓이면 CFG를 바꾸지 않고 STOP.
  2. **바이트 복사**: CFG-B1 → CFG(`[System.IO.File]::Copy(<CFG-B1>, <CFG>, $true)` 또는 `Copy-Item -LiteralPath`; 줄 끝 변환 없음). 이 뒤에는 `make_config_n31.py --k92b1 --check`를 돌리지 않습니다(설계상 `ValueError`, §2.2·§9.1-7).
  3. `python -B scripts/build_obs150_detectors.py --tuning diagnostics/sdmpc_n31_20260924/config_n31_v2.json --check`(1과 같은 환경) → exit 0, `OBS150_DETECTORS_OK rows=294 sha256=108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc`로 시작하는 한 줄(첫 Declare 때 CFG-B1로 낸 출력 `pre_obs150_arm_check.out.txt` `7e6191ad…`와 같은 글), 실행 뒤 `git status --porcelain` = CFG 한 줄뿐·새 `.pyc` 0개.
  4. blob: 작업 CFG `git hash-object --no-filters` = `b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`, sha256 = `c8e3ee2c…1866`, 크기 278,607 B, CFG-B1과 바이트 같음(`cmp`).
  5. 두 경로: JSON 값 차이(작업 CFG 대 `git show e27ceac8:diagnostics/sdmpc_n31_20260924/config_n31_v2.json`) = 정확히 `/urban/sc109w_through_saturation`, `/urban/capacity/head_floor_seed`(둘 다 작업 쪽에만, 값 = 위 두 값), `runtime.decision_error_policy` = `"hold_previous_on_exception"` 있음.
  6. diff 범위: `git diff --name-status` = `M diagnostics/sdmpc_n31_20260924/config_n31_v2.json` 한 줄, `git diff e27ceac8 -- evaluation vendor plant scripts` 빈 결과, 추적 안 된 새 파일 0.
- 커밋: 경로 하나만 `git add -- <경로>`, 작성자·커미터 `git -c user.name=Ming2you -c user.email=alsrjsrb1915@snu.ac.kr commit`, amend·rebase·force·`--renormalize` 금지.
  - 메시지 첫 줄(고정): `K9-2-6: promote the bundle-1 arm config_n31_v2_k92b1.json bytes to config_n31_v2.json (V-A, runtime unchanged)`
  - 본문: 바뀐 뒤 sha·blob·크기, 바뀌기 전 sha·blob, 두 경로·증거 sha, 유지 정책 키 있음, 순서 1–6 결과 줄(1은 "make_config --k92b1 --check run on the clean K9-2-5 tree before the byte copy (D-K9-72)"), `D-K9-67`·`D-K9-72`, 보충 34 고정 sha. 마지막 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 커밋 뒤: `git ls-tree K9-2-6 <경로>` blob = `b6ccd50d…` = 작업 파일 `hash-object --no-filters`. `git diff --name-status e27ceac8 K9-2-6` = 그 한 경로. 다르면 STOP(푸시 없음).

### 3.2 K9-2-7 GB-7′ 목록 보충 (보충 24 §14.3 그대로)

- 부모 = K9-2-6. 바꾸는 파일 = `diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py` 하나. 줄 끝 LF 유지(`-text`, `i/lf w/lf` [실행]).
- [검토 R2] 편집 전: HEAD = K9-2-6(§3.1 커밋 뒤 기록 값), `status --porcelain` 0줄, 작업 파일 `hash-object --no-filters` = `9fd7d5194081a089298444351072a2d058af5aef`(= K9-2-6 ls-tree blob). 편집은 바이트로 하고(LF만), 편집 뒤 파일의 CR 0개를 셉니다.
- 넣는 것(그 밖 바이트 0):
  - R2-11 항목 튜플 바로 뒤에 한 항목: `('R2-12', 'R2', r'/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback)', '<이유>')`. 이유 문자열 = 보충 24 §14.3 글자 그대로 `어댑터 _LEGSPLIT_LAST 길이 진단 키: W_out 롤아웃 도착 유무에 따라 써짐, 계산 영향 0(ROOTCAUSE §6.1, D-K9-11·12). 재생 출력을 본 뒤 더한 항목 — D-K9-38 ④`. 소스에서는 R2-11처럼 두 줄로 써도 되지만, 이어 붙인 문자열 값은 이 글자와 같아야 합니다(목록 sha가 값을 셈).
  - 모듈 docstring의 줄 `- A_K8 항목은 "달라도 됨"이지 …` 다음 줄(`  A 밖 경로가 하나라도 다르면 … (보충 1 §E).`) 바로 뒤에 한 줄: `- R2-12는 재생 출력을 본 뒤 더한 항목입니다(보충 1 §E '재생 출력을 본 뒤에는 더하지 않음'의 사후 예외, 사용자 결정 D-K9-38 ④, 보충 24 §14.3).` (docstring은 목록 sha에 들지 않음 [읽음 `canonical()`].) [검토 R2] 이 줄 = 보충 24 §14.3 :593 따옴표 안 글자에 앞의 `- `(docstring 목록 꼴)와 끝의 `.`만 붙인 것입니다(둘 다 이 보충이 정한 꼴; 따옴표 안 글자는 바이트 그대로 [실행 `VA/a34review/rev_a34.py` `docline.a34_is_dash_a24_dot` 참]).
- 점검(S-K17; 하나라도 거짓이면 STOP):
  1. `git diff --name-status K9-2-6..K9-2-7` = 그 파일 하나.
  2. `git diff K9-2-6 K9-2-7 -- evaluation vendor plant scripts` 빈 결과.
  3. [검토 R2 정정] `python -B diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py`(CurrentDirectory = GWT8, `PYTHONDONTWRITEBYTECODE=1`) exit 0, 표준 출력이 정확히 한 줄 `GB7_ALLOWED schema=k8-gb7-allowed/v1 V=7 A_K8=35 R1=16 R2=12 R3=7 list_sha256=a8148f3849fb5e26f09d8f0a095d442aa56da051d888df0b2f657dba089e7af1`(모듈 `__main__` 꼴 그대로; 마무리 판은 `V=7 …` 부분만 적어 줄 전체와 같을 수 없었음. 기대 줄은 검토가 e27ceac8 소스 + R2-12로 메모리 안에서 다시 냄 [실행 `rev_a34.py` `list_after.print_line`]; 목록 sha는 `a34_gb7_keyon_probe.out.txt` 1행과도 같음), 실행 뒤 새 `.pyc` 0개.
  4. 판정 표(보충 24 §14.3 6행)가 그대로: `len_SC1001_W_out` → R2-12, `length_fallback` → R2-12, `req_last_SC1001_W_out` → 밖, `u_on_last` → 밖, `len_SC1001_W_out/x` → 밖, `injected_RM_C10484` → R2-11 [실행 오늘 메모리 안 같은 결과; 검토 `rev_a34.py` `table`도 같음].
  5. [검토 R2] 바이트 범위: `git diff K9-2-6 K9-2-7 -- <파일>`의 지운 줄 0, 더한 줄 = R2-12 튜플 줄(1–3줄)과 docstring 한 줄뿐. 이어 붙인 이유 문자열 값이 보충 24 §14.3 :592 따옴표 안 글자(117자, UTF-8 sha256 앞 16자 `7a51c150f6bc3cc4`)와 같음 [기대값 실행 `rev_a34.py` `reason`]. 파일 CR 0개, `git ls-files --eol` = `i/lf w/lf attr/-text`.
  6. [검토 R2] E_K92 경로 넷(`/metadata/k92_w`, `/metadata/k92_hb`, `/metadata/k92_hb_seed_binding`, `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634`)이 새 목록 A에 걸리지 않음(`which` = None). 걸리면 E_K92 조건이 그 경로에서 무의미해지므로 STOP [기대값 실행 `rev_a34.py` `E_in_A` 넷 모두 None].
- 커밋 메시지 첫 줄(고정): `K9-2-7: GB-7' allowed list entry R2-12 (leg_ramp_split length keys; amendment 24 section 14.3, D-K9-38 (4); diagnostics only)`. 본문에 새 목록 sha, 파일 sha·blob, "결과를 본 뒤의 목록 보충(D-K9-38 ④)", D-K9-12 예외는 다시 쓰지 않음. 끝 줄 Co-Authored-By.
- 커밋 뒤: ls-tree blob = 작업 파일 `hash-object --no-filters`. 새 파일 sha256을 LOG·관문 기대값(§5)에 적음.
- 공개: 이 항목은 결과를 본 뒤의 목록 보충입니다(D-K9-38 ④, 보충 24 §14.3). FRZ_K92에서는 D-K9-12 예외와 D-K9-22 "같은 사건 재적용"을 쓰지 않습니다.

### 3.3 [검토 R3] 승격 독립 검증 VerifyPromote (J1 선례: 푸시 전 `VERIFY_PROMOTE` pass = true, `SP/j1/FREEZE_PUSH.md:16`, `:44`)

- 때: K9-2-7 커밋 뒤, 푸시(§4.1) 전. 커밋·푸시·동결 0.
- 도구: `VA/vpromote/v_promote.py`(읽기 전용; `make_config_n31.py`·`gb7_allowed.py`·`build_obs150_detectors.py`·이 단계 Promote 점검 스크립트를 import하지 않음 — 목록 sha는 `git show <K9-2-7>:<gb7_allowed.py>` 소스를 자료로 읽어 `canonical()` 규칙을 따로 짜서 셈). 첫 실행 **전에** sha256을 `VA/LOG.md`와 `VA/vpromote/v_promote_pins.sha256`에 고정(`VA/a34_pins.sha256`은 검토 뒤 바꾸지 않음; 단계별 고정은 그 단계 자기 목록 파일에). 출력 `VA/vpromote/v_promote.json`, 보고 `VA/VERIFY_PROMOTE_VA.md`(+ REPVA 사본) 끝에 `pass = true|false`.
- 다시 내는 것(모두 Promote 단계 기록과 따로 계산; 하나라도 다르거나 거짓이면 pass = false → STOP, 푸시 없음):
  1. `git log --format='%H %an <%ae> %cn <%ce>' b9734abe..HEAD` = 8개, 순서 K9-2-7, K9-2-6, K9-2-5 … K9-2-0, 작성자·커미터 모두 `Ming2you <alsrjsrb1915@snu.ac.kr>`, 두 새 커밋 메시지 첫 줄 = §3.1·§3.2 고정 글, 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  2. `git diff --name-status e27ceac8 <K9-2-7>` = {M CFG, M `gb7_allowed.py`}, `git diff e27ceac8 <K9-2-7> -- evaluation vendor plant scripts` 빈 결과, K8 가지 = `b9734abe…`.
  3. K9-2-6 CFG blob = `b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`, 바이트 sha256 = `c8e3ee2c…1866` = e27ceac8의 CFG-B1 바이트; e27ceac8 CFG 대 K9-2-6 CFG JSON 값 차이 = 정확히 두 경로(둘 다 새 쪽에만), 두 값의 `evidence_sha256` = 그 증거 파일 바이트 sha256, `runtime.decision_error_policy` = `hold_previous_on_exception`.
  4. K9-2-7 `gb7_allowed.py`: 목록 sha = `a8148f38…7af1`, A_K8 35(R1 16·R2 12·R3 7), V 7, 판정 표 6행(§3.2-4), 지운 줄 0·더한 줄 범위(§3.2-5), 이유 글자 = 보충 24 §14.3 :592, E 경로 넷 A 밖(§3.2-6).
  5. 작업 트리: HEAD = K9-2-7, `status --porcelain` 0줄, 바뀐 두 경로의 `hash-object --no-filters` = ls-tree blob.
- `VERIFY_PROMOTE_VA.md`의 검증 head = 푸시할 head여야 합니다(§4.1 전 조건).

---

## 4. (2) 푸시와 동결

### 4.1 푸시 (D-K9-68: K9-2-7 뒤, 발사 전)

- 전: [검토 R3] `VA/VERIFY_PROMOTE_VA.md` pass = true이고 그 검증 head = K9-2-7(§3.3). HEAD = K9-2-7, `git log --format=%H b9734abe..HEAD` = 8개(K9-2-7, K9-2-6, K9-2-5 … K9-2-0, 이 순서), 8개 모두 작성자·커미터 `Ming2you <alsrjsrb1915@snu.ac.kr>`, 끝 줄 Co-Authored-By. 두 새 커밋의 바뀐 경로 blob = 작업 바이트. K8 브랜치 = `b9734abe…`. `status --porcelain` 0줄.
- `git push origin claude/k92-b1-20261016`(새 원격 가지 만들기; 강제 없음). 뒤: `git ls-remote origin refs/heads/claude/k92-b1-20261016` = K9-2-7 40자리. K8 원격 가지는 그대로 `b9734abe…`.
- STOP: 푸시 거부, 원격 head ≠ K9-2-7, blob 불일치, K8 가지가 움직임, [검토 R3] VerifyPromote pass가 true가 아니거나 검증 head ≠ K9-2-7.

### 4.2 동결 FRZ_K92 (`-Freeze -PreflightOnly`; 무제어 사전점검 이름)

- 전: GWT8 `status --porcelain` 0줄, HEAD = 원격 = K9-2-7. `D:/VISSIM-merge/frozen/` 최상위 목록 저장. C:·D: 8 GB 이상. 출력 폴더 `VA/freeze/`를 먼저 만듦. VISSIM 0이 아니어도 됨(사전점검은 VISSIM을 띄우지 않음).
- 실행(WMI, CurrentDirectory = `D:\VISSIM-merge\sim3-n31-k8`):
  `cmd.exe /c set "PYTHONHASHSEED=0" && set "PYTHONDONTWRITEBYTECODE=1" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_k92pre_s31 -SimPeriod 9000 -Seed 31 -Controller no-control -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 > C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\k92\va\freeze\k92_freeze_preflight.out 2>&1`
  (보충 22 §7.2와 같은 꼴, 이름·RunsRoot만 바꿈. `-PreflightOnly`는 `RVA\_preflight\<이름>_<시각>`만 만들고 런 이름을 차지하지 않음 [읽음 `FREEZE_PUSH.md:100`, `J1_LAUNCH.md` §2].)
- PASS(모두 참; 출력 파일과 사전점검 폴더 launch 로그로 셈):
  1. `FREEZE_OK … head=<K9-2-7 40자리> status_entries=0` 1줄, `FREEZE_DONE`.
  2. `FREEZE_VERIFIED … sha256=<새 FREEZE.json sha> … head=<K9-2-7>` 1줄.
  3. `LAUNCH_PLAN_DETAIL … network_sha=3de889f0 detectors=294 controller=no-control sim_period=9000 seed=31` 1줄, plan `tuning.sha256` = **`c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`**, `warnings []`, `expected_env.RW_DECISION_ERROR_POLICY` = `hold_previous_on_exception`.
  4. `NETWORK_COPY_OK … sha256=3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e sig=42`, `NETWORK_OK … sig=42`.
  5. `PREFLIGHT PROVENANCE_OK … freeze=<새 FREEZE.json sha>` 1줄; provenance `env.RW_DECISION_ERROR_POLICY` = hold, `files.tuning.sha256` = `c8e3ee2c…`, `files.network` = `3de889f0…`.
  6. WD 줄 `RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)` 정확히 1개(이 동결 사전점검 출력에서는 1개였음 [읽음 `FREEZE_PUSH_K8b.md:28`]).
  7. `PREFLIGHT_ONLY done; no VISSIM started`, `EXIT sdmpc31_v3c3_k92pre_s31 code=0`.
  8. FRZ_K92 이름 = `sdmpc31_<K9-2-7 8자리>_<12자리 시각>`. `FREEZE.json` `git.head` = 푸시 head, 브랜치 `claude/k92-b1-20261016`, `status_entries 0`.
  9. **기대 튜닝 sha**: FRZ_K92 안 CFG 파일 = FREEZE 표 = plan = provenance = GWT8 파일 = `c8e3ee2c…1866`(blob `b6ccd50d…`). FRZ_K92 안 `gb7_allowed.py` = K9-2-7 blob 바이트.
  10. 동결 차이 대조: FRZ_K92 `FREEZE.json` `files` 대 FRZ_K8b `files`의 바뀜·더함·없음 경로 집합 = `git diff --name-status b9734abe <K9-2-7>`의 M·A·D 집합과 정확히 같음. 기대: A 21, M 12(= `b9734abe..e27ceac8`의 A 21·M 10 [실행] + CFG·`gb7_allowed.py`), D 0, 합 33. 그 밖 파일 바이트 변화 0(줄 끝 포함). 바뀐 33경로의 FRZ 바이트 `hash-object --no-filters` = K9-2-7 ls-tree blob.
  11. `frozen/` 최상위 변화 = 새 동결 폴더 + 그 robocopy 로그 둘뿐. FRZ_K8b `FREEZE.json` `6143d3eb…` 그대로. 사전점검 뒤 FRZ_K92 안 캐시(`__pycache__`·`*.pyc`·`__tangentcache__`·`.pytest_cache`) 0개.
  12. 로그에 error·exception·fail·refuse·warning 낱말 0(`RW_DECISION_FAIL_FAST`·`RW_DECISION_ERROR_POLICY` 줄 제외; `FREEZE_PUSH_K8b.md:39` 꼴).
- 판정 도구: `VA/freeze/check_freeze_k92.py`(K8b `check_freeze_k8r.py` 꼴; 읽기 전용, 경로·개수·sha만 출력). 동결 실행 **전에** sha256을 LOG에 고정. 결과 `VA/freeze/check_freeze_k92.json`, 끝 줄 `ALL_OK`.
- 기록: FRZ_K92 경로, `FREEZE.json` sha256, K9-2-7 head를 LOG에 적고 다음 단계 기대값으로 씁니다. REPVA 사본 `REPVA/freeze/`.
- STOP: 위 하나라도 거짓.

---

## 5. (3) FRZ_K92 오프라인 관문 (J1 꼴: 보충 21 §8·OG_METHOD, 보충 22 §8.4에서 V-A에 맞는 것)

### 5.0 공통

- OG_METHOD §1·보충 21 §7.0 그대로: sha 확인 사본(prepare를 복사 전용으로), F17b 이력 사본(`obs150/derived_<T′>.json`, T′ = 150 … T − 150), 무거운 Python 한 번에 하나, BELOW_NORMAL, `python -B`, `PYTHONDONTWRITEBYTECODE=1`, 스레드 1, `NUMBA_CACHE_DIR = OUTVA/numba_cache`, `PYTHONHASHSEED=0`(해시 A/B만 {미설정, 0, 2}), 5분 넘는 실행은 WMI 분리·로그, 확인 간격 9분 이하, C:·D: 8 GB 밑이면 멈춤, 끊긴 뒤 재개 규칙(요약 있으면 건너뜀, 요약 없는 폴더는 `<이름>_interrupted_<시각>`으로 옮김).
- 시작 조준 검사: FRZ_K92 `FREEZE.json` sha = §4.2 기록 값, `git.head` = K9-2-7, GWT8 HEAD = K9-2-7, GWT8 `status --porcelain --ignored`(캐시 제외) 0줄, GWT8 바이트 = FRZ_K92 표(바뀜·없음·더함 0/0/0). 목록 검사: FRZ_K92 `gb7_allowed.py` 파일 sha = K9-2-7 blob 바이트 sha, `list_sha256()` = `a8148f38…7af1`, A_K8 35, V 7.
- Root: 무제어 재생(GB-7′·해시 A/B) = FRZ_K92(앞뒤 FRZ_K92 목록 대조, 바뀜 0 아니면 FAIL). SDMPC 재생(GB-9′) = GWT8 @ K9-2-7(조준 검사), 도구 = FRZ_K92 사본. 새 GWT8 탄젠트 캐시는 끝난 뒤 `OUTVA/moved_tangentcache_gwt8/`로 옮기고 목록을 남김.
- 출력: OUTVA. 묶음 폴더 이름은 `T<6자리>[_접미사]` 꼴(소문자 영숫자·밑줄).
- 블라인드: 판정 출력은 같음/다름·경로·sha·종료 코드·벽시계·개수뿐. 목적값·예측값은 판정 메모리에서만(보충 21 §6.4).
- 판정기(데이터 전 고정): `VA/gates/` 아래 K8b 도구의 사본에 기대값만 바꾼 판 — `gcommon.py`, `gprep.py`, `greplay.py`, `gjudge.py`, `g_driver.py`, `launch.ps1`, `gh5_check.py`, `gb7_report.py` — 와 **이 보충이 지금 고정하는 E_K92 판정 함수 `VA/gates/gb7_k92decl.py`(sha256 `d15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11`, §5.2)**. 사본 `gjudge.py`가 바꾸는 것은 기대값(FRZ_K92·K9-2-7·`c8e3ee2c…`)과 §5.2-4의 조건 7 연결뿐이고, K8b `gjudge.py`의 D-K9-12 예외 분기(`PROGRESS_DK912`, `gjudge.py:172-201`)는 **넣지 않습니다**(보충 24 §14.3: FRZ_K92에 D-K9-12 예외를 다시 쓰지 않음). 첫 관문 재생 **전에** 파일 sha256을 `VA/gates/va_gates_pins.sha256`과 LOG에 고정합니다. `gb7_k92decl.py`의 sha가 위 값과 다르면 STOP(S-A34-11). 자기 시험(데이터 전, 자식 프로세스 0): (i) K8b 출력(`D:/VISSIM_runs/20261001_v3c3/reports/k8/offline_gates_k8h/`, 읽기만)으로 K8b 판정 재현(K8b 프로필 = FRZ_K8b 목록 `f954c2b0…`; K8b 출력에는 E_K92 경로가 없어 `c7_A_or_EK92` = `c7_declared_A`; GB-7′ 60/61·T=1 조건 7 거짓, 해시 PASS, GB-9′ PASS, S 74/74) (ii) 합성 변조(새 키 하나 → 조건 7 거짓, CSV 1바이트 → 조건 8 거짓, 튜닝 sha → 조건 5 거짓) (iii) §5.2-6의 E_K92 자기 시험 `gb7_k92decl_selftest.py`(sha `e15b60a1…9765`)를 `--out OUTVA/selftest_ek92`로 다시 돌려 표준 출력이 Declare 때 고정 출력(`666cbac3…1110`)과 바이트 같음(목록 원천은 고정 커밋 `e27ceac8`이라 HEAD = K9-2-7에서도 같은 출력이 나와야 함; Declare 때와 같은 꼴 — `cmd /c start /belownormal /b /wait python -B …` 표준 출력 파일 받기, `PYTHONHASHSEED=0`, `PYTHONIOENCODING=utf-8:surrogateescape`(Declare 때 세션 환경 값 그대로 [실행]), `PYTHONUTF8` 미설정; 표준 출력 줄 끝 CRLF; 자식 프로세스는 `git show` 읽기뿐). 고정 뒤 판정기를 고치면 결과와 무관하게 그 관문 STOP(보충 21 S-9, 보충 24 S-K12 꼴).
- [검토 R4] **사본이 K8b 도구와 다른 곳(닫힌 목록; 위 "기대값만 바꾼 판"·"기대값과 조건 7 연결뿐"을 이 목록으로 바로잡음)**. 이 밖의 차이가 있으면 그 관문 STOP(S-A34-4).
  1. 기대값: FRZ = FRZ_K92(§4.2 기록 경로), `FREEZE.json` sha = §4.2 기록 값, HEAD = K9-2-7, 튜닝 sha = `c8e3ee2c…1866`, 목록 파일 sha = K9-2-7 `gb7_allowed.py` 바이트 sha(§3.2 커밋 기록), 목록 sha = `a8148f38…7af1`, 출력 = OUTVA. FRZ7(R-obs3 기록 루트)·K7 GB-9 벽시계 기준값·R-obs3 경로는 그대로.
  2. `gb7_row`의 조건 7 = `gb7_k92decl.judge_cond7(...)['c7_A_or_EK92']`(§5.2-4). `c7_declared_A`·`outside_A`·`outside_A_and_EK92`·`ek92_*`는 보고 칸.
  3. GB-7′ 상태 = PASS ⇔ 61행 모두 있음 + 행마다 조건 1–8 참 + **`control_fields_equal_count` = 61**(§5.1 1행 글; K8b `gb7_row`의 `ok`는 제어 7필드를 따로 세지 않고 보고만 했음 — `gjudge.py:125`, `:132-133`, `:157`). 해시 A/B도 9회 각각 `control_fields_equal` 참을 더함. 없으면 INCOMPLETE, 그 밖 FAIL.
  4. D-K9-12 분기(`PROGRESS_DK912`, `gjudge.py:172-201`)와 `DK912_PATH` 상수를 뺌.
  5. 구동기 단계 = guard → FG → A(GB-7′) → H(해시 A/B) → B(GB-9′) → S → G-H5′ 세 시드(§5.1 순서). K8b 구동기의 D(G-H2d)·GH1·R1·R2 단계와 G-H2a–c 비교(`cmp21.py`·`judge_pairs`·`gh2*_pairs`)는 넣지 않음(§5.1 아래 "다시 돌리지 않는 K8b 관문"). `gh1*.py`·`gr.py`·`gtree.py`·`cmp21.py`·`gh4_confirm.py`는 사본에 두지 않음.
  6. 읽기 전용 감시(K8b `g_driver.py:68-104` `snapshot`·`check_snap` 꼴, 단계마다 대조, 변화 있으면 STOP): FRZ_K92(캐시 포함; GB-7′·해시 A/B 앞뒤 바뀜 0), FRZ_K8b, `frozen/` 최상위 항목, R-obs3, J1 런 폴더 넷(RR 아래 `sdmpc31_v3c3_k8j1r_s31`·`sdmpc31_v3c3_k8j1_s31`·`sdmpc31_v3c3_k8j1_s41`·`sdmpc31_v3c3_k8j1_s43`), RR 최상위, RVA 최상위(G-H5′ 단계 전까지; G-H5′ 뒤에는 `_preflight` 아래 새 폴더 셋만 늘어야 함), GWT8 HEAD.
  7. 자기 시험용 K8b 프로필(FRZ_K8b·`b9734abe`·`d0f9ef39…`·목록 `f954c2b0…`·OUTH)은 (i)에만 씀. 이 프로필의 E_K92 증거 Root = FRZ_K8b(증거 파일 없음; K8b 출력에는 E 경로가 없어 증거를 읽지 않음).
- [검토 R5] 실행 위생 더함(이 워크플로 규칙, 보충 28·33 교훈): 자식 프로세스에 긴 목록(결정 T 목록·경로 목록)은 파일로 넘김(명령 줄 32,767자 한계), 프로세스별 임시 이름은 PID만으로 정하지 않음(시각 ns·난수 덧붙임; Windows PID 재사용), 관문 산출에 경로 문자열을 튜닝·증거 파일로 쓰지 않음(이 단계는 튜닝·증거 파일을 만들지 않음).
- 독립 검증(VerifyGates): 판정기·`gb7_k92decl.py`를 import하지 않는 재계산 도구 `VA/vgates/v_*.py`(E_K92도 §5.2 글에서 따로 다시 짬), 첫 관문 출력을 읽기 전에 sha 고정. 판정(선언 목록 판과 A ∪ E_K92 판 둘 다)이 하나라도 다르면 STOP.

### 5.1 관문 표 (순서대로; 앞이 FAIL·보류·INCOMPLETE면 STOP, 뒤는 돌리지 않음)

| # | 관문 | 상태·계산 | 통과 (모두 참) |
|---|---|---|---|
| FG | 동결·커밋 정합 (K8b 동결 차이 대조 꼴) | git·sha만 | FG-1 `git diff --name-status e27ceac8 <K9-2-7>` = {M CFG, M `gb7_allowed.py`}. FG-2 `git diff e27ceac8 <K9-2-7> -- evaluation vendor plant scripts` 빈 결과(런타임 코드 = K9-2 관문·V-B가 본 K9-2-5 코드). FG-3 §4.2 10항 결과 참. FG-4 FRZ_K92 재생 도구 두 파일 sha = FRZ_K8b 사본(`4adf41cf…`, `5d34109f…`) |
| 1 | **GB-7′** T5 재생 (OG_METHOD §2) | R-obs3 v3c3-s31 61결정(T = 1, 150, …, 9,000), Root = FRZ_K92, 무제어, 튜닝 = ps1이 R-obs3 provenance 경로를 FRZ_K92로 옮긴 CFG(= B1 바이트) | T마다 조건 1–8(OG_METHOD §2), 고정값: 조건 3 `FREEZE_VERIFIED … head=<K9-2-7>`, 조건 4 root = FRZ_K92·run_root = FRZ_K7·rebased·`REBASE` 줄·`workspace_root` = FRZ_K92, 조건 5 재생 provenance `inputs.tuning_json.sha256` = `c8e3ee2c…`, 조건 6 상시 관문 S, **조건 7 = 원본 대 재생 action JSON 차이가 모두 A ∪ E_K92 안(§5.2; `gb7_k92decl.judge_cond7(...)['c7_A_or_EK92']` 참, 하한 키 기대 이름 `head_discharge_floor_173_p4_e36d6761cfeac634`, 증거 Root = FRZ_K92)**, 조건 8 CSV 바이트 같음; 그리고 제어 7필드(`CONTROL_FIELDS`) 61/61 같음. 61/61이면 PASS. 보고만: OG_METHOD §2 (a)(b)(결정 기록 NOTES 3번), A 항목별·E1–E4별 적중 수, **선언 목록 A만의 조건 7 결과(`c7_declared_A`; 61/61 거짓이 예상, §2.1)**, A 밖 경로 목록과 A ∪ E_K92 밖 경로 목록(값 없음), E_K92 조건별 참거짓 |
| 2 | **해시 A/B** (OG_METHOD §3) | T ∈ {4,050, 4,500, 9,000} × `PYTHONHASHSEED` ∈ {미설정, 0, 2}, Root = FRZ_K92, 9회 | 9회 모두 1번 관문의 T마다 조건(**조건 1의 GB-7′ 조건 7 = 1번과 같은 A ∪ E_K92 정의, 같은 함수·같은 기대 이름·같은 Root**), 같은 T에서 미설정 대 0·미설정 대 2 action JSON 차이가 V 밖에 없음·CSV 바이트 같음(이 비교는 재생 대 재생이라 E_K92를 쓰지 않음, OG_METHOD §3 조건 2 그대로), 환경 `PYTHONHASHSEED`가 의도대로. 보고만: 9회 각각의 `c7_declared_A` |
| 3 | **GB-9′** 반사실 SDMPC (OG_METHOD §4) | T ∈ {900, 2,700, 4,950, 6,300}, 각 1회, `PYTHONHASHSEED=0`, `wu-link`, 직전 행동 = R-obs3 `action_<T−150>`, Root = GWT8 @ K9-2-7, 튜닝 = GWT8 CFG(= `c8e3ee2c…`) | 상태마다: 상시 관문 S(어댑터 exit 0, `*.error.txt` 0, `DECISION_FAILED` 0, ps1 exit 0 또는 2), 유효성(`replay_run.controller` = wu-link, `sdmpc_active` 참, 튜닝 인자 파일 sha·재생 provenance `inputs.tuning_json.sha256` = `c8e3ee2c…`, `workspace_root` = GWT8, `workspace_git_commit` = K9-2-7), 결정 벽시계 (가) `replay_run.json wall_sec` ≤ 1,005.0 / 859.95 / 996.0 / 974.4 s, (나) `metadata.decision_wall_sec` ≤ 985.6443465 / 841.0834455 / 975.7478355 / 955.3794375 s(= 1.5 × K7 GB-9 r1 같은 상태, OG_METHOD §4 표 그대로). 4/4면 PASS. 보고만: action metadata에 `k92_w`·`k92_hb` 있음, `k92_hb_seed_binding` 값, (173, p4) 하한 키 이름 수(목적값·예측값은 출력하지 않음) |
| 4 | **상시 관문 S** (OG_METHOD §5) | 1–3의 재생·반사실 74회 | 74/74 S 참 |
| 5 | **G-H5′** 발사 출처 (보충 21 §7.5 꼴, 시드마다) | `run_sdmpc_n31.ps1 -PreflightOnly`(`-Freeze` 없이), CurrentDirectory = FRZ_K92, `-Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 -Name sdmpc31_v3c3_k92va_s<S>`, WMI, `PYTHONHASHSEED=0`, S = 31·41·43 하나씩 | 1 `FREEZE_VERIFIED … head=<K9-2-7>`·sha = FRZ_K92. 2 `LAUNCH_PLAN_DETAIL … network_sha=3de889f0 … controller=wu-link sim_period=9000 seed=<S>`, plan `tuning.sha256` = `c8e3ee2c…`, `warnings []`. 3 `NETWORK_COPY_OK … 3de889f0…`, `NETWORK_OK`. 4 `PREFLIGHT PROVENANCE_OK … freeze=<FRZ_K92 sha>`. 5 provenance `env.RW_DECISION_ERROR_POLICY` = hold, plan `expected_env` 같음. 6 WD 정책 줄 정확히 1개. 7 `PREFLIGHT_ONLY done; no VISSIM started`, `EXIT … code=0`. 8 RVA에 `sdmpc31_v3c3_k92va_s<S>` 런 폴더 없음(사전점검이 이름을 차지하지 않음) |

- **다시 돌리지 않는 K8b 관문과 까닭** [읽음 `GATES_K8b.md` §0]: G-H0·G-H4·G-H1·G-R0·G-R1·G-R2·G-H3는 K8-8·K8-9·K8-10 코드 변경을 시험한 관문이고, G-H2a–d는 "같은 코드·같은 튜닝이면 새 동결 출력 = 옛 동결 출력"을 본 관문입니다. V-A 동결은 런타임 코드가 K9-2-5와 같고(FG-2), 키 끔 = `b9734abe`는 K9-2 관문 G-K0(D-a GB-7′ 61 대 OUTH `gb7/A` 포함)·J-0·J-a·J-b가 이미 보였으며, 튜닝은 일부러 바꿨으므로 G-H2 꼴 동일성은 성립할 수 없습니다. 그래서 FG로 대신합니다.
- 결과 처리: 다섯 관문(FG·1·2·3·4)과 G-H5′ 세 시드가 모두 PASS이고 [검토 R18] 독립 검증 `VA/VERIFY_GATES_VA.md` pass = true일 때만 발사(§6, §6.1 발사 전제). 하나라도 FAIL·보류·INCOMPLETE면 STOP, 정확히 보고, 사용자 결정. 결과를 본 뒤 조건·문턱·목록·판정기를 바꾸지 않습니다.
- 보고: `VA/K92_VA_OFFLINE_GATES.md`(+ REPVA 사본), 독립 검증 `VA/VERIFY_GATES_VA.md`. GB-7′·해시 A/B 줄에는 "선언 목록 A 기준" 결과와 "A ∪ E_K92 기준" 결과를 나란히 적고, 관문 PASS/FAIL은 뒤의 것으로 셉니다(D-K9-71).

### 5.2 E_K92 — GB-7′ 조건 7과 해시 A/B 조건 1에 더하는 K9-2 선언 차이 (D-K9-71, 데이터 전 고정)

1. **목록은 그대로**: `gb7_allowed.py`는 보충 24 §14.3대로 R2-12 한 항목만 더합니다(§3.2, 목록 sha `a8148f38…7af1`). E_K92는 목록 파일에 넣지 않고, 판정 함수 `VA/gates/gb7_k92decl.py`(sha256 `d15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11`)에만 있습니다.
2. **꼴**: 보충 24 §4.2 A_K92-M(한쪽에만 있는 새 메타 하위 트리, 결정적 잎은 미리 고정한 sha와 같을 때만)과 H5 선언 차이(하한 키 이름·값 s·그 결정의 묶임 1.0)를 GB-7′의 "원본 = R-obs3(FRZ_K7 코드, 키 없음) 대 재생 = FRZ_K92(B1 키 켬)"에 옮긴 것입니다. 차이 경로 꼴은 `gjudge.raw_diff`(= OG_METHOD §2의 K7 `deep_diff`) 그대로입니다.
3. **정의 (정확히 네 경로; 모든 조건이 참일 때만 그 경로가 E_K92 안)**. 공통 조건: 차이 종류가 `presence`이고, 원본 `metadata`에 그 키가 없고 재생 `metadata`에 있음(= "재생 쪽에만").

| 항목 | 경로 (정확히) | 더한 조건 (재생 쪽 값) |
|---|---|---|
| E1 | `/metadata/k92_w` | dict; `evidence_sha256` = `b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712` **이고** = 증거 Root의 `diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json` 바이트 sha256; `u4_sha256` = `22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b`; `after`가 float이고 repr = `5209.8` |
| E2 | `/metadata/k92_hb` | dict; `evidence_sha256` = `b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee` **이고** = 증거 Root의 `diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json` 바이트 sha256; `rule_code_sha256` = `d9bd53920eea89ace2b71a589d780069c3c7191be889aca894994ddf65bcc106` |
| E3 | `/metadata/k92_hb_seed_binding` | float이고 0.0 또는 1.0 |
| E4 | `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634` | 이름이 정확히 이것(R-obs3 v3c3-s31 기록 이름, T = 900 … 9,000 [실행]); float이고 repr = `1045.1612903225805`(= s); **그리고 그 결정 재생 쪽 `metadata.k92_hb_seed_binding`이 float 1.0** |

   - 이 넷 밖의 A 밖 경로, 또는 조건 하나라도 거짓인 이 네 경로 → 그 결정의 조건 7 거짓 → GB-7′(또는 해시 A/B) FAIL → STOP(D-K9-71 "그 밖 차이는 그대로 STOP"). 양쪽에 있고 값이 다른 경우(초안의 E4 (ㄴ) = 보충 24 H5 (나) 꼴 포함), 원본 쪽에만 있는 경우, 이름의 해시16이 다른 하한 키, 새 `k92_*` 키는 모두 E_K92가 아닙니다.
   - 증거 Root = 그 재생의 Root = FRZ_K92(GB-7′·해시 A/B). FRZ_K92의 두 증거 파일 바이트는 K9-2-7 blob(`0399c369…`, `6ed42f16…`)과 같아야 합니다(§4.2-10·FG-3).
   - T ≥ 900에서 원본에도 하한 키가 있으면, 재생 값이 원본과 같아 그 경로는 차이로 나오지 않는 것이 예상입니다(보충 24 §5.2 :330 "R-obs3 61 중 v3c3-s31 T ≤ 750"만 씨앗이 묶임) [읽음]. 그때 `k92_hb_seed_binding`은 0.0일 수 있고(E3이 0.0을 받음), 값이 다르면 FAIL입니다. [검토 R17] 근거 보탬: K9-2 관문 J-0(R-obs3 61 포착, SAF-K91 대 SAF-K92b1)이 씨앗 묶임을 R-obs3에서 T = 300·450·600·750 넷으로만 셌습니다(T = 1·150은 그 하네스에서 두 팔 같은 초기화 실패라 셈 밖) [읽음 `KB/GATES_K92B1.md:67`]. J-0의 바탕 튜닝은 SAF-K91이고 GB-7′는 CFG-B1이라 같은 양이 아닙니다 [추론: 지지값은 관측 창의 통과율에서 오고(`signal_head_observation.py:216-257`), base(키 끔 좌회전 용량 413.06…, 보충 24 §2.2 B2)는 두 튜닝 모두 s보다 작으므로 묶임이 같을 것으로 봄, 시험하지 않음]. 다르면 결과를 본 뒤 조건을 바꾸지 않고 FAIL → STOP입니다(§11-2b).
4. **판정기 연결**: 사본 `gjudge.py`의 `gb7_row`는 원본·재생 action JSON을 읽은 뒤 `gb7_k92decl.judge_cond7(a, b, G, <FRZ_K92>, floor_key='head_discharge_floor_173_p4_e36d6761cfeac634')`를 부르고, `r['c7_diff_in_A']` = 그 결과의 `c7_A_or_EK92`(판정에 씀), `r['c7_declared_A']` = `c7_declared_A`(보고만), `r['diff_outside_A']` = `outside_A`, `r['diff_outside_A_EK92']` = `outside_A_and_EK92`, `r['ek92']` = `ek92_hits`·`ek92_checks`를 적습니다. 적중 수는 `gb7_k92decl.which(path, G, floor_key, <조건을 채운 E 경로>)`로 셉니다. `judge_hash`는 같은 `gb7_row`를 씁니다. G = FRZ_K92 `gb7_allowed.py` 모듈(시작 목록 검사 뒤).
5. **블라인드**: 함수 출력은 경로·차이 종류·참거짓·개수·목록 sha뿐입니다. 값(5,209.8·s 포함)은 비교에만 쓰고 출력하지 않습니다.
6. **자기 시험과 마른 점검 [실행, Declare 마무리 2026-10-23 07:2x–07:4x KST, V-A 데이터 0]**: 두 번 돌렸습니다. 둘 다 BELOW_NORMAL·`python -B`·`PYTHONHASHSEED=0`, exit 0, 끝 줄 `ALL_OK`, 오류 출력 0 B, 기대는 실행 전 docstring에 적고 실행 전 도구 sha를 LOG에 고정, 판정 함수는 같은 바이트(`d15e9cc0…fb11`).
   - v1(`9a079ec3c5278e38a4bd38d4f4f3c5f8a9d96eae597555406483469bd4986087`, 목록 원천 = GWT8 HEAD = K9-2-5): 출력 `gb7_k92decl_selftest.out.txt` `666cbac34ace9b76025c66fc655468e733935a7e69e2fc93519c62a20f3c1110`, `selftest/gb7_k92decl_selftest.json` `0601efdd1e005db899aee5ebf3efad4cb430c92ab0eefbe02f5943fb04906bf6`.
   - v2 = 고정판(`e15b60a18c633e2730c6ac2a272c1d1947759eb681fc6ad3db0ec912f2219765`): v1을 제자리에서 고친 판(v1 바이트는 보관하지 않음, sha는 LOG). 고친 것은 관문 단계 다시 돌리기를 위한 세 가지뿐 — 목록 원천을 HEAD 대신 고정 커밋 `e27ceac8`(관문 때 HEAD = K9-2-7에는 R2-12가 이미 있어 v1은 `LIST_SHA_MISMATCH`로 멈춤), 합성 Root 증거를 같은 커밋 blob에서, `--out` 인자. `--out VA/gates/selftest_v2`로 돌린 출력 `gb7_k92decl_selftest_v2.out.txt`·`selftest_v2/gb7_k92decl_selftest.json`이 v1 출력과 바이트 같음(`666cbac3…`, `0601efdd…`) [실행 `fc /b`].
   - 목록 = K9-2-5 목록 + R2-12(메모리 안) = `a8148f38…7af1`.
   - (가) 합성 21사례 모두 기대와 같음: 참 3(S01 네 경로 재생 쪽에만; S02 T ≥ 900 꼴 = 하한 키 양쪽 같음·묶임 0.0; S18 A 안 차이만 — V·R2-12, 이때만 `c7_declared_A`도 참), 거짓 18(S03 W 증거 sha 바뀜, S04 u4 sha, S05 `after` = 5209.800000000001, S06 H-b 증거 sha, S07 rule sha, S08 Root 증거 파일 1바이트 다름, S09 `k92_w` 양쪽·하위 값 다름, S09b 묶임 양쪽·값 다름, S10 묶임 2.0, S10b 묶임 정수 1, S11 하한 키 해시16 다름, S12 s보다 1 ulp 큼(`1045.1612903225807`), S13 하한 키인데 묶임 0.0, S14 양쪽·원본 < s·재생 = s, S15 목록 밖 새 `k92_other`, S16 하한 키인데 묶임 키 없음, S17 `k92_w`가 dict 아님, S19 `k92_w` 원본 쪽에만).
   - (나) V-B 마른 점검(보고 끝난 V-B 출력, 읽기만): VB-41w 무제어 6결정(T = 1, 150, …, 750), 원본 역할 = OFF, 재생 역할 = B1, 증거 Root = VBT, 하한 키 기대 이름 = 그 런(J1 v3c3-s41)의 이름 `head_discharge_floor_173_p4_301ceabb95f116fa`(`K92_VALUES.json` `/p0_2/f_expected_floor_keys`). 결과 = 실행 전 기대와 6/6 같음: E1·E2·E3은 6결정 모두 E_K92 안; E4는 T = 1·150에서 안, T = 300 … 750에서는 `binding_is_float_1`만 거짓(사슬에서 앞 B1 결정이 하한 키 = s를 날라, s가 max(base, carried)보다 엄격히 크지 않음 — [검토 R12] 마무리 판의 낱말을 메커니즘 글로 바꿈; GB-7′ 한 결정 재생은 앞 행동이 키 없는 R-obs3 기록이라 이 나르기가 없음 [추론, `signal_head_observation.py:204`, `:209-215`, `:258-260`]); A ∪ E_K92 밖에 남은 것 = T=1 없음(조건 7 참), T=150 사슬 4경로(`head_observation_prior_discarded`, `n31_binding/vsl_cohort_initialization/{sha256,source}`, `prediction_error/source_action_json`), T=300 … 750 사슬 4경로(`head_observation_groups_carried` + 같은 셋) + E4 하한 키. 같은 자료를 FRZ_K92 기대 이름(`e36d6761…`)으로 보면 B1 하한 키(`301ceabb…`)가 6/6 A ∪ E_K92 밖에 남음(이름 조건이 실제 자료에서 걸림).
   - 이것은 판정 도구 시험이지 관문이 아닙니다. 사슬 경로는 V-B 사슬의 인공물이고(§2.1 표), GB-7′ 결과를 미리 말하지 않습니다.
7. **바꾸지 않는 것**: OG_METHOD §2 조건 1–6·8, 제어 7필드, 61/61 규칙, 해시 A/B 조건 2·3, GB-9′·S·G-H5′, 목록 `gb7_allowed.py`(R2-12만), STOP 규칙. E_K92는 GB-7′ 조건 7과 해시 A/B 조건 1(그 안의 조건 7)에만 씁니다.

---

## 6. (4) V-A 런

### 6.1 대상·이름·조건 (지금 고정)

| 시드 | 런 이름 | RunsRoot |
|---|---|---|
| v3c3-s31 | `sdmpc31_v3c3_k92va_s31` | `D:\VISSIM_runs\20261023_sdmpc31_k92` |
| v3c3-s41 | `sdmpc31_v3c3_k92va_s41` | 같음 |
| v3c3-s43 | `sdmpc31_v3c3_k92va_s43` | 같음 |

- [검토 R18] **발사 전제(모두 참일 때만 첫 발사; 하나라도 거짓이면 발사 없이 STOP·보고)**: (1) `VA/a34_pins.sha256` 대조 모두 OK, 이 보충 sha = 고정점 `VA/AMENDMENT34_FIXED.md` 64자 값; (2) §3.3 VerifyPromote pass = true, §4.1 푸시·§4.2 동결 PASS; (3) §5 관문 FG·1–5와 G-H5′ 세 시드 PASS, 독립 검증 `VA/VERIFY_GATES_VA.md` pass = true(J1 선례 `SP/j1/VERIFY_GATES.md`); (4) §8.0-2 분석 도구·`ANALYSIS_METHOD_VA.md`와 §8.0-3 검증 도구 sha 고정 끝; (5) `va_monitor.py`·`va_health.py`·`k92va_s43_watcher.ps1`(드라이런 8건 끝) sha 고정 끝(§6.2–§6.4가 이미 "발사 전"으로 정함; `VA/validity/va_j1a.py`는 §9.3대로 유효성 단계 첫 계산 전); (6) C:·D: 8 GB 이상, K8 가지 = `b9734abe…`. (4)는 J1보다 이릅니다(J1은 런 뒤·성능 숫자 열기 전에 방법 문서를 고정). 이 보충이 처음부터 "첫 V-A 발사 전"으로 정했고(§8.0-2) 검토는 이를 늦추지 않습니다.
- RVA는 지금 없습니다 [실행]. 동결 사전점검(§4.2)이 처음 만듭니다. 런 이름 폴더가 발사 때 이미 있으면 STOP(다른 이름을 지어 쓰지 않음).
- 조건: `-SimPeriod 9000`, `-Seed <S>`, `-Controller wu-link`, 예열 no-control(T = 1 … 750), ControlStartSec 900, `-Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json`(= B1 바이트 `c8e3ee2c…`), CurrentDirectory = FRZ_K92, `PYTHONHASHSEED=0`. 세 시드 모두 s31 망 파일에 시드를 COM으로 덮음(K8 §5.6-6 그대로). v3c3-s47·봉인 시드는 쓰지 않음.
- 발사 줄(WMI, J1 꼴; 보충 22 §9.4):
  `Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = 'cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_k92va_s<S> -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 [-AllowConcurrentDev] > D:\VISSIM_runs\20261023_sdmpc31_k92\wmi_sdmpc31_v3c3_k92va_s<S>.log 2>&1'; CurrentDirectory = '<FRZ_K92>'}`
  러너는 WD에 `-NoGlobalKill -MaxAttempts 1`을 넘깁니다(`run_sdmpc_n31.ps1:115`) [읽음]. 이름으로 끄지 않고, 내가 띄우지 않은 프로세스는 건드리지 않습니다.
- 발사 기록: `RVA\wmi_launch_lines.txt`에 J1 꼴 한 줄(`<ISO 시각>  k92va_s<S>  RV=<값> PID=<값> VISSIM_before=<n> dev_before=<n> cwd=<FRZ_K92> head=<8자리> flag=<none|-AllowConcurrentDev> | <명령>`), 같은 줄을 `VA/launch/wmi_launch_lines.txt`에도.
- STOP: `ReturnValue` ≠ 0, launch 로그 `REFUSED`·`NOT_LAUNCHED`, 런 폴더가 이미 있음.

### 6.2 발사 순서와 좌석 (VISSIM PC 전체 ≤ 4)

- 좌석 규칙 [읽음 `run_sdmpc_n31.ps1:25-29`, `:84-86`]: 플래그 없음 = PC 전체 VISSIM ≤ 3이고 dev 0. `-AllowConcurrentDev` = 전체 ≤ 2이고 dev ≤ 1. 러너가 플랜 전과 VISSIM 직전에 두 번 셉니다. 그래서 dev 런은 동시에 많아야 2개입니다.
- 순서(K8 §5.2 꼴): (1) v3c3-s31 — 좌석이 "플래그 없음" 조건이면 발사, 아니면 기다림. (2) s31의 VISSIM 창 제목이 보이고 시뮬레이션이 시작된 뒤(runlog `NATIVE_SIM_PROGRESS sim_sec=1`) v3c3-s41을 `-AllowConcurrentDev`로 — 좌석 조건이 맞을 때만. (3) v3c3-s43은 감시기가 띄웁니다.
- 좌석이 없으면 기다립니다(9분 이하 간격으로 다시 셈). 좌석을 비우려고 무엇도 끄지 않습니다. 발사 직후 PC 전체 VISSIM이 5개 이상이면 아무것도 끄지 않고(내 런 포함) 곧바로 사용자에게 알림(질문 지점).
- s43 감시기 `RVA\k92va_s43_watcher.ps1`: J1 `j1_s43_watcher.ps1`(`d388f498…`)의 규칙을 이름·PID만 바꿔 씀 — 끝남 = 러너 자기 로그 `EXIT <런> code=N` 줄 **그리고** 발사 cmd PID(생성 시각까지 맞는 것)가 없음; 좌석·플래그 = V-A 하나가 아직 돌면 `-AllowConcurrentDev`(전체 ≤ 2, dev ≤ 1), 하나도 안 돌면 플래그 없이(전체 ≤ 3, dev 0), 그 밖은 기다림; 20 s 간격 두 번 맞아야 발사; 잠금 `k92va_s43_watcher.lock`(`CreateNew`)·기록 파일·런 폴더로 두 번 발사 막음; 멈춤 파일 `RVA\STOP_K92VA_S43`; C: < 8 GB 또는 D: < 30 GB면 기다림; 36 h 지나면 `GIVE_UP`; kill 코드 없음. 발사 전 드라이런 8건(J1 `J1_LAUNCH.md` §5.2 T1–T8 꼴, 발사·잠금·기록 0)을 돌리고 감시기 sha를 LOG에 고정합니다.
- [검토 R7] 감시기를 띄우는 때와 가장자리(J1은 s31·s41 둘 다 뜬 뒤 감시기를 띄움, `J1_LAUNCH.md` §1·§5):
  - 감시기는 s31·s41 둘 다 발사되고 두 발사 cmd PID(생성 시각 포함)를 안 뒤에만 띄웁니다. 감시 대상 = 그 두 런.
  - s41이 좌석 때문에 못 뜬 채 s31이 끝나면(EXIT 줄 + PID 없음): s41을 그때 좌석 규칙대로 발사합니다(V-A 런이 돌지 않으므로 플래그 없음 조건). 그 뒤 감시기를 띄우되 감시 대상은 s41 하나이고, s43은 s41이 끝난 뒤 같은 규칙으로 띄웁니다. 감시기 꼴·드라이런은 같음(대상 수만 다름, 발사 전 다시 고정).
  - 러너가 `EXIT` 줄 없이 죽은 런은 감시기가 "끝남"으로 보지 않습니다(J1 `ABNORMAL_NO_EXIT_LINE` 꼴). 그 런은 실패 시드 후보이고(§7.1) S-VA-7로 보고합니다.
  - s31(또는 위 경우의 s41) 발사를 좌석 때문에 24 h 넘게 기다리면 질문 지점입니다(STOP 아님, 계속 기다림, 아무것도 끄지 않음). 감시기의 36 h `GIVE_UP`도 질문 지점입니다(S-VA-6).

### 6.3 감시 (블라인드)

- `watch_sdmpc.py` 결정 줄은 목적값을 찍으므로 쓰지 않습니다(보충 21 S-11 꼴). 감시는 `VA/launch/va_monitor.py`(읽기 전용, 발사 전 sha 고정)로만 하고, 출력은 결정 T 목록·개수, runlog `CONTROLLER_DECISION`의 `exit=`·`wall_sec`, 파일 있음/없음·크기·mtime, 유지 줄(`DECISION_HOLD_ATTEMPT`·`DECISION_HELD_ON_EXCEPTION`·`ERROR=`) 수·sim_sec·첫 토큰, 유지 영수증의 바깥 형·root 형 이름과 숫자를 지운 메시지, `STAGE=`·`EXIT` 줄, 건강 점검 참/거짓뿐입니다. 목적값·예측값·녹색·가격·Ω·TTT·지연은 내지 않습니다. 런 파일은 5분 넘게 지난 것만 `REPVA/live/<런>/`로 복사한 뒤 읽습니다. 확인 간격 9분 이하.
- 유지를 처음 보면(어느 T든) 곧바로 그 T·형 이름·숫자 지운 메시지·보충 21 §5-9 표시를 메인 세션 보고에 적습니다. 무효가 아니고 런은 계속됩니다(D-K9-14).
- 멈춘 런은 WD `StallSec` 2,400이 끝냅니다(보충 21 P-8). 내가 따로 끄지 않습니다. 그렇게 끝난 런은 무효입니다(보충 22 §9.5 꼴, §7.1 실패 시드).
- [검토 R6] WD가 끝내지 못하는 멈춤: 감시에서 그 런의 런로그·launch 로그·결정 폴더 모두 4,800 s(= 2 × `StallSec`) 넘게 새 줄·새 파일이 없고 `EXIT` 줄도 없으며 발사 cmd PID가 살아 있으면 → S-VA-7(STOP·알림, 아무것도 끄지 않음, 런을 끝낼지는 사용자 결정, 끝낼 때도 내가 띄운 PID만).

### 6.4 첫 SDMPC 결정 건강 점검 (T = 900, 런마다; `VA/launch/va_health.py`, 발사 전 sha 고정)

| # | 항목 | 기대 |
|---|---|---|
| H1 | `action_000900.json`·`.csv`·`.json.applied` | 있음 |
| H2 | `metadata.sdmpc_active` | 참 |
| H3 | `stopline_approach_install_check` 있음·`passed` | 참 |
| H4 | S6 캡처 `action_000900.stdout.txt`·`.stderr.txt` | 둘 다 있음 |
| H5 | decisions 폴더 `*.error.txt` | 0 |
| H6 | `DECISION_FAILED` (runlog·runlog.err·launch·wmi·stdout·stderr) | 0 |
| H7 | 예산 필드 `unlimited_time`·`expired_stage`·`output_completed` | 참·null·참 |
| H8 | 결정 수(T = 1 … 900) | 7 |
| H9 | 런로그 `DECISION_ERROR_POLICY=hold_previous_on_exception` | 1줄 |
| H10 | launch 로그 WD 줄 `RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)` | **WD 호출마다 1줄 = 2줄(사전점검·실행), 모두 hold, strict 0** — D-K9-25 읽는 법을 이번에는 데이터 전에 고정 |
| H11 | `FREEZE_VERIFIED … head=<K9-2-7 40자리>` | 1줄, sha = FRZ_K92 |
| H12 | `PROVENANCE_OK … freeze=<FRZ_K92 sha>` | 그 시점 1줄(사전점검 줄) |
| H13 | 런 provenance 튜닝 sha | `c8e3ee2c…1866` |
| H14 | `action_000001.json` metadata: `k92_w`(`after` = 5209.8, repr `5209.8`)·`k92_hb` 있음, `head_discharge_floor_173_p4_*` 키 정확히 1개·값 repr `1045.1612903225805`, `k92_hb_seed_binding` = 1.0 | 참 (B1이 실제로 배포됐는지; V-B VB-41w T=1과 같은 꼴 [실행 오늘 키 이름 읽기]) |
| H15 | `action_000150.json` `metadata.head_observation_prior_discarded` | **1.0** (보충 24 §2.2·§2.6-12·§14.2의 선언된 예상 값; 계산 영향 0) |
| H16 | `action_000900.json` metadata `k92_w`·`k92_hb` 있음, 하한 키 이름 = H14 이름 | 참 |
| T1·T2 | T = 900 exit 0, 유지·오류 없음 | 참 |

- 건강 점검 실패 → STOP, 곧바로 사용자에게 알림. 런을 끝낼지는 사용자 결정(끝낼 때도 내가 띄운 PID만).
- H14–H16은 성능 숫자가 아닙니다(키 있음·고정 값 repr·계수).

### 6.5 기대 벽시계 [읽음·추론]

- J1 런 벽시계(`WATCHDOG_EXIT wall_sec`) 30,699 / 30,045 / 33,055 s(8.5 / 8.3 / 9.2 h), SDMPC 결정 중앙 469.6 / 409.6 / 490.0 s, 최대 587.5 s [읽음 `J1_REPORT.md:408-410`].
- B1 키가 결정 시간을 늘린다는 근거는 없습니다: 키 끔 짝 벽시계 비 중앙 ≤ 1.0158(G-K5 PASS), V-B 훅 켬 사슬 SDMPC 중앙 B1 710.4 s 대 OFF 733.5 s(오프라인, 재는 자리가 다름) [읽음 V-B 보고 §3.7].
- 기대: 런 하나 약 8.5–10 h. s31·s41 동시 → 약 9–10 h, s43는 그 뒤 → 전체 약 18–21 h [추론]. 결정 하나가 2,400 s를 넘으면 WD가 런을 끝냅니다(무효).
- 디스크: 런 하나 약 4–6 GB(FZP 약 1.2 GB + 결정 JSON 약 58 MB × 61) [추론, J1 런 크기에서]. D: 368.9 GB 여유.

---

## 7. (5) 유효성과 STOP 규칙

### 7.1 런 유효성 = 개정 J1-A (보충 21 §4.1; 세 런 모두 유지 정책 켜짐)

- 항목은 J1 v3c3-s31 재실행 점검(`VALIDITY.md` §2, 27항목 + J1-V + U9-a)과 같습니다: S1(`DECISIONS_FAILED=0` + `DECISIONS_HELD_ON_EXCEPTION=n` 1줄), S2(`ERROR=` 0), S3(발사기 `EXIT … code=0`), S4(`STAGE=SIM_DONE`), S5(실패 계수 0), S6(`*.error.txt`는 유지 T에만, 영수증과 1:1; `*.hold_error.txt` 0), K8(`DECISION_FAILED` 허용 자리만), SIG1(`SIGNAL_MIDBLOCK_COM_SKIPS > 0`), SIG2(`sg_no ≥ 9` 행 0), DEC1(`action_\d{6}.json` 61, OK + HELD = 61, 유지 T 집합 다섯 곳 일치), DEC2(예열 no-control), DEC3–DEC5(유지 T 빼고), PROV1–3, 동결본·환경·런로그(보충 22 §9.2 꼴), 시드, VSL1·VSL2, MTR(K3), K8a, K8b, J1-V(`pairing_check(t_act=900)` ok, 해당 시드 NC3), U9-a(사슬 1–5).
- 기대 출처(지금 고정; 실행 중 값은 그 단계 기록에서 읽음):

| 항목 | 기대 |
|---|---|
| PROV1 head | K9-2-7 40자리. **읽는 법 A(D-K9-26)를 데이터 전에 고정**: `FREEZE_VERIFIED`·plan `freeze.head`·FRZ_K92 `FREEZE.json` `git.head`로 판정. 동결본 런의 `run_provenance.workspace_git_commit`은 늘 빈 값이고(`FREEZE_PUSH_K8b.md` §1-6) 판정에 쓰지 않음(보고만) |
| PROV2 튜닝 | `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866` (plan, provenance `files.tuning`, provenance env `RW_SIGNAL_OBSERVATION_CONFIG_SHA256`, FRZ_K92 파일 해시) |
| PROV3 망 | `3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e` |
| 동결본 | FRZ_K92 `FREEZE.json` sha(§4.2 기록) |
| 환경 | provenance `env.RW_DECISION_ERROR_POLICY` = `hold_previous_on_exception`, `env.RW_DECISION_FAIL_FAST` = `1`, plan `expected_env` 같음 |
| 런로그 | 시작 줄 `DECISION_ERROR_POLICY=hold_previous_on_exception` 1줄, 끝 `DECISIONS_HELD_ON_EXCEPTION=n` 1줄 |
| 시드 | provenance·plan seed = S |

- 유지 결정은 따로 셉니다(보충 21 §4.1 읽는 법, D-K9-22 확인 1): 유지 T는 DEC1·DEC3·DEC4·DEC5·K8a·S6·K8에서 따로 다루고, 유지 장치 자체의 온전함은 H-A로 엄격히 봅니다.
- 유지 감사 H-A1–H-A9(보충 21 §4.2): 유지 T마다. H-A1–H-A8 위반 = 유지 장치 실패 = 런 무효. H-A9(연속 유지의 예외 서명 다름)은 질문 지점.
- 유지 정책 동작(보충 21 P-1–P-12 그대로): 예외 → 유지(무효 아님, 상한 없음, D-K9-14), T = 900 첫 SDMPC 결정 예외 → 엄격 정지(런 무효), 제외 형 여덟·계약 함수 → 엄격 정지(런 무효), 유지 실패 → 런 무효, 시간 초과 유지 없음.
- **T = 150 계수(보충 24 §14.2)**: 세 런 모두 `action_000150.json`의 `head_observation_prior_discarded` = 1.0이 예상입니다. 건강 점검 H15에서 봅니다. 다른 T의 1.0은 판정에 쓰지 않고 T 목록을 보고합니다(유지 뒤 재시작 등). 이 계수는 J1-A 항목이 아닙니다.
- **실패 시드**(보충 21 §4.1 Q-H7, 시드 단위): 그 시드의 V-A 런이 다음 중 하나이면 실패 시드입니다 — 개정 J1-A 항목 하나라도 거짓, H-A1–H-A8 위반, 발사기 `EXIT` code ≠ 0 또는 `EXIT` 줄 없음, `STAGE=SIM_DONE` 없음(StallSec 끝남 포함), 건강 점검 STOP 뒤 사용자가 무효로 정함, 출처(head·튜닝·망·환경·동결본)가 §7.1 표와 다름. [검토 R6] 이 셈은 러너가 VISSIM 단계로 들어간 런(launch 로그 `START <런>` 줄 있음)에만 씁니다.
- [검토 R6] **발사 거부는 실패 시드가 아닙니다**: 러너가 `REFUSED`(앞검사 `NO_SEAT` 등, 런 폴더 없음, `run_sdmpc_n31.ps1:145-148`, `:67-70`) 또는 `NOT_LAUNCHED`(재검사 좌석 거부, 런 폴더 차지·VISSIM 0, `:229-235`)로 끝나면 런이 없는 것이지 무효 런이 아닙니다(보충 21 §4.1 Q-H7은 J1-A 무효 런을 셈). 마무리 판은 `NOT_LAUNCHED`를 실패 시드에 넣었는데, 그러면 좌석 경합 하나가 K8 §6-7 "2시드 이상 → 분석 전체 STOP"을 부를 수 있어 바로잡습니다. 처리: 그 시드는 유효 런이 없으므로 S-VA-8(STOP, 사용자 결정). 재발사·이름은 사용자가 정함(`NOT_LAUNCHED`는 런 폴더를 차지해 같은 이름을 다시 못 씀; 앞검사 `REFUSED`는 폴더가 없음). 자동 재발사 없음.
- [검토 R6] J1-A 항목이나 H-A를 셀 수 없으면(파일 없음·읽기 실패·도구 오류) 그 항목은 INCOMPLETE → STOP·보고입니다. 그 시드를 실패로 셀지는 사용자 결정입니다(INCOMPLETE를 참으로 셈하지 않음).

### 7.2 STOP 규칙 (V-A 단계; 하나라도면 멈추고 정확히 보고, 사용자 결정)

- S-VA-1 실패 시드 2개 이상 → V-A 분석 전체 STOP(K8 §6-7).
- S-VA-2 실패 시드 1개 → 그 시드에 유효 런이 없으므로 세 시드 분석을 하지 않음 → STOP, 사용자 결정(재발사 / 두 시드 분석 등). 재발사는 사용자 결정 뒤에만(같은 이름·다른 이름 모두).
- S-VA-3 건강 점검 H1–H16·T1·T2 하나라도 거짓 → STOP, 곧바로 알림.
- S-VA-4 감시·유효성 단계에서 성능 숫자(Ω·TTT·①–④·지연·목적값·녹색)를 내거나 열면 → 그 단계 중지·보고(보충 21 S-6 꼴). 성능 숫자는 §8의 분석 도구 고정 뒤 분석 단계에서 처음 엽니다.
- S-VA-5 FRZ_K92·FRZ_K8b·다른 `frozen/*`·J1 런 폴더·NC3·R-obs3 폴더에 쓰기·옮기기·지우기(런이 FRZ_K92 `__tangentcache__`·`__pycache__`에 쓰는 캐시는 J1과 같은 정상 동작으로 보고만, `J1_LAUNCH.md` §7) → 중지·보고.
- S-VA-6 질문 지점(STOP 아님): 유지 발생(첫 유지 즉시 알림), H-A9, 발사 직후 VISSIM 5개 이상, `GIVE_UP`, [검토 R7] 좌석 기다림 24 h 넘음(§6.2).
- [검토 R6] S-VA-7 WD가 끝내지 못하는 멈춤(§6.3: 4,800 s 무진행·`EXIT` 없음·cmd PID 살아 있음), 또는 러너가 `EXIT` 줄 없이 죽음 → STOP·곧바로 알림. 아무것도 끄지 않음. 그 런은 실패 시드 후보(§7.1)이고 끝낼지·무효인지는 사용자 결정.
- [검토 R6] S-VA-8 발사 거부(`ReturnValue` ≠ 0, launch·wmi 로그 `REFUSED`, `NOT_LAUNCHED.txt`) → 그 시드 발사 없이 STOP·보고. 실패 시드에 세지 않음(§7.1). 재발사·새 이름은 사용자 결정 뒤에만.

- [검토 R6] **사건별 처리 표** (위 규칙을 한곳에 모음; 새 규칙 아님. "실패 시드"는 §7.1 정의)

| 사건 | 런 | 처리 |
|---|---|---|
| T ≥ 1,050 결정 예외 → 유지 성공(`DECISION_HELD_ON_EXCEPTION`) | 계속 | 질문 지점(S-VA-6, 첫 유지 즉시 알림). 무효 아님(D-K9-14). H-A1–H-A9로 감사, `DECISION_FAILED`는 보충 21 §4.1 K8 허용 자리에만 |
| T = 900 결정 예외, 제외 형 여덟·계약 함수 예외, 예열(T ≤ 750) 결정 예외 | 엄격 정지(러너가 끝냄) | 런 무효 → 실패 시드. 건강 점검 시점이면 S-VA-3도 |
| 유지 실패(`ERROR=DECISION_HOLD_FAILED`) | 러너가 끝냄 | 런 무효 → 실패 시드 |
| 유지는 됐는데 H-A1–H-A8 위반 | 끝까지 돎 | 런 무효 → 실패 시드(런 뒤 감사) |
| 시뮬레이션 무진행 → WD `StallSec` 2,400 | WD가 끝냄 | `STAGE=SIM_DONE` 없음 → 실패 시드 |
| WD도 끝내지 못함 / 러너가 `EXIT` 없이 죽음 | 멈춤 또는 없음 | S-VA-7(STOP·알림, 끄지 않음) |
| 좌석 없음(발사 전 셈) | 아직 없음 | 기다림(9분 이하 간격), 24 h 넘으면 질문 지점, 끄지 않음 |
| 러너 `REFUSED` / `NOT_LAUNCHED` | VISSIM 0 | S-VA-8(STOP), 실패 시드 아님 |
| 발사 직후 PC 전체 VISSIM ≥ 5 | 계속 | 질문 지점, 아무것도 끄지 않음(내 런 포함) |
| 건강 점검 H1–H16·T1·T2 거짓 | 계속(사용자 결정 전까지) | S-VA-3 STOP·알림 |
| J1-A·H-A 셈 불가 | 끝남 | INCOMPLETE → STOP(§7.1) |
| 실패 시드 1개 / 2개 이상 | — | S-VA-2 / S-VA-1 |
| C: 또는 D: < 8 GB | — | S-A34-9 멈춤(감시기는 D: < 30 GB면 발사를 기다림) |

---

## 8. (6) 분석 방법 (데이터 전 고정, J1 꼴)

### 8.0 순서와 고정

1. 유효성(§7.1) → 보고 머리(보충 21 §5 1–10, 시드마다; 10번 오프라인 관문 줄 = §5 결과와 E_K92 처리(§5.2, D-K9-71; 선언 목록 기준 결과와 A ∪ E_K92 기준 결과 둘 다)) → 분석.
   - [검토 R10] 보고 머리 6번의 H-R1은 보충 22 재실행 전용이라 "해당 없음"으로 적습니다. 8번은 보충 22 §11 고정 문구를 바이트 그대로 두고 바로 아래에 이 한 줄을 더합니다(고정 문구 끝의 "K9-2에서 고친다"가 이 V-A에는 해당하지 않으므로): `[K9-2 V-A] 묶음 1(W·H-b)은 유령 movement 수정을 담지 않는다(보충 24 §2.4, D-K9-19). 위 줄의 "K9-2에서 고친다"는 이 V-A 런에서 아직 이루어지지 않았다.`
2. 분석 도구와 조작 정의 문서 `VA/analysis/ANALYSIS_METHOD_VA.md`(이 절을 코드로 옮긴 정의만; 이 절과 다르면 이 절이 이김)는 **첫 V-A 발사 전에** sha256을 `VA/analysis/va_analysis_pins.sha256`과 LOG에 고정합니다. 도구는 J1·NC3 자료(이미 공개된 숫자)로만 자기 시험합니다: J1 − NC3 표(`J1_REPORT.md` §3.1–§3.2, §5, §7, §8.1)를 0.1 반올림 안에서 다시 내야 합니다. 고정 뒤 도구를 고치면, 결과를 보기 전이라도 새 고정·공개가 필요하고, V-A 출력을 읽은 뒤이면 S-K12 꼴 STOP입니다.
3. 독립 검증 도구 `VA/analysis/verify/v_*.py`(분석 도구·stage1을 import하지 않음)는 분석 출력을 읽기 전에 sha를 고정합니다. 다르면 STOP.
- 도구 이름(고정): `VA/analysis/tools/va_provenance.py`(입력 해시만), `va_scan.py`(stage1 스캔), `va_metrics.py`(네 지표·Ω 밖·통계·표시 규칙), `va_followup.py`(링크 174 사슬·입력 1083·SC109 동측 링크), `va_fzp_local.py`(SC1001 EB 국소·U9-a `DESSPEED`·링크 대수), `va_control.py`(결정·벽시계·유지·직전 계획 유지·SC109 p3·하한·미터·VSL), `va_tables.py`, `va_report_build.py`. J1 도구(`SP/j1/analysis/tools/an_*.py`, 앞 16자: scan `cb43153c2e78403e`, metrics `9186f7bc8e3e44e4`, fzp_local `c81295f8bd267746`, control `b5828f67a9bca30c`, followup `6d5b2e74c3eab95e`, extra `bb11cc7a3c3bbfb0`, tables `0188ce675790b5a0`)를 바탕으로 런 경로·이름만 바꾸고 새 항목을 더합니다.
- 고정 도구 함수: stage1 네 파일(sha §0), `find_rule_policy` = None(봉인 시드 폴더 glob 막음), J1 FZP 0.10 s 행은 읽기 심으로 건너뜀, 적분 5.1–8,995.1 s 사다리꼴, 150 s 칸, Ω 지킴 1,236/635.
- 출력: `VA/analysis/out/`, 사본 `REPVA/analysis/`(`SHA256SUMS_ANALYSIS.txt`). BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, 한 번에 하나.

### 8.1 비교 대상

| 시드 | V-A 런 (RVA) | NC3 | J1 런 (RR) | J1 코드 출처 |
|---|---|---|---|---|
| v3c3-s31 | `sdmpc31_v3c3_k92va_s31` | `s31_v3c3nc/run` | `sdmpc31_v3c3_k8j1r_s31` (재실행) | FRZ_K8b `b9734abe`, 튜닝 `d0f9ef39…`, 유지 켜짐 → V-A와의 코드 차이 = B1 두 키뿐(K9-2 런타임은 키 끔이면 `b9734abe`와 같음, G-K0) |
| v3c3-s41 | `sdmpc31_v3c3_k92va_s41` | `s41_v3c3nc/run` | `sdmpc31_v3c3_k8j1_s41` | FRZ_K8 `74cd495f`, 튜닝 `5f0d0e40…`, 유지 장치 없음 → 코드 차이 = K8-8·9·10(오류 없는 결정에서 비트 같음, G-H2·G-H3) + B1 두 키 |
| v3c3-s43 | `sdmpc31_v3c3_k92va_s43` | `s43_v3c3nc/run` | `sdmpc31_v3c3_k8j1_s43` | 같음(s41과 같은 출처) |

- 원래 v3c3-s31 J1 런(`sdmpc31_v3c3_k8j1_s31`, 무효)은 쓰지 않습니다.
- [검토 R13] 위 표 "코드 차이" 칸을 정확히 풀어 씁니다(표 글이 이것과 다르면 이 줄이 이김): v3c3-s31에서 V-A와 J1의 차이 = 튜닝 두 키(B1: `urban.sc109w_through_saturation`, `urban.capacity.head_floor_seed`) + 그 키를 읽는 K9-2 런타임 코드(`evaluation/controllers/runtime_setup.py`, `signal_head_observation.py`; K9-2-1·K9-2-2, 키가 없으면 `b9734abe`와 같은 동작임을 G-K0가 보임) [실행 `git diff --name-status b9734abe e27ceac8 -- evaluation vendor plant scripts` = 그 두 파일]. v3c3-s41·s43은 여기에 K8-8(러너 유지)·K8-9(별칭) 코드와 K8-10 튜닝 키 `runtime.decision_error_policy`(보충 21 §7.1-5)가 더해집니다.
- J1·NC3 스캔은 J1 분석 산출(`SP/j1/analysis/scans/<tag>/scan.json`·`uninserted.json`)을 sha 확인 뒤 다시 씁니다(앞 16자: j1_s31 `4eb525ddbc8f3ff1`/`34fb9bc6885364e5`, j1_s41 `645f1861d1f3a47c`/`ac94e55d91a97238`, j1_s43 `35a3b79504740837`/`9813298b609dc7bd`, nc3_s31 `9419b0bc31e2ab18`/`3490c88ccd16175a`, nc3_s41 `fd103d4362a809ba`/`94f93c9193aa7014`, nc3_s43 `3d946a0fa489a46a`/`f2baaeddae324156`). sha가 다르면 같은 도구로 다시 스캔하고 공개합니다. V-A 세 런만 새로 스캔합니다.

### 8.2 두 짝 차와 미삽입 합집합

- **(A) V-A − NC3** (J1 꼴 그대로): d_s = V-A_s − NC3_s. 미삽입 합집합 U6 = V-A 3 + NC3 3 런에서 `queued` 참 또는 `remain_err > 0`인 입력, 시드별 NC3 앵커.
- **(B) V-A − J1** (같은 시드): d_s = V-A_s − J1_s. 미삽입은 V-A·J1 두 쪽에 같은 합집합 U9 = V-A 3 + J1 3 + NC3 3, 시드별 NC3 앵커로 다시 냅니다(같은 합집합이라 d가 정의상 맞음). 같은 표에 (B′) J1 − NC3을 U9로 다시 낸 값과, `J1_REPORT.md`의 원래 값(U6 of J1, 12입력)을 "J1 보고 값"으로 나란히 둡니다(합집합이 달라 ④·④b가 다를 수 있음을 표 위에 적음).
- 표는 시드마다 나란히: NC3 / J1 / V-A 수준값, d(J1 − NC3), d(V-A − NC3), d(V-A − J1).
- [검토 R8] 합집합에 기대는 칸(④, ④b, ④b 입력별, Ω 밖 (a)·(c))은 합집합마다 따로 냅니다: (A) d(V-A − NC3)와 그 수준값 = U6(V-A) 열, (B) d(V-A − J1)·(B′) d(J1 − NC3)와 그 수준값 = U9 열, "J1 보고 값" = U6(J1) 열(J1_REPORT 그대로). 열 머리에 합집합 이름을 적습니다. 그래서 한 표 안에서 d(V-A − J1) = d(V-A − NC3) − d(J1 − NC3)는 같은 합집합(U9) 열끼리만 성립하고, 다른 합집합 열끼리 빼지 않습니다. 합집합과 무관한 칸(①, ②, ③, ③u, Ω 분해, ④a, Ω 밖 (b)·(d)·(e)·(f))은 한 번만 냅니다. §8.4 표시 규칙은 (A)는 U6(V-A) 값으로, (B)는 U9 값으로 셉니다.
- 통계(두 짝 차 모두, J1이 한 꼴 그대로): 시드별 d, 평균, sd(n − 1), 90 % CI = 평균 ± 2.920 × sd / √3, 음/양 수(엄격 부등호), 평균/NC %(= 100 × 평균 d / 세 NC3 평균; (B)도 분모는 NC3 평균) 와 시드별 d/NC %. CI가 0을 포함하지 않으면 "관측된 차이"로만 적고 동시 비교 행 수와 "보정 없음"을 함께 적습니다. 잡음 참고 반폭(N1F sd × 1.686: ① 175, ② 194, ③ 172, ③u 13, ④ 106)은 옆 칸 참고로만. J1이 한 것보다 더 모으지 않습니다(시드를 더한 수준값·풀링 회귀 없음).

### 8.3 지표 (같은 표; 판정 아님)

1. K8 §5.5 네 지표: ① fw_e_main 7링크, ② 동측 국소 19링크, ③ Ω 635링크, ③u urban_omega, ④ = ④a 전체 1,236링크 TTT + ④b 미삽입. Ω 분해(fw_e_main, fw_w_main, onramp, offramp, urban_omega).
2. **Ω 밖**(Ω와 늘 같은 표): (a) ④ − ③, (b) ④a − ③, (c) ④b, ④b 입력별(1098, 1099, 그 밖), (d) 차로변경 제거 대수 — 읽는 법 A(런 끝 `.err` 전체)와 읽는 법 B(소속 파일 기준 Ω 밖 링크만; J1에서는 사후였고 이번에는 데이터 전에 둘 다 고정), (e) S7 늦은 보고(V-A·J1만), (f) 런 끝 입력별 remain. Ω는 ④와 Ω 밖 없이 따로 인용하지 않습니다.
3. **링크 174 사슬과 입력 1083** (`J1_REPORT.md` §5 꼴): 링크 21·10112·174·10280·10281·173의 stage1 `link_vh`(전체, 4,350 s 뒤 = 칸 29–59); 링크 174 프레임 대수의 평균·최대·최대 시각(FZP); 입력 1083 런 끝 remain, 삽입 수, 재구성 지체(NC3 앵커), 최대 큐(프레임 시각 값)와 시각, (V-A − NC3)과 (V-A − J1)의 0 아래 자른 큐 차가 처음 10대를 넘는 150 s 표본 시각, 4,200 s부터 150 s 칸별 진입 수 차, ④b의 입력 1083 몫 d.
4. **SC109 p3 발병** (V-B §6-1, J1 정의 24.5 s): SDMPC 결정 55개의 지령 `green_times.SC109_p3`(action JSON)에서 p3 ≤ 24.5 s인 결정 수, 첫 T, 최장 연속 길이; p2·p3·p4 평균·최대(4,350 s 뒤 따로). V-A와 같은 시드 J1을 나란히. 실현 녹색(signal readback)은 계산하지 않습니다(공개 §9-12).
5. **(173, p4) 하한·씨앗** (V-B §6-2): 하한 키 이름(런마다 하나인지), 값의 첫 값·최댓값·줄어든 T 목록(유지 뒤 재시작 제외), `k92_hb_seed_binding` = 1.0 결정 수, `head_observation_groups_carried`·`_updated` 합, `head_observation_prior_discarded` = 1.0인 T 목록(T = 150 기대). `k92_w`·`k92_hb` 있는 결정 수(61 기대).
6. **SC109 동측과 E_out** (V-B §6-3·공개 §9-4): VISSIM 링크 1220000704(동측 접근, SG6, Ω 밖)와 1220000803(서측 직진 출구, Ω 밖) [읽음 `lens_link174.md:32-34`]의 stage1 `link_vh`(전체, 1,800–7,200 s)와 FZP 프레임 대수 평균·최대; d(V-A − NC3), d(V-A − J1). 모형 쪽 `SC109_E_out`(지평 최대/220)은 폐루프 런에 기록기가 없어 "없음"으로 적습니다(추정하지 않음).
7. **미터·VSL** (`J1_REPORT.md` §8 꼴): 미터 8개의 러너 행동 로그 `rate_vph`·`green_sec` 분포, action JSON `ramp_metering` 값 분포, 미터 명령이 바뀐 결정 수; VSL 구역 머리 FW_E·FW_W 명령 분포, 110 미만 결정 비율·첫 T·최장 연속·전이 행렬, 미래 블록 1·2 계획 VSL, 110 미만 구역 노출(veh·km). 목적값은 "plant 모형 값"으로만 표시.
8. **유지와 직전 계획 유지** (D-K9-69): (i) 유지(예외) 횟수·T·형(보충 21 §5 표). (ii) **직전 계획 유지로 보이는 결정** = SDMPC 결정 T ≥ 1,050, 유지 결정이 아님, 그리고 세 조건이 모두 참: (가) `green_times`와 `offsets` 전체가 직전 결정(T − 150)의 action JSON 값과 같음(JSON 값 그대로 비교), (나) `diagnostics.sdmpc_prediction_sequence`가 없음, (다) `metadata.joint_leader_selection.selected_objective`와 `held_objective`가 repr로 같음. 세 조건 각각의 결정 수와 셋 모두 참인 결정 수·T 목록, `selection_status` 분포. V-A와 같은 시드 J1을 나란히(V-B no_match 두 결정의 서술 꼴 [읽음 V-B 보고 §0-5]).
9. **결정 벽시계** (V-B §6-5): runlog `CONTROLLER_DECISION … wall_sec`로 예열·SDMPC 각각 최소·중앙·평균·최대·합, 900 s 넘는 결정 수, 런 벽시계(`WATCHDOG_EXIT wall_sec`). 비 = V-A SDMPC 중앙 / 같은 시드 J1 SDMPC 중앙을 G-K5 예산 1.0158과 나란히 적음 — **보고만**(폐루프 상태가 달라 G-K5와 같은 양이 아님).
10. **SC1001 EB 국소** (`J1_REPORT.md` §7 꼴): 10491 커넥터 대수 평균·최대, 127 차로 1–2 대수, FW_W·FW_E 역류 창 비율(F1 §6 정의), 시간 범위 (P) 1,800–7,200 s와 (F) 전체 둘 다.
11. **150 s 칸별 d 시계열**: ①·③·④·Ω 밖 (a)를 시드별·평균으로 (A)·(B) 각각 CSV와 그림(VSL 110 미만 적용 T 세로선).
12. **U9-a `DESSPEED`** (FW_E, V-A만): J1 방법 §2.7 정의, 띠의 m은 두 읽는 법 C(m = 지령 c)와 M(m = 써진 분포 M(c))를 둘 다 적고 고르지 않음(J1에서는 M이 사후였음).
13. 점검: 900 s 전 칸(0–5)의 d(V-A − NC3) = 0, `pairing_check`; d(V-A − J1)의 900 s 전 칸도 보고(예열 결정 출력은 키 때문에 메타가 다르나 VISSIM 명령은 무제어로 같다는 기대 [추론]; 다르면 그 사실을 적음).
14. [검토 R9] **J1-R 재현 표본**(K8 §5.5 끝, K7 §3.8; "보고, 구속 아님"): J1처럼 이 단계에서는 하지 않습니다(결정 재생이 V-A 분석 단계 규칙에 없음; J1 `ANALYSIS_METHOD.md:170`, `J1_REPORT.md:504`). 보고서 "하지 않은 것"에 적고 열린 항목으로 둡니다. 런 유효성은 바뀌지 않습니다.

### 8.4 숫자를 읽을 때 쓰는 말 (고정)

- 표시 규칙(K8 §5.5, J1 방법 §2.5·Q1 그대로): d(③) < 0인 칸(시드별·3시드 평균)에만. 읽는 법 N: d(④) ≤ 0 **그리고** d(④ − ③) ≤ 0이면 "같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)", 하나라도 > 0이면 "대기 이전(Ω 밖으로)". 읽는 법 W: 더해 d(④b) ≤ 0, d(제거) ≤ 0(제거는 읽는 법 A·B 각각). 둘 중 하나를 고르지 않습니다. d(③) ≥ 0이면 "해당 없음(Ω 감소 아님)".
- **(B) V-A − J1에도 같은 규칙을 같은 글로 씁니다**(이 보충이 데이터 전에 정하는 새 적용). 
- "개선"은 표시 칸 밖에서 쓰지 않습니다. 이기다/지다/낫다/좋아졌다 같은 판정 문장 0. CI가 0을 벗어난 칸은 "관측된 차이"뿐.
- [검토 R12] 더 좁힘: 표시 칸의 글은 정확히 세 문구 `같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)`, `대기 이전(Ω 밖으로)`, `해당 없음(Ω 감소 아님)`뿐이고, "개선"이라는 낱말은 V-A 보고 어디에도(표시 칸 안 포함) 쓰지 않습니다. Ω(③) 값이나 d(③)를 적는 모든 표·문장에는 같은 자리에 ④(④a·④b)와 Ω 밖 (a)를 함께 적습니다(K8 §5.5 "항상 같은 표에").
- 보고서 머리: J1 단서 머리 두 파일(트리 안 `k9/J1_CAVEAT.md`, 트리 밖 `J1_CAVEAT_ADDENDUM.md`) 참조, 보충 24 §7-6 값 선택 표시(W = 5,209.8은 몫 가르기 뒤 선택, F-3 비블라인드), 보충 21 §5 보고 머리 10항목(시드마다), 이 보충 §9 공개 요약.
- [검토 R11] **J1 단서 덧붙임 2 (보충 24 §14.3 "공개: … J1 단서 덧붙임에 적습니다")**: 고정된 `SP/j1/J1_CAVEAT_ADDENDUM.md`(`b3484937…`, 고정 목록 줄)는 바꾸지 않습니다. 대신 V-A 보고 단계에서 새 파일 `VA/J1_CAVEAT_ADDENDUM_K92VA.md`를 아래 세 줄 글자 그대로(머리 줄 `# J1 단서 덧붙임 2 (K9-2 V-A, 트리 밖)` + 빈 줄 + 세 줄, UTF-8, LF) 만들고, V-A 보고서 머리에 앞의 두 단서 파일과 함께 붙입니다. 글은 지금 이 보충이 고정합니다(데이터 전).
  - `- [더함, D-K9-38 ④] GB-7′ 허용 목록에 R2-12(/diagnostics/leg_ramp_split_(?:len_[^/\[]*|length_fallback))를 더했다. 이것은 재생 출력을 본 뒤의 목록 보충이다(보충 24 §14.3, 목록 sha a8148f38…7af1). D-K9-12 예외는 K9-2 동결본에 다시 쓰지 않았다.`
  - `- [더함, D-K9-71] 묶음 1을 배포한 동결본의 GB-7′·해시 A/B 조건 7은 선언 목록 A에 더해 K9-2 선언 차이 E_K92(재생 쪽에만 있는 /metadata/k92_w·k92_hb·k92_hb_seed_binding과 (173, p4) 하한 키 하나, 고정 sha·값 조건)로 판정했다. 이 정의는 관문 데이터 전에 보충 34 §5.2로 고정했고, 보고에는 선언 목록 A만의 결과도 함께 적는다.`
  - `- [더함, D-K9-67] V-A 런은 묶음 1(W = SC109 서측 직진 용량 5,209.8, H-b = (173, p4) 좌회전 하한 씨앗 1045.1612903225805, 학습 유지)을 배포한 폐루프다. W 값은 몫 가르기 뒤 선택이고 씨앗은 F-3 비블라인드이며, 세 시드는 모두 원인 분석·몫 가르기·V-B에 쓴 fit 시드다.`

---

## 9. (7) 공개, 새 STOP 규칙, 고정 목록

### 9.1 공개 (보고서 머리에 옮김)

1. **D-K9-62·66**: V-B 사슬 이어받는 OFF 10결정은 판정이 아니라 보고였고, 닫힌 목록 밖 `action_token` 11경로(결정 5개, 잎 147)는 보고만 했습니다. V-A 비교는 G-K0 꼴이 아니라 이 보충 §8이 정합니다.
2. **D-K9-69**: V-B B1 사슬의 `no_match` 두 결정(VB-41 B1 T = 3,300·4,500; 녹색·오프셋이 앞 결정과 같고 예측 시퀀스 없음, selected = held)은 기록만 했습니다. V-A는 §8.3-8로 같은 꼴 결정을 셉니다.
3. **D-K9-70**: V-B·검증 공개(고정 전 요약 수치 노출, 데이터 뒤 보고용 도구 셋, E1 자기 시험 재실행 대신 고정 출력 확인, E3 효과 없는 잘못 섞인 명령, P14 `run_bn.py` 우선순위 설정 실패)는 수용됐습니다.
4. **동측 용량 미처리(V-B)**: V-B 같은 8상태에서 `SC109_E_out` 지평 최대/220은 B1 0.120–0.324, OFF 0.016–0.126이었고, VB-31 B1 T = 4,500에서 0.815였습니다(모형 값). 동측 `SC109_E_*`(`boundary_in` 206.53 × 4 = 826.1, 링크 1220000704)는 묶음 1 범위 밖입니다(보충 24 §2.4). V-A는 VISSIM 동측 두 링크를 §8.3-6으로 보고합니다.
5. **GB-7′ R2-12는 결과를 본 뒤의 목록 보충**입니다(D-K9-38 ④, 보충 24 §14.3). D-K9-12 예외는 FRZ_K92에 다시 쓰지 않습니다.
6. **GB-7′과 K9-2 메타 키(§2.1)**: 선언 A로는 B1 동결본의 GB-7′이 구조적으로 떨어진다는 것을 첫 Declare에서 데이터 전에 찾았습니다. 사용자 결정 D-K9-71로 판정에 선언 차이 E_K92(§5.2)를 더했고, 이 결정·정의·판정 함수 sha는 **관문 데이터 0개일 때** 정했습니다. GB-7′ 판정의 뜻이 바뀐 것이므로, 보고에는 선언 목록 A만의 결과(FAIL 예상)와 A ∪ E_K92 결과를 함께 적습니다.
7. **make_config 점검(§2.2)**: K9-2-6 뒤 head에서 `make_config_n31.py --k92b1 --check`는 설계상 `ValueError`입니다(생성기가 CFG를 바탕으로 읽음). 사용자 결정 D-K9-72로 이 점검은 바이트 복사 **전** 깨끗한 K9-2-5 트리에서만 돌립니다(§3.1-1). K8-7 선례와 점검 시점이 다릅니다. make_config·CFG 정합 수정은 묶음 2 목록(D-K9-59)에 더합니다.
8. ConfigFlagTests 2건(기존 실패, D-K9-59)은 승격 점검에 넣지 않았습니다(K8-7 선례 점검이 아님).
9. W 값 5,209.8은 몫 가르기 뒤 선택(D-K9-34), 씨앗 1045.1612903225805는 F-3 비블라인드(보충 24 §2.6-6), 학습 유지로 시드 의존이 남음(D-K9-36).
10. 세 시드는 모두 원인 분석·몫 가르기·V-B에 쓴 fit 시드입니다. V-A는 독립 근거가 아닙니다. J1 d(③) 시드 간 sd 366.8은 개방 루프 잡음 102보다 큽니다.
11. 시드별 J1 코드 출처가 다릅니다(§8.1). V-A − J1의 코드 차이는 v3c3-s31에서 B1 두 키, v3c3-s41·s43에서 K8-8·9·10 + B1 두 키입니다.
12. 실현 녹색(signal readback)은 이번 분석에서 계산하지 않습니다(지령만). 모형 쪽 `SC109_E_out`은 폐루프 런에 없습니다.
13. D-K9-44: 어댑터는 결정마다 봉인 시드·v3c3-s47 이름 파일의 sha를 셉니다(값 출력 없음, 코드 그대로). V-A 런도 같습니다. 고침은 묶음 2.
14. 이 Declare 단계(첫 Declare와 마무리)에서 읽은 것(V-A 데이터 아님): V-B 출력 VB-41w B1·OFF 무제어 6결정의 차이 경로(값 출력 0), 같은 6결정 B1의 `k92_w`·`k92_hb` 키 이름·sha 잎·`after`·`seed`의 형과 repr(고정 값과 같은지), 하한 키 이름; R-obs3 v3c3-s31 61결정 JSON의 메타 키 이름(값 출력 0); CFG·CFG-B1 JSON 값 차이; `make_config_n31.py --k92b1 --check`와 `build_obs150_detectors.py --tuning CFG-B1 --check` 실행(쓰기 0); 증거 파일 두 개의 바이트 sha; J1 보고서·분석 산출(이미 공개된 숫자). E_K92 마른 점검이 V-B 출력에서 E1–E4 조건의 참거짓을 셌습니다(§5.2-6).
15. **E4는 "재생 쪽에만"뿐입니다**: 초안 Q-A34-1 (가)의 E4 (ㄴ)(양쪽에 있고 원본 < s·재생 = s; 보충 24 H5 (나) 꼴)은 D-K9-71 글("재생 쪽에만 있을 때만")에 따라 뺐습니다. R-obs3 v3c3-s31에서 씨앗이 묶이는 결정은 T ≤ 750뿐이고 그때 원본에는 하한 키가 없으므로(보충 24 §5.2 :330, §2.1 표 [실행]), (ㄴ)이 필요한 결정은 없을 것으로 봅니다 [추론]. 그래도 그런 차이가 나오면 FAIL → STOP입니다.
16. **V-B 마른 점검의 E4 묶임 거짓(T = 300 … 750)**: V-B 사슬에서는 앞 B1 결정이 하한 키 = s를 날라 `k92_hb_seed_binding` = 0.0이 되어 E4 조건이 거짓이었습니다(§5.2-6). GB-7′ 한 결정 재생에서는 앞 행동이 R-obs3 기록(T ≤ 750 하한 키 없음)이라 묶임 1.0이 예상입니다 [추론]. 예상과 달라 묶임 0.0이 나오면 E4 거짓 → FAIL → STOP입니다(조건을 데이터 뒤에 바꾸지 않음).
17. **K8b 판정기의 D-K9-12 분기는 쓰지 않습니다**: K8b `gjudge.py:172-201`의 `PROGRESS_DK912`("FAIL(선언 목록 기준) + D-K9-12 예외 적용")는 V-A 판정기 사본에 넣지 않습니다(보충 24 §14.3). T = 1 길이 키는 이제 목록의 R2-12로만 다룹니다.
18. [검토 R14] **V-B 측정 훅은 V-A에서 쓰지 않습니다**(V-B §6-6): V-A 런은 FRZ_K92에서 러너로만 돌고 V-B 훅(`KB/a33decl/vbhook/sitecustomize.py`)을 `PYTHONPATH`에 두지 않습니다. 그래서 V-B 훅 이름 겹침 위험은 V-A에 없습니다 [추론: 러너는 자기 환경을 새로 세움, `run_sdmpc_n31.ps1:21` "clean env"; 시험하지 않음].
19. [검토 R6] **발사 거부는 실패 시드에 세지 않습니다**(§7.1): 마무리 판은 `NOT_LAUNCHED`를 실패 시드에 넣었습니다. 검토가 보충 21 Q-H7(무효 런을 셈)에 맞춰 뺐고, 대신 S-VA-8(STOP·사용자 결정)로 둡니다. STOP을 줄인 것이 아닙니다(두 경우 모두 STOP).
20. [검토 R18] **분석 도구 고정이 J1보다 이릅니다**: J1은 런이 끝난 뒤·성능 숫자를 열기 전에 방법 문서를 고정했고, V-A는 첫 발사 전에 분석 도구·방법 문서·검증 도구를 고정합니다(§8.0-2, §6.1 발사 전제 (4)).
21. [검토 R9] J1-R 재현 표본은 하지 않습니다(§8.3-14, J1과 같음).
22. [검토 R10·R11] 보고 머리 8번 고정 문구 아래 한 줄(§8.0-1)과 J1 단서 덧붙임 2(§8.4)를 이 보충이 글자로 고정했습니다.

### 9.2 새 STOP 규칙 (S-A34; 보충 24 §8·보충 21 §9·보충 22 §12와 함께)

- S-A34-1 이 보충의 고정 sha(`SP/K8_PREDECLARATION_AMENDMENT_34.md.sha256`와 `VA/LOG.md`의 고정 줄)와 고정 목록 `VA/a34_pins.sha256`이 생기기 전에, 또는 그 sha와 다른 보충 34로 K9-2-6·K9-2-7 커밋, 푸시, 동결, 관문, 발사를 하면 → 결과 무효, STOP. 각 단계는 시작 때 `VA/a34_pins.sha256`을 다시 대조합니다(`sha256sum -c` 꼴, 모두 OK). [검토 R15] 고정 sha는 고정점 `VA/AMENDMENT34_FIXED.md`의 64자 값입니다. 이 파일 sha가 그 값과 다르면(검토 전 판 `_r1` `37180bed…` 포함) 어떤 단계도 하지 않습니다. 고정 목록 1행도 그 값이어야 합니다.
- S-A34-2 §3의 커밋 점검(기대 sha·blob·차이 경로·목록 sha·판정 표) 하나라도 거짓 → STOP(커밋·푸시 없음).
- S-A34-3 §4.1 푸시 조건, §4.2 동결 PASS 12항 하나라도 거짓 → STOP.
- S-A34-4 §5 관문 하나라도 FAIL·보류·INCOMPLETE, 판정기 고정 뒤 수정 → STOP.
- S-A34-5 §6 발사 조건(이름·좌석·ReturnValue·REFUSED) 위반 → STOP. 좌석 없음은 기다림. 무엇도 이름으로 끄지 않고, 내가 띄우지 않은 VISSIM·cscript·python을 끄지 않음.
- S-A34-6 §7.2 S-VA-1–5, [검토] S-VA-7·S-VA-8(S-VA-6은 질문 지점).
- S-A34-7 분석 도구·방법 문서를 고정 전에 V-A 성능 출력을 읽음, 또는 고정 뒤 바꿈 → STOP.
- S-A34-8 봉인 시드 37·59·61·67 자료 열기, codex 64cf 숫자 사용, v3c3-s47을 V-A에 씀 → 중지·보고.
- S-A34-9 C:·D: 8 GB 밑 → 멈춤.
- S-A34-10 K8 브랜치(`claude/k8-sc1001eb-defects-20261004`)가 `b9734abe`에서 움직임 → STOP.
- S-A34-11 E_K92 판정 함수 `VA/gates/gb7_k92decl.py`의 바이트 sha256이 `d15e9cc08a600a60edb29b945bdab407e4e4631f5b0e44bc2d7ac080dc11fb11`와 다름, 관문 판정기가 다른 E_K92 구현을 씀, 또는 §5.0 자기 시험 (iii)의 출력이 고정 출력 `666cbac3…1110`과 바이트 다름 → 그 관문 STOP(결과를 보기 전이라도).
- S-A34-12 §3.1-1의 편집 전 make_config 점검이 참이 아님(출력 줄·exit·쓰기 0 중 하나라도 다름) → CFG를 바꾸지 않고 STOP. 바이트 복사 뒤에 `make_config_n31.py --k92b1 --check`를 돌려 그 오류를 실패로 셈하지 않습니다(설계상 오류, §2.2).
- [검토 R3] S-A34-13 §3.3 VerifyPromote가 pass = true가 아니거나, 검증 도구를 첫 실행 전에 고정하지 않았거나, 검증 head ≠ 푸시할 head → 푸시·동결 없음, STOP.

### 9.3 고정 목록 (고정 때 `SP/k92/va/a34_pins.sha256`에 적음)

- 이 보충 고정판, 결정 기록(고정 때 sha `6b76cc09…af88`), 첫 Declare 초안(`9ac1828e…ab2a`), 보충 21·22·23·24·33과 고정점, OG_METHOD, J1 `ANALYSIS_METHOD.md`·`J1_REPORT.md`·`VALIDITY.md`, `J1_CAVEAT_ADDENDUM.md`, V-B 보고 r3·`VERIFY_VB.md`, §0 표의 도구(러너·동결·망·재생·stage1·K8b 관문 도구·J1 건강 점검), J1 분석 도구 7개·J1/NC3 스캔 12파일, 이 단계 사전 점검 도구·출력 4개, [마무리] 사실 확인 도구·출력 2개, **E_K92 판정 함수 `VA/gates/gb7_k92decl.py`**, 자기 시험 `gb7_k92decl_selftest.py`(v2)와 출력 4개(v1·v2 각 표준 출력·JSON), `K92_VALUES.json`(a25decl).
- [검토 R15] 검토판 고정 목록: 마무리 판 목록(78줄, `VA/a34_pins_r1.sha256`로 보관)에서 1행을 이 검토판 sha로 바꾸고, 검토 산출 다섯 줄(`SP/K8_PREDECLARATION_AMENDMENT_34_r1.md`, `VA/a34_pins_r1.sha256`, `VA/a34review/rev_a34.py`, `VA/a34review/out/rev_a34.json`, `VA/a34review/out/rev_a34.out.txt`)을 끝에 더한 83줄입니다. 그 sha256은 고정점 `VA/AMENDMENT34_FIXED.md`에 적습니다.
- 단계별로 나중에 더하는 고정(그 단계 첫 계산 전): [검토 R3] `VA/vpromote/v_promote.py`, `VA/freeze/check_freeze_k92.py`, `VA/gates/va_gates_pins.sha256`, `VA/vgates/v_*.py`, `VA/launch/{va_monitor.py, va_health.py}`, `RVA/k92va_s43_watcher.ps1`, `VA/validity/va_j1a.py`, `VA/analysis/va_analysis_pins.sha256`(분석 도구 8개 + `ANALYSIS_METHOD_VA.md`), `VA/analysis/verify/v_*.py`.

---

## 10. 첫 Declare의 질문과 사용자 결정 (기록)

- **Q-A34-1 → D-K9-71 = (가) 판정에 선언 차이 E_K92 추가.** 반영: §5.0(판정기 목록·자기 시험·독립 검증), §5.1 1·2행(조건 7 정의, 보고 둘), **§5.2(정의·함수·자기 시험)**, §9.1-6·15·16·17, §9.2 S-A34-11. 초안 (가)와 달라진 곳: E4 (ㄴ) 뺌(D-K9-71 "재생 쪽에만"), E1·E2에 "증거 Root 파일 바이트 sha와도 같음"(보충 24 §4.2 A_K92-M 꼴 그대로) 더함, E1–E4 값의 형 조건(float·dict) 더함, 자기 시험 12사례 → 21사례 + V-B 마른 점검. (나)(다)(라)는 고르지 않았습니다.
- **Q-A34-2 → D-K9-72 = (가) 점검 순서만 바꿈.** 반영: §3.1 순서 1–6, §9.1-7, §9.2 S-A34-12. (나)(다)는 고르지 않았습니다.
- 아래는 첫 Declare 초안의 질문 글 그대로입니다(기록용; 정의는 위 반영 자리가 이깁니다).

### (기록, 답 = D-K9-71) Q-A34-1 GB-7′(그리고 해시 A/B 조건 1)의 조건 7을 B1 동결본에서 어떻게 둘까요?

- 배경: §2.1. 선언 A = V ∪ A_K8 ∪ R2-12로는 61결정 모두 `/metadata/k92_w`·`k92_hb`·`k92_hb_seed_binding`(재생 쪽에만)과 T ≤ 750의 `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634`(재생 쪽에만) 때문에 조건 7이 거짓입니다. 제어 7필드·CSV는 같을 것으로 봅니다 [추론: V-B 무제어 6결정에서 A 안 R2 차이만 있었음].
- **(가) 권장 — 목록 파일은 §14.3 그대로, 판정에 K9-2 선언 차이 E_K92를 데이터 전에 더함.** `gb7_allowed.py`는 R2-12만(S-K17 지킴, 목록 sha `a8148f38…`). GB-7′ 판정기는 A 밖 경로를 다음 E_K92로만 다시 나눕니다. 그 밖 A 밖 경로가 하나라도 있으면 조건 7 거짓.
  - E1 `/metadata/k92_w`: 재생 쪽에만 있고, 값의 `evidence_sha256` = `b4b7294df0369874ea53dd5f0538abd31bac1c946aebdf241bdc7837a7671712`, `u4_sha256` = `22384c00313a0104a9febf5344914acd15f20058a0a62fe91d2bc085dcbb292b`, `after` = 5209.8(repr `5209.8`).
  - E2 `/metadata/k92_hb`: 재생 쪽에만 있고, `evidence_sha256` = `b9fa1d01b9d922e9fc327793aa428cd7b544dae221044704dea7f0af610f20ee`, `rule_code_sha256` = `d9bd53920eea89ace2b71a589d780069c3c7191be889aca894994ddf65bcc106`.
  - E3 `/metadata/k92_hb_seed_binding`: 재생 쪽에만 있고 값이 0.0 또는 1.0.
  - E4 `/metadata/head_discharge_floor_173_p4_e36d6761cfeac634`: (ㄱ) 재생 쪽에만 있고 값 repr = `1045.1612903225805`, 또는 (ㄴ) 양쪽에 있고 원본 값 < s·재생 값 = s. 두 경우 모두 그 결정의 재생 `k92_hb_seed_binding` = 1.0. 이름이 다르면(해시16 다름) 거짓.
  - 근거: 보충 24 §4.2의 A_K92-M(새 쪽 한쪽 메타·결정적 잎 sha 조건)과 H5 선언 차이(하한 키 (가)(나)·묶임 1.0·기대 이름)를 같은 꼴로 옮긴 것입니다(D-K9-38 ⑦로 승인된 키 켬 비교 규칙). 보고에는 "선언 목록 기준" 결과(FAIL 예상)와 "A ∪ E_K92" 결과를 둘 다 적고, 관문 통과·실패는 뒤의 것으로 셉니다. 해시 A/B 조건 1도 같은 E_K92를 씁니다.
  - 판정기 자기 시험 사례(데이터 전): E1–E4 각각 통과 사례, 각 sha 하나 바꿈 → 거짓, 원본 쪽에도 있음 → 거짓, E4 이름 해시 다름 → 거짓, E4 값 1 ulp 큼 → 거짓, 묶임 0.0인데 E4 → 거짓, 목록 밖 새 키 하나 → 거짓 (12사례).
- (나) D-K9-67 글자 그대로(A만). GB-7′은 FAIL로 예상되어 관문 단계에서 STOP하고 그때 다시 묻습니다. 푸시·동결을 한 뒤라 한 번 더 돌아갑니다.
- (다) `gb7_allowed.py`에 K9-2 키 항목을 더 넣음(예: R1-17 `/metadata/k92_(?:w|hb|hb_seed_binding)`, `/metadata/head_discharge_floor_173_p4_[0-9a-f]{16}`). 보충 24 §14.3("한 항목만")·S-K17을 바꾸는 결정이고, 하한 키는 값 조건 없이 넓게 허용됩니다. 새 목록 sha를 데이터 전에 고정.
- (라) GB-7′·해시 A/B를 키 끔 튜닝(`d0f9ef39…` 바이트, FRZ_K92 밖 사본)으로 돌려 코드 동일성만 봄. 배포 튜닝을 재생하지 않아 J1 꼴과 다릅니다(키 켬 쪽은 K9-2 J-0·G-K1에 기댐).

### (기록, 답 = D-K9-72) Q-A34-2 승격의 make_config 점검을 어떻게 할까요?

- 배경: §2.2. K8-7처럼 "CFG를 바꾼 뒤·커밋 전"에 `make_config_n31.py --k92b1 --check`를 돌리면 생성기가 바뀐 CFG를 바탕으로 읽어 `ValueError`로 끝납니다.
- **(가) 권장 — 점검 순서만 바꿈.** CFG를 바꾸기 **전** 깨끗한 K9-2-5 트리에서 `python -B diagnostics/sdmpc_n31_20260924/make_config_n31.py --k92b1 --check` → `CONFIG_N31_K92B1_OK family=single_value sha256=c8e3ee2c…1866`(팔 파일 = 생성기(지금 CFG) 출력; 오늘 [실행] 같은 결과). 그 뒤 바이트 복사, 그 뒤 §3.1 점검 2–5(`build_obs150_detectors.py --tuning CFG --check`, hash-object = `b6ccd50d…`, JSON 두 경로, diff 범위). 승격 길(팔 바이트 복사)은 K8-7과 같고, 바뀌는 것은 첫 점검의 시점뿐입니다. K9-2-6 뒤 이 명령이 오류인 것은 공개(§9.1-7).
- (나) K9-2-6 앞에 `make_config_n31.py`에 바탕 파일 경로 인자를 더하는 진단 전용 커밋을 넣고, 바뀐 CFG에서도 `git show e27ceac8:CFG`를 바탕으로 점검. 코드 변경이 하나 늘고 그 커밋의 관문이 필요합니다.
- (다) 승격하지 않고 팔 파일을 `-Tuning …\config_n31_v2_k92b1.json`으로 배포(보충 24 §14.2가 적은 다른 길). GB-7′ 재생은 R-obs3 provenance의 튜닝 경로(= CFG, 키 끔)를 쓰므로(OG_METHOD §2) 배포 튜닝을 재생하지 않게 됩니다. K8-7·K8-10 선례와 다릅니다.

---

## 11. 자체 점검

1. *관문이 데이터 뒤에 움직일 길은?* 판정기·검증기·분석 도구 모두 그 단계 첫 계산 전에 sha 고정(§5.0, §8.0), 고정 뒤 수정 = STOP(S-A34-4·7·11). E_K92의 정의와 판정 함수 sha는 관문 데이터 0개에서 이 보충이 정합니다(§5.2).
2. *E_K92가 너무 넓지 않나?* 경로 넷만(이름 정확히), 재생 쪽에만 있을 때만, 결정적 잎은 고정 sha와 같고 Root 파일 sha와도 같을 때만, 하한 키는 이름·값 repr·그 결정의 묶임 1.0까지 봅니다. 계산 값 차이는 이미 A의 R2 항목 안에서만 허용됩니다. V-B 무제어 6결정에서 A 밖은 이 넷과 사슬 인공물뿐이었고 [실행], 함수는 합성 거짓 사례 18개를 모두 거짓으로 냈습니다(§5.2-6) [실행].
2b. *E_K92가 너무 좁아 아무 자료에서나 떨어지지 않나?* 이 위험은 남습니다: 예를 들어 T ≥ 900에서 원본 하한 값 < s인 결정이 있거나, GB-7′ 재생의 하한 키 이름이 R-obs3 이름과 다르면 FAIL → STOP입니다. 근거상 둘 다 예상하지 않지만(보충 24 §5.2 :330; 이름 문맥은 기록된 런 매니페스트에서 옴, `signal_head_observation.py` `validate_provenance`) [추론], 결과를 본 뒤 조건을 넓히지 않습니다(사용자 결정).
3. *T = 150 계수가 유효성을 깨지 않나?* J1-A 항목이 아니고 건강 점검 H15에서 1.0을 기대값으로 봅니다(보충 24 §14.2).
4. *승격 뒤 런타임이 V-B·K9-2 관문과 같은가?* FG-1·FG-2(런타임 파일 차이 0), 튜닝 바이트 = V-B·J·F에 쓴 CFG-B1(`c8e3ee2c…`, VB-I3 CFG-B1과 같은 sha [읽음 V-B 보고 §2 V2]).
5. *V-A − J1 비교가 공정한가?* 같은 시드·같은 망·같은 수요, 코드 출처 차이는 §8.1에 적음, 미삽입 합집합을 두 쪽에 같게(U9).
6. *풀링이 J1보다 넓지 않나?* 평균·sd·90 % CI·음/양·평균/NC %만, J1과 같은 꼴.
7. *유지 결정이 분석을 흐리지 않나?* 유지 결정은 따로 세고(§7.1), 보고 머리에 표로 둡니다. 성능 지표는 런 전체(유지 포함)로 냅니다(J1과 같음).
8. *빈 칸*: 첫 Declare 초안에서 결정이 필요했던 칸은 §3.1-1(make_config 점검)과 §5.1-1 조건 7 두 곳뿐이었고, 이 판에서 D-K9-72·D-K9-71로 채웠습니다(§3.1 순서 1–6, §5.1 1·2행, §5.2). 비운 칸·"정함 예정" 칸은 없습니다. 실행 중에만 알 수 있는 값(커밋 sha, FRZ_K92 이름·`FREEZE.json` sha, `run_id`, 감시기·건강 점검·분석 도구 sha)은 "그 단계 기록에서 읽어 다음 단계 기대값으로 쓴다 / 그 단계 첫 계산 전에 고정한다"는 규칙으로 정해져 있습니다.
9. [검토] *J1 순서(승격 → 검증 → 푸시·동결 → 관문 → 검증 → 발사)를 다 따르나?* 마무리 판에는 승격 뒤 독립 검증이 없었습니다. §3.3 VerifyPromote와 §4.1 전 조건, §6.1 발사 전제로 채웠습니다(R3, R18).
10. [검토] *판정기 사본의 차이가 닫혀 있나?* "기대값만 바꾼 판"은 사실과 달랐습니다(K8b 구동기에는 G-H1·G-H2·G-R 단계와 D-K9-12 분기가 있음). §5.0 R4의 닫힌 일곱 항목으로 적었고, 그 밖 차이는 STOP입니다.
11. [검토] *DECISION_FAILED·유지·멈춤·좌석 경합 때 무엇을 하나?* §7.2 사건별 처리 표. 새로 더한 것은 WD도 못 끝내는 멈춤(S-VA-7), 발사 거부(S-VA-8, 실패 시드 아님), 셈 불가 INCOMPLETE, 좌석 24 h 질문 지점뿐이고 모두 STOP·질문 쪽입니다.
12. [검토] *합집합이 다른 d를 한 표에서 빼지 않나?* §8.2 R8로 열마다 합집합을 적고, 같은 합집합 열끼리만 셈합니다.

## 12. 이 보충을 쓰며 한 일 [실행, 모두 읽기 전용 — 쓰기는 `VA/`, 이 파일·`.sha256`, `REPVA/declare/` 사본뿐]

### 12.1 첫 Declare (초안 `9ac1828e…`)

- 재개 점검: 보충 34·`VA` 없음, GWT8 head·status·K8 브랜치, 드라이브, 프로세스 수.
- 읽음: 결정 기록, 보충 21·22·24(§2, §4–§8, §14), 33 머리, K8 선언 §4–§6, OG_METHOD, K8b·J1 동결·관문·발사 보고, J1 분석 방법·보고서·유효성, V-B 보고 r3, CAUSES·lens_link174 일부, GWT8 `runtime_setup.py`·`signal_head_observation.py`·`make_config_n31.py`·`build_obs150_detectors.py`·`gb7_allowed.py`(HEAD), `run_sdmpc_n31.ps1` 좌석·RunsRoot 줄.
- 실행: sha256·blob·줄 끝 확인, CFG 대 CFG-B1 JSON 차이, `VA/work/a34_gb7_keyon_probe.py`(메모리 안 R2-12 목록 sha·판정 표, V-B VB-41w 무제어 6결정 B1 대 OFF 차이 경로 분류, R-obs3 v3c3-s31 메타 키 이름), `make_config_n31.py --k92b1 --check`(깨끗한 트리), `build_obs150_detectors.py --tuning CFG-B1 --check`, 메모리 안 `apply_k92b1(CFG-B1)`. 모두 BELOW_NORMAL·`python -B`·`PYTHONHASHSEED=0`, 실행 전후 GWT8 `status --porcelain` 0줄·새 `.pyc` 0.
- 하지 않음: 커밋·푸시·동결·관문·재생·VISSIM·COM·시험 0. 동결본·런 폴더 쓰기 0. 봉인 시드·v3c3-s47·codex 64cf 0. V-A 데이터 0(없음).

### 12.2 Declare 마무리 (이 판, 2026-10-23 07:1x–07:4x KST)

- 재개 점검: 고정 자리 `SP/K8_PREDECLARATION_AMENDMENT_34.md` 없음, 초안 sha `9ac1828e…ab2a` = `.sha256`·LOG, 결정 기록 sha `6b76cc09…af88`(D-K9-71·72 :226-232), GWT8 head `e27ceac8`·`status --porcelain` 0줄·K8 브랜치 `b9734abe`(로컬·원격), 원격 `claude/k92*` 0, `frozen/`에 새 동결 없음, RVA 없음, python·VISSIM·cscript 0, C: 39.5 GB·D: 368.9 GB.
- 읽음: 보충 24 §4.2(A_K92-M·H5 원문)·§5.2 :330, OG_METHOD §2–§3, K8b `gjudge.py`(조건 7·D-K9-12 분기), GWT8 `runtime_setup.py:230-286`(k92_w 잎), `signal_head_observation.py:120-150`·`:180-330`(하한 키 이름·씨앗·묶임), `make_config_n31.py:640-660`·`:715-730`, `gb7_allowed.py`(HEAD), 보충 32 VB-I6(기대 이름), `K92_VALUES.json` `/p0_2/f_expected_floor_keys`.
- 실행(한 번에 하나, BELOW_NORMAL·`python -B`·`PYTHONHASHSEED=0`·`PYTHONDONTWRITEBYTECODE=1`, 실행 전 도구 sha를 LOG에 고정): `VA/work/a34f_facts.py`(증거 sha·blob, V-B B1 k92 잎 sha·형, R-obs3 하한 키 이름; exit 0), `VA/gates/gb7_k92decl_selftest.py` v1·v2(각각 합성 21 + V-B 마른 점검 6결정 + 이름 교차 6; exit 0, `ALL_OK`, 두 출력 바이트 같음). 실행 전후 GWT8 `status --porcelain` 0줄, 새 `.pyc` 0개.
- 쓴 곳: `VA/work/a34f_facts.*`, `VA/gates/gb7_k92decl.py`·`gb7_k92decl_selftest.py`·`gb7_k92decl_selftest{,_v2}.out.txt`·`.err.txt`·`selftest/`·`selftest_v2/`(결과 JSON, 합성 Root `ek92_roots/good|bad` = 증거 두 파일 사본, bad는 W 증거 끝 1바이트 더함), 이 파일·`.sha256`, `VA/a34_pins.sha256`, `VA/LOG.md`, 사본 `REPVA/declare/`.
- 하지 않음: 커밋·푸시·동결·관문·재생·VISSIM·COM·러너·시험 실행 0(금지 목록 시험 0). GWT8·`.git`·동결본·런 폴더·R-obs3·V-B 출력·VBT 쓰기 0. 끈 프로세스 0. 봉인 시드 37·59·61·67 자료·codex 64cf 숫자·v3c3-s47 0. V-A 데이터 0(없음).

### 12.3 ReviewDeclare (이 검토판, 2026-10-23 07:33–08:0x KST)

- 재개 점검: `VA/LOG.md`에 ReviewDeclare 줄 없음, `VA/AMENDMENT34_FIXED.md`·`SP/K8_PREDECLARATION_AMENDMENT_34_r1.md` 없음 → 첫 검토. 대상 sha `37180bed…a01c` = `.sha256`. C: 39.5 GB·D: 368.9 GB, python·VISSIM·cscript 0. GWT8 head `e27ceac8`, `status --porcelain` 0줄, K8 가지 로컬·원격 `b9734abe`, 원격 `claude/k92*` 0.
- 읽음: 이 보충 전문, 보충 21 §4–§9, 보충 22 §7–§12, 보충 24 §2.2·§4.2·§5.2·§14, K8 선언 §4–§6, OG_METHOD 전문, K8b `GATES_K8b.md` §0–§2·`FREEZE_PUSH_K8b.md` §0–§2, `gjudge.py`(:1-240)·`g_driver.py`(단계·감시)·`gcommon.py`(상수), J1 `J1_LAUNCH.md` 전문, `FREEZE_PUSH.md:16,:44`, J1 `ANALYSIS_METHOD.md` §1–§2, `J1_REPORT.md` 절 목록·:405-411, V-B 보고 §0-5·§3.7·§6, `GATES_K92B1.md:67`, `lens_link174.md:28-36`, GWT8 `gb7_allowed.py`·`make_config_n31.py:636-740`·`runtime_setup.py:276-290,:405-426`·`signal_head_observation.py:186-264,:300-330`, `run_sdmpc_n31.ps1:1-120,:140-240`, `gb7_k92decl.py` 전문, 자기 시험 v2 출력.
- 실행(모두 읽기 전용): `VA/a34review/rev_a34.py`(sha256 `198a4b90826f806f236fadb9d2622b234de23869789f051d1a8b1bc064328848`, 실행 전 LOG 고정; BELOW_NORMAL·`python -B`·`PYTHONHASHSEED=0`·`PYTHONDONTWRITEBYTECODE=1`, 1회, exit 0, `ALL_OK`) — 고정 목록 78/78, 승격 바이트·JSON 차이 재유도(정확히 두 경로, 팔 쪽에만, 증거 sha = 파일 바이트, 정책 키 둘 다 hold), R2-12 이유 글자 = 보충 24 :592, 목록 sha `a8148f38…7af1`·인쇄 줄·판정 표, E 경로 넷 A 밖, `b9734abe..e27ceac8` A 21·M 10(CFG·`gb7_allowed.py` 없음), FRZ_K8b 표 경로 = `git ls-tree -r b9734abe` 10,548. PowerShell: `frozen/` 최상위 목록, NC3·J1·R-obs·RVA·REPVA 경로 있음/없음, `D:/VISSIM_runs` 깊이 2에서 `k92va|k92pre|20261023` 이름 0개, 동결 차이 대조 대상 33경로의 `git ls-files --eol`과 `hash-object --no-filters` = e27ceac8 blob(33/33 같음), `git diff --name-status b9734abe e27ceac8 -- diagnostics/sdmpc_n31_20260924/tools` 빈 결과.
- 쓴 곳: `VA/a34review/`(도구·`out/`), `SP/K8_PREDECLARATION_AMENDMENT_34_r1.md`(+ `.sha256`), `VA/a34_pins_r1.sha256`, 이 파일·`.sha256`, `VA/a34_pins.sha256`(1행 바꿈 + 다섯 줄), `VA/AMENDMENT34_FIXED.md`, `VA/LOG.md`, 사본 `REPVA/review/`.
- 하지 않음: 커밋·푸시·동결·관문·재생·VISSIM·COM·러너·시험 0. GWT8·`.git`·동결본·런 폴더·R-obs3·NC3·J1 런·V-B 출력·VBT 쓰기 0. 끈 프로세스 0. 봉인 시드·codex 64cf·v3c3-s47 0. 목적값·예측값 출력 0. V-A 데이터 0(없음).

---

## 13. 초안(`9ac1828e…`) 대비 바뀐 곳 (모두 결정 반영 또는 그 정합)

| # | 자리 | 바뀐 것 | 까닭 |
|---|---|---|---|
| C1 | 제목·머리 | "초안, 고정 전" → 선언판, 고정 방법(`.sha256`·LOG·`a34_pins.sha256`) | 고정 |
| C2 | 머리 "판정 말" 줄 | "§8.6의 미리 정한 규칙" → "§8.4" | 초안의 절 번호 오기(표시 규칙은 §8.4) |
| C3 | 줄임말 | A, E_K92, VBT 줄 더함 | 새 §5.2가 씀 |
| C4 | §0 | 결정 기록 새 sha(`6b76cc09…`)·초안 sha·마무리 도구/출력·증거 파일·`K92_VALUES.json` 행, 마무리 때 상태 줄 | 근거 갱신 |
| C5 | §1 | D-K9-71·72 행 | 결정 원문 |
| C6 | §2 | 제목, 2.1 표 R-obs3 하한 키 줄(55결정 [실행]·보충 24 :330), 2.1·2.2 끝 줄 Q → 결정·반영 절 | 결정 반영 |
| C7 | §3.1 | 커밋 전 점검 1–5 → 순서 1–6(1 = 편집 전 깨끗한 트리 make_config 점검, 2 = 바이트 복사, 3–6 = obs150·blob·두 경로·diff 범위), 커밋 본문 | D-K9-72 |
| C8 | §5.0 | 판정기 목록에 `gb7_k92decl.py`(sha 고정), D-K9-12 분기 빼기, 자기 시험 (i)(iii)·독립 검증 문구 | D-K9-71, 보충 24 §14.3 |
| C9 | §5.1 | 1행 조건 7 = A ∪ E_K92, 보고 둘; 2행 조건 1 같은 정의 | D-K9-71 |
| C10 | §5.2 (새 절) | E_K92 정의 표·연결·블라인드·자기 시험 결과·바꾸지 않는 것 | D-K9-71 |
| C11 | 초안 (가) E_K92 대비 | E4 (ㄴ) 뺌; E1·E2에 Root 파일 sha 조건 더함; 값 형(float·dict) 조건 더함; 사례 12 → 21 + V-B 마른 점검 | D-K9-71 글("재생 쪽에만"), 보충 24 §4.2 A_K92-M 꼴 |
| C12 | §8.0-1 | 보고 머리 10번 = E_K92 처리 | 정합 |
| C13 | §9.1 | 6·7·14 고침, 15·16·17 더함 | 결정 반영·공개 |
| C14 | §9.2 | S-A34-1 고정 방법 명시, S-A34-11·12 더함 | 결정 반영 |
| C15 | §9.3 | 고정 목록에 결정 기록 새 sha·초안·마무리 도구·E_K92 함수·자기 시험·`K92_VALUES.json` | 고정 |
| C16 | §10 | 질문 → 결정과 반영 자리(질문 글은 기록으로 남김) | 결정 반영 |
| C17 | §11 | 1·2·8 고침, 2b 더함 | 정합 |
| C18 | §12 | 12.1(첫 Declare, 글 그대로)·12.2(마무리) | 기록 |

- 그 밖의 글(§3.2, §4, §5.1 FG·3–5행, §6, §7, §8.1–§8.4, §9.1 1–5·8–13)은 초안 그대로입니다.

---

## 14. [검토] ReviewDeclare에서 바꾼 곳 (검토 전 판 `_r1` `37180bed…a01c` 대비; V-A 데이터 0개 상태, 2026-10-23)

- 검토 범위(과제 글): J1 선례와 보충 21–33에 비춘 적대적 검토 — 승격 바이트와 점검(팔 − 바탕을 검토가 다시 냄), GB-7′ 목록 항목이 보충 24 §14.3 그대로인지, 동결 조건, 오프라인 관문 정의·문턱이 선언된 변경 말고 J1과 같은지, 런 이름·루트 겹침, 유효성·STOP 완전성(`DECISION_FAILED`·유지·러너 멈춤·좌석 경합), 분석 방법의 완전성과 데이터 없음, 판정 말 없음, Ω와 ④·Ω 밖 함께.
- 정의·문턱·E_K92·판정 함수(`gb7_k92decl.py` `d15e9cc0…fb11`)·자기 시험·관문 표 1–5행의 통과 조건은 **바꾸지 않았습니다**. 바꾼 것은 사실 정정, 빠진 절차(J1 선례에 있던 것), 모호한 글의 조작 정의, STOP·질문 쪽으로만 더한 규칙입니다. STOP을 풀거나 문턱을 넓힌 곳은 없습니다.

| # | 자리 | 찾은 것 | 고친 것 |
|---|---|---|---|
| R1 | §0 마무리 때 상태 줄 | "`frozen/` 최상위 `sdmpc31_*`는 FRZ_K7·FRZ_K8·FRZ_K8b 셋뿐"은 거짓. 실제 `sdmpc31_*` 17개 + robocopy 로그 17개 [실행] | 사실로 고침. 판정 영향 없음(§4.2-11은 앞뒤 차이) |
| R2 | §3.2 점검 | (3) 기대 출력 `V=7 … list_sha256=…`이 실제 인쇄 줄 `GB7_ALLOWED schema=k8-gb7-allowed/v1 V=7 …`의 일부라 "출력 = …"이 성립할 수 없음 [실행 재계산]. 편집 전 조건·바이트 범위·CR·E 경로 대 A 점검 없음. docstring 줄이 보충 24 글에 `- `·`.`를 붙인 꼴인데 적지 않음 | (3)을 줄 전체로 고정. 편집 전 조건, (5) 지운 줄 0·더한 줄 범위·이유 글자 117자 sha16 `7a51c150f6bc3cc4`·CR 0, (6) E 경로 넷 A 밖 더함. docstring 꼴 공개 |
| R3 | §3·§4.1 | J1은 `VERIFY_PROMOTE` pass = true·검증 head = 푸시 head 뒤에만 푸시(`FREEZE_PUSH.md:16,:44`). 마무리 판에 승격 독립 검증 없음 | §3.3 VerifyPromote 새 절, §4.1 전 조건·STOP, S-A34-13, §9.3 고정 |
| R4 | §5.0 판정기 사본 | "기대값만 바꾼 판"·"기대값과 조건 7 연결뿐"은 틀림: K8b 구동기에는 G-H1·G-H2a–d·G-R1·G-R2/G-H3 단계와 `cmp21` 비교, D-K9-12 분기가 있음(`g_driver.py:330`, `gjudge.py:172-201`). §5.1 1행의 "제어 7필드 61/61"은 K8b `gb7_row.ok`에 들지 않음(`gjudge.py:125,:132-133,:157`) | 사본 차이를 닫힌 일곱 항목으로 적음(기대값, 조건 7 연결, PASS에 제어 7필드 61/61, D-K9-12 분기 뺌, 단계 목록, 읽기 전용 감시 대상, 자기 시험 프로필). 그 밖 차이 = STOP |
| R5 | §5.0 실행 위생 | 이 워크플로 규칙(긴 목록은 파일로 — 보충 28, 임시 이름에 PID만 쓰지 않음 — 보충 33, 튜닝·증거 파일에 경로 문자열 금지 — D-K9-42)이 관문 절에 없음 | 한 줄로 더함 |
| R6 | §6.3·§7.1·§7.2 | WD가 끝내지 못하는 멈춤·러너가 `EXIT` 없이 죽음의 처리 없음. `NOT_LAUNCHED`를 실패 시드에 넣어 좌석 경합 하나가 K8 §6-7(2시드 이상 → 분석 전체 STOP)을 부를 수 있음(보충 21 Q-H7은 무효 런을 셈). J1-A 셈 불가 처리 없음. 사건별 처리가 흩어져 있음 | S-VA-7(4,800 s 무진행·`EXIT` 없음 → STOP·알림, 끄지 않음), S-VA-8(발사 거부 → STOP, 실패 시드 아님), INCOMPLETE → STOP, 실패 시드 셈은 `START` 줄 있는 런만, 사건별 처리 표 |
| R7 | §6.2 | 감시기를 띄우는 때(J1은 s31·s41 둘 다 뜬 뒤)와 s41이 s31 끝까지 못 뜨는 경우, 좌석 기다림 상한 없음 | 감시기는 두 cmd PID를 안 뒤에만, s41 늦음 처리, 좌석 24 h 질문 지점, `EXIT` 없는 런은 S-VA-7 |
| R8 | §8.2 | 한 표에 U6(V-A)·U9·U6(J1) 합집합 칸이 섞여 ④·④b·Ω 밖 (a)·(c)의 d가 서로 빼지지 않음 | 합집합에 기대는 칸은 열마다 합집합 이름, 같은 합집합 열끼리만 셈, §8.4 표시 규칙도 (A) U6(V-A)·(B) U9 |
| R9 | §8.3 | K8 §5.5 끝의 J1-R 재현 표본에 대한 V-A 처리가 없음 | §8.3-14: J1처럼 하지 않음, 열린 항목 |
| R10 | §8.0-1 | 보고 머리 8번 고정 문구(보충 22 §11) 끝 "K9-2에서 고친다"가 묶음 1에는 맞지 않음(보충 24 §2.4 유령 movement 범위 밖). 6번 H-R1은 V-A에 없음 | 고정 문구는 그대로, 아래 한 줄을 글자로 고정. 6번 "해당 없음" |
| R11 | §8.4 | 보충 24 §14.3 "공개: … J1 단서 덧붙임에 적습니다"의 자리가 없음. 기존 덧붙임 파일은 고정 목록에 묶여 바꿀 수 없음 | 새 파일 `VA/J1_CAVEAT_ADDENDUM_K92VA.md`(머리 + 세 줄)를 글자로 고정, 보고 단계에서 만들어 보고서 머리에 붙임 |
| R12 | §5.2-6, §8.4 | "씨앗이 엄격히 이기지 못함"(판정처럼 읽히는 낱말), 표시 칸 안 "개선" 허용 여지, Ω와 ④·Ω 밖을 문장 단위로도 함께 적는다는 글 없음 | 메커니즘 글로 바꿈. 표시 칸 글 세 문구로 고정, "개선" 어디에도 안 씀, Ω가 나오는 모든 표·문장에 ④·Ω 밖 (a) |
| R13 | §8.1 표 | "코드 차이 = B1 두 키뿐"은 부정확(K9-2-1·2 런타임 코드 두 파일도 다름, 키 끔이면 같은 동작) | 튜닝 두 키 + 런타임 두 파일(G-K0)로 풀어 씀, s41·s43은 K8-8·9 코드 + K8-10 튜닝 키 더함 |
| R14 | §9.1 | V-B §6-6(측정 훅)의 V-A 처리 없음 | §9.1-18: V-A는 V-B 훅을 쓰지 않음 |
| R15 | 머리·S-A34-1·§9.3 | 고정 목록 1행이 이 파일 sha라 고치면 목록이 깨짐. 고정점 파일 지정 없음 | 고정점 `VA/AMENDMENT34_FIXED.md`(64자), 목록 1행 갱신 + 검토 산출 다섯 줄(83줄), `_r1` 보관 |
| R16 | 줄임말 NC3 | 작업 지시 글은 NC3를 `20261001_sdmpc31_v3c3/sdmpc31_v3c3_nc_s{31,41,43}`로 적었으나 그것은 R-obs 런 묶음이고 s41 폴더가 없음. 이 보충의 NC3는 J1 정의(`20261001_v3c3/s<S>_v3c3nc/run`) [실행·읽음] | 줄임말에 구분을 적음(정의 불변) |
| R17 | §5.2-3 | T ≥ 900 "씨앗 안 묶임" 근거가 보충 24 :330 한 줄뿐 | J-0 실측 근거(`GATES_K92B1.md:67`)와 바탕 튜닝 차이 단서를 더함(조건 불변) |
| R18 | §5.1 결과 처리·§6.1·§9.1-20 | 발사 전제가 한곳에 없음(VerifyGates pass, 분석 고정, 감시 도구 고정). 분석 도구를 J1보다 일찍 고정함을 공개하지 않음 | §6.1 발사 전제 (1)–(6), §5.1 결과 처리에 VerifyGates pass, §9.1-20 공개 |

- 검토가 다시 냈고 문제없던 것(모두 [실행] `rev_a34.py` 또는 PowerShell, 위 §12.3): 고정 목록 78/78; CFG `d0f9ef39…`/blob `268ae471…`/278,142 B, CFG-B1 `c8e3ee2c…`/blob `b6ccd50d…`/278,607 B(작업 트리 = e27ceac8 바이트, CR 0), 팔 − 바탕 = 정확히 `/urban/capacity/head_floor_seed`·`/urban/sc109w_through_saturation`(둘 다 팔 쪽에만), 두 값의 `evidence_sha256` = 증거 파일 바이트 sha(`b9fa1d01…`, `b4b7294d…`), 정책 키 둘 다 `hold_previous_on_exception`; R2-12 정규식·자리(R2-11 바로 뒤)·이유 글자 = 보충 24 §14.3, 목록 sha `a8148f38…7af1`, A_K8 35(R1 16·R2 12·R3 7), 판정 표 6행; FRZ_K8b 표 경로 = git 트리; 동결 차이 기대 A 21·M 12·D 0(33경로 작업 바이트 = blob, 33/33); `diagnostics/sdmpc_n31_20260924/tools/` 변경 0(FG-4); RVA·`k92va`·`k92pre` 이름 겹침 0; NC3·J1 네 런·R-obs3·FRZ_K8b·VBT 경로 있음; 관문 문턱(GB-9′ (가)(나) 표, 해시 T 집합, 61·74 수)·G-H5′ 조건 1–7이 OG_METHOD·보충 21 §7.5·§8과 같음; 동결 PASS 1–12가 보충 22 §7.2·`FREEZE_PUSH_K8b.md` §0과 같은 꼴; 런 이름·발사 줄·좌석 규칙(`run_sdmpc_n31.ps1:24-29,:84-86,:115,:145-148,:229-235`); J1 벽시계 인용(`J1_REPORT.md:408-410`); E_K92 판정 함수의 `raw_diff`가 K8b `gjudge.raw_diff`와 같은 꼴(`gjudge.py:32-49`); 유지·실패 시드 규칙이 보충 21 §4.1·§4.2와 같음; 분석 지표·통계·표시 규칙이 J1 방법 §2와 같고 V-A 데이터 0.
