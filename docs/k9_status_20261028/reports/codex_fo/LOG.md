# FO LOG (codex SDMPC 고속도로만 팔, D-K9-112)

- 시각은 KST. 표시: [실행]·[읽음]·[추론]·[계산]. 판정 낱말 없음.

## 2026-10-27 18:40 KST — FACTS 단계 (VISSIM 0)
- [읽음] 근거 결정 D-K9-112: K9_1_J1_NOTES_20261013.md sha 4d47ce5b77830264ed6472000e0ec6b88330c22a244a1542e66652db674611cf :380.
- [읽음] codex freeway_only 팔 = solo 판(2f28000a) + 설정 cd193948… (sdmpc_actuator_scope + sdmpc_information_scope + 고속 경로 18칸 끔). 러너·env·VBS·워치독은 joint 와 같음(설정 경로·sha 만 다름).
- [실행] FRZ_B1(a49981ff, FREEZE 558de2c1…) 코드에 두 스위치 grep 0건. codex git 에 2f28000a 객체 없음. FRZ_B1 은 모르는 adapter 키를 거부하지 않음 → 키만 넣으면 B 와 같은 런 [추론].
- [실행] solo 고침 = evaluation/controllers 13 고침 + 4 새 파일. 인계 사본 바이트가 solo FREEZE(f55ecec3…)와 18/18 같음. B0/B1 고침 7파일과 겹침 0.
- [실행] B 3시드 무제어 명령(t=1, t=750) green 68·offset 17 이 codex baseline 과 0 차이.
- [읽음] information_scope 는 목적함수(FW_W·FW_E 만)·예측기(실험용 지역 예측기)·NP 자원·고속 경로를 함께 바꿈 → D-K9-112 의 "같은 스위치" 와 "B 와 하나만 다름" 이 동시에 맞지 않음.
- 멈춤(STOP). 선택지 O1–O4 는 FACTS_FO.md §6. 사용자 결정 대기.
- 산출: FACTS_FO.md sha 8f379cc73be25509cdd2241a3c8edb6c46e888867b94cd4b4c8c7a49daf72447. 작업 파일 work/ (jdiff.py 57efcff2…, cmp_solo_vs_frz.py 58ec5196…, cmp_freeze_code.py 57206d03…, cmp_freeze_code.json f35c0b7a…, cmp_solo_vs_frzb1.json ad0b936d…, solo_vs_frzb1_13files.diff d29cdb26…).
- 무거운 일 0, 잠금 사용 0, VISSIM 0, kill 0, frozen·GWT8·codex 작업 트리 쓰기 0, sealed/ 0, 봉인 시드 0, 커밋·푸시 0.

## 2026-10-27 19:50 KST — Declare 단계 시작 (사용자 결정 D-K9-113 = O2, VISSIM 0)
- [읽음] 결정 기록 K9_1_J1_NOTES_20261013.md 의 D-K9-113 항목 뒤 sha 1bb1b1ef3b6897fd49ce7ca8c283cfec3e7f6555c9c5ee15488448638068d69b (:382-387).
- 할 일: FRZ_FO 만들기(FRZ_B1 + solo 17파일 + FO 설정 키 하나), 러너 사전 점검, 관문·발사기·비교 규칙 선언(PRE_FO), 발사기 모의 실행. VISSIM 발사 0.
- [실행] 짓기 도구 sha (첫 실행 전 고정): fo_overlay.py 2960eaa2c545a7a9d135c15cdf61c04207f33fdee41060f8eb428fa127faef99, fo_tree_check.py a791a033a49e1f16858da92e27870b92204a76490871e584e95fd084e43177b1, fo_chain.ps1 eb06bf75c65216330576b2d49e036c78332a93c79bc170a9cf6c0b05dfce0bc8, fo_preflight_wrapper.ps1 a793319ae262f840191e959482678430655d31362910c1240a8b11b477d10857, fo_summary.py 131a90f95cb4fa41fe4325152e1813dc7514defe277e8ab38b6a9dddc0530ebb, fo_launch_wmi.ps1 2b6119f83870e4878e1a132cc4fddc60aa3755f5dd7a1d488739e10a4ff3f700 (모두 ASCII).
- [실행] fo_overlay.py 자기 시험(작은 사본 트리 work/build/selftest_overlay_748603): 검사 11개 모두 참. 새 설정 sha 80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3, B 설정과 잎 차이 = /adapter/sdmpc_actuator_scope 아래 86잎(green 68 + offset 17 + mode)뿐. baseline 은 B 3시드(provenance 시드) t=1·t=750 무제어 명령과 차 0.
- 사슬은 공용 잠금 heavy.lock 아래에서 돈다(19:27 부터 vsl_plant 가 잡고 있어 기다릴 수 있음).

## 2026-10-27 19:58 KST — FRZ_FO 동결·사전 점검 끝 (사슬 fo_chain.ps1, WMI PID 36084, BELOW_NORMAL)
- [실행] 공용 잠금: 19:49:45 vsl_plant 가 잡고 있어 30 s 기다림 → 19:50:15 잡음 → 19:57:54 내 토큰 확인 뒤 지움. 남의 VISSIM 30964·30544·31656 은 건드리지 않음.
- [실행] fo/source = b1/source HEAD a49981ff 를 받은 새 git 저장소 + robocopy. 덮기 전 파일표 = FRZ_B1 FREEZE 와 0 차이(7,989).
- [실행] 덮기(overlay): 검사 11개 참. 덮은 뒤 FRZ_B1 대비 바뀜 13 + 더함 5(새 모듈 4 + config_fo_v3c3.json) 정확히. 13파일 차분 = Facts 차분과 같은 줄(frzb1_to_fo_13files.diff 643115b3…).
- [실행] FRZ_FO = D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/frozen/sdmpc31_a49981ff_202610271954, FREEZE.json sha256 d7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373, 파일 7,994, 바이트 495,975,719, tree sha 8994da3e…, git head a49981ff, status 3,671줄. FREEZE_VERIFIED 앞·뒤 두 번.
- [실행] FO 설정 diagnostics/b0_v3c3/config_fo_v3c3.json sha256 80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3. 러너 6ff68b38… · 망 3de889f0… · B 설정 729640af… 그대로.
- [실행] 러너 사전 점검 4개 모두 종료 0·검사 19개 참: s31 dea0ba5e…, s41 51766b3b…, s43 c640c095… (FO 설정), s31b d5a724f8… (B 설정, 관문 대조 R0 입력 전용). B1 사전 점검과 잎 대조: 다른 잎은 선언한 것뿐(created_at, run_id, freeze sha, 설정 경로·sha 6잎, files/adapter/sha256), controller_sources 는 solo 17파일만 다름.
- [실행] 짝 점검: NC3·B·V-A 시드(provenance/run.json) 일치, NC3 망 sha s31 3de889f0… / s41 726af589… / s43 51478c39…(기록된 원천 sha 와 같음), B·V-A 망 3de889f0…, .sig 42개가 FRZ_FO·NC3·B·V-A 9곳에서 바이트 같음. FO 결과 뿌리 아직 없음.
- 요약 fo_summary.json 0c6b3d00…, FO_BUILD_PASS true. 무거운 일은 잠금 아래 1건(사슬). VISSIM 0, kill 0.

