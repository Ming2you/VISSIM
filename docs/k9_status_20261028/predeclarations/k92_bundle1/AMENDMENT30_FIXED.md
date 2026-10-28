# 보충 30 고정점 (ReviewDeclare A30, 2026-10-21 11:53 KST)

이 파일이 고정점입니다. 아래 sha256과 다른 보충 30으로는 어떤 단계(G0–G3: check30 apply, seal30, f30, jb, post30)도 하지 않습니다. 새 구동기 `AD30/k92t30.py`의 `a30_sha()`가 이 파일 안에 보충 30 고정판 sha가 64자로 있는지 봅니다(`k92t30.py:499-508`). check30 C6은 `KB/a30_pins.sha256`의 sha가 이 파일 안에 64자로 있는지 봅니다(`k92t30.py:621-628`). 그래서 이 파일에는 고정판 sha만 64자로 적고, Declare 판 sha는 앞 16자만 적습니다(보충 29 §14.1 V4와 같은 까닭: 되돌린 파일이 통과하지 않게). 이 시각 뒤에는 보충 30을 고치지 않습니다. 바꿔야 하면 새 보충(31 이후)에 까닭을 적습니다.

| 문서 | sha256 | 크기 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_30.md` (검토 판 = 고정판) | `ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a` | 83,288 B, 476줄, LF, CR 0 |
| [보충 30 §9, G0·G1] 기대 고정 목록 `KB/a30decl/a30_pins.expected.sha256` (G1이 쓰는 `KB/a30_pins.sha256`은 이 바이트와 같아야 함; 검토가 바꾸지 않음) | `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e` | 83줄, 14,537 B, LF, CR 0 |
| [§3.1, 고정 목록 58·59줄] 새 구동기 `KB/a30decl/k92t30.py` / 새 판정기 `KB/a30decl/k92t30_judge.py` (검토가 바꾸지 않음) | `8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4` / `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` | 50,442 B / 52,254 B |

- 고정 시각: **2026-10-21T11:53+09:00** [실행 `date` 11:52:40 뒤]. 고정판 파일은 11:52에 마지막으로 바뀌었고 그 뒤 바뀌지 않았습니다(위 sha). 같은 폴더의 `SP/K8_PREDECLARATION_AMENDMENT_30.md.sha256`도 위 값과 같습니다 [실행 `sha256sum -c` OK].
- 줄임말: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, KB = `SP/k92/bundle1`, KI = `KB/impl`(바꾸지 않음), AD30 = `KB/a30decl`(새 구동기·판정기·확인 도구), RV30 = `KB/a30review`(이 검토의 도구·출력·사본), TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`, OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`, OUTK = `OK2/k92t`(판정 단계 출력), OUT30 = `OK2/a30`, GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, F = 충실도 관문, VR = VISSIM 기준 도구 `k92_vissim_ref.py`.
- 검토 전 판(`_r1`): `SP/K8_PREDECLARATION_AMENDMENT_30_r1.md` = `304719e19fc7fd02…`(62,957 B, 410줄; 64자는 그 `.sha256` 파일과 보충 30 머리에). Declare 단계가 11:11에 쓴 판과 바이트가 같습니다 [실행 `cmp`, `RV30/r1/K8_PREDECLARATION_AMENDMENT_30_declare.md`와도 같음].
- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `eae2e6faf3c13dc42e84ef545fef734ad5ed9650946de72a76cb392b028c8d99`(182줄, D-K9-56·57 :176-182), `KB/GATES_K92B1.md` `63dd35e2…`, `KB/VERIFY_GATES_K92B1.md` `b9e90cd2…`, 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…`와 고정점 24–29(보충 30 §0 값과 같음), `KB/k92t_pins.sha256` `38a2ce14…` 56/56 OK, 기대 고정 목록 83/83 OK(앞 56줄 = `KB/k92t_pins.sha256` 바이트), OUTK 이어 받는 기록 11개·`steps.jsonl`(59줄)·`driver.log`(3,434 B)·F 잡 로그 셋(크기·바이트 sha) = 보충 30 §0. `KB/LOG.md` 검토 시작 전 172,925 B = `cfebe3c5…`.
- 데이터: **F 판정 값·J-b 값·보충 30 적용 데이터 0개.** OUTK에서 10-21 07:04:32 뒤 바뀐 파일 0, `judge/` = j0·ja·jwall, `f_persist`·`f_persist30`·OUT30 없음, STOP 파일 `STOP_f.json` 하나 [실행]. 검토 끝 `check30 --mode decl` 37점검 거짓 0, OUTK 18,019파일 목록 = 선언 목록 [실행 `RV30/out/check30_rv.json`]. GWT8 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` 커밋 6개), K8 브랜치 `b9734abe`, `status --porcelain` 0줄, 원격 k92 참조 0, 푸시 0 [실행 검토 중].
- 이 검토에서 한 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. v3c3-s47 VR 0. 판정기를 실제 F 데이터에 부른 일 0. 무거운 일 여섯(스냅숏 둘, 훑기 둘, v3c3-s43 VR 한 번, `check30 --mode decl` 한 번)은 `RV30/rvlaunch.ps1`로 WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번에 하나. 쓴 곳: RV30, `TK/a30review/vr_s43_21`(새), SP의 보충 30·`_r1`·두 `.sha256`, 이 파일, `KB/LOG.md` 덧붙임. OUTK·TREE·봉인 뿌리·GWT8·KI·AD30·KT·V4·동결본·런 폴더 쓰기 0. 끈 프로세스 0. 끝에 python·VISSIM 0.
- 블라인드: 봉인 시드(37/59/61/67)·codex 64cf 숫자 0. F 잡 로그 셋·봉인 뿌리·s47 F 잡·포착 폴더·`f_vref`의 내용 열람 0(바이트 sha·stat·이름만). 훑기 도구는 파일 이름·개수만 냈고(줄 내용 0), 세션 기록은 보고만으로 훑었습니다. 스냅숏 `RV30/out/snap_rv30_before.json`·`snap_rv30_after.json` 모두 s02 대비 SAME [실행 `KI/k92snap.py diff`].
- 디스크: C: 38 GB, D: 396 GB 여유 [실행 `df`].

태그: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.

---

## 1. 찾은 구멍과 고친 곳 (자세한 표는 보충 30 §13.1)

| # | 구멍 | 고침 |
|---|---|---|
| V1 | §5.5·§10-4가 F 잡 로그 걸러 읽기를 "목적값 노출 가능성, 확인할 기록 없음"으로 적음 | 세션 기록으로 확인한 사실: Gates가 07:05:57 KST에 세 F 잡 로그에 `grep -c` 한 번(개수만, 's47' 글자 0). 03:30 뒤 세션 기록 7개에 F 주 표본 목적값 줄 0, 주 표본 K92T_JOB 줄 0. "엶" 공개는 그대로 |
| V2 | 실패 진단 열람이 "`f_persist.log` 끝 줄, 07:0x"로만 적힘 | 07:04:42 KST, `f_persist.log` 전체 75 B + `f_vref.log` 끝 300 B(값 없음) |
| V3 | §8 표가 검증 도구 고정 시점의 바뀜을 보충 24 §3.1-8만 적어, 보충 24 §5.4 끝 줄·보충 29 §5 "누가"와 어긋남 | §8 행을 세 자리로 넓힘 |
| V4 | G2의 "종료 코드"가 WMI 분리에서 남지 않음; STOP 파일 없는 SystemExit 끝의 처리 없음 | 종료 코드 = `steps.jsonl` rc, `post.json`·`STOP_a30_*` 없이 끝나면 G2 거짓 → STOP, 진단 경로 |
| V5 | 쓰는 명령(`seal30` 드라이 아님, `check30 --dest` OUT30 안)을 `chain30` 밖에서 돌릴 수 있음 | S-K41에 더함 |
| V6 | "`capture.json` ok 수" 글과 코드(`ok`가 false 아님)가 다름 | 정확한 뜻과 같은 까닭을 적음 |
| V7 | 봉인 이동 완전성의 근거·목록 밖 s47 파일·맨 위 여섯의 대조가 없음 | 훑기 결과, 목록 밖 파일과 까닭(재생 상태 공개), §10-15·16 |
| V8 | 21상태 VR이 다른 까닭으로 멈출지가 추론뿐 | v3c3-s43 같은 호출 rc 0·21/21·정수 |

- 바꾸지 않은 것: 판정 정의·문턱·표본·팔(F-1–F-3, J-0·J-a·J-b), 새 구동기·판정기·`dry_a30.py`·차이 파일·확인 출력·기대 고정 목록(§9). 고친 것은 보충 30의 글뿐입니다(V3·V5는 고정·STOP 규칙을 글과 맞추거나 늘리는 쪽).

## 2. 고친 파일

| 파일 | Declare 판 | 고정 값 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_30.md` | `304719e19fc7fd02…`(410줄) | 위 표(476줄; "[검토]" 글자 21곳, §13 더함) |

