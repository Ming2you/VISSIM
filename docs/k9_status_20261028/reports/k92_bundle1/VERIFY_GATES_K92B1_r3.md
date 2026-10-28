# K9-2 묶음 1 독립 검증 3차 (VerifyGates 3 = 보충 31 독립 검증 A31, D-K9-60, 2026-10-22)

- 검증 대상: 보충 31 적용 보고 `KB/GATES_K92B1_A31.md`(sha256 `e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885`)와 그 출력 `OUT31`, 그리고 G-K4 기록 `OK2/a27/judge/rjg4.json`(`246f28aa…`).
- **결과: PASS.** 보충 31 §4.3의 V1–V4 넷을 새 도구로 다시 냈고, 넷 모두 기록과 같고 통과 조건을 채웁니다 [실행 `VG4/out/vg4_result.json` `/verdict` = PASS, `/oks` 7개 모두 참].
  - V1 G-K4 plant 원자료 재계산: 4행 모두 PASS, 파일별(`summary.json`·`k92_record.json`) 모두 PASS. 기록 `rjg4.json`의 행 판정·파일 판정과 같음.
  - V2 봉인 뿌리 기록 훑기 다시 셈: 기록 134, s47 45, 나쁨 0. seed 칸 분포 `{'31': 42, '43': 47, '47': 45}`, 두 길 어긋남 0. `OUT31/scan31.json`·`sealed_records_a31.json`과 같음.
  - V3 jb_unit 판정 다시 셈: PASS. 공통 97, 다름 0, 한쪽에만 0/0, 통과 아닌 공통 2(`ConfigFlagTests` 두 실패, 두 쪽 같음). `OUT31/unit_judge.json`과 13항목 모두 같음.
  - V4 보관 그대로: OUTK 26·OUT30 2·`k92t30_chain.txt` sha 같음, OUTK 목록·봉인 맨 위 여섯·WT 없음·git 상태 참, CAP 3,944파일 바이트가 기준 목록과 같음.
- 이 보고는 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. 교통 성능 판정이 아닙니다.
- 표시: [실행] 이번에 내가 돌리거나 계산함, [읽음] 문서·코드·기록에서 확인, [추론] 시험하지 않은 판단.

## 줄임말 (처음 한 번)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. **VG4** = `KB/vgates4`(이 검증의 도구·출력, 새 폴더). KI = `KB/impl`(바꾸지 않음).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. OUTK = `OK2/k92t`(판정 단계 출력, 보관). OUT30 = `OK2/a30`. OUT31 = `OK2/a31`(보충 31 적용 출력). SEALED = `OK2/sealed_s47`(봉인 뿌리). CAP = `OUTK/jb/sa/cap/k92t`(J-b 포착 뿌리). UB = `OUT31/unit_base`(기준 실행 출력).
- TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`. TREE = `TK/a27/k92t`(git archive K9-2-5 `e27ceac8`). WT = 임시 분리 작업 트리 `TK/a31_wt_b9734abe`(적용 단계가 만들고 지움). GWT8 = 커밋 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`. K8 = K8 머리 `b9734abe`.
- jb_unit = J-b 안의 4c 단위 시험 pytest 실행(TREE 뿌리, `OUTK/jb/sa/unit_k92t.log`). 기준 실행 = 같은 넷을 WT(b9734abe)에서 돌린 실행(`UB/unit_b9734abe.log`). 4c 단위 시험 = `diagnostics/sdmpc_n31_20260924/tests/`의 `test_stopline_approach.py`·`test_stopline_wiring.py`·`test_stopline_evidence.py`·`test_stopline_approach_captured.py`.
- G5 = K9-1 plant 비교 규칙(보충 18 §3.3; 숫자 잎 비트 같음 등). G-K4 = 커밋 코드 대 스크래치 탐침 재현 관문. RS = `evaluation/controllers/runtime_setup.py`.
- J·F 값 고정 = `OUTK/judge/f.json`(`04cfa2e0…`)·`judge/jb.json`(`f8a273ef…`)의 sha가 둘 다 `KB/LOG.md`에 있고 파일이 그대로인 상태(보충 30 §4.5).
- 시드는 망 접두어를 붙입니다(v3c3-s31 등). 봉인 시드 37/59/61/67은 열지 않았습니다.

