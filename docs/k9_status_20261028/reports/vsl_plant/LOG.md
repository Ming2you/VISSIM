# vsl_plant LOG (우리 plant VSL 탐침 A·B + P1 편향 추적)

- 이 파일은 날짜·시각(KST)을 붙여 끝에만 덧붙입니다. 고치지 않습니다.
- 줄임: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, VP = `SP/vsl_plant`, GT = `D:/VISSIM-merge/k8_gate_trees/vsl_plant`.

## 2026-10-27 16:03 KST — Declare 단계 시작

- 근거: D-K9-101~103 (`SP/K9_1_J1_NOTES_20261013.md`, sha256 b33fe5e7…, 337–344 줄). 작업: PRE_VP.md 쓰기와 도구 고정(데이터 전).
- 읽은 것(읽기만): VSL_RESULTS r2 (9bbf83a3…), PRE_O1O2 (be6852a2…), o1o2 도구, V-A 런 기록(결정 JSON 1개 구조, 행동 CSV 의 vsl 행, provenance), FRZ_K92 코드(sdmpc.py, sdmpc_tangent*.py, physical_lane_groups.py, lane_freeway_runtime.py, freeway_fd.py, 어댑터 세그먼트 훅), SA 훅 하네스(읽기만), C1 탐침 도구(읽기만).
- 폴더 만듦: VP/{tools, tools/vp_hooks, logs, decl, selftest, smoke}, GT.
- VISSIM·COM·러너·동결 0. GWT8 손대지 않음.

## 2026-10-27 16:30 KST — 상태 목록·FZP 원천 고정, 코드 사본, 배관 시험(smoke v1)

- [실행] `tools/vp_states.py` → `decl/VP_STATES.json`: 탐침 A·B 12상태(시드마다 A1 = 첫 101 − 150 s, A2 = 첫 101, A3 = 101 결정의 아래 중앙값, A4 = 마지막 101 + 150 s), P1 9상태(T0 1,800·5,400·7,200, 세 결정 모두 FW_E 110 조건 → 모두 T0 그대로), 시험 상태 v3c3-s31 T=2,400(목록 밖). 시드는 run provenance `seed`.
- [실행] `tools/vp_fzp.py sources` → `decl/VP_FZP_SOURCES.json`: NC3·VSL·B·V-A × 시드 31·41·43 = FZP 12개. 선언된 폴더 이름만 열고 디렉터리 훑기는 하지 않음(첫 판이 NC3 루트를 훑다가 봉인 시드 폴더 이름에서 내 blind_guard 에 걸려 멈췄고, 그 폴더는 열지 않았음; 목록 방식으로 고침). NC3·VSL 의 vsl_cell_scan 출력은 기존 것 재사용(nc3 sha 는 SHA256SUMS_VSL 과 같음).
- [실행] 공유 잠금 아래 `vp_tree.py build`: FRZ_K92 → GT/code_va 바이트 복사, FREEZE.json(011f5be2…) 의 10,569 파일 sha 모두 같음(빠짐 0, 다름 0). 16:13–16:16.
- [실행] 배관 시험 smoke v1 (v3c3-s31 T=2,400, 목록 밖, 결과로 쓰지 않음; 16:16–16:23, 잠금 아래): 기록된 계획(held(T) + 기록된 미래 두 블록) AD 경로 목적값이 기록 selected_objective 와 비트까지 같음, 스칼라 경로와의 차 0.0, 재포장(identity) 비트 같음. 소유자별 비용 셋(FW_E·SC1001·SC1005)이 기록과 1.4e-14 이하로 다름 → R1 규칙을 "목적값 비트 같음 + 비용 차 ≤ 1e-9" 로 정함(데이터 전).
- [실행] smoke v1 에서 알게 된 구조: V-A 의 FW_E 는 차로군 plant 가 없고(lane_groups false), 31셀 집계 METANET(`area_freeway_accounting._freeway_substep_events`)으로 1 s 마다 굴러감. 내 첫 훅·절제 코드는 차로군을 가정해 틀렸음(훅 오류 "no lane plant", 절제 KeyError). 훅(재고 = 밀도 × 길이 × 차로)과 절제(구성 사본 패치)를 고침. 우리 plant 셀 = codex 31셀 경계(CELL_B)와 같음 → 구역·셀 번호를 31셀로 고침.
- smoke 숫자에 대해: 배관 확인 중 smoke 상태의 팔별 목적값 차(기록 대비)를 화면에서 봤음. 결과로 쓰지 않고 규칙·문턱 정하는 데 쓰지 않았음.
- [실행] 분석 자체 시험(합성 자료) `selftest/selftest_r2.json` 42/42.
- 16:27 smoke v2 발사(고친 훅·절제, 셀 8–25, 잠금 아래).

## 2026-10-27 16:45 KST — smoke v2·v3 와 도구 고침 (데이터 전, 목록 밖 상태만)

- [실행] smoke v2 (16:27–16:34, 잠금 아래): 종료 0, R1 목적값 비트 같음, 비용 최대 차 1.42e-14(≤ 1e-9), R2 − R1 = 0.0, R3 비트 같음, null 절제 비트 같음. 작업자 훅 14개 모두 걸음 450·오류 0. 작업자가 본 FW_E 구성 값: φ_lane 3.0, δ 1.0(튜닝 네트워크 덮어쓰기 0.3 은 FW_E 걸음이 읽지 않음), φ_cd 1.0, ν_cong 전환 꺼짐, Carlson A 1.33·E 0.87·m_v 0.7225/0.8120/0.9007, 표지 셀 [0,3,5,8,14,18,26,28], 구역 머리 10 = 셀 14–24, 출구 셀 9·11·18·20. C5 절제 요청이 null 과 바이트까지 같았음(구조상 0).
- [실행] smoke v2 에서 찾은 도구 결함 둘(결과 아님): (1) 절제 굴림이 모두 같은 계획(EXEC)이라 행동 토큰만으로는 훅 파일을 가를 수 없음 → 실행기를 묶음 이름별로 만들고(`make_runner(batch)`), 표 도구가 묶음+토큰으로 찾게 고침. 같은 바이트 요청이 두 프로세스에서 돈 경우 두 훅이 같아야 씀. (2) `reach()` 가 훅 없음에서 예외 → (거짓, 'no hook') 로 고침.
- [실행] smoke v3 (16:35–, 잠금 아래) 발사 뒤 찾은 결함(결과 아님): C1·C2 절제가 follower 의 부모 21행에 31셀 번호로 값을 써 넣었음 → follower 행은 행 수가 같을 때만 맞추도록 고침(`follower_rows_patched`, 행 수 기록). 그래서 최종 도구로 smoke v4 를 한 번 더 돌림.
- [실행] 각 plant 일 뒤 멈춤 규칙 점검 `vp_jobcheck.py` 를 큐에 넣음(걸리면 STOP_VP). 탐침 B 요약을 "블록의 실행 VSL 로 묶기" 로 바꿈(켬 22블록·끔 14블록). P1-P 매개변수 표를 더함. 분석 자체 시험 48/48(`selftest/selftest_final.json`).

## 2026-10-27 16:48 KST — 잠금 쉼 규칙 조임

- [실행] smoke v4 큐가 smoke v3 의 잠금 해제 2 s 뒤에 잠금을 잡았음(대기 시작이 해제 전이라 처음 한 번만 쉼 규칙을 봤기 때문). `vp_common.lock_acquire` 를 고쳐 매 시도마다 "우리 마지막 해제 + 20 s" 를 보게 함. 자체 시험에 잠금 쉼 시험을 더해 49/49. smoke v4 는 고치기 전 vp_common 으로 돌고 있음(잠금 함수만 다르고 plant 굴림과 무관).

## 2026-10-27 16:53 KST — smoke v4 (최종 도구) 와 기록 정정

- [실행] smoke v4 (16:45–16:51, 잠금 아래, 목록 밖 v3c3-s31 T=2,400): 종료 0, R1 목적값 비트 같음, 비용 최대 차 1.42e-14, R2 − R1 = 0.0, R3·null 비트 같음, `vp_jobcheck.py` 걸림 0, `vp_tablesmoke.py` 멈춤 0. 기준과 다른 절제 C1·C2·C3·C4·C7, 같은 절제 C5·C6(값은 보지 않고 같음·다름만 봄). 탐침 sha c38fc1a9…, 훅 sha 1c212040… = 고정본.
- **정정**: 16:45 항목의 "C1·C2 절제가 follower 의 부모 21행에 31셀 번호로 값을 써 넣었음" 은 틀린 추정이었음. smoke v4 기록(`component_rows_n` = `follower_rows_n` = 31)으로 follower FW_E 셀 행도 31행임을 확인. 더한 가드(행 수가 같을 때만 follower 를 맞춤)는 안전장치로 두고, V-A 에서는 follower 도 같이 맞춤. smoke v3 의 절제도 같은 동작이었음.
- 남은 글 차이: `vp_probe.py` 머리 설명(docstring)에 R1 비용을 "bit-equal" 로 적었으나 코드는 PRE_VP §3.4 의 1e-9 허용으로 점검함. 규칙은 PRE_VP 가 정본. smoke v4 가 돈 바이트를 그대로 고정하려고 설명은 고치지 않음.

## 2026-10-27 16:54 KST — PRE_VP 고정 (데이터 전)

- [실행] `PRE_VP.md` sha256 **4147f8595506bf2fdc8465a45eb2d94886116acef2535255654dff5e97317eac** (`PRE_VP.md.sha256`). 이 sha 뒤로 PRE_VP 는 고치지 않음.
- [실행] 도구·선언 핀 `SHA256SUMS_VP.txt` sha256 5c36cffa81b680eb06605e9085e59269f664de27e1bf797d2798f388c30a4410 (33줄, `sha256sum -c` 33/33 OK), 바깥 핀 `SHA256SUMS_VP_EXT.txt` sha256 7ce3016bf9214f3eae4068f36daef6d25e5482d2d26ad0ec0664e08158921cb1 (16줄, 16/16 OK). 주요: vp_probe c38fc1a9…, 훅 1c212040…, vp_analyze faff15d4…, vp_job 2164f97e…, vp_queue 53efbad4…, vp_jobcheck a922ab6d…, vp_common a8cdeff5…, VP_STATES 8f09c649…, VP_FZP_SOURCES 2bdf0e7d…, jobs_fzp 3b4f96a4…, jobs_A b68e18f2….
- 탐침 자료(목록 상태의 plant 굴림), 새 FZP 스캔(B·V-A), P1 입력 계산은 하나도 하지 않았음. 쓴 무거운 일은 코드 사본 1번과 목록 밖 smoke 4번뿐(모두 공유 잠금 아래, WMI 분리, BELOW_NORMAL). 잠금은 지금 비어 있음. 남의 프로세스 끄기 0, VISSIM·COM 0, GWT8·FRZ_K92·런 폴더 쓰기 0.
- 보고 사본: `D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant/`.

