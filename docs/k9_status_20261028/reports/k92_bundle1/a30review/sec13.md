
---

## 13. 반박 검토 (ReviewDeclare, 2026-10-21 11:29–11:5x KST) — 고친 곳과 확인

- 검토는 Declare 판(`SP/K8_PREDECLARATION_AMENDMENT_30_r1.md`, `304719e19fc7fd0238d5cc9c4203b66b6d228892b8cb56b02b15f5054885f262`; 사본 `RV30/r1/K8_PREDECLARATION_AMENDMENT_30_declare.md` 같은 바이트)을 읽고 다음을 했습니다: §0 sha 대조, 새 구동기·판정기 코드 읽기와 함수 글 대조, 하네스 출력 줄·U4 창 규칙·VR 코드 읽기, 봉인 뿌리 밖 k92t 출력과 세션 기록의 v3c3-s47 목적값 줄 훑기(개수만), OUTK의 F 주 표본 라벨 위치 훑기(경로·개수만), 같은 VR 호출을 v3c3-s43에 돌린 시험, 새 구동기 `check30 --mode decl` 다시(읽기만), 스냅숏 앞·뒤.
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. v3c3-s47 VR 실행 0. 판정기를 실제 F 데이터에 부른 일 0. F 잡 로그 셋·봉인 뿌리·s47 F 잡·포착 폴더·`f_vref`의 내용 열람 0(바이트 sha·stat·이름만). 봉인 시드·codex 64cf 숫자 0. OUTK·TREE·봉인 뿌리·GWT8·KI·AD30 쓰기 0(OUTK 18,019파일 목록 같음, 아래 13.2-3). 커밋·브랜치·푸시 0. 금지 시험 0, 시험 실행 0. 무거운 일은 모두 `RV30/rvlaunch.ps1`로 WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번에 하나. 끈 프로세스 0. 끝에 python·VISSIM 0.
- 검토 도구는 쓰고 나서 데이터에 처음 돌리기 전에 sha를 LOG에 적었습니다(LOG 2026-10-21 11:29 항목과 덧붙인 줄; 머리 시각을 잘못 적은 곳은 같은 항목에 바로잡음).

### 13.1 고친 곳 (모두 글; 코드·문턱·판정 정의·고정 목록 바이트는 그대로)