## 보고서 머리에 옮겨 적는 공개 (보충 31 §5·§9 요약 + 이 검증의 공개)

1. 보충 31 P1–P6과 §9-1–16은 `GATES_K92B1_A31.md` 머리에 옮긴 그대로입니다. 특히 scan31 개수(134/45/0)와 jb_unit K9-2 쪽 요약은 이미 알려진 값이었고, 이 검증도 블라인드 점검이 아닙니다(P6).
2. **고정 전 노출(이 검증)**: 작업 지시 글에 적용 보고 요약(134/45/0, 공통 97·다름 0, OUT31 파일 sha 앞 8자 등)이 들어 있었습니다. 도구를 짜려고 출력 꼴을 코드에서 읽었습니다(§1). OUTK `jb/sa/unit_k92t.meta.txt`(환경 줄·명령 줄·`rc=1`)와 `OUTK/steps.jsonl`의 `jb_unit` 줄(이름·rc)을 고정 전에 봤습니다. 이 둘은 보충 31 §4.3 "첫 읽기 전 고정" 목록 밖이지만 적어 둡니다. OUT31 파일 이름·크기와 G-K4 입력 파일 16개의 있음/없음(메타데이터)을 고정 전에 봤습니다. 고정 전에 OUT31 파일 내용·두 pytest 로그·봉인 기록·G-K4 행 파일·`rjg4.json`·CAP·`cap_manifest.json`의 내용은 열지 않았습니다.
3. **독립성의 한계**: 새 파일이고 아무것도 import하지 않았습니다. 다만 G5 규칙의 제외 낱말은 보충 27 §2.3이 줄 번호로 가리킨 코드 상수(`k8b_commit_gates.py:118`·`:797-798`)에서 그대로 옮겼고, 그 과정에서 `compare_g5`(`:878-942`)·`sa_compare.flatten`·`k92_gates.judge_g4_plant`(`:482-504`)·`k92t31_unit.py`의 머리말과 결과 꼴(`:1-37`, `:231-317`)을 읽었습니다. 그래서 잎 경로 꼴(`/key[i]`)과 sha 열쇠 판별 꼴은 기존 코드와 같은 선택입니다 [읽음]. 규칙 글이 정하지 않은 곳의 선택은 §5에 적었습니다.
4. 기존 어댑터의 봉인 시드·v3c3-s47 sha 계산(D-K9-44)은 그대로입니다(기록만, 고침은 묶음 2).

## 1. 도구 고정과 순서 [실행]

- 03:25 LOG에 시작 항목, 03:39 LOG에 도구 고정 항목(`KB/LOG.md` 903·910줄). 고정 목록 `VG4/vg4_pins.sha256` = `fb4fa16fb9d711e115e4cd8237ac8b5aafccf845873198e6b088187956a47896`(9줄; 도구 7 + 합성 시험 도구·출력 2). 끝에 다시 `sha256sum -c` 9/9 OK, 고정 뒤 바뀐 도구 0.