## 2026-10-27 17:12 KST — 적대적 검토 시작 (PRE_VP r1 → PRE_VP_FIXED)

- 검토 대상: `PRE_VP.md` sha256 4147f859… (= `PRE_VP_r1.md`, 바이트 그대로 보존). r1 도구 사본: `tools/vp_probe_r1.py`(c38fc1a9…), `tools/vp_analyze_r1.py`(faff15d4…), `tools/vp_selftest_r1.py`(2834d829…), `tools/vp_smokecheck_r1.py`(6ee274ee…), `tools/vp_pin_r1.sh`(f40cdbcd…), `tools/vp_hooks/sitecustomize_r1.py.txt`(1c212040…, 자동 import 막으려고 .txt), `SHA256SUMS_VP_r1.txt`(5c36cffa…), `SHA256SUMS_VP_EXT_r1.txt`(7ce3016b…).
- [실행] 핀 33/33·16/16 OK. [실행] 결정 기록 앞 344줄 sha = b33fe5e7…(PRE 인용과 같음), 지금 파일 efc3a722… 는 D-K9-104(346줄~) 덧붙임뿐.
- 찾은 것(요지): (1) R3 는 같은 물리 키 캐시 적중이라 구조상 참(smoke v4: SCALAR 묶음 7계획에 작업자 5개). (2) 셀 18 의 예견항이 4→3 차로 경계에서 차로당 밀도 도약을 봄(metanet.py:113-119, AFA:193·:375) — 후보 목록 밖. (3) 출구 막힘 속도 상한(AFA:346-354·:399-400, 10481 = 셀 18, 10483 = 셀 20)이 측정도 안 됨. (4) C2 ×1.2 는 크기가 자료에서 오지 않음. (5) H1 비용 과대(기존 스캔 23–35 s/개).
- 고침 방향: C8(셀 18 ν=0)·C9(C4+C8 함께) 절제 추가, 훅이 advance 반환값의 출구 흐름·막힘을 수동으로 읽음(X1·X2), R3 뜻 고침, C2 읽는 법 고정. 도구 바뀌므로 자체 시험 + 목록 밖 smoke v5(잠금 아래) 다시.

## 2026-10-27 17:16 KST — 검토 고침: 도구 r2 와 smoke v5 발사 (목록 밖 상태만)

- [실행] 도구 고침(scratch, 저장소·동결 트리 0): `vp_probe.py` C8_antic18(셀 행 ν=0)·C9_lanedrop_both(φ=0 + 셀 18 ν=0) 절제 가지, 설명 글 정정(R1 비용 1e-9, R3 캐시, follower 31행). 훅 `sitecustomize.py` 가 advance 반환값(ttt, off_flows, diagnostics)[2]['FW_E'] 의 `offramp_flow_<o>`·`offramp_blocked_flow_<o>`·`speed_projection_count` 를 블록마다 쌓음(읽기만, 키 없으면 exit_missing, 오류로 치지 않음). `vp_analyze.py` X1·X2·C8·C9 도달 점검·방향 근거 칸·표 B5. `vp_smokecheck.py` 출구 기록 참/거짓. `vp_selftest.py` 65/65 (`selftest/selftest_r5_review.json`).
- [실행] smoke v5 발사 17:15:27 (WMI PID 46848, BELOW_NORMAL, tag pre5, 목록 밖 v3c3-s31 T=2,400, 명세 `smoke/specs/spec_smoke_v5.json` = v2 + C8·C9). 발사 때 공유 잠금은 다른 워크플로(c1_guard_general_data) 것이라 큐가 기다림. 남의 프로세스 손대지 않음.

## 2026-10-27 17:31 KST — smoke v5 결과와 PRE_VP_FIXED 고정 (데이터 전)

- [실행] smoke v5 (17:15:33–17:25:42, 잠금 아래, 목록 밖 v3c3-s31 T=2,400): 종료 0, 벽시계 609 s, R1 목적값 비트 같음, 비용 최대 차 ≤ 1e-13, R2 − R1 = 0.0, REPACK 토큰 = REC 토큰, null 비트 같음(요청 sha 가 EXEC_scalar 와 다름), C5 요청 = null 요청. 훅 16개 걸음 450·오류 0, 출구 기록 모두 있음(exit_missing 0), 셀 경계 차 0.000 m. 도달 점검 C1–C9 참. 기준과 다른 절제 C1·C2·C3·C4·C7·C8·C9, 같은 절제 C5·C6. vp_jobcheck 걸림 0, vp_tablesmoke 멈춤 0. J·편향·X1·X2 값은 보지 않음. 잠금 해제 17:25:42(우리 것만), 그 뒤 잠금은 다른 워크플로가 잡음.
- [실행] 자체 시험 65/65 (`selftest/selftest_final_r2.json` 48efab47…). 핀 `SHA256SUMS_VP.txt` 51f9f38b… (39줄, -c 걸림 0), `SHA256SUMS_VP_EXT.txt` 5e84baf4… (15줄, -c 걸림 0).
- [실행] VISSIM 되읽기 대조 63/63 블록 같음, 21상태 × 3결정 `.applied` 모두 있음, CELL_B·구역이 o1o2 원천과 같음, P1 상태의 T−150 은 모두 110.
- [실행] `PRE_VP_FIXED.md` sha256 **33e71ac36b316e702006b2259ab7438233382de78a172b2f2340be813d7755f1** (`PRE_VP_FIXED.md.sha256`). 이 문서가 정본이고 r1(`PRE_VP.md` = `PRE_VP_r1.md`, 4147f859…)은 대체됨. 이 sha 뒤로 고치지 않음.
- 남은 선택지(결함 아님, 사용자): 출구 막힘 절제(출구 저장·포트 용량·SA 접근로를 함께 바꾸는 설계)는 이번에 안 함. X1 로 작동 여부만 잼.
- 탐침 자료(목록 상태 plant 굴림), B·V-A 새 FZP 스캔, P1 입력 계산은 하나도 하지 않았음(GT/out 없음). VISSIM·COM·러너·동결 0, GWT8·FRZ_K92·런 폴더 쓰기 0, 남의 프로세스 끄기 0.

## 2026-10-27 17:29 KST — 기록 정정

- 바로 위 항목 머리의 "17:31" 은 어림이었음. 실제로 쓴 때는 17:29 KST(파일 시각). 보고 사본은 RVP 에 17:29 에 복사(PRE_VP_FIXED.md 33e71ac3…, PRE_VP_r1.md 4147f859…, LOG.md, 핀 목록 둘).

## 2026-10-27 17:33 KST — P1 실행 시작: L0 (핀·자체 시험)

- 정본: `PRE_VP_FIXED.md` sha256 33e71ac3… [실행 다시 셈, `PRE_VP_FIXED.md.sha256` 과 같음]. 이번 일은 P1(§5) 만 돕니다: L0 → L1 → H0 → H1 → L2 → H3 → L3. 탐침 A·B(H2)는 이번 일에 넣지 않습니다.
- [실행] 핀 `SHA256SUMS_VP.txt` sha 51f9f38b…(§9 와 같음) `sha256sum -c` 39/39 OK, `SHA256SUMS_VP_EXT.txt` sha 5e84baf4…(§9 와 같음) 15/15 OK. 걸림 0.
- [실행] 자체 시험 `vp_selftest.py` → `selftest/selftest_L0_p1.json`: 65/65 참. r2 기록(48efab47…)과 다른 칸은 시각과 잠금 쉼 시험의 잰 시간(1.0005 s 대 1.0051 s)뿐. 자체 시험의 잠금 시험은 임시 잠금 파일(selftest/lock_<pid>)만 씀.
- 디스크 여유 C 17 GB, D 201 GB (≥ 8 GB). 남의 프로세스(다른 세션의 VISSIM 2개, 어댑터·작업자, c1_guard 의 gd_scan) 손대지 않음. 공유 잠금은 지금 c1_guard_general_data 것.

## 2026-10-27 17:32 KST — Q-V3 실행 시작 (탐침 A·B, PRE_VP_FIXED 그대로)

- 범위: PRE_VP_FIXED(33e71ac3…) §8 의 L0 → H0 → H1 → H2 → L3. P1(L1·L2·H3, Q-V4)은 이 실행에서 하지 않음. H1 은 선언된 `decl/jobs_fzp.json` 9개를 그대로 돌림(탐침 B 는 V-A 프레임 3개만 씀; 셀 스캔 6개는 P1 입력으로 남김).
- [실행] L0: PRE_VP_FIXED.md sha 33e71ac3… = `PRE_VP_FIXED.md.sha256`. 핀 `SHA256SUMS_VP.txt` 51f9f38b… 39/39 OK, `SHA256SUMS_VP_EXT.txt` 5e84baf4… 15/15 OK. 결정 기록 앞 344줄 sha b33fe5e7… 같음. 자체 시험 65/65 (`selftest/selftest_qv3_run_741546.json` 66bb0065…). STOP_VP 없음, GT/out 없음(탐침 자료 0 에서 시작). 디스크 C: 17 GB, D: 201 GB.
- H0 일 목록 `runs/jobs_qv3_h0.json`(vp_tree.py verify 하나, 공유 잠금 아래). 잠금은 지금 다른 워크플로(c1_guard_general_data) 것이라 큐가 기다림.

## 2026-10-27 17:35 KST — P1: L1, H0·H1 는 Q-V3 실행과 같이 씀

