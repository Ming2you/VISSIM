# K9-2 묶음 1 관문 보고 — 보충 31 적용 (Gates A31, 2026-10-22) — 사슬 PASS: 봉인 뿌리 기록 훑기(scan31)·jb_unit 기준 대조(unit31)

- 상태: **사슬 PASS.** 보충 31 §4.2 순서(G0 → G1 → G2 사슬 하나 → G3)대로 했습니다. 사전 점검(check31) 45점검 거짓 0, 봉인 뿌리 기록 훑기(scan31) PASS, jb_unit 기준 대조(unit31) PASS, 스냅숏 셋 모두 SAME, STOP 파일 0입니다.
- scan31: 기록 134, s47로 셈 45, 나쁨 0, 자식 종료 코드 0, 보관 파일 둘 그대로 → 선언 조건(134/45/0)과 같음.
- unit31: b9734abe 임시 분리 작업 트리에서 4c 단위 시험 넷을 돌림(종료 코드 1, 128.3 s). 공통 시험 97, 결과 다름 0, 기준에만 있는 시험 0, K9-2에만 있는 시험 0, 해석 점검 INCOMPLETE 0. 통과가 아닌 공통 시험 2개는 이미 알려진 `ConfigFlagTests` 두 실패이고, 두 쪽 결과가 같습니다. 임시 작업 트리는 지웠고 GWT8·K8 브랜치는 그대로입니다.
- 이 보고는 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. 교통 성능 판정이 아닙니다.
- **아직 아닌 것**: K92_GATES_PASS는 아직 아닙니다. 보충 31 §4.4가 독립 검증 A31(§4.3 V1–V4, G-K4 plant 원자료 재계산 포함) PASS를 더 요구합니다. 이 단계는 그것을 하지 않았습니다.
- 표시: [실행] 이번에 돌리거나 계산함, [읽음] 문서·코드·기록에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.

## 줄임말 (처음 한 번)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. KI = `KB/impl`(구현 도우미, 바꾸지 않음). AD31 = `KB/a31decl`(보충 31 새 구동기·판정기·비교기). GA31 = `KB/a31apply`(이 단계의 기다림 도우미, 판정에 쓰지 않음).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. OUTK = `OK2/k92t`(판정 단계 출력, 보관; 이 단계에서 쓰지 않음). OUT30 = `OK2/a30`. **OUT31** = `OK2/a31`(이 단계 출력). SEALED = `OK2/sealed_s47`(봉인 뿌리). CAP = `OUTK/jb/sa/cap/k92t`(J-b 포착 뿌리). V4 = `D:/VISSIM-merge/k8_gates_out_v4`(K9-1 판정 산출, 읽기만).
- GWT8 = 커밋 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`. TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`. TREE = `TK/a27/k92t`(git archive K9-2-5 `e27ceac8`). **WT** = 임시 분리 작업 트리 `TK/a31_wt_b9734abe`(K8 머리 b9734abe; 이 단계 안에서 만들고 지움). UB = `OUT31/unit_base`(기준 실행 출력 뿌리).
- **scan31** = 봉인 뿌리 `k92_record.json` 훑기를 고친 s47 판별 규칙(보충 31 §2.2)으로 다시 한 것. **unit31** = jb_unit 기준 대조(보충 31 §3). **jb_unit** = J-b 안에서 TREE를 뿌리로 4c 단위 시험 넷을 돌린 pytest 실행(`OUTK/jb/sa/unit_k92t.log`, 종료 코드 1). **4c 단위 시험** = `diagnostics/sdmpc_n31_20260924/tests/`의 `test_stopline_approach.py`·`test_stopline_wiring.py`·`test_stopline_evidence.py`·`test_stopline_approach_captured.py`(K8-6 선언 시험).
- J·F 값 고정 = `OUTK/judge/f.json`(`04cfa2e0…`)과 `judge/jb.json`(`f8a273ef…`)의 sha256이 둘 다 `KB/LOG.md`에 있는 상태(보충 30 §4.5). K92_GATES_PASS = 보충 24 §6 :361을 보충 30 §8·보충 31 §4.4로 넓힌 모든 관문 PASS 상태.
- 시드는 망 접두어를 붙입니다(v3c3-s31 등). 봉인 시드 37/59/61/67은 열지 않았습니다.

## 보고서 머리에 옮겨 적는 공개 (보충 31 §4.2 끝: `GATES_K92B1_A30.md` 머리 공개 + 보충 31 §5·§9; 줄마다 줄여 옮김, 원문은 그 절)

