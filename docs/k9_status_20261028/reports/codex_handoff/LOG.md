# codex handoff 검토 로그 (R_CLAIMS 담당)

## 2026-10-24 19:33 KST
- 디스크: C 33.9 GB, D 333.9 GB 여유 [실행].
- 공유 worktree D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff 가 없어 생성 시도. 'Filename too long' 7건(diagnostics/.../baseline_reproduction_20260929 하위 긴 경로)으로 'fatal: Could not reset index file' 로 끝남 [실행]. worktree 는 등록됨(locked 표시), 체크아웃은 부분적(최상위에 diagnostics, HANDOFF.md 등만). 지우지 않음(규칙).
- 대신 `git archive a49981ff handoff HANDOFF.md SHA256SUMS.txt | tar -x` 로 scratchpad/k8/codex_handoff/work/tree 에 읽기용 사본 추출 [실행]. 저장소·브랜치 변경 없음.

## 2026-10-24 19:35 KST — R_MECH 에이전트 시작
- 디스크: C 33.9 GB, D 333.9 GB 여유 [실행].
- 공유 worktree D:/VISSIM-merge/k8_gate_trees/codexhandoff/a49981ff 생성. 첫 시도는 'Filename too long' 로 git 이 스스로 정리(폴더 없음). 두 번째는 `git -c core.longpaths=true worktree add --detach ...` (명령 한 번에만 적용, config 미변경) 로 성공, HEAD a49981ff [실행].
- HANDOFF.md sha256 e2cef38c… 일치 [실행].
- 트리 구조: 루트 = 코드 루트(code/ 폴더 없음). handoff/evidence/ 에 작은 근거 파일 [실행].
- 19:37 KST (R_MECH) 확인: 지금 worktree 는 완전 체크아웃, `git -c core.longpaths=true status --short` 빈 출력(깨끗함), locked 아님 [실행]. 다른 에이전트도 이 경로를 그대로 읽어도 됨. 긴 경로 파일은 core.longpaths 없이 열면 실패할 수 있음.

## 2026-10-24 19:39 KST — R_CLAIMS 에이전트 (재시작분) 시작
- 디스크: C 33.9 GB, D 333.7 GB 여유 [실행].
- 공유 worktree 존재·HEAD a49981ff 확인, HANDOFF.md sha256 e2cef38c… 일치 [실행]. 이 에이전트는 worktree 를 읽기만 함.
- 작업 폴더: work/claims/ (앞선 R_CLAIMS 시도의 work/a1~a3*.py 는 건드리지 않음).
- 19:55 KST 무렵 (R_MECH) 읽기 끝: codex 트리(CX)·GWT8 c20aff1d(OU)의 sdmpc·physical_ramp_branches·lane_plant_runtime·urban_storage_guard·route_choice_corridor·head_service_resources·runtime_setup·adapter, 두 설정(c9088262 / c8e3ee2c) 잎 비교(195개 차이), plant reference 두 벌, Ω 소속 파일 두 벌 [실행]. 작업 파일은 scratchpad/k8/codex_handoff/work/mech/ (cfgdiff.py, pathcmp.py, cfggroup.py, cfg_leaf_diff.csv). VISSIM·COM·러너·재생·커밋·푸시 0, codex 감사 스크립트 실행 0, sealed/ 열기 0.
- (R_MECH) HANDOFF.md:46 의 NC HEAD 는 43자리("…abbc29b0a7b")입니다. 실제 커밋은 886a014a303dd155e05cc33041796822abbc29b0 (40자리) [실행 git cat-file].

## 2026-10-24 19:52 KST — R_NET 에이전트 (망·이식) 기록
- 시작 19:33 KST 무렵. 디스크: C 34 GB, D 334 GB 여유 [실행].
- 공유 worktree 는 다른 에이전트가 만든 것을 읽기만 함. 이 에이전트는 worktree add 를 실행하지 않음(실행 조건 검사 때 이미 폴더 있음) [실행]. HANDOFF.md sha256 e2cef38c… 일치 [실행].
- 작업 폴더: work/net/ (inv.py·inv2.py·det1–4.py·dem.py·anc.py·anc2.py·geo.py·pack.py·refs.py 와 출력 json). 우리 옛 망(v2nc·v3bnc·v3c1nc·rampdsd_src)은 `git show` 로 work/net/ 에 꺼냄. v3cnc·v3c2nc 는 D:/VISSIM_runs 의 s31 사본만 읽음(s37 등 봉인 시드 폴더는 열지 않음).
- codex 함수 실행 1건: diagnostics/build_control_area_membership.py 를 work/net/omega/bcam_codex.py 로 복사해 ROOT 만 바꾸고 `python -B` 로 Ω701 재유도(64cf·v3c3 두 망). 실행 뒤 worktree `git status --short --ignored` 0줄 [실행].
- VISSIM·COM·러너·재생·동결·커밋·푸시 0. sealed/ 열기 0. 봉인 시드 수치 인용 0.
- 19:41–19:53 KST (R_CLAIMS) [실행] evidence SHA256SUMS 23/23 일치(CRLF 제거 후), SOURCE_FILES 3,638/3,638 일치(긴 경로 5개는 git show), 핵심 20개 파일 sha 일치, native_seed29.inpx = 64cf5f55….
- [실행] work/claims/c1_metrics.py(백분율·분할 항등식), c2_actions.py(RM·유지·TSC), c3_tsc.py(offset·녹색합), c4_latent.py(NC 미삽입 0–8100 범위 추론). 모두 읽기 전용, 저장소에 쓰지 않음.
- [실행] 읽기 전용 git(cat-file/show/diff) 로 GWT8 저장소 객체에서 886a014a·ca181e84 의 VBS 등 비교. GWT8 작업 트리·브랜치 변경 없음.
- 봉인 시드 자료·sealed/ 열지 않음. v3c3_scan.json 안 봉인 시드 경로 문자열은 인용하지 않음.

## 2026-10-24 19:56 KST — R_MECH 끝
- R_MECH.md r1 sha256 2fc879d62760621f9e40df92774fe4f74eb29fc9ce8edaf08360d3eaab0434e5 (267 줄) [실행].
- 작업 파일 sha256: cfg_leaf_diff.csv 34dcc4916d3e5b68…, cfgdiff.py d74502a1d2fd2665…, pathcmp.py f3ce6b54693a4968…, cfggroup.py cac4f62fbb6ccf58… [실행].
- 디스크 끝: C/D 여유 확인은 시작 때 33.9/333.9 GB, 이 단계에서 쓴 양은 수 MB(worktree 약 105 MB 별도).
- VISSIM·COM·러너·재생·커밋·푸시·동결 0, sealed/ 0, 봉인 시드 0, codex 64cf-s59/s61/s67 숫자 0, kill 0.
- 19:57 KST (R_CLAIMS) R_CLAIMS.md r1 작성 완료. sha256 2a3a4ea5ad39febf8e4220966b2424d8514529cda5a5d79c95c7c44f47adfc48. 디스크 C 34 GB, D 334 GB 여유 [실행].
- 2026-10-24 19:57 KST (R_NET) 끝: R_NET.md sha256 f1e15b749c62ed333e96df2cb69beee6acff82cd5808a09f3a07b83009bd1f46 (291줄). 작업 산출물 sha 목록 work/net/SHA256SUMS_R_NET.txt. 핵심: 64cf = v2 경로 세대 + 5편집(v3c3 후손 아님), 기하·신호·.sig 같음, Ω701 은 v3c3 에서 재유도해도 같은 701 링크, codex 판은 v3c3 에서 그대로는 설정 단계 예외(러너 sha·계약 sha·sign cell 16 대 18), 1099 미삽입 지체가 망 안 TTT 의 약 2배. worktree git status --ignored 0줄 재확인.

## 2026-10-24 20:07 KST — TAKEOVER_PLAN (종합) 끝
- 입력: R_CLAIMS r1 2a3a4ea5…, R_MECH r1 2fc879d6…, R_NET f1e15b74…, HANDOFF 사본 e2cef38c…, VA r3 b57022e6…, MC r2 0b4036c6…, MN2 r2 acebbe73…, K93 r2 549f20e2…, W264_READ r2 8db20647…, NOTES 8a7ce78c… [실행 sha256sum].
- 디스크 시작 때 C 33.9 GB, D 333.6 GB 여유 [실행].
- CX worktree: git rev-parse·status(0줄)·설정 JSON 키 읽기 1회(/runtime/decision_timeout_sec = 1800, /runtime/decision_error_policy = hold_previous) [실행]. 쓰기 0. GWT8 은 rev-parse 만(c20aff1d).
- TAKEOVER_PLAN.md sha256 39c292330e3e6e164616041dab203dcbfd5b13aa3adc9991a169c05015b0c4e8 (244줄).
- VISSIM·COM·러너·재생·동결·커밋·푸시 0, codex 감사 스크립트 0, sealed/ 0, 봉인 시드 0, codex 64cf-s59/s61/s67 숫자 0, kill 0.

## 2026-10-24 20:10 KST — VERIFY_TAKEOVER 에이전트 시작
- 디스크: C 33.9 GB, D 333.4 GB 여유 [실행].
- 대상: TAKEOVER_PLAN.md(39c29233… 예정 확인), R_CLAIMS·R_MECH·R_NET. 작업 폴더 work/verify/. 공유 worktree 는 읽기만.


## 2026-10-24 20:30 KST — VERIFY_TAKEOVER 끝
- VERIFY_TAKEOVER.md r1 sha256 c5e98d9e33e37bdbc0e3ab1a56b26e497a185002b5cac1ab41080d1e66e3b2e2 (249줄). 작업 산출물 sha 목록 work/verify/SHA256SUMS_VERIFY.txt.
- 입력 sha 확인: TP 39c29233…, RC 2a3a4ea5…, RX 2fc879d6…, RN f1e15b74…, HO e2cef38c… [실행].
- [실행] 새 스크립트 v1–v9: evidence 백분율·VSL/RM/TSC 개수 전부 같음. 망 차이(입력 1099 하나, 경로 8+23, DSD 110·81/91/101, DSD 63–66 위치, .sig 42 같음) 같음. TP §0-7 "1099 2.06–2.27배" 는 1.84–2.27배(합 2.07)로 고칠 것.
- [실행] 우리 로컬 무제어 런 D:/VISSIM_runs/vsl_repro_s29/none/run(64cf-s29, 09-24) 이 codex NC 와 같음: FZP 6,475,075행, 895.1 s 까지 431,233행 LF sha256 f1a0b040…cbda, ①·②·Ω701·④a 차 0, native 합계 같음. 이 런으로 NC ④b(0–8100) ≈ 16,638±10 → joint−NC: Ω701 −494.7 / ④ ≈ −663 / Ω 밖 (a) ≈ −168 (64cf-s29 한 시드).
- [실행] W264 결정 벽시계(VBS 로그) 평균 1,709 s, 55 중 12개 > 1,800 s → TP Q5 "시한 1800 그대로(HO 와 같은 조건)" 와 A1 새 NC 필요 주장 반박. 고칠 문장은 VERIFY §5.
- FZP 읽기 3회(로컬 1.18 GB, 각 7–12 s, 한 번에 하나). 공유 worktree·GWT8 git status 0줄 재확인.
- VISSIM·COM·러너·재생·동결·커밋·푸시 0, codex 감사 스크립트 0, sealed/ 0, 봉인 시드 0, codex 64cf-s59/s61/s67 숫자 0, kill 0.
- 디스크 끝: C 33.9 GB, D 333 GB 여유 [실행].

## 2026-10-24 20:34 KST — TAKEOVER_PLAN r2 (Finalize) 시작
- 디스크: C 34 GB, D 334 GB 여유 [실행].
- 입력 sha 확인: TP r1 39c29233…, VERIFY r1 c5e98d9e…, RC 2a3a4ea5…, RX 2fc879d6…, RN f1e15b74… [실행].
- r1 보존: TAKEOVER_PLAN_r1.md = r1 바이트 그대로(sha 39c29233…) [실행 cp -p].
- 점검 [실행]: W264 runlog CONTROLLER_DECISION(sim_sec ≥ 900) 55개 wall_sec 평균 1,709.1 / 중앙 1,720.5 / 최대 2,172.2 / 최소 1,145.3 / 1,800 초과 12 — VERIFY 와 같음. CX preparation.json /validation_reused/full_selection_sec = 219.509, full_selection_converged = False. VERIFY v3·v6–v9 출력 값 다시 읽음(같음). CX git status 0줄.
- [실행] TAKEOVER_PLAN.md r2 작성(316줄). VT §5 #1–27 과 §5.1 고침을 모두 반영, 반박·근거 부족 문장은 본문에서 지우고 §8 변경 기록에만 인용. 세 보고 고침은 TP §6 표로 대체(보고 파일 자체는 r1 그대로).
- VT 밖 다듬기 [실행]: 9000 s codex 코드 런 "약 26–28 h" → W264 실측 28.3 h 에 맞춰 "약 28 h"; 8100 s "약 24–25 h"(48결정 합 82,709 s + 약 7,000 s); 새 결정 Q5c(결정 시한, A0 뒤).
- 산출물: TAKEOVER_PLAN.md r2 sha256 b75ad0418fa08dc0d0b64b70ffdd3c82e2ea101ab7ee73e75e27a67ab7482144; TAKEOVER_PLAN_r1.md sha256 39c292330e3e6e164616041dab203dcbfd5b13aa3adc9991a169c05015b0c4e8.
- CX git status 0줄 재확인. VISSIM·COM·러너·재생·동결·커밋·푸시 0, codex 감사 스크립트 0, sealed/ 0, 봉인 시드 0, codex 64cf-s59/s61/s67 숫자 0, kill 0. 디스크 끝 C 34 GB, D 333 GB 여유.

## 2026-10-24 20:39 KST — TAKEOVER_PLAN r2 끝
- 변경 기록 시각 줄 고침(20:50 → 20:39) 뒤 최종 sha256 위 값.

## 2026-10-25 00:29 KST — 원본 사본 복사+검증 (Copy+verify) 시작
- 디스크: C 34 GB, D 330 GB 여유 [실행]. 복사 예정량 약 41.4 GB(sealed/ 제외).
- 공유 드라이브 Y:/99_임시휴지통/20261024 는 읽기만. 이름·크기 목록만 훑음(sealed/ 안으로는 안 들어감) [실행 raw/source_scan.py → raw/source_scan.json]: sealed/ 밖 파일 13,380개 / 41,370,811,521 B, 그 안 SHA256SUMS.txt 1,023개, 하위 폴더 중 이름이 sealed 인 것 0개(그래서 /XD sealed 는 맨 위 sealed/ 하나만 뺀다).
- FILE_MANIFEST.csv(목록표) 14,722행 중 sealed/ 행 2,398개는 건너뜀(이름은 출력 안 함). sealed/ 밖 행 12,324개 / 41,351,610,348 B. 목록표에 SHA256SUMS.txt·FILE_MANIFEST.csv·publication_receipt.json·code/.git/ 는 없음(목록표 밖 파일 1,056개) [실행].
- WMI(Win32_Process.Create) 발사 시험: 새 프로세스가 Y:·D: 를 보고 우선순위 BelowNormal [실행 raw/probe_wmi.txt].
- robocopy 발사 00:29:43 KST, 래퍼 PID 29796, robocopy PID 34160(기본 우선순위 6 = BELOW_NORMAL) [실행]. 명령 그대로:
  robocopy.exe Y:/99_임시휴지통/20261024 D:/VISSIM_handoff/20261024 /E /XD sealed /COPY:DAT /DCOPY:T /R:3 /W:10 /MT:8 /NP /BYTES /XJ /UNILOG:<scratch>/k8/codex_handoff/raw/robocopy_20261025.log
  (실제 인자는 역슬래시 경로. 정확한 문자열은 raw/robocopy_state.json "command".)
