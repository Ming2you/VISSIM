# 보충 33 고정점 (ReviewDeclare A33, 2026-10-22 15:23 KST)

이 파일이 고정점입니다. 아래 sha256과 다른 보충 33으로는 V-B의 어떤 단계(V0 사전 점검, V1 트리, V2 팔, V3 훅 영향 0 시험 ZI, 사슬 계산, 판정, 재계산, 보고)도 하지 않습니다. V-B 구동기 `KB/k92_vb2/vb_chain.py`의 V0 C2는 이 파일 안에 보충 33 고정판 sha와 기대 고정 목록 sha가 64자 낱말로 있는지 봅니다(보충 33 §6.2, §7.2). 그래서 이 파일에는 고정판 sha를 64자로 적고, Declare 판 sha는 앞 16자만 적습니다(보충 29 §14.1 V4·보충 32와 같은 까닭: 되돌린 파일이 통과하지 않게). 이 시각 뒤에는 보충 33을 고치지 않습니다. 바꿔야 하면 새 보충(34 이후)에 까닭을 적습니다.

| 문서 | sha256 | 크기 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_33.md` (검토 판 = 고정판) | `76ae084b2b12eb820238a8c2b980c6554c2a988ebeebca877d51fb9714f733ea` | 135,275 B, 1,236줄, LF, CR 0 |
| [보충 33 §7.1, §6.1-2] 기대 고정 목록 `KB/a33decl/a33_pins.expected.sha256` (V-B가 쓰는 `KB/a33_pins.sha256`은 이 바이트와 `cmp` 같아야 함; 검토가 바꾸지 않음) | `a1b02027c3238dcb3cb55bae42e163d4d1ce60b0f7c688e44517efcfe9e7ac74` | 63줄, 12,478 B, LF, CR 0 |
| [§2, 고정 목록 1줄] 새 측정 훅 `KB/a33decl/vbhook/sitecustomize.py` (검토가 바꾸지 않음) | `691fe8100e38d3222f3508f3f682b84b225535d1d3f7cca57f08a671708e365c` | 12,368 B, 262줄 |
| [§3, 고정 목록 5–6줄] 새 구동기 `KB/k92_vb2/vb_chain.py` / 새 재계산기 `KB/k92_vb2/vb_recalc.py` (검토가 바꾸지 않음) | `87b89ce48b6552b4967cc5416d2e56d5f9f6d20d887d9997385df4f1be521322` / `6531a5e8eab37201781d4f81c80c7090b1546c2511c128c5db58026f28625d8b` | 108,273 B / 42,514 B |
| [§2.6, 고정 목록 2–4줄] 고르기 `KB/a32decl/vb_select.py` / 도움 함수 `KB/a32decl/vb_lib32.py` / 닫힌 잎 목록 `KB/a32decl/vb_closed_leaves.json` (보충 32 그대로) | `33adfd5033c277a3ad640f745a69efb2a929b27c1ff2a88d794dfa69b489e9cc` / `504999a196a9e08582f303d4ad38d4cc661fcfc765df62d11bc4cc7c05ddc75f` / `b800be45ae3e4e5030ed31ecd221e6288d52c2a287bdeaa5efee243e3cc2f426` | 9,899 B / 8,808 B / 10,129 B |
| [§5 (라), §6.5] 검토 때 보관 목록: 옛 VBT `TK/vb_e27ceac8` + `TK/vb_e27ceac8.build.json` (구동기 `archive_listing()` 꼴) | `d51f4deefc53b69cdadd9472a6ea2ca9197f694760f26c2380e1a101a1089680` | 10,660행(파일 10,659 + 빌드 기록) |
| [§5 (라), §6.5] 검토 때 보관 목록: 옛 VBR `OK2/vb` (같은 꼴, 덧붙인 행 없음) | `392d10278514a2206fe9a6b5d22190708931ffabdecaf911037668f5f4ecd583` | 1,129파일, 2,665,452,354 B, 마지막 수정 14:07:20 |

- 고정 시각: **2026-10-22T15:23+09:00** [실행 `date` 15:23:57]. 고정판 파일은 15:22에 마지막으로 바뀌었고 그 뒤 바뀌지 않았습니다(위 sha). 같은 폴더의 `SP/K8_PREDECLARATION_AMENDMENT_33.md.sha256`도 위 값과 같습니다 [실행 `sha256sum -c` OK].
- 줄임말: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, KB = `SP/k92/bundle1`, KI = `KB/impl`(바꾸지 않음), KV = `KB/k92_vb`(보관), KV2 = `KB/k92_vb2`(새 구동기·재계산기·자기 시험), AD32 = `KB/a32decl`, AD33 = `KB/a33decl`(새 훅·확인 도구·확인 출력·차이·기대 고정 목록), RV33 = `KB/a33review`(이 검토의 도구·출력·사본), TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`, VBT = `TK/vb2_e27ceac8`(아직 없음), 옛 VBT = `TK/vb_e27ceac8`(보관), OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`, VBR = `OK2/vb2`(아직 없음), 옛 VBR = `OK2/vb`(보관), RR = `D:/VISSIM_runs/20261004_sdmpc31_k8`(읽기만), GWT8 = `D:/VISSIM-merge/sim3-n31-k8`.
- 검토 전 판(`_r1`): `SP/K8_PREDECLARATION_AMENDMENT_33_r1.md` = `b0db6bf5d49e5b98…`(109,408 B, 1,158줄; 64자는 그 `.sha256` 파일과 보충 33 머리에). Declare 단계가 14:48에 쓴 판과 바이트가 같습니다 [실행 `cmp`, `RV33/r1/K8_PREDECLARATION_AMENDMENT_33_declare.md`와도 같음].
- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `187242343570f1fe4e22d644509139e87ff59f76c70458b58160c1cde5387109`(214줄, LF로 끝남, D-K9-65·66 :206-214) = 작업 지시 값. 보충 32 고정판 `7f25c21e72fc2599022c72adb1976257413a8486f4898ffcec61f3c6b01423e7` = `.sha256`, 고정점 32 `b59088ab44683f5990f2a44038c688aec59a21fcb5207e72b0bc7ee5782ddef4`. V-B STOP 판 r1 세 곳(`KV/K92_VB_REPORT.md`·`KB/VB_REPORT.md`·`OK2/vb/K92_VB_REPORT.md`)과 보관 사본 둘 = `d7bf44f3e309aa4ae8e5084b0db238f9baeb2870b6d75b4bea7b6d854427ea00`. 기대 고정 목록 63/63 OK. `KB/LOG.md` 검토 시작 전 270,869 B = `9a52b396efabcfa4601fbb46f415524c0e93d34e9559d72264dffe62893efb4e`.
- 데이터: **새 V-B 데이터 0개.** `OK2/vb2`·`TK/vb2_e27ceac8`·`KB/a33_pins.sha256`·`OK2/snap/s43–s46_vb2_*`·`OK2/logs/vb2_*` 없음 [실행]. 옛 VBR 안 14:07:20보다 늦은 파일 0, 옛 VBT 안 11:28:38보다 늦은 파일 0 [실행 `find -newermt`]. GWT8 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` 커밋 6개), K8 브랜치 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, `status --porcelain` 0줄, 원격 k92 참조 0, 이름에 vb 든 worktree 0, 푸시 0 [실행].
- 이 검토에서 한 일: VISSIM·COM·러너·동결·결정 재생·plant 잡·어댑터 실행 0. VBT·VBR 만들기 0, ZI·사슬 계산 0. 합성 시험 `RV33/rev_a33.py` 세 번(셋째가 기록 판; 첫째 검토 도구 결함, 둘째 우선순위 실패 — 보충 33 P15), 보관 목록 `RV33/rev_a33_archive.py` 한 번(첫 시도는 문법 오류로 시작 전 멈춤). 모두 실행 전 도구 sha를 LOG에 적음, 3분 안, 앞에서 돌림, 가벼운 합성 또는 이름·크기·시각만. 쓴 곳: RV33, SP의 보충 33·`_r1`·두 `.sha256`, 이 파일, `KB/LOG.md` 덧붙임. RR·동결본·GWT8·저장소 `.git`·K8 브랜치·OUTK·봉인 뿌리·옛 VBR·옛 VBT·KV·AD32·AD33·KV2·KI 쓰기 0. 끈 프로세스 0. 끝에 python·VISSIM 0.
- 블라인드: 봉인 시드(37/59/61/67)·codex 64cf 숫자 0, 봉인 뿌리 열람 0, v3c3-s47 자료 0. 목적값·예측값 출력 0. 옛 VBR·옛 VBT 파일 내용 열람 0(이름·크기·시각·경로 길이만).
- 디스크: C: 40 GB, D: 384 GB 여유 [실행].