| 파일 | 무엇 | sha256 |
|---|---|---|
| `vg4lib.py` | 경로 표·sha·JSON·LOG 자동 줄·J·F 고정 확인·도구 고정 확인 | `2e5a9d133b76c22dbace1ce7376cf378f19c637f0215bd713df04a5713d1902b` |
| `vg4_scan.py` | V2 봉인 훑기(보충 31 §2.2 글) | `bef3d5c78f8a3da7f0dea7d0b541d4281caadc9c4ea6da97ed36b3dbfe485a3c` |
| `vg4_unit.py` | V3 pytest 로그 해석·판정(보충 31 §3.2–3.3 글) | `eed86ef25f9a212f52c5626f3318a25973dab8c95178b7ce2f08636af53b938e` |
| `vg4_gk4.py` | V1 G-K4 plant 재계산(보충 29 §5, 27 §2.3·§5.2, 18 §3.3 글) | `0f81492561ae8dc61fc4a46aad7a07a9037a47224c403c7a13f04770e6434498` |
| `vg4_keep.py` | V4 보관 그대로·CAP 바이트 | `68798acec4613a6ae1542a1874716cdc1e54a74c08c528c1b3ad9f985cb90b8d` |
| `vg4_run.py` | 구동기(가드 → 스냅숏 → V4 → V2 → V3 → V1 → 스냅숏) | `56c10d1b0ade22f4567767592ae076c2caf438109330e24c3d4273a58b5612d9` |
| `vg4launch.ps1` | WMI 분리 발사기(BelowNormal, `PYTHONHASHSEED=0`, `python -B`) | `2848be71c8d7bee17c496489c049f7a96687067b40820be35394389c721de4f8` |
| `vg4_synth.py` / `out/synth.json` | 고정 전 합성 시험 / 그 결과(80/80) | `4943ec4d1808b8042e1fa265c5f87ce6034194af12699113206f4e13ae9f910a` / `d6de503131383b1efe8cbd9b6a3e1178ccf7f3f101b9b2d408e1f2ad8da4d603` |

- 고정 전 시험은 합성 입력만 썼습니다 [실행 `out/synth.json` 80/80]: 진리표 T1–T22(보충 31 §2.2 표의 "새" 칸과 22/22 같음), 합성 봉인 뿌리 둘(좋은 꼴 4/2/0, 위반 꼴 9/7/4·읽지 못함 1·어긋남 3), G5 규칙 13사례(PASS·EXPLAIN·FAIL·제외·sha 열쇠·경로 문자열·한쪽 잎·종류 충돌·NaN·bool), CAP 3사례(같음·바이트 바뀜·파일 더함), pytest 합성 트리 8벌을 실제로 돌린 로그 판정 24사례(같음 PASS, 통과→실패·새 시험 실패·기준에만·다른 메시지·다른 꼬리표 FAIL, 잘림·rc 어긋남·rc 없음·뿌리 틀림·개수 고침·제목 바꿔치기·platform·혼자 낱말 INCOMPLETE 등), 가짜 배치 전체 구동 6사례(가드 멈춤, PASS, 기록 판정 바꿈·숫자 잎 바꿈·CAP 바이트 바꿈·s47 기록 블라인드 깨짐 → 각각 STOP).
- 구동기는 시작 때 기계로 봅니다(`vg4_run.py:50-72` `guards`): 보충 31 sha = `.sha256` = 고정점 글 안 64자, 고정점 sha `605ccbd2…`, `KB/a31_pins.sha256` = `bf1ca001…`, 도구 7개 sha가 LOG에 있음, J·F 값 고정, C:·D: ≥ 8 GB, VISSIM 0. 실제 실행에서 여섯 모두 참이었습니다 [실행 `/guards`]. 그래서 첫 데이터 읽기는 고정 뒤입니다.
- 발사: `vg4launch.ps1 -Tag vg4_run -Script vg4_run.py -ArgLine run` 한 번, 03:39:42, ReturnValue 0, PID 19208(cmd.exe), BelowNormal(16384), 발사 때 python 0·VISSIM 0 [실행 `out/wmi_launch_lines.txt`]. 03:42:48 끝(185.6 s), 종료 판정 PASS. 기다림은 `Wait-Process` 한 번(480 s 상한). 표준 출력 `out/logs/vg4_run.txt`(판정 줄만).
- 열람 기록: 구동기가 읽기 직전에 LOG에 자동으로 적었습니다 — 03:40 CAP·기준 목록(V4), 03:41 봉인 `k92_record.json`(V2), 03:41 두 pytest 로그·OUT31 기록(V3), 03:41 G-K4 행 원자료 16파일·`rjg4.json`(V1), 03:42 결과 줄(`KB/LOG.md` 927–931줄).