- 01:28:36 KST robocopy 끝. 종료 코드 1(= 새 파일 복사 성공, 0–7 범위) [실행 raw/robocopy_state.json]. 걸린 시간 3,533 s(00:29:43 → 01:28:36).
- robocopy 요약 [실행 raw/robocopy_20261025.log, sha256 572447cb…]: 디렉터리 1,044 중 복사 1,043 / 건너뜀 1(= sealed) / 실패 0. 파일 13,380 복사 13,380 / 실패 0. 바이트 41,370,811,521 복사, 실패 0. 원본 이름 목록(source_scan)의 13,380개·41,370,811,521 B 와 같음. 로그에 robocopy 오류 줄 0(“실패” 는 요약 머리줄 하나뿐).
- 속도가 느린 이유: 이 PC 유선 랜 연결 속도가 100 Mbps(약 11.7 MB/s) [실행 Get-NetAdapter·네트워크 카운터]. robocopy 평균 13.18 MB/s.
- D:/VISSIM_handoff/20261024/sealed 없음 [실행 Test-Path].
- 01:29:21 KST 검증 발사: WMI, 래퍼 PID 42928, python PID 25548(기본 우선순위 6 = BELOW_NORMAL), PYTHONHASHSEED=0·PYTHONUTF8=1·OMP/OPENBLAS/MKL_NUM_THREADS=1, python -B raw/verify_manifest.py [실행]. 가짜 작은 트리로 먼저 시험(work/verifytest/: ok·크기 차이·해시 차이·없음·sealed 건너뜀 모두 맞게 나옴) [실행].
- 01:36:19 KST 검증 끝. 종료 코드 0, 417 s(01:29:22 → 01:36:19), 해시한 양 13,348 파일 / 41,355,040,320 B, 평균 99 MB/s [실행 raw/verify_state.json·verify_manifest.json].
- 목록표(FILE_MANIFEST.csv) [실행]: 전체 14,722행 중 sealed/ 2,398행 건너뜀(열지 않음). 나머지 12,324행: 일치 12,324 / 크기 다름 0 / 해시 다름 0 / 없음 0. 일치 바이트 41,351,610,348 B(= 목록표 합).
- 목록표 자체 [실행]: 로컬 FILE_MANIFEST.csv sha256 c26f0b18…(2,192,204 B) = 공유 드라이브 사본 = 맨 위 SHA256SUMS.txt 기재값. 맨 위 SHA256SUMS.txt(1,338 B, sha256 15946d8c…) 로컬 = 공유.
- 폴더별 SHA256SUMS.txt [실행]: sealed/ 밖 1,023개, 항목 13,348개 전부 일치, 없음 0, 형식 오류 0. sealed/ 를 가리키는 항목 1개(맨 위 파일의 sealed/SHA256SUMS.txt 줄)는 건너뜀.
- 어디에도 안 실린 파일 31개(code/.git/*, 15,769,863 B)는 로컬과 공유 드라이브 해시를 직접 비교: 31/31 같음 [실행 raw/verify_unlisted.json].
- 로컬 사본 전체: 파일 13,380 / 41,370,811,521 B, sealed/ 없음 [실행].
- 산출물 sha256: verify_manifest.json 3c368b29…(4,505,520 B), verify_manifest.py 878c68e8…, verify_unlisted.json 8f35d9cd…, verify_unlisted.py 3c88b055…, run_robocopy.ps1 c3321716…, run_verify.ps1 e281dadf…, robocopy_state.json fc2c77d1…, verify_state.json 2ec132a5…, source_scan.json 7c47511c…, robocopy_20261025.log 572447cb… [실행].
- 내 프로세스(29796·34160·42928·25548·4824) 모두 스스로 끝남. kill 0. 공유 드라이브 쓰기 0. sealed/ 열기·해시 0(PATHS.txt 포함). VISSIM·COM·러너·재생·커밋·푸시 0, codex 스크립트 실행 0, 봉인 시드 숫자 0. GWT8·동결 트리·codex worktree 접근 0.
- 디스크 끝: C 34 GB, D 290.9 GB 여유 [실행].

## 2026-10-25 01:38 KST — Ω701 재집계(OMEGA701_V3C3) 에이전트 시작
- 디스크: C 34 GB, D 290.9 GB 여유 [실행].
- 대상: 우리 v3c3 9런(V-A s31/41/43, J1 s31r/41/43, NC3 s31/41/43) FZP. 작업 폴더 work/omega/. FZP 스캔은 fzp.lock 으로 한 번에 하나.

## 2026-10-25 01:40 KST — A0 (D-K9-83) 에이전트 시작
- 디스크: C 34 GB, D 290.9 GB 여유 [실행].
- 할 일: codex joint 결정 오프라인 재생 준비(scratch D:/VISSIM-merge/k8_gate_trees/codexhandoff/a0/), 결정 3개 재생·대조, 시간 분해, 속도 후보 비트 동일 시험, PRE_A1.md·A0_PROFILE.md 작성.
- 규칙: VISSIM·COM·폐루프 러너·커밋·푸시 0. 무거운 재생은 한 번에 하나, WMI 분리, BELOW_NORMAL, PYTHONHASHSEED=0, python -B. 공유 드라이브 쓰기 0, sealed/ 0, 봉인 시드 0. GWT8·동결 트리·codex worktree 읽기만.
- HANDOFF.md (사본 루트) sha256 e2cef38c… = 우리 사본 [실행].

## 2026-10-25 01:45 KST — RAW_CHECK (rawcheck) 에이전트 시작
- 디스크: C 34 GB, D 290.9 GB 여유 [실행].
- 할 일: TAKEOVER_PLAN §4 순서 raw 검증(D:/VISSIM_handoff/20261024 읽기만). 작업 폴더 work/rawcheck/. 산출 RAW_CHECK.md.
- 규칙: VISSIM·COM·러너·재생·커밋·푸시 0. FZP 스캔은 다른 에이전트와 같은 잠금(work/omega/fzp.lock 있으면 기다림) 으로 한 번에 하나. 공유 드라이브 쓰기 0, sealed/ 0, 봉인 시드 0. GWT8·동결 트리·codex worktree 읽기만.
- 01:44 KST [실행] 합성 FZP 자기 시험(work/omega/selftest/test_small.py): 우리 적분 = 직접 계산(차 0), codex 꼴 = check_fzp.py 사본 integrate()(차 < 1e-12). check_fzp.py 사본 sha256 1a2cf568…(원본과 같음).
- 01:48:02 KST FZP 스캔 발사: WMI, 래퍼 PID 43760, run_omega.ps1 -Step scan(PYTHONHASHSEED=0·PYTHONUTF8=1·OMP/OPENBLAS/MKL=1, python -B, BELOW_NORMAL). 10개 FZP(v3c3 9 + LNC 64cf-s29 NC 1, codex 분할 대조용)를 fzp.lock 아래 하나씩.
- 02:05 KST (rawcheck) [실행] 내 FZP 스캐너(work/rawcheck/scan_fzp.py) 로 7개 FZP(raw nc·joint·window·off·freeway_only·urban_only + 로컬 LNC) 를 하나씩 읽음(각 30–43 s, BELOW_NORMAL, work/omega/fzp.lock 공유 잠금). 6조건 + LNC 모두 895.1 s 까지 431,233행 LF sha256 f1a0b040…cbda. raw NC 와 LNC 는 0–8100 데이터행 전체 LF sha 6ee7ccec… 로 같음. 지표는 codex 캐시와 최대 3.2e-11 차.
- 02:10 KST (rawcheck) [실행] 입력별 미삽입 재구성(uninserted2.py): 5 제어 팔의 실현 도착(I+U)이 1098 16,070×5, 1099 20,166–20,169 로 같음 → 도착열은 시드가 정함. 공통 도착 추정으로 native − 재구성 잔차가 5팔 모두 232.8–232.9 veh·h 로 일정. NC ④b(0–8100) 16,643.4(경로 A) / 16,644.9(경로 B).

## 2026-10-25 02:20 KST — A0 준비·대조 규칙 고정
- [실행] SOURCE_FILES.csv 3,638행: 로컬 사본 code/ 와 CX worktree 모두 3,638/3,638 일치(둘 다 실행 바이트). a0/code 는 code/ 를 robocopy(.git 제외)로 복사, 다시 3,638/3,638 일치, .pyc 0.
- [실행] provenance controller_sources 116개 = a0/code 와 sha 같음.
- [실행] 입력 트리 a0/pristine/T000900·T002700·T004950: 원자료 바이트 그대로 복사, 상태 JSON 만 경로 접두 둘 재배치(E: 런 폴더 6곳, 동결 트리 1곳).
- 대조 규칙 A0-CMP-1 고정: work/a0/COMPARE_RULE_A0.md sha256 a05f20716f5b6056deb0783482523d52dd89c3a60dfc4be6b27609bc2047a634. 첫 재생 전.
- 고침: 바로 위 항목 머리의 "02:20 KST" 는 오기입니다. 실제 기록 시각은 01:53 KST 무렵이고, 규칙 파일(COMPARE_RULE_A0.md, sha a05f2071…) 첫 줄의 "02:20" 도 같은 오기입니다. 규칙 내용은 첫 재생 발사(01:54:14 KST) 전에 고정됐습니다 [실행 date].

## 2026-10-25 01:54 KST — A0 첫 재생 발사 (T=900, 차가운 numba 캐시, 열기 추적)
- WMI, 래퍼 PID 19892, BELOW_NORMAL, 라벨 base_cold_trace. 출력 a0/out/base_cold_trace/T000900/.
- 같은 때 이 PC 에서 다른 세션 프로세스가 돎(건드리지 않음): codex VISSIM 폐루프 1개(VISSIM200 PID 25352, 어댑터 python Normal 우선순위), TD3 학습 python 1개, FZP 스캔 에이전트.
- 01:51:05 KST 스캔 끝(182.8 s, 종료 코드 0). FZP 10개 각 9.9–13.4 s, 잠금 파일 스스로 지워짐. 01:51:16–01:51:27 KST 계산 단계(WMI, 래퍼 PID 11276, 11.1 s, 종료 코드 0, FZP 다시 읽지 않음).
- [실행] 검증: 우리 꼴 0–9000 Ω635·④a·①·②·④·Ω 밖 (a)(b) 가 V-A 보고 va_metrics.json 과 지표마다 27칸 모두 ≤ 0.001 veh·h, ④b·입력별 차 0, 기존 stage-1 uninserted.json 입력 기록 9런 모두 같음. codex 분할(도시도로·진입·진출·서측 본선·Ω701−서측)은 LNC 에서 codex 값과 ≤ 1.3e-11.
- [실행] NC3 v3c3-s41·s43 .inpx 는 randSeed 한 줄만 v3c3 3de889f0 판과 다름(나머지 7런은 같은 바이트).
- 01:57 KST OMEGA701_V3C3.md 작성(547줄), sha256 5c02894a84ed155c428004e740e27bb074eba482a747fcea43db8f2314470c64. 산출물 sha 목록은 그 문서 부록 B. 주요: omega701_recount.py 5b7826f6…, omega701_v3c3.json fa6d24cf…, omega701_pairs.csv 82c094d3…, omega701_levels.csv f0a6d31d…, verify_vs_va_report.csv 0e2b8ac6….
- 내 프로세스(43760·43884·11276 및 그 python) 모두 스스로 끝남, kill 0. 런 폴더·동결 트리·GWT8·codex worktree 쓰기 0. 공유 드라이브 접근 0. sealed/ 0, 봉인 시드 숫자 0. VISSIM·COM·러너·재생·커밋·푸시 0. codex 스크립트는 check_fzp.py 사본의 integrate() 를 합성 FZP 에만 import(쓰기 없음).
- 디스크 끝: C 33.9 GB, D 290.3 GB 여유 [실행].

## 2026-10-25 02:05 KST — A0 재생 1·2차 실패 원인: 인계 code/ 에 빠진 데이터 파일
- [실행] 1차(01:54, base_cold_trace): 6.2 s 만에 ValueError "Native choice must partition exactly one complete approach". 원인: outputs/movement_merge_plan_20260824.json 이 인계 부분집합에 없음 → 어댑터가 is_file() 로 조용히 병합 끔(movement_merge_enabled 0, 기록 결정은 1.0) → 뒤 단계에서 실패.
- [실행] 2차(01:58, base_cold_trace2, 열기+없는 파일 추적): 7.7 s 실패 "SC107_N_SC1_to_S: stale expected head-free movement semantics". 추적에 없는 파일 outputs/movement_phase_correction_20260828.json, outputs/movement_beta_routing_20260824.json.
- [실행] 원래 동결 트리 목록(evidence/original_FREEZE.json, 74,076 파일 sha)에는 셋 다 있음. 어댑터 경로 상수 중 부분집합에 없고 동결 목록에 있는 파일 20개(s8_const_paths.py).
- [실행] 복원 규칙: 동결 목록 sha 와 바이트가 같을 때만 a0/code 에 넣음. 원천은 읽기만: GWT8 작업 트리, D:/VISSIM-merge/repo git blob(ca181e84·886a014a). outputs·evaluation·plant·vendor·network 아래 동결 목록 파일 중 없던 3,541개 + 개별 3개 = 3,544개 복원(GWT8 트리 3,543, git 1, 맞는 바이트 없음 0). .py 는 0개(코드 바이트는 인계 그대로). 기록 a0/RESTORED_FILES.json sha256 184a26047350e0b8….
- 고침: 바로 위 항목 머리 "02:05 KST" 도 오기(실제 02:01 KST 무렵). 이후 시각은 date 명령 값으로만 적음.
- 02:01:44 KST 3차 재생 발사(T=900, base_cold_trace3, 추적), WMI 래퍼 PID 21056.
- 02:40 KST (rawcheck) [실행] 결정 JSON 읽기(dec_extract.py joint·freeway_only, ramp_fc.py, walltimes.py, h10633.py), LSA·LDP 비교(lsa_cmp.py, ldp_cmp.py, rm_exec.py), 원래 평가기 분할 재실행(orig_eval.py, 캐시 입력), NC 출처(prov_cmp.py, ncdeps.py), raw NC 와 LNC 전체 데이터행 LF sha 6fad8e06… 같음(fullhash.py). 모두 읽기 전용. codex 스크립트 실행 0.
- 02:55 KST (rawcheck) 끝. RAW_CHECK.md sha256 c8411d78e756a0182042a4f6e125b9e37b8e01672539daf046214039fade38fc (287줄). 작업 산출물 sha 목록 work/rawcheck/SHA256SUMS_RAWCHECK.txt (sha 3e3b5307…, 52개).
- 핵심 [실행]: 6조건+LNC 접두 sha f1a0b040 같음, raw NC = LNC 전체 6,950,156행 같음(6fad8e06…). 지표 캐시와 ≤3.2e-11. NC ④b(0–8100) 16,643.4. joint−NC Ω701 −494.7 / ④ −668.8 / Ω 밖 (a) −174.2 / Ω 밖 (b) +45.7 (64cf-s29 한 짝). VSL 기울기 2,688행 모두 secant, 0.4545 넘는 행 0. 램프 도착 120 s·900 veh/h 폴백 47/47. 6900 유지 = ValueError(시한 아님). codex PC joint 결정 평균 294.8 s·최대 448.6 s. freeway_only 도시 신호 LDP 로 native 와 같음. 미터 실행 1,920구간 어긋남 0.
- VISSIM·COM·러너·재생·동결·커밋·푸시 0, codex 스크립트 실행 0, 공유 드라이브 접근 0, sealed/ 0, 봉인 시드 0, kill 0. 내 프로세스 모두 전경 실행·종료. 디스크 끝 C 31 GB, D 290 GB 여유 [실행].

## 2026-10-25 02:19 KST — 재생 3·4차, 반복 복원 드라이버
- [실행] 3차(02:01): 런 provenance JSON 의 경로가 열림(signal_head_observation.py:548 plant_manifest) → 입력 트리에서 run_provenance JSON 도 같은 두 접두로 재배치(런 43곳, 동결 147곳). 그 밖 입력은 바이트 그대로.
- [실행] 4차(02:02)·드라이버 r900(02:16): diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/flow279/config_10686_free.json 이 없음. 원래 동결 목록에는 있음(sha a26ab121…). 이 PC 어디에도(인계 사본 FILE_MANIFEST, W264 동결 트리, rolling_cea 동결 트리 5벌, GWT8, git ca181e84·886a014a) 같은 sha 바이트가 없음.
- [읽음] 이 파일은 flow279/audit.py:121-124 가 urban_clock277/config_fw5_urban10.json(이것도 없음, sha 6591ca6c…) 에서 한 칸을 바꿔 쓴 설정. 런타임에서 읽는 곳은 sc109_routes321/candidate.py:13 하나이고 control_area_objective.membership_path 만 씀. 그 결과는 링크 1220012103·1210012600 의 안/밖에만 쓰임(calibrated_urban_runtime.py:143,157). 이 PC 의 membership 파일 4벌 모두에서 두 링크는 "안".
- [실행] 그래서 대역 파일 1개(membership_path = Ω701 approaches_only) 를 a0 트리에만 둠. sha c4032d1f…(원본과 다름). 기록 a0/STANDIN_FILES.json. 이 대역이 결정을 바꾸는지는 기록 결정과의 대조(A0-CMP-1)로만 확인함.
- 02:19:26 KST 드라이버 r900b 발사(WMI, PID 56140).
- 02:19–02:21 KST: 드라이버 r900b 가 sc107_shared316/config.json(동결 sha d884ea00…) 에서 멈춤. 정적 훑기(s11_candidate_reads.py)로 런타임 후보 모듈이 읽는데 없는 파일을 더 찾음: sc109_transport317/config.json(b2e83f62…). 둘 다 이 PC 원천 없음. 런타임 독자는 각각 키 두 개만 확인함(sc107_shared316/candidate.py:13-17, sc109_transport317/candidate.py:60-62) → 그 두 키만 담은 대역 2개 추가(STANDIN_FILES.json, 모두 3개). sc101_clock299 의 assessment.json·source_geometry.json, canonical_harness 기본 설정은 오프라인 main()·미사용 기본값에서만 읽어 대역 없음.
- 02:21:04 KST 드라이버 r900c 발사(PID 20048). 02:21:34 KST 결정 계산 단계(joint progress 파일 생김) 진입 확인.

## 2026-10-25 02:33 KST — 첫 완주 재생(T=900) 결과
- [실행] r900c_it01: 종료 0, 벽시계 624.6 s(차가운 numba 캐시, 열기 추적, 다른 세션 부하 아래). codex PC 같은 결정 228.8 s(budget)·229.4 s(runlog).
- [실행] A0-CMP-1 대조: R1(CSV 바이트) 다름, R2(일곱 필드) 다름, R3(토큰) 다름. derived_000900·vsl_cohorts_000900 은 경로 유래 해시 1칸씩(raw_sha256, derived_sha256)만 다르고 나머지 같음.
- [실행] PFO 두 걸음의 owned_cost·omega_cost 는 진행 기록에서 float 표기까지 같음. 그러나 같은 PFO 안 local_rows 에서 마지막 자리 차이(own_gradient −1.4638358840914507 대 …512)와 QP 반복 수 차이(8 대 13)가 이미 있음. 그 뒤 tangent 테이프 노드 수(3,246,935 대 3,246,960)·리더 목적(423.73996067 대 423.73981249)·미래 녹색(38.226 대 38.227) 등으로 번짐.
- [추론] 무작위성이 아니라 부동소수 연산 경로 차이로 보임(CPU SIMD 폭·OpenBLAS 커널·PYTHONHASHSEED·Python 3.12.2 대 3.12.14 후보). 먼저 이 PC 안 결정성 확인: 02:33:43 KST 같은 T=900 반복(base_rep2, 데운 numba 캐시, 추적 없음) 발사, WMI PID 27024.

## 2026-10-25 02:45 KST — 이 PC 안 결정성, 수치 경로 맞춤 시험
- [실행] base_rep2(T=900, 데운 캐시, 추적 없음) 종료 0, 602.2 s. r900c_it01 과 비교: R1·R2·R3 같음. 잎 차이는 시계 잎 + 이름이 *_sec 인 소요시간 잎 14개(reverse_sec, compile_or_load_sec, sweep_sec, state_check_sec, tangent_sec 등; 고정 규칙 정규식이 못 잡은 시계 잎이라 따로 적음)와 그것을 담은 action JSON 의 sha 하나뿐. 즉 이 PC 에서는(PYTHONHASHSEED=0) 같은 입력이 같은 결정을 냄.
- [실행] 이 PC CPU 는 AVX-512(SKX/CLX) 가 있음(numpy dispatch 확인). codex PC CPU 는 원자료에 기록 없음(모름).
- [추론] 기록과의 마지막 자리 차이가 PFO 의 기울기·QP 에서 처음 보여, BLAS 커널·SIMD 폭 차이를 첫 후보로 봄. 02:45:05 KST env_hsw 발사(WMI PID 504): OPENBLAS_CORETYPE=Haswell, NPY_DISABLE_CPU_FEATURES=AVX512 넷, NUMBA_CPU_NAME=haswell. 코드·설정 변경 없음.

## 2026-10-25 02:58 KST — env_hsw T=900 결과, T=2700 발사
- [실행] env_hsw T=900: 종료 0, 589.0 s. 기록 대비 R1(CSV 바이트) 같음, R2(일곱 필드·물리 행·메타·CSV sha·행 수) 같음, R3(scored_action_token) 다름. 남은 잎 차이 6,917(기준 재생 24,671): central_derivative_work 테이프 노드 수(3,246,935 대 3,246,960), central_multiplier 마지막 자리 등.
- [실행] 같은 PC 의 기준 재생(base_rep2)과 env_hsw 는 R1 부터 다름 → 수치 경로 설정이 이 결정의 명령을 바꿈.
- [실행] joint.json 의 source_sha256 핀 목록에 이 PC 의 C:/Users/TRLAB/Desktop/찐찐막/VISSIM·C:/Users/TRLAB/Documents/ChatGPT/VISSIM 아래 파일 20개가 들어감(설정 속 절대 경로가 이 PC 에 실제로 있어서). 18개는 codex 기록의 같은 이름 파일과 sha 같음, freeway_control_manifest_ver2.csv 는 a0 사본과 sha 같음, canonical_topology_v3.json 1개는 codex 기록에 없음. 이 목록은 joint_runtime_source_pins(vissim_stackelberg_adapter.py:12588-12628)의 핀(해시) 용도이고 결정 계산 입력이 아님 [읽음].
- 02:58:27 KST env_hsw T=2700 발사(WMI PID 54396).
- 03:00 KST env_hsw T=2700 1차: 61 s 만에 "SDMPC prior price/application context mismatch"(sdmpc.py:774-783). 직전 명령의 VBS 적용 영수증(action_002550.json.applied, UTF-16, 3줄: 시각·CSV 경로·크기)의 CSV 경로가 E: 원래 경로라 맞지 않음. 출력은 out/env_hsw_fail_applied/ 로 옮겨 둠.
- [실행] 입력 재배치 하나 추가: 직전 명령 .applied 의 경로 줄만 같은 런 접두로 바꿈(UTF-16 왕복 바이트 동일 확인 뒤). pristine T002700·T004950 다시 만듦(T000900 은 직전 750 에 .applied 가 원래 없음).
- 03:01:27 KST env_hsw T=2700 재발사(WMI PID 42040).

## 2026-10-25 03:24 KST — env_hsw T=2700 결과, T=4950 발사
- [실행] env_hsw T=2700: 종료 0, 1,114.1 s(codex PC 425.0 s). 기록 대비 R1·R2·R3 다름. 명령 CSV 213행 중 40행(signal 6, signal_sg 34; SC5·6·105·108·1001·1002) 이 다름. 차이 크기: 녹색 최대 0.001 s, offset 최대 0.003 s. 램프 미터 8행·VSL 66행은 같음.
- [실행] 비교로 기준 재생(base_rep2) T=900 은 23행(SC6·107·1004) 이 녹색 0.001 s·offset 0.004 s 까지 다름. env_hsw T=900 은 0행.
- [추론] 남은 차이는 AD 기울기 마지막 자리에서 시작함(PFO local_rows own_gradient −1.4638358840914507 대 …512 는 env_hsw 에서도 그대로). 후보: codex 런의 PYTHONHASHSEED 미설정, Windows UCRT·Python 3.12.14 대 3.12.2 의 수학 함수, codex PC CPU(모름). 규칙상 해시 시드는 0 으로만 돌림 — 그래서 해시 시드 영향은 시험하지 않음.
- [실행] 소규모 측정(가벼운 import 만): 바이트코드 캐시 없이 어댑터 묶음 import 0.97–1.01 s, PYTHONPYCACHEPREFIX 캐시 읽기 0.42–0.48 s. 이 측정 중 한 번은 -B 없이 돌려 pyc 를 a0/pyc_probe 에만 씀(규칙 "python -B" 에서 벗어남, 쓰기 위치는 a0 scratch 안).
- 03:20:16 KST env_hsw T=4950 발사(WMI PID 42128).
- 고침: 바로 위 항목 머리 "03:24 KST" 는 오기, 실제 기록 시각 03:22 KST(03:22:18 확인).

## 2026-10-25 03:37 KST — env_hsw T=4950 결과, 기준 T=2700 발사
- [실행] env_hsw T=4950: 종료 0, 962.3 s(codex PC 381.7 s budget). 기록 대비 R1·R2·R3 다름. 명령 CSV 213행 중 17행(signal 3, signal_sg 14; SC1·107·1004) 이 녹색 최대 0.001 s 다름. offset·램프 미터·VSL 행은 같음.
- 03:36:39 KST 기준 env(코드·러너 환경만) T=2700 발사(라벨 base, WMI PID 28892).

## 2026-10-25 03:55 KST — 기준 env T=2700 결과, 기준 T=4950 발사
- [실행] base T=2700(codex 러너 환경만): 종료 0, 1,061.1 s. 기록 대비 R1·R2·R3 다름. 명령 CSV 44행 다름(signal 7, signal_sg 36, ramp_meter 1). 차이 크기: 녹색 최대 0.008 s, offset 최대 0.015 s, 램프 미터 SC9101(RM_C10480) 녹색 1 s(rate 90 veh/h). env_hsw T=2700 은 40행, 녹색 0.001 s·offset 0.003 s, 미터·VSL 같음.
- 03:54:39 KST base T=4950 발사(WMI PID 55492).

## 2026-10-25 11:42 KST — A0 이어 하기(사용 한도로 04:10 KST 무렵 끊긴 뒤)
- 디스크: C 29.8 GB, D 281.1 GB 여유 [실행].
- [실행] base T=4950(WMI 래퍼 PID 55492, python PID 55632) 은 끊기기 전 04:10:24 KST 에 스스로 끝남: 종료 0, 벽시계 944.1 s(어댑터 보고 924.6 s; codex PC 381.7 s). 남은 내 프로세스 0.
- [실행] A0-CMP-1 대조(s13_compare.py 4950 base): 기록 대비 R1·R2·R3 다름. 명령 CSV 213행 중 33행(signal 5, signal_sg 28; SC1·6·11·1001·1004) 이 녹색 최대 0.001 s 다름. offset·램프 미터·VSL 행은 같음. env_hsw T=4950 대비로는 26행(SC6·11·107·1001) 다름. 출력 out/base/T004950/compare_vs_recorded.json.
- [실행] 지금 이 PC 에서 도는 다른 세션 프로세스: TD3 학습 python(PID 23672)과 그 tangent 워커(PID 35644). 건드리지 않음. VISSIM 은 지금 0개. CPU 전체 부하 약 40 % (이 PC: Xeon Silver 4210R 2.4 GHz, 10코어 20스레드).
- [실행] GWT8 git log 886a014a..c20aff1d 65개 커밋에 속도·캐시·병렬·numba·tangent 동시성 커밋 0(sdmpc.py 변경은 K8-2·K8-3 회계뿐). 설정 비교(s23_speedkeys.py): 속도 관련 키 56개 중 49개 같음, 다른 7개는 우리 쪽에 max_leader_candidates 1(codex 3)·meter_neighbor_audit 없음·response_cap_cache 없음·decision_timeout_sec 없음 등 — 모두 D-K9-83 이 금한 지름길 쪽이거나 시한 키.
- [읽음] numba prange 커널은 sdmpc_tangent_spatial.py:152-157 하나뿐이고 spatial_receiving(codex 설정에 없음, 속도 기각 영수증 있음 — 메모리 vissim-sdmpc-flags-rejected) 에서만 불림. 그 캐시 파일도 a0/code 에 없음 [실행] → NUMBA_NUM_THREADS 는 이 설정에서 계산 경로가 없음. derivative_workers 는 8 고정(sdmpc.py:213-216, 233-242).
- 11:42:12 KST 속도 후보 묶음 발사(run_speed_set2.ps1, WMI 래퍼 PID 34808, BELOW_NORMAL): compileall 로 바이트코드 접두 캐시(a0/pycache_prefix, 코드 트리 밖) 채운 뒤, S1 = PYTHONPYCACHEPREFIX + NUMBA_NUM_THREADS=2 를 env_hsw 위에서 T=900·2700·4950(라벨 spd_hsw), 기준 env 위에서 T=900(spd_base) 차례로. 대조 기준은 같은 env 의 이 PC 재생(env_hsw, base_rep2). run_replay.ps1 은 환경 기록에 NPY_*·OPENBLAS_* 이름을 더하도록만 고침(계산 무관).

## 2026-10-25 11:58 KST — 속도 후보 S1 첫 결과(T=900), 시간 분해 도구
- [실행] compileall(바이트코드 접두 캐시 채우기) 224 s, 종료 1 = Python Lib/test 의 일부러 깨진 파일과 a0/code 의 diagnostics 보관 사본·scripts/derive_measured_turn_beta.py 186개 컴파일 오류. evaluation·plant·vendor 아래 런타임 모듈 오류 0.
- [실행] spd_hsw T=900(env_hsw + S1): 종료 0, 527.3 s. 같은 env 기준(env_hsw T=900, 589.0 s)과 R1·R2·R3 같음. R4 차이는 시계 잎(정규식) 82·152·6개 + 정규식 밖 소요시간 잎(*_sec) 14·14개 + 그것을 담은 action JSON sha 1개뿐, 설명 안 된 차이 0(s27_candidate_check.py, out/spd_hsw/T000900/candidate_vs_env_hsw.json). 기록 대비 R1·R2 같음, R3 다름(env_hsw 와 같은 꼴).
- [실행] 시간 분해 도구 s22_profile_all.py(진행 기록·decision_budget·joint.json physical_response_cache·typeperf), 표 s26_tables.py. 기존 재생 10개 + 기록 3개 분해 결과 prof_all_pre_spd.json.
- [실행] 확인: W264(이 PC 결정 평균 1,709 s) 설정은 vsl_window264/config.json(f181dc1d…)으로 joint 설정과 다름 — sdmpc_response_cap_cache 없음, decision_timeout_sec 0. W264 러너(e3558b71…)는 인계 러너(8e95423b…)와 달리 예약 작업 24 h 한도를 끔·TEMP 를 옮김(diff 로 확인).
- [읽음] 인계 러너 run_closedloop3000.ps1: :82 예약 작업 24 h 한도(-Detached 일 때), :161 StartupStallSec 300·StallSec 2400, :164-172 다른 VISSIM 이 열려 있으면 발사 거부. 워치독 :329-331 시한은 30 ≤ 시한 < StallSec, :992-997 시간 무제한 결정이면 joint.progress.jsonl 쓰기도 진행으로 셈. VBS :1259 가 RW_DECISION_TIMEOUT_SEC 를 읽음. 어댑터는 decision_timeout_sec 를 읽지 않음(grep), 그러나 tuning 파일 sha 는 joint.json source_sha256 에 핀으로 들어감.
- 시한 키 시험 준비(아직 발사 안 함): a0/code 안 tuning 사본 optimized_config_t2390.json(decision_timeout_sec 1800→2390 한 칸만, sha 9365141f…; 원본 c9088262…), run_replay_tuning.ps1(-TuningName 매개변수만 더함), run_tmo.ps1.

## 2026-10-25 12:02 KST — 대기열 2 발사(속도 묶음 끝난 뒤 시작)
- [실행] 이 PC 에 codex 런타임 Python 이 있음: C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe = "3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]". 인계 derived/current_environment_20261024.json /python 과 같은 빌드 문자열. 당시(10-12) 판은 /historical_python "모름". 두 Python 모두 PYTHONPATH 로 D:/VISSIM-window264-deps 의 numpy 2.3.5·numba 0.67.0·scipy 1.18.1·llvmlite 0.49.0 을 읽음(가벼운 import 확인).
- run_replay2.ps1 = run_replay.ps1 + 기본값이 같은 -TuningName·-PyExe 두 매개변수(diff 확인). run_replay_tuning.ps1 은 지움(발사 전).
- 12:01:33 KST run_queue2.ps1 발사(WMI 래퍼 PID 35168, BELOW_NORMAL): speed_set2.done 을 기다린 뒤 하나씩 ① tmo2390_hsw T=900(시한 키만 바꾼 tuning, 기준 env_hsw) ② py31214_base T=4950 ③ py31214_hsw T=4950(인터프리터만 codex 판으로, 기록과 대조).

## 2026-10-25 12:16 KST — S1 T=2700 결과
- [실행] spd_hsw T=2700: 종료 0, 994.7 s(같은 env 기준 env_hsw 1,114.1 s, codex PC 425.0 s). 기준과 R1·R2·R3 같음, 명령 CSV 다른 행 0. R4 차이는 시계 잎 142·269·6 + *_sec 소요시간 잎 21·21 + action JSON sha 1, 설명 안 된 차이 0(out/spd_hsw/T002700/candidate_vs_env_hsw.json). 기록 대비는 env_hsw 와 같은 40행(SC5·6·105·108·1001·1002, 녹색 ≤0.001 s·offset ≤0.003 s).
- [실행] 진행 기록 첫 차이(s29_progress_diff.py, progress_first_diff.json): T=2700·4950 base 와 T=2700 env_hsw 는 PFO 첫 걸음(5번째 줄, 첫 예측 묶음 뒤) owned/omega_cost 가 이미 다름(env_hsw 상대차 약 4e-10, base 약 6e-8). T=900 base 는 cap1 첫 걸음(20번째 줄), T=4950 env_hsw 도 20번째 줄. T=900 env_hsw 는 32번째 줄 derivatives_reused key(해시)만 다르고 명령은 같음.

## 2026-10-25 12:29 KST — S1 T=4950 결과
- [실행] spd_hsw T=4950: 종료 0, 905.3 s(기준 env_hsw 962.3 s, codex PC 381.7 s). 기준과 R1·R2·R3 같음, 명령 CSV 다른 행 0. R4 차이는 시계 잎 146·277·6 + *_sec 잎 21·21 + action JSON sha 1, 설명 안 된 차이 0. 기록 대비 17행(SC1·107·1004, 녹색 ≤0.001 s) = env_hsw 와 같음.
- 이로써 S1 은 env_hsw 위 3결정 모두 같은 env 기준과 비트 동일(시계·소요시간 잎 제외). 12:26:32 KST spd_base T=900 시작.

## 2026-10-25 12:37 KST — S1 base T=900 결과, 속도 묶음 끝, 대기열 2 시작
- [실행] spd_base T=900(base env + S1): 종료 0, 527.6 s(기준 base_rep2 602.2 s). 기준과 R1·R2·R3 같음, 명령 CSV 다른 행 0, R4 는 시계 82·152·6 + *_sec 14·14 + action JSON sha 1 뿐. 기록 대비 23행(SC6·107·1004) = base_rep2 와 같음.
- [실행] S1 의 시간: 같은 env 기준 대비 0.85–0.94배(4개 재생). 그러나 같은 때 이 PC CPU 사용률이 41.7–45.3 % 로 기준 재생(39.2–61.1 %)과 달랐고, plant 스칼라 롤아웃 중앙값은 거의 같음(19.5 대 19.5, 29.8 대 33.0, 22.9 대 22.5 s). 적재·모형 준비는 3–5 s 줄었음. [추론] S1 몫은 프로세스 시작·import(결정당 수 초)이고, 나머지 차는 다른 세션 부하 흔들림으로 봄. 반복 측정 없이 가를 수 없음.
- [실행] 재생별 작업 수: env_hsw·S1 은 세 결정 모두 기록과 PFO 예측 수·롤아웃 수가 같음. base 는 T=2700(스칼라 112 대 113, 요청 128 대 129)·T=4950(PFO 예측 6 대 7, tangent 14 대 15) 에서 기록과 다름.
- 12:35:22 KST 속도 묶음 끝(speed_set2.done). 12:35:35 KST 대기열 2 첫 일(tmo2390_hsw T=900) 시작.

## 2026-10-25 12:47 KST — 시한 키 시험 결과
- [실행] tmo2390_hsw T=900(env_hsw, tuning 사본 optimized_config_t2390.json = decision_timeout_sec 1800→2390 한 칸, sha 9365141f…; RW_SIGNAL_OBSERVATION_CONFIG_SHA256 도 그 sha): 종료 0, 531.4 s. 어댑터가 바뀐 tuning 을 받음.
- [실행] 같은 env 기준(env_hsw T=900) 대비 R1·R2·R3 같음, 명령 CSV 다른 행 0(기록 대비도 0행). R4 에서 시계·*_sec 잎 말고 다른 것: 해시 잎 16(action JSON)·14(joint.json) — frozen_context_token·reference_response_token·request_sha256·response_token 꼴, 경로 잎 2(run_provenance inputs tuning_json path), joint.json source_sha256 에 새 tuning 핀 1개 더함. 설명: tuning 파일 이름·sha 가 문맥 토큰에 들어감. 채점 토큰·명령은 그대로.
- 12:44:28 KST py31214_base T=4950 시작.

## 2026-10-25 13:03 KST — 인터프리터 시험 (base)
- [실행] py31214_base T=4950(codex 런타임 Python 3.12.14, base env): 종료 0, 926.0 s. 시스템 Python 3.12.2 의 base T=4950 과 R1·R2·R3 같고 R4 차이는 시계 145·275·6 + *_sec 21·21 + action JSON sha 1 뿐(설명 안 된 차이 0). 기록 대비는 base 와 같은 33행.
- [추론] 이 결정에서 인터프리터 판(3.12.2 대 3.12.14)은 결과에 닿지 않음. 12:59:58 KST py31214_hsw T=4950 시작.

## 2026-10-25 13:18 KST — 인터프리터 시험 (env_hsw), 대기열 3 발사
- [실행] py31214_hsw T=4950(Python 3.12.14, env_hsw): 종료 0, 929.9 s. env_hsw(3.12.2) T=4950 과 R1·R2·R3 같음, R4 는 시계 146·277·6 + *_sec 21·21 + sha 1 뿐. 기록 대비 같은 17행.
- [추론] 두 env 모두에서 인터프리터 판은 결과에 닿지 않음. 기록과의 남은 차이는 인터프리터 밖(CPU·BLAS·numpy·numba 경로, OS C 런타임 후보)으로 봄.
- [실행] 대기열 2 끝 13:15:32 KST. 내 프로세스(34808·35168·55492) 모두 스스로 끝남, kill 0. 이 순간 이 PC 에 python·VISSIM 프로세스 0, CPU 0.3–2.1 %(다른 세션 학습도 끝난 것으로 보임). 디스크 C 29.9 GB, D 279.7 GB.
- 13:18:19 KST run_queue3.ps1 발사(WMI 래퍼 PID 52780, BELOW_NORMAL): 빈 PC 에서 env_hsw T=900 반복(env_hsw_idle)과 S1 반복(spd_hsw_idle)을 차례로. 목적: 부하 없는 결정 시간, S1 시간 몫을 같은 조건에서 가르기.

## 2026-10-25 13:40 KST — 빈 PC 반복 결과
- [실행] env_hsw_idle T=900: 종료 0, 재생 535.1 s(결정 534.1 s, codex 대비 2.33배), CPU 평균 15.4 %(우리 재생만). 앞선 env_hsw T=900(588.1 s, CPU 56.5 %)과 R1·R2·R3 같음.
- [실행] spd_hsw_idle T=900(S1): 종료 0, 재생 530.7 s(결정 529.5 s, 2.31배), CPU 16.0 %. env_hsw_idle 과 R1·R2·R3 같음. 같은 조건에서 S1 의 차는 −4.5 s(−0.85 %): 적재·모형 준비 19.0→17.6 s, PFO 100.5→96.9 s, tangent spawn 몫 약 0.4 s 줄어듦. cap 2 QP 구간 169.2 대 168.4 s.
- [실행] 같은 env·같은 결정에서도 부하·주파수에 따라 단계 시간이 ±10 % 흔들림(예: cap 2 QP 구간 env_hsw 174.1 s(부하 56 %) / spd_hsw 150.6 s(42 %) / 빈 PC 169.2 s).
- 최종 시간 분해 prof_all_final.json, 표 tables_final.md, A1 어림 a1_estimate.json(배수 2.30–2.63, 10.9–12.2 h, 결정 최대 1,031–1,179 s). 내 프로세스(52780 및 자식) 모두 스스로 끝남, kill 0.

## 2026-10-25 13:43 KST — A0 끝: A0_PROFILE.md·PRE_A1.md
- A0_PROFILE.md (codex_handoff/, 421줄) sha256 900bad3c823327053434b93e0892351584624549a3ee95686c3540008d96c9de. 산출물 sha 목록은 그 문서 §10.
- PRE_A1.md (codex_handoff/a0/, 143줄) sha256 1027dc321cfa80638af1d8780ca2051585001f5595f30a7c2c211a4f6d8d83aa. 계획만. 사용자 결정 U1–U9(env, 재현 기준, 시한, 자리, 발사 방식, S1, 차가운 캐시, NC, A0b).
- 요약 [실행]: 이 PC 안 결정성 7쌍 + 인터프리터 2쌍 같음. 기록 재현: 어떤 env 도 3결정 모두 비트 동일 아님(env_hsw: 900 명령 일치, 2700 40행·4950 17행 ≤0.001 s/≤0.003 s; base: 23·44·33행, 2700 미터 녹색 1 s). 시간 2.30–2.63배(빈 PC T=900 2.31–2.33배), 단계마다 고르게. 우리 줄기 속도 커밋 0. S1 은 5재생 비트 동일, 빈 PC 이득 −4.5 s/결정. 시한 키 2390 은 명령·채점 토큰 같음(문맥 해시 30·경로 2 다름). A1 어림 10.9–12.2 h, 결정 최대 1,031–1,179 s.
- D-K9-83 기준은 바꾸지 않았고 PRE_A1 U2 로 올림.
- VISSIM·COM·폐루프 러너 0, 커밋·푸시 0, 공유 드라이브 쓰기 0, sealed/ 0, 봉인 시드 0. GWT8·동결 트리·codex worktree 읽기만(git log/diff·파일 읽기). 쓰기는 a0 scratch(재생 출력, pycache_prefix, tuning 사본 1개)와 work/a0, 문서 둘, LOG 뿐. 내 프로세스 모두 스스로 끝남, kill 0(내가 띄운 백그라운드 셸 하나(du 로 접두 캐시 크기 재기)만 TaskStop, 결과 없음). 이번 이어 하기에서 -B 위반 없음(compileall 은 접두 캐시에 명시 쓰기). 디스크 끝 C 30 GB, D 280 GB.

## 2026-10-25 13:52 KST — 종합: HANDOFF_RESULTS.md
- 입력(읽기만, sha256 [실행]): RAW_CHECK c8411d78…, OMEGA701_V3C3 5c02894a…, A0_PROFILE 900bad3c…, a0/PRE_A1 1027dc32…, TAKEOVER_PLAN r2 b75ad041…, NOTES cb71c563…, HANDOFF 사본 e2cef38c…. R_NET §3 도 읽음.
- HANDOFF_RESULTS.md (codex_handoff/, 280줄) sha256 f657591339bff3d97444d79126970e528076a7d04b49bd3d1207b5b9f79396d9.
- 내용: §0 쉬운 답 11줄, §1 지표 한 표(codex 꼴 0–8100: v3c3 세 시드 짝 V-A−NC3·J1−NC3·V-A−J1 + codex 64cf-s29 joint−NC 한 짝 따로; 백분율; 우리 꼴 0–9000 줄인 표 + 링크 66), §2 A1 계획(10.9–12.2 h, 시한 선택지 1800/2390/함께 올림), §3 B 에 필요한 것 B-1–B-13(복원 데이터 3,544, env 고정, 램프 도착 폴백 추적, 6900 꼴 ValueError, LDP 실행 점검, 런당 어림 12.2–13.6 h, 인계 러너 동시 발사 거부 → 차례로 1.5–1.7일), §4 사용자 결정 H1–H13 + H3 하위 표(U1·U3–U8), §5 TP·HO 고칠 곳 표, §6 모름.
- [계산] 이번 산술: 백분율, codex 열 Ω635 기준 세 칸(−86.8, −260.9, −41.1), 링크 66 V-A−J1(−53.1/+44.4/−32.7), B 런 어림(55결정 × 287.5 s × 2.30–2.63 + 결정 밖 3,130.4 s × 2.12 × 9000/8100).
- RW §12-6(Ω635 집합 대조)은 OM §3.4 `previous_inside_links_eq_635 = True` 로 답이 있음을 적음.
- VISSIM·COM·러너·재생·커밋·푸시 0, codex 스크립트 0, Y: 접근 0, 로컬 사본·GWT8·런 폴더·동결 트리·codex worktree 접근 0, sealed/ 0, 봉인 시드 0, kill 0. 디스크 C 29.9 GB, D 279.5 GB.

## 2026-10-25 13:58 KST — VERIFY_HANDOFF_RESULTS 에이전트 시작
- 디스크: C 29.9 GB, D 279.5 GB 여유 [실행].
- 할 일: HANDOFF_RESULTS.md 와 RAW_CHECK·OMEGA701_V3C3·A0_PROFILE 을 새 스크립트(작업 폴더 work/vhr/, 앞 저자 스크립트 재사용 0)로 다시 확인. FZP 재집계(joint·NC raw·LNC·V-A s31·NC3 s31·J1 s31), VSL 결정 JSON, A0 재생 1개(scratch 트리 D:/VISSIM-merge/k8_gate_trees/codexhandoff/ 아래 새 폴더), 목록표 수.
- 13:58:03 KST FZP 스캔 발사: 내 WMI 래퍼(vhr_launch.ps1), cmd PID 21552, BELOW_NORMAL, PYTHONHASHSEED=0·PYTHONUTF8=1·OMP/OPENBLAS/MKL=1, python -B vhr_scan.py. 읽기만.
- 14:01 KST [실행] FZP 스캔 끝(6개, 각 36.6–40.2 s, exit 0). joint·NC raw·LNC 895.1 s 접두 431,233행 LF sha256 = f1a0b040…8fbcda(끝 4자리는 "bcda"; RW:22·PRE_A1:84 의 "…cbda" 는 줄임 오기). NC raw = LNC 전체 6,950,156행 sha 6fad8e06…. joint−NC(codex 꼴 0–8100) Ω701 −494.660 / Ω635 −407.895 / ① −283.655 / ④a −448.989 / Ω 밖 (b) +45.672. V-A s31 − NC3 s31 codex 꼴 Ω701 −207.671 / ① −21.472, 우리 꼴 0–9000 Ω701 −240.589 / ① −12.342 / 링크 66 +180.685.
- 14:02 KST [실행] 내 재생 트리 D:/VISSIM-merge/k8_gate_trees/codexhandoff/vhr/code: 인계 code/ robocopy(.git 제외, 4,343 파일) + A0 의 RESTORED_FILES 3,544개를 원래 동결 sha 와 같을 때만 복사(3,544/3,544 같음, .py 0) + 대역 3개. SOURCE_FILES 3,638/3,638 일치(긴 경로 접두 사용). A0 트리에 목록 밖 파일은 optimized_config_t2390.json 1개뿐(+캐시 125).
- 14:06 KST [실행] 내 입력 트리 vhr/runs/T000900(규칙: 결정 900 시작 때 있던 파일만; readback CSV 는 sim_sec<900 행만, mer_index 는 ≤900 항목만(정규 직렬화 왕복 바이트 같음), 경로 접두 둘만 바이트 재배치).
- 14:07:32 KST 재생 발사(env_hsw, T=900): 내 cmd 래퍼(run_replay_hsw900.cmd), WMI, cmd PID 8160, BELOW_NORMAL, PYTHONHASHSEED=0, python -B. 다른 python·VISSIM 0개 확인 뒤.
- 14:16:24 KST 재생 끝: exit 0, 532.4 s(decision_budget wall 531.5 s). [실행 vhr_cmp.py] 기록 대비 R1(CSV sha 5be7a91b…) 같음, R2 다섯 칸 같음, 213행 중 다른 행 0. R3(scored_action_token)는 기록·A0 env_hsw 와 셋 다 서로 다름(내 3918bd7d…, A0 84cfeb38…, 기록 3a34ccae…). 진행 기록에서 시계 칸을 뺀 첫 차이는 33번째 줄(1부터 셈) sdmpc_derivatives_reused key 해시이고 이것도 셋 다 다름.
- 14:17–14:33 KST 내 잎 전수 비교 스크립트(vhr_leaves.py)가 너무 느려(CPU 1,010 s) 명령줄 확인 뒤 내 PID 34000 만 kill. 결과 없음. 대신 vhr_leaves2.py(부분 트리 해시) 로 바꿈.
- 14:34 KST [실행] 다른 세션 프로세스가 새로 보임: VISSIM200 2개(PID 29028·35148), python 1개(PID 14944). 건드리지 않음.
- 14:34:39 KST 2차 스캔 발사(WMI cmd PID 24820, BELOW_NORMAL): window·off·freeway_only·urban_only FZP + 첫 관측 스캔 7런. 14:38 끝(exit 0). 6조건 모두 접두 431,233행 sha 같음, Ω701·①·④a·도시도로가 codex 값과 ≤3.1e-11.
- [실행 vhr_unins.py] 첫 관측 차분(같은 도착열 가정): window−joint −91.60(native −91.51), off−joint +29.56(native +29.68). joint−NC 0–8100 ④b −221.29(1098 +96.98, 1099 −69.24, 그 밖 −249.03) → NC ④b 경로 C 16,644.86. A_1099(8100) joint = 9,949+10,217 = 20,166. v3c3-s31: V-A−NC3 0–8100 −111.24 / 0–9000 −174.31, J1−NC3 0–8100 −236.22 / 0–9000 −264.33.
- [실행 vhr_leaves2.py] T=900 내부 부분 트리(경로·해시·토큰·시계 칸 뺌): 내 재생 = A0 env_hsw(13개 모두 같음). 기록과는 gradient_rows·local_rows·central_multiplier·central_derivative_work·pfo_warm_start·iteration_dual_updates 가 다름, 선택 목적값·후보·이웃 검사·일곱 필드는 같음.
- 14:40–14:44 KST [실행 vhr_vsl.py] joint 결정 JSON 47개: VSL 기울기 2,688행 모두 executable_secant_fallback / inactive_vsl_legal_step / stencil [−0.0909, 0]; 음수 2,410·0 이 204·양수 74, 1e-9 넘는 양수 5, 최대 +0.1017, 최소 −8.997, 0.4545 이상 0. 출력 VSL 모두 110. local_rows VSL 걸음이 반 걸음(0.04545) 이상인 결정은 4500 s 하나(−0.2589, FW_E seg5 블록 1, 반복 1, own −1.447·ext +0.458·price +3.579). 램프 도착 예측 47/47 이 30 의 배수, R_* 4칸 0. 벽시계 47개 평균 294.8·중앙 277.5·최대 448.6(2400 s)·360 초과 11; 49개 합 14,088.1; 900 전 45.5.
- [실행 vhr_meter2.py] 미터 이웃 검사: 선택 후보(목적값 = selected_objective)의 delta_veh_h 합 −7.34, 최소 −0.736(3600 s), 47/47 음수. 같은 이름 후보가 여럿일 때 맨 뒤 후보를 고르면 RW 값(−6.62, −0.49 @3450, 2850 +0.0002, 46/47)이 그대로 나옴 → RW §7.2 는 선택 후보가 아닌 마지막 후보를 읽은 것.
- 14:45:16 KST 3차 스캔 발사(WMI cmd PID 48972): v3c3-s41·s43 의 V-A·J1·NC3 6런 FZP 전체 + 첫 관측.
- 14:45–14:51 KST 3차 스캔 끝(exit 0). [실행 vhr_v3c3_all.py] 9런 27짝 칸: Ω701·Ω635·①·④a·Ω 밖 (b) 는 OM 표와 ≤0.05 veh·h. 첫 관측 정확 차분 ④b 는 OM 의 stage-1 재구성 ④b 와 최대 35.5 veh·h 차(codex 꼴 0–8100: V-A−NC3 s41 +4.6·s43 −4.3, J1−NC3 s31 +11.7·s43 +31.3, V-A−J1 s31 −11.6·s43 −35.5). V-A−J1 s43 의 ④b(+28.5 → −7.0)·Ω 밖 (a) Ω701(+21.5 → −14.0) 부호가 바뀜. 같은 도착열 가정 점검: 입력 링크 39개 중 27–28개가 세 팔에서 첫 관측 총수가 정확히 같고, 9000 s 총수(삽입+remain)가 시드마다 ±4 안.
- [실행 vhr_cmp_a0.py] A0 출력(재생 다시 안 함)을 내 스크립트로 기록과 대조: base 2700 44행(신호 7·SG 36·미터 1, RM_C10480 3 대 2 s), env_hsw 2700 40행, 4950 17행, base 4950 33행, py31214 둘은 각 env 와 같은 행 수. AP 표와 같음.
- 14:52:07 KST 목록표 재검증 발사(WMI cmd PID 42084, BELOW_NORMAL, vhr_manifest.py; sealed/ 행은 경로 접두로 수만 셈).
- 14:57:04 KST 목록표 재검증 끝(exit 0, 288.5 s): 14,722행, sealed/ 2,398행 건너뜀, 12,324행 일치(크기·해시 다름 0, 없음 0, 41,351,610,348 B). 로컬 13,380 파일 41,370,811,521 B, 목록 밖 1,056. 폴더별 SHA256SUMS 1,023개 13,348항목 일치(sealed 가리킴 1개 건너뜀). FILE_MANIFEST.csv sha c26f0b18… = 공유 드라이브 사본(해시 읽기만).
- 15:05 KST VERIFY_HANDOFF_RESULTS.md 작성(273줄) sha256 d9e0348be14d44ff7426e98d37f793396bce31ad72aff69913fcca1083825302. 요약: 반박 1 = v3c3 짝 ④b(stage-1 재구성)가 첫 관측 정확 차분과 최대 35.5 veh·h 다름(V-A−J1 s43 ④b·Ω 밖 (a) 부호 바뀜, HR §0-5 의 V-A−NC3 ④ s41 −478.9→−474.3·s43 −336.1→−340.4); 반박 2 = B-7 미터 이웃 delta 합 −6.62→−7.34; 반박 3 = H4 까닭 논리; 근거 부족 = HR §0-9 까닭 태그, H1 까닭 3 "수치 차만". 나머지(접두 해시, Ω701·①·④a, 도시도로 분할, VSL 2,688행, 벽시계, A0 env_hsw T=900 비트 동일, 목록표 수)는 확인.
- 내 프로세스: 스캔·재생·목록표 래퍼(21552·8160·24820·48972·42084)는 스스로 끝남. kill 은 내 PID 34000 하나. VISSIM·COM·러너·커밋·푸시 0. 디스크 C 29.5 GB, D 278.8 GB.

## 2026-10-25 15:17 KST — 마무리: HANDOFF_RESULTS r2·PRE_A1 r2 (VERIFY_HANDOFF_RESULTS 고침 반영)
- 입력(읽기만): VERIFY_HANDOFF_RESULTS.md d9e0348b…(= 15:05 항목의 sha), work/vhr 산출물(v3c3_all.json bf26275e…, unins_out.json 1328eb0c…, meter2_out.json 1fea0f7d…, corr_tables.md 73a4d89a…).
- r1 보존: HANDOFF_RESULTS_r1.md f6575913…(= 13:52 항목 sha), a0/PRE_A1_r1.md 1027dc32…(= 13:43 항목 sha).
- [실행] 몇 값 다시 셈(VH 산출물 JSON, python 숫자만): 미터 선택 후보 합 −7.336·최소 −0.7361@3600·47/47 음수, 마지막 후보 합 −6.617·−0.4897@3450·2850 +0.0002 → RW §7.2 는 마지막 후보를 읽은 것. ④b 재구성 대 첫 관측 최대 차 codex 꼴 0–8100 35.5, 우리 꼴 0–9000 37.17(VH 본문 "35.5" 는 codex 꼴 값). ④ % = 첫 관측 ④ / NC3 ④ 수준값(OM §6.2 12,425.8/12,239.2/12,148.2) → −2.25/−3.88/−2.80, +0.91/−4.02/+0.86.
- [실행] 읽기만 find: v3c3-s31 NC3·V-A·J1 런 폴더(깊이 3)에 native 망 성능 파일 0개, codex raw/joint/sdmpc 에 native_network_performance.json 1개(sealed/ 아님).
- [읽음] RW:191 대조: B-5 "같은 예외" 수는 window 1·off 7·urban_only 3, 다른 ValueError(Terminal queue count changed) off 2·urban_only 2. VH 의 off 9·urban_only 5 는 팔별 유지 수 합이라 둘 다 맞음 → HR r2 B-5 에 나눠 적음.
- HR r2 고친 곳(§8 C1–C29): §0-5·§1.1·§1.3 의 ④b·④·Ω 밖 (a)·입력별 칸을 첫 관측 차분으로(V-A − J1 v3c3-s43 ④b +28.5→−7.0, Ω 밖 (a) Ω701 +21.5→−14.0 부호 바뀜), ④ %, codex 열 경로 A/B 두 값, B-7 미터 −7.34/−0.74@3600/47/47, B-9·B-10 12.1–13.6 h·36–41 h, §0-9·B-9 까닭 태그 [추론], H1·§2.1-3 "작은 수치 차만" 고침, H4 읽는 법(같은 T/앞/뒤) 고침, VSL 문턱 설명, R3 해석, 새 결정 H14(④b 계산법, 권장 (a) 첫 관측 차분 주 값)와 U10(PYTHONHASHSEED, 권장 0), §5 에 RW·OM·VA_REPORT·AP·PA·LOG 고칠 곳 줄 더함.
- PRE_A1 r2 고친 곳(§10 P1–P10): 접두 sha …fbcda, U8·§5 ④b 두 값과 첫 관측 차분, 첫 관측 도구 sha 둘, U9 읽는 법, U10 새로, 대역 몫 섞임 문장.
- 이 LOG 의 12:16 KST 항목 "32번째 줄" 은 시계 칸을 빼고 1부터 세면 33번째 줄(VH §3.7). 2700·4950 의 "5번째·20번째" 는 다시 세지 않음.
- 산출: HANDOFF_RESULTS.md r2(358줄), a0/PRE_A1.md r2(164줄). sha 는 보고 폴더 SHA256SUMS.txt 와 반환값에 적음. 보고 폴더 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/.
- VISSIM·COM·러너·재생·커밋·푸시 0, codex 스크립트 0, Y: 접근 0, sealed/ 0, 봉인 시드 숫자 0, kill 0. GWT8·동결 트리·codex worktree 접근 0. 디스크 C 30 GB, D 279 GB.

## 2026-10-25 15:42 KST — A0b 시작 (기록 결정 1,050–2,550 s 재생, VISSIM 0)
- 근거: NOTES D-K9-85(sha 67dcc32b… [실행]), PRE_A1 r2(2d9aa15a… [실행]) U9. 대조 규칙 A0-CMP-1(work/a0/COMPARE_RULE_A0.md, a05f2071… [실행]) 그대로 씀, 고치지 않음.
- 디스크 [실행 15:35]: C 31.4 GB, D 298.2 GB 여유.
- [실행 15:35] 이 PC 에 다른 세션 VISSIM200 PID 29028(14:16 시작)과 cscript PID 18916(D:/VISSIM_runtime/20261023_rolling_cea 의 VBS)이 돎. 건드리지 않음. A0b 는 VISSIM 을 쓰지 않으므로 기다리지 않고 진행, CPU 부하는 재생마다 typeperf 로 적음.
- 할 일: s4_build_inputs.py(바꾸지 않음)로 pristine T001050…T002550 11개를 만들고, run_replay2.ps1(바꾸지 않음)로 env_hsw 재생을 하나씩(라벨 a0b_hsw). 각 결정은 기록 상태와 기록 직전 명령에서 시작(사슬 아님). 도구 sha 는 첫 재생 전에 다음 항목에 적음.

## 2026-10-25 15:44 KST — A0b 사전 고정 (첫 재생 전)
- [실행] 코드 트리 점검(work/a0b/a0b_tree_check.py → tree_check.json): a0/code 가 SOURCE_FILES 3,638/3,638, RESTORED_FILES 3,544/3,544(목록 sha 184a2604…), STANDIN 3/3(목록 sha c80839a9…) 일치. 세 목록 밖 파일 706개 중 705개는 인계 code/ 사본과 바이트 같음(SHA256SUMS·HANDOFF.md 등), 1개는 A0 의 optimized_config_t2390.json(A0b 는 쓰지 않음, 기본 tuning optimized_config.json).
- [실행] 입력 트리: work/a0/s4_build_inputs.py(바꾸지 않음)로 a0/pristine/T001050…T002550 11개 만듦(파일 102–162개, 상태 JSON 경로 재배치 run 6·frozen 1, 직전 명령 .applied UTF-16 재배치 1, 재배치 안 된 경로 0). 각 결정은 기록 상태 + 기록 직전 명령(사슬 아님).
- 고정한 선언과 도구 sha256 [실행]:
  - work/a0/COMPARE_RULE_A0.md a05f20716f5b6056deb0783482523d52dd89c3a60dfc4be6b27609bc2047a634 (A0-CMP-1, 고치지 않음)
  - work/a0b/COMPARE_RULE_A0B.md 6b988a2886db8ac34e80bdb7584ae4b655476d1c2374bf3191f2755bf820eae0 (A0b 선언: T 목록, "처음 다른 T" 정의, 행 목록·크기·시간 적는 법)
  - work/a0/s4_build_inputs.py 72f7a5acdb2423cccfacde4f6ef8f163d7caee7327353e483461681dfea34e19
  - work/a0/run_replay2.ps1 119bbd380a737dc58718c744fba0d8f33f43f84ee4657d274e9698cb9078dc2a
  - work/a0/s5_collect.py 90b1a350f1c05f8f5aa3f39275d893a12af46b850da3aab53e718b3d0020dcb1
  - work/a0/s13_compare.py 02aa1ee297cca2dd49e39b1b877f128ccf69f1133be9b2770f7d9c5ab002bba4
  - work/a0/s20_cmdsummary.py 7633c3d403885dd4b57ecad30cd22d51074fe286d22f5b4df7b6d963ea3c2852
  - work/a0/s29_progress_diff.py a856464879f9d104f9abc54aa8f3315336051f91be152a63df398aac1a9bcba8
  - work/a0b/a0b_rows.py 66632924c56655a5194c9c4c42e4cdae12d616f32c4a08f974886d74c0cdeeff
  - work/a0b/a0b_summary.py 9231b82b28bfdd7d6d817800053fc3319f35b40d7f39c97588f1f1d60e3f88bc
  - work/a0b/a0b_tree_check.py 3ae8ab74c69f0f15ff5c4b7e5ed12e94ffe70998987667135da26774257abc0b
  - work/a0b/run_queue_a0b.ps1 16547a6e18a0ea1ed9ac7de1589ffc21c7ff6b9fcf597777c9f86a1f8a5c95fb
  - work/a0b/launch_wmi_a0b.ps1 7374e20b188f5c3ae6dc4b29c01aad2ae816a7e50e85fd9dda80b3b12d73a42d
- [실행] 도구 시험(A0 의 env_hsw 출력, A0b 데이터 아님, 결과는 work/a0b/smoke/): a0b_rows 가 T=900 0행, T=2700 40행(signal 6·signal_sg 34, SC5·6·105·108·1001·1002), T=4950 17행(SC1·107·1004) — A0_PROFILE §4.1 과 같음. a0b_summary 의 진행 기록 첫 차이(1부터 셈) 900=33·2700=6·4950=21. [읽음] A0 의 "5번째·20번째" 는 s29 의 0부터 센 번호였음(=1부터 6·21번째), VH §3.7 의 900 "33번째" 와 맞음.

## 2026-10-25 15:43 KST — A0b 발사
- 15:42:11 KST launch_wmi_a0b.ps1 → WMI 래퍼 PID 53284(BelowNormal), 첫 재생 T=1050 python PID 49568, 15:42:13 시작. replay_state env 에 OPENBLAS_CORETYPE·NPY_DISABLE_CPU_FEATURES·NUMBA_CPU_NAME·PYTHONHASHSEED=0 이 모두 적힘 [실행].
- [실행] 발사 때 다른 세션 프로세스: VISSIM200 PID 29028, cscript PID 18916, rolling_cea 결정 python PID 45456(state_001800). 건드리지 않음. 그래서 A0b 시간에는 다른 세션 부하가 섞임.
- 고침: 바로 앞 두 항목의 머리 시각 "15:42"·"15:44" 는 어림으로 적은 것. 실제로 두 항목 모두 발사(15:42:11) 전에 썼음(사전 고정 순서는 지켜짐).

## 2026-10-25 18:15 KST — A0b 결과 (재생 11개 모두 종료 0)
- [실행] 대기열 15:42:11–18:08:29 KST(2 h 26 m). 11개 재생 모두 exit 0, 명령 CSV 213행씩 나옴, 대조 도구 세 개 모두 exit 0. 래퍼 PID 53284 와 자식은 스스로 끝남, kill 0. VISSIM·COM·러너 0.
- [실행 a0b_summary.json sha 6e1d4eda…] R1(명령 CSV 바이트)이 기록과 같은 T: 1050·1500·2550. 다른 T: 1200·1350·1650·1800·1950·2100·2250·2400. **처음 다른 T = 1200.** R3(채점 토큰)는 11개 모두 다름.
- [실행] 다른 행 수(signal/signal_sg/ramp_meter): 1200 38(5/32/1), 1350 131(16/114/1), 1650 29, 1800 17, 1950 10, 2100 29, 2250 54, 2400 14, 나머지 0. VSL 행 차 0(11개 모두).
- [실행] 이산 차: 1200·1350 에서 RM_C10646 rate 720 대 540 veh/h, 녹색 8 대 6 s(group 1166.4 대 842.4). 1350 은 신호 16개 녹색 최대 5.385 s(SC1004 p3), 1 s 넘는 녹색 칸 113개, offset 선형 차 최대 148.463 s(주기 끝 감싸기로 보이는 칸 SC11·SC105 포함). 1200 의 offset 최대 0.695 s(SC1004). 그 밖 T 는 녹색 ≤ 0.002 s, offset ≤ 0.207 s.
- [실행] 진행 기록 첫 차이(1부터 셈): R1 같은 세 T 는 32·33·33번째 줄(derivatives_reused key 해시만). 1200·2250 은 6번째(PFO 첫 걸음), 1350·2400 은 9번째, 1650–2100 은 21번째(cap 1 첫 걸음). 작업 수는 1200 만 기록과 다름(요청 105 대 107, 스칼라 롤아웃 69 대 71).
- [실행] 시간: 재생 decision_budget wall 합 8,016.4 s 대 codex 3,348.9 s = 2.394배(T별 2.12–2.54). 최대 1,042.5 s(T=2400, codex 447.8 s). 이 PC CPU 평균 31.8–40.5 %, 다른 세션 VISSIM PID 29028 이 재생 내내 돎.
- 사후 읽기(사전 고정 밖, 데이터 본 뒤에 만든 것이라 따로 밝힘): work/a0b/post_selection_fields.py(sha 048d7810…) → post_selection_fields.json(b92ca567…). selected_objective 차: 1350 −0.898, 1200 −0.0032, 나머지 |차| ≤ 4.2e-4(1050·2550 은 0). 1200 의 held_objective 가 끝자리(−5.7e-14) 다름.
- 디스크 끝: C 29.2 GB, D 271.0 GB.

## 2026-10-25 18:25 KST — A0B.md 작성
- A0B.md (codex_handoff/, 213줄) sha256 7db91c0d411b8bcdb13ba7e2d61a13a366754c454afefe1803488758ab4fc94c.
- 재생 출력 sha 목록 work/a0b/A0B_OUTPUT_SHA256.txt(33줄: 11 T × rows·compare JSON·명령 CSV) sha256 233c0a1c19e8e37d2b9e4dea879c525726804216ec4f269d25c76638e2fc3e35.
- [실행] codex runlog 의 1050–2550 wall_sec 합은 3,356.9 s 로, PRE_A1 r2 U9 의 "3,377 s" 와 20 s 다름(U9 값 출처는 다시 보지 않음). budget wall 합은 3,348.9 s.
- 요약: 처음 다른 T = 1200(RM_C10646 720 대 540 veh/h, SC1004 offset +0.695 s 등 38행). R1 같은 T 1050·1500·2550, 다른 T 8개, R3 는 11개 모두 다름, VSL 차 0. 시간 배수 2.12–2.54(합 2.394), 최대 1,042.5 s @2400. 판정 낱말 없음.
- VISSIM·COM·러너 0, B 폐루프 0, 커밋·푸시 0, kill 0, sealed/·봉인 시드 0, GWT8·frozen·공유 드라이브 쓰기 0. 디스크 C 29.2 GB, D 271.0 GB.

## 2026-10-25 18:20 KST — A1 발사 단계 시작 (PRE_A1 r2 §8)
- 근거: NOTES D-K9-85(sha 67dcc32b… [실행]), PRE_A1 r2(sha 2d9aa15a… [실행]), A0B.md(7db91c0d…). A0b 결과(처음 다른 T = 1200)는 이미 LOG 18:15 항목.
- 고침: 바로 앞 항목 머리 "18:25 KST" 는 이 PC 시계(Get-Date 18:19:00 KST 에 A0B.md 수정 시각 18:13)보다 늦은 어림값임 [실행]. A0B.md 는 18:13 에 쓰였음.
- 디스크 [실행 18:19]: C 29.2 GB, D 271.0 GB 여유.
- [실행 18:19] 이 PC 의 다른 세션 프로세스: VISSIM200 PID 29028(14:16 시작, D:/VISSIM_runtime/20261023_rolling_cea 런, cscript PID 18916, 결정 python PID 32452), TD3 학습 python PID 36468 + tangent 워커 8개(18:15–18:18 시작). 건드리지 않음. 러너는 VISSIM 이 있으면 발사를 거부하므로(run_closedloop3000.ps1:164-172) 발사(5단계)는 PID 29028 이 끝날 때까지 기다림. 1–3단계(동결·사전 점검·env 기록)는 VISSIM 을 띄우지 않으므로 먼저 함.
- 정한 것(PRE_A1 §2, D-K9-85): env_hsw, PYTHONHASHSEED=0, 결정 시한 1,800 s(tuning 바이트 그대로), S1 안 넣음, 차가운 캐시, WMI 분리 발사·우선순위 Normal(러너 -Detached 안 씀), LNC 재사용(NC 팔 안 돌림, -Arms sdmpc).

## 2026-10-25 18:34 KST — A1 1–3단계: 동결 트리·사전 점검·env 기록 (VISSIM 0)
- [실행] 1단계 동결: freeze_manifest.py build 는 원천 W 가 git 작업 트리여야 함(git-state 를 build 앞뒤로 비교, freeze_manifest.py:101-132). a0/code 는 git 저장소가 아님 [실행 rev-parse 128]. 그래서 원천 W = D:/VISSIM_runtime/20261025_codex_a1/source 를 새로 만듦: 빈 git init(커밋·브랜치 만들지 않음) → 인계 사본 저장소(D:/VISSIM_handoff/20261024/code, 읽기만)에서 codex/handoff-rmtsc-20261024 를 fetch → a49981ff 를 detached checkout(4,343 파일, core.autocrlf false, 인계 .gitattributes "* -text") → a0/code 를 robocopy(캐시·*.pyc·A0 전용 optimized_config_t2390.json 제외, 7,890 파일) → git status 는 "??" 3,547줄뿐(수정 0, 무시 0).
- [실행] 동결: 인계 tools/sdmpc31/freeze_worktree.ps1(sha 2f8ff1ea…, 바꾸지 않음) -Source W -FrozenRoot D:/VISSIM_runtime/20261025_codex_a1/frozen → **FREEZE_OK**, FRZ = D:/VISSIM_runtime/20261025_codex_a1/frozen/sdmpc31_a49981ff_202610251820, FREEZE.json sha b56268d988cbbb1cc727f903d77b3e36b341fc338ca39ba776bb17f700bac975, 7,890 파일, 487,316,243 B, git head a49981ff, status 3,547, 217 s. 출력 freeze_worktree.out.txt sha 405eec91….
- [실행 work/a1/a1_tree_check.py sha 32869b5d… → tree_check_a1.json 6b8f6654…] FRZ 에서 SOURCE_FILES 3,638/3,638(목록 sha 5f575512…), RESTORED 3,544/3,544(184a2604…), STANDIN 3/3(c80839a9…) 일치. 목록 밖 705개 모두 인계 code/ 사본과 바이트 같음. FRZ = a0/code(캐시·t2390 뺌) 파일표 완전 일치(바뀜·빠짐·더함 0). FREEZE.json 파일표 = FRZ, git status 경로 = RESTORED+STANDIN 경로. 핵심 파일 sha: 러너 8e95423b·워치독 b56e1b36·VBS 14722088·lane_native_b110.vbs b74e05b2·_sgplan ec731cab·어댑터 a615d8ca·sdmpc.py 5c1ba251·tuning c9088262·망 64cf5f55 모두 PRE_A1 §1 과 같음.
- [실행] 2단계 사전 점검: 내 래퍼(a1_wrapper.ps1)를 WMI 로 띄워 인계 러너를 -PreflightOnly 로 돌림(VISSIM·cscript 0). 1차(v1 래퍼 84c438a4…, PID 47112, 18:28): exit 0, FREEZE_VERIFIED, provenance /env 21키 — RW_PYTHON_EXE="" 하나가 더 있었음. 까닭 [실행]: 사용자 레지스트리 env 에 RW_PYTHON_EXE(=Python312 경로)가 있고, pwsh 7 에서 SetEnvironmentVariable(name, $null) 은 지우지 않고 빈 값으로 남김(러너 :109-111 도 같은 방식). 래퍼를 Remove-Item Env: 로 고친 v2(7a913760…; 발사기 v2 dbcf7048…)로 2차(PID 50388, 18:30): exit 0, FREEZE_VERIFIED, /env 20키 = codex 와 같은 키. 1차 출력은 a1_launch/preflight1_copy/ 에 보존.
- [실행 a1_prov_cmp.py c726cb4a… → prov_cmp_preflight2.json a55144ee…] codex joint provenance 대비: 값이 다른 RW_* 는 RW_OBS150_DETECTORS(동결 경로)·RW_PYTHON(3.12.2 경로) 둘뿐. files 18개 sha 모두 같음(망 64cf5f55, tuning c9088262, 어댑터, VBS, 워치독 등). controller_sources 116·signal_programs 42 차 0. ramp_meter_timing·signal_observation 은 경로만 다르고, observation 은 경로와 FREEZE.json sha 하나만 다름(a1_prov_blocks.py 4a32cf9f…). 워치독 출력: OBS150 kill_policy=pid_only, no_global_kill=True, max_attempts=1, StartupStall 300, StallSec 2400(러너 :161), 시한 1800.
- [실행] 3단계 env 기록: a1/A1_LAUNCH_ENV.json(sha 698de48f…; 도구 a1_env_record.py a26f0b21…). WMI 로 만든 래퍼 안에서 잰 것: 넣은 변수 PYTHONHASHSEED=0·OPENBLAS_CORETYPE=Haswell·NPY_DISABLE_CPU_FEATURES="AVX512F AVX512CD AVX512_SKX AVX512_CLX"·NUMBA_CPU_NAME=haswell, 지운 변수 19개 + RW_* 전부, Python 3.12.2(C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe), 의존성 D:/VISSIM-window264-deps(numpy 2.3.5·scipy 1.18.1·numba 0.67.0·llvmlite 0.49.0·pandas 3.0.1, 모두 그 폴더에서 import), numba CPU 이름 haswell, numpy AVX512F/CD/SKX/CLX 꺼짐, pwsh 7.6.5(codex 런타임). 프로세스 env 전체(이름 99개, 비밀꼴 이름 가림)를 함께 적음. 실제 런 래퍼의 env 는 발사 뒤 같은 파일에 더함.
- 사전 고정(A1 데이터 전): T=900 점검 선언 work/a1/COMPARE_RULE_A1_T900.md sha 14349ed9b22ce5bcfe1f3ef0c37d6d0f24e9af8bec525bb8ec49b50165880b72, 도구 work/a1/a1_t900_check.py sha 2d41cd2a21a6dfb60dc0214447dcbb1891e1e9b18d0a32f4ab1ec74c5fb018b3. 기록끼리 시험(smoke/t900_selfcheck_codex.json 12e248a1…): R1 같음 7/7, 행 차 0, codex 기록 T=900 CSV = A0 env_hsw CSV(A0 결과와 같음).
- 발사 도구: D:/VISSIM_runtime/20261025_codex_a1/launch/a1_launch_wmi.ps1(dbcf7048…), a1_wrapper.ps1(7a913760…). 대기 도구 work/a1/a1_wait_vissim.ps1(sha 아래 줄). 30 s 마다 VISSIM 을 보고, 바뀔 때·270 s 마다·끝에 work/a1/vissim_wait.log 에 적음, 다른 VISSIM 은 건드리지 않음.
- 4단계 상태 [실행 18:33]: 다른 세션 VISSIM PID 29028 이 돎(rolling_cea 런, 결정 sim_sec 3450 까지, 8100 까지 남음). 그래서 기다림 시작. 상한 12 h(2026-10-26 06:34 KST). 넘으면 멈추고 보고.
- 디스크 [실행 18:30]: C 29.2 GB, D 269.8 GB.
- 대기 도구 sha: 26cc67317ec688371eb7b35d687ad81e9c1fac057f709a85e85291bc9b90bf3b

## 2026-10-25 20:06 KST — A1 4단계 대기 중
- [실행] 다른 세션 VISSIM PID 29028 계속 돎(rolling_cea 런 결정 sim_sec 4350 까지). 30 s 마다 확인, 기록은 work/a1/vissim_wait.log. 건드리지 않음. 대기 시작 18:33, 상한 06:34(26일).

## 2026-10-25 21:38 KST — A1 4단계 대기 중
- [실행] 다른 세션 VISSIM PID 29028 계속 돎(rolling_cea 결정 sim_sec 5100 까지). 건드리지 않음. 기록 work/a1/vissim_wait.log.

## 2026-10-25 23:00 KST — A1 4단계 대기 중
- [실행] 다른 세션 VISSIM PID 29028 계속 돎(rolling_cea 결정 sim_sec 6000 까지). 건드리지 않음.

## 2026-10-26 00:13 KST — A1 4단계 대기 중
- [실행] 다른 세션 VISSIM PID 29028 계속 돎(rolling_cea 결정 sim_sec 6900 까지). 건드리지 않음.

## 2026-10-26 00:59 KST — A1 감시 기준 (발사 전 고정)
- 다른 세션 VISSIM PID 29028 은 아직 돎(rolling_cea 결정 sim_sec 7800 까지) [실행]. 건드리지 않음.
- 사용자 정책(5분 무진행이면 확인 뒤 소유 PID 만 kill·한 번 재발사)의 "정상" 을 발사 전에 이렇게 둠 [추론, A0_PROFILE §5.3·PRE_A1 §8.5]: 진행 신호 = 워치독의 목록(runlog·state CSV·action CSV·최신 action_*.json·최신 action_*.joint.progress.jsonl; watchdog:962-998) + WATCHDOG_PROGRESS.txt. 결정 안 진행 기록 간격의 정상 최대 = 199 s(A0). 그래서 "정상 + 5분" = 무진행 499 s 초과. 그 전에는 확인만 함. kill 은 이 런의 PID 만, 재발사는 한 번만, 기록함.
- 감시 도구 work/a1/a1_watch.ps1 sha 7a1fced1c3d26cb0756a4c34f38f887df8463216b524dc7184a8f59af33cadec (읽기만, 30 s 간격, IdleLimit 499).

## 2026-10-26 01:18 KST — A1 발사 (5단계)
- [실행] 대기 끝: 다른 세션 VISSIM PID 29028 이 01:16 무렵 스스로 끝남(그 워치독 기록 "10-26 01:16:07 OK … elapsed=39589s"). 01:16:32 에 VISSIM 0, 01:17:32 에 60 s 넘게 0 확인(vissim_wait.log). 대기 18:33–01:17(6 h 44 m), 12 h 상한 안. kill 0. 01:17:41 에 python·pwsh·cscript·VISSIM 프로세스 0(TD3 학습도 끝나 있었음).
- [실행] 01:17:48.909 KST a1_launch_wmi.ps1 -Mode run(dbcf7048…) → Invoke-CimMethod Win32_Process Create **ReturnValue 0, ProcessId 34448**(래퍼 pwsh 7.6.5, PriorityClass 32 = Normal, 숨김 창, 작업 폴더 = FRZ). 명령줄: "C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "D:\VISSIM_runtime\20261025_codex_a1\launch\a1_wrapper.ps1". 영수증 D:/VISSIM_runs/20261025_codex_a1_s29/a1_launch/wmi_launch_run.json. 발사 때 디스크 C 30.2 GB, D 264.6 GB, VISSIM 0.
- [실행] 01:18:03 프로세스: 래퍼 34448 → 러너 pwsh 43828(01:17:54, Normal, run_closedloop3000.ps1 -FrozenTree FRZ -ResultsRoot D:/VISSIM_runs/20261025_codex_a1_s29 -StatusPath …/native_status.json -SimPeriod 8100 -Arms sdmpc -TuningRelativePath …/native413_adopted355/optimized_config.json -PythonExe Python312 -PowerShellExe codex 런타임 pwsh -DependenciesPath D:/VISSIM-window264-deps) → freeze_manifest verify python 54248. 래퍼 env·python 기록은 a1_launch/wrapper_run_*.json.

## 2026-10-26 01:43 KST — A1 T=900 끝남 (6단계) · A1_LAUNCH.md
- [실행] 01:18–01:20: 러너 동결 검사 약 90 s 뒤 워치독 pwsh 43080(01:19:25) → cscript 48380(01:19:28), VISSIM 40024(01:19:32, 부모 svchost PID 1204). 워치독 "KILL_POLICY … pid_only", "VISSIM_PROCESS … pid=40024".
- [실행] 준비 결정 T=1…750 모두 exit 0(11.2–16.4 s, codex 5.7–8.2 s). T=900: state 01:27:25 → action CSV 01:34:04, runlog wall 400.74 s, exit 0, decision_budget 399.72 s(codex 228.81 s, 1.747배). 시한 1,800 s 에 닿지 않음.
- [실행 a1_t900_check.py 2d41cd2a…(발사 전 고정) → work/a1/t900_check_a1.json a9b137ea…] T=900 명령 CSV sha 5be7a91b… = codex 기록 = A0 env_hsw 재생(R1 같음, 213행 중 다른 행 0). R2 다섯 칸 둘 다 같음. R3 셋 다 다름(A1 942da6fd…, codex 3a34ccae…, A0 84cfeb38…). T=1…750 CSV 도 codex 와 6/6 같음. 입력: state_000900.json 잎 28,910 중 28,898 같음(다름 = 해시 6, run_id 3, mer byte_start·byte_end, mer max_t_any 899.97 대 899.89), derived_000900.json 6,986 중 6,979 같음(해시 5, run_id, lag/max_t_any). 경로·시계 잎 차 0.
- [실행 01:40] T=1050 결정 진행 중(01:36:03 시작), VISSIM 40024 살아 있음, native_status stage native_running, 결과 폴더 241 MB. 디스크 C 30.2 GB, D 264.3 GB.
- 고침: 18:3x 항목의 "프로세스 env 전체(이름 99개…)" 는 틀림. 이름은 46개임(99 는 1차 env 파일의 줄 수) [실행]. 런 래퍼 env 는 2차 사전 점검 env 와 이름·값 모두 같음(차 0).
- 산출: a1/A1_LAUNCH.md(sha 227ac13ef1932c91cc7b22344ecd730e68db1aa4fafd43ce8bd797b8eb75adfe), a1/A1_LAUNCH_ENV.json(4faf4da5…). 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/a1/.
- VISSIM 은 A1 하나만 띄움. kill 0, 재발사 0, B 폐루프 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0.

## 2026-10-26 01:52 KST — V-A r4 고침 메모 단계 시작 (D-K9-87)
- 할 일: V-A 보고 r3(`k92/va/analysis/VA_REPORT.md`, sha b57022e6… [실행 01:51 일치])의 ④b(입력별·합)·④·Ω 밖 (a) 칸을 첫 관측 차분으로 다시 셈. 9런(V-A·J1·NC3 × v3c3-s31/41/43). r3 바이트는 그대로 두고 메모 `VA_REPORT_r4_CORRECTION.md` 를 붙임. 데이터 뒤 방법 변경(사용자 결정 D-K9-87)임을 공개.
- 작업 폴더: `k92/va/analysis/r4/`(새로 만듦). 런 폴더·NC3·J1·인계 사본·GWT8·frozen 은 읽기만.
- A1 은 돌고 있음(VISSIM PID 40024, T=1200 결정 중 [실행 01:46]). 무거운 일은 BELOW_NORMAL, 한 번에 하나, A1 결정 벽시계가 1,500 s 를 넘으면 멈춤. VISSIM 은 띄우지 않음.
- 순서: 규칙·도구를 쓰고 합성 자료로만 자기 시험 → sha 고정(이 LOG) → FZP 첫 관측 스캔 9개(하나씩) → 본 계산 → 메모.
- 디스크 [실행 01:4x]: C 31 GB, D 265 GB 여유.

## 2026-10-26 01:52 KST — B0 시작 (codex 판 v3c3 이식 준비, VISSIM 0)
- 근거: NOTES D-K9-84 Q6·D-K9-86·D-K9-87(NOTES sha 67dcc32b… [실행]), TAKEOVER_PLAN r2 §1.2(b75ad041… [실행]), HANDOFF_RESULTS r2 §3(964a23ce… [실행]), PRE_A1 r2(2d9aa15a… [실행]).
- 자리: 트리 D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/code, 작업 폴더 work/b0/, 보고 폴더 b0/. GWT8·D:/VISSIM-merge/frozen·인계 사본·런 폴더는 읽기만.
- [실행] b0/code = a0/code 를 robocopy(캐시·*.pyc·t2390 제외) 뒤 복사된 __tangentcache__ 116개를 지움 → 7,890 파일, A1 FRZ 의 FREEZE.json 파일표와 바뀜·더함·빠짐 0(work/b0/b0_tree_check.py 64fcbb1c… → tree_check_baseline.json 060279c9…). 이 상태가 B0 편집의 출발점.
- 이 PC: A1(VISSIM PID 40024, 래퍼 34448) 이 돎. B0 의 무거운 재생은 A1 규칙대로 BELOW_NORMAL, 한 번에 하나, A1 결정 벽시계가 1,500 s 를 넘으면 멈춤. 가벼운 읽기·편집·설정 단계 시험은 겹쳐 함. 디스크 C 31 GB, D 264 GB.

## 2026-10-26 01:44 KST — A1 대기·분석 단계 시작
- [실행 01:44] A1 돎: VISSIM 40024, 마지막 결정 줄 T=1050(wall 445.76 s, exit 0), T=1200 진행 중, stage native_running. 디스크 C 30.2 GB, D 264.2 GB.
- 감시: work/a1/a1_watch.ps1(7a1fced1…, 읽기만) 를 한 번에 ≤ 9 분씩. 무진행 499 s 넘으면 확인 뒤 이 런 PID 만 kill·한 번 재발사(01:00 항목 기준 그대로).
- 분석 도구는 A1 출력(T ≥ 1050 결정 내용·FZP·지표)을 읽기 전에 work/a1/full/ 에 만들고, codex 자료로 자기 시험(--smoke) 뒤 sha 를 여기에 적음. 선언 work/a1/full/COMPARE_RULE_A1_FULL.md.
- [실행] PRE_A1 §5 고정 도구 sha 다시 확인: scan_fzp.py c8a6e5c4…, metrics.py b524b51b…, uninserted2.py bc3b4849…, vhr_firstseen.py 42e17585…, vhr_unins.py fc233013…, fullhash.py 32f9bf44…, omega701_recount.py 5b7826f6… — 모두 PRE_A1 §5 와 같음.
- [실행 01:5x] 자기 시험 체인 WMI 발사(run_a1_analysis.ps1 -Smoke, BELOW_NORMAL, PID 42624). codex 기록·LNC·A0b 출력만 읽음. A1 자료 0.

## 2026-10-26 02:01 KST — V-A r4: 규칙·도구 고정 (r4 숫자 내기 전)
- 규칙 `k92/va/analysis/r4/COMPARE_RULE_R4.md` sha256 349bd69d9074318d1f4ed3f29d706fffcd74af05bb0a01f8c15b8b92364ca363.
- 고정 목록 `r4/R4_PINS.sha256` sha256 1ca353a937ae81cc10bedbf46ee49cadca30012f0f97926d5e0235790841a29f (8줄): r4_common cd8b777e…, r4_fzp_first 6548de5e…, r4_firstobs 49b0d3e7…, r4_selftest 9e125512…, r4_memo_build f05639cc…, r4_driver 0988188e…, r4_launch 07f49fde…. 고치지 않고 import: va_common 49681fa9…, va_report_build 651812cd….
- [실행] 자기 시험(합성 자료만) `r4/selftest/selftest.json` sha256 dec45d3f… ALL_OK 8/8(격자 = 닫힌 꼴, 첫 관측 항등식 무차별 대조, 합성 FZP 스캔, vhr 식, 표시·통계, 파이프라인 건식 실행). 건식 실행은 첫 관측 시각을 난수로 바꾼 뒤 돌려 실제 ④b 값은 내지 않았음. `--preflight`(구조만) stops 0.
- 공개: 9런 [0, 9000] 꼴 ④b 합은 VERIFY_HANDOFF_RESULTS §2.2 에 이미 있음(규칙 §1). 이번 고침은 데이터 뒤 방법 변경(사용자 결정 D-K9-87).
- [실행 01:59] 다른 python: A1 결정 PID 53872(T=1350), 다른 작업 PID 34072(`codex_handoff/work/a1/full/a1_trace.py --smoke`, BELOW_NORMAL). 드라이버는 A1·r4 가 아닌 python 이 돌면 기다림(한 번에 하나).

## 2026-10-26 02:05 KST — V-A r4: 드라이버 v1 멈춤 → v2 (실행 감싸개만 고침, 공개)
- [실행] 02:00:58 r4_launch.ps1 → WMI ReturnValue 0, 드라이버 PID 31276(BELOW_NORMAL). 첫 단계 `r4_fzp_first.py va_s31`(PID 14344)은 8.2 s 에 끝났고 출력도 정상(차량 67,343, 행 6,510,368, 0.10 s 행 1개 건너뜀, 프레임 1,799, 5.1–8,995.1 s, 불규칙 0, stderr 0 B). 그런데 드라이버가 종료 코드를 빈 값으로 읽어 "ABORT" 하고 멈춤.
- 까닭 [실행]: Windows PowerShell 5.1 의 `Start-Process -PassThru` 는 프로세스 핸들을 먼저 읽지 않으면 ExitCode 가 비어 있음. 같은 꼴 시험(`$null = $p.Handle` 를 넣으면 종료 코드가 채워짐)으로 확인.
- 고침: 고정한 `r4_driver.ps1`·`r4_launch.ps1` 은 그대로 둠. 새 파일 `r4_driver_v2.ps1`(sha256 732ab60f019771afb97f397a4c276e352cf9d25f96fc2312b016edd2ac5f1676; v1 대비 `$null = $p.Handle` 한 줄과 로그 이름·머리 주석만 다름)와 `r4_launch_v2.ps1`(0ff6007a8a4d5cd3cf762b9870904b55605f8aded98ea592b98b579e5b29eeb9; 띄우는 파일 이름만 다름)을 씀. 분석 도구(r4_common·r4_fzp_first·r4_firstobs·r4_memo_build)와 규칙은 바꾸지 않음(R4_PINS 8/8 OK). v2 는 9개 스캔을 처음부터 다시 돌림. v1 의 va_s31 출력은 `r4/logs/attempt1_fzp_first_va_s31.json`(sha256 ca2c9c7c…)으로 남김. 이 시점까지 r4 값(④b 차 등)은 하나도 계산하지 않았음.

## 2026-10-26 02:02 KST — A1 전체 대조 선언·도구 고정 (A1 출력 T ≥ 1050 을 읽기 전)
- 선언 work/a1/full/COMPARE_RULE_A1_FULL.md sha256 0d69b1246e914c3b1a8e9cca1cda3e8a9b28c27e7eaad7da58eda34756eba0b0
- 도구 sha256 (work/a1/full/, 목록 TOOLS_SHA256_A1_FULL.txt 8ccf75fb…):
  - a1_trace.py f56f24cfcd14aff759c849a54690160e115e356e3ecb24c0f565c71348ec2f82
  - a1_fzp_firstdiff.py 009247032fab7eb359d9537a75244eadf2f4445b62b622b83c41174bd0091402
  - scan_fzp_a1.py e4009bdb7bdeab59fa67884c1f32ffc5ca8d6cbb5e6a121f41f37209be3994f9 (← rawcheck/scan_fzp.py c8a6e5c4…, 차 = OUT 경로·a1 경로·--smoke)
  - metrics_a1.py 94ff93fec83ec49cea7c0751c9607848efa7286a42962c8b05d56d1a58cd8a55 (← rawcheck/metrics.py b524b51b…, 차 = a1 조건·읽기/쓰기 경로)
  - vhr_firstseen_a1.py c66f95e2c0179ff3e647f9a6578df9dfafe2e029b939181563f255d86bba0725 (← vhr/vhr_firstseen.py 42e17585…, 차 = OUT·a1·lnc 경로·--smoke)
  - unins_a1.py 2d733ac866d2a5962ddf147ec1d0b3e2948b4f881a5de2f81073a7cc7e242eb9 (vhr_unins.py fc233013… 의 S_int·dU 그대로, 짝 목록 A1 용)
  - a1_ours.py 7f38613e08d2e7b6f593f928d8fb429fa79d92338027688bd9f48a8beaf8ee80 (omega701_recount.py 5b7826f6… sha 확인 뒤 import)
  - a1_table.py 733f400eac96a70b7d678eff5a64e77abb650f3ea0ed684e7103241253fd5322 (분할 함수 = metrics.py 글자 그대로)
  - run_a1_analysis.ps1 7cd6801da733eac990e8da57a8237acae540e605ec57f7c5f0f52589a37c3df7, launch_wmi_analysis.ps1 251c7419867c11b05da3fd550ef4108f542a4455971d03cf0a8b45d26fb43084
- [실행] 자기 시험(--smoke, A1 자리에 codex joint, 01:54:36–01:59:45 KST, BELOW_NORMAL, 모든 단계 exit 0):
  - 결정 55개 모두 R1 같음, 다른 행 0, 상태·derived 값 잎 차 0. 유지 T=6900 하나(ValueError) 그대로 읽힘. codex 대 A0b 칸은 A0B.md 와 같음(R1 같음 1050·1500·2550, 처음 다른 1200 38행 signal 5/signal_sg 32/ramp_meter 1).
  - FZP: a1(=joint)–joint 다른 프레임 0, 접두 ≤ 895.1 같음. joint–LNC 처음 다른 프레임 905.1 s(1,619 중 1,439 프레임 다름).
  - 표: A1 − LNC = joint − NC = Ω701 −494.7, Ω635 −407.9, ④a −449.0, ④b(첫 관측) −221.3, ④ −670.3, Ω 밖 (a) −175.6 / (b) +45.7(Ω701), ① −283.7, ② −156.6, 도시도로 codex −294.6 / 우리 −377.1, 진입 E/W(우리) +142.8/+35.3, 입력별 +97.0/−69.2/−249.0, 링크 66 −51.0. A1 − joint 모든 칸 0. RAW_CHECK §5.2·HR §1.1 값과 같음. 내부 검산: 분할 대 metrics_a1 차 0, LNC 대 NC 링크 차 0, 두 스캐너 codex 꼴 차 ≤ 1.4e-12. 첫 관측 1098 링크 74 수 16,070, 1099 도착 20,166, LNC 첫 관측 = codex NC 첫 관측.
  - 시험 출력 sha 목록 work/a1/full/SMOKE_OUTPUT_SHA256.txt.
- 이 항목 뒤로 도구·선언은 바꾸지 않음. A1 데이터는 런이 끝난 뒤 run_a1_analysis.ps1(-Smoke 없이)로만 읽음.

## 2026-10-26 02:09 KST — V-A r4 고침 메모 끝 (D-K9-87)
- 고침: 바로 앞 항목 머리 "02:05 KST" 는 어림값. 실제로는 v2 발사(02:02:08) 전에 썼음 [실행: v2 런처 출력 시각].
- [실행] 드라이버 v2 PID 11544(02:02:08–02:03:48 KST): FZP 첫 관측 스캔 9개 하나씩(각 9–11 s, exit 0), `r4_firstobs.py` exit 0(3 s). WAIT 0줄(단계 시작 때 A1 결정 나이 0 s, 다른 python 없음). v1 의 va_s31 출력은 v2 출력과 `scan_sec` 만 다름.
- [실행] 점검 C1–C7 통과(STOP 0), C8 900 s 전 d④b 12짝 모두 0. 새 FZP 스캔 대 stage-1 짝 d④b 차 최대 1.1e-11 veh·h. VERIFY §2.2 [0, 9000] 꼴 9칸 재현(|차| ≤ 0.05). 창 효과 −0.25 ~ +0.23.
- [실행] 결과(짝 차 d, veh·h, s31/s41/s43): 짝 A ④b −174.1/−105.6/−62.0(r3 −168.0/−117.5/−58.6), ④ −373.8/−506.2/−356.4, Ω 밖 (a) +115.6/+153.1/+260.1(③ −489.3/−659.3/−616.5 그대로). 짝 B ④b +90.2/+28.9/−52.1(r3 +103.4/+28.5/−15.2), ④ −475.4/+27.2/−549.7, Ω 밖 (a) −4.7/−39.4/−136.8(r3 +8.5/−39.8/−99.9; ③ −470.6/+66.7/−412.9 그대로). J1R ④b −264.3/−134.5/−9.8, Ω 밖 (a) +120.3/+192.5/+396.9.
- [실행] 표시 규칙: 바뀐 칸 1개 = 짝 B v3c3-s31 읽는 법 N "대기 이전(Ω 밖으로)" → "같은 방향(K8 §5.5 표시 조건 충족, 판정 아님)". 같은 칸 W(제거 A·B) 그대로(d④b +90.2 > 0). 짝 A 전부, 짝 B 평균 그대로(평균 d④b +22.3). J1R 참고 표시 그대로. J1R Ω 밖 (a) CI 표시 "관측된 차이" → "0 포함".
- [실행] 대조 504칸 중 글자 바뀜 386, 엄격 부호 바뀜 12(짝 B s31 Ω 밖 (a) 여섯 자리, 짝 B 평균 3,600 s 누적 Ω 밖 (a), J1R Ω 밖 (a) CI 아래 끝, 입력 1083 몫 0 근처 4칸).
- 산출(sha256): 메모 `k92/va/analysis/VA_REPORT_r4_CORRECTION.md` 6127ce413153e41c5d12776ac501b850d273b85d7476854a6fe232b13a638225(375줄, 금지 낱말·Ω 표 점검 통과), r4_firstobs.json a8f2df7b…, r4_cells.csv f62d8fd1…, r4_tables.json 94e1822c…, memo_src.md f2e508b2…. r3 `VA_REPORT.md` b57022e6… 그대로.
- 사본: `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va/VA_REPORT_r4_CORRECTION.md`(+ .sha256, OK), 같은 것 `…/k92_va/analysis/`, r4 폴더 전체 `…/k92_va/analysis/r4/`(53파일, 바이트 같음).
- VISSIM·COM·러너 띄움 0(이 단계), kill 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0. 디스크 C 31 GB, D 264 GB. A1 은 계속 돎(sim_sec 1500 [실행 02:08]).

## 2026-10-26 02:12 KST — 표 서식 도구 고정 (A1 데이터 전)
- work/a1/full/a1_compose.py sha256 5f39df13358c81bc05fdd76401564cde414e6d8d7b5a0f06b643804d8a4ffdda — trace·fzpdiff·a1_table JSON 을 Markdown 표로만 바꿈(새 숫자 없음, 차·배수만). 자기 시험 출력 compose_smoke.md b0814252…(표 칸이 02:02 항목의 값과 같음).
- [실행 02:0x] A1: 마지막 결정 줄 T=1500(wall 545.65 s, exit 0), VISSIM 40024 살아 있음.

## 2026-10-26 02:22 KST — 다른 세션 VISSIM 이 A1 도중 뜸 (건드리지 않음)
- [실행 02:21] 다른 세션 프로세스: pwsh 44508(02:20:38, C:/Users/TRLAB/Documents/ChatGPT/RL/work/vissim_td3_run… 래퍼) → pwsh 32080 → cscript 27480(…/vissim_td3_runtime/sdmpc31_9a8320ec_20261026021817/scripts/run_real_world_stackelberg_controller.vbs) → VISSIM200 PID 48616(02:20:52, 부모 svchost 1204). 우리 소유 PID(34448·43828·43080·48380·40024)와 겹치지 않음. kill 0.
- PRE_A1 U4(a) 는 A1 혼자를 권장했으나 다른 세션 일정은 사용자 몫임. 이 때부터 A1 결정 벽시계에 동시 VISSIM 몫이 섞일 수 있음(크기는 재지 않음). 결과 보고에 밝힘.
- A1: 마지막 결정 줄 T=1650(wall 425.26 s, exit 0), 진행 중.

## 2026-10-26 02:49 KST — B0 재핀·설정 단계 점검 끝, 재생 선언 고정 (재생 전)
- [실행] 재핀 생성기 work/b0/b0_make_v3c3.py(5bb3941e…) → b0/code/diagnostics/b0_v3c3/ 98 파일 기록(B0_REPIN_RECEIPT.json 7b2e61a8…). B 설정 config_b0_v3c3.json **729640af…**(codex c9088262 대비 잎 편집 30), 대조용 config_b0_v3c3_groupkeys.json e8a5730a…(램프 도착 예측 객체 하나만 codex 원래 값).
  - Ω701 v3c3 = codex 빌더(build_control_area_membership.expand…)를 우리 v3c3 Ω635 에 돌림 → inside 701/outside 535 = codex 집합. 경로 계약 = prepare_next 경로 부분 → codex approaches_only/route_contract.json 과 **바이트 같음**(turn 57개 갱신).
  - 우리 v3c3 팩 문서 8개를 prepare_next 재결속 규칙으로 Ω701 에 묶음(연결자 지원 29개 = codex 와 같은 수). 나머지 5개는 우리 팩 그대로 가리킴.
  - lane plant manifest: 망·geometry(우리 v3c3)·sig manifest·Ω701·검지표 경로 재핀, reference config = eval_036 에서 FW_E sign_cells[5] 16→18 한 칸만.
  - codex 계약 10개(native_beta·goal8 authority 덧씌움, sc6_queue 3·sc1_supply·urban66_u7·unrouted10646·head proof 2·head47 support)는 망 핀·참조만 바꿈(내용은 64cf 유도 그대로) — 런타임 검사가 v3c3 에서 판단.
  - 결정: VSL 고정 110 = codex off_config 객체 그대로, calibrated_aggregate 키 지움, RM_C 키 8개+strict_ramp_keys(V-A 설정 c8e3ee2c 값), decision_error_policy=hold_previous_on_exception·decision_timeout_sec 지움.
- [실행] 코드 고침 work/b0/b0_code_patches.py(18858467…, 영수증 cffd1f02…): physical_movement_routes.py(F1 v3c1 결정 1160 검토 함수, 우리 :442-484·:555-556 이식), control_area_objective.py(F2 유령 경로 별칭, 우리 :252-273·:651-663·:745·:759-766), lane_offramp_runtime.py(F3 v3c3 1133:2 가 링크 70 에서 끝나면 10638 꼬리표 안 붙임 = 우리 :109), 워치독(H1 hold_previous_on_exception 받음, 시한 키 거부). 트리 점검 tree_check_prereplay.json(cdf8369f…): 바뀜 4, 더함 99, 빠짐 0.
- [실행] 설정 단계 탐침(b0_probe_main.py 4d1caa81…, configure 끝에서 멈춤) 15번: 멈춘 자리 차례 = lane plant 망 → 검지표 sidecar → native choice → phase authority → head-free → head resource → route proof(10691) → provenance(plant_n31_v2) → 결정 1160 → 10638 연속 경로 → VSL 노출 이력(V-A 3,450 s 부터 101) → 고정 VSL 키. 고친 뒤 T=3,450·1,800·그룹키 T=3,450 셋 모두 B0_PROBE_CONFIGURE_DONE(25–32 s).
- [실행] 워치독 -PreflightOnly(b0 트리, v3c3 망, B 설정): wd06 exit 0, RW_DECISION_ERROR_POLICY=hold_previous_on_exception, obs150 detectors 294행, freeze=null(동결 전). wd03·wd05 는 내 래퍼의 튜닝 경로 오타(백스페이스 문자)로 실패, 버림.
- 재생 선언(데이터 전 고정): work/b0/COMPARE_RULE_B0.md **438027db387574e637d055ae500273ad8b2b8d84361d229304dbb69bec6333a4**. 도구: run_queue_b0.ps1 8c3764a8e3fb6d6072c50f26cc099c43e81d4b47230368b3e8a25138dc4cc629, run_replay_b0.ps1 1b32085d6ac52148d16ec2e9736f4914558aad0c046c4e71c95fb163651a04df, b0_replay_summary.py b20edbf4c1afa01a68522ade9fee98dfecc95af2c5ec29d3e120cd26be06c940, b0_build_inputs.py 62dabb59a215859c7426aceddceaca2b8e0c6892a3ac43e1a177bee48968aff8, b0_probe_main.py 4d1caa81b801468008343fd90cbe7e708128dde8d3831263900c23b51bb518df, launch_wmi_b0.ps1 07b1516586b99f5df216c16dee4c834c10f6e0f6025d230ea399a5d2e211ef11, a0/s5_collect.py 90b1a350f1c05f8f5aa3f39275d893a12af46b850da3aab53e718b3d0020dcb1. 재생 R1(va_s31 T=3450 B 설정)·R2(같은 T, 그룹키)·R3(T=1800 B 설정) 차례.
- A1 [실행 02:48]: T=1950 까지 끝, 결정 벽시계 354–645 s. 디스크 C 31 GB, D 263 GB 무렵.

## 2026-10-26 02:57 KST — B0 재생 R1–R3 결과 (선언대로 셋, 모두 같은 자리에서 멈춤) · 재생 중단
- [실행] 대기열 run_queue_b0.ps1(8c3764a8…) 02:48:56–02:51:57, WMI 래퍼 PID 23272(BelowNormal), python BelowNormal. A1 보호 발동 0(재생이 짧아 A1 결정 1,500 s 초과 없음). kill 0.
- [실행 b0_replay_summary.json 64aca804…] R1(va_s31 T=3450 B 설정) exit 1, 56.4 s · R2(같은 T, 그룹키) exit 1, 41.3 s · R3(T=1800) exit 1, 50.4 s. 셋 다 `ValueError: SDMPC prior price/application context mismatch` (sdmpc.py:783 load_prices ← :813 solve ← adapter :12681 run_joint_owner_decision). 설정 단계는 지났고 결정 풀이 첫머리에서 멈춤. 명령 CSV·decision_budget 없음.
- [읽음 sdmpc.py:770-787] 까닭: 직전 명령(V-A 우리 제어기 출력)의 metadata.sdmpc_state 가 있으면 .applied 영수증과 `policy_sha256 == policy_token(policy)` 를 요구함. V-A 의 SDMPC 정책 토큰은 codex B 설정과 다름 → 재생 장치의 한계(다른 제어기의 직전 명령). B 폐루프에서는 직전 명령이 codex 자기 출력이라 이 검사는 같은 런 안에서 맞춰짐 [추론]. 직전 명령에 sdmpc_state 가 없는 T=900(워밍업 직후 첫 제어 결정)은 'first_sdmpc_decision' 길로 감 [읽음 :772-774].
- [실행] 열기 기록(opens.tsv 2,351줄씩): 대역 3개(flow279·sc107_shared316·sc109_transport317)와 native348/calibration.json 열기 0 — calibrated_aggregate 끔에서 설정 단계와 풀이 첫머리까지 이 파일들이 안 읽힘(B-1 부분 확인).
- 선언(COMPARE_RULE_B0.md 438027db…)의 재생 셋은 그대로는 v3c3 결정 시간을 낼 수 없음이 드러남. 과제 규칙(재생 1–3회, 쓰인 대로 불가하면 멈추고 보고)에 따라 **추가 재생은 하지 않음**. T=900 재생(또는 사슬 재생)은 새 선언과 별도 허락이 있어야 함 → B0.md 열린 일.
- 도구 결함(데이터 해석은 바꾸지 않음): b0_replay_summary.py 는 수집 폴더를 `files/run/<결정폴더>` 로 찾지만 run_replay_b0.ps1 의 s5_collect 는 `files/<결정폴더>` 로 모음. 그래서 요약의 budget·진행·CSV 칸은 None(셋 모두 그 출력이 원래 없음, 진행 기록 파일도 없음 [실행 ls]). exit·예외·벽시계·열기 칸은 영향 없음.
- 재생 중(02:5x) 코드 고침 H2(control_hold.py 함수 추가·write_hold 정책 분기)와 H3(VBS)·H1 보완(워치독 RW_DECISION_HOLD_PREVIOUS=1, 시한 0)을 b0 트리에 적용함. 재생이 쓰는 결정 경로(validate_fixed_vsl·fixed_vsl_values)는 글자 그대로라 재생 결과에 영향 없음 [읽음 패치 내용]. 밝혀 둠.

## 2026-10-26 03:01 KST — B0 고침 더함(유지·러너) 시험, 동결 연습 시작, 램프 도착 점검 도구 고정
- 고침 [실행 b0_code_patches.py → code_patches_receipt.json]: H1 보완(워치독: hold_previous_on_exception 이면 RW_DECISION_HOLD_PREVIOUS=1·RW_DECISION_TIMEOUT_SEC=0 → VBS 는 시한 없이 RunCapture3), H2(control_hold.write_hold 가 그 정책을 받되 먼저 우리 decision_hold.py:49-63 의 목록으로 자격 검사: 실패 보고 .error.txt 필수, 제외 예외 8종·직전 명령 계약 함수 9개·계약 메시지 1개면 거부), H3(VBS: codex 유지 길을 ExceptionHoldGate 로 거름 = exit 1 + .error.txt + 첫 제어 결정 아님 + 워밍업 제어기 아님, 요약 줄 DECISIONS_HELD_ON_EXCEPTION), N1(러너 -NetworkRelativePath/-NetworkSha256, 기본값 = codex 64cf).
- 앞 항목 고침: H2·H3 적용 시각은 02:51:08(파일 수정 시각 [실행]) = R3 실행 중(R1·R2 뒤).
- [실행] 유지 시험 work/b0/test_hold_b0.py(A0 기록 T=1050 상태 + 기록 직전 명령, 임시 폴더): 6/6 기대대로 — ValueError 유지 / TimeoutError·BrokenProcessPool·load_prices 프레임·보고 없음 거부 / codex hold_previous 정책은 보고 없이 유지(A 동작 그대로). 결과 hold_test/test_hold_b0.json.
- [실행] VBS 시험 vbs_test/make_harness.py → cscript(VISSIM·COM 없음, FileSystemObject·WScript.Shell 만): 고친 RunControllerDecision·고치기 전 것 모두 컴파일, ExceptionHoldGate 7/7, 고친 If 문 3/3 기대 분기. PowerShell 구문 분석: 러너·워치독 오류 0.
- 동결 연습(work/b0/b0_freeze_preflight.ps1, WMI PID 35148, BelowNormal): 새 git 저장소(커밋·브랜치 없음)에 인계 사본에서 a49981ff 를 fetch·detached → b0/code 덮어쓰기 → git status 3,653줄, 수정 7(고친 파일). 첫 시도(02:57)는 core.longpaths 미설정으로 checkout 실패, 지우고 다시 함(A1 source 설정과 같게 longpaths·safecrlf).
- 램프 도착 점검(설정 단계까지만, 결정 없음) 도구 고정: b0_probe_rampfc.py 9c2120d176f6093ec0c349b62eb149401caa6c495a8d4d9e7ce562369172a29f, run_rampfc_b0.ps1 e653ce03299a8c018c3ab4ae902b147c22987355d4a14132d107a02419016ef4. 적는 것: 설정된 램프 키·on_ramp_to_movement·gate_onramp_queue_ramps·램프 용량, 같은 상태에서 B0 예측 객체(RM_C·strict)와 codex 그룹키 객체 각각의 profiled_demand_rates 램프 도착값. 판정 없음.

## 2026-10-26 03:04 KST — B0 동결 연습·러너 사전 점검(v3c3) 통과, 램프 도착 점검 결과
- [실행] freeze_worktree.ps1(codex, 바꾸지 않음) → **FREEZE_OK** FRZ_B0 = D:/VISSIM-merge/k8_gate_trees/codexhandoff/b0/frozen/sdmpc31_a49981ff_202610260258, FREEZE.json **853d1c4fb97ed3de4cf62a409b06b9001648ce56171e2ed826236bdddb1506c6**, 7,989 파일, 495,607,788 B, head a49981ff, git status 3,653(수정 7), 200.3 s.
- [실행] 고친 러너 run_closedloop3000.ps1 -PreflightOnly -FrozenTree FRZ_B0 -SimPeriod 9000 -Seed 31 -Arms sdmpc -TuningRelativePath diagnostics/b0_v3c3/config_b0_v3c3.json -NetworkRelativePath …/baseline_s31_v3c3nc.inpx -NetworkSha256 3de889f0… → exit 0, FREEZE_VERIFIED, status preflight_complete. provenance(ece04055…): 망 3de889f0, 튜닝 729640af, freeze 핀 853d1c4f, RW_DECISION_ERROR_POLICY=hold_previous_on_exception·RW_DECISION_HOLD_PREVIOUS=1·RW_DECISION_TIMEOUT_SEC=0, plant manifest 11842498…, 검지 294행. VISSIM·cscript 0.
- [실행] 램프 도착 점검(설정 단계만, rampfc.json T=3450 96ab40b5…, T=1800 b2717d89…): 램프 키 8개 모두 RM_C. on_ramp_to_movement 가 비지 않은 램프 = RM_C10482·RM_C10490·RM_C10639 셋, gate_onramp_queue_ramps = 10480·10482·10639·10681·10490·10484. 예측 합(veh/h) B0(RM_C·strict) 5,242.6 대 codex 그룹키 2,790.0 (T=3450), 5,247.5 대 2,910.0 (T=1800). 그룹키 쪽 값은 모두 30 의 배수(120 s 폴백), 상한 900.
- [읽음·추론] 예측 소비처: 도시 착지(urban_flow_accounting.py:433-456)는 on_ramp_to_movement 가 있는 램프만 쓰고, leg split 경로(ADP:2984-2990, UFA:874-880)가 gate 램프의 착지를 0 으로 둠 → 이 설정에서 착지 0 인 램프 = 셋 모두 [추론: /urban/ramp/leg_split·boundary_out/ramp_split true]. 고속도로 회계(area_freeway_accounting.py:164-171)는 결합 경로가 update_ramp_queues=False(:611, lane_freeway_runtime.py:187). 메타데이터(ADP:13211-13217)는 합과 옛 그룹키 4칸(RM_C 에선 늘 0). vendor NumSim 제어기의 소비(leader.py:457 등)는 결정 경로에 있는지 런타임으로 확인하지 못함. 그래서 "RM_C 키가 lane plant 예측을 바꾸는가" 는 결정 대조 재생(T=900, 새 선언 필요)으로만 닫힘.
- 디스크 C 30 GB, D 261 GB. A1 T=2100 까지(결정 415–679 s).

## 2026-10-26 03:10 KST — B0.md·PRE_B.md 작성 (B0 이번 단계 끝)
- 산출: codex_handoff/b0/B0.md sha256 b7216dd06b3e11986739e6a36f1407e001a325682e23715a46e504dbc95f8df7, codex_handoff/b0/PRE_B.md sha256 3149cfe520a3025fb42b296c967e53660fdbb19fc75ea7846acf8bd9491ec1eb (계획만, 발사 허락 아님).
- [실행] 유령 별칭 시험 work/b0/test_alias_b0.py(e30cca5e…) → test_alias_b0.json(f10a4a2b…): v3c3 Ω701 경로 계약의 유령 키 3개 확률 null·형제 3개 숫자, 별칭 없으면 MembershipError, 있으면 형제 확률로 기록·`phantom_route_alias:` 셈, 유령 아닌 이전 그대로.
- [실행] 마지막 트리 점검 tree_check_final.json = tree_check_prefreeze.json(같은 바이트 d640327a…): 바뀜 7, 더함 99, 빠짐 0, b0/code 안 __pycache__ 0. 동결 FRZ_B0 는 이 상태의 사본.
- 고침(앞 항목들): 02:49 항목의 "탐침 15번" → 16번(p00–p15). 같은 항목의 "codex 계약 10개" → 11개(덧씌움 2 + 망 핀 재핀 9). 02:57 항목의 "재생 중(02:5x)" → 02:51:08, R3 실행 중(03:01 항목에 이미 적음).
- 요약: 설정 단계는 v3c3 세 상태에서 통과, 러너 사전 점검(동결 FRZ_B0 853d1c4f, v3c3) exit 0, 우리 고침 넷 이식·시험 통과. 결정 재생 3회는 직전 명령의 SDMPC 가격 문맥(V-A 우리 제어기) 때문에 load_prices 에서 멈춰 v3c3 결정 시간은 못 잼 — 규칙대로 더 돌리지 않음. 다음 = T=900 재생(새 선언·허락 필요). 판정 낱말 없음.
- VISSIM·COM 0(내 것), B 폐루프 0, 커밋·푸시 0, kill 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·런 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0. 이 PC 의 VISSIM/cscript 는 A1 의 40024/48380 뿐 [실행 03:09]. A1 T=2100 까지(679 s). 디스크 C 30 GB, D 261 GB.

## 2026-10-26 03:58 KST — A1 진행 중
- [실행] 결정 줄 T=2700 까지 모두 exit 0(감시 도구가 읽는 runlog 줄만 봄). T=2850 진행 중. 다른 세션 VISSIM 48616 은 02:20–03:0x 무렵 돌다 끝남(감시 출력에서 사라짐). 지금 VISSIM 은 A1 의 40024 하나. 디스크 C 29.2 GB, D 260.5 GB. kill 0.

## 2026-10-26 04:18 KST — A1 T=3150 결정 실패 → 직전 명령 유지 (런은 계속)
- [실행 runlog 감시 줄만] CONTROLLER_DECISION sim_sec=3150 wall 21.49 s exit=1, DECISION_HOLD_ATTEMPT 원인 "ValueError: Queue count differs", DECISION_HELD_PREVIOUS source=action_003000.json. 러너 정책(hold_previous) 그대로 돈 것이며 우리 개입 0. codex joint 는 6900 에서만 유지(다른 원인 "Missing observed speed…")였음. 원인 분석은 고정 도구(a1_trace)로 런 뒤에.

## 2026-10-26 05:21 KST — A1 진행 중
- [실행 runlog 감시 줄] T=3300 도 exit=1(14.04 s) 로 끝나 유지된 것으로 보임(T=3450 결정이 이어 돌았음). T=3450–4050 은 exit 0. T=4200 진행 중. VISSIM 은 A1 의 40024 하나. kill 0.

## 2026-10-26 07:11 KST — A1 진행 중
- [실행 runlog 감시 줄] T=4200–5400 모두 exit 0(벽시계 504–771 s). T=5550 진행 중. VISSIM 은 A1 의 40024 하나. kill 0. 디스크 8 GB 위.

## 2026-10-26 08:06 KST — A1 진행 중
- [실행 runlog 감시 줄] T=6000(24.86 s)·6150(15.03 s) exit=1 → 유지로 이어진 것으로 보임(다음 결정이 이어 돔). T=5550·5700·5850·6300·6450 exit 0. T=6600 진행 중. VISSIM 은 40024 하나. kill 0.

## 2026-10-26 09:10 KST — A1 진행 중
- [실행 runlog 감시 줄] T=6750 exit=1(22.95 s) → 유지로 보임. T=6600·6900–7500 exit 0. T=7650 진행 중. VISSIM 40024 하나. kill 0.

## 2026-10-26 09:36 KST — A1 끝남
- [실행] runlog STAGE=SIM_DONE, SIM_SEC=8100, DECISIONS_OK=49, DECISIONS_FAILED=6, DECISIONS_HELD_PREVIOUS=6. 워치독 launch.log "10-26 09:34:22 OK sdmpc31_sdmpc8100_s29 attempt=1 elapsed=29694s". 래퍼 wrapper_run_end.json runner_exit 0, wall_sec 29,787.5(01:17:48 → 09:34:22). native_status stage requested_native_arms_complete_unanalyzed. runlog .err 0 B. VISSIM 프로세스 0(스스로 닫힘). kill 0, 재발사 0, 5분 무진행 발동 0.
- 디스크 C 30 GB, D 256 GB.
- 다음: run_a1_analysis.ps1(-Smoke 없이, 02:02 항목 sha 그대로) WMI·BELOW_NORMAL 로 발사.

## 2026-10-26 09:58 KST — A1 분석 (고정 도구) · A1_RESULT.md
- 고침: 바로 앞 "09:36 KST — A1 끝남" 머리 시각은 어림값임. 그 항목은 분석 발사(09:34:49) 전, 09:34:2x–09:34:4x 에 썼음 [실행 analysis.state.txt 첫 줄].
- [실행] 도구 sha 다시 확인(TOOLS_SHA256_A1_FULL.txt 모두 OK, a1_compose.py 5f39df13…) 뒤 run_a1_analysis.ps1(-Smoke 없이) WMI 발사, PID 30224, BELOW_NORMAL, 09:34:49–09:40:05, 8단계 모두 exit 0. 출력 sha: trace.json 69277e6c…, fzpdiff.json 058fe4c4…, a1_table.json 6c9671ef…, unins_a1.json 70142013…, metrics_out_a1.json 937c4770…, ours_a1.json 077d126c…, scan/a1.json e0d475a6…, compose_a1.md 4a1ff08f….
- [실행] 결정 추적: 처음 R1 다른 T = 1200(38행, signal 5/sg 32/meter 1, RM_C10646 720/8 대 540/6, 녹색 ≤ 0.002 s, offset ≤ 0.695 s). T=1200 입력 값 잎 차 0, A1 1200 명령 = A0b 1200 명령(바이트 같음). 상태 값 잎이 처음 다른 T = 1350. T ≥ 1500 은 signal 17/17·sg 122/122 행이 매번 다름, 미터는 T ≥ 1200 의 47결정 모두 다름, VSL 은 8결정(1800, 3450–4350)에서 A1 이 FW_E S13 4행 100 km/h(codex 110).
- [실행] 유지: A1 3150·3300(Queue count differs), 6000(Mixed ready ownership needs explicit partition), 6150·7800(Terminal queue count changed), 6750(Missing observed speed with nonempty moving source); codex 6900 하나. 시한 유지 0. 결정 벽시계 최대 771.5 s, > 1500 s 0.
- [실행] FZP: 접두 ≤ 895.1 s 같음(f1a0b040…fbcda), A1–joint 처음 다른 프레임 1240.1 s(11대, 링크 10641·126·71·10643).
- [실행] 표(codex 꼴 0–8100, 한 짝씩): A1 − LNC Ω701 −505.7 / Ω635 −411.4 / ④ −699.2 / Ω 밖 (a) −193.5·−287.8 / (b) +41.6·−52.7 / ① −251.1 / ② −181.8 / ④b(첫 관측) −235.1(1098 +94.8, 1099 −78.8, 도시 −251.1) / 도시도로 codex −312.4·우리 −338.6 / 링크 66 −50.5. joint − NC 는 RAW_CHECK·HR 값 그대로(−494.7 / −407.9 / −670.3 / −175.6·−262.4 / +45.7·−41.1 / −283.7 / −156.6 / −221.3). A1 − joint ④b 첫 관측 −13.803 대 native −13.799. 1099 도착 A1 20,163 대 joint 20,166.
- 사후 읽기(사전 고정 밖, 데이터 본 뒤라 따로 밝힘): A1 유지 6결정의 action_T.error.txt 호출 경로(grep File 줄). 6개 모두 calibrated_urban_runtime.py:160/163 initialize → sc10_north325 / sc105_initial340 candidate install 에서 시작. 표·추적 숫자에는 쓰지 않음.
- 계산(문서 안 [계산]): 둘 다 exit 0 인 42결정 벽시계 합 배수 1.78(중앙 1.86), 결정 밖 시간 7,096 s 대 3,130.4 s.
- 산출: codex_handoff/a1/A1_RESULT.md sha256 a808e9f898df74d714e905c872bf1f3bb01729f8435eaf04ed4c6b5b70d22543 (틀 work/a1/full/A1_RESULT.template.md 65964312…, 표 칸은 compose_a1.md 를 그대로 끼움). 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/a1/A1_RESULT.md (같은 sha).
- VISSIM 은 A1 하나뿐(이 단계 새로 띄움 0), kill 0, 재발사 0, B 폐루프 0, 오프라인 재생 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0. 디스크 C 30 GB, D 256 GB.

## 2026-10-26 09:55 KST — 종합: A1_B0_RESULTS.md (A0b·A1·B0·r4 모음, B 계획·비용, 사용자 결정)
- 고침: 바로 앞 "09:58 KST — A1 분석" 항목 머리 시각은 실제 쓰기 시각보다 늦게 적힘. LOG.md 파일 시각 09:46:34, 그 항목이 마지막 쓰기 [실행 ls --full-time].
- [실행] 읽음: A0B.md 7db91c0d…, a1/A1_LAUNCH.md 227ac13e…, a1/A1_RESULT.md a808e9f8…, b0/B0.md b7216dd0…, b0/PRE_B.md 3149cfe5…, k92/va/analysis/VA_REPORT_r4_CORRECTION.md 6127ce41…(.sha256 파일과 같음), r3 VA_REPORT.md b57022e6…(그대로), NOTES 67dcc32b…, PRE_A1 2d9aa15a…, HR 964a23ce…, TAKEOVER_PLAN b75ad041….
- [실행] 새로 잰 것(읽기만): RES D:/VISSIM_runs/20261025_codex_a1_s29 6.6 GB → B 런당 약 7.3 GB [계산]. V-A 세 시드 state_000900.json 있음(D:/VISSIM_runs/20261023_sdmpc31_k92/…_s{31,41,43}/decisions_…/). B 설정 config_b0_v3c3.json 729640af… 에 calibrated_aggregate 키 0개, A1 codex 설정에는 native348/calibration.json be929a1d… 핀. calibrated_urban_runtime.py:22-24·:116-117 [읽음] → A1 유지 6번의 길은 B 에서 바로 빠짐. 디스크 C 29.1 GB, D 255.8 GB, VISSIM·cscript 0 (09:48).
- [계산] A1−LNC 대 joint−NC 22줄 부호 모두 같음. |A1−joint|/|joint−NC|: Ω701 2.2 %, Ω635 0.9 %, ④ 4.3 %, Ω 밖 (a) Ω701 10.2 %, ① 11.5 %, ② 16.2 %, 진입 E(우리) 43.0 %. B 런당 어림 10.2 h(A1 속도: 55 × 520.5 + 7,096 × 9000/8100 + 91.4 = 36,603 s) – 13.6 h(HR B-9), 세 시드 차례 30.5–40.8 h + 대기.
- 결정 거리 10개(권장): 1 B 관문 1 T=900 재생 4개 (a) / 2 B 폐루프 조건부 go 3시드 차례 + s31 멈춤 조건 (a) / 3 B 설정 PRE_B §1 그대로 (a) / 4 다른 VISSIM 대기 (a) / 5 64cf 유도 계약·F3 그대로 (a) / 6 A1 반복 런 지금 안 함 (a) / 7 T=1200 수치 원인·유지 관측값 추적 안 함 (a) / 8 VSL 100 까닭은 B 뒤 (a) / 9 r4 메모로 둠 (a) / 10 J1_REPORT 에도 메모 (a).
- 산출: codex_handoff/A1_B0_RESULTS.md sha256 dc0626479dae758d94bb48090e7fcbe4882b8754c8fccd15d49b0c773e97d723 (판정 낱말 검사 0건).
- VISSIM·COM·재생·분석 도구 실행 0, B 폐루프 0, kill 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·런 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0.

## 2026-10-26 10:09 KST — VERIFY_A1_B0 대조 규칙·도구 고정 (다시 세기 전)
- 대상: A1_B0_RESULTS.md dc0626479dae758d94bb48090e7fcbe4882b8754c8fccd15d49b0c773e97d723 (LOG 09:55 기록값과 같음 [실행]), a1/A1_RESULT.md a808e9f8…, b0/B0.md b7216dd0…, b0/PRE_B.md 3149cfe5…, A0B.md 7db91c0d…, VA_REPORT_r4_CORRECTION.md 6127ce41…, r3 VA_REPORT.md b57022e6….
- 규칙 work/vfy_a1b0/VERIFY_RULE_A1B0.md d0a88dd41f84489625a9340c6c7652b4f34b400764cec5e7f6ccbb6b85e786da
- 도구(저자 도구 재사용 없음): vfy_fzp_scan.py f955fc3785cd74e8d59a2c9f72dea710642c0afda359b535cf15a818c02cf6db / vfy_a1_table.py b97b1813feb836d010a53dcbcb428bceaba6a8809d7c601951e2bca794134a99 / vfy_trace.py dbf0189cf5cd7316f99c9a6bd3482c97bc9667d5e20f9fd82544f75d0a16517b / vfy_b0.py de06161e1fea2a64cceb844791126f977529647fb33a1762755d054e47d8980b / vfy_r4.py e22e634fee773f68f7fa04d0436ae180d5a4e7b558156410e7f957049ff69b1e (목록 work/vfy_a1b0/PINS.sha256).
- 이 고정 전에 본 것: 보고 본문, 자료 꼴(FZP 머리, 결정 CSV 머리, JSON 키, runlog 줄 꼴, r3 va_metrics 키 구조), V-A s31 T=750/900/1650/3300 action JSON 의 sdmpc_state 유무, sdmpc.py:768-787. 합성 FZP 자기 시험만 함.
- 실행 계획: BELOW_NORMAL, 한 번에 하나, VISSIM·결정 재생 0. 다른 세션 python(ChatGPT/RL td3, PID 14388 등)은 건드리지 않음. 디스크 C 29 GB·D 255 GB.

## 2026-10-26 10:14 KST — VERIFY_A1_B0 추가 도구 고정 (규칙 고정 뒤, 밝힘)
- vfy_inputs_extra.py e0b0ab7bd873b7ad35f842da52847c593ee179d20ef88bf46fd50c872fbf823f : T=1,050·1,200 의 나머지 결정 입력(obs150 capture·err·mer·vsl_cohorts, lane_observations frame)과 직전 명령 metadata.sdmpc_state 를 A1 대 joint 로 대조. 까닭: A1_RESULT 의 "같은 입력" 근거가 state·derived 두 파일뿐이라 나머지 입력과 직전 가격 상태를 따로 봄. 실행은 본 드라이버(10:09:36 발사, BELOW_NORMAL) 가 끝난 뒤.
- 밝힘: 10:10 경 V-A/J1/NC3 FZP 경로 확인용 ls 의 glob 이 봉인 시드 s37(그리고 s47·s53) NC FZP 의 파일 이름·크기를 보여 줌. 내용은 열지 않았고 이후 glob 을 쓰지 않음.

## 2026-10-26 10:21 KST — VERIFY_A1_B0 본 실행 결과(1차)와 고친 도구 둘 (밝힘)
- 고침: 바로 앞 "10:14 KST" 항목은 실제로 10:12 경에 적었음(머리 시각 이름값).
- [실행] 드라이버 run_vfy.ps1(WMI PID 31332, BELOW_NORMAL) 10:09:36–10:19:59. 스캔 13개·a1_table·trace·r4 는 끝까지 돌았고(.err.txt 0 B; PS 5.1 이 exit 를 null 로 읽음), vfy_b0.py 는 A1 동결 트리의 260자 넘는 경로에서 FileNotFoundError 로 죽음.
- 고친 도구 1: vfy_b0.py r2 7651b427bd204f86cb80127ec5e19504cf7aefef1d7d11cfa9137e9bf1789bac — sha() 에 긴 경로 접두만 더함(값 판단 무관).
- 더한 진단 1(규칙 밖, 자료 본 뒤): vfy_form_diag.py d92893d6c64e32457a8361de2c9b0a950ad3e4433c599613a23b27ca4c1cf70c — 까닭: 규칙에 적은 codex 꼴(앞으로 유지)로 낸 수준값이 보고값보다 1.4–1.8 veh·h 작고 짝 차 7칸이 0.06 을 0.11 까지 넘음. codex 자체 수치(인계 derived/metrics_0_8100.json nc·joint)를 기준으로 꼴을 가려 다시 냄. 규칙(앞으로 유지) 결과도 그대로 보고함.
- 1차 결과 요지(값 판단은 VERIFY 문서에서): 결정 추적·A0b·입력 잎·벽시계는 보고와 같음. r4 는 199칸 중 193 같음, 다른 6칸은 모두 입력 1091·1092 몫의 첫 링크 근사(귀속 방법 차). 

## 2026-10-26 10:27 KST — VERIFY_A1_B0 2차 실행(b0 r2·꼴 진단) 결과와 고친 도구
- [실행] run_vfy2.ps1(WMI PID 37932, BELOW_NORMAL) 10:21:22–10:22:54: vfy_b0.py r2 exit 0, vfy_form_diag.py exit 0, vfy_inputs_extra.py exit 1(UTF-16 BOM 파일을 utf-8 로 읽다 죽음).
- 꼴 진단 결과: codex 자체 수치(nc·joint 의 Omega701·network_sampled_residence·FW_E_7·local_19)와 1e-3 안에서 맞는 꼴은 사다리꼴(TR, 0 에서 선형 시작·프레임 사이 선형·마지막 4.9 s 유지)뿐. 규칙에 적은 앞으로 유지 꼴은 내 정의 오독이었음(밝힘). TR 꼴로 A1 표 76칸 모두 보고와 0.06 안.
- 고친 도구: vfy_inputs_extra.py r2 a10bb66c624fcb22a3e4d5a71669ece0c8314d7071a224e6f55beb7ea1f5e641 — UTF-16 BOM 읽기만 더함(값 판단 무관). 다시 돌림.

## 2026-10-26 10:31 KST — VERIFY_A1_B0 추가 진단 도구 고정 (규칙 밖, 밝힘)
- vfy_entry_diag.py 1e35d634f9f476a2b0572a79766cb4f59bcee987d73f2880c3fe8faa6211bd03 : 진입 E·W 두 분할 칸(A1_B0_RESULTS §0-5 의 "진입 E(우리 분할) 43.0 %" 근거)을 A1 대조 규칙 §C 글의 정의(codex onramp_roads + 미터 상류 링크 70·68·129·31 / 124·32·121·69)와 TR 꼴로 다시 냄. 정의가 보고값을 못 내면 '다시 내지 못함' 으로 적고 정의를 바꿔 맞추지 않음.
- [실행] vfy_inputs_extra.py r2 exit 0 (T=1,050·1,200 나머지 입력: 값 잎 차는 err jsonl 의 런 고유 barrier 토큰 1잎뿐, 직전 sdmpc_state 값 차 0).
- [실행, 규칙 밖 즉석 점검] A1·joint FZP 1,240.10 프레임: 양쪽 4,227행, 한쪽만 0, 내용 다른 차 11대(링크 10641×5·126×3·71×2·10643×1).

## 2026-10-26 10:34 KST — VERIFY_A1_B0.md 작성 (A1·B0·r4 종합 보고 다시 검증)
- 산출: codex_handoff/VERIFY_A1_B0.md sha256 6075c1df184a6177d40228651037d794805c53cbd407782eee7c474e6898264d.
- [실행] 요지: 반박된 무게 있는 주장 0. 결정 추적(T=1,200 첫 갈림, 38행, 녹색 0.002, RM_C10646 720/8 대 540/6, 입력 값 차 0, A1=A0b), A1 결과 표 76칸(codex 자체 꼴 = 시각축 사다리꼴로), B0 재핀 30경로·코드 7파일·FREEZE·사전 점검, r4 193/199칸 같음(다른 6칸은 입력 1091·1092 몫, 제 근사 귀속의 한계 → 근거 부족, 무게 없음).
- 고칠 것 6개(정의 문구·22줄 범위·램프 예측 소비 보충·비 반올림·/name·SC 9103), 수치 결론 바뀜 없음.
- 밝힘: 규칙의 codex 꼴(앞으로 유지)은 제 오독 — codex 자체 수치로 꼴을 가려 다시 냄(자료 뒤 진단). 꼴만 고친 도구 2, 규칙 뒤 더한 점검 여럿(문서 §8).
- VISSIM·결정 재생 0, kill 0, 커밋·푸시 0, GWT8·frozen·인계 사본·런 폴더·Y: 쓰기 0, sealed/·봉인 시드 내용 0, 금지 시험 0. 디스크 C 30 GB·D 256 GB.

## 2026-10-26 10:36 KST — 마무리(A1_B0_RESULTS r2) 산술 도구 고정 (실행 전)
- 근거: VERIFY_A1_B0.md 6075c1df184a6177d40228651037d794805c53cbd407782eee7c474e6898264d §7 고칠 것 6개 + 근거 부족 3건.
- 도구 work/fin_a1b0/fin_calc.py e68492abb7089fd46c0b70523413ec1fef45b13a609d275276004202a99c911b. 규칙(파일 머리 글): (1) 비 % = 100·|a1-joint|/|joint-nc| 를 a1_table.json(6c9671ef…) 반올림 전 값으로, 22줄. (2) 22줄 부호 같음 다시 셈. (3) trace.json(69277e6c…) sc_with_diff 를 sc_no '91…'(미터 행) / 그 밖(신호 SC)으로 나눔. 읽기만, 새 측정 없음.
- 밝힘: 비 열은 r1 에서 반올림 표 값으로 냈음(VERIFY §7-4). 식은 그대로 두고 입력 정밀도만 바꿈. SC 수 열 분해는 VERIFY §7-6 의 9103 지적을 같은 표의 다른 T 에도 적용하려는 것.
- 실행: python -B, PYTHONHASHSEED=0, 가벼운 산술(수 초)이라 직접 실행.

## 2026-10-26 10:45 KST — 마무리: A1_B0_RESULTS r2 (VERIFY_A1_B0 고침 반영) · 하위 보고 r2 · 보고 폴더 사본
- [실행] fin_calc.py(e68492ab…, 10:36 고정) 실행 → work/fin_a1b0/fin_calc.json 3aabadd61a3dd7025b2ac953f25c055f2f211dcd2c0de4cdbf5331c9672cf4df. 비(반올림 전): ② 16.14 %, 링크 66 0.90 %, 1099 13.84 % (r1 16.2/1.0/13.9), 다른 16줄은 0.1 자리에서 같음; 22줄 부호 같음 true; SC 수 열 = 다른 신호 SC + 다른 미터 행(49결정 모두, 1200 은 5+1(9103), 1350 은 10+1, ≥1500 은 17+1–8).
- [읽음] ADP:2984-2985 주석("리더의 N_UF 도착 목표는 원래 demand 를 보므로 건드리지 않는다") 직접 확인(B0T 읽기만).
- r1 보존: A1_B0_RESULTS_r1.md dc0626479dae758d94bb48090e7fcbe4882b8754c8fccd15d49b0c773e97d723, a1/A1_RESULT_r1.md a808e9f898df74d714e905c872bf1f3bb01729f8435eaf04ed4c6b5b70d22543, b0/B0_r1.md b7216dd06b3e11986739e6a36f1407e001a325682e23715a46e504dbc95f8df7 (r1 원본과 같은 sha).
- r2 산출: A1_B0_RESULTS.md a9f491ee1cad3d704f79ea606fe83bbd99667d928365a6c5b6940ec04198f1b0; a1/A1_RESULT.md 0ef733fb2450c71925d6b2723c7446a7441d6bf5581a23d105d2523e095cc714; b0/B0.md 11fa75788e5457f95ab20a43ca2287e663f0390bef67940bcfb66dd8368c86bc. VF §7 고침 6개 모두 반영(codex 꼴 = 시각축 사다리꼴 정의, 22줄 범위 '독립 20줄 + 표 도구 2줄', 램프 예측 → 리더 N_UF 목표 길 보충, 비 반올림 전 값, /name, 신호 SC 5 + 미터 9103), 근거 부족 3건 표시(우리 꼴 ≤ 0.15, r4 칸 수 셈, 1091·1092 몫 6칸). 하위 보고 둘은 줄 번호를 r1 과 같게 두고 끝에 변경 기록. 반박된 글은 변경 기록 표의 'r1 글' 칸에만 남김. 숫자 결론 바뀜 0. r4 메모·r3·A0B·A1_LAUNCH·PRE_B 는 바꾸지 않음(VF 반박 0).
- [실행] 보고 폴더 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/ 에 사본 90개(위 보고 9개 + work/vfy_a1b0 + work/fin_a1b0), 원본과 sha 불일치 0. 그 뒤 이 LOG 사본과 SHA256SUMS.txt(폴더 전체 다시 셈)를 씀. r4 메모 사본(reports/k8/k92_va/ 두 곳)은 6127ce41… 그대로.
- [실행 10:40] 다른 세션 VISSIM 1개(PID 29264, cscript 32716, D:/VISSIM_runtime/20261023_rolling_cea/… ttt_lambda001_s29_8100_v4) 돌고 있음 — 건드리지 않음. 디스크 C 29.1 GB, D 255.5 GB.
- VISSIM 띄움 0, 결정 재생 0, 분석 도구 재실행 0, B 폐루프 0, kill 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·런 결과 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0.

## 2026-10-26 11:11 KST — B 관문 1 선언·도구 고정 (재생·사전 점검 전)
- 근거: 사용자 결정 D-K9-88·89(NOTES `K9_1_J1_NOTES_20261013.md` sha256 d248605e725532c5b65a63eeb9fb4ba2d8d47552d4169d25a372cdf55afbbee1 [실행]). PRE_B §2-1·§2-3, B0.md r2 §7-1, A1_B0_RESULTS r2 §3 결정 거리 1 (a).
- 선언 `codex_handoff/b/GATE1_RULE.md` sha256 766c57376c9a78e154fca93c8bbaafe6887575b6ad38d747c43198de267fc5e0.
- 재생 넷(T=900 첫 제어 결정, 직전 action_000750 = NoControl·sdmpc_state 없음·.applied 없음 [실행]): R1 V-A v3c3-s31 B 설정 / R2 V-A v3c3-s41 B 설정 / R3 V-A v3c3-s43 B 설정 / R4 V-A v3c3-s31 그룹키 설정(e8a5730a…, H8 대조). 상태 sha: s31 d005d68a…, s41 22b521a6…, s43 1d3a40bd….
- 통과 조건(재생마다): 종료 0, 예외 0(Traceback·DECISION_FAILED·.error 파일 없음), 결정 끝남(action JSON·CSV, budget output_completed true), 벽시계(래퍼·budget 중 큰 값) ≤ 1,500 s. 관문 1 = 넷 모두 + 러너 사전 점검 s31·s41·s43 모두 + 재생 뒤 FRZ_B0 FREEZE_VERIFIED.
- 도구(work/gate1/): g1_preflight_wrapper.ps1 17549a56d04dfc5989045b60352745cc5d504d9b3451c8105f759fa0b404f56e / g1_build_inputs.py 51aa645e7be64ca7c0f1092776dfe58a4b1ee04a467738e6093275d742363db3 (← b0_build_inputs.py 62dabb59…, 경로 상수만: V-A s41·s43 원천, gate1 뿌리, code root = FRZ_B0, freeze 핀 = FRZ_B0 FREEZE.json; 바뀐 줄 copies_gate1_record.json 3330c867…) / g1_replay.ps1 4fa4167826dc6d80abf8c2dad10789c77d07ca6e7a9ac6d373f74ea2e68bfa29 / g1_queue.ps1 7b41d3d859c68b08a0373bdcde644eca7a35008da4809311a325eec2086f6ede / g1_launch_wmi.ps1 bcd208f905ecaa38e58b81290d391c11c6ce591405f469b2744d5747659da045 / g1_summary.py cf1786c878bfecfe4bb896fa8886ab6fc0125025557ba43cfbff89e3a0f33370 / mkcopy.py 8ec4f60c4662d2c53fbce282390a6bbe37928d94eb91ea4bdf9f256d71f1a90b / spec_gate1_copies.json 83b297e88c90c700f7569fd3f69e97c7e9318f2ae7024b06acbea068e77ecacc. 바꾸지 않고 씀: work/a0/s5_collect.py 90b1a350….
- 실행 계획: WMI(Normal) → g1_queue.ps1: 러너 -PreflightOnly s31·s41·s43(B)·s31gk(그룹키, R4 입력용) → 입력 4 → 재생 R1–R4 한 번에 하나(Normal, env_hsw, PYTHONHASHSEED=0, python -B) → FRZ_B0 freeze verify → 요약. 결과 뿌리 D:/VISSIM-merge/k8_gate_trees/codexhandoff/gate1(B 결과 뿌리 아님). 재생 상한 7,200 s(내 프로세스 나무만 멈춤). VISSIM 띄움 0.
- [실행 10:51] 이 PC 의 다른 세션: VISSIM PID 29264(rolling_cea, cscript 32716)와 그 어댑터·탄젠트 워커 8개, TD3 학습 python 14388 과 탄젠트 워커 8개. 건드리지 않음. 부하는 재생마다 typeperf 로 기록. 디스크 C 29 GB, D 255 GB.

## 2026-10-26 11:20 KST — COMPARE_RULE_B·B 분석 도구 사본 고정 (첫 B 발사 전, B 데이터 0)
- 규칙 `codex_handoff/b/COMPARE_RULE_B.md` sha256 f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c. PRE_B §3·§4 를 옮기고 표 칸·반올림·결측·점검(X1–X6)을 적음. ④ 적분 꼴 두 가지를 글로 적음: 우리 꼴 [0, 9000] s(5.1 s 첫 프레임–8,995.1 s, 0.10 s 프레임 건너뜀, 양끝 늘림 없음), codex 꼴 [0, 8100] s = 시각축 사다리꼴(0 s 빈 망에서 선형, 모든 프레임 실제 시각, 8,095.1 s 재고를 8,100 s 까지 4.9 s 유지; VERIFY_A1_B0 §0-4 로 codex 자체 수치와 1e-3 안 확인된 꼴).
- [실행 11:18] PRE_B §4 14개 sha 그대로, 목록 셋(SHA256SUMS_RAWCHECK·va_analysis_pins·R4_PINS) sha256sum -c 에서 OK 아닌 줄 0.
- 사본(경로 상수만; 생성기 work/gate1/mkcopy.py 8ec4f60c4662d2c53fbce282390a6bbe37928d94eb91ea4bdf9f256d71f1a90b, 명세 work/gate1/spec_b_copies.json f857d830ec17c2eccea9f50e66b4a3a1848a625faf5da250cd3900679ecb2186 ← make_spec_b.py c867432221dbebb941e234f9f43c05219f9e72055357f5e9279c9d8845515ed9, 바뀐 줄 원문 work/gate1/copies_b_record.json 51936d431dd05f3bad3983dfb1504567886707b37d8f8590a5c46fbc800ea52a). 원래 런 칸 이름은 두고 경로만 B 로(칸 j1 / joint / a1 = B, nc = NC3, lnc = V-A):
  - omega_b/omega701_recount_b.py 3d5160da36f984b554444c06e513500590551682b706a234cc67f9fc0221f150 (← omega/omega701_recount.py 5b7826f6…): replace 원본 1-1줄 -> 사본 1-1줄; insert 원본 69-68줄 -> 사본 69-72줄; replace 원본 72-72줄 -> 사본 76-76줄; replace 원본 78-78줄 -> 사본 82-82줄
  - vhr_b/vhr_scan_b.py 0c445bc4bf05f45f7638be8227f0f29c2b036c0f276083958ff6bac87a85466e (← vhr/vhr_scan.py a19942b8…): replace 원본 8-8줄 -> 사본 8-8줄; replace 원본 16-16줄 -> 사본 16-16줄; replace 원본 22-22줄 -> 사본 22-22줄; replace 원본 25-25줄 -> 사본 25-25줄
  - vhr_b/vhr_firstseen_b.py d5c3c126490e4d1260063b51a9b97b4948b7c1ac35846c32761423c90088471b (← vhr/vhr_firstseen.py 42e17585…): replace 원본 7-7줄 -> 사본 7-7줄; replace 원본 13-13줄 -> 사본 13-13줄; replace 원본 17-17줄 -> 사본 17-17줄; replace 원본 20-20줄 -> 사본 20-20줄
  - vhr_b/vhr_v3c3_all_b.py d91ded54904eb43a78a49f0d2a1382396258a0cf0621fbf6e7ba2410fb7283ed (← vhr/vhr_v3c3_all.py b4237251…): replace 원본 4-4줄 -> 사본 4-4줄
  - rawcheck_b/s31/scan_fzp_b_s31.py 943e06db1151ec73e652e8dbd61d980e6ebfb11025f2ddc9fd7a95ffa353311a (← rawcheck/scan_fzp.py c8a6e5c4…): replace 원본 10-10줄 -> 사본 10-10줄; replace 원본 14-15줄 -> 사본 14-15줄
  - rawcheck_b/s31/metrics_b_s31.py 84d15045efcb9756e675b534df60f6a6a8ce5e5b873a1c3a33a7ed8675e42235 (← rawcheck/metrics.py b524b51b…): replace 원본 4-4줄 -> 사본 4-4줄
  - rawcheck_b/s31/rm_exec_b_s31.py 0c26104b46e79733d7dc5a4bd10a27a02dc30011518a02282d98a6c6e3e7d39a (← rawcheck/rm_exec.py 27f64022…): replace 원본 3-3줄 -> 사본 3-3줄; replace 원본 6-7줄 -> 사본 6-7줄; replace 원본 14-14줄 -> 사본 14-14줄
  - rawcheck_b/s31/walltimes_b_s31.py 6974d2b43c54eed4c34e9a3963a0a69e2243c35d95ab70292848df6e3c537aa6 (← rawcheck/walltimes.py 13734307…): replace 원본 4-5줄 -> 사본 4-4줄
  - rawcheck_b/s31/ramp_fc_b_s31.py 22275050c962defaedc137576a8994a7d6671bcce385b76d1d01f4c2872b49a4 (← rawcheck/ramp_fc.py cee99f5b…): replace 원본 5-5줄 -> 사본 5-5줄
  - rawcheck_b/s31/a1_fzp_firstdiff_b_s31.py 8e476eba81c6d37d60e9b79da5c545207f35486648419dc2b5a2b730fe4bcb15 (← a1/full/a1_fzp_firstdiff.py 00924703…): replace 원본 14-16줄 -> 사본 14-16줄
  - rawcheck_b/s41/scan_fzp_b_s41.py 19e33689806e399000ee6d706539adaaec60d266f023c700e2a5c95ca456f3c1 (← rawcheck/scan_fzp.py c8a6e5c4…): replace 원본 10-10줄 -> 사본 10-10줄; replace 원본 14-15줄 -> 사본 14-15줄
  - rawcheck_b/s41/metrics_b_s41.py f93e653783df2a26f3bb1f510b7614c661eb95010fc5ea31f72b5c232a8262fd (← rawcheck/metrics.py b524b51b…): replace 원본 4-4줄 -> 사본 4-4줄
  - rawcheck_b/s41/rm_exec_b_s41.py 1fbac884ac25c4a5619907bbee58daf6935eb32f531011af05c383d7764faa96 (← rawcheck/rm_exec.py 27f64022…): replace 원본 3-3줄 -> 사본 3-3줄; replace 원본 6-7줄 -> 사본 6-7줄; replace 원본 14-14줄 -> 사본 14-14줄
  - rawcheck_b/s41/walltimes_b_s41.py a16776b514c6d82c76c4b9343a93dcc8690eab360b36d9b9a0bc426f171ccbdf (← rawcheck/walltimes.py 13734307…): replace 원본 4-5줄 -> 사본 4-4줄
  - rawcheck_b/s41/ramp_fc_b_s41.py 9732ffc9ec4e7d08f83cd65e7c6c5d944d7eaa502de1ba268ac3851491fdb745 (← rawcheck/ramp_fc.py cee99f5b…): replace 원본 5-5줄 -> 사본 5-5줄
  - rawcheck_b/s41/a1_fzp_firstdiff_b_s41.py e4df20affd6630e76229d35051dc70af304090a08d8b802d9e64b710fbb56411 (← a1/full/a1_fzp_firstdiff.py 00924703…): replace 원본 14-16줄 -> 사본 14-16줄
  - rawcheck_b/s43/scan_fzp_b_s43.py 906b8ae30d79daa7c378bd59f05cfa5339bdd290cf6771ec9aa0c814b16a43b3 (← rawcheck/scan_fzp.py c8a6e5c4…): replace 원본 10-10줄 -> 사본 10-10줄; replace 원본 14-15줄 -> 사본 14-15줄
  - rawcheck_b/s43/metrics_b_s43.py b27ab3b36bbe5de283c55cacc98044d051db8aa96d1db27e50940f4661dbd034 (← rawcheck/metrics.py b524b51b…): replace 원본 4-4줄 -> 사본 4-4줄
  - rawcheck_b/s43/rm_exec_b_s43.py af2c9eb81ae53470f3823b3f31972aa4cb521cadb049ad2486b8e0348d024b9a (← rawcheck/rm_exec.py 27f64022…): replace 원본 3-3줄 -> 사본 3-3줄; replace 원본 6-7줄 -> 사본 6-7줄; replace 원본 14-14줄 -> 사본 14-14줄
  - rawcheck_b/s43/walltimes_b_s43.py c5916bd7cbaaabfe654845b802533d47a427495b0314a47042353d7a95d40d7f (← rawcheck/walltimes.py 13734307…): replace 원본 4-5줄 -> 사본 4-4줄
  - rawcheck_b/s43/ramp_fc_b_s43.py 9134790c328ea9f3eb26124a618f9f6d19a1915ea1b144d4dd2718c669c99b80 (← rawcheck/ramp_fc.py cee99f5b…): replace 원본 5-5줄 -> 사본 5-5줄
  - rawcheck_b/s43/a1_fzp_firstdiff_b_s43.py c20db189073290a144915bd7c3bfc1a264198e9f4164be927c3966d9e4a9502c (← a1/full/a1_fzp_firstdiff.py 00924703…): replace 원본 14-16줄 -> 사본 14-16줄
  - rawcheck_b/dec_extract_b.py 2d128f759685f1ff7151aeb09659ca1fcfe847abd6aebf220a1e2a5a8b3a9e97 (← rawcheck/dec_extract.py 672c7bed…): replace 원본 8-8줄 -> 사본 8-8줄
- 원본 밖에서 더한 도구 둘(목록 밖이라 밝힘): vhr/vhr_scan.py a19942b8…(PRE_B §4 의 vhr_v3c3_all.py 입력을 만드는 도구, VERIFY_HANDOFF_RESULTS 에서 고정), a1/full/a1_fzp_firstdiff.py 00924703…(PRE_B §2-5 접두 점검에 도구 이름이 없어 A1 고정 도구를 씀). walltimes·ramp_fc·dec_extract 는 SHA256SUMS_RAWCHECK 목록 안.
- 고치지 않고 씀: omega/top66.py 1424b5ad…(작업 폴더 omega_b). 쓰지 않음(까닭은 규칙 §7.4): vhr_unins.py, build_tables.py, ldp_cmp.py, r4 도구, dec_summary.py.
- 데이터 전 준비: work/rawcheck_b/s{31,41,43}/scan/ 에 codex 스캔 다섯(window·off·freeway_only·urban_only·lnc)을 rawcheck/scan/ 에서 바이트 그대로 복사, sha 가 SHA256SUMS_RAWCHECK 와 같음 [실행].
- 못 내는 줄 하나(데이터 전 선언): LDP 신호 실행 대조(ldp_cmp 꼴) — NC3 s31·s41·s43 vissim_eval 에 FZP 뿐, V-A 는 fzp·lsa·mer [실행 ls] → '못 냄', 대체 계산 없음.
- 이 항목 뒤로 규칙·사본은 바꾸지 않음.
- 묶음 고정 목록 `codex_handoff/b/PINS_B.sha256` sha256 5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804 (54줄: 두 규칙, 사본 23, codex 스캔 사본 15, top66, 관문 1 도구, 생성기·명세·기록, s5_collect; 작업 폴더 codex_handoff 에서 sha256sum -c 로 확인, 지금 OK 아닌 줄 0).

## 2026-10-26 11:45 KST — B 관문 1 결과 (재생 4·사전 점검 4·재생 뒤 freeze 검사) · GATE1.md
- 고침: 앞 "11:20 KST — COMPARE_RULE_B" 항목 머리 시각은 어림값, 실제로는 11:19 무렵에 씀(재생 R1 진행 중, 가벼운 일).
- [실행] 큐 g1_queue.ps1(WMI PID 33528, Normal) 11:11:09–11:39:42. 사전 점검 s31 89.8 s·s41 15.0 s·s43 16.8 s·s31gk 16.4 s 모두 exit 0·FREEZE_VERIFIED. provenance sha256: s31 f734ebcbbf8f79b5ab0297e15430f60d4a6c81a47c8af36033e6d80711f3deac, s41 9b10552766ef5df5f7fec3b19c14dd3456c835c0dff613769bb33d5414f61905, s43 19aa70671cf7ab0be27706245aadee51ee28e5c9d7ffac5a127d4f8760e1242a, s31gk e622be686497b56b1dcbc4d6174eb880f90e66dd8f67ee95715fc6edeea9dd6f. 망 3de889f0, 유지 env 3칸, 튜닝·freeze 853d1c4f·plant 11842498·검지표 108debbb/294 핀 모두 맞음, env 키 21(빈 값 RW_OBS150_GT 하나, RW_PYTHON_EXE 없음).
- [실행] 재생(T=900, 직전 NoControl): R1 s31 B 381.5 s / R2 s41 B 403.1 s / R3 s43 B 296.4 s / R4 s31 그룹키 401.3 s(래퍼 벽시계; budget wall 1 s 쯤 짧음). 넷 모두 exit 0, Traceback·DECISION_FAILED·오류 파일 0, action JSON·CSV(213행: vsl 66·signal 17·signal_sg 122·ramp_meter 8), output_completed true, VSL 110 만. stderr 는 A1 과 같은 [경고] 세 줄. 최대 403.1 s ≤ 1,500 s.
- [실행] R1 대 R4: 명령 CSV 바이트 같음(c130fde6…), 다른 행 0, selection 스칼라 같음. 램프 도착 예측 합 4,067.4 대 2,040.0 veh/h(RM_C 칸은 메타데이터에 없음, 옛 그룹키 4칸 0).
- [실행] 재생 뒤 freeze_manifest verify FRZ_B0 exit 0: FREEZE_VERIFIED sha256=853d1c4f… files=7989. FRZ_B0 에 새로 생긴 파일 = __tangentcache__ 100 + numba __pycache__ .nbi/.nbc 6 (둘 다 FREEZE 제외 폴더), 그 밖 0.
- 밝힘(데이터 뒤, 값 판단 무관): 요약 r1(g1_summary.py) 이 freeze 검사 출력(PS 5.1 '>' 의 UTF-16LE)을 UTF-8 로 읽어 verified false·관문 칸 false 를 냄 → 읽기 두 줄만 고친 g1_summary_r2.py 520bb2b99a3cda8fc637572cbcbf80e735302ab3eb338ee0d3fd2014b054b5f5(mkcopy, 명세 spec_g1_summary_r2.json 58c0b45e…, 기록 copies_g1_summary_r2_record.json 803a415b…) → gate1_summary_r2.json ea27c492e54cc2547433e507abdf4517cc0f79593c6c1b875943f5672241ac6b(r1 gate1_summary.json 2f8742db… 보존; 재생·사전 점검 칸 같음). 표 서식 도구 g1_tables.py 7b91496aea61568e1c8e217a8e5b65058b6ed39430c7aeb9d7bce5ee1cb16007(새 숫자 없음) → gate1_tables_r2.md 398b2049….
- [실행] 사본 연기 시험(규칙 고정 뒤, B 데이터 아님): vhr_b/vhr_firstseen_b.py nc3_s31 → 원본 first_nc3_s31.json 과 같음(초 칸만 다름). 이 사본이 출력 폴더를 만들지 않아 work/vhr_b/scan_out 를 먼저 만듦(원본 도구도 같은 성질, 규칙 §7.5 차례면 vhr_scan_b 가 만듦).
- 산출: codex_handoff/b/GATE1.md sha256 aae6b0ca537e4b24edcc0823b1dab46a71476f72300659dc23b919dd2d6e8026 (판정 낱말 점검 0건).
- 관문 1 조건(GATE1_RULE §3: 재생 넷 모두 네 조건 + 사전 점검 s31·s41·s43 모두 + 재생 뒤 FREEZE_VERIFIED): 모두 맞음. B 런은 이 단계에서 띄우지 않음.
- [실행 11:42] 다른 세션 VISSIM PID 29264(rolling_cea)·cscript 32716 아직 돎 → 인계 러너는 발사 거부, BRuns 단계는 끄지 않고 기다려야 함. 디스크 C 29.1 GB, D 253.9 GB. D:/VISSIM_runs/20261026_codex_b_v3c3 는 없음(만들지 않음).
- VISSIM·cscript 띄움 0, B 폐루프 0, kill 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·런 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0.

## 2026-10-26 11:58 KST — B 런 v3c3-s31 단계 시작: 발사 전 확인·감시 기준 고정 (발사 전, B 데이터 0)
- 근거: NOTES d248605e…(D-K9-88·89) [실행 sha], PRE_B 3149cfe5… §1·§5, GATE1.md(관문 1 조건 모두 맞음, LOG 11:45).
- [실행 11:46] 고정 확인: COMPARE_RULE_B.md f902f7f0013bed0a0eb5dec27818e2bda4851995eae235130b7cb241e8b28f0c, PINS_B.sha256 5e8ffbc5cc192c25a15a07c11dda5036c7005b73c342aa16d1f7d6ed5e67d804 — 둘 다 11:20 고정값 그대로. `sha256sum -c b/PINS_B.sha256` 54줄 모두 OK. PRE_B §4 14개 sha 모두 그대로. FRZ_B0 FREEZE.json 853d1c4f…, config_b0_v3c3.json 729640af…, 망 3de889f0… [실행].
- 앞 B 런: 없음(첫 런). D:/VISSIM_runs/20261026_codex_b_v3c3 없음 [실행].
- [실행 11:46] 디스크 C 29.1 GB, D 253.8 GB. 다른 세션 VISSIM PID 29264(10:14 시작, rolling_cea ttt_lambda001_s29_8100_v4, cscript 32716, 러너 pwsh 41200/25344, 마지막 결정 T=1800 11:45)·TD3 학습 python 14388 이 돎 → 건드리지 않고 기다림. 기다림 상한 12 h = 2026-10-26 23:46 KST. 넘으면 STOP·보고.
- 발사 도구(work/b/, 새로 씀): b_wrapper.ps1 433482948475a72473421bb9d509f473d31419d79ea6bc332032314fe8696b1b (A1 래퍼 v2 7a913760… 꼴: env 지우기·env_hsw·PYTHONHASHSEED=0·env/파이썬 기록 → 동결 러너 그대로, 인자 = PRE_B §1; RW_* 를 Remove-Item 으로 지운 뒤 남은 RW_* 가 있으면 멈추는 검사 한 줄 더함) / b_launch_wmi.ps1 b88a51dbb62b0e6835ae37e5c7d2a1643631e6c59e2137d1d6aead94f028d4ec (A1 꼴 WMI Create, Normal 32, 숨김; 규칙·핀·FREEZE·설정 sha, STOP, 디스크 C≥8·D≥8+8×남은 런, VISSIM 0, 영수증·runlog 없음, s41/s43 은 앞 시드 SIM_DONE·SIM_SEC=9000·runner_exit 0 확인) / b_wait_vissim.ps1 ea243ad2198999f8876011adf6a5c7cb1e97459c7b950dfd39c34d07e8c4c10d (A1 대기 도구 꼴, 읽기만, 30 s 간격, 한 번 ≤ 540 s) / b_watch.ps1 9c2a71cade17454ef5b2f75a0720bebaceebb5b36f0e8f5b4d008b5e3465c6d0 (A1 감시 꼴, 읽기만).
- 러너 인자(PRE_B §1 그대로): -FrozenTree FRZ_B0 -ResultsRoot D:/VISSIM_runs/20261026_codex_b_v3c3/s31 -StatusPath <RES>/native_status.json -SimPeriod 9000 -Seed 31 -Arms sdmpc -TuningRelativePath diagnostics/b0_v3c3/config_b0_v3c3.json -NetworkRelativePath diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx -NetworkSha256 3de889f0… -PythonExe Python312 -PowerShellExe codex 런타임 pwsh 7.6.5 -DependenciesPath D:/VISSIM-window264-deps.
- 감시 "정상" (발사 전 고정) [실행 work/b/b_normal_gaps.py fd605b17… → b_normal_gaps.json 0dd2b38c…]: 같은 codex 코드의 끝난 기록에서 진행 신호 간격 — A1 결정 안 진행 줄 간격 최대 146.3 s(43결정), 관문 1 재생 넷 최대 144.2 s, A1 결정 사이(action_(T−150).csv → state_T.json) 최대 178.7 s(54구간, 중앙 135.1 s), A1 발사 → state_000001 162 s. 정상 최대 간격 = 199 s(A1 과 같은 값, 위 관측 최대 이상) → "정상 + 5분" = 무진행 499 s 초과. 진행 신호 = A1 목록(runlog·state CSV·action CSV·최신 action_*.json·최신 progress.jsonl·WATCHDOG_PROGRESS) + 기동 중에만 b_launch 기록·launch.log.
- s31 멈춤 규칙(D-K9-88 "s31 이 이상하면 멈추고 물음", 발사 전 고정): (가) 유지되지 않은 결정 실패·T=900 예외·제외 예외로 런이 멈춤, (나) 러너/래퍼 종료 ≠ 0·native_status failed·STAGE=SIM_DONE 없음·SIM_SEC ≠ 9000, (다) 무진행 499 s 초과 → 확인(이 런 python·VISSIM CPU) → 멈춘 것이 맞으면 이 런 PID 만 kill, **s31 은 다시 띄우지 않고** STOP·보고(사용자 정책의 "한 번 재발사" 는 선택이며 D-K9-88 이 s31 에서 앞섬), (라) 결정 하나 > StallSec 2,400 s, (마) 디스크 < 8 GB. 이 가운데 하나면 STOP. 예외 유지(DECISION_HELD_PREVIOUS)는 설계된 동작이라 멈춤이 아니며 T·예외 종류를 적음.
- 발사 경합: 내 VISSIM 0 확인과 러너의 발사 전 검사 사이에 다른 세션 VISSIM 이 뜨면 러너가 30 s 기다린 뒤 거부함(FRZ_B0 run_closedloop3000.ps1:170-178, 우리 VISSIM 기동 전). 이것은 런 이상이 아니라 발사 실패로 보고, 다시 기다린 뒤 -Attempt 2 로 한 번만 띄움(기록함).

## 2026-10-26 12:00 KST — J1 보고 고침 메모(D-K9-89 ⑦) 규칙·도구 고정 (재셈 실행 전)
- 근거: 사용자 결정 D-K9-89 ⑦(J1_REPORT 에도 같은 고침 메모), 방법 D-K9-87(미삽입 ④b 주 값 = 첫 관측 차분). NOTES d248605e725532c5b65a63eeb9fb4ba2d8d47552d4169d25a372cdf55afbbee1 :286·:294. J1_REPORT 4bf31b134845401524c2a04032e79b41772cb0f6a8f7aef7b2d9e94d41f0bc52 은 바꾸지 않음(D-K9-29 유지).
- 규칙 SP/j1/analysis/corr/COMPARE_RULE_J1C.md 506f342b898d1267683e99a30d45db96a2ff42c08c95697c00ae95cfcac4d350. 고정 목록 corr/J1C_PINS.sha256 5fa9b8988e96b61cc15b9dfbbdc1f77316b4a91757044c1e8e21d6ed5fb15b2f (13줄, sha256sum -c OK 아닌 줄 0).
- 도구(corr/tools): r4_common.py 28c67a6a78da4dddf88940b73b7eae2618001bb4025e87d9f9162c18dbf56e4f (← r4 고정 cd8b777e…, 경로 상수 한 줄: 원본 18줄 'AV = os.path.dirname(R4)' → 사본 18줄 절대 경로) / r4_fzp_first.py 6548de5e…0161, r4_firstobs.py 49b0d3e7…ad0c (r4 고정과 바이트 같음) / j1c_compare.py 1996367fb851268a9f75079cd59fea867e589ddfe19db46ec263d6a4c80c73c8 (새로 씀) / j1c_selftest.py 084c8d7c41bfd87f25df0c110536c40a6cfa5de9f765d27f2511bdfb9472ebf9 / j1c_memo_build.py 3d688118e2a9f138bde258b37109b26f2e4df56a66e36b1c434c938aa8dca6da / j1c_driver.ps1 0dcc6ae9d735d2580063a8871a5e4f18e4f7db55489f9df530e39e867c559e80 (← r4_driver_v2 732ab60f…: 머리 글·로그 이름·가드·단계 목록; 경로 상수만은 아님, 실행 감싸개) / j1c_launch.ps1 9d0cfe32945a5e271781a29352baccef016f97445ccecc37d45a5828749c75d6 (← r4_launch_v2 0ff6007a…: 드라이버 이름). 사본 생성 mkcopy.py 8ec4f60c…(고정본) + 명세 spec_j1c_copies.json abe61a70… (생성기 make_spec_j1c.py b4a1a396…) + 바뀐 줄 기록 copies_j1c_record.json 51e2deb0dc0271f9f624196ab80360e79bf76414ffaa27cf33bbb239a216a621.
- 자기 시험(고정 전, J1_REPORT 값만): selftest/selftest.json a907c2a9… ALL_OK — 같음 시험 245칸 바뀜 0·보고 글 대조 242칸, 흔든 시험(합성 차) 부호·N 표시 바뀜 잡음.
- 밝힘: 이 J1 짝의 첫 관측 차분 값은 V-A r4 메모(6127ce41…) 'J1R' 칸으로 이미 공개됨. 아직 안 낸 것 = J1_REPORT 칸 대조·§6 누적·14행 CI 수·글 속 숫자.
- 실행 계획: j1c_launch.ps1(WMI, BELOW_NORMAL) → j1c_driver.ps1: FZP 첫 관측 스캔 9개 하나씩 → r4_firstobs.py(사본) → j1c_compare.py. 가드 = 이 작업 흐름의 무거운 python(관문 1 재생·codex_handoff\work 도구·r4 도구)만 기다림, B 런·다른 세션은 기다리지 않음, kill 0, VISSIM 띄움 0. 출력 corr/out·corr/logs.
- [실행 11:59] VISSIM.exe: ;VISSIM200.exe 29264; (다른 세션 rolling_cea PID 29264 만, B 런 아직 없음). 디스크 C 30 GB, D 254 GB.

## 2026-10-26 12:12 KST — B s31 대기 중 · 분석 실행기 고정 · NC3/V-A s31 미리 스캔 (B 데이터 0)
- [실행 12:08] 다른 세션 VISSIM 29264 계속 돎(rolling_cea 결정 T=1950). 기록 work/b/vissim_wait.log. 건드리지 않음.
- 분석 실행기(새로 씀, 고정 도구를 바꾸지 않고 차례로 부름, 부르기 전 PINS_B sha 대조): work/b/b_ana.ps1 11a7deef4e3651a85ee23d89fc595a487ef4d887ca349a552263409893359da5, WMI 발사기 work/b/b_ana_launch_wmi.ps1 7544873b98dde5878e70a6f4171ff4e8255321f55fa38ebea3d7f3407eb7839c (BELOW_NORMAL 16384, 한 번에 하나). 계획 prescan = vhr_scan_b.py va_s31 nc3_s31(COMPARE_RULE_B §7.5 끝: B 전 NC3·V-A 칸 미리 스캔 허용). 계획 s31stage(런 끝난 뒤) = walltimes_b_s31 → ramp_fc_b_s31 → rm_exec_b_s31 → dec_extract_b s31 → vhr_scan_b j1_s31 → a1_fzp_firstdiff_b_s31. env: python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1, 스레드 1.

## 2026-10-26 12:05 KST — 미리 스캔 발사 · 앞 두 항목 고침
- 고침(앞 두 항목, 값 무관): "11:58 KST — B 런 v3c3-s31 단계 시작" 항목의 머리 시각은 어림값이며 실제로는 11:52 무렵에 씀(대기 도구 첫 줄 11:53:17). "12:12 KST — B s31 대기 중" 항목도 실제로는 12:03 무렵에 썼고, 그 안의 "[실행 12:08]" 은 "[실행 12:02]"(대기 도구 끝 줄) 임.
- 고침: 그 항목의 b_ana_launch_wmi.ps1 sha 7544873b… 는 첫 판. 첫 판의 "다른 b_ana 실행 중" 검사가 bash 명령줄의 글(LOG 본문)에 걸려 발사를 거부함(아무것도 띄우지 않음) → 검사를 powershell/pwsh 의 `-File "…\b_ana.ps1"` 로 좁힌 판 34b2e003f63a60e686bb7cf9fa4eb1acc49c8522af82dd55b83696803f48d953 으로 바꿈. b_ana.ps1(11a7deef…)은 그대로.
- [실행 12:03:59] prescan WMI 발사 ReturnValue 0, PID 55688, BELOW_NORMAL. 기록 work/b/ana_prescan.state.txt.

## 2026-10-26 12:08 KST — J1 보고 고침 메모(D-K9-89 ⑦) 결과 · J1_REPORT_CORRECTION.md
- [실행] j1c_launch.ps1 12:00:06 (WMI RV=0, 드라이버 PID 50520, BELOW_NORMAL) → FZP 첫 관측 스캔 9개 하나씩(각 9–11 s) → r4_firstobs.py(사본) exit 0 → j1c_compare.py exit 0 → 12:01:48 ALL_STEPS_DONE. 가드 WAIT 0줄. 그동안 VISSIM 은 다른 세션 PID 29264(rolling_cea)뿐, B 런 없음. kill 0.
- [실행] 점검: K0 J1_REPORT 4bf31b13… 앞뒤 같음 / K1 an 값 = va_metrics J1R 차 0, 스캔 sha 6개 같음 / K2 재셈 J1R = 공개 r4(a8f2df7b…) 차 0, 표시 글 같음 (재셈 r4_cells.csv·r4_tables.json 바이트 같음, r4_firstobs.json·fzp_first 9개는 r4_common sha 칸·scan_sec 밖에 같음) / K3 stats 재현 차 0 / K4 label 재현 / K5 칸 합 ≤ 4e-6 / K6 보고 글 대조 242칸 같음 + §5 3칸 ±0.05 / 재셈 C1–C8 STOP 0.
- [실행] 결과(J1 − NC3, 3시드 v3c3-s31·s41·s43): ④b −271.4/−135.6/−42.6 → −264.3/−134.5/−9.8; ④ +94.6/−534.5/+160.6 → +101.6/−533.4/+193.4 (평균 −93.1 → −79.5, CI 0 포함 그대로); Ω 밖 (a) +113.2/+191.5/+364.2 → +120.3/+192.5/+396.9, 평균 +223.0 → +236.6, CI [+6.5, +439.4] → [−5.3, +478.5] 라 CI 표시 '관측된 차이' → '0 포함'; ③ −18.7/−725.9/−203.6 그대로. 선언 14행 CI 0 미포함 5 → 4. 표시 규칙(J1 방법 §2.5) 바뀐 칸 0 (세 시드·평균, N·W(A·B) 모두 '대기 이전(Ω 밖으로)'). 대조 245칸 중 글자 바뀜 189, 부호 바뀜 7 (Ω 밖 (a) CI 아래 끝 세 자리, §6 ④ 누적 네 칸). 1083 몫 +124.0/0.0/+140.5 → +125.5/+0.0/+165.5. 합집합 밖 1092 +11.7/−0.0/+12.2.
- 산출: SP/j1/analysis/J1_REPORT_CORRECTION.md 6c30e391bc1e9586830b82e974b001a5e17d249da0adf511824fea7308e4f22d (+ .sha256; 조립 j1c_memo_build.py 금지 낱말 8개·Ω 표 점검 통과). 원천 corr/memo_src.md 2c321486…, j1c_compare.json bad91fdb…, j1c_cells.csv 40bd6d8c…, j1c_tables.json 54421192…, 재셈 r4_firstobs.json dcd4dfa3…, 드라이버 로그 ffd60c23…. J1C_PINS 다시 확인 OK 아닌 줄 0.
- 사본: D:/VISSIM_runs/20261001_v3c3/reports/k8/j1_analysis/J1_REPORT_CORRECTION.md (+ .sha256, sha256sum -c OK) 와 j1_analysis/corr/ 60파일 + SHA256SUMS_CORRECTION.txt 2fa61b3004a1f76a166bd159ff792efe7d51539ad671fa7cf84c51ace17b0b35 (원본 대조 불일치 0). 기존 j1_analysis 파일은 건드리지 않음(J1_REPORT 사본 4bf31b13… 그대로).
- 밝힘: 데이터 뒤 방법 변경(사용자 결정), 값은 V-A r4 메모 J1R 칸으로 이미 공개됨. 드라이버 가드는 r4 와 다름(A1 가드 대신 이 작업 흐름의 무거운 python 만). 열린 것: V-A r4 메모 §1 의 '1098·1099 첫 관측 수가 세 팔에서 같음' 은 1099 v3c3-s31 NC3(10,565) 대 V-A·J1(10,690)에서 맞지 않음(NC3 런 끝 remain 122; 숫자 영향 없음, r4 메모는 안 고침). J1_REPORT r2 재조립 여부는 사용자 결정.
- VISSIM 띄움 0, 결정 재생 0, kill 0, 커밋·푸시 0, J1_REPORT·AN 기존 파일·AV/r4·GWT8·D:/VISSIM-merge/frozen·인계 사본·런 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, codex 64cf 숫자 0, 금지 시험 0. 디스크 C 30 GB, D 254 GB.

## 2026-10-26 12:24 KST — 미리 스캔 결과 · 완료 요약 도구 고정 (B 데이터 0)
- [실행] prescan 12:04:00–12:05:23 exit 0(83.8 s, BELOW_NORMAL). 출력 work/vhr_b/scan_out/va_s31.json·nc3_s31.json 이 원본 work/vhr/scan_out 의 같은 파일과 scan_sec 칸 말고 모두 같음. NC3 s31 lf_sha_le_895_1 734a2d88…(첫 프레임 5.1 s), V-A s31 aef8ea5b…(0.1 s 프레임 있음).
- 완료 요약 도구(새로 씀, 읽기만, B 데이터 전): work/b/b_run_summary.py 762420920ad7e96ccb3a63405f453c35b109cee2dbe115bc046d390fdedc37e8 — 런 로그(STAGE·SIM_SEC·DECISIONS_* 줄·결정 줄·유지 T 와 예외 종류·벽시계 분포 n/평균/중앙/p90/최대/>1500/>2400), 래퍼 끝·native_status·launch.log·WATCHDOG_PROGRESS·STOP, 결정 폴더 error.txt 끝 줄·budget wall, 명령 CSV 의 미터 (rate, green) 수·VSL 속도 수(T ≥ 900), .err 줄 종류·주된 글(B 와 NC3 같은 시드), 그리고 있으면 고정 도구 출력(walltimes·dec_extract·ramp_fc·rm_exec·fzp_firstdiff·vhr 접두 sha)을 모음. 빈 B 폴더로만 연기 시험(NC3 .err 만 읽힘).
- [실행] 다른 세션 VISSIM 29264 계속(결정 T=2250). 건드리지 않음.

## 2026-10-26 13:30 KST — B s31 대기 중 (다른 세션 VISSIM 넷)
- [실행 13:20–13:22] 다른 세션이 VISSIM 셋을 더 띄움: 42156·33600·40128(TD3 native 학습 C:/Users/TRLAB/Documents/ChatGPT/RL/artifacts/td3/native_training_20261026/run_20261026_v1 의 episode_0000·_evaluation·_baseline, cscript 54632·48808·23272). rolling_cea 29264 는 결정 T=3000. 이 PC VISSIM 4개 = 동시 상한. 모두 건드리지 않음. 기록 work/b/vissim_wait.log.
- 기다림 계속, 상한 23:46 KST(12 h). 넘으면 STOP·보고. kill 0.

## 2026-10-26 13:55 KST — 메인 세션: 세션 재시작 뒤 B 워크플로 상태 확인
- [실행] wf_208fe09b-359: gate1 PASS(T=900 재생 4개 예외 0, 결정 296–403 s), j1-memo PASS, b-run-s31 은 끝나지 못함 — 이전 Claude 프로세스 종료와 함께 끊김. 마지막 기록 13:38 까지 b_wait_vissim.ps1(전경 폴)로 다른 VISSIM 대기 중이었고, B s31 은 발사되지 않음(D:/VISSIM_runs/20261026_codex_b_v3c3 없음). 남은 우리 프로세스 0.
- [실행] 지금 VISSIM 4개 = 상한: 29264(rolling_cea, 10:14~), 42156·33600·40128(13:20~, codex TD3 native 학습 episode_0000·_evaluation·_baseline). 사용자 확인: 이 셋은 codex 가 따로 시킨 일.

## 2026-10-26 14:08 KST — B1 준비(D-K9-90) 시작: 러너 두 곳 고침 → FRZ_B1 동결 → 사전 점검 3시드 (VISSIM 띄움 0, B 데이터 0)
- 근거: 사용자 결정 D-K9-90 (NOTES `SP/K9_1_J1_NOTES_20261013.md` 59e41ff58995207dea199b1320ce5f6c01147331e15af35566030edad3ae221c :296-301) [실행 sha]. 사용자 말(이 세션): "지금 돌아가는 나머지 세 비씸은 codex에서 따로 시킨 업무" → 건드리지 않음.
- [읽음] 고칠 곳(FRZ_B0 러너 `diagnostics/sdmpc_n31_20260924/integration_20260926/run_closedloop3000.ps1`, sha 8b2da855…, 194줄): 발사 전 VISSIM 검사 :169-179 (`$live.Count` 가 0 이 아니면 30 s 기다린 뒤 거부, :173·:178), StallSec 은 워치독 인자 :167 `'-StallSec','2400'`. 사전 점검(-PreflightOnly)은 이 검사를 건너뜀(:168). 워치독은 자기 VISSIM 을 '새 PID + 시작 시각 + 창 제목의 망 파일 이름'으로 찾음(워치독 :588-599), 이름으로 끄지 않음(:770-773) → 시드별 망 이름이 달라 동시 실행에서도 남의 VISSIM 을 고르지 않음 [읽음]. VBS 에는 다른 VISSIM 검사 없음(CreateObject 한 곳 :457) [실행 grep].
- 도구(work/b1/, 새로 씀): b1_edit_runner.py f6cfa40e6019ef9baac609971b7b12de9e5b74a3a21936a14671229148a02b16 (입력 sha 가 FRZ_B0 러너여야 함, 옛 글이 꼭 한 번씩, 세 곳만 바꿈) / b1_tree_check.py e339b71fcfeb5d578e5bb012989146fd480e904d75de4e6d809dcaa4f5b6e75c (FRZ_B0 의 freeze_manifest 를 -B 로 import 해 같은 제외 규칙으로 파일표·차이) / b1_seat_logic_test.ps1 9ce90273a96db6aae7fe84d45737280a3a627a02da0a6588c9cbdc23b55bf0c6 (러너의 발사 전 블록을 꺼내 Get-CimInstance·Start-Sleep 을 흉내 내고 VISSIM 0–6 개로 실행) / b1_preflight_wrapper.ps1 02309fe3d8d46b58cce7dddd79dcedad4a2daddbd4a775fe6bfa32ead1846f3a (← g1_preflight_wrapper 17549a56…: FRZ 인자, b1 뿌리, 러너를 Start-Process 로 띄워 도는 동안 워치독 자식 명령줄과 상태 파일 'preflight' 단계 사본을 기록) / b1_summary.py 9e6c601e4736541af48a4a3be7297f1008c341b2288d4d664cba324fa4cb5b51 / b1_chain.ps1 54fe6e1959385faeb79bb290a26bd7fe804a2231a8c6f7352f96cc307adc4075 / b1_launch_wmi.ps1 f7ee6cfcab71729d6036a71eddd9a4e2bdbd30647317e11c8a2509a03ff8aa42 (WMI, BELOW_NORMAL 16384).
- [실행] 연습(scratch 사본, 트리 밖): 고친 러너 PowerShell 구문 오류 0, diff 는 의도한 세 곳 + 주석 한 줄. 좌석 검사 흉내: 고친 것 N=0–3 허용·N=4–6 거부, FRZ_B0 원래 것 N=0 만 허용·N≥1 거부.
- 차례(b1_chain.ps1): b1/source = 새 git 저장소(커밋·브랜치 없음)에 b0/source HEAD(a49981ff)를 fetch·detached → b0/source 를 robocopy(B0 연습과 같은 /XD /XF) → 파일표가 FRZ_B0 FREEZE.json 과 같은지(0 차이) → 러너 고침 → 러너만 다른지 → 좌석 검사 시험 → codex freeze_worktree.ps1(FRZ_B0 와 같은 바이트인지 먼저 확인) → FRZ_B1 FREEZE.json 대 FRZ_B0: 러너만 → verify → 사전 점검 s31·s41·s43 하나씩 → verify 다시 → 요약. 실패하면 그 자리에서 멈춤(chain_b1.stop).
- [실행 14:06] 디스크 C 26.7 GB, D 252.0 GB. 지금 VISSIM 2개(29264 rolling_cea, 40128 codex TD3; 42156·33600 은 그 사이 끝남) — 모두 남의 것, 건드리지 않음. 이 단계는 VISSIM·B 런을 띄우지 않음.

## 2026-10-26 14:11 KST — B1 준비 1차 시도 멈춤(robocopy 인자) · 고쳐서 2차 발사
- 고침(앞 항목): 머리 시각 "14:08" 은 어림값, 실제로는 14:06–14:07 에 씀. 체인 1차 발사 14:07:12 (WMI RV=0, PID 26872, BelowNormal).
- [실행] 1차: git init·fetch(FETCH_HEAD a49981ff, b0/source HEAD 에서)·detached checkout 까지 됨, robocopy exit 16 으로 멈춤(chain_b1.stop). 까닭 [실행]: `/UNILOG:(Join-Path …)` 를 PS 5.1 이 인자 둘('/UNILOG:', 경로)로 나눔 → 잘못된 인자, 아무것도 복사 안 됨. 러너 고침·동결·사전 점검 전 단계라 데이터 영향 없음.
- 처리: 1차 폴더는 지우지 않고 `D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1_attempt1_robocopy_arg` 로 이름만 바꿔 둠, 상태 파일은 work/b1/chain_b1_attempt1.state.txt·.stop. b1_chain.ps1 의 robocopy 줄만 고침(로그 인자를 먼저 문자열로 만듦, 주석 두 줄): 54fe6e19… → cba337848953c4e256853aa5ce09e99f436dc8fbd28f6a1e3e8ff39439f9a771. 같은 꼴 인자 전달을 python argv 출력으로 확인 [실행]. 다른 도구 sha 그대로.

## 2026-10-26 14:19 KST — B1 준비 결과: FRZ_B1 동결·사전 점검 3시드 · PRE_B_CONCURRENT.md 고정 (VISSIM 띄움 0, B 데이터 0)
- 고침(앞 항목): "14:11 KST — 1차 시도 멈춤" 항목의 머리 시각은 어림값, 실제로는 14:08 무렵에 씀. 2차 발사는 14:08:22 (WMI RV=0, PID 35892, BelowNormal; 영수증 work/b1/launch_receipts.log).
- [실행] 2차 체인 14:08:22–14:14:01, 모든 단계 exit 0, 상태 work/b1/chain_b1.state.txt 0b746bcdc3a994d2c7c1cc58e57cf4d9547eff78f3e829a7f6447221ce13e75c.
  - b1/source: FETCH_HEAD a49981ff(b0/source HEAD), robocopy exit 1. 파일표 대 FRZ_B0 FREEZE.json: 바뀜 0·빠짐 0·더함 0 (7,989; diff_src_preedit_vs_frzb0.json eb7da08b647f553354c4b74f0a250bcac5da11355d8e3cc18254605a4de3072d). git-state 앞뒤 같음(e532873b…, head a49981ff, 3,653줄).
  - 러너 고침: EDIT_OK 8b2da855… → 6ff68b385a4bf6dab23a26bea5a6015641a77808230bfc8366bbc5d2554b38f7, 194 → 195줄, +158 B (edit_record.json 9ebc00ceb28f586940b8119d8043641f111048c051c8692366b7c0a3fa2e1ad0). 전체 diff work/b1/runner_b0_to_b1.diff ae599d8b396bbc0c0709f45e4e70660d4cf1aa5abdde059740ac90814c98d67e: :167 '-StallSec','2400' → '3600'; :173 주석 한 줄 더함; :174 `$live.Count -and` → `$live.Count -ge 4 -and`; :179 `if($live.Count)` → `if($live.Count -ge 4)` 와 거부 글. 고친 뒤 대 FRZ_B0: 바뀜 1(러너)·빠짐 0·더함 0 (7b7c9db7…).
  - 좌석 검사 흉내(b1/source 러너): N=0–3 띄움, N=4–6 거부 (seat_test_b1.json 6d5c21a16ccb36c84de316275507fc6bc99cddc3711a3f7b0dc2c4e437414e87).
  - 동결: freeze_worktree.ps1(2f8ff1ea…, FRZ_B0 의 것과 같은 바이트) → **FREEZE_OK** FRZ_B1 = D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1/frozen/sdmpc31_a49981ff_202610261410, FREEZE.json **558de2c1b80799a9bedfb192b40b6f5cfa2775853b3431eb181f7b25beca10d1**, 7,989 파일, 495,607,946 B, head a49981ff, status 3,653(status sha 558ddef8… = FRZ_B0 와 같음), 122.2 s. FRZ_B1 대 FRZ_B0 FREEZE.json: 바뀜 1(러너)·빠짐 0·더함 0 (diff_frzb1_vs_frzb0.json c4672774b14b83c87be722805010e849735cdd2f2e4a8ecf9271712ddfd2de91). FREEZE_VERIFIED 14:13:00·14:14:01(사전 점검 앞뒤).
  - 사전 점검(-PreflightOnly, VISSIM·cscript 0, 하나씩): s31 exit 0 17.5 s provenance 0d3ec1c35612f2204b746ec10828fabf4d2010cbdf7741b57e482556b8bac227 / s41 exit 0 14.8 s 86ae6e5d468029c44c9873f43517f5433fe5eb96a0fe72e08141cec1f54006b8 / s43 exit 0 14.2 s d8e6ea3fb078371e4dd0f887795049a725135bbe07ed92bc21788c17802cc7dc. 셋 모두: FREEZE_VERIFIED(FRZ_B1 558de2c1), 망 3de889f0, 튜닝 729640af, 유지 env hold_previous_on_exception·1·0, freeze 핀 558de2c1, plant 11842498, 검지 294행 108debbb, wu-link, 시드·9,000 s, 작업 뿌리 FRZ_B1, 빈 RW 값 없음, StallSec 3600 = 워치독 자식 명령줄과 러너 상태 'preflight' 단계 인자 둘 다(provenance 에는 StallSec 칸 없음, 워치독 :808-832). 관문 1(FRZ_B0) 같은 시드 provenance 와 잎 비교: 다른 잎 created_at·run_id·observation/freeze/sha256 셋뿐.
  - 요약 b1_summary.py → b1_summary.json 89040b1a990a61f228c3a45e5d9b4af6b688175d0139220095c466eb41eda227: 트리 검사 13개·시드별 검사 16개 모두 true, B1_PASS True.
- [실행 14:14] FRZ_B0 다시 verify: FREEZE_VERIFIED 853d1c4f…(그대로). COMPARE_RULE_B f902f7f0… · PINS_B 5e8ffbc5… 그대로, sha256sum -c 54줄 OK. PRE_B 3149cfe5…·GATE1 aae6b0ca…·NOTES 59e41ff5… 그대로.
- **고정: codex_handoff/b/PRE_B_CONCURRENT.md sha256 3d21dddd5cf4c75ba02dc826f6ea15370d21cf26062e7a328efbb5d15a243fef** (+ .sha256). 내용: 바꾼 것(러너 두 곳, 전체 diff)·까닭(D-K9-90)·동시 실행이 바꿀 수 있는 것(벽시계뿐: ignore_wall_time_limits true, area_follower_objective.py:2363-2397, 유지는 예외 한정·시한 0; 빈틈은 [추론])·그대로인 것(COMPARE_RULE_B·PINS_B·PRE_B §1, FRZ 만 FRZ_B1)·발사 정책(분리 발사기, s31→s41→s43 한 번씩, 최대 3 동시, 12 h 상한, 이상 종료 시 더 안 띄우고 STOP)·자리 규칙(PC 전체 ^Vissim < 4, 잠금 + 직전 재셈, 러너 거부는 발사 시도 실패)·한 번 재발사 규칙(499 s 무진행 → 120 s CPU 확인 → 멈췄으면 그 런 PID 만 끄고 s<seed>_try1_stalled 로 이름 바꾼 뒤 한 번 재발사). 판정 낱말 점검 0건(va_report_build FORBIDDEN 8개).
- 1차 시도 폴더 D:/VISSIM-merge/k8_gate_trees/codexhandoff/b1_attempt1_robocopy_arg 는 남겨 둠(체크아웃만 있음, 쓰이지 않음).
- [실행 14:18] VISSIM 1개(29264 rolling_cea, 남의 것). 우리 프로세스 0. 디스크 C 26.5 GB, D 250.9 GB. D:/VISSIM_runs/20261026_codex_b_v3c3 없음.
- VISSIM·cscript 띄움 0, B 폐루프 0, kill 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·기존 런 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, codex 64cf 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B 바꾸지 않음.

## 2026-10-26 14:40 KST — B 발사기 단계: 발사 도구 고정 · 연습(dry run) 통과 (발사 전, B 데이터 0)
- 근거: D-K9-90, PRE_B_CONCURRENT 3d21dddd…(§4 "발사기 단계에서 FRZ_B1 판을 새로 쓰고 첫 발사 전에 sha 를 LOG 에"), PRE_B §1. 사용자 말(이 세션): "지금 돌아가는 나머지 세 비씸은 codex에서 따로 시킨 업무" → 남의 VISSIM 은 건드리지 않음.
- 새로 쓴 도구 (모두 SP/codex_handoff/b/, ASCII, PS 구문 오류 0) [실행 sha256]:
  - b_wrapper_b1.ps1 93814842ae7a504e714c309a58caf77621aba153db36fa953258db72db5a1185 (← work/b/b_wrapper.ps1 43348294…. 다른 곳 셋뿐: FRZ = FRZ_B1; -Try 인자(자리 거부 시도 번호, -Attempt 와 따로) 와 기록 이름 run<A>_try<T>; 러너 끝난 뒤 native_status.json 을 b_launch/native_status_run<A>_try<T>.json 로 복사. env 지우기·env_hsw·PYTHONHASHSEED=0·러너 인자(PRE_B §1)는 같음 [실행 diff]).
  - b_launcher.ps1 cb657ecbe0aa01fb810137422646fdba3c652191db7cc070c040058ae692d463 (PS 5.1, WMI 분리 발사됨). 하는 일: 90 s 마다 폴하고 폴마다 한 줄 b/b_launcher.log; s31→s41→s43 차례; 잠금 파일(FileShare.None) 잡고 PC 전체 ^Vissim 수 + 우리 대기 중 런(아직 VISSIM_PROCESS 없음) < 4 일 때만 발사, 발사 직전 다시 셈; 발사 = WMI Create(Normal 32, 숨김, 작업 폴더 FRZ_B1) 로 codex pwsh 7 래퍼; 발사 전 _launcher/launched_s<seed>_run<A>_try<T>.json 을 CreateNew 로 만듦(있으면 다시 안 띄움, 재시작해도); 영수증 _launcher/receipt_*·<res>/b_launch/wmi_launch_run<A>_try<T>.json·<root>/wmi_launch_lines.txt; 그 런의 VISSIM_PROCESS 줄(WATCHDOG_PROGRESS.txt, 없으면 launch.log)·런 끝·600 s 까지 잠금 유지; 그 뒤 소유 프로세스 나무 _launcher/owned_<key>.json. 발사 멈춤(LAUNCH_STOPPED.json, 재시작해도 유지): STOP_B_LAUNCHER 또는 STOP 파일, 이상 종료(러너/래퍼 ≠ 0 중 자리 거부·STOP 거부 아닌 것, SIM_DONE·SIM_SEC=9000 없음, 래퍼 오류, 기록 없이 래퍼 사라짐, WMI RV ≠ 0, 영수증 없는 표지), 디스크(C<8, D<8×(우리 활성 런+1)), 고정 파일 sha 바뀜(COMPARE_RULE_B·PINS_B·PRE_B_CONCURRENT·FREEZE.json 558de2c1·설정 729640af·러너 6ff68b38·망 3de889f0·래퍼 93814842), 자리 대기 12 h 초과, 시도 20 초과. kill 없음. 우리 활성 런이 없고 (모든 시드 끝 또는 발사 멈춤)이면 끝냄; 첫 시작부터 72 h 면 포기.
  - b_status.ps1 f07a8f6b9621f457b904e53cda83b422338bb1407ca0c9b6cf6b41528e2d3c37 (읽기만: 시드별 시도·상태, 래퍼·VISSIM 생존, sim_sec, 결정 수·마지막 T·벽시계·exit≠0 수·최대 벽시계, 진행 중 결정, 유지 시도·유지 T, 진행 신호 나이(>499 s 표시), 런 나무 CPU 초, 러너 종료, SIM_DONE/SIM_SEC, 워치독 끝 줄).
  - b_launcher_start.ps1 9c818f1f4d5e6aadd338060e52e84b25f400e5741204cb41963cdf547b635c23 (발사기 sha·래퍼 sha 확인, 이미 도는 발사기 있으면 거부, WMI Create Normal 숨김, b/b_launcher_start_receipts.log).
  - b_launcher_dryrun.ps1 fa5652b59f56e1e3613b9ed5a482f45e9056aaf7b30d81b36e7339ab8ee6e7d1 (연습: -Mode dryrun, WMI·프로세스 시작 없음, 뿌리 b/dryrun/…, 경우마다 기대값 대조).
- [실행] 연습 b/b_launcher_dryrun.log bc2c63185f59b7daa087186ee27f79c7e9d25adeb2b5c014ec06bc2e3ac7708e (세 번 기록 모두 남김):
  - 1차(14:33, 발사기 b1b0e128…): 7/15. **결함 하나 찾음**: 함수 안 지역 변수 `$mode`(시도 이름) 가 PowerShell 이름 대소문자 무시 때문에 스크립트 인자 `-Mode` 를 그 함수와 그 함수가 부르는 함수에서 가렸음 → 실제 모드에서는 발사 함수가 WMI 대신 연습 분기로 가고 생존 검사가 틀릴 뻔함. 고침: 지역 이름 `$tmode`, 모드는 `$script:LMODE` 로만 읽음(AST 로 다른 가림 없는지 확인 — 남은 가림은 자기 지역에서만 쓰는 이름).
  - 2차(14:35, cb657ecb…): 14/15, 남은 1 은 내 기대값 잘못(모든 시드가 끝나면 'all seeds ended' 로 끝남). 3차(14:37, 같은 발사기, 하네스 fa5652b5…): **15/15 PASS**.
  - 경우: A 4·5개 바쁨 → 자리 남 → s31·s41·s43 차례 발사, 끝나면 종료 / B 재시작(기존 표지 s31 은 다시 안 띄우고 s41·s43 만) / C·C2 STOP 파일(발사 전·s31 뒤) / D 러너 자리 거부 → try2 / E·E2 이상 종료(러너 exit 1, 기록 없이 래퍼 사라짐) → 남은 시드 안 띄움 / F 직전 재셈 4 → 안 띄움 / G VISSIM 600 s 안에 안 보이면 대기 1 로 셈 / H 멈춤 기록 → run2 한 번, run2 도 멈추면 이상 종료 / I·I2 디스크 / J 12 h 초과 / K 두 번째 발사기(인스턴스 잠금) exit 2 / L 영수증 없는 표지 → 이상. 연습 앞뒤 실제 뿌리 D:/VISSIM_runs/20261026_codex_b_v3c3 없음, PC VISSIM [29264] 그대로.
  - b_status.ps1 시험: 연습 뿌리 둘·없는 실제 뿌리, A1 runlog 사본(scratch)으로 파싱 확인(결정 55·exit≠0 6·유지 6 = A1 기록과 같음).
- 선언 해석 [추론, PRE_B_CONCURRENT 는 바꾸지 않음]: (1) 자리 셈에 '우리 대기 런' 을 더한 것은 §6 보다 엄격할 뿐 느슨하지 않음. (2) 과제 글의 72 h 는 발사기 수명, 자리 대기 상한은 §5-4 의 12 h(첫 시작부터) 그대로. (3) §7 재발사의 자리 대기 상한은 §7 에 없어 멈춤 기록 시각부터 12 h 로 둠. (4) STOP 파일은 과제의 STOP_B_LAUNCHER 와 예전 도구의 STOP 둘 다. (5) §6-2 의 'launch.log 의 VISSIM_PROCESS 줄' 은 워치독 Log 가 같은 줄을 WATCHDOG_PROGRESS.txt 와 호스트 출력(=launch.log) 둘에 씀(워치독 :471-478) [읽음] → 앞 파일 먼저, 없으면 launch.log.
- 감시 단계가 할 일(§7 한 번 재발사): b_status 로 499 s 무진행 확인 → 120 s 간격 b_status 두 번으로 cpu_tree 비교 → 멈췄으면 **먼저** _launcher/stalled_s<seed>_run1.json 을 씀 → owned_<key>.json 의 그 런 PID 만(PID+시작 시각) 끔 → <root>/s<seed> 를 s<seed>_try1_stalled 로 이름 바꿈 → 발사기가 run2 를 자리 규칙으로 한 번 띄움. 순서를 어기면(멈춤 기록 전에 끄면) 발사기는 '기록 없이 래퍼 사라짐' 으로 보고 발사를 멈춤.
- [실행 14:39] VISSIM 1개(29264 rolling_cea, 남의 것), 우리 프로세스 0, 디스크 C 26.5 GB·D 250.5 GB, 실제 뿌리 없음. COMPARE_RULE_B f902f7f0·PINS_B 5e8ffbc5·PRE_B_CONCURRENT 3d21dddd 그대로.

## 2026-10-26 14:46 KST — B 발사기 시작 · v3c3-s31·s41·s43 세 런 발사 (B 데이터 시작)
- [실행 14:40:07] b_launcher_start.ps1 → WMI Create ReturnValue 0, **발사기 PID 30860**(powershell 5.1, Normal 32, 숨김, 부모 WMI). 영수증 b/b_launcher_start_receipts.log. 발사기 sha cb657ecb…, 래퍼 sha 93814842… (14:40 항목 값 그대로). 첫 시작 기록 D:/VISSIM_runs/20261026_codex_b_v3c3/_launcher/first_start.json 14:40:07 → 자리 대기 상한 2026-10-27 02:40, 포기 2026-10-29 14:40 KST.
- [실행] 발사 (모두 try1, 한 번씩; 기록 <root>/wmi_launch_lines.txt 9914bc27…, receipt_s31 3206da29…·s41 7c7292ee…·s43 e3927c02…):
  - v3c3-s31: 14:40:09, 발사 직전 PC VISSIM 1(29264), 래퍼 42296 → 러너 46544 → 워치독 39344 → cscript 33440, VISSIM 38792(14:40:31). 잠금 해제 62 s 뒤(VISSIM_PROCESS).
  - v3c3-s41: 14:41:22, 직전 VISSIM 2, 래퍼 25476 → 러너 49356 → 워치독 14340 → cscript 35684, VISSIM 55280(14:41:42). 62 s.
  - v3c3-s43: 14:42:36, 직전 VISSIM 3, 래퍼 54020 → 러너 54556 → 워치독 34888 → cscript 45588, VISSIM 23840(14:42:56). 57 s.
  - 소유 PID 표: _launcher/owned_s<seed>_run1_try1.json (PID·시작 시각·명령줄). 결정 python 은 결정마다 cscript 아래에 새로 뜸.
- [실행] 확인: 러너 FREEZE_VERIFIED 558de2c1 (s31 runner 로그 첫 줄). 러너 인자 = PRE_B §1 + FRZ_B1(세 시드 wrapper_run1_try1_runner_cmd.json). native_status 'native_running' 단계 인자에 -StallSec 3600. 래퍼 env: RW_* 0개, PYTHONHASHSEED=0·env_hsw, Normal, pwsh 7.6.5; env 이름 46개와 값이 A1 래퍼(wrapper_run_env.json)와 모두 같음, python 탐침(3.12.2·numpy 2.3.5·numba 0.67.0·cpu 이름·AVX512 표)도 A1 과 같음.
- [실행 14:43:46 b_status] s31 sim_sec 300 결정 3(T=300 17.1 s exit 0), s41 sim_sec 150 결정 2, s43 기동 중(DEMAND_DONE). 유지 0, .err 0 B.
- [실행 14:45:16] 발사기 폴 5: PC VISSIM 4 = [29264 남의 것, 38792 s31, 55280 s41, 23840 s43] = 상한, action=nothing_to_launch, 90 s 간격으로 계속 돎. 디스크 C 26.5 GB, D 250.3 GB.
- 남의 VISSIM 29264(rolling_cea)는 건드리지 않음. kill 0. 자리 거부 0, 재발사 0, 이상 종료 0. 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·기존 런 폴더·Y: 쓰기 0. COMPARE_RULE_B·PINS_B·PRE_B_CONCURRENT 바꾸지 않음.
- 감시: `powershell -NoProfile -ExecutionPolicy Bypass -File SP/codex_handoff/b/b_status.ps1` (읽기만). 발사 멈춤은 D:/VISSIM_runs/20261026_codex_b_v3c3/STOP_B_LAUNCHER 파일(이미 도는 런은 안 끔).

## 2026-10-26 14:51 KST — B 감시 단계 시작 · 감시·분석 도구 고정 (B 런 셋 도는 중)
- 근거: D-K9-90, PRE_B_CONCURRENT 3d21dddd… §5·§7, COMPARE_RULE_B f902f7f0… §7.5. 사용자 말(이 세션): "너 꺼졌었는데 다시 한 번 확인해볼래??", "지금 돌아가는 나머지 세 비씸은 codex에서 따로 시킨 업무" → 남의 VISSIM 은 건드리지 않음.
- [실행 14:46:36·14:49:10 b_status] 발사기 PID 30860 살아 있음(90 s 폴, 마지막 action=nothing_to_launch). PC VISSIM 4 = 29264(남의 것, rolling_cea) + 38792 s31 + 55280 s41 + 23840 s43. 14:46 기준 s31 sim_sec 600·결정 5(T=0–600), s41 450·결정 4, s43 300·결정 3. 모두 exit 0, 유지 0, 런 로그 .err 0 B, 무진행 최대 40 s. 디스크 C 26.5 GB, D 250.2 GB.
- 새 도구 (work/b/, ASCII, PowerShell 구문 오류 0) [실행 sha256]:
  - b_poll_wait.ps1 4a0b0dd493b0d8136691cb3719922f36297f5791354000dfa38732008290d0b9 — 읽기만. b_status.ps1 을 30 s 마다 불러, 깃발(발사기 유무·발사 멈춤·STOP 파일·디스크·VISSIM > 4·시드별 시도 목록·래퍼 생존·T=900 끝남·exit ≠ 0 수·유지 수·IDLE_OVER_499·SIM_DONE·래퍼 끝·native_status)이 바뀌면 바로 끝남. 한 번 ≤ 520 s.
  - b_ana_seed.ps1 d9f3242dbf5142fe47c3644715a4a42a7da3ab37be23d7c65018fefb48fcdfd1 — b_ana.ps1(11a7deef…, s31 만 앎)과 같은 일을 시드 인자로. prescan = vhr_scan_b.py va_sS nc3_sS. stage = walltimes_b_sS → ramp_fc_b_sS → rm_exec_b_sS → dec_extract_b sS → vhr_scan_b j1_sS → a1_fzp_firstdiff_b_sS. 부르기 전 PINS_B sha 대조, 고정 도구는 고치지 않음. python -B, PYTHONHASHSEED=0, 스레드 1.
  - b_ana_seed_launch_wmi.ps1 49f3d8c95f90c5ecb8af0f567b7b5c97121c6f549298405063c305efbb5feabc — WMI 분리 발사, BELOW_NORMAL 16384, b_ana·b_ana_seed 가 이미 돌면 거부(한 번에 하나).
  - 완료 요약은 work/b/b_run_summary.py 762420920ad7e96ccb3a63405f453c35b109cee2dbe115bc046d390fdedc37e8 (12:24 고정) 를 그대로 씀.
- 계획: NC3·V-A v3c3-s41·s43 미리 스캔(B 데이터 아님, COMPARE_RULE_B §7.5 끝, 접두 sha 짝 대조용). 런이 끝나면 시드마다 stage → b_run_summary → B_RUNS.md.
- 감시 규칙은 PRE_B_CONCURRENT §7 그대로: 무진행 499 s 넘으면 120 s 동안 그 런 나무 CPU 확인 → 늘지 않으면 stalled 기록 먼저, 그 런 PID 만 끄고, 결과 폴더 이름만 s<seed>_try1_stalled 로 바꿈, 발사기가 run2 를 한 번 띄움. 이상 종료면 STOP_B_LAUNCHER 를 만들고 도는 다른 B 런은 끝까지 둠.

## 2026-10-26 15:03 KST — B 감시: 세 런 첫 제어 결정 T=900 끝(exit 0) · NC3·V-A s41·s43 미리 스캔
- 고침(앞 항목): "14:51 KST — B 감시 단계 시작" 항목은 실제로 14:50 에 씀.
- [실행] 미리 스캔(b_ana_seed_launch_wmi.ps1, WMI, BELOW_NORMAL, 한 번에 하나): prescan s41 14:50:24 PID 47836 → vhr_scan_b va_s41 nc3_s41 exit 0 91.8 s; prescan s43 14:53:42 PID 42560 → va_s43 nc3_s43 exit 0 89.9 s. 기록 work/b/ana_prescan_s41.state.txt·ana_prescan_s43.state.txt, 영수증 work/b/launch_receipts.log.
- [실행] 점검(work/b/cmp_prescan.py → cmp_prescan.out.txt): vhr_b/scan_out 의 va·nc3 s31·s41·s43 여섯 파일이 원본 work/vhr/scan_out 같은 파일과 scan_sec 칸 말고 모두 같음. NC3 접두(≤ 895.1 s) LF sha: s31 734a2d88…(387,397행), s41 b61cdb73832c3ad5a97b4bd29254c00d685b407cf3373714ec0e38f1a2d77906(398,331행), s43 86c06c735b3aba291da9a2efc94fb6f4086ea90392ba2ea16410b9823605b9a8(393,558행). V-A s43 는 0.1 s 프레임이 없고 NC3 s43 와 접두 sha 가 같음; V-A s31·s41 은 0.1 s 프레임 1행이 더 있음.
- [실행 runlog] 첫 제어 결정 T=900 (워밍업 결정 T=1·150·300·450·600·750 은 모두 exit 0, 13.5–21.0 s):
  - v3c3-s31: wall 488.32 s, exit 0, stdout status ok, action_000900.json controller_status ok·selection best_observed_feasible_sdmpc, 14:57:25 무렵 끝.
  - v3c3-s41: wall 521.82 s, exit 0, status ok, 14:59 무렵 끝.
  - v3c3-s43: wall 516.41 s, exit 0, status ok, 15:01 무렵 끝.
  - 그때 동시 상황: PC VISSIM 4(남의 것 1 + B 셋), B 세 런의 T=900 결정이 서로 겹쳐 돎. 관문 1 재생(다른 VISSIM 1–2개)의 296–403 s 보다 긺 — 동시 실행 아래 잰 값이라 같은 조건이 아님(PRE_B_CONCURRENT §3).
  - 유지 0, exit ≠ 0 0, 런 로그 .err 0 B. 결정 JSON 한 개 약 54 MB + joint.json 약 50 MB [실행 ls s31].
- 발사기 30860 계속 90 s 폴, action=nothing_to_launch. 디스크 C 26.5 GB, D 249.6 GB. kill 0, 재발사 0.

## 2026-10-26 16:54 KST — B 감시 중간 (세 런 정상 진행)
- [실행 16:53:06 b_status] v3c3-s31·s41·s43 모두 sim_sec 2400, 결정 17개(T=0–2400) 모두 exit 0, 유지 0. 제어 결정(T ≥ 900) 벽시계 최대: s31 597.71 s, s41 608.54 s, s43 588.18 s. 무진행 최대 105 s(499 s 문턱 아래). PC VISSIM 4 = 29264(남의 것) + B 셋. 발사기 30860 계속 폴(nothing_to_launch). 디스크 C 26.1 GB, D 244.2 GB. kill 0, 재발사 0.

## 2026-10-26 18:01 KST — B 감시 중간 (세 런 정상 진행)
- [실행 18:00:11 b_status] 세 런 모두 sim_sec 3150, 결정 22개(T=0–3150) 모두 exit 0, 유지 0, T=3300 결정 도는 중. 제어 결정 벽시계 최대: s31 597.71 s, s41 617.69 s, s43 634.69 s. 무진행 최대 106 s. PC VISSIM 4 그대로(29264 남의 것). 디스크 C 26.9 GB, D 241.3 GB. kill 0, 재발사 0.

## 2026-10-26 19:07 KST — B 감시 중간 (세 런 정상 진행)
- [실행 19:06:38 b_status] s31·s41 sim_sec 4050 결정 28개, s43 sim_sec 3900 결정 27개(T=4050 도는 중). 모두 exit 0, 유지 0. 제어 결정 벽시계 최대: s31 597.71 s, s41 690.86 s(T=4050), s43 634.69 s. 무진행 최대 약 110 s. PC VISSIM 4 그대로. 디스크 C 27.0 GB, D 238.0 GB. kill 0, 재발사 0.

## 2026-10-26 20:13 KST — B 감시 중간 (세 런 정상 진행)
- [실행 20:12:59 b_status] s31 sim_sec 4950 결정 34개, s41·s43 sim_sec 4800 결정 33개. 모두 exit 0, 유지 0. 제어 결정 벽시계 최대: s31 597.71 s, s41 690.86 s, s43 634.69 s. 무진행 최대 125 s(20:04 s31 T=4950 안). PC VISSIM 4 그대로. 디스크 C 27.0 GB, D 235.0 GB. kill 0, 재발사 0.

## 2026-10-26 21:12 KST — B 감시 중간 (세 런 정상 진행)
- [실행 21:11:10 b_status] s31 sim_sec 5850 결정 40개, s41·s43 sim_sec 5700 결정 39개. 모두 exit 0, 유지 0. 제어 결정 벽시계 최대: s31 597.71 s, s41 690.86 s, s43 634.69 s. 무진행 최대 약 125 s. PC VISSIM 4 그대로. 디스크 C 30 GB, D 232.0 GB. kill 0, 재발사 0.

## 2026-10-26 22:10 KST — B 감시 중간 (세 런 정상 진행 · 남의 VISSIM 끝남)
- [실행 21:19:32 b_status] 남의 VISSIM 29264(codex rolling_cea)가 21:11–21:19 사이에 스스로 끝남. 우리는 건드리지 않음. 그 뒤 PC VISSIM 3 = B 셋.
- [실행 22:09:19 b_status] s31 sim_sec 6750 결정 46개, s41·s43 sim_sec 6600 결정 45개. 모두 exit 0, 유지 0. 제어 결정 벽시계 최대: s31 597.71 s, s41 690.86 s, s43 634.69 s. 무진행 최대 약 125 s. 발사기 30860 계속 폴(nothing_to_launch). 디스크 C 30 GB, D 229.6 GB. kill 0, 재발사 0.

## 2026-10-26 23:09 KST — B 감시 중간 · 동시 실행 기록 도구
- [실행 23:08:20 b_status] s31 sim_sec 7800 결정 53개, s41·s43 sim_sec 7500 결정 51개. 모두 exit 0, 유지 0. 제어 결정 벽시계 최대: s31 597.71 s, s41 690.86 s, s43 634.69 s. 무진행 최대 약 126 s. PC VISSIM 3 = B 셋. 디스크 C 30 GB, D 227.5 GB. kill 0, 재발사 0.
- 새 도구 work/b/b_concurrency.py 5d6e8ab4fe6e27cab0e0bbc902b27a552f18ee878a43164ae387ae7ffd3cc3bc (읽기만): 결정마다 시작 = state_T.json 시각, 끝 = action_T.decision_budget.json 시각, 그 사이 함께 돈 B 결정 수(시간 가중 평균·최대), 남의 VISSIM 29264 있음/없음/모름(21:11:10 에 있었고 21:19:32 에 없었음). 부분 자료로 연습만 함(work/b/b_concurrency_test.json).

## 2026-10-26 23:20 KST — 남의 VISSIM 새로 뜸 · 동시 실행 도구 v2
- [실행 23:16:48 b_status, 23:17 Get-CimInstance] 남의 VISSIM200.exe PID 23564 가 23:11:56 에 뜸(부모 PID 1204, 우리 것 아님). 건드리지 않음. PC VISSIM 4 = B 셋 + 23564. 우리 B 셋은 모두 이미 떴으므로 발사기는 더 띄울 것이 없음.
- work/b/b_concurrency.py 를 v2 로 고침: 5d6e8ab4… → 38fb94cbd27996c0ef6384b2da30ea88bfd070e4918349cc50522e5ff2324ca2. 바뀐 것: 남의 VISSIM 구간을 JSON 파일(work/b/other_vissim_windows.json: 29264 = 10:14–[21:11:10, 21:19:32], 23564 = 23:11:56–아직)로 받아 결정마다 있음/없음/모름을 셈. 결정 구간·동시 B 결정 수 계산은 그대로. 부분 자료로 연습 exit 0.

## 2026-10-27 00:15 KST — B v3c3-s31 끝 (정상 종료) · s31 분석 단계 발사
- [실행 00:12:38–00:14:04 b_status·발사기 로그] v3c3-s31: 런 로그 STAGE=SIM_DONE, SIM_SEC=9000, 결정 61줄(T=1·150–9000) 모두 exit 0, 유지 0, 런 로그 .err 0 B. 러너 종료 0, 래퍼 벽시계 34,368.9 s, native_status requested_native_arms_complete_unanalyzed. 발사기 TRY_END s31_run1_try1 status=completed (00:13:41). VISSIM 38792 닫힘. 시도 1번, 재발사 0.
- 남의 VISSIM 23564 는 23:42:52 에 있었고 23:51:11 에 없었음(스스로 끝남, 건드리지 않음). work/b/other_vissim_windows.json 에 적음.
- [실행 00:14:10] b_ana_seed_launch_wmi.ps1 -Plan stage -Seed 31 → WMI RV 0, PID 37652, BELOW_NORMAL. 기록 work/b/ana_stage_s31.state.txt.
- s41·s43 은 sim_sec 8700, 계속 돎. PC VISSIM 2 = B 둘.

## 2026-10-27 00:25 KST — s31 분석: rm_exec_b_s31 은 쓰인 대로 못 돎(B 런에 LDP 없음) · 나머지 도구용 계획 추가
- [실행 00:14:11–00:15:51 work/b/ana_stage_s31.state.txt] walltimes_b_s31 exit 0(1 s), ramp_fc_b_s31 exit 0(97.8 s), rm_exec_b_s31 exit 1: FileNotFoundError D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_9101_001.ldp. [실행 ls] B s31 vissim_eval 에는 fzp(1,122,662,375 B)·lsa·mer 셋뿐, LDP 파일이 없음. 그래서 실행기가 그 자리에서 멈춤(dec_extract·vhr_scan_b j1_s31·a1_fzp_firstdiff 는 안 돎).
- COMPARE_RULE_B §5 X6 에 따라 rm_exec 는 고치지 않고 대체 계산도 하지 않음 → 미터 실행 대조(§4-4) 칸 = '못 냄(B 런 폴더에 LDP 없음)'. X6 는 비교 분석 단계의 멈춤 조건이므로 열린 것으로 보고함. 이 감시 단계는 런 기록(접두 sha·명령 요약)에 필요한 나머지 고정 도구만 바꾸지 않고 돌림.
- work/b/b_ana_seed.ps1 에 계획 rest(= dec_extract_b sS → vhr_scan_b j1_sS → a1_fzp_firstdiff_b_sS, rm_exec 뒤 단계 그대로) 더함: d9f3242d… → 737ffc60dc7a2e209abdbd0856b81fbbdd8f83183ad430b2c819ee36d577f17c. 발사기 b_ana_seed_launch_wmi.ps1 ValidateSet 에 rest 더함: 49f3d8c9… → 37de941a97511fbc56d128973cd9a788dde32b40038e6bcb892403963801fa85. 고정 도구(PINS_B)는 그대로이며 실행 전 sha 대조.

## 2026-10-27 00:45 KST — B 런 셋 모두 끝 (정상 종료) · B_RUNS.md
- 고침(앞 항목): "00:25 KST — s31 분석: rm_exec…" 항목은 실제로 00:22 에 씀.
- [실행 b_status·발사기 로그] v3c3-s41: STAGE=SIM_DONE·SIM_SEC=9000(RL:6828-6829), 결정 61 모두 exit 0, 유지 0, 러너 종료 0, 래퍼 벽시계 34,993.3 s, TRY_END completed 00:25:51. v3c3-s43: SIM_DONE·9000(RL:6942-6943), 결정 61 모두 exit 0, 유지 0, 러너 종료 0, 35,143.2 s, TRY_END completed 00:28:52. 발사기 30860 `LAUNCHER_EXIT all seeds ended` 00:28:52 (폴 387번). 세 시드 모두 시도 1번, 재발사 0, kill 0, 이상 종료 0, STOP_B_LAUNCHER 안 만듦. 남은 우리 프로세스 0, PC VISSIM 0 (00:40).
- [실행] 감시 동안 무진행 최대 약 126 s(499 s 문턱 아래), PC VISSIM 최대 4. 남의 VISSIM 29264·23564 는 스스로 끝남, 건드리지 않음.
- [실행] 분석(고정 도구 그대로, BELOW_NORMAL, 한 번에 하나): stage s41 00:26:06(walltimes 0, ramp_fc 0, rm_exec 1 — LDP 없음), rest s41 00:28:10–00:31:31(dec_extract 0, vhr_scan_b j1_s41 0, a1_fzp_firstdiff 0); stage s43 00:32:46(walltimes 0, ramp_fc 0, rm_exec 1 — LDP 없음), rest s43 00:35:17–00:38:11(셋 다 0). 세 시드 B vissim_eval = _001.fzp·.lsa·.mer 뿐. → COMPARE_RULE_B §4-4 미터 실행 대조 = "못 냄(B 런 폴더에 LDP 없음)", §5 X6 열린 것(도구 안 고침, 대체 계산 안 함).
- [실행] 접두(≤ 895.1 s) 주 값: s31 B aef8ea5b… ≠ NC3 734a2d88…, s41 B 817dc613… ≠ NC3 b61cdb73…, s43 B = NC3 86c06c73…. 세 시드 모두 B = V-A 접두. s31·s41 의 차이는 0.1 s 프레임 1행(B 에만 차 1대, 링크 90 / 26)뿐, 5.1–895.1 s 프레임 같음(a1_fzp_firstdiff 블록), 900.1 s 프레임도 같음(work/b/b_frame900.py 5e572d787df57bc1973cfb70393ea0f06117444c1a11a6ea6b883b597270c3c5, 행 3,106/3,086/3,057). 0.1 s 다음 첫 다른 프레임 905.1 s. 규칙대로 s31·s41 B − NC3 칸에 "†접두 다름". COMPARE_RULE_B §1 의 "codex 러너 FZP 는 5.10 s 부터" 와 다름.
- [실행] 제어 결정(T ≥ 900, 55개) 벽시계 평균/최대: s31 458.7/597.7 s, s41 470.1/690.9 s, s43 472.3/634.7 s; > 1,500 s 0. VSL 명령 모두 110. 미터 녹색 RM_C10482·RM_C10644 는 55번 내내 10, 나머지 여섯은 2–10 사이로 바뀜.
- 완료 요약: work/b/b_run_summary.py 76242092…(그대로) → b_run_summary_s31.json 1df396eb09edce8903242b1ec5e63688ec04726f61faa097f743cb3e76883a9b / s41 b68d2e87fdbaa74288d57c7434d3373f0109d780463713e8a546575ec0b5c56b / s43 be86d1fe477be80509cba9d83e29b463fa4b63bb3e367f86613f685f4e42ade9. 동시 실행 b_concurrency.py v2 38fb94cb… + other_vissim_windows.json 58946a9dbf7b5a5727cd3cf985cb633fa64c3b3cda2e8d5749ee13c67cfad0cd → b_concurrency.json 10ac8dc4cf6d6681ad8fb6a362ecc70984d07d19a69d2c8abc94029df56f38c2. 새 읽기 도구: cmp_prescan.py 5a2455f6224fcedd8a92f458c43418d7f6be2cb6953d46c04444d863a07e5844, b_digest.py 6c78388fa18ca8a6ae583a49298dfc8b71a1446dc6f535dad867eac95335e87e, b_runs_tables.py d4329edeef49cd3e3d367fe56ad973df720954f4d06df962e915f627e84580e6 → b_runs_tables.md 9bb7ff25e217144cd91943d2fb01847ad6580de5ffa8e170404b4331f517bb4c.
- **산출: SP/codex_handoff/b/B_RUNS.md 0e30cb71723fa6640cb367ee2d38f9d8d4dd281b6022e2fa9784a96de5324ad2** (+ .sha256). 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/b/B_RUNS.md (+ .sha256, sha256sum -c OK). 금지 낱말 8개 0, 봉인 시드 0.
- 그대로: COMPARE_RULE_B f902f7f0…, PINS_B 5e8ffbc5…(sha256sum -c 54줄 OK), PRE_B_CONCURRENT 3d21dddd…. 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·기존 런 폴더·Y: 쓰기 0, sealed/·봉인 시드 0, 금지 시험 0. 디스크 C 29.4 GB, D 224.0 GB.
- 열린 것: (1) X6 — rm_exec 못 냄, 분석 단계를 이대로 나아갈지 사용자 결정. (2) s31·s41 "†접두 다름"(0.1 s 1행) 의 읽는 법. 짝 차 숫자는 아직 안 냄.

## 2026-10-27 00:58 KST — B 분석 단계 시작 (COMPARE_RULE_B §7.5 남은 도구)
- 사용자 말(이 세션): "너 꺼졌었는데 다시 한 번 확인해볼래??", "지금 돌아가는 나머지 세 비씸은 codex에서 따로 시킨 업무" → 남의 VISSIM 은 건드리지 않음. [실행 00:46] 지금 PC VISSIM 0, 우리 프로세스 0, 디스크 C 29.4 GB·D 224.0 GB.
- [실행] COMPARE_RULE_B f902f7f0… · PINS_B 5e8ffbc5… · PRE_B_CONCURRENT 3d21dddd… 그대로, `sha256sum -c b/PINS_B.sha256` 54줄 OK, OK 아닌 줄 0.
- X6 읽는 법 [추론, 규칙은 바꾸지 않음]: §5 X6 글은 "그 도구를 고치지 않고, **그 칸을** '못 냄' 으로 두고 멈추고 보고". 전체 멈춤은 X3 처럼 "B 숫자를 내지 않고 멈춤" 으로 따로 적혀 있고, §0 도 "(그 칸은 '못 냄')" 이라 칸 단위로 읽음. 그래서 미터 실행 대조(§4-4) 칸만 '못 냄(B 런 폴더에 LDP 없음)' 으로 두고, LDP 와 무관한 나머지 선언 칸은 고정 도구 그대로 냄. 이 읽는 법은 B_REPORT 와 반환에 밝히고, 사용자가 다르게 정하면 보고서를 쓰지 않은 것으로 돌림.
- 새 실행기(읽기만, 고정 도구 안 고침): work/b/b_analyze.ps1 2ae300183116a851835b6bfc60161f37fb2a31d674feb7163f8a73e5fc85def7 (사슬 A: vhr_firstseen_b 9칸 → vhr_v3c3_all_b / B: omega701_recount_b scan → metrics → omega/top66.py(작업 폴더 omega_b) / C31·C41·C43: scan_fzp_b nc → joint → metrics_b. 단계마다 PINS_B sha 대조, 실패하면 그 사슬만 멈추고 기록), 발사 work/b/b_analyze_launch_wmi.ps1 b28bc3e796212aa4a82cf7bd75e7c3a15ed1403f88ee9f71e14311c0bbbd8d62 (WMI, BELOW_NORMAL 16384, b_ana* 가 돌면 거부). 기록 work/b/ana_full.state.txt.
- vhr_scan_b 9칸은 이미 고정 도구로 돈 출력(work/vhr_b/scan_out, 상태 파일에 sha 대조 기록)을 그대로 씀, 다시 돌리지 않음.

## 2026-10-27 01:10 KST — B 분석: 실행기 v1 가 C31 중간에 조용히 끝남 · v2 로 C 사슬만 다시
- 고침(앞 항목): "00:58 KST — B 분석 단계 시작" 항목의 머리 시각은 잘못 적음. 실제로는 00:50 에 쓰고 00:50:59 에 발사(WMI RV 0, PID 34608, BELOW_NORMAL; 영수증 work/b/launch_receipts.log).
- [실행 work/b/ana_full.state.txt] 사슬 A: vhr_firstseen_b 9칸 exit 0(71.6 s) → vhr_v3c3_all_b exit 0(1.1 s). 사슬 B: omega701_recount_b scan exit 0(161.4 s, 10 FZP) → metrics exit 0(12.1 s) → omega/top66.py exit 0(1.1 s). 사슬 C31: scan_fzp_b_s31 nc exit 0(33.3 s) → scan_fzp_b_s31 joint 은 00:56 에 출력(scan/joint.json, out 줄)을 다 쓰고 python 이 끝났으나 실행기가 'step end' 를 못 쓰고 사라짐(01:06 확인: 실행기·python 프로세스 없음, fzp.lock 없음). 오류 기록 없음.
- 까닭 [추론]: 내가 상태 파일을 tail -f(Monitor)와 5 s grep 으로 읽는 동안 Add-Content 가 거부되어 $ErrorActionPreference Stop 으로 끝났다고 봄. 시험하지 않음. 감시(tail·grep)는 멈춤.
- 처리: work/b/b_analyze.ps1 v2 eeffa0e772ca47efda2a4f1ebdde123e192d655e57c8b2230ff44e3bee69587b (Note 를 재시도·예외 없는 덧붙이기로, -Chains·-Tag 인자; 단계·도구·인자·환경은 그대로), 발사 work/b/b_analyze_launch_wmi.ps1 v2 0a6192cfc9d3fba5856eb464813237af4edeaa88e7400f82b1716de1a07a4edf (-Chains·-Tag 넘김). 사슬 C31·C41·C43 을 처음부터 다시 돌림(C31 nc 도 다시; 같은 입력이라 같은 출력이 될 것, 확인은 산출 비교로). 기록 work/b/ana_full2.state.txt. 사슬 A·B 출력은 그대로 씀.
- [실행 00:59] X3 의 V 쪽: vhr_b/v3c3_all.json 의 va-nc3 108칸이 원본 work/vhr/v3c3_all.json(bf26275e…, sha 다시 셈 같음)과 모두 같음.

## 2026-10-27 01:16 KST — B 분석 결과 · B_REPORT.md (COMPARE_RULE_B 칸 모두, 미터 실행 대조만 못 냄)
- 고침(앞 항목): "01:10 KST — 실행기 v1 …" 항목은 실제로 01:08 에 쓰고 01:08:01 에 v2 발사(WMI RV 0, PID 12800, BELOW_NORMAL).
- [실행 ana_full2.state.txt] 사슬 C31·C41·C43 모두 exit 0 (scan nc·joint 각 32–35 s, metrics 1.1 s), 01:11:26 끝. v1 이 쓴 C31 joint 스캔 사본(work/b/v1_c31_copy/, json 8d52d1df…·npz b93ef0c5…)과 v2 출력은 scan_sec 칸 말고 같음.
- [실행] 점검: X1 V 대 O 48값 차 최대 0.000472, X2 ≈ 1e-11, X3 통과(V va-nc3 108칸 다른 칸 0, O VA-NC3|*|*|U6VA 240값 차 0; 원본 bf26275e·fa6d24cf), X4 차 0, X5 입력 1098 첫 관측 수 세 런 같음, 1099 도착 B − NC3 −1/−4/0, 전체(첫 관측+남은 수) 0/−2/0.
- [실행] 결과(B − NC3, 우리 꼴 [0, 9000], v3c3-s31†/s41†/s43, veh·h): Ω701 −157.0/−523.4/−222.2, Ω635 −159.6/−474.4/−257.4, ④a −128.3/−548.6/−219.1, ④b(첫 관측) +303.5/+318.0/−231.5, ④ +175.1/−230.6/−450.6, Ω 밖 (a) Ω701 +332.1/+292.9/−228.4, ① −37.3/−178.1/−88.9, ② +28.2/−245.2/−34.7, ④b 1099 +490.0/+468.4/+84.0, 도시 −161.0/−131.0/−202.0, 1098 −25.5/−19.3/−113.5. codex 꼴 [0, 8100]: Ω701 −126.9/−464.0/−195.4, ④ +129.1/−258.0/−425.5, Ω 밖 (a) +256.1/+206.1/−230.1. B − V-A 우리 꼴: Ω701 +83.6/−101.8/+87.3, ④ +549.1/+275.6/−94.3, Ω 밖 (a) +465.5/+377.3/−181.6. 링크 66 B − NC3 +28.0/−9.8/+61.1. 도시도로 codex 꼴 B − NC3 codex 규칙 −214.3/−338.9/−110.1, 우리 규칙 −263.5/−318.8/−204.0. ④b 수준 B native 4079.2/3582.7/2856.5.
- 못 냄: LDP 신호 실행 대조(데이터 전 선언, NC3 에 LDP 없음; B 에도 없음), 미터 실행 대조(X6, B 에 LDP 없음; 도구 안 고침, 대체 계산 안 함). 램프 도착 RM_C 별 칸 = 출력에 없음(결정 JSON 9개 grep, 합 + 옛 그룹키 4칸뿐).
- 64cf-s29 별도 묶음(A1_RESULT.md:253-276 옮김, 짝 안 지음): joint − NC Ω701 −494.7, ④ −670.3, Ω 밖 (a) −175.6; A1 − LNC −505.7/−699.2/−193.5.
- 새 도구(읽기만): work/b/b_report_tables.py 13ee5a5ab95baa221f204306095f5426b186a37e6745a1b7680565b9d8597f10 → b_report_tables.json 1815162dca93e97ebf78d7dbfdc7ba33b1af777b0d021988b8e4f9b77591d027 · b_report_tables.md ce0de5b772cb909b703a3d03dea372444a7485375f958207bb5d0228dc6e086a; work/b/b_report_lines.py dcecf3b3b5bfcb1bfb5236c991bdbae2034136e3932772dc64c9925e85dca0da → b_report_lines.md d5e5822c24e9b27ce202eeccfa9af562acd7b0e95ee595c1a35cffd1f917aced; 원문 work/b/b_report_src.md 44dcc5776848d234e93e58b2f1fac22f2ea51b62d3a81dd4abc8c0622ae17d79; 조립 work/b/b_report_build.py ade94080602695c7740c7a5a8d240846fcc79a10dead1ea4650fad50de02e4b8 (금지 낱말 8개 0, 봉인 시드 0, 조립 때 PINS_B 54줄 OK).
- 도구 출력: vhr_b/v3c3_all.json f982fbff…, omega_b/omega701_v3c3.json 823f9dcc…, omega_b/omega701_per_link.csv c4f7a3a3…, omega_b/top66.json a4e47a48…, rawcheck_b/s31·s41·s43/metrics_out.json 74a06771…·b9e41f92…·9d3e4364….
- **산출: SP/codex_handoff/b/B_REPORT.md 115e8da15df632d67b34c28f16bfd76bced0eb5ffe0ff6901ff6e8d9fc1934d1** (+ .sha256). 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/b/B_REPORT.md (+ .sha256, sha256sum -c OK).
- X6 읽는 법(칸 단위)은 [추론]이며 B_REPORT §1-11·§10-1 에 밝힘. 사용자가 전체 멈춤으로 읽으면 B_REPORT 를 거둠.
- VISSIM 띄움 0(PC VISSIM 0), kill 0, 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·기존 런 폴더·Y: 쓰기 0(D: 쓰기는 reports/k8/codex_handoff/b 사본뿐), sealed/·봉인 시드 0, codex 64cf-s59/s61/s67 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B·PRE_B_CONCURRENT 바꾸지 않음. 디스크 C 29.3 GB, D 224.0 GB.

## 2026-10-27 01:31 KST — B 종합 B_RESULTS.md (Synthesize)
- 읽음(바꾸지 않음): b/GATE1.md aae6b0ca…, b/PRE_B_CONCURRENT.md 3d21dddd…, b/B_RUNS.md 0e30cb71…, b/B_REPORT.md 115e8da1…, j1/analysis/J1_REPORT_CORRECTION.md 6c30e391…, NOTES 59e41ff5…, A1_B0_RESULTS a9f491ee…, TAKEOVER_PLAN b75ad041…, a1/A1_RESULT 0ef733fb…, RAW_CHECK·R_MECH·COMPARE_RULE_B·rmcause/METER_CAUSE·amend1/S1_OWNER 일부.
- [실행] COMPARE_RULE_B f902f7f0… · PINS_B 5e8ffbc5…(sha256sum -c 54줄 OK) · PRE_B_CONCURRENT 3d21dddd… 그대로.
- 새 읽기 도구: work/b/b_results_tables.py 065878dd96ecc9730f1a019d0272296c89b8167f78f11c8943914644c53bc8f8 (V f982fbff·O 823f9dcc·P c4f7a3a3 를 읽어 표만 냄, python -B, PYTHONHASHSEED=0, 수 초) → work/b/b_results_tables.md 6db26aeb33c022c496efce48cdac618499c152c0ad35e9635a62dffec74d55a3, work/b/b_results_tables.json dfd0fbf969f959cafc9e5ed25b50db5ea48bb4f82cb448971c8e3d9e7cb41037. B − NC3·B − V-A 156칸이 B_REPORT 표와 0.05 넘게 다른 칸 0. V-A − NC3 칸 더함(V va-nc3·O VA-NC3·P). 선언 밖 참고 칸(FW_W 본선 O FW_W_main, 링크 124·10480·70·10639·26·120 수준값)은 '데이터 뒤 참고' 로 표시.
- 핵심 [실행]: B − NC3 우리 꼴 Ω701 −157.0/−523.4/−222.2, ④ +175.1/−230.6/−450.6, Ω 밖 (a) +332.1/+292.9/−228.4; V-A − NC3 Ω701 −240.6/−421.7/−309.5, ④ −373.9/−506.2/−356.4, Ω 밖 (a) −133.3/−84.5/−46.9; B − V-A Ω701 +83.6/−101.8/+87.3, ④ +549.1/+275.6/−94.3, Ω 밖 (a) +465.5/+377.3/−181.6. ④b 1099 B − NC3 +490.0/+468.4/+84.0. 미터 명령 6/8 움직임(V-A·J1 은 0/8), 실행 대조 못 냄(LDP 없음), VSL 110.
- 결정 거리 8개(권장): 1 X6 칸 단위 (a) / 2 † 그대로 (a) / 3 .lsa 미터 실행 대조 새 선언 (a) / 4 입력 1099 대기 오프라인 분해 (a) / 5 통째 교체 아님, C 묶음별 이식·첫 묶음은 3·4 뒤 (a) / 6 K9-3 보류 유지 (a) / 7 VSL 오프라인 먼저(A1 VSL 100 결정 JSON → plant 대 VISSIM 대조) (a) / 8 같은 시드 반복 안 함 (a).
- **산출: SP/codex_handoff/B_RESULTS.md efb6cff7596fae897c9b20b11c58df3870b4ad3d96c17903f6c4c228489a789e** (+ .sha256). 금지 낱말 8개 0, 봉인 시드 이름 0. D: 사본 안 만듦.
- [실행 01:22] PC VISSIM 2(PID 20452·55624, 부모 1204, 01:19–01:20 시작 — 우리 것 아님, 건드리지 않음), 우리 프로세스 0. 디스크 C 29 GB, D 224 GB. VISSIM 띄움 0, kill 0, 커밋·푸시 0, GWT8·frozen·인계 사본·기존 런 폴더·Y: 쓰기 0, sealed/ 0, 금지 시험 0.

## 2026-10-27 01:35 KST — VERIFY_B 시작 (B_RESULTS·B_REPORT 적대 재검)
- 사용자 말(이 세션): "너 꺼졌었는데 다시 한 번 확인해볼래??", "지금 돌아가는 나머지 세 비씸은 codex에서 따로 시킨 업무" → 남의 VISSIM(지금 2개, PID 20452·55624, 부모 1204)은 건드리지 않음. VISSIM 띄움 0.
- 새 도구(작성자 도구 재사용 없음, 읽기만): work/verify_b/vb_scan.py d9d3e268a5e59a7927a3f511e9827080bc5d536c2ec92b6dbaff00bbd72225fd (FZP 9개: B·NC3·V-A × v3c3-s31·s41·s43 → 링크별 체류 두 꼴 + 첫 관측 S(W)), 발사 work/verify_b/vb_launch_wmi.ps1 52df786945f1be5c3f96bfbf52d70e8259537bdf8ee55b198e6c3a1a3bcdaa61 (WMI, BELOW_NORMAL 16384, python -B, PYTHONHASHSEED=0, 스레드 1, 한 번에 하나).

## 2026-10-27 01:55 KST — VERIFY_B 결과 (B_RESULTS·B_REPORT 적대 재검)
- [실행] 새 도구(작성자 도구·출력 안 씀, 읽기만, 무거운 것은 WMI·BELOW_NORMAL·한 번에 하나): work/verify_b/vb_scan.py d9d3e268… (FZP 9개, 01:35 PID 55912), vb_compare.py c6811880…, vb_runfiles.py 57314075…, vb_decjson.py 9a9f02b9… (결정 JSON 162개, 01:40 PID 33872), vb_frz.py 8bb5be3a… (1차 01:44 PID 55636 은 260자 넘는 경로로 FileNotFoundError, 긴 경로 접두만 더해 01:45 PID 44816 다시), vb_frz_extra.py 9450bde0…, vb_link26.py 8da0230e… (선언 밖, 01:49 PID 27164). 발사 vb_launch_wmi.ps1 52df7869…, vb_launch2.ps1 09ff5016…. 출력 work/verify_b/out/ (compare.json 7fd5dd97…, runfiles.json 66fe4272…, decjson.json 2452fa2d…, frz.json d626fbbf…, frz_runner.diff 7742999a…, link26.json ae32f3f6…).
- [실행] 숫자: 세 짝 × 세 시드 × 두 꼴 234칸 최대 차 0.0503(반올림 폭), 수준·링크 99칸 0.05 안. X5 첫 관측 수·.err 남은 수·5.1–900.1 s 행 해시(B=NC3=V-A)·0.1 s 행 1대 같음. 런 기록(61결정 exit 0, 유지 0)·벽시계·미터 녹색/rate 분포·VSL 110·상태·램프 도착 키 같음. FRZ_B1 대 FRZ_B0: 표 기준 러너 한 파일·선언한 세 곳만, 디스크는 제외 폴더 캐시만 더 다름.
- [실행] 반박 1: B_RESULTS 쉬운 답 10·결정 3(a) "`.lsa` 로 미터 녹색 세기" — B·V-A 여섯 런 .lsa 에 미터 SC 9101–9108 줄은 1.0 s off 8줄뿐. 대신 decisions/signal_readback.csv: 선언 밖으로 세어 B 3시드 × 미터 8 × 주기 810 모두 읽은 녹색 = 명령, V-A 488행 모두 GREEN.
- 근거 부족 2: (가) §2.1-3 볼 길 (i) — FW_W 본선 줄은 링크 26 포함, 링크 120 은 B − NC3 −10.2/−10.4/−1.5; 링크 26 늘어남은 차로 1 위주·0–3,750 m·2,700–4,500 s(선언 밖). (나) FW_E 쪽 B − V-A 를 미터 묶음 후보로 읽을 때 V-A FW_E VSL 100(9/10/14결정) 단서 빠짐.
- **산출: SP/codex_handoff/VERIFY_B.md f2851f8b53f026ada64f52e51d877b8c0ddc7ac3bbaf7f19cd27097c21462104** (+ .sha256). pass = false(반박 1이 권장에 남음). 고칠 글은 VERIFY_B §3. B_RESULTS·B_REPORT 는 바꾸지 않음.
- 그대로: COMPARE_RULE_B f902f7f0…, PINS_B 5e8ffbc5…(54줄 OK), PRE_B_CONCURRENT 3d21dddd…. VISSIM 띄움 0, kill 0; 지금 PC VISSIM 1 (55624, 남의 것, 건드리지 않음), 우리 프로세스 0. 커밋·푸시 0, GWT8·frozen·인계 사본·기존 런 폴더·FRZ 트리·Y: 쓰기 0, sealed/ 0, 금지 시험 0. 디스크 C 28.1 GB, D 224 GB.

## 2026-10-27 02:05 KST — B 마무리 (VERIFY_B 고침 반영, r2) · D: 사본
- 사용자 말(이 세션): "너 꺼졌었는데 다시 한 번 확인해볼래??", "지금 돌아가는 나머지 세 비씸은 codex에서 따로 시킨 업무" → 남의 VISSIM·남의 python(codex TD3 런타임, 부모 cscript 22812)은 건드리지 않음. [실행 01:57] PC VISSIM 1(55624, 부모 1204, 남의 것), [실행 02:04] PC VISSIM 0(55624 스스로 끝남). 우리 프로세스 0. VISSIM 띄움 0, kill 0.
- [실행] 고치기 전 대조: B_RESULTS efb6cff7…·B_REPORT 115e8da1…·B_RUNS 0e30cb71…·VERIFY_B f2851f8b… sha256sum -c OK. COMPARE_RULE_B f902f7f0…, PINS_B 5e8ffbc5…(54줄 OK), PRE_B_CONCURRENT 3d21dddd… 그대로.
- [실행] 반박 D5 재확인(읽기만): B v3c3-s31·V-A v3c3-s31 `.lsa` 의 SC 9101–9108 줄 = 1.0 s `off` 8줄씩; B v3c3-s31 `signal_readback.csv` 머리 확인. [읽음] VERIFY_B 출력 runfiles.json(readback 810주기 × 8 × 3시드 어긋남 0)·link26.json(차로·위치·시간 칸)을 다시 빼 VERIFY_B 값과 같음 [계산].
- r1 보관: B_RESULTS_r1.md efb6cff7…, b/B_REPORT_r1.md 115e8da1…, b/B_RUNS_r1.md 0e30cb71… (+ .sha256).
- 고침(VERIFY_B §3-1–§3-8 모두, 숫자 칸 바꿈 0, 권장 8개 모두 (a) 그대로): §0-10·결정 3 의 `.lsa` 방법 지우고 readback 대조로(반박), §2.1-3 볼 길 (i) 을 링크 26 끝 엮임 구간 차로 1 대기로·링크 120 은 B 가 낮음·"FW_W 본선" 은 링크 26 포함(근거 부족 D4), §2.1-2·§2.1-3·결정 5·§0-5·§0-9 에 VSL 단서(D3), §0-5 같은 부호 칸 보완(D12), §0-7·§1.5·§1.7·§2.1-4 "규칙 도구로는" + readback(R10), 크기 참고·결정 8 배수 단서(D11), §2.2-2·결정 7 "직접 닿지 않음" 은 시험 안 한 판단(D10), 결정 4 볼 칸. B_REPORT §5.4·§8-3·§10-1 readback 한 줄·`.lsa` 예시 지움, B_RUNS §9 `.lsa` 예시 지움. 변경 기록: B_RESULTS §5, B_REPORT §11, B_RUNS §12.
- 점검 [실행]: 금지 낱말 8개 0, 봉인 시드 이름 0(세 파일). 새 도구·새 파이썬 0.
- **산출: SP/codex_handoff/B_RESULTS.md 152a2f6fe0fd6c5cfd1462ba7d7e444cd13a6bd0ba2554874d07a1390a8209f9**, b/B_REPORT.md 3d1065e4a213624ce4c1ca0bea1034edcb3e215ecdc77de780230c68343d1aa0, b/B_RUNS.md 405272f5dabe879ef4cf0bdbc7184c4641f264e96fb2fef5ec0a46e9969b6723 (각 .sha256).
- 사본 D:/VISSIM_runs/20261001_v3c3/reports/k8/codex_handoff/: B_RESULTS(.md·_r1)·VERIFY_B·b/B_REPORT(.md·_r1)·b/B_RUNS(.md·_r1)(각 .sha256) + b/COMPARE_RULE_B·PINS_B·PRE_B_CONCURRENT(읽기 사본) + SHA256SUMS_B.txt 45ec27646af29a045911cee47b08749928b0f92cbead9cc28e5b630b0911d8af (sha256sum -c 10줄 OK). LOG.md 사본은 이 항목 뒤.
- 커밋·푸시 0, GWT8·D:/VISSIM-merge/frozen·인계 사본·기존 런 폴더·FRZ 트리·Y: 쓰기 0(D: 쓰기는 reports/k8/codex_handoff 사본뿐), sealed/·봉인 시드 0, codex 64cf-s59/s61/s67 숫자 0, 금지 시험 0. COMPARE_RULE_B·PINS_B·PRE_B_CONCURRENT 바꾸지 않음. 디스크 C 28 GB, D 225 GB.
- 열린 것: (1) X6 칸 단위 읽기(결정 1), (2) † 읽기(결정 2), (3) readback 대조를 새 선언으로 할지(결정 3), (4) 입력 1099 대기 분해(결정 4), (5) 인계 길 C(결정 5), K9-3(6), VSL 오프라인(7), 반복 런(8) — 모두 사용자 결정.