태그: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.

---

## 1. 찾은 구멍과 고친 곳 (자세한 표는 보충 33 §16.1)

| # | 구멍 | 고침 |
|---|---|---|
| R1 | `AD33/run_bn.py`의 BelowNormal 설정이 조용히 실패(ctypes 기본 int 반환형이 가짜 핸들을 자름, `SetPriorityClass` 0·오류 6) [실행]; §0.1·§3.3은 자기 시험이 BelowNormal이었다고 적음 | 사실 바로잡기·공개 P14; 바이트는 고정 목록 그대로, V-B 단계는 쓰지 않음(`KI/launch.ps1` WMI 16384 + 구동기 `k92lib.set_below_normal()` 바른 꼴) |
| R2 | 보관 지킴이 V0–V10뿐(멈춘 실행 → V0 틈) | 검토 때 목록 값 둘(위 표)을 §5 (라)와 여기에 적고, VerifyVB가 V0 `archive_tree`·다시 낸 두 목록과 견줌, 다르면 S-K57 |
| R3 | VerifyVB "`loaded` 수 = 기록을 남긴 프로세스 수" 모호 | 이름·오류 0·짝(PID 일치)·순번 넷 + 보고 항목(같은 PID 토큰 묶음의 후보 시각 겹침) |
| R4 | 겹침 확률이 "12개" 가정에 기대고, 실제 재사용·동시·두 번 실림·셋 중 둘 겹침·결정 단계 다시 시도 근거가 합성 강제뿐 | 가정 없는 상한(≤ 1.6 × 10⁻¹², 58번 합쳐), 검토 시험 R1(실제 PID 재사용 3번: 새 훅 겹침 0)·R1o(옛 훅 재사용 8번: `hook_error` 8)·R2(같은 PID·시각 동시 12: 겹침 0)·R3(한 프로세스 두 번: 작업자 같은 기록 둘, 어댑터 STOP 쪽)·R4(셋 중 둘 토큰 전체 겹침: 거절, 첫 파일 11개 그대로, STOP 쪽) |
| R5 | ZI `hook_on`이 있으면 S-K54라는 인용이 코드와 다름 | 실제 동작(준비 S-K54, `exist_ok=False` 예외로 멈춤) |
| R6 | 경로 길이 여유 미확인(긴 경로 지원 꺼짐) | 234/260, 약 145/260 |
| R7 | 고르기 자식 작업 폴더가 보관 `KV` | 공개 P16(쓰기 아님) |