## 2. 한눈에 [실행 `VG4/out/vg4_result.json` `0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603`]

| 항목 | 기록(적용 보고·기록 파일) | 내 다시 셈 | 같음 | 근거(`vg4_result.json`) |
|---|---|---|---|---|
| 가드 | – | 여섯 모두 참 | – | `/guards` |
| OUT31 기록 그대로 | 보고 §7 sha | 8파일 sha가 보고 값과 같음(`check31` `007d316f…`, `scan31` `98de5508…`, `sealed_records_a31` `47f91364…`, `unit31_run` `73e2984d…`, `unit_judge` `b7e9b649…`, `unit31` `23591103…`, `chain31` `5ca6c428…`, `unit_b9734abe.log` `e2aaf860…`) | 같음 | `/out31_unchanged` |
| V1 G-K4 plant | `rjg4.json` plant 4행 PASS, 파일별 PASS | 4행 PASS, 파일별 PASS | 같음 | `/V1` |
| V2 봉인 훑기 | 134/45/0, ok 참 | 134/45/0, seed 분포·어긋남 0 | 같음 | `/V2` |
| V3 jb_unit | PASS, 공통 97, 다름 0, 0/0, 통과 아닌 공통 2 | 같음 | 같음 | `/V3` |
| V4 보관 | (보충 31 §4.3 V4 조건) | 모두 참 | – | `/V4` |
| 스냅숏 앞·뒤 | – | 둘 다 s02 대비 SAME | – | `/snap_before`, `/snap_after` |

## 3. V1 — G-K4 plant 원자료 재계산 (D-K9-55·D-K9-60) [실행 `vg4_gk4.py`; 정의 보충 29 §5, 보충 27 §2.3 끝·§5.2, 보충 18 §3.3]

- 행: K9-2-1 W·K9-2-2 B1 × {`TL3_1500_SAF_OBS_H3`(v3c3-s31), `TL3_1050_s43_SAF_OBS_H3`(v3c3-s43)}. v3c3-s47 잡 파일은 열지 않았습니다(구동기가 잡 이름의 s47 조각을 막음, `vg4_gk4.py:183-187`).
- 옛 쪽 `OK2/probe_a25/plant/sa/jobs/k92p{W,B1}/<잡>`, 새 쪽 `SEALED/K9-2-{1,2}/plant/new/sa/jobs/k92{1,2}g4{W,B1}/<잡>`, 파일 `summary.json`·`k92_record.json`. 경로 문자열 뿌리 넷 = `TK/a25/k92b1_probe`, `TK/k92{1,2}_pl`, `OK2/probe_a25/plant`, `SEALED/K9-2-{1,2}/plant/new`.
- 결과(네 행 모두 같은 꼴):

| 파일 | 잎(양쪽) | 제외 | 비교한 숫자 잎 | 비교한 문자열 잎 | 숫자 다름 | 1e-9 안 다름 | 문자열 다름 | sha 열쇠 다름 | 경로 문자열 다름 | 한쪽 | 종류 충돌 | 판정 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `summary.json` | 10,286 / 10,286 | 28 | 10,213 | 32 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |
| `k92_record.json` | 79 / 79 | 2 | 69(K9-2-1) / 70(K9-2-2) | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PASS |

  - `/k8b0`·`signal_queue` 잎(G5는 비교함)은 summary마다 4,787개를 비교했고 다름 0입니다. bool·null 잎 다름 0, 한쪽 0.