- 같은 시각에 Q-V3 실행(탐침 A·B)이 같은 VP·GT 에서 돌고 있음(LOG 17:32 항목). 겹치는 일(H0·H1)은 두 번 하지 않음: 같은 출력 파일을 두 큐가 동시에 쓰는 경합(.done 은 일이 끝난 뒤에 써짐)과 `code_va.tree.json` 덮어쓰기를 피하려고. 이 P1 실행은 Q-V3 의 H0·H1 결과를 sha 로 받아 씀.
- [실행] L1 `vp_analyze.py p1-fzp` → `GT/out/tables/p1_fzp_L1.json` (f063c865…): 셈이 있는 원천 6개(NC3·VSL × 3). B·V-A 는 H1 전이라 없음(정의대로).
- [실행 읽음] H0 = Q-V3 큐 `qv3_h0` 의 `vp_tree.py verify`(17:32:18–17:32:39, 공유 잠금 아래, 종료 0): ok 참, 10,569 파일, 빠짐 0, 다름 0, FREEZE.json sha 011f5be2…. 기록 `GT/code_va.tree.json` 이 다시 써져 sha 가 53e4403f… → 67e6681e… 로 바뀜(시각 칸). 그래서 이 뒤로는 EXT 핀 목록의 그 한 줄이 맞지 않는 것이 정상입니다(H0 가 쓰는 파일). 내 L0 는 H0 전에 끝났음.
- H1 은 Q-V3 큐 `fzp`(17:32:57 발사, `decl/jobs_fzp.json` 3b4f96a4… 그대로)가 돌림. 9개 `.done` 을 기다린 뒤 L2.

## 2026-10-27 17:40 KST — H0·H1 끝, H2 발사

- [실행] H0 (17:32:18–17:32:39, 잠금 아래, WMI PID 4140, 큐 pid 40616): `vp_tree.py verify` 종료 0, 10,569 파일 빠짐 0·다름 0, FREEZE.json sha 011f5be2… 같음. 기록 `GT/code_va.tree.json` 이 다시 쓰여 sha 가 67e6681e… 로 바뀜(바깥 핀의 53e4403f… 는 16:16 기록; 바뀐 칸은 확인 시각 `checked_kst` 뿐이라고 봄 [추론, 옛 바이트 없음]; 도구 핀이 아니고 vp_job 은 ok 칸만 읽음).
- [실행] H1 (17:32:57–17:40:33, 일마다 잠금, WMI PID 40772, 큐 pid 47192): `decl/jobs_fzp.json` 9개 모두 종료 0(셀 스캔 31–38 s, 프레임 스캔 26–27 s). 첫 일은 다른 워크플로 잠금 뒤 16 s 기다림, 그 뒤는 우리 해제 + 20 s 쉼. 프레임 스캔 셋은 1,200 프레임씩. 출력 sha: frames VA s31 7710f1e9…, s41 d364dd95…, s43 d5be51bf…; cell B s31 25ef21a5…, s41 6b1f4353…, s43 bf92542b…; cell VA s31 70a0f8ca…, s41 9e9851da…, s43 1b027e41…. 값은 보지 않음.
- H2 발사: `decl/specs/jobs_A.json`(b68e18f2…) 12상태, 태그 qv3h2.

## 2026-10-27 17:43 KST — P1: H1 결과 받음, L2, H3 발사

- [실행 읽음] H1 = Q-V3 큐 `fzp`(17:33:13–17:40:33, 일마다 공유 잠금, 해제 뒤 20 s 쉼): 9개 모두 종료 0(26–38 s). 출력 sha: 셀 B_v3c3-s31 25ef21a5…, B_v3c3-s41 6b1f4353…, B_v3c3-s43 bf92542b…, VA_v3c3-s31 70a0f8ca…, VA_v3c3-s41 9e9851da…, VA_v3c3-s43 1b027e41…; 프레임 VA_v3c3-s31 7710f1e9…, VA_v3c3-s41 d364dd95…, VA_v3c3-s43 d5be51bf… (프레임 1,200개씩).
- [실행] L2 `vp_analyze.py p1-inputs GT/out/p1_specs` (데이터 뒤 기계적 생성, 규칙 §5.4): `p1_inputs.json` dda66474…, `jobs_P.json` b6c75af5…, 명세 9개(sha 는 P1_REPORT). C1 은 NC3 저밀도 창 ≥ 20 인 셀 12개(8–18, 22)만 바꿈 — 셀 19–21·23–25 는 창이 20 미만이라 규칙대로 그대로 둠. C7 은 상태마다 프레임 2개(T−4.9, T+0.1), 셀 18개.
- H3 발사: `vp_launch.ps1 -Jobs GT/out/p1_specs/jobs_P.json -Tag p1h3` (큐 이름 plantP). 지금 공유 잠금은 Q-V3 의 H2 첫 일(plantA)이 잡고 있어 큐가 기다림. STOP_VP 는 두 실행이 함께 씀(어느 쪽이 멈춤 규칙에 걸려도 남은 무거운 일은 멈춤, §7).

## 2026-10-27 17:42 KST — 기록 정정과 H3 큐 시작

- 바로 위 항목 머리의 "17:43" 은 어림이었음. 실제로 쓴 때는 17:41 KST.
- [실행] H3 큐 발사 17:41:31 (WMI PID 32620, 큐 pid 35444, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움; `jobs_P.json` b6c75af5…, 큐 sha 53efbad4… = 핀). 첫 일 P_v3c3-s31_T001800 은 잠금을 기다리는 중(잠금 = Q-V3 plantA 첫 일).

## 2026-10-27 17:56 KST — P1: S-R1 걸림 → STOP_VP, 남은 P1 무거운 일 0

- [실행] H3 첫 일 P_v3c3-s31_T001800 (잠금 17:46:02–17:49:45, 벽시계 223 s): 탐침 종료 5, `stop` = S-R1. 그 뒤 `vp_jobcheck.py` 종료 2, 큐가 `VP/STOP_VP` 를 17:49:46 에 쓰고 멈춤(QUEUE_END). 남은 P1 8상태는 돌지 않았음.
- [실행 읽음 probe.json 46e85a2f… `checks`] R1 목적값 비트 같음 = 거짓, 차 = +1.1368683772161603e-13 veh·h (기록 428.70567665096473 대 재생 428.70567665096485, 그 크기의 ULP 5.68e-14 의 2배). 비용 20개 키 같음, 최대 차 3.55e-15 (≤ 1e-9 참). 다른 비용은 SC1001·SC1003·SC1004·SC1005 넷뿐이고 각 1–2 ULP; FW_E 비용은 비트 같음. R0(기록 토큰 같음) 거짓(PRE 에 적힌 대로 보고만).
- R1 에서 멈췄으므로 스칼라 묶음·절제(null, C1–C9)는 하나도 돌지 않았음. 편향·R 값 없음. 훅 파일은 R1 AD 굴림 1개뿐.
- 규칙대로 멈춤(§3.4·§7). 규칙을 바꾸지 않고, 다시 돌리지 않음. 사용자 결정 대기.
- [실행 읽음] 관찰: Q-V3 큐(plantA, pid 27604)가 STOP_VP(17:49:46) 뒤 17:50:05 에 잠금을 잡고 A_v3c3-s31_T003450 을 시작함. `vp_queue.py` 가 STOP_VP 를 잠금 기다리기 전(:38)에만 보고, 잠금을 잡은 뒤(:47)에는 다시 보지 않기 때문. 내 프로세스가 아니라 손대지 않음.

## 2026-10-27 17:51 KST — 기록 정정

- 바로 위 항목 머리의 "17:56" 은 어림이었음. 실제로 쓴 때는 17:51 KST.

## 2026-10-27 17:56 KST — P1_REPORT 씀 (멈춤 보고), 보고 사본

- [실행] 멈춘 뒤 가벼운 읽기만: `vp_analyze.py p1-fzp` 를 H1 출력까지 넣어 다시 돌림 → `GT/out/tables/p1_fzp_afterH1.json` f2c76752… (원천 12개, VISSIM 쪽만; plant 기준 굴림이 없어 편향은 없음). 잠금 없음.
- [실행 읽음] Q-V3 큐(plantA)는 그 일(A_v3c3-s31_T003450, 17:50:05–17:54:28) 뒤 17:54:29 에 "STOP_VP present" 로 멈춤. 17:56 공유 잠금 비어 있음.
- [실행] `P1_REPORT.md` c28c9178…, `P1_REPORT.json` 59b67ad6… (같은 이름 .sha256). JSON 은 일회용 읽기 스크립트 `report_p1/p1_report_json.py` 834ae30a… 로 씀(출력만 읽음, 도구 아님).
- 상태: STOP (S-R1). 사용자 결정 D1–D4 대기(P1_REPORT §6). STOP_VP 는 지우지 않음. 규칙·도구 바꾸기 0, 다시 굴리기 0.
- 보고 사본: RVP 에 P1_REPORT.md·.json·.sha256 둘, LOG.md.

## 2026-10-27 18:01 KST — Q-V3: H2 2상태 뒤 멈춤 (STOP_VP), 부분 표와 보고

- [실행] H2 큐(plantA, WMI PID 24604, 큐 pid 27604): A_v3c3-s31_T003300 17:40:59–17:45:42 종료 0·점검 걸림 0. 다음 일 앞(17:45:43)에서 STOP_VP 없음 → 잠금 기다림. P1 큐가 17:46:02 에 잠금을 잡고 S-R1(목적값 2 ULP, +1.137e-13 veh·h) → STOP_VP 17:49:46. 우리 큐는 17:50:05 에 잠금을 잡아 A_v3c3-s31_T003450 을 돌림(17:54:28 종료 0·점검 걸림 0) — STOP_VP 뒤 시작(큐가 잠금 잡은 뒤 STOP_VP 를 다시 보지 않는 틈, vp_queue.py:38–47). 17:54:29 다음 일 앞에서 멈춤. 남은 10상태 안 돎.
- 규칙대로 멈춤(PRE_VP_FIXED §7). 규칙·도구 바꾸지 않음, STOP_VP 지우지 않음, 다시 굴리지 않음. 끈 프로세스 0.
- [실행] 데이터 뒤: A1 상태의 R2 − R1 = +1.137e-13(스칼라 대 AD, 같은 계획) — P1 R1 걸림과 같은 크기. A1·A2 의 R1 은 비트 같음.
- [실행] 가벼운 일: 핀 다시 대조 17:59 (VP 39/39, EXT 14/15 — code_va.tree.json 한 줄, H0 가 시각 칸을 다시 씀). 고정 도구 `vp_analyze.py tables` 로 부분 표를 선언 이름이 아닌 `GT/out/tables/vp_tables_qv3_stop.{json,md}` 로 냄(b658d74d… / 5dd44892…). 읽기만 하는 모음 `runs/qv3_collect.py`(567229be…) → `runs/qv3_collect.{json,md}`. 보고 `QV3_REPORT.md`·`QV3_REPORT.json`(+ .sha256), 사본 RVP.
- 사용자 결정 대기: Q1(R1 규칙 = P1 D1), Q2(T=3,450 결과 씀/다시), Q3(큐 틈 = P1 D4), Q4(EXT 핀 줄), Q5(STOP_VP 지우기 = P1 D2).

