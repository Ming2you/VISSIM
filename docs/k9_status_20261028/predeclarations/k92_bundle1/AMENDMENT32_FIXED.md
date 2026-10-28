# 보충 32 고정점 (ReviewDeclare A32, 2026-10-22 10:5x KST)

이 파일이 고정점입니다. 아래 sha256과 다른 보충 32로는 V-B의 어떤 단계(V0 사전 점검, V1 트리, V2 팔, V3 훅 영향 0 시험 ZI, 사슬 계산, 판정, 재계산, 보고)도 하지 않습니다. V-B 구동기의 V0 C2는 이 파일 안에 보충 32 고정판 sha가 64자 낱말로 있는지 봅니다(보충 32 §4.2). 그래서 이 파일에는 고정판 sha를 64자로 적고, Declare 판 sha는 앞 16자만 적습니다(보충 29 §14.1 V4와 같은 까닭: 되돌린 파일이 통과하지 않게). 이 시각 뒤에는 보충 32를 고치지 않습니다. 바꿔야 하면 새 보충(33 이후)에 까닭을 적습니다.

| 문서 | sha256 | 크기 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_32.md` (검토 판 = 고정판) | `7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7` | 110,229 B, 605줄, LF, CR 0 |
| [보충 32 §10, §4.1] 기대 고정 목록 `KB/a32decl/a32_pins.expected.sha256` (V-B가 쓰는 `KB/a32_pins.sha256`은 이 바이트와 `cmp` 같아야 함; 검토가 바꾸지 않음) | `9e4dc5925e36fcc092f1b4ace4c3e86600d8f96422f3720653fe7d72d4514fcb` | 51줄, 10,356 B, LF, CR 0 |
| [§3, 고정 목록 1–3줄] 측정 훅 `KB/a32decl/vbhook/sitecustomize.py` / 고르기 `KB/a32decl/vb_select.py` / 도움 함수 `KB/a32decl/vb_lib32.py` (검토가 바꾸지 않음) | `4d7e0375116c3f805aa223651da0dc1c0c04b7d3315062e98e21137ba60aa321` / `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc` / `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f` | 11,471 B / 9,899 B / 8,808 B |
| [§2.2, 고정 목록 5줄] 닫힌 잎 목록 `KB/a32decl/vb_closed_leaves.json` (검토가 바꾸지 않음) | `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426` | 10,129 B |

- 고정 시각: **2026-10-22T10:53+09:00** [실행 `date` 10:53:08]. 고정판 파일은 그 직전에 마지막으로 바뀌었고 그 뒤 바뀌지 않았습니다(위 sha). 같은 폴더의 `SP/K8_PREDECLARATION_AMENDMENT_32.md.sha256`도 위 값과 같습니다 [실행 `sha256sum -c` OK].
- 줄임말: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, KB = `SP/k92/bundle1`, KI = `KB/impl`(바꾸지 않음), KV = `KB/k92_vb`, AD32 = `KB/a32decl`(새 도구·확인 출력), RV32 = `KB/a32review`(이 검토의 도구·출력·사본), TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`, VBT = `TK/vb_e27ceac8`(아직 없음), OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`, VBR = `OK2/vb`(아직 없음), RR = `D:/VISSIM_runs/20261004_sdmpc31_k8`(읽기만), GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, KC = K9-2-5 비교기 `k92_compare.py`, REC = K9-2-0 기록기 `k92_record.py`, ZI = 훅 영향 0 시험.
- 검토 전 판(`_r1`): `SP/K8_PREDECLARATION_AMENDMENT_32_r1.md` = `176ded8997b53206…`(89,398 B, 532줄; 64자는 그 `.sha256` 파일과 보충 32 머리에). Declare 단계가 10:12에 쓴 판과 바이트가 같습니다 [실행 `cmp`, `RV32/r1/K8_PREDECLARATION_AMENDMENT_32_declare.md`와도 같음].
- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `402eaf59aa738bef1dcb27f41d51eba873a8cb6abdbfde7707dfc6b146cfbd3b`(204줄, D-K9-62~64 :200-202), 보충 24–31과 각 `.sha256`·고정점 24–31 = 보충 32 §0. `KV/VB_PRECHECK_STOP.md` r2 `b96637d9…`, `KV/verify/out/vvb_a_01.json` `618b9592…`. 기대 고정 목록 51/51 OK. `KB/a31_pins.sha256` 133줄 가운데 다른 것 = `GATES_K92B1.md`(`449b361e…`) 하나. `KB/LOG.md` 검토 시작 전 249,863 B = `28a6622c…`.
- 데이터: **V-B 데이터 0개.** `OK2/vb*`·`TK/vb*`·`KV/vb_chain.py`·`KV/vb_recalc.py`·`KV/selftest`·`KB/a32_pins.sha256`·`KV/vb_pins.sha256`·`*VB_REPORT*` 없음. VerifyVB 끝(04:42) 뒤 바뀐 파일: OK2(봉인 뿌리 `-prune`)는 Declare 스냅숏·로그와 이 검토 로그(`logs/rv32_nested.txt`)뿐, TK 0, KB는 LOG·`impl/wmi_launch_lines.txt`·AD32·RV32뿐 [실행 `find -newermt`]. GWT8 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` 커밋 6개), K8 브랜치 `b9734abe`, `status --porcelain` 0줄, 원격 k92 참조 0, `git worktree list`에 vb 0, 푸시 0 [실행].
- 이 검토에서 한 일: VISSIM·COM·러너·동결·결정 재생·plant 잡·어댑터 실행 0. VBT·VBR 만들기 0, ZI·사슬 계산 0. 무거운 일 하나(`rv32_nested`, RR 기록 결정 파일 읽기)는 실행 전 sha를 LOG에 적고 `KI/launch.ps1`로 WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번. 쓴 곳: RV32, SP의 보충 32·`_r1`·두 `.sha256`, 이 파일, `KB/LOG.md` 덧붙임, `OK2/logs/rv32_nested.txt`(WMI 표준 출력), `KI/wmi_launch_lines.txt`(launch.ps1이 한 줄 덧붙임). RR·동결본·GWT8·저장소 `.git`·K8 브랜치·OUTK·봉인 뿌리·AD32·KI 코드 쓰기 0. 끈 프로세스: 내가 띄운 파일 시각 `find` 하나(PID 612, OK2 이름 훑기가 오래 걸려서; 대상 자리는 직접 확인). 끝에 python·VISSIM 0.
- 블라인드: 봉인 시드(37/59/61/67)·codex 64cf 숫자 0, 봉인 뿌리 파일 열람 0(`find`는 `-prune`), v3c3-s47 자료 0. 목적값·예측값 출력 0.
- 디스크: C: 40 GB, D: 388 GB 여유 [실행].