- 바꾸지 않은 것: 판정 정의·문턱·표본·VB-I1 판정 4결정·보고 10결정·닫힌 잎 목록·VB-I1–I7·VB-M1–M9·ZI 규칙(z1)–(z7)·결과 넷의 뜻·STOP S-K50–S-K56의 조건(S-K57은 VerifyVB 보관 대조를 더함). 도구·확인 출력·기대 고정 목록(`a1b02027…`, 63줄)은 그대로입니다. 고친 것은 보충 33의 글뿐입니다. R2·R3은 STOP을 늘리는 쪽이고 V-B 데이터 전입니다.

## 2. 다시 확인했고 문제없는 것 (자세히는 보충 33 §16.2)

1. 근거 sha, 기대 고정 목록 63/63, 차이 파일 셋이 지금 파일에서 다시 낸 본문과 같음, 자기 시험 둘·`dry_a33` 모두 참 [실행].
2. 훅 고침은 이름·열기 모드·`os.mkdir`과 시작 때 `os.urandom(8)`·`time.time_ns()` 한 번뿐이고, 결정 계산·원천 고정(`src.*` 모듈 sha, 튜닝 경로 글자)·어댑터의 `sys.modules` 훑기에 닿지 않음; `vb`→`vb2`는 비교 규칙이 자리로 가르므로 옛 실행과 같은 분류 [읽음·실행]. 직접 증거는 V-B 단계의 ZI·VB-I1.
3. 이름 유일성: Declare P1–P8 + 검토 R1–R4 [실행].
4. 고르기·재계산기는 앞머리 `glob`과 `cand.json` 안 값만 씀(이름 쪼개기 0), 검토 시험에서 두 도구의 상태·고른 폴더 같음 [읽음·실행].
5. 새 V-B 데이터 0, 보관 그대로(고정 목록 20–33줄 OK, `archive_bytes()` 아홉 참, 파일 시각) [실행].
6. V0 C2·C3·C5·C13, V10 S-K57/S-K53 갈림이 글과 같음; HOOKDIR 등에 `__pycache__` 0 [읽음·실행].

