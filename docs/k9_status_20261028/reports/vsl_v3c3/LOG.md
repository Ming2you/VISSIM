# vsl_v3c3 LOG — v3c3 고정 VSL 단독 런 3개 (D-K9-95) 작업 기록

- 시각은 모두 KST. 덧붙이기만 합니다(고쳐 쓰지 않음).
- 표시: [실행] 명령으로 확인 · [읽음] 파일·코드를 읽어 확인 · [추론] 시험하지 않은 판단.
- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, VS = `SP/vsl_v3c3`, RR = `D:/VISSIM_runs/20261027_vsl_v3c3`, GT = `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3`.

## 2026-10-27 10:13 KST — 시작 (선언 단계: VISSIM 0)

- 근거 결정: `SP/K9_1_J1_NOTES_20261013.md`(sha256 bbfe77b087bf41c6ec7810b145d45802cc36efbad88622a09c6737f4467a8863) D-K9-95 [실행 sha256sum].
- 할 일: PRE_VSL.md(팔 정의·준비 폴더·자리 인식 발사기·비교 규칙·도구) 쓰기, 준비 폴더 3개 만들기, 드라이런(VISSIM 없이), 모든 sha 를 이 LOG 에 고정.
- 시작 상태 [실행]: PC 전체 VISSIM 프로세스 0개(10:13:10), RR·GT 없음, `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 없음, 디스크 C 25 GB·D 223 GB 남음(df).
- 읽은 근거 sha256 [실행]: VSL_OFFLINE r2 a8ff255ecf5b20717c16b7c6bbb45e388810fa3d8bef47ef23e686a759a5d0ba, VERIFY_C_PREP c83130bb4200f417e236be9799f1bb8ece68bacd61c666b58ad9d7306a44a004, W264_READ 8db20647d3174140ab145212fa7b6a8ed3d9ad2c64356d23fbf707ded0ad5a6e, INV_PHYSICS 00d94e900a67c5edbe91079e5fce4bcbf55035327c7ded9c3a548f47358574c9.

## 2026-10-27 10:21 KST — 준비 폴더 빌더 고정, 리허설 통과

- 빌더 `VS/tools/build_vsl.py` sha256 55d3ae335b8667fcbc89def7b35028352e357a7885c3e7b2d3f857f3042f164c [실행]. 하위 명령 build·check·dryrun·launchlines. sim3 코드 6개는 읽기·import 만(python -B, .pyc 0).
- 리허설 [실행]: 환경변수 BUILD_VSL_REHEARSAL=1 로 같은 단계를 `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3_rehearsal/` 에 돌림. 첫 시도는 s31 의 "시드 파일 차이 줄" 단언이 같은 파일(차이 0줄)을 못 받아 멈춤 → 단언에 s31 예외를 더함. 첫 dryrun 은 기대 인자 글에서 '//nologo' 를 '\nologo' 로 바꾸는 잘못된 replace 로 거짓 불일치 → replace 지움. 둘째 리허설: build 3시드, check all_ok True, dryrun all_ok True(VISSIM 0, run 폴더 생성 0).
- 리허설에서 본 것 [실행]: s31·s41 VSL 망 바이트 = rule-RM 팔 망(04630354…, e4953eaf…), s43 = 94318d4d…(새 망, NC3 s43 대비 차이 줄 내용이 rule-RM s31 대 NC3 s31 과 같음). fixed_initial.csv 는 rule-RM 판과 줄바꿈만 다름(우리 CRLF, rule-RM LF; 내용 같음 diff --strip-trailing-cr) — sim3 prepare() 의 csv 기본 줄바꿈. codex 64cf VSL 팔 fixed_initial.csv 와는 바이트가 같음.
- 이 고정 sha 의 빌더로 실제 위치(RR, GT)에 build → check → dryrun → launchlines 를 돌립니다.

## 2026-10-27 10:24 KST — 실제 준비 폴더 빌드·점검·드라이런 (VISSIM 0)

- [실행] 빌더 55d3ae33… 로 build → check(all_ok True) → dryrun(all_ok True) → check 재실행(all_ok True) → launchlines. 앞뒤 PC VISSIM 0개. 디스크 C 24 GB·D 222 GB.
- 리허설 트리 `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3_rehearsal/` 는 영수증 3개만 `GT/rehearsal_receipts/` 로 옮기고 지움(내가 만든 것).
- 망 sha256: s31 046303541667838f30045a06d230fb5b31944a18db483770539dfcc873176f0d (= rule-RM s31 망) · s41 e4953eaf8c8f983f28b9a14c684075757ddd45e180e63f2235dc9db8b4ed7524 (= rule-RM s41 망) · s43 94318d4d1c235fa800da70cbcfff85e13567092a86c628e62010b9b03396549f (새, 같은 조리법).
- prepared.json sha256: s31 79eefd753a3f0717e5cad254b120bb3a38ef52ea47979e6dbc0e667d8c91a52a · s41 27ccd7ba91410153d28ca62709bbbeb68d99969f5ca4f9c1d360a53ff2a039ed · s43 36170f2d3fb1852e3002498b80d370bb5ddfe3e8f3fbcb3b30fc6360e76aed45.
- fixed_events.csv (세 시드 같음) 17abe578c75e6a873fdd782c40eead3e69fa95bc961fb3b815cfe6c41efce0ce = 16줄 "900,vsl,63–66,{10,20,30,70},91". fixed_initial.csv (세 시드 같음) 14e47ea34d13ce7166c5904db9213b1faf91a5724a9727d9fdb26564f5de4988.
- 프로필(GT/profiles) sha256: s31 c832cfdc862183e22e2ac61a140baa7daf3be3012ae009d91feebea5259a0702 · s41 7228d999913eb967bfbf8a155820a6fb5beda43afd45398761da024bf5df654e · s43 427e264affe834682e12fbdfc3df20072da8ec5f64d24e6a02cc760020f1e151.
- 영수증: build_receipt 51fb1b9e11b11cd60556514f23795dcb7ac48554272a1554787ea5f21fd969c2 · check_receipt(마지막) 119f6db6815762282db1105593735073e76ed7e75803618d6031d52ef1d7d3ab · dryrun_receipt b98b449ade13862f4658fa7c7e4eb6240908251fb7c729703f4ff2e8f30fe393 · launch_lines_vsl.txt 0456cf45944b5be5752c36434bc49135531e2004989a23dc1fdeb0ecd6a41396 (발사 안 함).
- dryrun_check.txt: s31 80f297aa0d67fc02c6e933a2a707a992c6cb5bf0f9a5f2b2a1cfc8e2ef6892ce · s41 d4bb5c705a5496969d68cc23593d7d017b1a1274b70ac3846d421cb9f5907a27 · s43 76ae2201d7901596fe5ed9eee62699c5f74d73a4e0b0a2a1d20b63d1b6e546d6. rule-RM 팔 dryrun_check.txt 와 경로 3개만 다름(s31·s41).

## 2026-10-27 10:40 KST — 발사기·분석 도구 고정 (실행 전), 데이터 전 자체 시험 준비

- 자리 인식 발사기 `VS/tools/vsl_launcher.ps1` sha256 cbc37aff191ef1cf53c247a8b2c29f4b1686e10bd4aadeef6bf34fb8bdebff4e. 드라이런 시험 `VS/tools/test_vsl_launcher.py` b1725433b566ec73f65fa62600a598f6044b2b7e8894ab2e8ffea84a80c8034f [실행 10:28]: 시나리오 9개(A 자리 4개 규칙·대기 / B 멈춤 뒤 한 번 재발사 / C 비정상 끝 → 발사 중단 / D 디스크 8 GB 미만 / E 발사기 재시작 뒤 두 번 발사 0 / F 600 s 뒷받침 kill(자기 PID 만) 뒤 재발사 / G 재발사도 멈춤 → 중단 / H STOP 파일 / I 고정 파일 sha 바뀜) 모두 PASS, WMI 0·kill 0·VISSIM 0. 결과 `VS/dryrun/test_result.json`.
- 분석 도구(실행 전 sha):
  - `vsl_vhr.py` 52086b7c095f0164dace251f5a379d26e101b197a362348cf23a4648a7b85900 — 고정 B 사본 vhr_scan_b.py(0c445bc4…)·vhr_firstseen_b.py(d5c3c126…)를 sha 확인 뒤 모듈로 불러 출력 폴더만 바꿈(식 복사 0).
  - `vsl_cell_scan.py` fa5aeafd01c99297652f8f5fce6d5f760cdbb223640b3258d2020cd03229a078 — 31셀·100 m 칸·VSL 구역 준수(새 도구). 합성 FZP 연기 시험 [실행]: 셀·구역·희망속도 칸이 손셈과 같음.
  - `vsl_firstdiff.py` a8ec13d95e0cbcdffd93aeceebb9f68fd37da853e2ad8c5762e3bf40a81bdfa7 — 두 FZP 첫 다른 데이터 행, 895.1 s 접두 sha(새 도구). 합성 FZP 연기 시험 [실행]: 900.1 s 에 심은 차이를 찾음, 같은 파일은 차이 없음.
  - `vsl_heavy.ps1` 479a7e69b09190aa840d04d5a98ab42f67672bff7342bd25d286aa4611b52492 — 공유 잠금 heavy.lock(CreateNew, 대기·재시도, 끝에 자기 토큰일 때만 지움) 아래 무거운 python 차례 실행, BELOW_NORMAL 은 WMI 시작 정보로.
  - `jobs_predata.json` b993f5c4af1641e13cbd53bb7a78fc5dec3ed07a6d8f2f6ba43ac239c9cb6344 — 데이터 전 일: NC3 s31·s41·s43 셀 스캔(분석 때 NC3 칸으로 씀) + 첫 다른 행 도구 자체 시험(rule-RM s31 대 NC3 s31; O1 기록의 첫 갈림 2,500.1 s 를 다시 내는지).
  - `vsl_metrics.py` 는 NC3 셀 스캔 sha 를 넣은 뒤 고정합니다(다음 항목).

## 2026-10-27 10:44 KST — 시각 정정, 데이터 전 자체 시험, 도구 최종 고정, PRE_VSL 고정

- 시각 정정: 바로 앞 항목 머리 "10:40 KST" 는 잘못 적은 시각입니다. 실제로는 10:33 무렵(무거운 일 WMI 발사 10:34:45 보다 앞) 적었습니다. 내용은 그대로입니다.
- 무거운 일(공유 잠금 아래, VISSIM 0) [실행]: `vsl_heavy.ps1`(479a7e69…) 를 WMI·BELOW_NORMAL 로 10:34:45 발사(RV=0 PID=14924, 기록 `VS/logs/wmi_heavy_lines.txt`). 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 10:34:46 얻음 → NC3 셀 스캔 s31·s41·s43(29.2·31.9·30.0 s, exit 0) → 첫 다른 행 시험(8.7 s, exit 0) → 10:36:26 잠금 지움, rc 0. 로그 `VS/logs/predata_20261027/heavy.log`.
  - NC3 셀 스캔 sha256: nc3_s31 6345ce9450062e6f961bb6622628491bddfe881dea1c945337ce9c2258dddb53 · nc3_s41 70ef1f26ab17b413b497281e6f051aaf23d88d2c828e198a5b093db10623038e · nc3_s43 a67a8751bcfa841c2d69e823523ea19bff39179ae384de8ae60fed3cb0e83abd. 체인 veh·h 와 6,000–8,600 m 칸 수가 fwe_scan NC3 스캔과 정확히 같음(s31·s41 확인). 구역 안 희망 89–93 몫 0.
  - 첫 다른 행 시험: rule-RM s31(VSL 팔 s31 과 같은 망 바이트) 대 NC3 s31 → 첫 다른 행 2,410.1 s(O1 행 내용 기준 값과 같음), 895.1 s 접두 387,397행 sha 같음. 출력 f90f7023554a374e764d0a8877f77c68b54af288e29e13ab6cece77e8cc3a905.
- `vsl_metrics.py` 에 NC3 셀 스캔 핀을 넣고, 런 모드에서 못 쓰는 시드는 "못 냄" 으로 두게 고침 → 최종 sha256 160c23c76d354b769718ab31044782609b96e238196b2bf1817ef053aacca71c. 자체 시험 [실행]: V6 B 칸 72/72 같음(최대 차 0), 물리·셀 대역 차 0 → `VS/selftest/vsl_metrics.json` 1055689f23876273f47e72baa0b27d9a457d7ea2febbd3c213d6e578173ebd8b. 런 모드 배관 시험(가짜 런 트리, `VSL_METRICS_TEST_ROOT`): 재발사 고르기·"못 냄" 확인 → `VS/runmode_test/out/vsl_metrics.json` e581e920b92faf2dd9a2464b33c5a80aebc31292997a5dffcfd6094bf6765161.
- 새로 고정: `vsl_analysis_jobs.py` 7d4a71cc29656832c434c33942b6f9ce018cd533c396cee44dfa951c45e969dd, `analysis_tool_pins.json` 260deb96d8d4345ccca1aa6c077216bd2b9f93495c782c5ee0fffe9fac41ff93(vsl_vhr 52086b7c…, vsl_cell_scan fa5aeafd…, vsl_firstdiff a8ec13d9…, vsl_metrics 160c23c7…), `vsl_launcher_start.ps1` d038e32c4354421b3c841110a3822d03a27c8bfce62d1e5cd528548e34c89530. 생성기 시험 출력은 `VS/selftest/jobs_analysis_TEST_predata.json`(dcf5ba1e…)으로 옮김(실제 jobs_analysis.json 은 런 뒤 새로 만듦).
- 그대로인 고정값(앞 항목): build_vsl 55d3ae33…, vsl_launcher cbc37aff…, test_vsl_launcher b1725433…, vsl_heavy 479a7e69…, jobs_predata b993f5c4…, vsl_vhr 52086b7c…, vsl_cell_scan fa5aeafd…, vsl_firstdiff a8ec13d9….
- **PRE_VSL.md 고정**: sha256 27452ae62ae84e7c1cbe4717f1c8777b3c18b5a3f5d18b7cd5da033d83a3faf1 (`VS/PRE_VSL.md.sha256`). 비교 규칙(§6)·도구(§7)·발사기(§5)·VSL 설정(§2: DSD 63–66 → 분포 91, 900–9,000 s) 은 이 sha 로 데이터 전에 고정됩니다.
- 묶음 목록 `VS/SHA256SUMS_VSL.txt`(62줄: PRE_VSL·도구·NC3 셀 스캔·자체 시험 출력·RR 준비 폴더·영수증·발사 줄·GT 프로필·리허설 영수증) sha256 cf43058d90a216b434c8177baaef358e07af70d7a6c742d9791826eadcb9b52e.
- 런: 발사 0. 발사기 시작 0. 다음 단계는 `vsl_launcher_start.ps1` 로 발사기를 띄우는 것(이 선언 작업 밖).

## 2026-10-27 10:57 KST — 런 단계 시작: 발사 전 점검 (VISSIM 0)

- [실행] PRE_VSL.md sha256 27452ae6… 다시 확인(같음). `SHA256SUMS_VSL.txt`(cf43058d…) 62줄 모두 OK(RR·GT 줄임을 실제 경로로 펴서 sha256sum -c).
- [실행] sim3 러너 4개 sha 가 발사기 고정값과 같음: fast_nc_run.ps1 269345da…, fast_nc_runner.vbs bf07acda…, fast_fixed_profile_verify.py 91441391…, validate_native_signal_record.py 4a647072….
- [실행] 발사기 드라이런 재확인: 고정 시험 `tools/test_vsl_launcher.py`(b1725433…)에서 출력 폴더 줄(8행 `D = …`) 하나만 `dryrun/recheck_20261027_1057` 로 바꾼 사본 `logs/recheck_launcher_1057/test_vsl_launcher_recheck.py`(c1b8b3fb…)로 돌림(고정 결과 `dryrun/test_result.json` 은 안 건드림). 시나리오 9개 모두 PASS, 11.5 s, WMI·kill·VISSIM 0. 발사기 sha cbc37aff… 그대로.
- [실행] 상태: RR 에 `_launcher`·run 폴더·launch.log 없음. heavy.lock 없음. PC VISSIM 0개. 디스크 C 24 GB·D 222.4 GB.
- [읽음] 같은 러너·망의 앞선 런 진행 속도: rule-RM s31·s41, R2c s31 모두 첫 진행 약 42 s, progress.csv 행 사이 최대 6.1 s, 마지막 진행 → 끝 약 40 s(`V3/s*_v3c3rm*/run/run.json`, progress.csv). 300 s(러너)·600 s(발사기 뒷받침) 문턱과 거리가 큼.
- 다음: `tools/vsl_launcher_start.ps1`(d038e32c…)로 발사기를 WMI 분리 시작.

## 2026-10-27 11:00 KST — 발사기 시작, 런 3개 발사 / 런 점검 도구 고정 (데이터 전)

- [실행] 10:57:02 `vsl_launcher_start.ps1`(d038e32c…) → WMI RV=0, 발사기 PID 20992(sha cbc37aff…, PriorityClass Normal), 그때 PC VISSIM 0, C 24 GB·D 222.4 GB. 영수증 `RR/vsl_launcher_start_receipts.log`.
- [실행] 발사기 기록(`RR/vsl_launcher.log`, `RR/wmi_launch_lines_vsl.txt`): 10:57:04 s31_run1 RV=0 PID 47896(VISSIM 앞 0) · 10:58:05 s41_run1 RV=0 PID 43392(앞 1) · 10:59:06 s43_run1 RV=0 PID 54996(앞 2). 표지 파일 `_launcher/launched_s{31,41,43}_run1.json`. 발사 줄은 `RR/launch_lines_vsl.txt` 의 줄과 같음.
- [실행] 10:59:16 상태: s31 sim 415.1 s(VISSIM PID 49048), s41 sim 205.1 s(VISSIM PID 39172), s43 시동 중. PC VISSIM 3개(모두 이 발사기 것; 다른 세션 VISSIM 0).
- 런 점검 도구(데이터 전 고정, PRE_VSL §6.2 V1·V2·V3 정의 그대로 옮김; 새 정의 없음):
  - `tools/vsl_runcheck.py` sha256 e0da7f03dc34afab1b3d8d828b2fa163c3d6de96dffb9b93496b2134be3677e8 — run.json·stdout·fixed_readback.csv·fixed_validation.json·발사기 끝 표지·firstdiff 출력만 읽음(FZP 안 엶). 출력 `VS/out/runcheck/runcheck.json`. 합성 시험 `selftest/runcheck/test_runcheck.py`(087d1cef…) PASS(정상·값 틀림·끝값 틀림·재발사 고르기·접두 다름 구분).
  - `tools/jobs_runcheck.json` sha256 583d12bef2aeadcac4827e9e35cc03942066e403cb63183cc6cfd7e8ae478477 — V3 용 vsl_firstdiff(a8ec13d9…) 3개(VSL s<S>/run 대 NC3 s<S>), 출력 `VS/out/runcheck_firstdiff`. vsl_heavy.ps1(479a7e69…)로 heavy.lock 아래 WMI·BELOW_NORMAL 실행 예정. 재발사가 생기면 그 시드 경로만 run_retry1 로 바꾼 새 판을 만들고 sha 를 따로 적음.

## 2026-10-27 11:12 KST — 오프라인 O1·O2 규칙 고정 (실행 전; o1o2 일)

- 이 항목부터 `o1o2` 는 오프라인 O1(φ·ρ_crit 민감도)·O2(VSL 켠 상태 plant 충실도) 일입니다. VISSIM 0. 런 발사기·VSL 런은 건드리지 않음.
- **PRE_O1O2.md 고정**: `VS/o1o2/PRE_O1O2.md` sha256 be6852a25b0662a3be5dbad3d72b1fb2f241aae2c1cd7ff8aca0f9f484932178 (`VS/o1o2/PRE_O1O2.md.sha256`). 상태(64cf-s29 넷 + v3c3 B 1차 셋·2차 둘), 설정 13개(φ 4 × ρ 3 + 반복), 바꾸는 키, 부호 규칙(|ΔJ| < 0.01 veh·h = 0), O2 상태(window·off T=1,800–2,550 열둘), 지표, 실행 순서·시간 모자랄 때 규칙. 데이터 전.
- [실행] 코드 사본(robocopy, `__tangentcache__` 뺌): `GT/o1o2/code64` ← `codexhandoff/vsl_off/code`(파일 7,900 / 7,900), `GT/o1o2/codeB1` ← FRZ_B1 `codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410`(7,996 / 7,996). 원본은 읽기만.
- 도구 sha 는 분석 밖 상태 시험 뒤, 분석 실행 전에 다음 항목에 적습니다.

## 2026-10-27 11:26 KST — o1o2 도구 고정 (분석 실행 전), 시험 결과

- 시험(분석 밖 상태, PRE_O1O2 §4) [실행]: 큐 `smoke`(WMI 11:13:28 RV=0 PID 51652, BELOW_NORMAL; 일마다 공유 잠금 잡고 풂, 잠금 대기 0) → v3c3-s31 B T=1,650(251 s), 64cf A1 T=1,650(265 s), 64cf window T=1,650(91 s), 모두 exit 0·예외 0·행동 파일 0. 확인: 두 망 모두 FW_E 집계 경로(lane_group_roads = [], φ 받음), seg13 키 = FW_E__seg13·seg14, plant 가 VSL 을 낮춘 셀 = 64cf 16–25 / v3c3 18–25(sign_cells[5] 18), base 와 base_repeat 의 J 가 비트까지 같음, φ 0.85·ρ×0.9 가 J 를 바꿈(설정이 질의에 닿음), 상태당 준비 57–78 s·굴림 14–16 s. 시험 출력은 `VS/o1o2/out/smoke/`(결과로 안 씀). 분석 도구 자체 시험(시험 출력 + 합성 스캔, `VS/o1o2/selftest_analyze/`): 구역 재고·Edie 흐름이 손셈과 같음.
- 입력 만들기 [실행]: 분석 상태 21개(O1 64cf 4·v3c3 5, O2 12)를 `GT/o1o2/pristine/` 에 만듦, 모두 경로 안 옮긴 것 0(`VS/o1o2/logs/build_inputs.txt`).
- 고정 도구 sha256 (`VS/o1o2/tools/SHA256SUMS_TOOLS.txt` = 8006e6b627a6a10f9b568cc759a84edbddf643b7c8b4e63d660bc4f973854133):
  - o_build_inputs.py 739b29059cfb51b18d4358d23735f42828ee3bda5ca80251b5db1df6dfb00518
  - o_probe.py 8a9e2e5e55f49185ce42c7faa73ee8694ca5b92142b7f12e1435305990e03463 (시험 전 한 번 고침: plant 걸음 끝 = 다음 걸음 시작, 마지막 = T+450 — 훅에서 t_after == t 라서; VSL_OFFLINE v3_analyze c973fe58 와 같은 규칙. 시험은 고친 판으로 돌림)
  - o_run_probe.ps1 459c3f9e356f22e93b967a22decf044c3f1a2f57ebf0b19949ca45efdb1ea996 · o_heavy.ps1 bf37dcfc6854302fb998eff1d720d36f5e8927f7f3e2065c0da96055c2c111c1 · o_launch.ps1 3e4e803a9624aec38d17b96a35e39db89dec38243733c88b5ef5b1822e4f0bc1
  - o2_fzp_cells.py cff42e34d518bb5d1864fcd5d9c503b329037007f73947564088362c3a412013 · o_analyze.py bc9ac1ef32ee81de7ba6e4faa30a0657cbf64a2e0b8e5c284d5f21d828a5a518
  - spec_o1 266ecc5d… · spec_o2_win b3fa47fa… · spec_o2_off 9c1c3940… · jobs_main beed3e29bbaee82c5f4b3ac7765f65503af599a735de542c422ed66fd2b2c7b1 (26 일, PRE §3 순서)
- 코드 사본 점검 [실행]: code64·codeB1 의 sdmpc.py 5c1ba251…, adapter a615d8ca…, area_freeway_accounting cd182276… (둘 같음, VSL_OFFLINE 기록과 같음). B 튜닝 729640af….
- 다음: `jobs_main.json` 을 WMI 로 띄움.

## 2026-10-27 11:27 KST — o1o2 큐 발사, 표 그리는 도구 고정

- 시각 정정: 바로 앞 항목 머리 "11:26" 은 잘못 적은 시각입니다. 그 항목은 11:24:36 에 썼고(파일 시각), 큐 발사(아래)보다 앞입니다. 내용은 그대로입니다.
- [실행] 큐 `main` WMI 발사 11:24:42 RV=0 PID 41288 BELOW_NORMAL (`VS/o1o2/logs/wmi_launch_lines.txt`), jobs_main beed3e29…, o_heavy bf37dcfc…. 일마다 공유 잠금.
- 표 그리는 도구 `o_tables_md.py` sha256 b3432186ea11e98ea955b9d785eea58f1787a7badab17ae2c1b20873cfbb6e2b — o1o2_tables.json 의 숫자를 표로만 옮김(새 숫자 0). 자체 시험 = selftest_analyze 출력.

## 2026-10-27 11:28 KST — 진행 확인

- [실행] 세 런 모두 stdout 에 `SIM_SEC=900`(이벤트 쓰기 단계 통과, VBS 의 Die 없음) 뒤 계속 진행. 11:27:26 sim 시각 s31 2,715.1 / s41 2,620.1 / s43 2,540.1 s, progress.csv 나이 0–3 s. 걸음 약 1.26 sim s/벽 s [계산].
- [실행] PC VISSIM 4개: 우리 3개(49048·39172·55456, 10:57–10:59 생성) + 다른 세션 1개(PID 32060, 11:25:15 생성). 다른 세션 것은 세기만 하고 건드리지 않음. 우리 발사기는 더 띄울 런이 없음.
- 디스크 C 24 GB·D 218 GB.

## 2026-10-27 12:41 KST — o1o2 진행: VSL 런 셋 끝난 뒤 VSL·NC3 프레임 스캔 큐

- [실행] o1o2 큐 `main`: 11:24:42 시작, 12:41 까지 FZP 스캔 5개(window·off·B s31·s41·s43, 각 22–25 s)와 O1 상태 5개(A1 1,800·3,600, joint 1,800·4,500, v3c3-s31 B 1,800; 각 653–699 s) exit 0. 실패 0. 잠금은 일마다 잡고 풂.
- [실행] VSL 런 발사기 기록 `RR/vsl_launcher.log`: RUN_END s31 12:38:04 · s41 12:40:05 · s43 12:40:05 모두 status=done, 12:40:05 EXIT. PC VISSIM 0 (12:40). FZP 셋 1.15–1.18 GB.
- [실행] PRE_O1O2 §3 (7) 대로 큐 `vslscan`(jobs_vslscan.json sha256 66d29dc8f97d4e2f70fcc7b510e351c7e44b3712fbbfd4ebabd1734869855207; o2_fzp_cells cff42e34… 로 VSL s31·s41·s43 와 NC3 s31·s41·s43, 1,500–4,200 s) WMI 12:40:37 RV=0 PID 52980 BELOW_NORMAL. 같은 공유 잠금으로 main 큐와 일 단위로 번갈아 돎. VSL 런 폴더는 읽기만.

## 2026-10-27 12:42 KST — 세 런 완료, V1·V2 통과

- [실행] 발사기 기록: 12:38:04 RUN_END s31_run1 done · 12:40:05 s41_run1 done · 12:40:05 s43_run1 done · 12:40:05 EXIT(stopped=False). 멈춤·뒷받침 kill·재발사 0(`_launcher` 에 backstop_kill·LAUNCH_STOPPED·run2 표지 없음). 발사기는 스스로 끝남. 이 세션의 kill 0.
- [실행] 벽시계: s31 10:57:05→12:37:33(100.5분) · s41 10:58:06→12:39:39(101.6분) · s43 10:59:07→12:39:43(100.6분). run 폴더 각 1.2 GB. 12:40 PC VISSIM 0.
- [실행] `tools/vsl_runcheck.py`(e0da7f03…) → `out/runcheck/runcheck.json`: 세 시드 모두 V1 참(completed true·exit 0·검증 exit 0·fixed_validation passed·SIM_DONE·SIM_SEC=9000), V2 참(쓰기 16줄 = 900 s·vsl·DSD 63–66 × 10/20/30/70·91/91·ok 1, 미터 쓰기 0, 0 s 읽기 110, 9,000 s 읽기 91). fixed_validation: event_readbacks 16, snapshot 864, 쓰지 않은 DSD·SG 스냅샷 sha 앞뒤 같음 93d33a9c…(세 시드 같음), LDP 450,000행. fixed_readback.csv 세 시드 바이트 같음 8185c883….
- [실행] 핀 재확인: SHA256SUMS_VSL 62줄 모두 OK(준비 폴더 고정 파일 안 바뀜). run.json sha256 s31 36a01b22… · s41 66de3c89… · s43 fe668539….
- [실행] .err: 메시지 종류가 NC3 와 같음(차로변경 대기 제거, 다음 링크 못 찾음, 여행시간 구간, 입력 미완료, VISSIG DLL 경고). network 폴더 `VISSIG_Controller.dll.err` = "SC 9101–9108 신호 프로그램 없음"(미터 native OFF), NC3 와 같은 글.
- V3(895.1 s 접두)는 `jobs_runcheck.json`(583d12be…) 을 vsl_heavy 로 WMI·BELOW_NORMAL 발사(12:40:24, PID 47724). heavy.lock 은 다른 작업(`owner=vsl_v3c3_o1o2 …`, 12:33:58 잡음)이 잡고 있어 30 s 마다 기다리는 중.

## 2026-10-27 12:45 KST — o1o2 큐 공정성 고침 (결과에 닿지 않는 큐 방식만), 남은 일 다시 띄움

- 까닭 [읽음 `SP/c_port/c1/LOG.md` 12:34 항목]: C1 워크플로가 공유 잠금을 기다리는데, 내 큐(o_heavy bf37dcfc…)는 일을 마치고 잠금을 풀자마자 다음 일로 곧바로 다시 잡아 C1(확인 간격 2–60 s)이 틈을 못 얻음. 남의 프로세스·잠금은 건드리지 않음.
- 고침: `o_heavy2.ps1` sha256 478fe7aa6f1d0fc422785cd951387fb555a295cdbf2aed9265dc9fdad7248128 = o_heavy 에 "잠금 푼 뒤 20 s 쉼" 한 줄만 더함(diff 로 확인). `o_launch2.ps1` 9a6757404087983d9be49f040bf7f30ab808b812341eaaed43107a6f3ce5e80f(o_heavy2 를 부름). 남은 일 `jobs_main_rest.json` c11ce2f747c075acab2c0503b01761a841e6e8756b44fe8e0ce0a66f4da1c55d = jobs_main 의 O2 12개 + O1 2차 2개, 순서 그대로(PRE §3). 탐침·스펙·입력·분석 도구는 바꾸지 않음.
- 방법: `VS/o1o2/STOP_O` 를 만들어 main 큐가 지금 일(o1_b43_T001800) 뒤에 멈추게 하고, 멈춘 것을 본 즉시 STOP_O 를 지운 뒤 main_rest 를 o_launch2 로 띄움.

## 2026-10-27 13:20 KST — V3 통과, VSL_RUNS.md 작성

- [실행] vsl_heavy(479a7e69…, jobs_runcheck 583d12be…): heavy.lock 을 다른 작업(o1o2 → C1)이 잡고 있어 30 s 마다 75번 기다림 → 13:17:56 잠금 얻음 → firstdiff s31·s41·s43(2.4·2.7·2.5 s, exit 0) → 13:18:03 우리 토큰 확인 뒤 잠금 지움, rc 0. 기록 `logs/runcheck_20261027/heavy.log`.
- [실행] V3: 세 시드 모두 ≤ 895.1 s FZP 행 수·sha256 이 NC3 와 같음(s31 387,397행 734a2d88… = 데이터 전 자체 시험 값 · s41 398,331행 b61cdb73… · s43 393,558행 86c06c73…). 모든 행이 같은 마지막 프레임 900.1 s, 첫 다른 행 905.1 s. 첫 다른 행은 세 시드 모두 링크 2 표지(3,998.67 m) 바로 뒤 차(4,007.7–4,033.5 m)의 희망속도 90.0–91.7(VSL) 대 99.3–126.8(NC3) km/h. 출력 `out/runcheck_firstdiff/firstdiff_s{31,41,43}.json`(e13e9600… · 5100ee6d… · 94417e24…).
- [실행] `tools/vsl_runcheck.py` 를 firstdiff 폴더와 다시 돌림 → `out/runcheck/runcheck.json` 2ec689c97cbed588a1db8923dd724d41b794c2fe477c21bfbd6398da5aa0dc1f: 세 시드 V1·V2·V3 모두 참.
- [실행] 망 .err(200 B)·readback.csv 가 같은 시드 NC3 와 같은 글·값(RandSeed·SimRes·FZP 설정).
- `VSL_RUNS.md` 를 쓰고 `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_v3c3/` 에 사본(다음 항목에 sha).

## 2026-10-27 13:22 KST — 런 단계 끝

- `VSL_RUNS.md` sha256 b967b675f99af7866750258415a8709dcea9e818f87f55e8d8083d34ec0dc62d (`VSL_RUNS.md.sha256`). 사본 `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_v3c3/VSL_RUNS.md`(같은 sha) + .sha256.
- 상태 [실행]: 발사기 끝남, 우리 VISSIM·cscript 0, 우리 heavy 잠금 없음. kill 0. 세 시드 1차 런(run) 이 분석 대상. 다음 = PRE_VSL §7.3 분석(이 단계 밖).

## 2026-10-27 14:30 KST — o1o2 끝: O1 9상태·O2 12상태·FZP 스캔 11개, VSL_O1_O2.md

- [실행] 큐 main(11:24:42–12:45:44, 일 13개 + o2_win_T001800), main_rest(o_heavy2, 12:45:52–14:24:39, 남은 일 14개, 첫 일은 출력 있어 건너뜀), vslscan(12:40:37–13:20:26, 6개). 실패 0, 재실행 0, kill 0. C1 워크플로가 잠금을 쓰는 동안 기다림(남의 잠금·프로세스 건드림 0). 14:25 내 프로세스 0, 잠금 빔. 디스크 C 21 GB·D 206 GB.
- [실행] O1: 상태 9개(64cf 4 + v3c3 B 1차 3 + 2차 2) × 설정 13 × VSL 3 모두 오류 0, base = base_repeat 비트 같음, 64cf 넷의 base J 가 VSL_OFFLINE V3 와 같음. O2: window·off 각 6상태 오류 0. FZP 프레임 스캔: window·off·B s31·s41·s43·VSL s31·s41·s43·NC3 s31·s41·s43.
- 분석: o_analyze(bc9ac1ef…) → out/o1o2_tables.json 9d4b5a55…, o_tables_md(b3432186…) → out/o1o2_tables.md 3828a3be…. 출력 묶음 OO/SHA256SUMS_O1O2_OUT.txt 43eb6201….
- 보고서 `VS/VSL_O1_O2.md` sha256 054e85ba048799937cd5c0c80e52529f99332712fe147c04a915dd1d59c44968 (r1). 규칙(PRE_O1O2 be6852a2…)·탐침·분석 도구는 데이터 뒤 바꾸지 않음.

## 2026-10-27 14:31 KST — 분석 단계 시작: 핀 확인, 작업 목록 생성 (PRE_VSL §7.3)

- [실행] 핀 확인: PRE_VSL.md 27452ae6… (= `PRE_VSL.md.sha256`), SHA256SUMS_VSL.txt cf43058d… 62줄 모두 OK(RR·GT 줄임을 실제 경로로 펴서 sha256sum -c), VSL_RUNS.md b967b675…. 분석 도구 4개 = `analysis_tool_pins.json`(260deb96…) 값(vsl_vhr 52086b7c · vsl_cell_scan fa5aeafd · vsl_firstdiff a8ec13d9 · vsl_metrics 160c23c7), vsl_analysis_jobs 7d4a71cc…, vsl_heavy 479a7e69…, fwe_scan 0619e9fc…. 런 뒤 도구 고침 0.
- [실행] 결정 노트 `SP/K9_1_J1_NOTES_20261013.md` 의 지금 sha256 은 cb84bf22… 로, 시작 때 적은 bbfe77b0… 와 다릅니다(다른 작업이 덧붙인 것으로 보임 [추론]). 이 분석은 그 파일을 입력으로 쓰지 않습니다.
- [실행] 발사기 표지: `_launcher/end_s{31,41,43}_run1.json` 만 있고 run2 없음 → 세 시드 모두 1차 `run` 을 씀.
- [실행] `python -B tools/vsl_analysis_jobs.py` → `tools/jobs_analysis.json` sha256 2f29e762bc94d4a3b25b22c18e8d6328c2df5c7055f2b4ffb051d81d1d46cb1d (일 11개: vhr 1 · 시드마다 phys·cell·firstdiff · metrics 1, missing_fzp 없음).
- 상태: heavy.lock 없음(14:28), 다른 세션 VISSIM 1개·python 3개(남의 것, 건드리지 않음). 디스크 C 20 GB·D 205 GB.

## 2026-10-27 14:38 KST — 분석 실행 끝 (PRE_VSL §7.3), V6 참

- 시각 정정: 바로 앞 항목 머리 "14:31" 은 잘못 적은 시각입니다. 실제로는 14:28 무렵(WMI 발사 14:28:53 보다 앞) 적었습니다. 내용은 그대로입니다.
- [실행] `vsl_heavy.ps1`(479a7e69…) -Jobs `jobs_analysis.json`(2f29e762…) 을 WMI·BELOW_NORMAL 로 14:28:53 발사(RV=0 PID 39980, `logs/wmi_heavy_lines.txt`). 14:28:54 공유 잠금 얻음(대기 0) → vhr(158.8 s) → 시드마다 phys(44–46 s)·cell(33–35 s)·firstdiff(2.7 s) → metrics(2.4 s), 일 11개 모두 exit 0 → 14:35:40 우리 토큰 확인 뒤 잠금 지움, rc 0. 기록 `logs/analysis_vsl/heavy.log`. kill 0, VISSIM 0.
- [실행] V 점검(`out/vsl_metrics.json`): 세 시드 1차 런, receipts ok 참, V3 접두 같음(첫 다른 행 905.1 s, vhr `lf_sha_le_895_1` 도 같음), 세 스캔(vhr·phys·cell)이 같은 FZP sha 를 읽음(s31 63a827fe… · s41 ea91826e… · s43 5492358d…). **V6 B 칸 재현 72/72 같음(최대 차 0)** → 숫자를 냄.
- 출력 sha256 [실행]: `out/vsl_metrics.json` b1eea2f19257ff0a24d7e819ba5de9e1cd3e11fecf7223a45230ec3579d7ecf2 · `out/vsl_tables.md` 50c754c13c8796c1390bbf84125a813b3fbc6b0b323a5fd7fe48a0270f55bf16 · vhr vsl_s31/41/43 64112bf3…/6fb9e514…/b0cf5b9f… · first_vsl_s31/41/43 0335b111…/e8d956c9…/bd764866… · phys 3169172b…/c9fd195a…/61526d64… · cell 1281f05c…/4e6a8161…/3b760d04… · firstdiff 41d5653a…/5100ee6d…/06f7886f…(runcheck 판과 elapsed_s 만 다름).
- 데이터 뒤 만든 것(표 옮기기만, 새 식 0): `tools/vsl_report_tables.py` sha256 c228749531b6abbb1aa4bb85ff501be596ea2b3928fda25dd7e03a16ae9dff3e — vsl_metrics.json 에 이미 있는 값(구역 veh·h·속도 수준값, 단면·합류 흐름, 램프 대기, 차로별 속도, 번짐 분·꼬리, 셀 창별 Δ, 준수 칸 몫)만 표로 옮김. 시험: selftest JSON 사본으로 돌려 봄(`selftest/report_tables_test/`). 출력 `out/report_tables.md` 69d65993dc5cf87d3b6fa9192d492801e9b899b630f1fe09daa9ea84b002a400.
- 사후(계획 밖) 한 번: 고정 스캔 출력(phys)만 읽는 즉석 python 으로 3,800–8,000 m 차로별 칸에서 "한 차로 < 15 km/h, 같은 칸 다른 차로 > 60 km/h" 인 분을 셈. NC3 s41 은 차로 2 의 3,500–4,500 m 에서 56분(5,880–8,160 s), VSL s41 은 8분. 보고서에 "사후" 로만 적음.

## 2026-10-27 14:41 KST — 정정: 사후 차로 정지 분 수

- 바로 앞 항목의 "NC3 s41 56분, VSL s41 8분" 은 칸별 분 수를 더한 값이라 같은 분을 두 번 셌습니다. 분의 합집합으로 다시 셈 [실행, 사후]: 3,800–4,500 m(차로 칸 자료는 3,800 m 부터) NC3 s41 36분(5,880–8,220 s) · VSL s41 8분(5,820–6,360 s) · NC3 s43 8분 · VSL s43 0 · s31 둘 다 0. 4,500–5,000 m: s31 VSL 14 / NC3 7 · s41 11 / 8 · s43 16 / 17 분. 보고서는 이 값을 씁니다.

## 2026-10-27 14:55 KST — VSL_REPORT.md 작성, 분석 단계 끝

- `VS/VSL_REPORT.md` sha256 01bf8a3122f2b6d6080cfedfc2789eca297e87e4b2c76202ea81289aa8d235cf (`VSL_REPORT.md.sha256`). 사본 `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_v3c3/VSL_REPORT.md`(같은 sha, sha256sum -c OK) + .sha256.
- 표는 고정 도구 출력의 줄을 그대로 끼움: `work_report/fill_report.py` 202e6876…(새 숫자 0), 틀 `work_report/VSL_REPORT.template.md` 4df4bf13…. 본문 숫자는 표 값과 한 줄씩 대조함 [실행].
- 결과 요약(주 꼴 [0, 9000] s, VSL − NC3, s31 / s41 / s43, 시드 3): Ω701 +70.3 / −162.0 / −50.5 · ④ +10.6 / +68.6 / −109.9 · Ω 밖 (a) −59.8 / +230.6 / −59.4 · ④b 첫 관측 −75.7 / +213.2 / −54.9. codex 꼴 같은 부호. 64cf-s29 숫자는 보고서 §7 에 따로.
- 상태 [실행]: 우리 heavy 프로세스 0, heavy.lock 우리 것 없음, VISSIM 실행 0, kill 0. 디스크 C 20 GB·D 206 GB.

## 2026-10-27 14:59 KST — 종합 VSL_RESULTS.md 작성 (VISSIM 0, 무거운 python 0)

- [실행] 읽은 입력 sha 확인: PRE_VSL 27452ae6… · VSL_RUNS b967b675… · VSL_REPORT 01bf8a31… · VSL_O1_O2 054e85ba… · vsl_metrics.json b1eea2f1… · o1o2_tables.json 9d4b5a55… · VSL_OFFLINE r2 a8ff255e…. 모두 앞 항목 값과 같음.
- [실행] 앞 문서 밖 읽기(쓰기 0): V-A 런 action CSV 3개(`D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s<S>/`, a579f913… · e1765496… · 02fdf0e7…) 에서 110 미만 VSL 쓰기 = 9·10·14 결정 × DSD 59–66 여덟 곳 = 101. VSL 팔 inpx(04630354…):4622 DSD 59 @ 링크 2 2,652.03 m. GWT8 config_n31_v2.json(c8e3ee2c…):8058-8077 `vsl_zone_heads`·`vsl_zone_free` 읽기만. VA_REPORT b57022e6…, C1_DESIGN_DRAFT c32e1006…, B_RESULTS r2 152a2f6f…, TAKEOVER_PLAN b75ad041…, R_MECH 91·231 줄.
- [실행] 결정 노트 `SP/K9_1_J1_NOTES_20261013.md` 지금 sha 4429c003… (작업 지시 bbfe77b0…, 14:28 cb84bf22… 와 다름). 300–335 줄만 읽음.
- 산출: `VS/VSL_RESULTS.md` sha256 3753ccab2fa7c3f7596ccc2e6e95db65a619e508d14e4d879343af0a35b3ae3e (`VSL_RESULTS.md.sha256`). 새 분석 도구 실행 0, 산술은 백분율·체인 덧셈뿐. 판정 낱말 없음, Ω 줄은 ④·Ω 밖과 같은 표.
- 시각 메모: 바로 앞 항목 머리 "14:55" 는 LOG.md 파일 시각 14:45·VSL_REPORT.md 14:44 보다 뒤입니다 [실행 ls]. 그 항목은 14:45 무렵 적힌 것으로 봅니다 [추론]. 고쳐 쓰지 않고 여기 적습니다.
- 상태 [실행]: 디스크 C 19.9 GB·D 204.9 GB. VISSIM·kill·잠금 0. 런 폴더·GWT8·sim3·frozen·Y: 쓰기 0. sealed/ 0.
## 2026-10-27 15:03 KST — 검증(VERIFY_VSL) 시작: 새 스크립트로 다시 셈 (VISSIM 0)

- 할 일: VSL_RESULTS.md(3753ccab…)·보고서를 새 스크립트(저자 도구 재사용 0)로 다시 봄. Ω701·④(④b 첫 관측 차분)·① 를 VSL − NC3 두 짝(v3c3-s41·s43)에서 다시 셈, VSL 준수·NC3 대비 차이가 VSL 이벤트뿐인지 런 파일에서 확인, O1 부호 바뀜 한 건(v3c3-s43 B T=1,800 φ 0.90) 다시 봄.
- 작업 폴더 `VS/verify/`(스크립트·출력). 무거운 python 은 공유 잠금 heavy.lock 아래, WMI·BELOW_NORMAL·PYTHONHASHSEED=0·python -B. 런 폴더·GWT8·sim3·frozen·Y: 읽기만. 시작 상태 [실행]: heavy.lock 없음, 다른 세션 VISSIM 1개(PID 30964)·python 3개(남의 것, 건드리지 않음), 디스크 C 19.9 GB·D 204.9 GB.

## 2026-10-27 15:14 KST — 검증: 새 스크립트 고정·정적 점검 결과, FZP 일 발사

- 새 스크립트 sha256 (VS/verify, 저자 도구 import·복사 0): v_static.py 00a5d9cb… · v_scan.py b508693a… · v_prefix.py 4603ea98… · v_compare.py 646b515c… · v_heavy.ps1 c013b788… · jobs_fzp.json c7d3fce1…. 시험: 60 MB FZP 머리(s43 VSL·NC3)로 배관만 봄(결과로 안 씀).
- [실행] v_static(가벼움, 잠금 없이): 세 시드 모두 VSL 망 = NC3 망 + 기록 전용 차이(평가 켬 8줄 + 검지 측정·검지점 각 58개), 자산 43개 sha 같음, `<simulation>` 줄 같음, DSD 63–66 정의 같음(110), 분포 91 = (90,0)–(92,1). fixed_readback: 쓰기 16줄(900 s·vsl·63–66·91, ok), 신호 contr_by_com 모두 False, 처음 대비 끝 VSL 값이 바뀐 것은 63–66 × 4차종 16개뿐. 출력 `VS/verify/out/static.json`.
- 다음: v_heavy.ps1 로 공유 잠금 아래 FZP 스캔 6개(VSL·NC3 × s31·s41·s43) + 접두 비교 3개 + 짝 비교 3개. 짝 두 개(s41·s43)가 과제 범위이고 s31 은 싸서 함께 셈.

## 2026-10-27 15:18 KST — 검증: FZP 다시 셈 끝, 도착열 가정 점검, O1 재실행 준비

- 시각 정정: 바로 앞 항목 머리 "15:14" 는 잘못 적은 시각입니다. 실제로는 15:08 무렵(WMI 발사 15:09:13 보다 앞) 적었습니다. 내용은 그대로입니다.
- [실행] v_heavy.ps1(c013b788…) WMI·BELOW_NORMAL 15:09:13 RV=0 PID 25364. 공유 잠금 15:09:14 얻음(대기 0) → 스캔 6개(27 s 안팎)·접두 3개·비교 3개 모두 exit 0 → 15:12:13 우리 토큰 확인 뒤 잠금 지움. 기록 `VS/verify/logs/heavy.log`. 과제 범위 두 짝(s41·s43)에 더해 s31 도 셈.
- [실행] 결과(새 스크립트): T1 주 꼴·codex 꼴의 Ω701·Ω635·④a·④b·④·Ω 밖·①·②·입력별 ④b 가 세 시드 모두 보고서 표와 소수 첫째까지 같음. 접두 ≤895.1 s 행 수·sha 같음, 첫 다른 행 905.1 s(표지 뒤 차의 희망속도). 905.1 s 에 다른 행은 표지 앞 50 m ~ 하류 링크 119 안에만 있음. 준수 몫 0.907/0.903/0.902, 구역 속도·B2 속도·체류 차 보고서와 같음.
- [실행] 도착열 가정 점검(가벼움, 스캔 출력만 읽음; v_arrival*.py 6339bde4·a22929e2·c3f7bcb2·29ed4c08): 입력 1098·1099·도시의 (희망속도, 길이) 다중집합이 두 런에서 기간마다 96–100 % 겹침. 1098 누적 첫 관측 차 D(t) 가 세 시드 모두 8,100·9,000 s 에 정확히 0. → 같은 차들이 같은 때 도착하고, 다른 것은 삽입 지연으로 읽음 [추론].
- 다음: O1 재실행(v3c3-s43 B T=1,800, φ 1.0·0.95·0.90·0.85·1.0 다시 × VSL 110·90). 새 탐침 v_o1probe.py 8007d72f…(저자 o_probe 재사용 0; 실제 sdmpc.solve 를 그대로 돌리다 질의·운영 seed 를 가로채는 다른 경로), 실행기 v_o1run.ps1 209d11f8…(공유 잠금, 코드·입력은 `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3/verify_o1/` 로 복사해 씀).

## 2026-10-27 15:27 KST — 검증: O1 재실행 끝

- [실행] 첫 시도(WMI 15:18:12, PID 30016): 실제 solve 의 load_prices 가 "prior price/application context mismatch" 로 멈춤(입력 사본을 다른 폴더로 옮겨 .applied 의 CSV 경로가 안 맞음). exit 1, 잠금 15:19:32 지움. 저자 폴더 쓰기 0(15:00 뒤 바뀐 파일 없음 확인).
- 고침: v_reloc.py df9b8da3…(우리 사본의 state·provenance·.applied 안 경로만 우리 폴더로 옮김), v_o1run.ps1 ed3b849a…(그 단계 추가). 탐침 v_o1probe.py 8007d72f… 는 그대로.
- [실행] 둘째 시도(WMI 15:21:24, PID 14648): 잠금 15:21:24 얻음(대기 0) → 실제 solve 가 sdmpc_pfo.solve 직전까지 돌고 가로챔(준비 51.8 s) → φ 1.0·0.95·0.90·0.85·1.0 × VSL 110·90 → exit 0, 196 s → 15:24:41 잠금 지움. 행동 파일 0. 코드 sha(sdmpc 5c1ba251·adapter a615d8ca·AFA cd182276·튜닝 729640af) 가 LOG 값과 같음.
- 결과: J 열 개 모두 저자 O1 기록(o1_b43_T001800.json 33fdd13f…)과 비트까지 같음. ΔJ(90) base +1.0983 · φ0.95 +0.9465 · φ0.90 −0.3537 · φ0.85 +0.4028 · base 다시 +1.0983. plant 가 90 을 쓴 셀 18–25(저자 기록과 같음). 출력 `VS/verify/out/o1_recheck_b43_T001800.json`.
- 상태: 우리 잠금 없음, 우리 python 0, VISSIM 실행 0, kill 0. 사본 폴더 `D:/VISSIM-merge/k8_gate_trees/vsl_v3c3/verify_o1/`(코드 474 MB + 입력) 은 남김.

## 2026-10-27 15:28 KST — 검증 끝: VERIFY_VSL.md

- 시각 정정: 바로 앞 항목 머리 "15:27" 은 잘못 적은 시각입니다. 실제로는 15:25 무렵 적었습니다. 내용은 그대로입니다.
- 산출: `VS/VERIFY_VSL.md` sha256 cef46ba8fa55b6be7138f70a3d71d36b9d0723c1a0b147c4ed09652988d63172 (`VERIFY_VSL.md.sha256`).
- 요약 [실행]: T1 72칸(12줄 × 꼴 2 × 시드 3)이 보고서와 같음. NC3 대비 차이는 기록 전용 망 줄과 900 s VSL 16줄뿐. 준수·B2 자유류 값 같음. ④b 가정 시험에서 같은 차·같은 도착 시각으로 읽힘. O1 φ 0.90 부호 바뀜은 실제 solve 경로로 다시 돌려 J 비트까지 같음. 작은 흠 둘(RS:136 J_110 범위가 T=1,800 상태만, "16곳" 은 DSD 4 × 차종 4). 반박된 핵심 주장 없음.
- 상태 [실행]: 공유 잠금 없음, 우리 python·VISSIM 0, kill 0. 디스크 C 20 GB·D 204 GB. 런 폴더·GWT8·sim3·frozen·Y: 쓰기 0. sealed/ 0.

## 2026-10-27 15:32 KST — 마무리(Finalize) 시작: VERIFY_VSL 정정 반영 (VISSIM 0)

- 할 일: VERIFY_VSL.md(cef46ba8…)가 적은 정정을 VSL_RESULTS.md 에 넣고 r2 로 냄. 정정 둘 = (가) RS:136 "φ < 1 이면 J_110 v3c3 +1.1 ~ +6.6" 은 T=1,800 세 상태 범위(다섯 상태면 +1.1 ~ +13.9), (나) "16곳 = 91"(RS:12,47-49) 은 DSD 4곳 × 차종 4 = 쓰기 16줄. 더해 검증의 단서(링크 2 표지 뒤 2.2 % 89–93 밖, O1 −0.354 와 작업자 경로 차 0.294 의 같은 자릿수, ④b 가정 시험, 다시 보지 않은 것)를 적음. 같은 범위 문장의 출처 VSL_O1_O2.md:71 에도 범위를 밝힘(r2).
- r1 사본: VSL_RESULTS_r1.md(= 3753ccab…), VSL_O1_O2_r1.md(= 054e85ba…). 끝나면 최종본을 `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_v3c3/` 로 복사.
- 시작 상태 [실행]: 디스크 C 19.3 GB·D 203.9 GB. 무거운 python 0(정정 확인은 o1o2_tables.json 9d4b5a55… 을 읽는 가벼운 python 한 번).

## 2026-10-27 15:36 KST — 마무리 끝: VSL_RESULTS r2·VSL_O1_O2 r2, 최종본 D: 사본

- 정정 반영 [실행]: VSL_RESULTS.md r2 sha256 9bbf83a3c320dd0f46c7f6ad40621b66b966ce7e40e8c587a695a22f105da86f (r1 사본 VSL_RESULTS_r1.md = 3753ccab…). (가) φ < 1 J_110 범위: o1o2_tables.json(9d4b5a55…)을 가벼운 python 으로 다시 읽어 64cf 네 상태 +6.9 ~ +14.4, v3c3 T=1,800 세 상태 +1.1 ~ +6.6, T=3,600 두 상태 +6.5 ~ +13.9 확인 → RS 를 "v3c3 다섯 상태 +1.1 ~ +13.9" 로 고침. (나) "16곳 = 91" → "DSD 4곳 × 차종 4 = 쓰기 16줄 = 91". 단서 더함: 링크 2 표지 뒤 2.2 % 89–93 밖(compare_s41.json /vsl_zone 확인), O1 −0.354 와 작업자 경로 차 0.294 같은 자릿수, ④b 가정 시험, VF 가 다시 세지 않은 줄(§4.3). 권장안(§3) 바뀜 0, 숫자 결론 바뀜 0.
- VSL_O1_O2.md r2 sha256 d64a06c983e68be7b70efb6686f540bf1fc28d685df7228d0e2ee9d94d91cab1 (r1 사본 VSL_O1_O2_r1.md = 054e85ba…): 71·213 줄에 범위·단서만 더함, 본문 줄 번호 그대로.
- 고치지 않은 것: VERIFY_VSL.md(cef46ba8…, 검증 기록 그대로), VSL_REPORT.md·VSL_RUNS.md·PRE_VSL.md(바뀜 0; RU:18 은 곱을 이미 밝힘).
- 최종본 사본: D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_v3c3/ 에 PRE_VSL·PRE_O1O2·VSL_RUNS·VSL_REPORT·VSL_O1_O2(r2·r1)·VSL_RESULTS(r2·r1)·VERIFY_VSL + .sha256 + SHA256SUMS_FINAL.txt(1689df79e43eebe417be89144e985330cf8c9d4bf4b656ea8f7b21ca2fa1ef9e). 대상 폴더에서 sha256sum -c 모두 OK.
- 상태 [실행]: VISSIM 0, kill 0, 무거운 python 0, 공유 잠금 잡지 않음. 런 폴더·GWT8·sim3·frozen·Y: 쓰기 0(reports 폴더 사본만). sealed/ 0. 디스크 C 20 GB·D 204 GB(8 GB 문턱 위). heavy.lock 없음.