`GATES_K92B1.md` 머리 1–6 [읽음 `GATES_K92B1_A30.md` 머리]:
1. W 값 5,209.8은 몫 가르기 결과를 본 뒤 고른 값입니다(D-K9-34).
2. F-3(좌회전)은 비블라인드 안전 문턱입니다. 설계 단계가 v3c3-s47 좌회전 자료를 읽었습니다.
3. G-K2·G-K4는 처음에 HARD만으로 판정했고, 보충 27–29로 결과 넷·"모든 차이"로 다시 판정했습니다. 다시 판정은 결과를 짐작하는 상태의 판정입니다.
4. G-K4 결정 W 4행은 RS 소스 sha 잎 하나만 좁게 허용했습니다(A28-W, D-K9-51).
5. G-K4 plant 4행의 원자료 재계산은 독립 검증기가 합니다(D-K9-55, D-K9-60). **이 단계도 하지 않았습니다**(보충 31 §4.3 V1 몫).
6. 기존 어댑터는 결정마다 봉인 시드·v3c3-s47 파일의 sha를 계산합니다(D-K9-44, 기록만).

보충 27 §8: K9-2-1·2 관문의 G-K2 9칸은 처음에 HARD만으로 PASS였고 전체 결과는 9칸 모두 보류였습니다. G-K4 결정 행도 HARD 숫자만 봤습니다. 규칙은 결과를 본 뒤 정했습니다. G-K2·G-K4 결과는 RJ-G2·RJ-G4로 대신합니다.
보충 27 §13: (1) 데이터 뒤 규칙, (2) G-K4 W 예측 STOP은 사용자 몫, (3) (b) S3 예외, (4) G-K4는 다시 재생하지 않음, (5) R-old가 보이는 범위, (6) CR 범위는 L 10파일, (7) 묶음 폴더 목록 닫힘, (8) U4 바탕은 K9-2-3, (9) 개발 시험은 TKD 사본에서만, (10) D-K9-44, (11) 앞 보충 한계 그대로, (12) N이 보지 못하는 것, (13) G-K4 plant 행은 A 대 C 트리, (14) keyed 증거 핀은 구동기 점검, (15) R-old 허용 수 규칙은 허용 수를 본 뒤 고침.
보충 28 §9: (1) A28-W는 결과를 짐작하는 상태의 허용, (2) 두 RS 바이트는 다름(`70cca680…` 대 `1ab45c03…`), (3) A28-W는 구동기 층, (4) RJ-G2 목록 sha는 옛 트리 keyed, (5) 명령줄 길이 점검, (6) R0 다시 봄, (7) 로그 이름, (8) 확인 범위, (9) 입력 파일 경로에 `sealed_s47` 글자 8번, (10) D-K9-44, (11) 앞 한계 그대로, (12) `input_text` 점검 범위, (13) `child()` OSError 처리, (14) `a28w.py` 바이트 다르면 STOP, (15) 점검 10의 약한 변이, (16) `judge_row` 예외는 STOP 쪽, (17) 허용 집합 안 차이는 W 행에서도 허용, (18) Declare LOG 시각 오기.
보충 29 §11: (1) 데이터를 본 뒤의 정의, (2) N 글 충돌과 선택, (3) 기존 시험 두 파일 고침, (4) A_K92는 옛 뿌리 필수, (5) 무리 K 옛 뿌리 = 동결본, (6) 다시 비교는 "같은 보고" 요구, (7) plant 4행 재계산은 J·F 값 고정 뒤, (8) A28-W `strip29`, (9) 망가뜨림 58개만, (10) D-K9-44, (11) TKD9 시험 사본, (12) K9-2-5 관문 트리 넷, (13) 입력 핀, (14) 앞 한계 그대로, (15) A_K92-M 마디, (16) 증거 뿌리 해석, (17) 못 잡는 망가뜨림 넷, (18) 판정 자식이 부르는 파일 10개, (19) `amendment29_sha()`는 고정점 글 안 sha만 봄, (20) `$` 정규식.
보충 30 §10: (1) 데이터를 본 뒤의 보충, (2) 지속성 보고 21/22(T=1,050 측정 불가(T_FROM=900)), (3) 새 점검 셋은 STOP을 늘리는 쪽, (4) F 잡 로그 `grep -c` 한 번 = "엶", (5) J-0 글자 그대로 59/61(T=1·150은 두 팔 같은 실패로 셈), (6) 검증 도구 고정 시점과 vg_ja → vg_ja2 사후 수정, (7) VerifyGates 대표 잡 다시 돌리기 DIFFERENT 기록, (8) TREE 실행 캐시, (9) D-K9-44 계속, (10) 판정기 둘, (11) STOP 파일 둘, (12) OUTK 목록에 s47 라벨 이름, (13) 4c 단위 시험은 선언 시험, (14) 앞 한계 그대로, (15) 봉인 뿌리 맨 위가 여섯, (16) `OUTK/f_*/replays/s47/`의 재생 상태 공개, (17) `f_vref.log` 끝 300 B 실패 진단 열람.
`GATES_K92B1_A30.md` N1–N7: N1 `jb_unit` rc=1(시험 2개), N2 post30 STOP 진단으로 봉인 `k92_record.json` 134개를 메모리에서 읽음(J·F 값 고정 뒤), N3 J-b 중 `unit_k92t.log`·`unit_k91t.log` 끝 부분 열람(14:25), N4 J·F 값 고정 전 읽은 파일 셋(값 0), N5 LOG 시각 오기 바로잡음, N6 s33 없음·끝 확인 s34, N7 `GATES_K92B1.md` §8 덧붙임.