## 3. 메인 세션이 할 일·사용자에게 알릴 것 (막힘 아님)

1. 사용자 보고에 적을 것: (가) P1 — 이름 고침이 결정 글의 "후보 폴더"보다 넓음(`loaded`·오류 파일·배타 생성; 사용자가 고른 권장안 글이 "후보 폴더·`loaded` 파일"이었음); (나) P14 — `run_bn.py` 우선순위 설정 실패, Declare 자기 시험 둘은 보통 우선순위(가벼운 합성), V-B에서 안 씀; (다) P15 — 검토 시험 세 번(첫째 검토 도구 결함, 둘째 우선순위 실패, 셋째 기록 판), 보관 목록 도구 첫 시도 문법 오류; (라) 실제 운영 체제 PID 재사용이 차례로 띄운 121개에서 2–8번 — 보충 32 P14의 "60개 재사용 0"보다 잦음; (마) 비용 약 9.5–10 h(결정 기록 8–9 h보다 김).
2. V-B 시작: 보충 33 §6.1 — 이 파일 sha를 LOG에 적고(V0 C2), `cp AD33/a33_pins.expected.sha256 KB/a33_pins.sha256`·`cmp`·63/63, LOG 한 항목, `KI/launch.ps1 -Tag vb2_chain -Script ..\k92_vb2\vb_chain.py -ArgLine chain`. 자기 시험은 다시 돌리지 않음. `AD33/run_bn.py`는 쓰지 않음.
3. VerifyVB: 보충 33 §6.5의 넷과 보관 대조(위 표의 두 값).
4. 남은 미해결: 없음.

## 4. 검토 도구와 출력 (RV33 = `KB/a33review`; 읽기만 하는 점검·합성 시험, 판정에 쓰지 않음)

| 파일 | sha256 |
|---|---|
| `rev_a33.py` (셋째 판; 첫째 `da72c75054234f22…`, 둘째 `10119951615cfa5b…`) | `a35a286f82560617e692f4b15f307ede4be95eec73faf82817cd41b27a847487` |
| `out/rev_a33.json` (셋째 실행: R1–R4 참, BelowNormal 참) | `9b8694dca6fe08349e91857c0ff56c496a0fae3493b48012a7cecf7560e68f14` |
| `out/rev_a33_run1.json` (첫째, R4 거짓 = 검토 도구 결함) | `2ebe01d0fd4da3938e839c5c4dcc47b3943a344b1b9ee37d3e7b80544724a515` |
| `out/rev_a33_run2.json` (둘째, R1–R4 참, 우선순위 실패) | `c1796ee1215a5377e82def50152e4f66204fa66a805737051ae6efe83fe67e09` |
| `rev_a33_archive.py` | `325871a7e2e72846d2bca48a9bf93a26a94fe5bf8e00a470ec116711707a6a0a` |
| `out/rev_a33_archive.json` (검토 때 보관 목록 값) | `b08c3b5ebb1ff6ed4e8fcbdd09b53f12b739d99b002d9a4aa379a405bba83b07` |
| `r1/K8_PREDECLARATION_AMENDMENT_33_declare.md` (Declare 판 사본) | `b0db6bf5d49e5b98…` |