## 2026-10-27 18:12 KST — 고침 r3 시작 (데이터 뒤, 사용자 결정 D-K9-108·109)

- 근거: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` sha256 64f20294… (361–367 줄 D-K9-108·109) [실행 sha 다시 셈]. 보고 `QV3_REPORT.md` 7e196d9f…, `P1_REPORT.md` c28c9178…, `STOP_VP` ebd85663…, 정본 `PRE_VP_FIXED.md` 33e71ac3… [실행 sha 다시 셈, 모두 같음].
- 할 일(이것만): `PRE_VP_R3.md`(데이터 뒤 고침) · `vp_probe.py`·`vp_jobcheck.py` 의 R1 목적값 허용(|재생 − 기록| ≤ 1e-9 veh·h) · `vp_queue.py` 의 잠금 뒤 STOP_VP 다시 보기 · 자체 시험 다시 · 핀 r3(`SHA256SUMS_VP_r3.txt`, `SHA256SUMS_VP_EXT_r3.txt`) · 멈춘 P1 일 폴더와 `.done` 을 `*_interrupted_*` 로 옮김 · 그 뒤 STOP_VP 지움. 탐침 굴림·FZP 스캔·VISSIM·COM·러너·동결 0.
- [실행] 시작 상태 18:11: r2 핀 `SHA256SUMS_VP.txt` 39/39 OK, `SHA256SUMS_VP_EXT.txt` 14/15 (걸린 줄은 `code_va.tree.json` 하나, H0 가 시각 칸을 다시 씀 — D-K9-109 (3) 의 대상). STOP_VP 있음. 우리 python 프로세스(vp_queue·vp_job·vp_probe) 0. 공유 잠금은 다른 워크플로(fwe_verify) 것 — 이번 일은 무거운 일이 없어 잠금을 잡지 않음. 디스크 C 16.3 GB, D 199.4 GB.

## 2026-10-27 18:18 KST — r3: 도구 고침 셋, 시험, 핀 r3 기록 (새 계산 전)

- [실행] r2 바이트 보존(18:13): `tools/vp_probe_r2.py` 1c08ad5b…, `tools/vp_jobcheck_r2.py` a922ab6d…, `tools/vp_queue_r2.py` 53efbad4… (r2 핀과 같음).
- [실행] 고친 도구 셋(스크래치만; 저장소·동결 트리·GWT8 0). r3 sha: `vp_probe.py` 81925375151d5eb4b5129c3999e3fdc5e1975bbe01ad485be4a664ce9e209dae, `vp_jobcheck.py` a664ab99dbcd7766049533dcaaf44c6ca952006c0f740b65915300b885305b24, `vp_queue.py` 9145bd3592f566257c1bcfdfa4b530a5c5149cc43fd41831822b59dbc0d40d7c. 차이(diff -u, r2 → r3, 파일 `review_r3/diff_*_r2_r3.txt` 와 같은 글):

```diff
--- vp_probe.py@r2
+++ vp_probe.py@r3
@@ -26,9 +26,10 @@
   EXEC  = pack([held(action_T), held(action_{T+150}), held(action_{T+300})]) = the block-0 commands VISSIM actually
           ran in [T, T+450).
 Checks written to the output (the caller applies the stop rules):
-  R1  REC, AD mode (as recorded: the selected plan was scored by an AD rollout) -> objective bit-equal to action_T
-      metadata.joint_leader_selection.selected_objective and every omega_partition cost within 1e-9 veh*h
-      (PRE_VP_FIXED section 3.4; the r1 docstring said "bit-equal" for the costs, the code always used 1e-9).
+  R1  REC, AD mode (as recorded: the selected plan was scored by an AD rollout) -> objective within 1e-9 veh*h of
+      action_T metadata.joint_leader_selection.selected_objective and every omega_partition cost within 1e-9 veh*h
+      (PRE_VP_R3, user decision D-K9-108, data-after amendment r3; r2 = PRE_VP_FIXED section 3.4 required the
+      objective bit-equal.  R1_objective_bit_equal is still written, report only).
   R2  REC, scalar mode -> recorded gap R2 - R1 (reported).
   R3  REPACK scalar == REC scalar (bit).  REPACK normally has the REC token, so Query.evaluate serves it from the
       same physical-key cache entry (one worker): R3 then checks the identity repack, not a second rollout.
@@ -302,11 +303,14 @@
             out['checks']['R1_costs_max_abs_diff'] = cdiff
             out['checks']['R1_costs_within_1e-9'] = same_keys and cdiff <= 1e-9
             out['checks']['R1_objective_diff'] = r1['objective_veh_h'] - rec_obj
+            # r3 (D-K9-108): the objective uses the same tolerance as the costs; bit equality stays a report field.
+            odiff = out['checks']['R1_objective_diff']
+            out['checks']['R1_objective_within_1e-9'] = math.isfinite(odiff) and abs(odiff) <= 1e-9
             write(out)
             if mode == 'S' and SPEC.get('smoke_candidates'):
                 evaluate([('CAND_direct_ad', plans['CAND_direct'])], True, 'CAND_ad')
-            if not (out['checks']['R1_objective_bit_equal'] and out['checks']['R1_costs_within_1e-9']) and mode != 'S':
-                out['stop'] = 'S-R1: recorded plan does not reproduce the recorded objective bit-exactly (or a cost by > 1e-9)'
+            if not (out['checks']['R1_objective_within_1e-9'] and out['checks']['R1_costs_within_1e-9']) and mode != 'S':
+                out['stop'] = 'S-R1: recorded plan does not reproduce the recorded objective within 1e-9 (or a cost by > 1e-9)'
                 write(out)
                 return finish(out, 5)
             # scalar batch
--- vp_jobcheck.py@r2
+++ vp_jobcheck.py@r3
@@ -2,12 +2,15 @@
 
     python -B vp_jobcheck.py <job_dir> <mode A|P|S> <out.json>
 
-Checks: probe errors / stop (S-ERR, S-R1), R1 objective bit-equal and costs <= 1e-9 (S-R1), R3 repack bit-equal
+Checks: probe errors / stop (S-ERR, S-R1), R1 objective and costs within 1e-9 veh*h (S-R1; r3 = PRE_VP_R3,
+D-K9-108: the objective is no longer required bit-equal; a probe.json written before r3 has no
+R1_objective_within_1e-9 field and is judged from its R1_objective_diff), R3 repack bit-equal
 (S-R3), null ablation bit-equal (S-NULL, modes P and S), every scalar evaluation used by the tables has exactly one
 hook record with 450 steps, t = T..T+449, 150 steps per block, 31 cells and no hook error (S-HOOK), plant cell
 boundaries within 1 m of CELL_B (S-MAP), ablation values seen by the worker (S-REACH).  Exit 0 = no rule hit,
 2 = a rule hit (the queue then writes STOP_VP)."""
 import json
+import math
 import sys
 from pathlib import Path
 
@@ -16,6 +19,20 @@
 import vp_common as C  # noqa: E402
 import vp_analyze as A  # noqa: E402
 
+R1_TOL = 1e-9   # veh*h, the R1 cost tolerance of PRE_VP_FIXED 3.4, used for the objective too since r3 (D-K9-108)
+
+
+def r1_objective_ok(ck):
+    """R1 objective rule of r3: |replay - record| <= 1e-9 veh*h.  Uses the probe's own boolean when present (r3 probe),
+    else the recorded difference R1_objective_diff (probe.json written by the r2 probe).  Missing / non-finite -> False."""
+    v = ck.get('R1_objective_within_1e-9')
+    if isinstance(v, bool):
+        return v
+    d = ck.get('R1_objective_diff')
+    if isinstance(d, bool) or not isinstance(d, (int, float)) or not math.isfinite(d):
+        return False
+    return abs(d) <= R1_TOL
+
 
 def main():
     jd, mode, out_path = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
@@ -28,8 +45,9 @@
     if probe.get('stop'):
         hits.append('S-R1: %s' % probe['stop'])
     ck = probe.get('checks') or {}
-    if ck.get('R1_objective_bit_equal') is not True or ck.get('R1_costs_within_1e-9') is not True:
-        hits.append('S-R1: R1 objective %s costs %s' % (ck.get('R1_objective_bit_equal'), ck.get('R1_costs_within_1e-9')))
+    obj_ok = r1_objective_ok(ck)
+    if obj_ok is not True or ck.get('R1_costs_within_1e-9') is not True:
+        hits.append('S-R1: R1 objective within 1e-9 %s costs %s' % (obj_ok, ck.get('R1_costs_within_1e-9')))
     if ck.get('R3_repack_bit_equal') is not True:
         hits.append('S-R3: %s' % ck.get('R3_repack_bit_equal'))
     if mode in ('P', 'S') and ck.get('null_bit_equal') is not True:
@@ -59,6 +77,7 @@
                 hits.append('S-REACH: %s %s' % (lab, rwhy))
     rec = {'schema': 'vp-jobcheck/1', 'kst': C.kst(), 'job': jd.name, 'mode': mode, 'hits': hits,
            'checks': {k: v for k, v in ck.items() if isinstance(v, bool)}, 'hooks': hooks,
+           'r1_rule': 'r3: objective and costs within 1e-9 veh*h (D-K9-108)', 'r1_objective_ok': obj_ok,
            'probe_sha256': C.sha256_file(jd / 'probe.json') if (jd / 'probe.json').is_file() else None}
     C.write_json(out_path, rec)
     print('JOBCHECK %s mode=%s hits=%d' % (jd.name, mode, len(hits)))
--- vp_queue.py@r2
+++ vp_queue.py@r3
@@ -7,7 +7,9 @@
                                      "dir": ...},
                                     {"tag": ..., "kind": "py", "args": [script, arg, ...]}]}
 Per job: skip when <VP>/logs/<name>/<tag>.done exists (resume); stop before the next job when <VP>/STOP_VP exists;
-take the shared LOCK (exclusive create; our own last release must be >= 20 s ago), run the job as a BELOW_NORMAL
+take the shared LOCK (exclusive create; our own last release must be >= 20 s ago), look for STOP_VP once more right
+after taking the LOCK (r3, D-K9-109: another queue may have written it while we waited; then release the LOCK, run
+nothing, write no .done and stop), run the job as a BELOW_NORMAL
 child with the K9-2 environment (vp_common.child_env), release the LOCK, write <tag>.done with the exit code.  A job
 of mode A/P is followed by vp_jobcheck.py (stop rules of PRE_VP section 7); a nonzero job exit, a probe stop or a
 jobcheck hit writes STOP_VP and the queue stops (user decision).  Kills nothing except a job's own process tree (vp_job.py watchdog)."""