보충 31 §5 (P1–P6):
- P1 데이터 뒤 판정기 고침(D-K9-58): `_seed47_path` 한 함수를 보충 30 사후 데이터를 본 뒤 고쳤습니다(보충 24 S-K12의 예외, 사용자 결정). 결과는 실패 진단·검증 2차로 이미 알려졌습니다(블라인드 아님). 개수 조건 134/45/0도 그 자료를 본 뒤 적었습니다.
- P2 보충 30 §5.3 바꿈(D-K9-59): "모든 단계 실행 rc≠0 → STOP"을 jb_unit 한 줄에 한해 보충 31 §3 규칙으로 대신합니다. jb_unit 판정은 J-b 값 뒤입니다.
- P3 메인 세션 `grep -rl`(10-22, J·F 값 고정 뒤, 파일 이름만 출력, 내용 0, 그때 LOG 없음). 봉인 뿌리도 훑었을 수 있습니다.
- P4 검증 2차 공개 수용(D-K9-61): 고정 전 노출, `vg3t` → `vg3r` 이름 바꿈, M2·M3 VISSIM 쪽 FZP 재계수 없음. `OK2/vg3r/jbcopy`(4.1 GB)는 K9-2 끝까지 보관.
- P5 Declare 단계는 OUTK 파일 내용을 열지 않음(sha만), 봉인 뿌리는 맨 위 이름·`k92t/logs` 이름·크기만.
- P6 결과 짐작: scan31 개수와 jb_unit K9-2 쪽 요약·b9734abe 재현(메인 세션, 참고)은 이미 알려졌습니다. 이번 판정은 그것을 고정 도구로 다시 낸 것입니다.

보충 31 §9 (1–16): (1) 데이터를 본 뒤의 보충, (2) 판정기 예외는 `_seed47_path` 하나, (3) scan31은 블라인드 점검이 아님, (4) jb_unit 판정은 J-b 값 뒤, (5) CR 꼴 10파일(GWT8 LF, archive CRLF; 새 WT는 archive와 같을 것으로 봄 — **이번 실행에서 WT 대 b9_ref 차이 0으로 확인**, §3), (6) 비교 범위(건너뜀 까닭·첫 `E` 줄 뒤 메시지·하위 시험별 통과는 비교하지 않음; 무작위 임시 이름 메시지는 다르게 셈), (7) 포착 시험은 K9-2 트리가 만든 J-b 포착을 b9734abe 코드로 읽음("같은 입력, 다른 코드"), (8) 메인 세션의 b9734abe 실행(10-22)은 참고, (9) `git worktree` 관리 폴더는 만들고 같은 단계 안에서 지움, (10) D-K9-44 계속, (11) 설정 정합(`make_config_n31.py`·`config_n31_v2.json`)은 묶음 2 목록, (12) `grep -rl`(P3)·검증 2차 공개(P4) 수용, (13) 임시 트리 보관(`OK2/vg3r/jbcopy` 등), (14) 앞 보충 한계·`GATES_K92B1_A30.md` N1–N7 그대로, (15) 훑기는 이름이 정확히 `k92_record.json`인 파일만 읽음(봉인 뿌리의 `k91_record.json` 212개는 VISSIM 칸 없음), (16) seed 칸·경로 두 길의 한계는 실제 봉인 뿌리에서 닿지 않음(독립 검증 V2가 다시 셈).

