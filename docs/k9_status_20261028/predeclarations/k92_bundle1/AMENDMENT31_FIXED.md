# 보충 31 고정점 (ReviewDeclare A31, 2026-10-22 02:5x KST)

이 파일이 고정점입니다. 아래 sha256과 다른 보충 31로는 어떤 단계(G0–G3: check31 apply, scan31, unit31, chain31)도 하지 않습니다. 새 구동기 `AD31/k92t31.py`의 `a31_sha()`가 이 파일 안에 보충 31 고정판 sha가 64자 낱말로 있는지 봅니다(`k92t31.py:202-211`). check31 C6은 `KB/a31_pins.sha256`의 sha가 이 파일 안에 64자로 있고, 구동기·판정기·비교기의 `'<sha> *<경로>'` 줄이 그 목록에 있는지 봅니다(`k92t31.py:355-362`). 그래서 이 파일에는 고정판 sha를 64자로 적고, Declare 판 sha는 앞 16자만 적습니다(보충 29 §14.1 V4와 같은 까닭: 되돌린 파일이 통과하지 않게). 이 시각 뒤에는 보충 31을 고치지 않습니다. 바꿔야 하면 새 보충(32 이후)에 까닭을 적습니다.

| 문서 | sha256 | 크기 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_31.md` (검토 판 = 고정판) | `8541ccb7fa6c951b4affcca67d57e25be09b061c3ae3dd006d050c9c6413e304` | 98,679 B, 575줄, LF, CR 0 |
| [보충 31 §8, G0·G1] 기대 고정 목록 `KB/a31decl/a31_pins.expected.sha256` (G1이 쓰는 `KB/a31_pins.sha256`은 이 바이트와 같아야 함; 검토가 바꾸지 않음) | `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e` | 133줄, 23,474 B, LF, CR 0 |
| [§2.3·§3.4, 고정 목록 85–87줄] 새 구동기 `KB/a31decl/k92t31.py` / 새 판정기 `KB/a31decl/k92t31_judge.py` / jb_unit 비교기 `KB/a31decl/k92t31_unit.py` (검토가 바꾸지 않음) | `63b5aa229eeaf013f2136a838cf9e5be163a087771fc3a71ea3202b0ad12b53d` / `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c` / `a1d82bffb71660361b07b19a823c1ff79286d2add90a0a58fdda8376cc03c6e2` | 34,182 B / 53,192 B / 16,547 B |
| [§4.3 V4 기준] CAP 바이트 목록 `KB/a31review/out/cap_manifest.json` (독립 검증 V4가 기준 실행 뒤 같음을 봄; 파일 3,944개, 1,690,146,202 B, 목록 sha256 `5340ac03da81742dd864044f9922a75bed1e542147249d4a8699a6432e273038`) | `d6691f48954d07dd2b3bbfe718e468fd59f3f6b7492060a2151d4d02e177e3a9` | — |

- 고정 시각: **2026-10-22T02:53+09:00** [실행 `date` 02:52:36 뒤]. 고정판 파일은 02:52에 마지막으로 바뀌었고 그 뒤 바뀌지 않았습니다(위 sha). 같은 폴더의 `SP/K8_PREDECLARATION_AMENDMENT_31.md.sha256`도 위 값과 같습니다 [실행 `sha256sum -c` OK].
- 줄임말: SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`, KB = `SP/k92/bundle1`, KI = `KB/impl`(바꾸지 않음), AD31 = `KB/a31decl`(새 구동기·판정기·비교기·확인 도구), RV31 = `KB/a31review`(이 검토의 도구·출력·사본), TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`, OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`, OUTK = `OK2/k92t`(판정 단계 출력, 보관), OUT31 = `OK2/a31`(아직 없음), SEALED = `OK2/sealed_s47`(봉인 뿌리), CAP = `OUTK/jb/sa/cap/k92t`(J-b 포착 뿌리), GWT8 = `D:/VISSIM-merge/sim3-n31-k8`, WT = `TK/a31_wt_b9734abe`(임시 분리 작업 트리, 아직 없음).
- 검토 전 판(`_r1`): `SP/K8_PREDECLARATION_AMENDMENT_31_r1.md` = `8a76e210230b69c0…`(77,939 B, 506줄; 64자는 그 `.sha256` 파일과 보충 31 머리에). Declare 단계가 02:20에 쓴 판과 바이트가 같습니다 [실행 `cmp`, `RV31/r1/K8_PREDECLARATION_AMENDMENT_31_declare.md`와도 같음].
- 근거 [실행 sha]: 결정 기록 `SP/K9_1_J1_NOTES_20261013.md` = `09974cfc3e1412735ba6cf3228f4a2e4c08ad01294327d534290011b4a8042cc`(193줄, D-K9-58~61 :184-193), 보충 24 `d46db6dc…`·25 `4fd7b599…`·26 `8f835616…`·27 `4ce8b27a…`·28 `9881eb40…`·29 `4bd6dc8d…`·30 `ba556227…`와 각 `.sha256`, 고정점 24–30(보충 31 §0 값과 같음), `KB/GATES_K92B1_A30.md` `167e9e18…`, `KB/VERIFY_GATES_K92B1_r2.md` `5f7c1256…`, `KB/GATES_K92B1.md` `3f3a069a…`, `KB/k92t_pins.sha256` `38a2ce14…` 56/56 OK, `KB/a30_pins.sha256` `7afabd03…` 83/83 OK, 기대 고정 목록 133/133 OK, OUTK 보관 기록(`STOP_a30_post.json` `8fa75243…`, `judge/sealed_records.json` `517582ad…`, `judge/f.json` `04cfa2e0…`, `judge/jb.json` `f8a273ef…`, `jb/sa/unit_k92t.log` `ef8033f5…`, `steps.jsonl` 102줄 `1fdef906…` 등) = 보충 31 §0. `KB/LOG.md` 검토 시작 전 208,366 B = `a5341514…`.
- 데이터: **보충 31 적용 데이터 0개.** OUT31 없음, OUTK 마지막 수정 10-21 23:34:09, 10-21 23:42 뒤 바뀐 파일 OUTK 0·봉인 뿌리 0·OUT30 0, WT·그 관리 폴더 없음·`git worktree list`에 없음, LOG에 scan31·unit31 줄 0 [실행]. 검토 끝 `check31 --mode decl` 43점검 거짓 0 [실행 `RV31/out/check31_rv.json`]. GWT8 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` 커밋 6개), K8 브랜치 `b9734abe`, `status --porcelain` 0줄, 원격 k92 참조 0, 푸시 0 [실행].
- 이 검토에서 한 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. 실제 저장소 임시 작업 트리 0, b9734abe 시험 실행 0, 4c 시험 실행 0. 판정기·비교기를 실제 봉인 기록·jb_unit 로그에 부른 일 0. 무거운 일 둘(CAP 바이트 목록 `rv31_capman`, `check31 --mode decl` `rv31_check31`)은 `KI/launch.ps1`로 WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번에 하나. 쓴 곳: RV31, `TK/a31review/syn`(합성 봉인 뿌리, 만들고 지움; 빈 `TK/a31review`도 지움), SP의 보충 31·`_r1`·두 `.sha256`, 이 파일, `KB/LOG.md` 덧붙임, `OK2/logs/rv31_capman.txt`·`rv31_check31.txt`(WMI 표준 출력), `KI/wmi_launch_lines.txt`(launch.ps1이 두 줄 덧붙임). OUTK·봉인 뿌리·TREE·GWT8·저장소 `.git`·K8 브랜치·KI 코드·AD31·V4·동결본·런 폴더 쓰기 0. 끈 프로세스 0. 끝에 python·VISSIM 0.
- 블라인드: 봉인 시드(37/59/61/67)·codex 64cf 숫자 0. 봉인 뿌리 파일 내용 열람 0(메타데이터 `find -newermt` 개수만). 봉인 뿌리 밖 봉인 목록의 이름·검증 2차 개수·`jb_copies.json` `caps` 목록·`rjg4.json` 키 이름을 읽었고 LOG에 적었습니다(J·F 값 고정 뒤). jb_unit 로그 내용 열람 0.
- 디스크: C: 42.6 GB, D: 416.6 GB 여유 [실행 check31].

태그: [실행] 이번에 돌려서 확인 · [읽음] 문서·코드에서 확인 · [추론] 시험하지 않은 판단 · [계산] 산술.

---

## 1. 찾은 구멍과 고친 곳 (자세한 표는 보충 31 §12.1)

| # | 구멍 | 고침 |
|---|---|---|
| R1 | 새 s47 판별 규칙의 한계(seed 칸이 `'47'`이 아니면서 상대 경로에 s47 조각 없는 기록 — 폴더 `v3c3-s47`·`seed47`·`s47-run`, seed 47.0, JSON 오류, 다른 파일 이름)와 "실제 s47 기록을 놓치지 않음"의 근거가 없었음 | 합성 시험으로 한계를 적고, 실제 봉인 뿌리에서 닿지 않는 근거(검증 2차: seed 칸 134/134, `'31'` 42·`'43'` 47·`'47'` 45, 두 길 어긋남 0; 봉인 목록 이름에 새 함수만 → 45, 옛 → 134; 기록 쓰는 코드)와 개수 조건의 STOP 길 |
| R2 | 독립 검증 V2가 같은 규칙만 다시 셈 | V2에 seed 칸 값별 개수와 두 길 어긋남 0을 더함(STOP 늘리는 쪽) |
| R3 | 독립 검증 "첫 읽기 전 고정" 목록에 K9-2 쪽 jb_unit 로그가 빠짐 | 더함 |
| R4 | 기준 실행이 CAP(OUTK 안)를 읽기만 했는지 대조할 기준이 없었음 | 데이터 전 CAP 바이트 목록(위 표), V4가 실행 뒤 대조 |
| R5–R8 | GWT8·K8 보호 근거, pytest 뿌리 근거, 시간 상한 끝의 손자 프로세스, 훑기 범위 밖 `k91_record.json` 212개 | 근거·처리·공개 |

- 바꾸지 않은 것: 판정 정의·문턱·표본(scan31 PASS = rc 0·ok·나쁨 0·134/45/0; jb_unit 규칙 §3.2–3.3), 새 구동기·판정기·비교기·`dry_a31.py`·차이 파일·확인 출력·기대 고정 목록(§8). 고친 것은 보충 31의 글뿐입니다(R2·R4는 독립 검증 STOP 조건을 늘리는 쪽).

## 2. 고친 파일

| 파일 | Declare 판 | 고정 값 |
|---|---|---|
| `SP/K8_PREDECLARATION_AMENDMENT_31.md` | `8a76e210230b69c0…`(506줄) | 위 표(575줄; "[검토]" 글자 붙은 곳 + §12 더함) |

## 3. 다시 확인했고 문제없는 것 (자세히는 보충 31 §12.2)

1. 판정기 변경은 `_seed47_path` 한 함수뿐(`diff` 한 덩어리, 기반 사본 = 보충 30 판정기 바이트) [실행].
2. 새 함수: 진리표 22/22, 적대 경로 24/24, 합성 봉인 뿌리 11/5/3 기대대로; 실제 이름 134 → 45 [실행].
3. s31·s43 기록을 s47로 세지 않음(실제 이름에서 경로 길 45 = seed 47 개수, 어긋남 0), 세면 나쁨 ≥ 1 → STOP [실행·읽음].
4. 새 scan 데이터 0(파일 시각) [실행].
5. jb_unit 기준 실행: 쓰는 git 명령은 `worktree add --detach`(커밋 sha)·`worktree remove --force`(상수 WT 자리) 둘, 시험의 git은 읽기, 훅·LFS·export-ignore·심볼릭 링크·서브모듈 0, 최장 경로 237자; GWT8·K8 브랜치를 바꿀 길 없음 [읽음·실행]. 환경은 jb_unit과 트리에 묶인 값만 다름 [읽음].
6. G-K4 재계산 순서(사슬 PASS·G3 보고 뒤, 새 도구, 첫 읽기 전 LOG 고정, 보충 29 §5 규칙)와 `rjg4.json` 칸 이름 [읽음].
7. V-B 시작 조건(K92_GATES_PASS 뒤, VerifyVB, V-A·푸시 0) [읽음].

## 4. 메인 세션이 할 일·사용자에게 알릴 것 (막힘 아님)

1. 사용자 보고에 적을 것: (가) R1 — 새 규칙은 seed 칸 없음·다른 꼴 seed와 s47 조각 없는 폴더가 겹치는 기록을 못 보지만 실제 봉인 뿌리에는 그런 기록이 없음(seed 칸 134/134, 두 길 어긋남 0), 독립 검증 V2가 다시 셈; (나) R4 — 기준 실행 뒤 CAP가 그대로인지 V4가 이 검토의 기준 목록으로 봄; (다) §12.3-1 — 구동기 머리말의 "C1-C15"는 글 오류(점검은 C1–C14), 바이트 그대로; (라) 검토의 열람(봉인 목록 이름, 검증 2차 개수, `jb_copies.json`, `rjg4.json` 키 이름)과 `rv_idxnames.py`·`rv_capx.py`를 sha를 LOG에 적기 전에 돌린 일(공개).
2. 적용은 보충 31 §4.2 G0부터: 보충 31 sha = `.sha256` = 이 파일의 `8541ccb7…`(64자 위 표). 기대 고정 목록은 `KB/a31decl/a31_pins.expected.sha256`(`bf1ca001…`, 133/133). G1의 `KB/a31_pins.sha256`은 그 파일과 `cmp` 같아야 합니다. G2는 `powershell -NoProfile -File KI/launch.ps1 -Tag k92t31_chain -Script ..\a31decl\k92t31.py -ArgLine chain31` 하나뿐입니다.
3. 남은 미해결: 없음.

## 5. 검토 도구와 출력 (RV31 = `KB/a31review`; 읽기만 하는 점검·시험, 판정에 쓰지 않음)

| 파일 | sha256 |
|---|---|
| `rv_s47rule.py` / `out/rv_s47rule.json` (적대 경로 24, 진리표 22, 합성 봉인 뿌리 12기록; 합성만) | `b39ae21fb58bebd370f1ec3a4b0597ecb3e4661ade98ed04a68ecbc06be4bb96` / `2ebc5153986558f01d38249f1e02ef6210d8fe4626b517f1be5d23602bd68e0b` |
| `rv_idx31.py` / `out/rv_idx31.json` (봉인 목록 이름에 새·옛 함수; 개수만) | `83057a00500b449fc7ae074c4e6b94bd8c78096c7b97aae72908b90404aee449` / `e752e800fe02e8970be22a7644748299969b86831b3628b8528255215588a260` |
| `rv_idxnames.py` (record가 든 바닥 이름별 개수) | `e968718b6ced9941347175e4052dc7e93e8a76dc90ec8c9c72071193f0fccd86` |
| `rv_capman.py` / `out/cap_manifest.json` (CAP 바이트 목록, V4 기준) | `d74e5e2a1fe4b90009e10fb3eb853ce462c8ebff40ff8d8cf334452e17799596` / `d6691f48954d07dd2b3bbfe718e468fd59f3f6b7492060a2151d4d02e177e3a9` |
| `rv_capx.py` (CAP 목록 대 `jb_copies.json` `caps`: 같음 960·다름 0·없음 0) | `f34fc326df4a70a25b7951078d1168c4fd77a92194200001f140a50e3bbfb0ed` |
| `out/check31_rv.json` (검토 끝 `check31 --mode decl`, 43점검 거짓 0) | `cd2112fa182cf943350a24ca7a0ccd83667749b3131c402f8c953d793b7ad95d` |
| `sec12.md` (보충 31 §12 원고; 붙인 뒤 §12.2-8의 줄 번호 하나를 고침) | `98ca55ba2db4b9f80fb43248421f59131ef814ff2e5770facc241997d1441023` |
| `rv_fixcheck31.py` (구동기 자신의 `a31_sha()`와 C6 글자 대조를 이 파일·기대 고정 목록에; 결과 `a31_sha` = `8541ccb7…`, C6 같은 뜻 참·133줄·틀린 줄 0, Declare 판 64자 sha가 이 파일에 없음) | `233c060f30e95138790302efce90b7ef24772ed69e67c483bb90783df49b8c2e` |
| `r1/K8_PREDECLARATION_AMENDMENT_31_declare.md` (Declare 판 사본) | `8a76e210230b69c0…` |

- 공개: `rv_s47rule.py`는 합성 입력만 다루므로 sha를 LOG에 적기 전에 한 번 돌렸고, `rv_idxnames.py`·`rv_capx.py`는 쓴 바로 뒤 LOG 적기 전에 돌렸습니다(LOG에 적음). `rv_idx31.py`·`rv_capman.py`는 실제 자료에 돌리기 전에 sha를 LOG에 적었습니다.