태그: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.

---

## 1. 찾은 구멍과 고친 곳 (자세한 표는 보충 32 §14.1)

| # | 구멍 | 고침 |
|---|---|---|
| R1 | 판정 4결정이 구조로 실패하지 않는다는 근거가 한 줄 [추론]뿐이었고, VB-41w T=1(무제어)의 G-K0 D-a 선례가 J1 기록 대 재생이 아니라는 점이 빠짐 | 출력·준비 자리(자기 출력 이름 잎 0, 결정 폴더 문자열 = 직전 13 + V 2), N 뿌리, 원천·입력 sha 조건, CR 짝 근거와 간접 선례(K8 G-H2a 61/61, GB-7′ T=1)를 적음; PASS가 아니면 S-K55 STOP(P13) |
| R2 | 닫힌 목록이 바로 앞 결정 파일만 본 결과라 더 앞 사슬 파일을 가리키는 잎이 빠질 수 있었음 | RR 기록에서 따로 찾아 0개; 기계 파일 = `vvb_a` 10/10(경로·HARD·기록 개수); 완전·정확 |
| R3 | ZI (z5)가 "같은 경로면 토큰(F1)도 같다"에 기대는 점과 그 위험이 빠짐 | 근거(몫 가르기 A0/A0h)·선례 없음·STOP 쪽임을 적음(P12); 둘째 실행이 보는 첫 실행 산물(`derived_<T>.json` 하나, 고정 목록 같음)·폴더 훑기 없음 |
| R4 | 훅이 원천 고정·D5·AD 값·시간 예산·GC 계수를 건드릴 길이 없다는 근거가 짧았음 | 코드 자리와 다섯 근거, PID 겹침 위험(60번 시험 재사용 0, 겹치면 STOP, P14) |
| R5 | 보고 전용 결정의 "출력은 있는데 INCOMPLETE" 처리 모호 | 출력 없음만 VB-I4 STOP, 그 밖은 보고만(굵게) — D-K9-62 그대로 |
| R6 | 표준 출력 파일 이름 모호 | `action_<T6>.stdout.txt`·`.stderr.txt`(RR와 같음), 자기 시험 비교 대상 아님 |