이 단계에서 새로 생긴 공개:
- A31-N1. LOG 순서: 구동기의 첫 자동 줄(02:58:24 사전 점검)이 내 "G2 발사" 줄(발사 02:58:19 뒤 몇 초 뒤에 씀)보다 위에 있습니다. 줄 안의 시각은 맞습니다.
- A31-N2. G3 끝 대조(03:07:18, 03:15:34 다시; 둘 다 133/133 OK) 뒤에 `KB/GATES_K92B1.md`에 §9를 덧붙였습니다. 이 파일은 `KB/a31_pins.sha256`의 127줄(`3f3a069a…`)입니다. 고정 창(G1 → G3 끝 대조)이 닫힌 뒤의 바꿈이지만, 그 뒤 `sha256sum -c KB/a31_pins.sha256`은 127줄 하나가 다르게 나옵니다(덧붙임 뒤 sha는 `KB/LOG.md`의 Gates A31 G3 항목에 적음; 이 보고와 그 절이 서로의 sha를 담지 않게 하려는 것). 보충 30 단계(N7)와 같은 덧붙임입니다.
- A31-N3. 끝 확인으로 메타데이터 `find -newermt` 개수를 셌습니다: OUTK·SEALED·OUT30(10-21 23:42 뒤) 0·0·0, TREE·`TK/b9_ref`·V4(10-22 02:57 뒤) 0·0·0. SEALED는 개수만 셌고 이름·내용 출력 0입니다. OK2에서 OUT31 밖의 02:57 뒤 바뀐 것은 OK2 폴더 자신, `a31`, `logs/k92t31_chain.txt`, `snap/s35·s36·s37` 이름만 출력했습니다.
- A31-N4. 이 보고를 쓰려고 사슬이 끝난 뒤 OUT31 기록(`check31.json`, `scan31.json`, `sealed_records_a31.json`, `unit31.json`, `unit31_run.json`, `unit_judge.json`, `chain31.json`, `stages/*.json`, `driver31.log`, `logs/scan31.log`·`unit31_judge.log`·`unit31_wt_add.log`, `unit_base/unit_b9734abe.meta.txt`)과 `OK2/logs/k92t31_chain.txt`를 읽었습니다. 두 pytest 로그(`UB/unit_b9734abe.log`, `OUTK/jb/sa/unit_k92t.log`)는 열지 않았습니다(sha·크기만). 독립 검증 A31은 자기 도구 sha를 LOG에 적은 뒤에만 이 자료를 처음 읽어야 합니다(보충 31 §4.3) — 이 단계의 열람은 그 규칙의 대상(독립 검증 단계)이 아닙니다.
- A31-N5. `sealed_records_a31.json`은 판정기 출력입니다(개수·참거짓·빈 `bad` 목록·봉인 밖 부분 `notes` 0). 봉인 뿌리 파일이 아닙니다. 봉인 뿌리 기록은 판정기 자식이 메모리에서만 읽었고 구동기가 열람 줄을 LOG에 썼습니다(02:59:22).
- A31-N6. 기다림 도우미 `GA31/poll31.py`(`f6e53fd3…`)는 프로세스 표, OUT31 단계·STOP 파일 이름, `steps31.jsonl`의 name·rc·sec·VISSIM 칸만 봤습니다. 로그 걸러 읽기 0. 그 출력의 프로세스 목록에는 도우미 자신의 python도 보입니다.

## 한눈에

| 관문·단계 | 정의 (요약) | 값 | 문턱 | 결과 |
|---|---|---|---|---|
| G0 사전 확인 | 보충 31 §4.2 G0 | 보충 31 `8541ccb7…` = `.sha256` = 고정점 `605ccbd2…` 안 64자(1회); 결정 기록 193줄 `09974cfc…`; 보충·고정점 24–30 = §0; `k92t_pins` 56/56; `a30_pins` 83/83; 기대 목록 `bf1ca001…` 133/133; GWT8 상태(C4); python·VISSIM 0; C: 42.6 GB, D: 416.6 GB | 모두 참 | PASS |
| G1 고정 | 기대 목록 → `KB/a31_pins.sha256` | `cmp` 같음, `bf1ca001…`, 133/133 OK·종료 0 | 같음·OK | PASS |
| check31 (apply) | 보충 31 §4.1 C1–C14 (45점검) | 거짓 0; C6 133줄 틀림 0; C11 블롭 넷 같음 | 거짓 0 | PASS |
| 스냅숏 s35 | S-K11, s02 대비 | SAME | SAME | PASS |
| scan31 | 보충 31 §2.4 | 자식 rc 0, `ok` 참, `n_bad` 0, {files 134, s47 45, bad 0, ran 참}, 보관 두 파일 sha 그대로 | rc 0·ok·134/45/0·보관 그대로 | PASS |
| 스냅숏 s36 | S-K11 | SAME | SAME | PASS |
| unit31 작업 트리 만들기 | 보충 31 §3.4 1–3 | `worktree add --detach` rc 0(31.6 s); WT head = b9734abe, status 0줄; GWT8·K8 그대로 | 모두 참 | 참 |
| unit31 보고 항목 | §3.4 4·6 | WT 대 `TK/b9_ref`: 바뀜 0, WT에만 0, b9_ref에만 0; 실행 뒤 WT status(추적 밖 포함) 0줄 | 보고만 | 보고 |
| unit31 기준 실행 | §3.4 5 | `run_pytest_bn.py -v` 넷, rc 1, 128.3 s(상한 1,800 s) | 끝남 | 참 |
| unit31 작업 트리 지우기 | §3.4 7, S-K48 | `worktree remove --force` rc 0; WT 폴더·관리 폴더 없음, 목록에 없음, GWT8·K8 그대로 | 모두 참 | 참 |
| unit31 판정 (jb_unit 줄; **보충 31 §3 규칙, 보충 30 §5.3을 이 줄에 한해 대신함**) | §3.2–3.3 | 공통 97, 다름 0, 기준에만 0, K9-2에만 0, 해석 INCOMPLETE 0, rc 1/1, `rootdir` 참/참, `platform` 같음; 통과 아닌 공통 2(같은 결과) | (가)(나)(다) 참, INCOMPLETE 0 | PASS |
| 스냅숏 s37 | S-K11 | SAME | SAME | PASS |
| G2 사슬 | 보충 31 §4.2 G2 | `chain31.json` 있음, `stages/unit31.json` `ok` 참, `STOP_a31_*` 0; `steps31.jsonl` 11줄 VISSIM 전·후 모두 0 | 모두 참 | PASS |
| G3 끝 대조 | 보충 31 §4.2 G3 | `a31_pins` 133/133 OK·종료 0(03:07:18, 덧붙임 직전 03:15:34 다시); GWT8 head `e27ceac8`, status 0줄, 6커밋, K8 `b9734abe`, 원격 k92 0, 푸시 0, WT 없음; python·VISSIM 0 | 모두 참 | PASS |
| 독립 검증 A31 (V1–V4, G-K4 plant 재계산 포함) | 보충 31 §4.3 | 이 단계 밖 | – | 하지 않음 |