- 기록 대조: `rjg4.json`(sha `246f28aa…` 확인 뒤 읽음)의 plant 열쇠 넷 = 내 행 넷, 행 `verdict` PASS 4/4, `parts.summary.json.verdict`·`parts.k92_record.json.verdict` PASS 8/8, 내 값과 모두 같음(`/V1/record_compare/all_same` 참) → **V1 PASS**.
- 참고 기록(대신하지 않음): 검증 2차 `vgates3/out/gk4_plant.json`(`3999f0cc…`)도 4행 PASS였습니다. 그 파일의 숫자 잎 수(summary 10,237, 기록 70–71)는 내 수(10,213, 69–70)보다 큽니다. 제외 잎을 세기 전·후의 차이로 봅니다 [추론: 내 제외 28·2개 가운데 숫자 잎이 24·1개면 맞음]. 판정은 같습니다.

## 4. V2 — 봉인 뿌리 기록 훑기 다시 셈 [실행 `vg4_scan.py`; 정의 보충 31 §2.2, §4.3 V2]

- SEALED를 `os.walk`로 걷고 이름이 정확히 `k92_record.json`인 파일만 읽었습니다(seed·vissim·vissim_reason 칸, 메모리 안). 출력은 개수·경로뿐입니다.
- 결과: 기록 134, s47 45, 나쁨 0, 읽지 못함 0, 걷기 오류 0. 맨 위 폴더별 K9-2-0 26 · K9-2-1 54 · K9-2-2 54(K9-2-3 0).
  - (가) seed 칸 값별 = `{'31': 42, '43': 47, '47': 45}`, seed 칸 없음 0 → 선언 값과 같음.
  - (나) "seed = '47'"과 "봉인 뿌리 아래 상대 경로에 s47 조각"이 어긋나는 기록 0. s47을 seed 길로 45, 경로 길로 45.
  - s47 기록 45개 모두 `vissim` 열쇠가 있고 값 null, 이유 `k92_blind_s47`(열쇠 없음 0).
  - 내부 확인: 글의 함수(긴 경로 머리 떼기 → normcase·abspath → 뿌리 뒤 상대 경로)와 걷기 상대 폴더로 낸 조각 판별이 134/134 같음.
- 기록 대조 11항목 모두 참: `sealed_records_a31.json`의 `sealed_records` = {files 134, s47 45, bad 0, ran 참}, `ok` 참, `n_bad` 0; `scan31.json` 판정 PASS, rc 0, ok 참, 개수·기대 개수 같음, 보관 그대로 참, `output_sha256` = `sealed_records_a31.json` 실제 sha → **V2 PASS**.

## 5. V3 — jb_unit 판정 다시 셈 [실행 `vg4_unit.py`; 정의 보충 31 §3.2–3.3]

- 입력: `UB/unit_b9734abe.log`(`e2aaf860…`, 기준, 뿌리 WT), `OUTK/jb/sa/unit_k92t.log`(`ef8033f5…`, K9-2, 뿌리 TREE). 선택 = 4c 넷(선언 순서). 정규화 뿌리 7개 = WT, TREE, UB, JB(`OUTK/jb`), CAP, WT git 폴더 `D:/VISSIM-merge/repo/.git/worktrees/a31_wt_b9734abe`, jb_unit `GIT_DIR` `…/worktrees/sim3-n31-k8`.
- 종료 코드: 기준 = `unit31_run.json` `base_rc` 1 = `steps31.jsonl` `unit31_pytest` rc 1(한 줄) = `unit_b9734abe.meta.txt` `rc=1`; K9-2 = `OUTK/steps.jsonl` `jb_unit` rc 1(한 줄).
- 해석 점검 P1–P10: 두 쪽 모두 참(20/20). 수집 97/97, `rootdir` = 자기 트리 뿌리 참/참, `platform` 줄 같음.
- 결과 낱말: 두 쪽 모두 PASSED 95, FAILED 2, ERROR·SKIPPED·XFAIL·XPASS 0. 최종 줄: 기준 "2 failed, 95 passed, 92 subtests passed in 126.54s (0:02:06)", K9-2 "… in 106.19s (0:01:46)".
- 판정: 공통 97, 다름 0, 기준에만 0, K9-2에만 0, 새 시험 나쁨 0, INCOMPLETE 사유 0 → **PASS**.
- 통과 아닌 공통 2개: `test_stopline_wiring.py::ConfigFlagTests::test_arms_add_exactly_the_key`, `::test_default_output_is_byte_identical`. 두 쪽 모두 행 결과 `['FAILED']`, 실패 항목 `FAILED`·꼬리표 없음·첫 `E` 줄(정규화·300자) 같음. 메시지는 바이트 비교 `AssertionError`의 줄인 repr입니다(정규화 규칙의 역슬래시 → `/` 때문에 repr의 `\n`이 `/n`으로 보임; 두 쪽 같은 규칙).
- 기록 `unit_judge.json` 대조 13항목 모두 참: 판정, INCOMPLETE 빔, 기준·K9-2·공통 개수, 다름 목록·수, 기준에만·K9-2에만·새 시험 나쁨 목록, 통과 아닌 공통 목록(시험 이름·행 결과·실패 항목 정확히 같음)과 수, rc. 적용 기록 `unit31_run.json`의 보고 항목도 확인: 선택 = 넷, WT head = b9734abe, WT git 폴더 = 선언 값, `wt_removed_and_state_same` 참, `problem` 없음, WT 대 `TK/b9_ref` 0/0/0, 실행 뒤 WT status 0줄 → **V3 PASS**.