| # | 구멍 | 고침 | 자리 |
|---|---|---|---|
| V1 | §5.5·§10-4가 Gates 단계의 F 잡 로그 걸러 읽기를 "목적값이 화면에 나왔을 가능성 [추론; 확인할 기록 없음]"으로 적었습니다. 세션 기록이 있습니다 | 세션 기록으로 확인한 사실로 바꿈: 07:05:57 KST `grep -c` 한 번(개수만, 결과 554자, 's47' 0), 10-21 03:30 뒤 세션 기록 7개에서 F 주 표본 목적값 줄·주 표본 K92T_JOB 줄 0 [실행 `rv_cmds30.py`, `rv_leak30.py`]. 개수만 냈어도 보충 25 §6.4의 "엶"이므로 공개는 그대로 | 머리 알리는 말 4, §5.5, §10-4 |
| V2 | Gates 단계의 실패 진단 열람이 "`f_persist.log` 끝 줄 하나, 07:0x(분 미상)"로 적혔습니다. 실제로는 07:04:42 KST에 `f_persist.log` 전체(75 B)와 `f_vref.log` 끝 300 B(값 없음)도 열었습니다 | 파일·분을 적음 | §5.5, §10-17 |
| V3 | §8 표가 검증 도구 고정 시점의 바뀜을 보충 24 §3.1-8만 적었습니다. 같은 뜻의 보충 24 §5.4 끝 줄과 보충 29 §5 "누가"("sha를 k92t 데이터 전에 LOG에 고정")는 §8 "그 밖은 그대로 구속"에 남아 §5.4와 어긋났습니다(k92t 데이터는 이미 있음) | §8 표 행을 넓힘(같은 규칙 "처음 읽기 전"을 세 자리에) | §8 |
| V4 | §6 G2가 "종료 코드"를 보라고 했지만 WMI 분리 발사는 사슬 프로세스의 종료 코드를 남기지 않습니다. 또 몇몇 가드(`a30_sha`·`require_prev`·`persist_argv`·`chain30` 가드)는 STOP 파일 없이 SystemExit로 끝나, 그 경우의 처리가 글에 없었습니다 | "종료 코드 = `steps.jsonl`의 rc 칸", "`post.json`도 `STOP_a30_*`도 없이 끝나면 G2 거짓 → STOP(S-K41/S-K43)", 진단은 §4.5 예외로 `k92t30_chain.txt` 끝 부분 | §6 |
| V5 | 새 구동기는 `seal30`(드라이 아님)·`check30 --mode apply --dest <아무 곳>`을 `chain30` 밖에서도 돌릴 수 있습니다. 그러면 `chain30`이 시작하지 못하거나 봉인이 점검 없이 일어납니다 | S-K41에 "§6 G2의 `chain30` 밖에서 쓰는 명령을 돌림"을 더함(STOP을 늘리는 쪽) | §7 |
| V6 | §4.2 잡 정상 셈의 "`capture.json` ok 수"와 코드(`ok`가 `false`가 아님)가 글자로 달랐습니다 | 정확한 뜻과 그것이 같은 까닭(성공한 포착만 `capture.json`을 씀)을 적음 | §4.2 |
| V7 | 봉인 이동이 완전한지(F 잡 로그 셋 말고 v3c3-s47 F 목적값이 봉인 뿌리 밖에 남는 곳)의 근거와, 닫힌 F 데이터 목록 밖 s47 파일의 처리가 글에 없었습니다. 봉인 뿌리 맨 위가 여섯이 된 뒤의 대조도 없었습니다 | 훑기 결과(F 목적값 줄 0, 라벨 파일 6개는 값 키 0), 목록 밖 파일과 까닭(재생 상태 = K9-1 V4와 같은 꼴, 공개), 맨 위 여섯의 대조 규칙 | §4.2, §10-15·16 |
| V8 | 21상태 VR 호출이 창 범위 말고 다른 까닭으로 멈출 수 있는지가 [추론]뿐이었습니다 | v3c3-s43 같은 호출 결과(rc 0, 21/21, 정수)를 적음 | §2.2 |

- V1–V8은 판정 값을 바꾸지 않습니다. V3·V5는 고정·STOP 규칙을 글과 맞추거나 늘리는 쪽, 나머지는 공개·정확성입니다. 새 구동기·판정기·`dry_a30.py`·차이 파일·확인 출력·기대 고정 목록(§9, `7afabd03…`, 83줄)은 바꾸지 않았습니다.

### 13.2 다시 확인했고 문제없는 것