## 2026-10-27 20:36 KST — Declare 끝: PRE_FO 고정 (FO 데이터 0, VISSIM 0)
- [실행] 고정 문서: PRE_FO.md 9a83dbaff52701f478b30f04e78d073b7ebcebf59cfb0ecda194905c7357b2fa, COMPARE_RULE_FO.md d5a47e8dd7922121adcc9847f7a051e093525d4cdfe482ce84a7a7f72c62e9c0, PINS_FO.sha256 5458c623ae3a19afc0db9f07f56bd9bb142ac56c78f48cffdc75cc710204723e (124줄, sha256sum -c 모두 OK). 이 셋은 FO 데이터 뒤 고치지 않음.
- [실행] FRZ_FO FREEZE d7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373, FO 설정 80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3 (B 설정 + adapter.sdmpc_actuator_scope 하나; information_scope 없음; 고속 경로·VSL 110 고정 B 그대로).
- [실행] 관문 도구(아직 안 돌림): fog_build_inputs.py e9741850…, fog_replay.ps1 b8eda978…, fog_queue.ps1 d015a692…, fog_summary.py 7ac04cd5…, fog_sg_native.py 751e1e4c… (64자는 PINS_FO). 관문 = R1–R3(B 기록 T=900 상태, FO 설정) + R0(B 설정 대조) + G2(도시 SG GREEN 대 native) + FRZ_FO verify.
- [실행] 자기 시험(모두 FO 데이터 아님): G2 양성 대조(codex 64cf freeway_only: 규칙 대 LDP 0 프레임 차·.lsa 대 LDP 0·64cf 판 G2 0·readback 규칙 0, SG 136), 음성 대조(B T=900 최적 계획 대 native: 122 SG 다름, 3시드); 요약 도구(B 기록을 넣으면 R1–R3 A5·A6·A8 거짓, R0 C4·C5 참); 입력 도구(4라벨 95파일, 못 바꾼 경로 0; 첫 시도에서 80자 자르기 결함 찾아 고침); FW_E 칸 도구 fo_fwe.py 102/102; 표 도구 fo_tables.py 318/318; 런 점검 도구(B 런: V1·V3·V5 참, V2·V4 거짓); 발사기 모의 17/17(+ GATE_NOT_PASSED·SHA_MISMATCH 새 상황), 멈춤 도구 모의 7/7. 남의 VISSIM [30964, 31656] 모의 앞·뒤 같음.
- [실행] PowerShell 대소문자 충돌 검사로 $out/$OUT(멈춤 모의), $code/$CODE(재생), $s/$S(분석 실행기) 셋을 핀 전에 고침.
- [실행] 사건: nc_s*.json 글롭이 nc_s47.json·nc_s53.json 의 sha256 을 계산함(내용 열람·출력·사용 0). 이후 도구는 시드 31·41·43 경로만 이름으로 씀.
- [실행] 결정 노트 sha 가 19:31 다른 줄기(D-K9-114, C1 가드)의 덧붙임으로 1bb1b1ef… → bfd3fc2b… 로 바뀜. D-K9-113 줄은 그대로.
- 무거운 일: 짓기 사슬 1건(잠금 19:50:15–19:57:54, 내 토큰만 지움). 자기 시험은 캐시·작은 파일만(FZP 0). VISSIM 0, 재생 0, kill 0, 커밋·푸시 0. frozen/*·FRZ_B0·FRZ_B1·V-A·K92·GWT8·codex 작업 트리 쓰기 0, sealed/ 0, 봉인 시드 0.
- 다음: T=900 관문 큐(PRE_FO §5.1 명령). 통과 전에는 런을 띄우지 않음.

## 2026-10-27 21:05 KST — Review 단계: PRE_FO·동결·사전 점검·모의 실행 적대적 리뷰, 고침 r2 (FO 데이터 0, VISSIM 0)
- [실행] 동결 트리 FRZ_FO 대 FRZ_B1: FREEZE 표 바뀜 13 + 더함 5, 빠짐 0, 표 밖 차이 0; 18파일 디스크 = 표; 17 코드 = solo FREEZE, FRZ_B1 의 13 = joint FREEZE; 러너·B 설정 바이트 같음 (review/rv_manifest_diff.py, rv_solo_check.py).
- [실행] FO 설정 대 B 설정: 다른 잎 86 개 모두 /adapter/sdmpc_actuator_scope 아래, information_scope 없음, VSL 고정 110 같음 (rv_cfg_diff.py). FO 사전 점검 provenance 대 B 런 provenance: 선언한 잎만 다름 (rv_prov_diff.py).
- [읽음] O2 코드 길: 신호 green·offset 축 0(sdmpc.py:420), 미터 축 24(:457, 소유자 FW_W·FW_E), VSL 축 0(:462), 범위 검사(:558, :931, sdmpc_sequence.py:196), 축 없는 소유자 QP 건너뜀(:1210). 키 없는 줄은 B 와 같은 값.
- [실행] G2 v3c3 양성 대조: codex 64cf T=900 baseline 행 대 B v3c3 3시드 .lsa [2,899] → 136 SG 0 프레임 차, pass true (rv_g2_pos.py). .sig 42 = 64cf 망 바이트.
- [실행] .lsa: 쓴 SG 에는 COM 상태가 안 남음(64cf 122 SG 290,691 프레임 대 LDP), 쓰지 않은 146 SG 는 native 와 0 차(64cf·B 3시드). 도시 readback 요청=읽음·ok 1, B 3시드 어긋남 0 (rv_lsa64.py, rv_lsa_b.py).
- 찾은 것: R1 V1 이 B 규칙보다 엄격(유지 1회면 시드 버림) + PRE_FO §12 와 어긋남; R2 범위 검사 원인 유지를 잡는 칸 없음; R3 V4 가 요청 글자만·쓰지 않은 SG 안 봄; R4 비교 규칙이 B 의 진입 E·W 줄을 밝히지 않고 뺌; R5 G2 의 v3c3 양성 대조 없음; R6 멈춤 확인 주체·이름 바꾸기 실패 처리 없음; R7 발사기 머리 주석의 B 이름(코드는 FO, 고치지 않음).
- 고침(r1 남김): fo_run_check.py r2 1415cddcfe5029e036245c4da5278b913e14c605ed1faf148d225afa659937c9 (r1 acfd805b… = fo_run_check_r1.py; V1 B 규칙, V4(d)(e), V9 멈춤). 자기 시험 B 3시드: V1·V3·V5·V9 참, V2·V4 거짓(V4 는 (c) 만 거짓). 음성 대조: (d) 에 쓴 SG 넣으면 122 SG 다름, 합성 범위 유지 → V9 거짓 (rv_runcheck_neg.py).
- 고정 문서 r2: PRE_FO.md 743909fd95374568e1679f965f42e565fbe74d7486c04d4d446b26ed4691b210 (r1 9a83dbaf… = PRE_FO_r1.md), COMPARE_RULE_FO.md 7ef1b03da6492de3c077e349086f6125fe4ac0e2673359bf1949bc185640c5c8 (r1 d5a47e8d… = COMPARE_RULE_FO_r1.md), PINS_FO.sha256 314d51dc5006ee65f3913940f2e7064b19f1a43d2d50e3c7df049ef7760cae66 (154줄, sha256sum -c 154/154 OK; r1 5458c623… = PINS_FO_r1.sha256), pins_list.txt fcd8cd30…, 리뷰 기록 PRE_FO_FIXED.md 725c16773529897be59fe6c19dc9b3483ff0ee5ec9d105b24055b09d51ad6c02.
- 바뀌지 않음: FRZ_FO FREEZE d7fa4db6…, FO 설정 80e0abef…, 관문 도구 다섯, 발사기·래퍼·시작·멈춤 도구, fo_ana·fo_tables·fo_fwe.
- 무거운 일 0(잠금 사용 0, FZP 0), VISSIM·COM·재생 0, 남의 VISSIM(30964) 손댐 0, kill 0, frozen/*·FRZ_B0·FRZ_B1·V-A·K92·FRZ_FO·GWT8·codex 작업 트리 쓰기 0, sealed/·봉인 시드·v3c3-s47 값 0, 금지 시험 0, 커밋·푸시 0.
- 다음: T=900 관문 큐(PRE_FO r2 §5.1 명령 그대로). 통과 전 런 없음. 발사 때 -PreSha 743909fd… -RuleSha 7ef1b03d… -PinsSha 314d51dc….

## 2026-10-27 21:07 KST — Gate 단계 시작 (PRE_FO r2 §5.1 그대로, VISSIM 0)
- [실행] 발사 전 확인: PRE_FO.md 743909fd…, COMPARE_RULE_FO.md 7ef1b03d…, PINS_FO.sha256 314d51dc…, PRE_FO_FIXED.md 725c1677… 가 .sha256 파일과 같음. `sha256sum -c PINS_FO.sha256` 154/154 OK(관문 도구 다섯·fo_launch_wmi·s5_collect 포함).
- [실행] 입력 있음: 사전 점검 provenance 4개(s31·s41·s43·s31b), B 기록 3시드 state_000900.json·action_000750.json/csv·action_000900.csv. 공용 잠금 없음, PC 의 VISSIM 1개(30964, 남의 것, 손대지 않음).
- [실행] 선언 밖 준비 1건(도구 바이트·명령·조건은 그대로): 관문 출력 뿌리 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/fo/gate` 가 없었음. `fog_queue.ps1` 0단계는 `freeze_verify_before.txt` 를 그 폴더에 Start-Process 재지정으로 씀. PS 5.1 탐침(scratchpad 의 없는 폴더로 재지정): python 은 종료 0 인데 파일이 생기지 않음 → 이대로면 요약의 freeze_verify.before 가 도구 탓으로 거짓이 됨. 그래서 빈 폴더만 미리 만듦(그 밖의 쓰기 0). B 관문 1 은 사전 점검이 그 폴더를 먼저 만들어 이 문제가 없었음.

## 2026-10-27 21:38 KST — Gate 단계 끝: T=900 관문 + G2 (FO 재생 4, VISSIM 0)
- [실행] 21:07:31 WMI 발사(PRE_FO r2 §5.1 명령 그대로, 큐 PID 26896, BelowNormal) → 21:33:07 done. 기록 `work/gate/queue_fog.state.txt` eb9fee4b01245079caa3a5043a916ce096ba3251f0459402ec53be5a96e444ad.
- [실행] FREEZE_VERIFIED 앞(21:09:20)·뒤(21:32:51), FRZ_FO d7fa4db6…. 입력 넷 각 95파일, 못 바꾼 경로 0.
- [실행] 재생(공용 잠금 아래, 내 토큰만 지움): R1 s31 170.875 s, R2 s41 167.408 s, R3 s43 161.980 s (FO 설정), R0 s31 471.345 s (B 설정). R0 는 남의 잠금(vsl_plant, PID 47852) 때문에 270 s 기다림, 손대지 않음.
- [실행] R1–R3: A1–A8 모두 만족. 좌표 meter 24 뿐, 도시 green 68·offset 17·signal 17행 baseline 차 0, signal_sg 122행 세 시드 같음(bd21439e…), VSL 66행 110, 정책 토큰 7673d367…(셋 같음, B 848d55d3… 와 다름), 정책 차 = actuator_scope 하나, 지역 표지 0. 결정 벽시계 최대 170.875 s ≤ 1,500 s.
- [실행] R0: C4 정책·토큰 = B, C5 action_000900.csv 바이트 = B 기록 fb297196… (HOLD 아님).
- [실행] G2 세 시드: 쓰는 SG 136(창 122 + 적색 14) GREEN 차 0 프레임 [2, 899], 주기 17곳 같음, 기대 밖 0, native 전용 24 안 씀. → 다르면 멈춤 조건 생기지 않음.
- [실행] 관문 요약 work/gate/fog_summary.json sha256 d0494cfb78270f2d6b272e189e6b6606ed33c324de5262321d2195dc8adb2ce1, pass true (발사기 -GateSha 값). g2_R1/R2/R3.json 5b7e1c2c…/0fe04a5f…/dbf96cb9….
- [실행] FRZ_FO 안 캐시 106개(__tangentcache__ 100, __pycache__ 6)는 FREEZE 제외 폴더, 그 밖의 새 파일 0.
- 보고: GATE_FO.md sha256 은 GATE_FO.md.sha256 에. 선언 밖 준비 1건(빈 폴더 G)은 21:07 항목. 보고만(무게 낮음): T=900 미터 값이 B 기록과 다른 곳 s31 2·s41 1·s43 4 / 8.
- VISSIM 0, FO 런 발사 0, kill 0, 남의 VISSIM 30964 손댐 0, frozen/*·FRZ_B0·FRZ_B1·V-A·K92·GWT8·codex 작업 트리 쓰기 0, sealed/·봉인 시드·v3c3-s47 값 0, 금지 시험 0, 커밋·푸시 0.
- 다음: 사용자 발사 허락 뒤 PRE_FO §6 시작 명령(-GateSha d0494cfb…). 허락 전에는 띄우지 않음.

## 2026-10-27 21:41 KST — Runs 단계 시작 (PRE_FO r2 §6 시작 명령, D-K9-112 "관문 뒤 자리 나는 대로 3시드")
- [실행] 발사 전 확인 21:38–21:41: 관문 요약 fog_summary.json d0494cfb… pass true; PRE_FO.md 743909fd…, COMPARE_RULE_FO.md 7ef1b03d…, PINS_FO.sha256 314d51dc…, PRE_FO_FIXED.md 725c1677… 가 .sha256 파일과 같음; `sha256sum -c PINS_FO.sha256` 154/154 OK; fo_launcher.ps1 e73990d0…, fo_wrapper.ps1 b79f38ac…, fo_launcher_start.ps1 b9994d2c…, fo_status.ps1 9b4e35be…, fo_stall_stop.ps1 961bc521… 핀과 같음.
- [실행] PC VISSIM 1개(30964, 남의 것, 손대지 않음), 우리 발사기 0, 결과 뿌리 D:/VISSIM_runs/20261028_codex_fo_v3c3 없음, 공용 잠금 없음, 디스크 C 16.2 GB · D 191.5 GB.
- 다음: fo_launcher_start.ps1 (WMI, Normal) → 발사기가 자리 규칙대로 s31 → s41 → s43.

## 2026-10-27 21:47 KST — 발사 기록 (Runs)
- [실행] 21:40:13 fo_launcher_start.ps1 → WMI ReturnValue 0, 발사기 PID 47704 (Normal, 영수증 `fo/fo_launcher_start_receipts.log`). 위 21:41 항목의 시각은 계획 시각이고 실제 시작은 21:40:13 입니다.
- [실행] s31: 21:40:14 래퍼 PID 40692 (발사 직전 PC VISSIM 2 = 30964·51120, 둘 다 남의 것), 워치독 VISSIM 53192 (21:41:14). s41: 21:41:28 래퍼 PID 50620 (직전 3), VISSIM 52432 (21:42:25). s43: 21:42:41 부터 SEAT_BUSY (PC VISSIM 4 = 남 2 + 우리 2), 자리 기다림.
- [실행] 남의 VISSIM 51120 은 21:40:03 에 새로 뜸(우리 발사 10 s 전). 세기만 함, 손대지 않음.
- [실행] 21:47:19 `-Plan prescan`(NC3·V-A 만, FO 데이터 아님, COMPARE_RULE_FO §7 (가)) 을 fo_launch_wmi.ps1 로 WMI 발사, PID 53868, BelowNormal. FZP 일마다 공용 잠금.
- 감시 도구: `fo/work/run/fo_poll_wait.ps1` (B 의 b_poll_wait.ps1 4a0b0dd4… 에서 상태 스크립트 경로·머리 주석만 바꾼 읽기 전용 사본, sha e9694a4d4e9fb9a7b283be46ab1e562d045b3433384b2621e10a90bcab0d0a71). 30 s 마다 fo_status.ps1, 깃발이 바뀌면 바로, 아니면 ≤ 520 s.

## 2026-10-27 22:13 KST — prescan 끝 (NC3·V-A, FO 데이터 아님)
- [실행] `-Plan prescan` 21:47:20–22:06:06, 22단계 모두 exit 0, 잠금 22번 모두 0 s 만에 잡고 내 토큰만 지움, STOP 0 (`fo/work/ana/ana_prescan.state.txt`).
- [실행] 점검 X3b 를 미리 셈(가벼운 일): `CW/vhr_fo/scan_out` 의 nc3_s31·s41·s43·va_s31·s41·s43 가 `CW/vhr_b/scan_out` 의 같은 파일과 scan_sec 빼고 같음 6/6.
- [실행] 런: s31·s41 T=900 첫 제어 결정 exit 0 (155.4 s · 159.7 s), 유지 0. s43 은 자리 기다림(PC VISSIM 4 = 남 30964·51120 + 우리 53192·52432).

## 2026-10-27 22:28 KST — s43 발사 (자리 남)
- [실행] 남의 VISSIM 51120 이 22:17:40–22:19:11 폴 사이에 스스로 끝남(우리는 건드리지 않음). 22:19:11 발사기가 s43 을 띄움: 래퍼 PID 53820, 발사 직전 PC VISSIM 3 (30964 남 · 53192 s31 · 52432 s41), 워치독 VISSIM 55356 (22:20:08, 57 s 뒤). SEAT_BUSY 폴 23번(21:42:41–22:17:40, 약 36 분).
- [실행] 지금 PC VISSIM 4 = 남 1(30964) + 우리 3. 세 런 모두 결정 exit 0, 유지 0, 무진행 문턱 499 s 넘은 적 없음.

## 2026-10-28 01:10 KST — 중간 감시
- [실행] 남의 VISSIM 30964 가 01:01:26–01:09:45 폴 사이에 스스로 끝남(건드리지 않음). PC VISSIM 3 = 우리 셋.
- [실행] 01:09 sim_sec: s31 4,800 · s41 4,350 · s43 4,200. 결정 exit ≠ 0 은 0, 유지 시도 0, 결정 벽시계 최대 s31 466.3 · s41 527.9 · s43 428.4 s. 무진행 499 s 넘은 폴 0 (폴 최대 진행 나이 약 66 s). kill 0, 재발사 0.

## 2026-10-28 03:51 KST — s31 끝, stage s31 발사
- [실행] s31: 03:49 무렵 런 로그 STAGE=SIM_DONE·SIM_SEC=9000, 래퍼 끝 runner_exit 0, 래퍼 벽시계 22,204.5 s, native_status requested_native_arms_complete_unanalyzed, 발사기 03:50:42 TRY_END s31_run1_try1 status=completed. 결정 61, exit ≠ 0 은 0, 유지 시도 0, 결정 벽시계 최대 466.3 s.
- [실행] 03:51:04 `-Plan stage -Seed 31` 을 fo_launch_wmi.ps1 로 WMI 발사, PID 36664, BelowNormal (잠금 그때 비어 있음). 런 점검 fo_run_check.py 31 은 이 plan 의 마지막 단계.

## 2026-10-28 04:00 KST — stage s31 끝, 런 점검 s31
- [실행] `-Plan stage -Seed 31` 03:51:04–03:58:00, 11단계 모두 exit 0 (FZP 일 6개 각각 공용 잠금, 내 토큰만 지움), STOP 0.
- [실행] 런 점검 `fo/work/ana/runcheck_s31.json` sha256 2aa529424885d440dcba653e9ec7c72bebdfa681ad26ab1918401ef262323d73: V1·V2·V3·V4·V5·V6·V9 모두 참 (usable true, pass true). V4 = 쓴 SG 136 차 0 프레임, 쓰지 않은 SG 146 차 0, 도시 readback 46,396행 어긋남 0. V6 FO 접두 = B (aef8ea5b…), NC3 와는 다름(0.1 s 행 1개, † 대상). V7 워밍업 CSV 6개 = B, t=1 글자 = solo. V8 n 55 · 중앙 211.9 · 최대 466.3 s. V9 범위 유지 0.
- [실행] s31 은 끝난 런이라 상태 도구의 IDLE_OVER_499 표시는 무진행 정책 대상이 아님(활성 시도 아님).

## 2026-10-28 04:20 KST — s41 끝, stage s41, 사건 하나(내 읽기가 기록 줄을 막음)
- [실행] s41: 래퍼 끝 runner_exit 0, 래퍼 벽시계 22,801.9 s, 발사기 04:02:52 TRY_END s41_run1_try1 status=completed. 결정 61, exit ≠ 0 은 0, 유지 0, 최대 527.9 s.
- [실행] 04:03:26 `-Plan stage -Seed 41` WMI 발사, PID 29748, BelowNormal. 단계 1–10 exit 0 (04:03:27–04:09:45, 잠금 내 토큰만 지움). 단계 11 fo_run_check.py 41 은 04:10:10 시작, 04:10:14 에 출력을 끝까지 씀(`logs/ana_stage_s41_11_fo_run_check.out.txt` 의 RUNCHECK 줄, `runcheck_s41.json` 5,395 B, .err 0 B).
- **사건** [실행]: `ana_stage_s41.state.txt` 에 "step end 11" 과 "plan stage_s41 done" 줄이 없고 fo_ana 프로세스는 사라졌습니다. 04:10:14 에 내 감시 명령이 그 상태 파일을 PowerShell Get-Content 로 읽었습니다. 시험(scratchpad 임시 파일): PS 5.1 Get-Content 가 파일을 여는 동안, 그리고 .NET FileShare.ReadWrite|Delete 로 여는 동안에도 Add-Content 는 "being used by another process" 로 실패합니다. fo_ana.ps1 은 ErrorActionPreference Stop 이라 Note(Add-Content) 실패에서 끝납니다 → 내 읽기가 원인으로 봅니다 [추론, 시험 두 개로 받침]. 도구·결과는 바꾸지 않았습니다.
- [실행] 보충(선언 밖, 가벼운 읽기 전용): 핀 sha 같은 fo_run_check.py 를 같은 env 로 `41 <recheck 경로>` 로 다시 돌림 → exit 0, `runcheck_s41.json`·`.v4c.json` 과 바이트 같음 (0dbf0a43585bedea3433c8d1bacea0a8fcff453d5ac318a2660baf351f642750 / 6a192d85…). 출력 `fo/work/ana/recheck/`.
- [실행] 런 점검 s41: V1·V2·V3·V4·V5·V6·V9 모두 참 (usable·pass true). V4 쓴 SG 136·쓰지 않은 SG 146 차 0, 도시 readback 46,396행 어긋남 0. V6 FO 접두 = B (817dc613…), NC3 와 다름(0.1 s 행 1개). V8 n 55 · 중앙 204.2 · 최대 527.9 s. V9 0.
- 교훈: 돌고 있는 fo_ana 의 상태 파일은 읽지 않는다(프로세스가 끝난 것을 본 뒤에만 읽음). s43 stage 부터 적용.

## 2026-10-28 04:40 KST — Runs 단계 끝: 세 런 완주, 런 점검 셋, FO_RUNS
- [실행] s43: 래퍼 끝 runner_exit 0, 래퍼 벽시계 21,779.5 s, 발사기 04:22:32 TRY_END s43_run1_try1 status=completed, 04:22:32 LAUNCHER_EXIT all seeds ended (폴 265, ERROR 0, LAUNCH_STOPPED 0).
- [실행] 04:22:59 `-Plan stage -Seed 43` WMI 발사 PID 47572 → 04:29:46 11단계 모두 exit 0 (프로세스 끝을 본 뒤에만 상태 파일 읽음). 런 점검 s43: V1·V2·V3·V4·V5·V6·V9 참, V6 FO = B = NC3 (86c06c73…).
- [실행] 세 시드 모두 시도 1번, 재발사 0, 멈춤 도구 호출 0, kill 0, 활성 런 IDLE_OVER_499 0, PC VISSIM 최대 4. 남의 VISSIM 30964·51120 은 스스로 끝남, 6768 은 01:26 부터 돎(손대지 않음).
- [실행] 끝난 뒤 우리 프로세스 0, 공용 잠금 없음, 디스크 C 15.4 GB · D 179.9 GB.
- 산출: FO_RUNS.md sha256 f562ed67df37326c7e738b86f1ad57c9f3e97582f0a9b5f0791bd701ae27c6bf, 숫자 모음 work/run/fo_runs_collect.json ec1ce7d8… (도구 fo_runs_collect.py 0451d4d9…, 읽기 전용). 보고 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_fo.
- 다음: `-Plan final`(Ω701·④·Ω 밖·FW_E 칸·표)은 분석 단계. 이 단계에서는 돌리지 않음.

## 2026-10-28 04:40 KST — Analyze 단계 시작 (COMPARE_RULE_FO §8 (다) `-Plan final`, VISSIM 0)
- [실행] 시작 전 확인 04:36: `sha256sum -c PINS_FO.sha256` 154/154 OK; PRE_FO 743909fd…, COMPARE_RULE_FO 7ef1b03d…, PINS_FO 314d51dc…, PRE_FO_FIXED 725c1677…, FO_RUNS f562ed67… 가 .sha256 파일과 같음. 공용 잠금 없음. `ana_final.state.txt` 없음. stage 출력(vhr_fo j1·first ×3, omega_fo 캐시, rawcheck_fo s31·s41·s43, fwe fo_s* ×3, readback cycles_fo* ×3) 있음.
- [실행] PC 의 VISSIM 1개(6768, 남의 것)와 codex 프로세스(pwsh·python)는 세기만 함, 손대지 않음.
- 선언 밖 덧붙임(결과 무관): 선언한 `-Plan final` 의 단계는 모두 캐시만 읽어(FZP 0) fo_ana 가 잠금을 잡지 않습니다. 과제 지시("잠금 아래")를 따르려고 바깥에서 공용 잠금을 한 번 잡고 그 안에서 `fo_ana.ps1 -Plan final` 을 바꾸지 않고 한 번 돌리는 껍데기 `work/ana/fo_final_locked.ps1` sha256 29e3b31b8b0284731bfbca0a2bcc4f26bf7f3ec806ec49235bda0734e2622a34 (ASCII, 구문 오류 0, 대소문자 충돌 0) 를 씀. 도구·인자·출력 경로는 그대로. fo_ana 가 도는 동안 그 상태 파일은 읽지 않음(04:10 사건 교훈).
- 발사: `fo_launch_wmi.ps1 -Script work/ana/fo_final_locked.ps1 -StateName final_locked.state.txt` (WMI, BELOW_NORMAL, 숨김).

## 2026-10-28 04:55 KST — Analyze 단계 끝: `-Plan final`, FO_REPORT (VISSIM 0)
- [실행] 위 04:40 항목의 시각은 계획 시각이고, 실제 발사는 04:37:50 입니다: `fo_launch_wmi.ps1` → WMI ReturnValue 0, 껍데기 PID 36168(BelowNormal). 04:37:50 공용 잠금 0 s 만에 잡음 → `fo_ana.ps1 -Plan final`(PID 8884) 04:37:51–04:38:25, 8단계 모두 exit 0(vhr_v3c3_all_fo 1.1 s, omega metrics 12.2 s, top66, metrics_fo ×3, fo_fwe run 15.2 s, fo_tables 1.1 s; 단계마다 PINS_FO sha 대조 통과) → 04:38:25 내 토큰만 지움 → 25 s 쉼 → 04:38:51 끝. 도는 동안 상태 파일 읽지 않음. 상태 `work/ana/ana_final.state.txt` c36e20f0…, `work/ana/final_locked.state.txt` 112dea62….
- [실행] 출력: `work/ana/fo_tables_out.json` 4e9b30f1…, `.md` 17265252…, `work/ana/fo_fwe_out.json` c100f9d4…, V `CW/vhr_fo/v3c3_all.json` 930fee15…, O 40107da9…, P 9c7fe1f4…, top66 88bc6c67…, metrics_out FO 54a9d796… / 5c4eb143… / 3fa96bbf….
- [실행] 점검: X1 최대 0.0004 veh·h(0.05 넘은 값 0), X2 차 ≤ 7e-12, X3 참(멈춤 거짓), X3b 6/6 참, X4 차 0, X6 0, X7 stops 0, 진입 E·W 의 nc = B 고정 출력 nc(차 0). 멈춤 규칙 걸린 것 0.
- [실행] 새 읽기 도구(가벼운 일, FZP 0, python -B, PYTHONHASHSEED=0): `work/ana/fo_report_extract.py` 439c9e1f… → `FO_REPORT.json` eb2fbb5b4d7bc51141656a316c2858dcd9f5cdc713517190efb22948c631db6f; `work/ana/fo_report_build.py` 69e52a29… + 원문 `work/ana/FO_REPORT_src.md` 2df29f9a… → `FO_REPORT.md` 4d0fc8305be3ab749ae0b85c928d95b6b51c13241c5bd743c651d1ac367767f4 (금지 낱말 0, 봉인 시드 이름 0, 자리표 0). 글 고침용 일회 패치 `patch_build_31337.py` b2e8c994…, `patch2_40211.py` 0addfa73…(부호 글자·참/거짓·진입 W s43 반올림 +1.3·반올림 단서).
- [실행] 독립 대조: V 를 직접 읽어 Ω701·④·Ω 밖 (a)·①·④b·④b 1098·④b 1099 의 FO − NC3·B − NC3·B − FO 가 표와 같음. (B − FO) + (FO − NC3) = B_RESULTS r2 의 B − NC3. B 미터 명령 분포(54결정) = B_RESULTS r2 §1.5.
- [계산] 요지: FO − NC3 ① −32.7 / −188.2 / −76.4(B − NC3 의 0.88 / 1.06 / 0.86배), B − FO ① −4.6 / +10.2 / −12.6; B − FO Ω701 −154.1 / −326.3 / −191.2, ④b 1099 +631.5 / +355.6 / +77.9, ④ +407.9 / −41.2 / −198.3, Ω 밖 (a) +562.1 / +285.0 / −7.1. 판정 낱말 없음.
- 지킨 것: VISSIM 0, 재생 0, kill 0, 남의 VISSIM(6768)·codex 프로세스 세기만 함. frozen/*·FRZ_B0·FRZ_B1·V-A·K92·FRZ_FO·GWT8·codex 작업 트리 쓰기 0. sealed/·봉인 시드·v3c3 봉인 시드 값 0. 금지 시험 0. 커밋·푸시 0. PRE_FO·COMPARE_RULE_FO·PINS_FO 바꾸지 않음.
- 보고 사본: D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_fo/ 에 FO_REPORT.md·FO_REPORT.json(+ .sha256), LOG.md.

## 2026-10-28 05:11 KST — Verify 단계 시작: 검증 도구 고정 (FO_REPORT·작성자 분석 출력 읽기 전, VISSIM 0)
- 할 일: FO_REPORT 의 주요 칸을 원자료(FZP·readback·명령·.lsa)에서 새 도구로 다시 셈. FO 가 도시 native 였는지(도시 SG 쓰기 = baseline·GREEN 초 = native), VSL 110, 미터 readback = 명령, 표시·64cf/v3c3 빼기 없음 확인. 고칠 것은 r2(r1 남김).
- [실행] 검증 도구 sha256 (모두 새로 씀, ASCII, 작성자 도구·VERIFY_B 도구 코드 재사용 없음; 폴더 `fo/verify/`):
  - vf_scan.py 679482849a5e20f29aebe052e0cea6dad067aa7140986bc492f22da27f6f4c8e (FZP → 링크 체류 두 꼴, 900 s 창 차량-프레임, 첫 관측 S(W), FW_E 체인 100 m 칸 두 규약)
  - vf_runfiles.py c5341207eefcaeb743f0c2663b21793599e484b4df68b936be58af5067d5f317 (런 로그·명령 CSV·결정 JSON·signal/vsl readback·.lsa)
  - vf_pairs.py 96e55e6c71a0a0caac64af6a38feab1a4de3b61f5dd3961a11433fd23a008b19 (짝 차·비·VERIFY_B 스캐너와 교차 대조)
  - vf_seedcheck.py 6e9c9e6bd39788a75530067c58e06f1f2ce4d7f3d4a31a6ac67f66c48acc060a (시드 = provenance/run.json, FZP 머리 File 줄 = 같은 런 뿌리)
  - vf_fzp_list.txt a70862078f148c1d803a5f68128aa3b190620355227223ecdfde09c642bf0acd (FZP 12개: FO·NC3·B·V-A × 3)
  - 핀 PINS_VF.sha256 78c30a307463486e0b68f0f7ef73d9d2bbe27b3f31830ca23a667e610acb9470 (위 다섯), 큐 vf_queue.ps1 336e04c6ffea38c69306ec1910d460b3d26e6c8b6150f892c35dfa4b88acb9c8, 발사 vf_launch.ps1 4bb6cbb02ccb86dca2661f48ec43b5bfdaa5463fc711501e0a66201ff2fea57d (PS 구문 오류 0, 대소문자 충돌 0).
- [실행] 도구 시험(가벼운 일): FO s31 FZP 앞 400,000줄 사본으로 vf_scan 한 번(사본은 지움), FO s31 .lsa·signal_readback 으로 주기(17곳: SC7 120, 나머지 150)와 SC1 SG1 의 어긋남(밀림 0/1/2 s → 108/0/108) 확인. 판정과 무관한 시험.
- 밝힘: FO_REPORT.md·FO_REPORT.json·FO_RUNS·작성자 분석 출력(V·O·P·M·fo_tables_out·fo_fwe_out·runcheck_*)은 아직 열지 않았습니다. 다만 이 단계 지시문에 Analyze 요약 숫자가 들어 있어 그 숫자는 보았습니다.
- 밝힘(사건): `reporting_partition.json` 위치를 찾으려고 `D:/VISSIM_handoff/20261024` 아래를 파일 이름으로 재귀 검색 1회 했습니다. 결과에서 sealed 경로는 걸렀고 내용 열람·출력 0 입니다. 이후 그 폴더는 이름을 아는 파일만 읽습니다(`derived/reporting_partition.json` 3142f69c…, `derived/omega_membership_exact.json` efdfaeb1…).
- 다음: `vf_launch.ps1 -QueueName vq1` (WMI, BELOW_NORMAL, 숨김). FZP 하나마다 공용 잠금 heavy.lock 한 번(배타 생성·30 s 재시도·60 분 상한·내 토큰만 지움·놓은 뒤 25 s 쉼), runfiles 도 잠금 아래.

## 2026-10-28 05:17 KST — Verify: 큐 vq1 발사, 둘째 도구 묶음 고정 (VISSIM 0)
- [실행] 05:10:56 `vf_launch.ps1 -QueueName vq1` → WMI ReturnValue 0, PID 53968 (BELOW_NORMAL, 숨김). 위 05:11 항목의 시각은 계획 시각이고 실제 발사는 05:10:56 입니다. FZP 하나마다 공용 잠금 한 번(상태 `verify/out/vq1.state.txt`, 돌는 동안 읽지 않음).
- [읽음] vq1 발사 뒤 FO_REPORT.md(4d0fc830…)·FO_REPORT.json(eb2fbb5b…)을 처음 읽음. 보고서가 인용하는 칸(진입 E·W, RF3·RF4·RF6·RF8, DA1, 미터 명령 분포, X5, 벽시계, 접두 †)을 덮으려고 둘째 도구 묶음을 **보고서를 읽은 뒤** 썼습니다. 숫자는 원자료(FZP·명령 CSV·readback·런 로그·.err)와 vq1 출력에서만 나오고, 보고서 값은 대조에만 씁니다.
- [실행] 둘째 묶음 sha256 (PINS_VF2.sha256 3473c98c57a5659c1c21bd99f54d3323b1a741169d681b8b8630fce5d1a0c4e0):
  - vf_extra.py cdfa8636cfdd8dd6c0ef3c4343294a502b9059d7518c1f791af07edf40182dc3 (FO·B 미터 명령 54결정 분포, FO·B 미터 readback 주기 표, 결정 벽시계, .err 남은 차, V-A 미터 readback)
  - vf_check.py 03123d3e1b024ca1b8889d1f45b44d20bbe534423aea39720d594550791cea11 (FO_REPORT.json·md 의 칸과 대조)
  - vf_prefix.py 9dc482725611573c0bdfcfd93c5ae70b7fceb61bacd4a88284b6374188f4102f (FO·B·NC3 FZP 900 s 전 접두 해시)
  - vf_runfiles.py c5341207… (vf_extra 가 함수 하나를 가져다 씀, 바뀌지 않음), vf_fzp_list.txt a7086207…
  - 큐 vf_queue2.ps1 f8d96322e8a16a1c353c918c1e364733ca6876dd23c0d4821929fc30a53734e9, 발사 vf_launch2.ps1 4f1d58484aa9a8cba60becfd0e1337173b2545f8432581fbd3d926bea36e1a71 (구문 오류 0, 대소문자 충돌 0, ASCII).
- [실행] vf_extra 시험 1회(가벼운 일, FZP 0, 출력은 지움): 돌아감 확인.
- 다음: vq1 끝난 뒤 `vf_launch2.ps1 -QueueName vq2` (vf_prefix 는 잠금 아래).

## 2026-10-28 05:34 KST — Verify 단계 끝: VERIFY_FO, FO_REPORT r2 (VISSIM 0)
- [실행] vq1 05:10:56–05:23:22: seedcheck(12/12 시드 = provenance), FZP 스캔 12개(각각 공용 잠금 한 번, 첫 시도에 잡음, 28–33 s 보유, 내 토큰만 지움, 25 s 쉼), runfiles(잠금 05:21:51–05:22:56), pairs. 모두 exit 0. vq2 05:23:40–05:24:20 (PID 52452): 핀 대조 PINS_OK, vf_prefix(잠금 05:23:41–05:23:52), vf_extra, vf_check. 모두 exit 0. 지금 잠금 파일 없음.
- [실행] 결과: J·md 의 칸 2,511개 대조 — T1·T2 JSON 441칸 최대 차 0.0009, md 330칸 반올림 폭 안. NC3·B·V-A 스캔은 VERIFY_B 스캐너와 링크마다 1e-15 안. 도시: COM 쓰기 있음(도시 readback 46,396행/시드), 값 = baseline, 좌표 = 미터 24칸뿐, readback GREEN = native(FO .lsa 900 s 전 주기 늘림, +1 s 시계) 0 프레임 차, 쓰지 않은 SG 161 0 프레임 차, FO .lsa ≤ 900 s = B. VSL 110(명령·JSON·readback). 미터 readback = 명령(8 × 810 × 3, 어긋남 0).
- [실행] 다른 칸 넷 → 문서 값 틀림 아님: V4(d) 수 161 대 146(문서는 SC < 9000; SC 9001–9004 15 SG 차이, 작성자 `fo_run_check.py:211`), B v3c3-s41 `.err` 두 사본이 다름(`sdmpc/vissim_simulation_001.err` 에는 남은 차 줄 없음, `network/…_001.err` 에 1087: 4·1099: 296; FO 는 두 사본 같음).
- [계산] 고친 숫자 하나: §1.1 FO − NC3 ① 의 NC3 대비 % v3c3-s41 −9.58 → −9.59(반올림 전 −188.250 ÷ 1,963.750). 표시 고침 일곱 곳(§0-6·§0-7 B − FO [실행] → [계산] 등), 글 셋(§0-1 V1–V6·V9, §0-10 COM 쓰기 사실, §5.1 V4(d) 범위).
- [실행] r1 남김: FO_REPORT_r1.md 4d0fc8305be3ab749ae0b85c928d95b6b51c13241c5bd743c651d1ac367767f4, FO_REPORT_r1.json eb2fbb5b4d7bc51141656a316c2858dcd9f5cdc713517190efb22948c631db6f. r2: FO_REPORT.md 908b736e240d66d0baf03af2c8442bf8d260b1803ee11d3977fe35da96018ab3, FO_REPORT.json bd91e1f03ff367dc0ddcd3ff203900788586623c75f08ef9b11e9e351ddfbd8d (r1 과 차 = 그 % 한 칸 + r2_note). 검증 문서 VERIFY_FO.md a471fd1f10f2799fd7217a65e03bfd4061becf33eaddf6982caf0bfcd8b51b0e. 출력 sha 는 VERIFY_FO §1(check.json a6a77397…, check_r2.json f6aba5ab…, pairs.json 32cb6836…, runfiles.json cae86bf5…, extra.json 0fad6ba3…, prefix.json 147a22c8…).
- 선언 밖 가벼운 확인(핀 없음, 읽기만): `.err` 두 사본 비교, 쓰지 않은 SG 의 SC 나누기, 표시·낱말 grep, 인용 줄, 작성자 V4(d) 코드 줄.
- 지킨 것: VISSIM 0, kill 0, 재생 0. 남의 VISSIM·codex 프로세스 세기만. frozen/*·FRZ_B0·FRZ_B1·FRZ_FO·V-A·K92·GWT8·codex 작업 트리·런 폴더 쓰기 0. sealed/·봉인 시드·64cf 다른 시드·v3c3-s47 값 0. 금지 시험 0. 커밋·푸시 0. PRE_FO·COMPARE_RULE_FO·PINS_FO 그대로.
- 보고 사본: D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_fo/ 에 FO_REPORT.md·.json(r2) + r1 사본, VERIFY_FO.md, LOG.md (+ .sha256).