@@ -45,6 +47,11 @@
         else:
             argv = [C.PY, '-B'] + [str(a) for a in j['args']]
         C.lock_acquire('vsl_plant %s/%s' % (spec['name'], j['tag']), log)
+        if stop.is_file():
+            # r3 (D-K9-109): STOP_VP written while this queue waited on the LOCK -> no job, no .done.
+            log('STOP_VP present after LOCK: stop before %s' % j['tag'])
+            C.lock_release(log)
+            break
         try:
             log('JOB_BEGIN %s %s' % (j['tag'], ' '.join(argv[2:])[:400]))
             rc, sec = C.run_capture(argv, logdir / (j['tag'] + '.out.txt'), env)
```

- 뜻: (1) R1 목적값 = |재생 − 기록| ≤ 1e-9 veh·h (비용과 같은 허용, D-K9-108). `R1_objective_bit_equal` 은 계속 적지만 보고만. (2) `vp_jobcheck.py` 는 새 칸이 없는 r2 꼴 probe.json 을 `R1_objective_diff` 로 판단(없음·NaN·무한·bool 이면 거짓). (3) 큐는 잠금을 잡은 바로 뒤 STOP_VP 를 한 번 더 보고, 있으면 잠금을 풀고 일·`.done` 없이 멈춤(D-K9-109 (2)).
- [실행] 새 파일(고침이 아니라 D-K9-109 (3) 구현과 기록): `tools/vp_treefields.py` e864fcf8…(code_va.tree.json 의 schema·ok·freeze_sha256·files_expected·missing_n·differs_n·missing·differs 만 대조, checked_kst 무시, 참/거짓만 냄), `tools/vp_pin_r3.sh` 5e044494…, `decl/R3_MARKS.json` e3c08da0…(s31 T=3,450 표시 "STOP_VP 뒤 시작(+19 s)", T=3,300 그대로, P1 s31 T=1,800 다시 굴림 예정).
- [실행] 고침 시험 `review_r3/r3_patchtest.py` 7c480d07… → `review_r3/r3_patchtest.json` 9e5d4577…: **30/30 참**. 합성 입력(PID 붙은 임시 폴더, 끝에 지움; 실제 잠금·STOP_VP 손대지 않음). A: 2 ULP 차는 S-R1 아님, 2e-9 는 S-R1, 비용 초과·probe stop 칸은 여전히 S-R1, r2 꼴 판단, 경계 ±1e-9 참. 기존 기록(읽기만, 데이터 뒤): P1 s31 T=1,800 은 r3 규칙으로 R1 목적값 참·비용 참(r2 비트 거짓), plant_A s31 T=3,300·3,450 은 참·참. B: 잠금 기다리는 동안 STOP_VP 가 생기면 r3 큐는 일 0·`.done` 0·잠금 1번 풀고 멈춤; 같은 상황에서 r2 큐는 일 1개를 돌림(틈 재현); STOP_VP 없으면 일 2개 모두; 시작 전 STOP_VP 면 잠금 안 잡음; 두 번째 일 기다리는 중 생기면 첫 일만. C: 실제 기록 칸 모두 참, 시각 칸만 바꾼 사본 참, ok 거짓·ok=1·missing_n 1·differs 있음·파일 수 다름·freeze sha 다름·dict 아님은 모두 거짓. D: 네 파일 compile 참(바이트코드 안 씀), 멈춤 줄이 새 칸을 씀, 큐에서 다시 보기가 잠금과 일 사이.
- [실행] 자체 시험 다시 `vp_selftest.py` → `selftest/selftest_amend_r3.json` 9df60af4…: **65/65 참**. r2 기록(48efab47…)과 다른 칸은 잠금 쉼 시험의 잰 시간(0.997 s 대 1.005 s, 문턱 0.9 s)뿐. (처음 출력 이름 `selftest_r3.json` 은 16:30 의 옛 파일이 있어 덮어쓰지 않고 새 이름으로 돌림; 옛 파일 c28190ef… 그대로.)
- [실행] **핀 r3 기록** (18:16:54): `SHA256SUMS_VP_r3.txt` sha256 **87a214065222626b4b312671c5668167946eb0a798fc48854e0baa37fb898720** (54줄, `sha256sum -c` 54/54 OK), `SHA256SUMS_VP_EXT_r3.txt` sha256 **217c0538bbd9e3491cef184f1bd0c6cfe86d4c3b30e58200937f3a5016933227** (14줄, 14/14 OK; r2 EXT 에서 code_va.tree.json 한 줄만 뺀 것과 같음 [실행 diff]). `vp_treefields.py` 실제 기록 ok 참(기록 sha 67e6681e…, 시각 칸 17:32:39 무시). r2 목록 `SHA256SUMS_VP.txt` 51f9f38b…·`SHA256SUMS_VP_EXT.txt` 5e84baf4… 는 바꾸지 않고 기록으로 둠(r3 VP 목록에 포함).
- 이 기록 전에 한 새 계산 0(탐침 굴림·FZP 스캔·P1 입력 0). STOP_VP 아직 있음. 우리 프로세스 0.

## 2026-10-27 18:20 KST — PRE_VP_R3 고정 (데이터 뒤)

- [실행] `PRE_VP_R3.md` sha256 **2c1d6ceff07a458f5b309b04a846ebae4fe2bb6cf63bcf52e9fef5fe438a030a** (`PRE_VP_R3.md.sha256`, 105줄). PRE_VP_FIXED(33e71ac3…)를 X1–X6 에서만 바꿈: X1 R1 목적값 ≤ 1e-9 veh·h(비트 같음은 보고만), X2 s31 T=3,450 표시하고 씀, X3 큐 잠금 뒤 STOP_VP 다시 보기, X4 EXT 핀에서 code_va.tree.json 줄 빼고 `vp_treefields.py` 칸 대조, X5 멈춘 P1 일 `*_interrupted_*` 로(일 폴더는 `GT/out/interrupted/plant_P/` — `vp_analyze.py`:170–171 이 `plant_P` 안 모든 폴더를 읽기 때문), X6 STOP_VP 지움(바이트 사본 남김). r3 뒤 L0 = PRE_VP_R3 §3.1.
- 적어 둔 것(고치지 않음): 표 도구 `vp_analyze.py` 는 지시 범위 밖이라 그대로 — R1 비트 다름을 "멈춤 규칙 걸림" 목록·표 A1 R1 칸에 계속 적으므로 PRE_VP_R3 §1.1 의 읽는 법으로 처리(사용자 선택지 O1). S-NULL·R3 는 비트 같음 그대로라 같은 꼴 걸림 위험이 남음(§5, O2).

## 2026-10-27 18:21 KST — r3: 멈춘 P1 일 옮김, STOP_VP 지움, 다시 대조

- [실행] X5 이동 18:20:35 (일회용 `review_r3/r3_move_interrupted.py` 2b89ced9…, 기록 `review_r3/move_interrupted_r3.json` 4dd3bd25…): 일 폴더 `GT/out/plant_P/v3c3-s31_T001800` → `GT/out/interrupted/plant_P/v3c3-s31_T001800_interrupted_r2stop_20261027_182035` (파일 40개·121,531,924 바이트 그대로, probe.json 46e85a2f…·jobcheck.json 97187314…·job_summary.json 5864c3db… 이동 전후 같음). 로그 `logs/plantP/P_v3c3-s31_T001800.{done,out.txt,check.txt}` → `P_v3c3-s31_T001800_interrupted_r2stop_20261027_182035.{done,out.txt,check.txt}` (sha 이동 전후 같음; .done 4c6ac9cb…). 지금 `plant_P` 안 폴더 0, 큐가 볼 `.done` 없음 → 다음 실행에서 이 상태부터 r3 도구로 다시 굴러감. 이동 때 공유 잠금은 우리 것이 아니었음(도구가 확인).
- [실행] X6 18:20:42: STOP_VP 바이트 사본 `review_r3/STOP_VP_r2.json` sha ebd85663… = 원본 → STOP_VP 지움. 핀 r3 기록(18:18 항목) 뒤입니다.
- [실행] 18:20:52 다시 대조: `SHA256SUMS_VP_r3.txt` 54/54, `SHA256SUMS_VP_EXT_r3.txt` 14/14, `PRE_VP_R3.md.sha256`·`PRE_VP_FIXED.md.sha256` OK, `vp_treefields.py` 종료 0. plant_A 의 두 상태(s31 T=3,300·3,450)와 `.done` 그대로. 공유 잠금 비어 있음. 바이트코드 파일 0.
- 이번 고침에서 한 것: 문서·도구 고침·시험·핀·파일 이동·표지 지움뿐. 탐침 굴림·FZP 스캔·P1 입력 계산·VISSIM·COM·러너·동결 0, GWT8·FRZ_K92·런 폴더 쓰기 0, 남의 프로세스 손대지 않음, 무거운 일 0(잠금 안 잡음).
- 다음: 같은 큐 도구로 H2(탐침 A 남은 10상태, s31 T=4,050 부터)와 H3(P1 9상태, s31 T=1,800 다시부터) 이어 감 — L0 는 PRE_VP_R3 §3.1. 사용자 선택지 O1(표 도구 R1 칸 코드 고침)·O2(S-NULL 허용) 는 그대로 남음.
- 보고 사본: RVP 에 PRE_VP_R3.md(+ .sha256), 핀 r3 둘, LOG.md, `r3/` 아래 R3_MARKS.json·r3_patchtest.json·move_interrupted_r3.json·selftest_amend_r3.json·차이 파일 셋.

## 2026-10-27 18:24 KST — Q-V3 r3 실행 시작 (탐침 A·B 이어 감): L0

- 정본: `PRE_VP_FIXED.md`(33e71ac3…) + `PRE_VP_R3.md`(2c1d6cef…). 근거 사용자 결정 D-K9-108·109 (결정 기록 sha 64f20294… [실행 다시 셈]). 이 실행은 Q-V3(탐침 A·B)만: L0 → H0 → (H1 끝남, 건너뜀) → H2 남은 10상태 → L3. P1(H3)은 따로 도는 P1 실행의 일입니다(같은 VP·GT·잠금·STOP_VP 를 함께 씀; 그쪽 L0 기록 `selftest/selftest_L0_p1r3_43144.json` 이 18:23 에 생김 [실행 읽음]).
- [실행] L0 (PRE_VP_R3 §3.1, 18:23): `PRE_VP_R3.md` sha = `.sha256` (2c1d6cef…), `PRE_VP_FIXED.md` OK. `SHA256SUMS_VP_r3.txt`(87a21406…) 54/54 OK, `SHA256SUMS_VP_EXT_r3.txt`(217c0538…) 14/14 OK. `vp_treefields.py` 종료 0(칸 8개 모두 참; 기록 `selftest/treefields_qv3r3_L0_745408.json` 4532d280…). 자체 시험 65/65 참(`selftest/selftest_qv3r3_L0_745408.json` 37f89e4b…; r2 기록 48efab47… 과 다른 칸은 시각과 잠금 쉼 시험 잰 시간 1.0051 대 1.0010 s 뿐).
- [실행] 이어 갈 자료 확인: plant_A s31 T=3,300 probe f8dc7dac…·job_summary e562397f…·jobcheck c2c99047…, T=3,450 probe 866ab215…·job_summary 1e9e280d…·jobcheck e9e913f6… = `decl/R3_MARKS.json` 과 같음. `.done` 둘 그대로(큐가 건너뜀). H1 출력 9개 sha = LOG 17:40 항목과 같음, `.done` 9개 종료 0 → H1 은 다시 돌리지 않음. `STOP_VP` 없음. 공유 잠금 비어 있음. 우리 VP 프로세스 0. 남의 VISSIM·어댑터 프로세스는 손대지 않음.
- 다음: H0(`vp_tree.py verify`, 새 일 목록 `runs/jobs_qv3r3_h0.json`, 잠금 아래) 뒤 H2(`decl/specs/jobs_A.json` 그대로, 태그 qv3r3h2).

## 2026-10-27 18:26 KST — P1 다시 시작 (r3): L0 와 명세 대조

- 정본: `PRE_VP_FIXED.md` 33e71ac3… + 고침 `PRE_VP_R3.md` 2c1d6cef… (둘 다 `.sha256` 과 같음 [실행]). 결정 기록 sha 64f20294… (367줄, 앞 344줄 b33fe5e7… 같음) [실행]. 이번 일은 P1(H3 9상태, s31 T=1,800 다시부터)과 그 뒤 L3·보고. 탐침 A·B(H2)는 다른 실행(Q-V3 이어 가기)이 같은 VP 에서 돌림 — 같은 시각 L0 기록 `selftest/*_qv3r3_L0_*` 가 보임 [실행 읽음]. 두 큐는 공유 잠금으로 차례.
- [실행] L0 (PRE_VP_R3 §3.1): `SHA256SUMS_VP_r3.txt` 87a21406… 54/54 OK, `SHA256SUMS_VP_EXT_r3.txt` 217c0538… 14/14 OK, `vp_treefields.py` 종료 0(모든 칸 참; 기록 `selftest/treefields_L0_p1r3_43144.json` 73aeca86…), 자체 시험 65/65 참(`selftest/selftest_L0_p1r3_43144.json` bc04fac6…). STOP_VP 없음, 공유 잠금 비어 있음, `plant_P` 안 폴더 0, 멈춘 상태는 `GT/out/interrupted/plant_P/` 에 있음. 디스크 C 19 GB, D 200 GB.
- [실행] L2 출력 대조(데이터 뒤 기계 생성물, P1_REPORT r1 JSON `steps.L2` 의 sha 와): `p1_inputs.json` dda66474…, `jobs_P.json` b6c75af5…, 명세 9개 모두 같음.
- H0 는 다시 돌리지 않음: r3 의 L0 가 `vp_treefields.py` 로 기록 칸을 대조하고, `vp_job.py` 가 일마다 기록 ok·튜닝 sha·gprep sha 를 봄. 기록 파일 sha 는 67e6681e3c1c30595b66… (17:32:39 그대로). **정정**: r1 보고 `P1_REPORT.md`·`QV3_REPORT.md` §9 에 이 sha 가 "67e6681e1c1c…" 로 잘못 적혀 있음(손으로 옮긴 글자 하나; 두 JSON 은 바른 값). 
- [실행] 큐 로그 `logs/plantP/queue.log`(dee98927…)는 큐가 끝에 덧붙이므로, 바이트 사본을 `report_p1/r2/queue_plantP_before_r3resume.log`(같은 sha)로 둠.

## 2026-10-27 18:26 KST — Q-V3 r3: H0 끝, H2 발사

- [실행] H0 (`runs/jobs_qv3r3_h0.json` d3ef5de8…, 태그 qv3r3h0, WMI PID 20000, 큐 pid 28012, 큐 sha 9145bd35… = r3 핀): 잠금 18:24:42–18:25:02, `vp_tree.py verify` 종료 0, 10,569 파일 빠짐 0·다름 0. 기록 `code_va.tree.json` 이 다시 써짐(1255496…; 시각 칸). `vp_treefields.py` 다시 종료 0(`selftest/treefields_qv3r3_H0_745612.json` c7628fc4…).
- [실행] H2 발사 18:25:20: `decl/specs/jobs_A.json`(b68e18f2…, 핀 그대로), 태그 qv3r3h2, WMI PID 38488, 큐 pid 43084, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움. 큐가 s31 T=3,300·3,450 을 `.done` 으로 건너뜀, 18:25:22 잠금(우리 마지막 해제 + 20 s) → A_v3c3-s31_T004050 시작.

## 2026-10-27 18:35 KST — H3 큐 다시 발사 (r3 도구)

- 바로 위 항목 머리의 "18:26" 은 어림이었음. 실제로 쓴 때는 18:24 KST.
- [실행] `vp_launch.ps1 -Jobs GT/out/p1_specs/jobs_P.json -Tag p1h3r3` 18:24:43 (WMI PID 30012, 큐 pid 11072, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움). 큐 sha 9145bd35… (r3 핀과 같음), jobs sha b6c75af5…. 발사 때 공유 잠금은 Q-V3 이어 가기의 `qv3r3_h0/tree_verify`(pid 28012) 것 — 그 실행이 H0 를 다시 돌림(`code_va.tree.json` 이 다시 써질 수 있음; 칸 대조는 그 전 18:23 에 끝냄).
- [실행] 첫 일 P_v3c3-s31_T001800: 잠금 18:31:05 (기다림 382 s), gprep 종료 0·이력 11/11, PROBE_START 18:31:07 (wu-link).

## 2026-10-27 18:40 KST — H3 1/9 끝: v3c3-s31 T=1,800 (다시 굴림)

- [실행] 잠금 18:31:05–18:38:48, 벽시계 463 s, 탐침 종료 0, `vp_jobcheck.py` 종료 0(걸림 0, `r1_objective_ok` 참). 훅 파일 13. probe.json 251150e8…, jobcheck.json a75b130b…, job_summary.json 3a27498b….
- [실행] 점검 칸: R1 목적값 비트 같음 거짓·차 +1.1368683772161603e-13 veh·h(r2 멈춤 때와 같은 값; r3 규칙 ≤ 1e-9 참), 비용 키 같음·최대 차 3.55e-15, R2 − R1 = −1.137e-13(스칼라 J 가 기록과 같아짐), R3 참, null 비트 같음 참, R0 거짓(보고만).

## 2026-10-27 18:58 KST — Q-V3 r3: H2 진행 (3상태 더 끝)

- [실행] `logs/plantA/queue.log`: A_v3c3-s31_T004050 (잠금 18:25:22–18:30:45, 323 s), A_v3c3-s31_T004800 (18:39:08–18:43:52, 284 s), A_v3c3-s41_T002400 (18:44:12–18:48:55, 283 s) 모두 종료 0, `vp_jobcheck.py`(r3) 걸림 0. A_v3c3-s41_T002550 18:56:38 시작.
- [실행] 같은 잠금을 P1 큐(pid 11072, 다른 실행)와 번갈아 씀: P1 s31 T=1,800 다시(18:31:05–18:38:48), T=5,400(18:49:15–18:56:18) 둘 다 jobcheck 종료 0 [실행 읽음 `logs/plantP/queue.log`]. 두 큐 모두 공유 `lock_last_release.json` 의 20 s 쉼을 지킴. STOP_VP 없음.
- R1 목적값 비트 같음이 거짓인 상태가 있음(r3 규칙에서는 보고만; 차는 보고서 표에 적음).

## 2026-10-27 19:37 KST — H3 3/9 끝 (s31 세 상태)

- [실행] P_v3c3-s31_T005400 잠금 18:49:15–18:56:18 (423 s) 종료 0·점검 걸림 0. P_v3c3-s31_T007200 잠금 19:27:48–19:36:39 (532 s) 종료 0·점검 걸림 0. 두 번째 일은 잠금을 1,889 s 기다림: Q-V3 큐(plantA, pid 43084)가 우리 해제 + 20 s 뒤 경합에서 여섯 번 연달아 먼저 잡음(규칙 위반 아님: 두 큐 모두 공유 `lock_last_release.json` 의 + 20 s 를 지킴) [실행 읽음 두 queue.log]. 끈 프로세스 0.

## 2026-10-27 19:45 KST — Q-V3 r3: H2 끝 (12/12), L3, 모음

- [실행] H2 큐(pid 43084) 19:41:44 QUEUE_END. 이 실행에서 돈 10상태: s31 T=4,050·4,800, s41 T=2,400·2,550·3,300·4,200, s43 T=2,700·2,850·3,750·5,100 — 모두 종료 0(벽시계 260–326 s), `vp_jobcheck.py`(r3) 걸림 0. 앞 실행의 s31 T=3,300·3,450 은 `.done` 으로 건너뜀(T=3,450 은 R3_MARKS 표시). STOP_VP 는 이 실행 내내 없었음. 큐 로그 `logs/plantA/queue.log` ae91b51d….
- [실행] 잠금: 우리 일 10개 + 다른 P1 큐 일 3개(s31 T=1,800·5,400·7,200)가 번갈아 잡음, 모든 다시 잡기가 마지막 해제 + 20 s 뒤. 이 시간 동안 vsl_plant 밖의 잠금 주인은 로그에 없음. 남의 프로세스 끄기 0, 우리 프로세스 끄기 0(워치독 안 걸림). 지금 우리 큐 프로세스 0(남은 것은 P1 실행의 큐 pid 11072 와 그 자식).
- [실행] R1(r3 규칙): 12상태 모두 목적값 |차| ≤ 1e-9·비용 ≤ 1e-9. 목적값 비트 다름 4상태(s31 T=4,050 −5.7e-14, s41 T=2,400 +5.7e-14, s41 T=3,300 −5.7e-14, s43 T=3,750 −1.7e-13 veh·h) — PRE_VP_R3 §1.1 대로 보고만. R3 12/12 비트 같음, REPACK 토큰 = REC 토큰 12/12.
- [실행] L3 (잠금 없음, 19:42): 고정 도구 `vp_analyze.py tables` → `GT/out/tables/vp_tables_qv3r3.json` 10b8cb32… / `.md` 890eb20c… (AB 12상태, 표 도구 "멈춤 규칙 걸림" AB 4건 = 위 R1 비트 다름 4건뿐). 선언 이름 `vp_tables.json` 은 쓰지 않음: 같은 시각 P1 실행이 아직 돌고 있어 그 파일을 두 실행이 덮어쓸 수 있기 때문(AB 부분은 plant_A·fzp_frames 만 읽음 [읽음 `vp_analyze.py`:248-323]). 이 파일의 P1 부분은 그 시각 P1 이 끝낸 3상태뿐이고 Q-V3 결과가 아님.
- [실행] 모음(데이터 뒤, 읽기만): 새 스크립트 `runs/qv3r3_collect.py` 616576a7… → `runs/qv3r3_collect.json` 1e547b6b…·`.md` 18649098… (r1 모음 `qv3_collect.py` 에 r3 칸·R3_MARKS 표시·멈춤 목록 r3 읽기·묶음별 범위만 더함). 핀 r3 다시 대조 19:42: 54/54·14/14, `vp_treefields.py` 종료 0. GWT8 HEAD c20aff1d, 작업 트리 변경 0 [실행 `git rev-parse`·`status --porcelain`].

## 2026-10-27 19:48 KST — Q-V3 r3: QV3_REPORT r2 씀, 보고 사본

- [실행] `QV3_REPORT.md` r2 sha256 6ad51eec6b51f7896b48d81b288464525e448a6da11d9269dedc408f43b4be02, `QV3_REPORT.json` 0b9d24ca6c7209ce60e1b2a84cfd94e852ea50eb347ec46455721cd5f86d5166 (상태 PASS = 12/12 끝·멈춤 규칙 걸림 0; 같은 이름 `.sha256`). JSON 은 읽기만 하는 `runs/qv3r3_report_json.py` 로 씀. r1 은 `QV3_REPORT_r1.md`(7e196d9f…)·`QV3_REPORT_r1.json`(3ce8c353…)로 바이트 그대로 둠(+ `.sha256`).
- 데이터 뒤 요지(보고 §0·§6): plant 100 의 ΔJ(− 110) 는 + 9상태·− 3상태(−0.145 ~ +0.918 veh·h/450 s), 90 은 12/12 +, 101 − 100 은 12/12 −. 4/6 VSL 결정 상태에서 ARM110 < REC(−0.035 ~ −0.628). plant − VISSIM: B1 +21 ~ +42 km/h(12/12), 셀 12 +52 ~ +63, VS0′ − 11/12, D −11 ~ −21(12/12). X1 = 0 모두.
- 보고 사본 RVP(`D:/VISSIM_runs/20261001_v3c3/reports/k8/vsl_plant`): QV3_REPORT.md·.json(+ .sha256), QV3_REPORT_r1.md·.json(+ .sha256), LOG.md, vp_tables_qv3r3.md, qv3r3_collect.md.
- 남은 사용자 선택: O1–O5 (보고 §7). P1(Q-V4) 은 따로 도는 실행이 이어 감(이 시각 그 큐가 잠금 사용 중, 손대지 않음).

## 2026-10-27 20:07 KST — H3 5/9 끝

- [실행] P_v3c3-s41_T001800 잠금 19:42:03–19:50:06 (482 s), P_v3c3-s41_T005400 잠금 19:57:56–20:06:21 (506 s; 그 앞 19:50–19:57 은 다른 워크플로 `fo_declare` 가 잠금). 둘 다 종료 0·점검 걸림 0. Q-V3 큐(plantA)는 19:42 무렵 남은 일을 마침 [실행 읽음 plantA queue.log].
- [실행] 중간에 고정 표 도구를 임시 이름(`report_p1/r2/tmp/partial_13856.*`)으로 한 번 돌려 출력 꼴을 봄(그때 끝난 P1 3상태). 규칙·문턱·도구 바꾸기 0.

## 2026-10-27 20:48 KST — P1: H3 9/9 끝, L3, P1_REPORT r2

- [실행] H3 남은 상태: s41 T=7,200 (20:06:41–20:15:31, 530 s), s43 T=1,800 (20:15:51–20:24:40, 529 s), s43 T=5,400 (20:25:00–20:32:44, 464 s), s43 T=7,200 (20:33:04–20:40:28, 444 s). 9상태 모두 탐침 종료 0, `vp_jobcheck.py` 걸림 0, 모든 `r1_objective_ok` 참, R3·null 비트 같음 9/9, 도달 점검 90/90 참. 큐 QUEUE_END 20:40:28, STOP_VP 0. R1 목적값 비트 다름 2상태(s31 T=1,800 +1.137e-13 = 2 ULP, s43 T=1,800 +5.68e-14 = 1 ULP; r3 규칙 안).
- [실행] 뒤 대조 20:40:53: 핀 r3 54/54·14/14, `vp_treefields.py` 종료 0, PRE 두 문서 sha 같음, 바이트코드 파일 0.
- [실행] L3: 고정 표 도구 `vp_analyze.py tables`(a3638816…) → `GT/out/tables/vp_tables_p1r3.json` b0ef5584…, `.md` 328c00f3… (선언 이름 `vp_tables.*` 대신 P1 이름; Q-V3 실행이 `vp_tables_qv3r3.*` 를 쓴 것과 겹치지 않게). "멈춤 규칙 걸림" 2건은 모두 `R1_objective_bit_equal` → PRE_VP_R3 §1.1 읽는 법으로 R1 비트 보고.
- [실행] 규칙 적용(데이터 뒤 해석 없이): 가리킴 규칙 충족 = C4 → VSa·VS0′ 속도, C9 → VSa·VS0′ 속도, C1 → M1 속도(고정 문구대로면 "방향 근거 없음" 표시; 방향 칸 +2.76 km/h 인데 C1 은 M1 에서 v_free 를 내렸음 → 사용자 질문 Q1). 중앙 R ≤ −0.2 = C2 → M1, C9 → M1. VSb 재고·속도 = 목록 밖 항에 남음, X1 ≥ 1 veh 0/9(네 출구).
- [실행] r1 보존: `P1_REPORT_r1.md` c28c9178…, `P1_REPORT_r1.json` 59b67ad6…(+ `.sha256` 사본 둘, 안의 이름 칸은 원래 이름). 새 보고 `P1_REPORT.md` 81659e8b…, `P1_REPORT.json` 902ce8c8…(일회용 읽기 스크립트 `report_p1/r2/p1_report_r2_json.py` 18483656…·`p1_report_r2_final.py` e9b7953a…; 모음 출력 `p1_report_r2_collect.json` 97be1c40…).
- 정정 기록: r1 보고 md 두 개의 `code_va.tree.json` sha 글자 하나(1c1c → 3c1c), 18:24 항목에 적은 것과 같음.
- VISSIM·COM·러너·동결 0, GWT8·FRZ_K92·런 폴더 쓰기 0, 도구 고침 0, 끈 프로세스 0. 보고 사본: RVP 에 P1_REPORT r2·r1, 표 p1r3, LOG.md.

## 2026-10-27 21:03 KST — 종합 VP_RESULTS 씀 (Q-V3·Q-V4, 데이터 뒤)

- [실행] 시작 점검 20:52–20:56: 핀 r3 `SHA256SUMS_VP_r3.txt` 54/54·`SHA256SUMS_VP_EXT_r3.txt` 14/14 같음, `STOP_VP` 없음, 공유 잠금 파일 없음, GWT8 HEAD c20aff1d·`status --porcelain` 0줄. 근거 보고 sha: QV3_REPORT.md r2 6ad51eec…, P1_REPORT.md r2 81659e8b…, 표 vp_tables_qv3r3.json 10b8cb32…·vp_tables_p1r3.json b0ef5584….
- [실행] 새 읽기 전용 스크립트 `runs/vp_results_extract.py`(ff05e92d…) → `runs/vp_results_extract.json`(fd12c111…): 고정 표 도구 출력 두 개만 읽음(plant 굴림·FZP 스캔·잠금 0). 낸 것(데이터 뒤): P1 9상태 기준 굴림의 모든 구역·셀 11–13·18 편향, 탐침 A 100 팔 VSL 반응 대 EXEC 편향 크기, 팔별 FW_E 입구 대기(절대값), 팔별 구역 veh·h 차. 임시 출력 이름에 PID 붙임.
- [실행, 데이터 뒤] 요지: VSL 끔 9상태에서 B1 +7.8 ~ +36.0 km/h(9/9), 셀 12 +23.1 ~ +63.9, D −7.4 ~ −15.1(9/9) — 탐침 B 12상태와 같은 부호(21/21). VSL 반응 대 편향 |e|/|반응| 중앙 VSa 5.4·VS0′ 13.4·VSb 6.0·M1 0.5. plant FW_E 입구 대기 12상태 × 4팔 모두 0.0. 100 팔 구역 veh·h 차는 M1 +0.598·VSb +0.213 중앙, U < 0.001.
- [실행 읽음] P1 훅 파일(상태마다 13개)에 블록별 31셀 적분 칸(n_dt·nv_dt·q_dt)이 있음 — 항 뺀 굴림의 B1·D 값은 새 굴림 없이 낼 수 있음(사용자 결정 2 의 (가)).
- 씀: `VP_RESULTS.md` f7f105fe5c2f5d11499e3c631513a8747af7fe57ffaf50c2142661b3ca806681 (+ `.sha256`). 사용자 결정 9개(§3). 보고 사본 RVP: VP_RESULTS.md(+ .sha256), vp_results_extract.py·.json, LOG.md.
- VISSIM·COM·러너·동결 0, 무거운 일·잠금 0, 코드·도구·규칙 바꾸기 0, GWT8·동결 트리·런 폴더 쓰기 0, 프로세스 끄기 0, 봉인 시드·64cf-s59/s61/s67·v3c3-s47 0.

## 2026-10-27 21:16 KST — 검증 VERIFY_VP 시작: 검증 도구 고정 (원자료 값 읽기 전)

- 대상: `VP_RESULTS.md` r1 sha256 f7f105fe5c2f5d11499e3c631513a8747af7fe57ffaf50c2142661b3ca806681 [실행 다시 셈, .sha256 과 같음].
- [실행] 시작 점검: 핀 r3 `SHA256SUMS_VP_r3.txt` 54/54, `SHA256SUMS_VP_EXT_r3.txt` 14/14 OK. VP_RESULTS §4 의 sha 26개 모두 다시 셈과 같음. STOP_VP 없음, 공유 잠금 파일 없음. GWT8 HEAD c20aff1d, `status --porcelain` 0줄. 디스크 C 16.2 GB, D 194.5 GB.
- 검증 도구(새로 씀, 생산자 도구·모음 스크립트를 import 하지 않음; 정의는 PRE_VP_FIXED §3.3·§4.2–4.3·§5.2–5.4 에서 다시 구현). 핀 `verify/SHA256SUMS_VV.txt` sha256 4b7e2c9bbf82594e11b18079f78af494cf91e9626b1cc47132ce01ead0a1fe17:
  - `verify/tools/vv_recompute.py` 1ea982fc11e4943fadef1f1ff6cbc20b3aa1418815ed4d18ee10e40c695fbe96 (원자료 → 모든 숫자 다시 셈)
  - `verify/tools/vv_claims.py` 21c64db724b8e92954bc2e04fb381f50e2d428a7af842df4bc0d41c2a28ab426 (VP_RESULTS r1 글의 숫자를 손으로 옮겨 적은 기대값 ↔ 다시 셈; 표시 자릿수 반올림 허용)
  - `verify/tools/vv_bitcompare.py` 36243a6a1be0e372893b815cd69d844c23da4b6a4a13cab0f997d6712291d455 (다시 굴린 일 ↔ 원래 일, 목적값·비용 20·토큰·훅 블록·훅 first 비트 같음)
  - `verify/tools/vv_queue.py` e1953877a241c702ffb22e4c3bd831906d797e745513e7d3449d784a5bfd6ddc, `verify/tools/vv_launch.ps1` bd972a343f6721929d76766f59f2ce777dec58a5012bc07a66f46831e0a1aebf (생산자 `vp_job.py`(2164f97e…)·`vp_probe.py`(81925375…)·훅(b498eee0…)·`vp_common` 잠금 함수 그대로 부름; jobcheck·STOP_VP 는 쓰지 않음 — P 명세가 절제 하나뿐이라 생산자 점검이 빠진 절제 8개를 걸림으로 셈)
  - `verify/tools/vv_make_spec.py` d30e7290d215faf5c6d3d7319cf473efebe6d5f8a15e6c7555169a37b41b3c9b → 명세 `GT/verify/specs/spec_P_v3c3-s41_T005400_C9only.json` afc9d0772991b0e0357dee6ffbef1663e10475a34ed81382fe97313f3bbc411b (생산자 명세에서 절제 C9_lanedrop_both 만 남김, 나머지 칸 같음 [실행 대조])
  - `verify/jobs_vv.json` a527b85510c76749723a225ea827eed9e114208d79d33ebd3041aee8131abccf
- 고정한 다시 굴림 (데이터 전 선택, 바꾸지 않음): (1) 탐침 A 상태 v3c3-s31 T=4,050 (A3, 원래 명세 그대로, VP_RESULTS §0 2번·§1.1 굵은 줄의 근거) → `GT/verify/plant_A/v3c3-s31_T004050`. (2) P1 절제 C9_lanedrop_both 한 개, 상태 v3c3-s41 T=5,400 (도구가 null 을 늘 함께 돎) → `GT/verify/plant_P/v3c3-s41_T005400_C9only`. 판단 기준 = vv_bitcompare 의 모든 칸 비트 같음(요청 sha 같음은 보고만). 다르면 멈추고 보고.
- 이 기록 전에 본 것: 원자료 파일의 키 구조·실행 메타(토큰·요청 sha·배치 이름·벽시계)와 C1·C7 명세 입력 일부. 원자료의 J·편향·속도 값은 아직 계산하지 않았음. VP_RESULTS 의 숫자는 기대값으로 vv_claims.py 에 옮겨 적음.
- 무거운 일은 두 개뿐(공유 잠금 아래, WMI 분리, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움, 폴링 ≤ 9 분). VISSIM·COM·러너·동결 0, 코드·생산자 도구·규칙 고침 0.

## 2026-10-27 21:26 KST — 검증: 다시 셈 결과, 탐침 A 다시 굴림, 사전 고정 기준 어긋남 → 멈춤 (데이터 뒤)

- [실행] 다시 셈 `verify/out/vv_recompute.json` 91f95eda… (21:16, 잠금 없음, 원자료만 읽음). 대조 `verify/out/vv_claims.json` 06fd2cb4…: VP_RESULTS r1 숫자 553개 중 551개 같음. 다른 둘: §1.4 12상태 VSb + 수(글 8, 셈 9; v3c3-s43 T=3,750 이 +0.032), §1.4 셀 12 저밀도 FD 차(글 +9.0, 셈 +8.936; 표 반올림 값끼리 뺀 값). 대조표 밖: §1.2 90 팔 U 중앙(글 +0.001, 셈 0.000283).
- [실행, 데이터 뒤] 새 읽기 도구 `verify/tools/vv_extra.py` 120f5e44… → `verify/out/vv_extra.json` 26bb1b9a…: 21작업 훅 194개 모두 X1 0.0. w450 VISSIM 셀 18 − 셀 16–17: VSL 끔 9상태 중 v3c3-s41 T=1,800 만 −16.4 km/h(나머지 −1.7 ~ +1.7), 탐침 B A1·A2 6상태 −6.0 ~ −22.2. C9 뒤 VS0′ +15.1 과 C8 R 최소는 둘 다 v3c3-s41 T=1,800.
- [실행] 다시 굴림 큐(WMI PID 50656, 큐 pid 47852, BELOW_NORMAL, PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS 지움): 탐침 A v3c3-s31 T=4,050 — 잠금 21:19:23–21:24:06(다른 워크플로 fo_gate 뒤 180 s 기다림), vp_job 종료 0, 284 s. probe.json 62545e8e…, 훅 6개. `vv_bitcompare.py` → `verify/out/vv_bitcompare_A.json` f79574ff…: 평가 8개 모두 목적값·비용 20·action 토큰·훅 블록·훅 first·걸음 비트 같음, 계획 7개·기록·점검 칸 같음. **response_token 8/8 다름**(요청 sha 도 다름 — 보고만 칸).
- [실행 읽음] response_token 은 응답 요약 해시이고 요청 틀 문맥 토큰을 담음(code_va sdmpc_tangent_surrogate.py:50·:66·:122). 같은 폴더에서 두 번 돈 생산자 P s31 T=1,800(r2 멈춤판과 r3) 은 요청 sha·response_token 모두 같았고, 다른 폴더 smoke v1–v5 는 같은 계획 같은 목적값에 response_token 이 매번 달랐음 → 작업 폴더 경로에서 온 차로 봄 [추론].
- 사전 고정 기준(위 항목: "모든 칸 비트 같음, 요청 sha 만 보고, 다르면 멈추고 보고")을 데이터 뒤에 바꾸지 않음 → **멈춤**. P1 절제 C9 다시 굴림은 잠금을 기다리던 중이라 우리 큐(pid 47852, 자식 없음, 잠금 안 가짐)를 21:26 에 끝냄. 공유 잠금은 그때 fo_gate 것이었고 손대지 않음. 끈 프로세스는 우리 것 둘(47852, 그 부모 cmd 50656 은 따라 끝남)뿐. P1 다시 굴림 출력 0.
- 사용자 결정 대기: response_token 을 보고만 칸으로 둘지, P1 절제 다시 굴림을 돌릴지 (VERIFY_VP §5).

## 2026-10-27 21:29 KST — 검증 VERIFY_VP 마감 (멈춤 상태, 사용자 결정 대기)

- 정정: 바로 위 항목의 "우리 큐를 21:26 에 끝냄" 은 어림. 실제는 21:25:43 KST(Stop-Process 출력 시각).
- [실행, 데이터 뒤] 새 읽기 도구 `verify/tools/vv_token_check.py` 654db535… → `verify/out/vv_token_check.json` bd3e9c3d…: 같은 폴더 두 번(P s31 T=1,800 r2·r3) 요청 sha·response_token 같음, 다른 폴더 다섯 번(smoke v1–v5) response_token 5가지·목적값 1가지.
- 씀: `VP_RESULTS.md` r2 118f91fd7506a997bac04daf776a86ad3c76730d7f1b3535f75efa58d192ae88 (+ .sha256; r1 은 `VP_RESULTS_r1.md` f7f105fe… + .sha256). 고침 F1–F8 (VERIFY_VP §4). `VERIFY_VP.md` 390d3510a0db2673eb142a7cc7972677938137383234358fb840da2bbe90399f (+ .sha256).
- [실행] 끝 점검 21:29: 핀 r3 54/54·14/14, 검증 핀 SHA256SUMS_VV 8/8, STOP_VP 없음(검증은 STOP_VP 를 쓰지 않음), 공유 잠금 = fo_gate 것(우리 것 아님), 우리 프로세스 0, 바이트코드 0, GWT8 HEAD c20aff1d·작업 트리 변경 0.
- 사용자 결정 V1(response_token 보고만?), V2(P1 절제 C9 다시 굴림?), V3(r2 고침 받아들임?) — 권장은 모두 (가). VP_RESULTS §3 결정 1–9 그대로 열림.
- 보고 사본: RVP 에 VP_RESULTS.md r2·VP_RESULTS_r1.md(+ .sha256), VERIFY_VP.md(+ .sha256), LOG.md, `verify/`(도구·출력·핀·큐 로그).