- 바꾸지 않은 것: 판정 정의·문턱·표본·판정 4결정·보고 10결정·닫힌 잎 목록·VB-I1–I7·ZI 규칙(z1)–(z7)·STOP S-K51–S-K55, 새 도구·확인 출력·기대 고정 목록(`9e4dc592…`, 51줄). 고친 것은 보충 32의 글뿐입니다.

## 2. 다시 확인했고 문제없는 것 (자세히는 보충 32 §14.2)

1. 고정 목록 51/51 OK, 51개 sha가 글에 그대로 [실행].
2. 결정 기록 세 줄 인용이 바이트 그대로 [실행].
3. VB-I2의 VB-41w B1 T=150 예외(1.0)와 OFF 0.0, 그 밖 B1 0.0이 코드상 일어나는 길(SHO:130-141, :209-214) — VB-I2–I6 충족 가능 [읽음].
4. 영수증 읽기·쓰기 규칙, 어댑터가 쓰는 짝 파일 [읽음].
5. ZI 두 상태(v3c3-s43 T=750·1,050)가 V-B 55결정 밖, 필요한 RR 파일 있음 [읽음·실행].
6. C12(`phase_price.mode` 없음), 옛 뿌리 = RR `run_provenance`, 세 튜닝 `ignore_wall_time_limits` = true [실행].
7. 다른 `sitecustomize` 없음 [실행].
8. V-B 데이터 0(파일 시각) [실행].

## 3. 메인 세션이 할 일·사용자에게 알릴 것 (막힘 아님)

1. 사용자 보고에 적을 것: (가) P12 — ZI의 "벽시계 잎만"은 같은 경로면 토큰도 같다는 가정에 기댐, 선례 없음, 틀리면 S-K51 STOP; (나) P13 — 판정 결정 VB-41w T=1은 J1 기록 대 재생의 직접 선례가 없음, 틀리면 S-K55 STOP; (다) P14 — 훅 후보 폴더 PID 겹침은 STOP 쪽, 시험에서 재사용 0; (라) P15 — 검토가 읽은 기록 자료(경로·개수·sha, 벽시계 두 값 화면에 한 번), 내 `find` 하나를 끈 일, LOG 시각 한 줄을 잘못 적고 바로 아래 줄로 고친 일.
2. V-B 시작: 보충 32 §4.1 고정(`KB/a32_pins.sha256` = 기대 파일 바이트, 51/51; 자기 시험 뒤 `KV/vb_pins.sha256`; LOG 한 항목) → §4.2 V0–V10. V0 C2는 이 파일 안의 고정판 64자 `7f25c21e…`(위 표)를 봅니다.
3. 남은 미해결: 없음.

## 4. 검토 도구와 출력 (RV32 = `KB/a32review`; 읽기만 하는 점검, 판정에 쓰지 않음)

| 파일 | sha256 |
|---|---|
| `rv32_nested.py` (RR 기록 사슬 14결정: 앞 사슬 파일 이름·sha를 담은 잎, 자기 출력 이름 잎, 결정 폴더 문자열; 경로·개수만) | `aa12297b7ddd215d35b927c707901a5ea8a69db1ff5bdeb5ca46538f518f5f26` |
| `out/rv32_nested.json` (그 출력; 보고 전용 10결정의 바로 앞 아닌 잎 0, 자기 출력 이름 잎 0) | `b6e146fba805d6226d56e4941cae696790141f52f5b5de2b94b866bdc084c1ba` |
| `r1/K8_PREDECLARATION_AMENDMENT_32_declare.md` (Declare 판 사본) | `176ded8997b53206…` |

- 공개: `rv32_nested.py`는 실제 자료에 돌리기 전에 sha를 LOG에 적었습니다. 문법 확인 `py_compile` 한 번이 RV32에 `__pycache__`를 만들어 지웠습니다. 인라인 대조(닫힌 목록 대 `vvb_a_01.json`, KC `norm_s`·`tree_root_ok`에 경로 글자)는 도구 파일 없이 했고 LOG에 적었습니다.