1. **sha** [실행]: §0의 문서·기록 값 모두 같음(결정 기록 `eae2e6fa…` 182줄, 보충·고정점 24–29, 관문 보고·검증, OUTK 이어 받는 기록 11개, `steps.jsonl` 59줄, `driver.log` 3,434 B, `k92t_chain.txt`, F 잡 로그 셋 크기·바이트 sha, 스냅숏 s02·s28·s28b). 기대 고정 목록 83/83 OK, 앞 56줄 = `KB/k92t_pins.sha256` 바이트(`cmp` 같음), `KB/k92t_pins.sha256` 56/56 OK, `TK/a27/k92t.build.json` `a1e98fa7…`. GWT8 head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, K8 `b9734abe`, status 0줄, 원격 k92 0, 6커밋. s28·s28b 모두 s02 대비 SAME.
2. **지속성 좁힘은 보고 전용만 바꿈** [실행·읽음]: 판정기 차이(`A30_DRIVER.diff` 1017–1265줄)는 `cmd_f`에서 지속성 파일 뿌리(`f_persist30`)·`persistence_report`·`job_counts` 칸·끝 줄뿐이고, 판정 칸(verdict·`f_judge`·INCOMPLETE 조건 `complete`)의 줄은 기반과 글자가 같습니다. `f_judge`(`k92_gates.py:861-887`)는 F-1·F-2·F-3 참거짓과 n만 내고 지속성 파일을 읽지 않습니다. 구동기 LOG 줄도 그 참거짓·n·지속성 개수·측정 불가 목록·`complete`만 적습니다(MAE 값 없음). 내 함수 글 대조(`rv_static30.py`)도 같음·바뀜·뺌·새 목록이 §3.2·§3.3과 같고, 지속성 상수(21상태·측정 불가 1,050·겹침 15)가 §2.2 글과 같습니다. U4 창 규칙 `a ≥ 900, b ≤ 9000, b − a ≥ 1`(`derive_head_saturation.py:72-73`, `:379`)과 VR 창(`k92_vissim_ref.py:99-101`, `:119-122`)도 §2.2와 맞습니다. VR의 `m1_T450`은 정수(`int(sel.sum())`)입니다.
3. **F 값 계산·열람 0** [실행]: (가) OUTK에서 10-21 07:04:32 뒤 바뀐 파일 0(`find -newermt`), `judge/`는 j0·ja·jwall 셋, `f_persist`·`f_persist30`·`OK2/a30` 없음, STOP 파일 `STOP_f.json` 하나. (나) LOG에 F 판정 줄 0. (다) 검토 끝에 새 구동기 `check30 --mode decl` 다시: 37점검 거짓 0, OUTK 파일 목록 18,019파일·4,223,333,998 B = 선언 목록(다름·한쪽 0) — 검토가 OUTK를 바꾸지 않았음. (라) 세션 기록: F 목적값 줄 0, F 잡 로그는 개수만 낸 걸러 읽기 한 번(V1).
4. **이어 하기 규칙** [읽음·실행]: 새 구동기에는 시작 훑기·prep·J-0·J-a·F 잡을 다시 돌리는 함수가 없습니다(§3.2 뺌 14). `chain30`은 OUT30이나 새 단계 기록이 있으면 시작하지 않고, `require_prev`는 STOP 파일이 기반 `STOP_f.json`(기록 바이트) 하나이고 기반 단계 기록 넷이 기록 바이트일 때만 다음으로 갑니다. f30은 기존 F 잡·포착·`f_vref`를 읽기만 하고 다시 만들지 않습니다(그것을 쓰는 명령이 없음). `KI/launch.ps1`로 돌 때 `__file__` 경로(`KI/../a30decl/k92t30.py`)를 풀어도 C6 글자 대조가 참입니다(`rv_c6path.py`: 참, 참). 사후 훑기(`scan_vissim_blind(sealed=True)`)는 봉인 뿌리에서 `k92_record.json`만 읽으므로 `k92t/logs`가 더해져도 영향이 없습니다(`k92t30_judge.py:359-371`).
5. **봉인 이동** [실행]: `seal30 --dry-run`(Declare) 3/3 크기·sha 같음, 봉인 뿌리 맨 위 다섯, `SEALED/k92t` 없음 — 지금도 같음(위 1). 이동 뒤 남는 곳은 §4.2 [검토] 줄(V7).
6. **J-b 다시 돌림 범위** [실행·읽음]: `gates_k91t.json`(`4e59f61d…`)의 J-b 판정 항목 45개 값에 트리 이름·경로 글자(`k91t`·`k92t`·드라이브 경로·`k8_gate_trees`·`/sa/`)가 0개입니다. 그래서 BASE 산출을 k91t에서 복사해도 판정 값 글자에 트리 차이가 들어가지 않습니다. 한 코드 트리 안 비교 셋은 다시 돌림 목록과 맞습니다: 같은 실패 규칙(`sa_gates.py:427`, `:1567`) ↔ ROBS61 BASE T=1·150 × 세 시드, 포착 출처(`captured_provenance`, `:210-250`, `:1637-1644`) ↔ TL3·T9C BASE 2,700, G-EB-13 양성 대조(`:1478-1496`) ↔ full BASE 2,700·4,950 hooks. 이것은 D-K9-57 ②와 기반 구동기(데이터 전 고정)의 O6 그대로입니다.
7. **STOP 규칙 ↔ 코드** [읽음]: S-K41(check30 거짓 → `STOP_a30_check30`; 보충 30 sha·이어 하기 가드 → SystemExit, V4), S-K42(seal30 전·뒤 점검·post30 목록), S-K43(VR rc·`complete`), S-K44(`fcount`), S-K8·S-K9(J-b·F), S-K10(사후 훑기), S-K11(스냅숏 다섯)이 모두 코드 자리에 있습니다(`k92t30.py:682-832`, `stage_jb`·`snap`).
8. **스냅숏** [실행]: 검토 앞 `RV30/out/snap_rv30_before.json`·뒤 `snap_rv30_after.json` 모두 s02 대비 SAME.