## 1. 실행 [실행]

- G0 02:55–02:57, G1 02:57(`KB/a31_pins.sha256` `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e`, 133줄; 구동기 `63b5aa22…`·판정기 `9dfc0b20…`·비교기 `a1d82bff…` 고정, LOG 02:57 항목).
- G2: 발사 전 `sha256sum -c KB/a31_pins.sha256` 133/133 OK(02:58:13). `KI/launch.ps1 -Tag k92t31_chain -Script ..\a31decl\k92t31.py -ArgLine chain31` → 02:58:19, ReturnValue 0, PID 18880(cmd.exe) → python PID 11496, BelowNormal(16384), `PYTHONHASHSEED=0`, `python -B`, 발사 때 python 0·VISSIM 0. 표준 출력 `OK2/logs/k92t31_chain.txt`(816 B; 단계 이름·rc·초·판정만).
- 기다림: `GA31/poll31.py wait` 세 번(60 s, 345 s, 60 s; 각 540 s 이하).
- 단계 시각: check31 끝 02:58:24, s35 02:58:25–02:59:22 SAME, scan31 02:59:22–02:59:23, s36 02:59:24–03:00:21 SAME, WT 만들기 03:00:22–03:00:54, WT 대 b9_ref 보고 03:00:54–03:03:08(약 134 s), 기준 pytest 03:03:08–03:05:16(128.3 s), WT 지우기 03:05:17–03:05:20(3.1 s), 판정 03:05:21–03:05:22, s37 03:05:22–03:06:22 SAME, 사슬 끝 03:06:23. 합 약 8분.
- `OUT31/steps31.jsonl` 11줄: rc≠0은 `unit31_pytest` rc 1 하나(기준 실행의 pytest 종료 코드; 판정 입력). 나머지 10줄 rc 0. VISSIM 전·후 모두 0/0.

## 2. scan31 — 봉인 뿌리 기록 훑기 (D-K9-58) [실행]

- 명령(구동기 자식, 작업 폴더 AD31, BelowNormal): `python -B AD31/k92t31_judge.py sealedscan --dest OUT31/sealed_records_a31.json`. 자식 rc 0(1.1 s). 표준 출력 한 줄 "ok=True files=134 s47=45 bad=0".
- 출력 `OUT31/sealed_records_a31.json` `47f91364ed00325b40d15ebb9dca464193b2ac093c569c2498b42398b90fa4fa`: `ok` 참, `n_bad` 0, `bad` [], `sealed_records` = {files 134, s47 45, bad 0, ran 참}.
- 구동기 기록 `OUT31/scan31.json` `98de5508c876444daa643afe4055323368ccf8309fb3644a9b7c51673b5d95f1`: 판정 PASS, 기대 개수 = 실제 개수, 보관 파일 그대로 참(`OUTK/STOP_a30_post.json` `8fa75243…`, `OUTK/judge/sealed_records.json` `517582ad…` 바이트 같음).
- 열람 줄: 구동기가 실행 직전 LOG에 자동으로 씀(02:59:22; 파일 = `OK2/sealed_s47/**/k92_record.json`의 seed·vissim·vissim_reason 칸, 판정기 메모리 안).
- 보충 30 판정(134/134/89)과의 차이는 `_seed47_path` 한 함수뿐입니다(보충 31 §2.3). 개수 134/45/0은 이미 알려진 값을 고정 도구로 다시 낸 것입니다(P1·P6).

## 3. unit31 — jb_unit 기준 대조 (D-K9-59) [실행]