## 3. 다시 확인했고 문제없는 것 (자세히는 보충 30 §13.2)

1. §0 sha 모두 같음, 기대 고정 목록 83/83, `k92t_pins` 56/56, GWT8 상태 [실행].
2. 지속성 좁힘은 보고 전용 항목만 바꿈: 판정기 차이에서 판정 칸 줄은 기반과 같고, `f_judge`는 참거짓·n만 냄, LOG 줄에 MAE 값 없음. 함수 글 대조(`rv_static30.py`)와 지속성 상수 = 글 [실행·읽음].
3. F 값 계산·열람 0: 파일 시각, `judge/` 셋, LOG, 세션 기록, 검토 끝 `check30 --mode decl`(OUTK 목록 같음) [실행].
4. 이어 하기 규칙: 기반 단계를 다시 돌릴 함수 없음, `chain30` 한 번, `require_prev` 가드, C6 글자 대조가 `launch.ps1` 경로에서도 참 [읽음·실행].
5. 봉인 이동 뒤 v3c3-s47 F 목적값이 남는 곳은 닫힌 F 데이터 폴더뿐(OUTK 밖 라벨 파일 6개는 값 키 0) [실행].
6. J-b 다시 돌림 범위: 판정 항목 45개 값에 트리·경로 글자 0, 한 트리 안 비교 셋 = 다시 돌림 목록 [실행·읽음].
7. STOP 규칙이 모두 코드 자리에 있음 [읽음].