### 13.3 남은 것 (막힘 아님)

- 미해결: 없음.
- 다음 검증에 넘길 것: §10-15(봉인 뿌리 맨 위 여섯의 대조 규칙), §5.4(도구는 처음 읽기 전 고정), §10-16(재생 상태 공개).

### 13.4 검토 도구와 출력 (RV30 = `KB/a30review`; sha는 고정점 `KB/AMENDMENT30_FIXED.md`에도 적음)

| 파일 | sha256 |
|---|---|
| `rv_leak30.py` / `out/leak30.json` | `3b7ece0e27075a5fb5abc3cb00d074a7144079ff6e4e827c67f4f11426845983` / `d844c450bfa30a57e3214a1710ad973373a58aa4248f19ebee5de7d6550bbd75` |
| `rv_cmds30.py` / `out/cmds30.txt` / `out/cmds30_main.txt` | `620b182a79dd83c39c257f792a0bc113f045177fef7a781a597c92b71f349102` / `7b06b7eb5d50114a4057f0652464dbb9d547117ac402f36fcfa1a6a0d8812e23` / `4e93cd2a62e6cb8ed8b5616a9d642df90a53b618b2d54b713c4b13a3175a2a63` |
| `rv_labels30.py` / `out/labels30.json` | `a42dd24d17cd98c12dadeca5b87966297d9f7507fcb9391b20f5edab9b3346aa` / `d0cb9472b4f2b376dd64c14df051cca9d27ddd42485e0f3667fe174840395bea` |
| `rv_vr30.py` / `out/vr30.json` | `11def0feee29c19d179bf5f21db62df6d852e9681cc9ed9c36db5d882f7d77b3` / `7dd617e75b75b571125160bddf61978ff6061b8c8dc41a8bb9a4a337901ab43f` |
| `rv_static30.py` / `out/rv_static30.json` | `d4580322ddcf1882f313fc23469ed7171444b4121b62be747e746dacb02ff35e` / `4af9b5357b73c0c6f09c0b78fa5c6825b8a8d8b60a2cb1b4bb46ec626421441f` |
| `rv_c6path.py` | `6ccc7a5b9d9f82b43d998c06040a2243939d99043fb2ca116cf6474257e32f75` |
| `out/check30_rv.json`(새 구동기 `check30 --mode decl`, 검토 끝) | `9df7c11f7c510ff9fa614c71d6d632cecc552cba72732ff69a80042b592d03c9` |
| `out/snap_rv30_before.json` / `out/snap_rv30_after.json` | `88762891f17c31e3ae998647790f16caf057df7080f2cfa304026493617183a3` / `11060d6b70244fdf90b460802f9f45549b922d5bccef8c76f257181f5ad00d1e` |
| `rvlaunch.ps1`(`VG/vglaunch.ps1`의 머리말 두 줄만 바꾼 사본) | `ecbbd276612bebd24cf964b202ef5da1e3f94884100ba7fa7fa7d95c5196de49` |

- 공개: `rv_cmds30.py`는 세션 기록의 명령 글(에이전트 자신의 입력)을 출력합니다. 결과 글은 출력하지 않고 길이·'s47' 글자 있음·규칙 개수만 냅니다. `rv_static30.py`·`rv_c6path.py`는 코드만 읽습니다(데이터 0). `rv_vr30.py`의 출력 뿌리 `TK/a30review/vr_s43_21`은 v3c3-s43 VR 결과(보고만)이며 판정에 쓰지 않습니다.