- **작업 트리** (`OUT31/unit31_run.json` `73e2984d449c8e37215ed3e9b7b76cda135a9fd5a527293e5025870c825c42bb`):
  - 만들기: `git -C GWT8 worktree add --detach D:/VISSIM-merge/k8_gate_trees/k92b1/a31_wt_b9734abe b9734abe1c83f95c9cec5fca5e42b7b18cd45991` rc 0 (파일 10,548개 꺼냄, "HEAD is now at b9734abe K8-10: …"). WT head = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, status 0줄, git 폴더 `D:/VISSIM-merge/repo/.git/worktrees/a31_wt_b9734abe`.
  - 보고 항목 WT 대 `TK/b9_ref`(git archive b9734abe, `b9_ref.build.json` `cace6ada…`): 바뀜 0, WT에만 0(`.git` 뺌), b9_ref에만 0. 보충 31 §3.6-1의 [추론] "새 작업 트리는 archive와 같은 줄바꿈"이 이번 실행에서 실제로 맞았습니다.
  - 실행 뒤 WT `git status --porcelain --untracked-files=all` 0줄. `UB/tmp`는 빈 폴더로 남았습니다(시험이 자기 임시 폴더를 지운 것으로 봄 [추론]).
  - 지우기: `git -C GWT8 worktree remove --force D:/…/a31_wt_b9734abe` rc 0. 뒤에 WT 폴더 없음, 관리 폴더 없음, `git worktree list`에 없음, GWT8 head `e27ceac8`·브랜치 `claude/k92-b1-20261016`·K8 `b9734abe`·status 0줄 = 앞과 같음(`wt_removed_and_state_same` 참). `git worktree prune` 0.
- **기준 실행 환경** [실행 기록]: 작업 폴더·`K8G_ROOT` = WT, `K8G_OUT` = UB, `TMP`·`TEMP` = `UB/tmp`, `GIT_DIR` = WT의 git 폴더, `K8_SA_CAPTURE_ROOT` = CAP(J-b 포착, 읽기만), `K8_SA_BASE_REV` = `ec063ffa`, `NUMBA_NUM_THREADS` = 1, `PYTHONHASHSEED` = 0, `PYTHONDONTWRITEBYTECODE` = 1, `PYTHONUTF8` = 1. 명령 `python -B SP/k8b_impl/run_pytest_bn.py -v <넷>`(발사기 `fe4451e4…`). 환경 기록 `UB/unit_b9734abe.meta.txt` `4673c20d…`.
- **기준 로그** `UB/unit_b9734abe.log` 20,922 B, `e2aaf860c26b44615f1f1a9602f3f31fd8c59b897ce8d13ad859a5d327c46781`(내용은 이 단계가 열지 않음). K9-2 쪽 jb_unit 로그 `OUTK/jb/sa/unit_k92t.log` 20,915 B, `ef8033f5…`(보관 값 그대로).
- **판정** `OUT31/unit_judge.json` `b7e9b64901ecd16a0d89a890b850358bae9708eba0e6ef2f392617a7f29cdea5`(비교기 `k92t31_unit.py` rc 0, 0.7 s):

| 항목 | 기준(b9734abe, WT) | K9-2(e27ceac8, TREE) |
|---|---|---|
| 종료 코드 | 1 | 1 |
| 수집(`collected`) | 97 | 97 |
| 최종 줄 개수 | failed 2, passed 95, subtests passed 92 | failed 2, passed 95, subtests passed 92 |
| 결과 낱말 | PASSED 95, FAILED 2, ERROR·SKIPPED·XFAIL·XPASS 0 | 같음 |
| `rootdir` = 자기 트리 뿌리 | 참 | 참 |
| 해석 점검 P1–P10 INCOMPLETE | 0 | 0 |

  - 두 로그 `platform` 줄 같음. 공통 시험 97, 결과 다름 0, 기준에만 0, K9-2에만 0(그래서 "K9-2에 새로 생긴 시험은 모두 통과" 조건은 빈 집합으로 참), K9-2 쪽 새 시험 나쁨 0 → 판정 **PASS**.
  - 통과가 아닌 공통 시험 2개(보고): `test_stopline_wiring.py::ConfigFlagTests::test_arms_add_exactly_the_key`, `::test_default_output_is_byte_identical`. 두 쪽 모두 행 결과 `['FAILED']`, 실패 항목 `FAILED`·꼬리표 없음·첫 `E` 줄 = 바이트 비교 `AssertionError`(줄인 repr: 왼쪽 `"_canonical"` 쪽, 오른쪽 `"stopline_approach"` 쪽)로 같음. 두 시험은 `make_config_n31.build()` 바이트가 트리의 `config_n31_v2.json`과 같은지 봅니다 [읽음 보충 31 §3.1]. 이 결과는 K8 머리 b9734abe에서도 같으므로 K9-2 커밋이 만든 실패가 아닙니다 [실행 비교; 원인 해석은 결정 기록 D-K9-59의 "K8-7·K8-10 손 편집"을 따름 — 추론]. 설정 정합 고침은 묶음 2 목록입니다(코드 변경 0).
- 구동기 기록 `OUT31/unit31.json` `235911035be67445915e87aad2d4fc87dc560e663a846c2f09867667606f7e7e`, 단계 기록 `OUT31/stages/unit31.json` `ok` 참.