## 6. V4 — 보관 그대로 [실행 `vg4_keep.py`; 정의 보충 31 §4.3 V4, §4.1 C7·C9]

- 고정 목록 `KB/a31_pins.sha256`(`bf1ca001…`, 133줄)에서 OUTK 아래 26줄과 OUT30 둘·`OK2/logs/k92t30_chain.txt` 한 줄(합 29줄)의 sha가 지금 파일과 모두 같음.
  - 133줄 전체로는 127줄 `KB/GATES_K92B1.md` 하나만 다름(지금 `449b361e96d047156e63f73bcdae905ec61408b9a5f9be047629092d3ab0a792`). 적용 보고 A31-N2의 설계된 덧붙임과 같은 값입니다(보고만).
- C7: OUTK STOP 파일 = {`STOP_a30_post.json`, `STOP_f.json`}, `stages/` 7개 이름, `judge/` 7개 이름, `steps.jsonl` 102줄 → 참.
- C9: 봉인 뿌리 맨 위 = K9-2-0·K9-2-1·K9-2-2·K9-2-3·a27·k92t, `SEALED/k92t/logs` = `f_f_b1_jobs.log` 4,971 B · `f_f_off_jobs.log` 4,996 B · `f_f_w_jobs.log` 4,936 B(이름·크기만, 내용 열지 않음) → 참.
- git(`--no-optional-locks` 읽기만): GWT8 head `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`, 브랜치 `claude/k92-b1-20261016`, status 0줄, `b9734abe..HEAD` 6, K8 브랜치 `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, 원격 k92 참조 0, `git worktree list`에 WT 없음, WT 폴더 없음, WT 관리 폴더 없음 → 참.
- CAP: 지금 걸은 파일 3,944개, 1,690,146,202 B, 걷기 오류 0. 기준 `KB/a31review/out/cap_manifest.json`(sha `d6691f48…` = 고정점 값 확인 뒤 읽음)과 비교해 지금에만 0, 기준에만 0, 크기 다름 0, 바이트 sha 다름 0. 내 걷기로 다시 낸 목록 sha `5340ac03da81742dd864044f9922a75bed1e542147249d4a8699a6432e273038` = 기준 목록 값 = 고정점 선언 값 → 참.
- 그래서 **V4 PASS**. 기준 실행이 CAP를 읽기만 했다는 보충 31 §3.4 글이 바이트로 확인됩니다.

## 7. 적용 보고와 대조 [읽음 `GATES_K92B1_A31.md`, 실행 비교]

| 보고 글 | 내 값 | 같음 |
|---|---|---|
| scan31: rc 0, ok 참, 134/45/0, 보관 두 파일 그대로 | V2 134/45/0, 기록 대조 11/11 참, V4에서 `STOP_a30_post.json` `8fa75243…`·`judge/sealed_records.json` `517582ad…` 같음 | 같음 |
| unit31: 기준 rc 1, 공통 97, 다름 0, 0/0, 통과 아닌 공통 2 | V3 같음 | 같음 |
| 표: 수집 97/97, 최종 줄 failed 2·passed 95·subtests passed 92, 결과 낱말 PASSED 95·FAILED 2, rootdir 참/참, P1–P10 INCOMPLETE 0, platform 같음 | 같음 | 같음 |
| 기준 로그 20,922 B `e2aaf860…`, jb_unit 로그 `ef8033f5…` | sha 같음(V4·OUT31 대조) | 같음 |
| WT 만들고 지움, WT 대 b9_ref 0/0/0, 실행 뒤 status 0줄, GWT8·K8 그대로 | `unit31_run.json` 보고 항목과 V4 git 확인 | 같음 |
| G3: GWT8 head·status·6커밋·K8·원격 0·WT 없음 | V4 git 같음(03:40, 그리고 04:03 다시) | 같음 |
| 기준 실행 128.3 s | pytest 자체 시간 126.54 s(최종 줄); 차이는 프로세스 시작 시간으로 봄 [추론] | 모순 없음 |

- 보고서의 OUT31 파일 sha(§7 표) 8개를 내가 다시 셈한 값과 맞췄습니다(§2).

## 8. 지킨 것 [실행]

- VISSIM·COM·러너·동결·결정 재생·plant 잡·pytest(실제 시험) 0. 돌린 pytest는 내 합성 시험뿐(`VG4/syn`, `VG4/dev/pyfmt`). 금지 시험 0.
- 무거운 일은 구동기 한 번(WMI 분리, BelowNormal, `PYTHONHASHSEED=0`, `python -B`). 기다림 8분 이하.
- 쓴 곳: VG4(도구·합성 트리·출력·스냅숏 둘), `KB/LOG.md`(덧붙임만), 이 보고. OUTK·OUT31·OUT30·SEALED·TREE·GWT8·저장소·K8 브랜치·V4·동결본·런 폴더 쓰기 0. 끝 확인 [실행 04:0x]: 03:39 뒤 바뀐 파일 수 OUTK 0·SEALED 0(개수만)·OUT30 0·OUT31 0·`OK2/a27` 0·`OK2/probe_a25/plant` 0·`OK2/snap` 0·`OK2/logs` 0·OK2 맨 위 0·TREE 0·V4 0.
- 읽기 전용 뿌리 스냅숏(`KI/k92snap.py` `0dbd7d2c…` 실행만): 앞 `out/snap_before.json` `101276f3…`, 뒤 `out/snap_after.json` `7a18c7b7…`, 둘 다 s02 대비 SAME.
- 봉인 시드 37/59/61/67 0, codex 64cf 숫자 0. v3c3-s47 값은 V2가 s47 기록의 세 칸을 메모리에서만 읽음(출력은 개수). G-K4는 s31·s43 잡만.
- 커밋·브랜치·푸시 0. 끝에 python·VISSIM·find 0. 끈 프로세스: 내 백그라운드 `find`(넓은 트리 메타데이터 개수 세기, 너무 느려 내가 멈춤; 출력 0) 하나. 그 뒤 좁은 자리만 다시 셈(위).
- 디스크: C: 40 GB, D: 388 GB 여유(df).

## 9. 해석 선택과 한계 (규칙 글이 정하지 않은 곳; 도구 머리말에 고정 전 선언)

1. **V1 경로 문자열 예외**: "어느 한쪽 값이라도 뿌리 넷 가운데 하나를 품으면" 예외로 봤습니다(보충 27 §2.3 "주어진 뿌리 넷의 경로 문자열"). 더 엄격한 읽기("뿌리를 `<root>`로 바꾼 뒤에도 같아야 함")는 보고만 셌고, 실제 자료에서 경로 문자열 다름이 0이라 두 읽기의 결과가 같습니다.
2. **V1 bool·null 잎**: 판정하지 않고 보고만(다름 0, 한쪽 0). 숫자 대 null·문자열 같은 종류 충돌은 FAIL로 셉니다(0개).
3. **V1 제외 낱말**: G5 제외 = 시각 낱말(`wall`·`sec`·`time`·`rss`·`elapsed`) + G5 제외 목록(`k8b_commit_gates.py:797-798`). 일반 제외의 `/k8b0`·`signal_queue`·`/k8b/`는 G5 글대로 비교했습니다.
4. **V3 메시지**: 덩어리 안 첫 `^E\s+\S` 줄에서 `E`와 빈칸을 뗀 글. 기록과 정확히 같았습니다.
5. **V2 읽지 못하는 기록**: s47 경로 자리면 나쁨으로 셈(글보다 엄격). 실제 0개.
6. V3은 보충 31 §3.3의 비교 범위 한계(건너뜀 까닭·첫 `E` 줄 뒤 메시지·하위 시험별 통과 비교 안 함)를 그대로 가집니다.
7. 이 검증은 블라인드 점검이 아닙니다(공개 1).

## 10. 남은 것·다음

- 보충 31 §4.4의 K92_GATES_PASS 조건 가운데 "독립 검증 A31 PASS"가 이 보고로 채워집니다 [읽음 §4.4]. 그 다음은 D-K9-37·D-K9-60 순서대로 V-B(보충 24 §14.1·27 §6.2·29 §6.2) → VerifyVB입니다. V-A·푸시는 그 뒤 사용자 결정입니다. 이 검증은 V-B를 하지 않았습니다.
- 정리 결정(사용자, K9-2 끝): `VG4/syn`(507 KB)·`VG4/dev`(22 KB)·`VG4/out/snap_*.json`(각 38.7 MB) 합성·보조 파일. `OK2/vg3r/jbcopy`(4.1 GB)는 D-K9-61대로 보관 중.

## 11. 파일

| 파일 | sha256 |
|---|---|
| `VG4/vg4_pins.sha256` (9줄) | `fb4fa16fb9d711e115e4cd8237ac8b5aafccf845873198e6b088187956a47896` |
| `VG4/out/vg4_result.json` (V1–V4 전부, 블라인드 꼴) | `0b7654eca9e1165fad42ebe59b28bde91598d0b183f0cf694a21ba09a398b603` |
| `VG4/out/synth.json` (고정 전 합성 80/80) | `d6de503131383b1efe8cbd9b6a3e1178ccf7f3f101b9b2d408e1f2ad8da4d603` |
| `VG4/out/snap_before.json` / `snap_after.json` | `101276f3441950dd958abf57b2aa1cecab465329552be423e947b3a61f7835dd` / `7a18c7b7108369d4ad805678bce76bcaf17ba58388a092315697c83b718af171` |
| `VG4/out/logs/vg4_run.txt` / `VG4/out/wmi_launch_lines.txt` | `aa0dc7fcbfd4873c69373fcd81eee747a52bea2f5e435a49a5e0cde99430a4a5` / `45795e448d2de92287bfde0ca082b813bd779c70aa11d713b57d8033b3e0e00d` |
| 검증 대상 `KB/GATES_K92B1_A31.md` | `e2b301837feb35d652d0db088d634e07449676abd01cb0e8b2dfef6eff232885` |
| 기록 `OK2/a27/judge/rjg4.json` / `KB/a31review/out/cap_manifest.json` | `246f28aa8cae77281d414a8cf774bd6c6c688d6929b726baf1e83c69448a82ec` / `d6691f48954d07dd2b3bbfe718e468fd59f3f6b7492060a2151d4d02e177e3a9` |