## 4. 메인 세션이 할 일·사용자에게 알릴 것 (막힘 아님)

1. 사용자 보고에 적을 것: (가) V1 — Gates의 F 잡 로그 걸러 읽기는 개수만 낸 `grep -c` 한 번이었고 목적값은 어느 출력에도 나오지 않았음(세션 기록 확인; 그래도 보충 25 §6.4의 "엶"), (나) V2 — `f_vref.log` 끝 300 B도 실패 진단으로 열렸음(값 없음), (다) V3 — 다음 검증의 도구 고정 시점 규칙이 G-K4 plant 원자료 재계산에도 걸림, (라) §10-15 — seal30 뒤 봉인 뿌리 맨 위가 여섯이 되므로 다음 검증의 봉인 대조 규칙을 도구 고정 전에 정할 것, (마) §10-16 — `OUTK/f_*/replays/s47/`의 재생 상태(K9-1 V4와 같은 꼴의 VISSIM 관측)는 닫힌 목록 밖임.
2. 적용은 보충 30 §6 G0부터: 보충 30 sha = `.sha256` = 이 파일의 `ba556227…`(64자 위 표). 기대 고정 목록은 `KB/a30decl/a30_pins.expected.sha256`(`7afabd03…`, 83/83). G1의 `KB/a30_pins.sha256`은 그 파일과 `cmp` 같아야 합니다. G2는 `powershell -NoProfile -File KI/launch.ps1 -Tag k92t30_chain -Script ..\a30decl\k92t30.py -ArgLine chain30` 하나뿐입니다(V5).
3. 남은 미해결: 없음.

## 5. 검토 도구와 출력 (RV30 = `KB/a30review`; 읽기만 하는 점검·시험, 판정에 쓰지 않음)