## 4. G3 끝 대조 [실행]

- `sha256sum -c KB/a31_pins.sha256` 133/133 OK·종료 0(03:07:18; `GATES_K92B1.md` 덧붙임 직전 03:15:34에 다시 133/133 OK, LOG). `KB/k92t_pins.sha256` 56/56, `KB/a30_pins.sha256` 83/83 OK. 목록 101–118줄이 OUTK 보관 기록·OUT30·`k92t30_chain.txt`를 덮으므로 이 단계가 그 파일들을 바꾸지 않았음도 같이 봄.
- GWT8: head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`, 브랜치 `claude/k92-b1-20261016`, status 0줄, `b9734abe..HEAD` 6커밋, K8 브랜치 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, 원격 k92 참조 0, 푸시 0, 지역 브랜치 이름에 a31 0. `git worktree list` 23개(앞과 같음, a31 0), 관리 폴더 `repo/.git/worktrees` 22개(a31 없음), `TK/a31_wt_b9734abe` 없음.
- 메타데이터 개수(A31-N3): OUTK·SEALED·OUT30 0·0·0, TREE·b9_ref·V4 0·0·0.
- 프로세스: python·VISSIM·cscript·wscript 0(03:11:39). 남은 python 0이라 PID 보고할 것 없음(보충 31 §3.6-8). C: 42.6 GB, D: 416.5 GB.

## 5. 다음 (보충 31 §4.3–4.4, D-K9-60)

- 독립 검증 A31: 적용 단계와 다른 단계가 **새 도구**(검증 2차 도구·하네스·k92t 구동기·판정기·`k92t31_unit.py` import 0)를 sha를 LOG에 적은 뒤에만 자료를 처음 읽고 V1–V4를 합니다. V1 = G-K4 plant 원자료 재계산(보충 29 §5, 4행, `rjg4.json` `246f28aa…`와 같아야 함), V2 = 봉인 훑기 다시 셈(134/45/0 + seed 칸 분포 `{'31': 42, '43': 47, '47': 45}` + 두 길 어긋남 0), V3 = jb_unit 판정 다시 셈(두 pytest 로그 → `unit_judge.json`과 같음), V4 = 보관 그대로(OUTK 26·OUT30·`k92t30_chain.txt` sha, 봉인 뿌리 맨 위 여섯, WT 없음, K8·GWT8, CAP 바이트 = `KB/a31review/out/cap_manifest.json`). V4의 GWT8·보관 대조는 `KB/GATES_K92B1.md`를 보지 않습니다 [읽음 §4.3]. 다만 `KB/a31_pins.sha256`을 다시 대조하는 쪽은 127줄 바꿈(A31-N2)을 만납니다.
- 그 뒤 K92_GATES_PASS면 V-B(보충 24 §14.1·27 §6.2·29 §6.2) → VerifyVB. V-A·푸시는 그 뒤 사용자 결정입니다(S-K13). 이 단계에서 V-A 행동 0, 푸시 0.

## 6. 지킨 것 [실행]

- VISSIM·COM·러너·동결·결정 재생·plant 잡 0. `steps31.jsonl` VISSIM 칸 11줄 모두 0/0. 무거운 일은 사슬 하나(WMI 분리, BelowNormal, `PYTHONHASHSEED=0`, `python -B`), 한 번에 하나. 기다림 한 번에 540 s 이하.
- 실제 저장소에 쓴 git 명령은 구동기의 `worktree add --detach`(커밋 sha)·`worktree remove --force`(상수 WT 자리) 둘뿐입니다. 내 git 호출은 `--no-optional-locks` 읽기뿐. 커밋·브랜치·푸시 0. K8 브랜치·GWT8 작업 파일 바꿈 0.
- 쓰기: OUT31, `OK2/logs/k92t31_chain.txt`, `OK2/snap/s35–s37`, WT(만들고 지움)와 그 관리 폴더(만들고 지움), `KB/a31_pins.sha256`(G1), `GA31/poll31.py`, `KI/wmi_launch_lines.txt`(launch.ps1이 한 줄 덧붙임), 이 보고와 사본, `KB/GATES_K92B1.md` §9 덧붙임과 사본 `OK2/GATES_K92B1.md`, `KB/LOG.md` 덧붙임. OUTK·SEALED·TREE·OUT30·V4·동결본·런 폴더 쓰기 0(개수 0, 고정 목록 OK).
- 판정 정의·문턱·표본·구동기·판정기·비교기 바이트 바꿈 0. 기반·보충 30 구동기 명령 0(S-K49).
- 봉인 시드 37/59/61/67 열지 않음. codex 64cf 숫자 0. 봉인 뿌리 파일 내용은 scan31 판정기 자식만 메모리에서 읽음(LOG 열람 줄). v3c3-s47 결과 값 열람 0. 두 pytest 로그 내용 열람 0.
- 금지 시험 0. 돌린 시험은 4c 선언 시험 넷(WT에서 한 번)뿐.
- 내 PID만 썼고 끈 프로세스 0. 끝에 python·VISSIM 0.

## 7. 파일

| 파일 | sha256 |
|---|---|
| `KB/a31_pins.sha256` (G1, 133줄) | `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e` |
| `OUT31/check31.json` (45점검 거짓 0) | `007d316f74d93ab25c559528885d9796d4249f54b346d42155b90c981675438f` |
| `OUT31/sealed_records_a31.json` (299 B) | `47f91364ed00325b40d15ebb9dca464193b2ac093c569c2498b42398b90fa4fa` |
| `OUT31/scan31.json` | `98de5508c876444daa643afe4055323368ccf8309fb3644a9b7c51673b5d95f1` |
| `OUT31/unit31_run.json` | `73e2984d449c8e37215ed3e9b7b76cda135a9fd5a527293e5025870c825c42bb` |
| `OUT31/unit_base/unit_b9734abe.log` (20,922 B, 내용 열지 않음) / `.meta.txt` | `e2aaf860c26b44615f1f1a9602f3f31fd8c59b897ce8d13ad859a5d327c46781` / `4673c20da1cee0ed7154e9bba4f12dbd40cdd9c79bd35612b7f451a49fdfc4c2` |
| `OUT31/unit_judge.json` (1,997 B) | `b7e9b64901ecd16a0d89a890b850358bae9708eba0e6ef2f392617a7f29cdea5` |
| `OUT31/unit31.json` | `235911035be67445915e87aad2d4fc87dc560e663a846c2f09867667606f7e7e` |
| `OUT31/chain31.json` | `5ca6c42857395650ceaa2613524d3bec24d5eec3b3ed9243972bbb3ee2d8238d` |
| `OUT31/stages/check31.json` / `scan31.json` / `unit31.json` | `6bbe53e717d1cf4f9da14c4c60c102e26a5d2a6d5cfb9685c4453b1f79864764` / `1ba218d43985ed1725c7ef77dc5d30899c32b201c57f44b25d75395da2b2b391` / `dfe864386c21012a0a339fdd710d99b97664b3c398afd0085d6884f9e4457e87` |
| `OUT31/steps31.jsonl` (11줄) / `OUT31/driver31.log` | `c8ed15619a3b8a996c3d9aa0b75732998dcb4e1e5cd276516f7fc1b4116b38ac` / `a24a185556227e4c833dd3d8afb37b795581393c20e68c78d1da89eaee14eff0` |
| `OUT31/logs/scan31.log` / `unit31_judge.log` / `unit31_wt_add.log` / `unit31_wt_remove.log`(0 B) | `23758d049753c913c9508300eea761dcda2cbe6aefcaaf100d817b0d6d4e63e1` / `2b3d44cda68cd4e5ee1bf1fe0d2f4a24bb352ea9ce02c54b5302f575d20ce6ce` / `9a73f858d9a5211b1159a770482c6c33412bbc9d75d3187f8ca57f6d8c6b723a` / `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `OK2/logs/k92t31_chain.txt` (816 B) | `4464ba8f5d2d7a3e2829259d7ea4f8f8392895e5dd8778ba44824ab729754382` |
| `OK2/snap/s35_a31_check.json` / `s36_a31_scan.json` / `s37_a31_unit.json` (모두 s02 대비 SAME) | `12eb59472c21b12419de99c530a7b2c7130fecf180daa68d68bdacbf508b2b14` / `1140517122963ebfa773821c391addcc6e7572dcedf0af8830b6b797403dc9a8` / `23dccfbee7523a36e01ebc90fe69962c26e2a64bba1cc5bef26318106b6dc46b` |
| 보관 그대로: `OUTK/STOP_a30_post.json` / `OUTK/judge/sealed_records.json` / `OUTK/jb/sa/unit_k92t.log` | `8fa7524342517c020715aa26757f38a54473cdcf30cdd1d18d9b5414dcf8e18e` / `517582ad15adc98d936199cc9d4c1e9e9c9cc6bbc3d359722b4d7a06941d6eb5` / `ef8033f54eb342c3431cdf2f756bce6ecaaab3832e90babff6150136466dc3eb` |
| 고정 도구: `AD31/k92t31.py` / `k92t31_judge.py` / `k92t31_unit.py` | `63b5aa229eeaf013f2136a838cf9e5be163a087771fc3a71ea3202b0ad12b53d` / `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c` / `a1d82bffb71660361b07b19a823c1ff79286d2add90a0a58fdda8376cc03c6e2` |
| `GA31/poll31.py` (판정에 쓰지 않음) | `f6e53fd3ba8b2db7150148431d7ae1f8915e0b596adc8e3f4ca90a40af08ac04` |
| 이 보고서 사본 | `OK2/GATES_K92B1_A31.md` (같은 바이트) |