| 파일 | sha256 |
|---|---|
| `rv_leak30.py` / `out/leak30.json` (봉인 뿌리 밖 k92t 출력·세션 기록의 v3c3-s47 목적값 줄; 이름·개수만) | `3b7ece0e27075a5fb5abc3cb00d074a7144079ff6e4e827c67f4f11426845983` / `d844c450bfa30a57e3214a1710ad973373a58aa4248f19ebee5de7d6550bbd75` |
| `rv_cmds30.py` / `out/cmds30.txt` / `out/cmds30_main.txt` (F 잡 로그를 건드린 명령 글; 결과는 길이·개수만) | `620b182a79dd83c39c257f792a0bc113f045177fef7a781a597c92b71f349102` / `7b06b7eb5d50114a4057f0652464dbb9d547117ac402f36fcfa1a6a0d8812e23` / `4e93cd2a62e6cb8ed8b5616a9d642df90a53b618b2d54b713c4b13a3175a2a63` |
| `rv_labels30.py` / `out/labels30.json` (닫힌 목록 밖 OUTK 파일의 F 주 표본 라벨·값 키 이름) | `a42dd24d17cd98c12dadeca5b87966297d9f7507fcb9391b20f5edab9b3346aa` / `d0cb9472b4f2b376dd64c14df051cca9d27ddd42485e0f3667fe174840395bea` |
| `rv_vr30.py` / `out/vr30.json` (같은 VR 호출을 v3c3-s43에; 출력 `TK/a30review/vr_s43_21`) | `11def0feee29c19d179bf5f21db62df6d852e9681cc9ed9c36db5d882f7d77b3` / `7dd617e75b75b571125160bddf61978ff6061b8c8dc41a8bb9a4a337901ab43f` |
| `rv_static30.py` / `out/rv_static30.json` (함수 글 대조·지속성 상수; 코드만) | `d4580322ddcf1882f313fc23469ed7171444b4121b62be747e746dacb02ff35e` / `4af9b5357b73c0c6f09c0b78fa5c6825b8a8d8b60a2cb1b4bb46ec626421441f` |
| `rv_c6path.py` (C6 글자 대조를 `launch.ps1` 경로로; 코드만) | `6ccc7a5b9d9f82b43d998c06040a2243939d99043fb2ca116cf6474257e32f75` |
| `out/check30_rv.json` (새 구동기 `check30 --mode decl`, 검토 끝; 37점검 거짓 0) | `9df7c11f7c510ff9fa614c71d6d632cecc552cba72732ff69a80042b592d03c9` |
| `out/snap_rv30_before.json` / `out/snap_rv30_after.json` (s02 대비 SAME) | `88762891f17c31e3ae998647790f16caf057df7080f2cfa304026493617183a3` / `11060d6b70244fdf90b460802f9f45549b922d5bccef8c76f257181f5ad00d1e` |
| `rvlaunch.ps1` (`KB/vgates/vglaunch.ps1`의 머리말 두 줄만 바꾼 사본) | `ecbbd276612bebd24cf964b202ef5da1e3f94884100ba7fa7fa7d95c5196de49` |
| `sec13.md` (보충 30 §13 글의 원고; 덧붙일 때 `k92_vissim_ref.py:99-101` 한 곳을 `:98-101`로 바꿈) | `ee55f6714e7246897d4d7122bfb90fefe67cf66539ad8dc9810afe8acb5b3c12` |
| `rv_fixcheck30.py` (구동기 자신의 `a30_sha()`와 C6 글자 대조를 이 파일·기대 고정 목록에; 결과 `a30_sha` = `ba556227…`, C6 같은 뜻 참·83줄·틀린 줄 0, Declare 판 64자 sha가 이 파일에 없음) | `4952b5d3b6a28aacc479e65a39bb4c8621db142eaf58685bb87861758ef706d6` |
| `r1/K8_PREDECLARATION_AMENDMENT_30_declare.md` (Declare 판 사본) | `304719e19fc7fd02…` |

- 공개: `rv_cmds30.py`는 세션 기록의 명령 글(에이전트 자신의 입력)을 출력합니다. 결과 글은 출력하지 않습니다. 검토 도구 sha는 데이터에 처음 돌리기 전에 LOG에 적었습니다(코드만 읽는 `rv_static30.py`·`rv_c6path.py`는 돌린 뒤 적음; 데이터 0). LOG 머리 시각을 두 번 잘못 적었고 같은 항목에 바로잡았습니다.
