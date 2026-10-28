# K8 보충 31 (고정판) — K9-2 묶음 1: 봉인 뿌리 기록 훑기의 s47 판별 고침(D-K9-58), jb_unit 판정 규칙(b9734abe와 시험별 같음, D-K9-59), 그 뒤 순서(봉인 훑기 → jb_unit → 보고 → G-K4 plant 원자료 재계산 → V-B → VerifyVB, D-K9-60), 검증 2차 공개 수용(D-K9-61) (2026-10-22)

- **상태: 고정판(반박 검토 판, ReviewDeclare 2026-10-22).** Declare 판은 `SP/K8_PREDECLARATION_AMENDMENT_31_r1.md`(sha256 `8a76e210230b69c0c21627f13eb7459e04f044d5ac62feac3cdcb2dd5c3d0cbc`, 같은 이름 `.sha256` 있음)로 남깁니다. 검토가 고친 곳에는 "[검토]"를 붙였고, 까닭과 확인은 §12에 모았습니다. 검토는 보충 31 적용 데이터(OUT31, 봉인 훑기 다시 돌림, b9734abe 기준 실행)가 0개인 상태에서 했습니다. 검토는 글만 고쳤습니다. 새 구동기·판정기·비교기·확인 도구·기대 고정 목록(§8, `bf1ca001…`)의 바이트는 그대로입니다. 고정점 파일은 `KB/AMENDMENT31_FIXED.md`입니다. 고정점에 적힌 sha256과 다른 보충 31로는 어떤 적용 단계(사전 점검, 봉인 훑기, jb_unit 기준 대조)도 하지 않습니다. 새 구동기 `AD31/k92t31.py`가 이것을 기계로 봅니다: `chain31`·`scan31`·`unit31`은 보충 31 sha = `.sha256` = 고정점 글 안의 64자 sha가 아니면 시작하지 않습니다(`k92t31.py:202-212` `a31_sha`) [읽음].
- 이 파일의 sha256을 `SP/K8_PREDECLARATION_AMENDMENT_31.md.sha256`에 적습니다.
- **쓸 때 상태** [실행 2026-10-22 01:29–02:1x KST]: GWT8 head = K9-2-5 `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` = 커밋 6개), K8 브랜치 `claude/k8-sc1001eb-defects-20261004` = `b9734abe1c83f95c9cec5fca5e42b7b18cd45991`, `git status --porcelain` 0줄, 원격 k92 참조 0, 푸시 0. 판정 단계 출력 `OUTK`는 보충 30 사후 STOP 그대로입니다: STOP 파일 `STOP_f.json`·`STOP_a30_post.json` 둘, 단계 기록 7개(start·prep·j0·ja·seal30·f·jb), 판정 파일 7개(j0·ja·jwall·f_jobs·f·jb·sealed_records), `steps.jsonl` 102줄. `OUT31`(`OK2/a31`) 없음, 임시 작업 트리 자리 없음, 봉인 뿌리 맨 위 여섯(K9-2-0·1·2·3·a27·k92t) [실행 `AD31/dry/decl/check31_decl.json`, 43점검 거짓 0].
- **구속**: 보충 1–30의 규칙·식·값·문턱·관문·표본은 §7 표에 적은 자리만 빼고 **그대로** 구속합니다.
- **알리는 말(먼저 읽을 것)**:
  1. **데이터를 본 뒤의 판정기 고침입니다(사용자 결정 D-K9-58).** 보충 30 사후 단계의 봉인 뿌리 기록 훑기가 STOP(S-K10)한 뒤, 그 판정기 함수 하나(`_seed47_path`)를 고칩니다. 보충 24 S-K12(:400)는 데이터 뒤 판정기 변경을 STOP으로 정했습니다. 이 보충은 사용자 결정에 따라 그 한 함수만 예외로 둡니다. 고친 규칙으로 다시 돌린 결과는 이미 짐작할 수 있습니다: 관문 단계의 실패 진단(`KB/GATES_K92B1_A30.md` §3)과 검증 2차의 선언 규칙 재계산(`KB/VERIFY_GATES_K92B1_r2.md` §6)이 둘 다 "v3c3-s47 기록 45개, 모두 블라인드 꼴, 나쁨 0"을 냈습니다. 그래서 다시 돌리기는 블라인드 점검이 아닙니다.
  2. **보충 30 §5.3의 "모든 단계 실행 rc≠0 → STOP" 글을 jb_unit 한 줄에 한해 바꿉니다(D-K9-59).** jb_unit은 J-b 안의 4c 단위 시험 실행입니다. 그 자리에 "K8 머리 b9734abe와 시험별 결과가 같으면 PASS" 규칙(§3)을 둡니다. 기반 구동기는 jb_unit rc=1에서 멈추지 않았고 J-b를 끝까지 돌렸습니다. 그래서 이 판정은 J-b 값이 나온 뒤에 합니다.
  3. **메인 세션 공개**: 10-22에 jb_unit 로그 자리를 찾으려 `OK2` 아래에 `grep -rl`(파일 이름만 출력)을 돌렸다가 멈췄습니다. 봉인 뿌리도 훑었을 수 있습니다. J·F 값 고정 뒤였고, 내용 출력은 0이었습니다. 그때 LOG에 적지 않았으므로 여기에 적습니다(§5 P3).
  4. **기준 쪽 트리 꼴**: b9734abe 기준 실행은 사용자 결정대로 임시 분리 작업 트리(`git worktree add --detach`)에서 합니다. K9-2 쪽 jb_unit은 `git archive` 트리(TREE)에서 돌았습니다. GWT8 작업 트리는 **CR만 다른 파일 10개**에서 archive와 다릅니다(GWT8 LF, archive CRLF) [실행 e27ceac8에서 GWT8 대 TREE: 바뀜 10, 한쪽 0, CR을 빼면 10/10 같음]. 그러나 **새로 만든** 작업 트리는 이 PC의 시스템 설정(`core.autocrlf=true`)에 따라 archive와 같은 줄바꿈으로 꺼냅니다 [실행 합성 저장소 `dry/decl/autocrlf_probe.json`: 커밋한 작업 트리 CR 0, 새 작업 트리 CR 3, archive CR 3, 블롭 CR 0]. 그래서 WT는 archive 꼴(`TK/b9_ref`)과 같고, 두 쪽의 줄바꿈 꼴도 같을 것으로 봅니다 [추론; 적용 때 보고 항목이 실제를 보임]. 차이가 나도 4c 시험은 그 파일들을 줄바꿈을 가리지 않는 방법으로 읽습니다 [읽음, §3.6]. 시험 결과가 다르면 STOP입니다.
  5. **검증 2차 공개를 받아들입니다(D-K9-61)**: 고정 전 노출, `vg3t`→`vg3r` 폴더 이름 바꿈, M2·M3의 VISSIM 쪽 FZP 재계수 없음(§5 P4).
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 보충은 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. 교통 성능 판정이 아닙니다.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. KI = `KB/impl`(구현 도우미, 바꾸지 않음). AD30 = `KB/a30decl`(보충 30 구동기·판정기, 바꾸지 않음).
- **AD31** = `KB/a31decl` — 이 보충의 새 구동기·판정기·비교기·확인 도구·확인 출력 폴더(§11).
- TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`. **TREE** = `TK/a27/k92t`(git archive K9-2-5 `e27ceac8`; K9-2 쪽 jb_unit이 돈 트리). `TK/b9_ref` = git archive b9734abe(보고 대조용, 읽기만).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. **OUTK** = `OK2/k92t`(판정 단계 출력, 이 보충에서 **쓰지 않는 보관 자리**). OUT30 = `OK2/a30`. **OUT31** = `OK2/a31`(이 보충의 출력, 지금 없음). **SEALED** = `OK2/sealed_s47`(봉인 뿌리). V4 = `D:/VISSIM-merge/k8_gates_out_v4`(K9-1 판정 산출, 읽기만).
- GWT8 = 커밋 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`. 저장소 `.git` = `D:/VISSIM-merge/repo/.git`.
- **WT** = 임시 분리 작업 트리 `TK/a31_wt_b9734abe`(b9734abe, 관리 폴더 `D:/VISSIM-merge/repo/.git/worktrees/a31_wt_b9734abe`). 같은 단계 안에서 지웁니다. 자리는 보충 27 §2.1 트리 자리 닫힌 목록의 1번 꼴(`TK/<이름>`)입니다.
- **UB** = `OUT31/unit_base`(기준 실행의 출력 뿌리 = 그 실행의 `K8G_OUT`). **JB** = `OUTK/jb`(J-b 뿌리). **CAP** = `OUTK/jb/sa/cap/k92t`(jb_unit이 읽은 포착 뿌리).
- **4c 단위 시험** = `diagnostics/sdmpc_n31_20260924/tests/`의 `test_stopline_approach.py`, `test_stopline_wiring.py`, `test_stopline_evidence.py`, `test_stopline_approach_captured.py`(K8-6 선언 시험, 금지 시험 아님). **jb_unit** = J-b 안에서 TREE를 뿌리로 이 넷을 돌린 pytest 실행(`OUTK/jb/sa/unit_k92t.log`, `steps.jsonl`의 `jb_unit` 줄 rc=1). **기준 실행** = 같은 넷을 WT(b9734abe)에서 돌리는 실행.
- pytest 줄: **행** = `-v` 출력의 `<파일>::<이름> PASSED [ n%]` 꼴 줄. **결과 낱말** = PASSED·FAILED·ERROR·SKIPPED·XFAIL·XPASS. **SUBFAILED** = pytest 9가 하위 시험(unittest `subTest`) 실패를 요약 줄에 적는 꼴.
- 새 구동기의 단계 이름: **check31**(사전 점검, 읽기만), **scan31**(봉인 뿌리 기록 훑기 다시), **unit31**(jb_unit 기준 대조), **chain31**(이것들을 차례로 한 번).
- **J·F 값 고정** = `OUTK/judge/f.json`(`04cfa2e0…`)과 `judge/jb.json`(`f8a273ef…`)의 sha가 둘 다 `KB/LOG.md`에 있는 상태(보충 30 §4.5). 지금 참입니다 [실행].
- 시드는 망 접두어를 붙입니다(v3c3-s31 등). 봉인 시드 37/59/61/67은 열지 않습니다. codex 64cf-s59·s61·s67 숫자는 쓰지 않습니다.

---

## 0. 근거 문서 [실행: sha256, 2026-10-22 01:29–02:07 KST]

| 문서 | sha256 |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(193줄; D-K9-58~61 :184-193) | `09974cfc3e1412735ba6cf3228f4a2e4c08ad01294327d534290011b4a8042cc` |
| 관문 보고(보충 30 적용, STOP) `KB/GATES_K92B1_A30.md` | `167e9e188c1053b89f814080b258e89238901126f153d2753bcdb0ab271f3556` |
| 독립 검증 2차 `KB/VERIFY_GATES_K92B1_r2.md` | `5f7c125614c65457c08e40644f0723e7db84dad669f2f98fcd73728ed64e2442` |
| 관문 보고 `KB/GATES_K92B1.md`(§8 덧붙임 판) | `3f3a069a68123f7b273d8ae2dc4c14c6be57b2aa8865d38fc975f10ab8ee7e8b` |
| 보충 24 / 25 / 26 / 27 고정판 | `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc` / `4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e` / `8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37` / `4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13` |
| 보충 28 / 29 / 30 고정판 | `9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e` / `4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d` / `ba556227a6356b1733bfa8125b334cfef180c1eed97e8d69ae4ba53a3106a56a` |
| 고정점 24 / 25 / 26 / 27 | `fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a` / `d1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed` / `6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581` / `394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb` |
| 고정점 28 / 29 / 30 | `14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5` / `3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43` / `ad3fafadd59985b3b71f33d5523ceb2324aa8267395d7280039228669cb83e9c` |
| 고정 목록 `KB/k92t_pins.sha256`(56줄, 56/56 OK) / `KB/a30_pins.sha256`(83줄, 83/83 OK) | `38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd` / `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e` |
| 보충 30 판정기 `AD30/k92t30_judge.py`(= `AD31/base/k92t30_judge.py` 바이트 사본) | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` |
| OUTK `STOP_a30_post.json` / `judge/sealed_records.json`(보관, 쓰지 않음) | `8fa7524342517c020715aa26757f38a54473cdcf30cdd1d18d9b5414dcf8e18e` / `517582ad15adc98d936199cc9d4c1e9e9c9cc6bbc3d359722b4d7a06941d6eb5` |
| OUTK `judge/f.json` / `judge/jb.json`(J·F 값 고정) | `04cfa2e0a9ac754bd13d5c5ca2d4cd5790acb34fda64fafdce7f7382027ac792` / `f8a273ef9b6e2f02f539b4193a39d35516959d8799e3cd89a2b060c006faa200` |
| OUTK `jb/sa/unit_k92t.log`(jb_unit 로그; 바이트 sha만, 내용 열지 않음) / `jb/sa/unit_k92t.meta.txt` | `ef8033f54eb342c3431cdf2f756bce6ecaaab3832e90babff6150136466dc3eb` / `e235e0ad2e8eb1997a29b674fc1834bd3e80f0754943a362b3d51a1e0072afdf` |
| OUTK `steps.jsonl`(102줄) / `driver.log` | `1fdef90665711ac849a6a09cff933b5392acc196d452a95364073bde08609123` / `a7ae60589baf3c40ea04702dd97043ab28ff6a56166ad3104b57dc5b2b5102de` |
| 그 밖 OUTK·OUT30 기록(26+3개) | `AD31/k92t31.py:91-120` `RECORDED31`·`OTHER31`, §8 고정 목록 101–118줄 |
| G-K4 기록 `OK2/a27/judge/rjg4.json` | `246f28aa8cae77281d414a8cf774bd6c6c688d6929b726baf1e83c69448a82ec` |
| 검증 2차 도구 목록 `KB/vgates3/vg3_pins.sha256` / G-K4 재계산 `vgates3/out/gk4_plant.json` / 사후 재계산 `vgates3/out/post.json`(참고 기록) | `a864482c66d47b260e17b9200bc7dd79ece8170d10f03687449185c8f7d53313` / `3999f0cc63b2342696e385b96f76e35ff84d915322625dd1aa1d233b7f61cba2` / `758c72ce3ce983c1fe0f57a350b99e1e0e43d305dee7470dfc32240b8715ae1b` |
| 관문 단계 실패 진단 도구 `KB/a30apply/diag_sealedscan.py`(참고) | `bdac6ad09b825d02494e8b376f19667abc686554a353cf5c5baf4c7edafe2cb1` |
| pytest 발사기 `SP/k8b_impl/run_pytest_bn.py`(k92t 고정 목록 6줄) | `fe4451e431a74e7653c5f064e7f2331f17ca9302148da86e51eb4e81c033489e` |
| `TK/a27/k92t.build.json` / `TK/b9_ref.build.json` | `a1e98fa72f787c17f576f9c2de2ed479709849e4880b962624a31d28b892b0d8` / `cace6ada47ef55e8a57c3e1d0f4b9e235b67cfa77c9508c9fbf884b41a2d7b2e` |
| 작업 기록 `KB/LOG.md`(이 단계 첫 항목 덧붙임 전, 203,463 B) | `638c97ebd72aed4659f1cb0184138df78f3d1c05e8f1c6a5cfb44b455dd6b3e2` |
| 읽기 전용 뿌리 스냅숏 `OK2/snap/s34b_a31decl.json`(이 단계, s02 대비 SAME) | `bb3fe248aea12587fa82faaeedac680d5b3c05d2687e43469143eecbf3d5a111` |

### 0.1 이 판을 쓰며 한 일 [실행]

- **읽기**: 위 문서들; AD30 구동기·판정기(`_seed47_path`, `scan_vissim_blind`, `cmd_sealedscan`, `stage_jb`, `stage_post30`, `chain30`); KI `k92lib.py`·`launch.ps1`·`k92snap.py`; GWT8 저장소의 4c 시험 넷 소스(시험 글만), `k8common.py`의 뿌리 처리, K9-2 diff(`b9734abe..e27ceac8`의 파일 목록과 `runtime_setup.py`·`signal_head_observation.py`·`sa_worker.py`·`sa_cap_child.py`·`make_config_n31.py`의 차이), `sa_s3parity.py`의 줄바꿈 처리; 보충 23(시험별 같음 선례), 보충 24 §5.4·§6·§8·§14.1, 보충 27 §6.2, 보충 29 §5·§6.2; TREE `k92_gates.py:576-626`(`junit_results`·`_norm_msg`·`judge_u`, 보충 24 U 규칙의 구현); `OUTK/jb/sa/unit_k92t.meta.txt`·`V4/sa/unit_k91t.meta.txt`(환경 줄, 결과 없음).
- **열지 않음**: `OUTK/jb/sa/unit_k92t.log`의 내용(바이트 sha만), 봉인 뿌리의 파일 내용(맨 위 이름·`k92t/logs` 세 파일의 이름·크기만), 봉인 시드, v3c3-s47 결과 값, b9734abe 시험 결과(만들지 않음).
- **쓰기**: AD31 전부(새 도구, 기반 사본, 확인 출력, 기대 고정 목록); `TK/a31decl/su`·`TK/a31decl/drv`(합성 시험 트리·합성 git 저장소, 실제 값 0); `OK2/snap/s34b_a31decl.json`; `OK2/logs/a31decl_fact_wt.txt`·`a31decl_fact_wt2.txt`·`a31decl_snap.txt`(WMI 발사 표준 출력, 개수만); `KI/wmi_launch_lines.txt`(launch.ps1이 한 줄씩 덧붙임); 이 글과 `.sha256`; `KB/LOG.md` 덧붙임. OUTK·SEALED·TREE·GWT8·저장소 `.git`·K8 브랜치·V4·동결본·런 폴더 쓰기 0.
- **확인 실행**:
  - `dry_a31.py static`·`truth`·`unit`·`drv`·`drive`(§2.5·§3.5; 앞 넷은 합성 입력만, `drive`는 `check31 --mode decl` 읽기만). 무거운 일 둘(사실 확인 `dry/fact_wt_vs_archive.py` 두 번, 스냅숏 한 번)은 `KI/launch.ps1`로 WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번에 하나. 가벼운 확인은 그대로 BelowNormal로 돌렸습니다.
  - 사실 확인(GWT8 작업 트리 대 TREE archive 바이트, 코드 트리만): 첫 실행 01:37(144.1 s), 둘째 실행 01:56(8.4 s), 둘 다 바뀜 10·한쪽 0. 둘째 실행은 첫 출력 파일을 내 폴더 정리 때 지워서 다시 낸 것입니다(같은 결과).
  - 줄바꿈 확인(합성 저장소 `TK/a31decl/drv/autocrlf_probe`, `dry/autocrlf_probe.py`, 02:18): LF로 커밋한 속성 없는 파일을 새 작업 트리와 `git archive`가 둘 다 CRLF로 냄, 커밋한 작업 트리는 LF 그대로.
- **개발 중 공개**(`AD31/dry/dev`, `dry/dev0`): pytest -v 출력 꼴을 보려고 합성 시험 파일 둘을 두 뿌리에서 돌렸습니다(`dry/dev0`, 실제 값 0). 첫 합성 파일은 셸 따옴표 문제로 문법 오류였고 다시 썼습니다. `dry_a31.py unit` 첫 실행은 합성 트리 경로가 Windows 길이 상한(260자)을 넘어 판정기 호출 전에 끝났습니다. 합성 트리를 `TK/a31decl/su`로 옮겼습니다. 확인 도구에 명령줄 점검과 구동기 합성 구동(`drv`)을 더하고 구동기를 고친 뒤(아래) `dry/decl`을 지우고 static·truth·unit·drv·drive를 다시 냈습니다(비교기 `k92t31_unit.py`는 첫 확인 실행 뒤 바꾸지 않았음). `drv` 둘째 실행은 합성 git 저장소의 읽기 전용 객체 파일을 지우지 못해 끝났고, 확인 도구에 지우기 도우미(`rmtree_rw`)를 더한 뒤 다시 돌렸습니다. 고정 목록에 든 확인 출력은 모두 마지막 바이트의 도구로 낸 것입니다.
- **개발 중 도구 고침(고정 전, 실제 데이터 0)**: 구동기 `git()`·`gout()`의 기본 인자를 호출 때 읽게 바꿈(합성 구동에서 GWT8을 바꿔 끼우려고), 기준 pytest 실행에 1,800 s 시간 상한, 보고 항목(WT 대 `TK/b9_ref`)의 예외가 실행을 멈추지 않게 함, `chain31`이 OUT31을 먼저 만들지 않게 함(check31 C10과 충돌), VISSIM 개수가 셀 수 없을 때(None) 멈추지 않고 기록만, WT 자리를 `TK/a31/<이름>`(두 단계 깊이)에서 `TK/a31_wt_b9734abe`로 옮김(보충 27 §2.1 닫힌 목록 1번 꼴에 맞추려고; 그 뒤 static·drv·drive와 고정 목록을 다시 냄).
- **하지 않은 일**: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. 실제 저장소의 임시 작업 트리 만들기 0(합성 저장소에서만). b9734abe 시험 실행 0. 봉인 기록 열람 0. 판정기·비교기를 실제 데이터에 부른 일 0. 커밋·브랜치·푸시 0. 금지 시험 0(4c 시험도 돌리지 않음; 합성 시험만).

---

## 1. 사용자 결정 원문 [읽음 결정 기록 :184-193, 표 행 그대로]

근거 줄(:185-187): `k92/bundle1/GATES_K92B1_A30.md` (167e9e18…), `k92/bundle1/VERIFY_GATES_K92B1_r2.md` (5f7c1256…). F PASS n22(F-1 〔가림: 봉인·블라인드 시드 값〕≤〔가림: 봉인·블라인드 시드 값〕, F-2 〔가림: 봉인·블라인드 시드 값〕≤〔가림: 봉인·블라인드 시드 값〕, F-3 〔가림: 봉인·블라인드 시드 값〕≤+5), J-b 45/45 같음, J-0·J-a·J 벽시계 PASS, 지속성 보고 21상태 MAE 〔가림: 봉인·블라인드 시드 값〕. 검증 2차가 모두 다시 냄(같음). STOP: post30 봉인 뿌리 k92_record 훑기 ok=False(134/134/bad 89) — 판정기 `_seed47_path`(k92t30_judge.py:303-305, :359-371)가 봉인 뿌리 이름 `sealed_s47` 을 s47 조각으로 읽음; bad 89 = v3c3-s31 42 + s43 47, 실제 s47 기록 45/45 vissim null(k92_blind_s47). 별건: jb_unit rc=1(test_stopline_wiring ConfigFlagTests 2개) — 메인 세션이 10-22 K8 머리 b9734abe 임시 작업 트리에서 같은 두 시험을 돌려 같은 2 failed 확인(K9-2 는 config_n31_v2.json 미변경, blob 268ae471 동일; 원인 = K8-7·K8-10 이 config 를 손으로 고쳐 make_config_n31.build() 가 재생산 못 함). 임시 트리는 지움. 공개(메인 세션): 10-22 jb_unit 로그 위치를 찾으려 OK2 아래 grep -rl(파일 이름만 출력)을 돌렸다가 멈춤 — 봉인 폴더도 훑었을 수 있음(J·F 값 고정 뒤, 내용 출력 0).

| # | 질문 | 사용자 답 | 효과 |
|---|---|---|---|
| D-K9-58 | 봉인 점검 STOP 처리는? | **보충 31로 규칙 고치고 재점검 (Recommended)** | 보충 31: s47 판별 = 기록의 seed 칸, 또는 봉인 뿌리 아래 상대 경로의 조각(뿌리 이름 자체는 제외). 판정기의 그 함수만 고치고(데이터 뒤 수정임을 공개), 봉인 뿌리 훑기만 다시 돌림. VISSIM 0 |
| D-K9-59 | jb_unit 2건 실패는? | **기존 실패로 공개, 보충 31에 함께 적음 (Recommended)** | 보충 23 꼴: 'jb_unit 실패 시험 목록 = K8 머리 b9734abe 의 같은 시험 실패 목록'이면 통과(보충 30 §5.3 의 rc≠0 STOP 조항을 이 한 줄에 한해 고침, 공개). 기준 목록은 고정 도구로 다시 내서 고정. make_config_n31/설정 정합 수정은 묶음 2 목록 |
| D-K9-60 | 봉인 점검 뒤 순서는? | **G-K4 재계산부터 다시** | 봉인 점검(보충 31) PASS 뒤 G-K4 plant 원자료 재계산을 한 번 더(독립 검증 몫, 도구는 실행 전 고정) → V-B → VerifyVB. 검증 2차의 G-K4 재계산(4행 PASS)은 참고 기록으로만 둠. V-A·푸시는 그 뒤 사용자 결정 |
| D-K9-61 | 검증 2차 공개 사항·재현 사본은? | **공개 수용, 사본은 K9-2 끝까지 보관 (Recommended)** | 고정 전 노출·vg3t→vg3r·M2·M3 FZP 재계수 없음을 기록으로 수용. OK2/vg3r/jbcopy(4.1 GB) 는 다른 임시 트리와 함께 K9-2 뒤 정리 결정 |

- 작업 지시(메인 세션) 글이 D-K9-59를 더 자세히 적었습니다: "b9734abe와 K9-2 트리에 둘 다 있는 시험은 시험별 결과가 b9734abe의 결과와 같고, K9-2에 새로 생긴 시험은 모두 통과하면 PASS. 기준 결과는 실행 전에 고정한 도구로, b9734abe의 임시 분리 작업 트리에서 다시 냄(뒤에 지움, K8 브랜치는 건드리지 않음)". 이 보충은 이 글을 따릅니다(§3).

---

## 2. 봉인 뿌리 기록 훑기 (D-K9-58)

### 2.1 무엇이 멈췄나 [읽음 관문 보고 §3, 검증 2차 §6]

- 보충 30 사후 단계(post30)가 판정기 `AD30/k92t30_judge.py sealedscan`을 돌렸습니다. 결과 `OUTK/judge/sealed_records.json` = `ok=False`, 기록 134, s47로 셈 134, 나쁨 89. 구동기가 S-K10으로 멈췄습니다(`OUTK/STOP_a30_post.json`).
- 원인: `scan_vissim_blind(sealed=True)`(`k92t30_judge.py:359-371`)는 `str(seed) == '47' or _seed47_path(full)`이면 s47 기록으로 셉니다. `_seed47_path`(`:303-305`)는 **경로 전체**의 조각을 봅니다. 봉인 뿌리 이름 `sealed_s47`이 `_s47`로 끝나므로 봉인 뿌리 아래 모든 기록이 s47이 됩니다. v3c3-s31 42개·s43 47개(이유 `k92_vissim_ref`, VISSIM 값이 있는 것이 맞는 기록)가 "s47 블라인드 아님"으로 셈되었습니다. 실제 v3c3-s47 기록 45개는 모두 `vissim` null·이유 `k92_blind_s47`입니다.
- post30의 다른 두 점검(봉인 k92t 목록 같음, 앞 기록 바이트 같음)은 참이었습니다. `OUTK/stages/post.json`은 없습니다.

### 2.2 새 s47 판별 규칙 (정확한 글)

봉인 뿌리 기록 훑기에서 `k92_record.json` 하나가 **s47 기록**인 것은 다음 둘 가운데 하나가 참일 때입니다.

1. **seed 칸**: 기록의 `seed` 값을 글자로 바꾼 것이 `'47'`입니다(`str(d.get('seed')) == '47'`; 정수 47과 글자 "47" 모두). 이 줄은 보충 30 판정기 글 그대로입니다(함수 `scan_vissim_blind`는 바꾸지 않음).
2. **경로 조각**: 그 파일 경로의 **봉인 뿌리 아래 상대 경로**의 조각 가운데 하나가 s47 조각입니다.
   - **s47 조각** = 소문자로 바꾼 조각 p가 `p == 's47'`, 또는 `p`가 `_s47`로 끝남, 또는 `'_s47_'`가 `p` 안에 있음, 또는 `p`가 `s47_`로 시작함. 이 조각 규칙은 보충 30 판정기 글 그대로입니다(바꾸지 않음).
   - **봉인 뿌리 아래 상대 경로**: 경로 앞의 긴 경로 머리 `\\?\`를 먼저 뗍니다. 그 뒤 절대 경로로 바꾸고 대소문자·구분자를 맞춘 경로(`os.path.normcase(os.path.abspath(…))`)가 봉인 뿌리(`SEALED` = `OK2/sealed_s47`, 같은 방법으로 맞춤)와 **같으면** 상대 경로는 빈 글자(조각 없음)입니다. 봉인 뿌리 **뒤에 구분자가 이어지면** 그 뒤의 글자가 상대 경로입니다. 그래서 **봉인 뿌리 자신의 이름(`sealed_s47`)과 그 위의 조각은 조각으로 세지 않습니다.** 봉인 뿌리 아래 더 깊은 자리에 같은 이름의 폴더가 있으면 그것은 셉니다.
   - 봉인 뿌리 아래가 아닌 경로(구분자 없이 이름만 길게 이어지는 형제 폴더 포함)는 보충 30과 같이 **모든 조각**을 봅니다. 봉인 훑기는 봉인 뿌리만 걷기 때문에 이 경우는 생기지 않지만, 같은 함수를 쓰는 시작 훑기의 봉인 밖 부분(보충 30에서 이미 PASS, 다시 돌리지 않음)의 뜻이 바뀌지 않게 하려는 것입니다.
- s47 기록은 `vissim`이 null이고 `vissim_reason`이 `k92_blind_s47`이어야 합니다(보충 25 §6.5, 보충 30 그대로). 아니면 나쁨입니다.

**닫힌 진리표** (K = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`; 옛 = 보충 30 함수, 새 = 보충 31 함수; 경로 판별만, seed 칸과 별개) [실행 `AD31/dry/decl/dry_a31_truth.json` `/truth`, 22/22 기대와 같음]

| # | 경로 | 옛 | 새 | 까닭 |
|---|---|---|---|---|
| T1 | `K/sealed_s47`(봉인 뿌리 자신) | 참 | 거짓 | 뿌리 이름 제외 |
| T2 | `K/sealed_s47/K9-2-0/probe/sa/jobs/k92p0/TL3_1500_SAF_OBS_H3/k92_record.json` | 참 | 거짓 | v3c3-s31 꼴, s47 조각 없음 |
| T3 | `K/sealed_s47/K9-2-1/probe/sa/jobs/k921/TL3_1050_s43_SAF_OBS_H3/k92_record.json` | 참 | 거짓 | `_s43_`는 s47 조각 아님 |
| T4 | `K/sealed_s47/K9-2-1/probe/sa/jobs/k921/TL3_900_s47_SAF_OBS_H3/k92_record.json` | 참 | 참 | `_s47_` |
| T5 | `K/sealed_s47/K9-2-2/probe/sa/cap/k922/TL3/000900_s47/SAF/capture.json` | 참 | 참 | `000900_s47`(끝이 `_s47`) |
| T6 | `K/sealed_s47/K9-2-0/s47/x/k92_record.json` | 참 | 참 | 조각 = `s47` |
| T7 | `K/sealed_s47/K9-2-0/s47_extra/k92_record.json` | 참 | 참 | `s47_`로 시작 |
| T8 | `K/sealed_s47/K9-2-0/v3c3-s47/k92_record.json` | 참 | 거짓 | 붙임표 `-s47`은 조각 규칙 밖(보충 30 규칙 그대로; seed 칸이 47이면 seed로 셈) |
| T9 | `K/sealed_s47/K9-2-0/s470/k92_record.json` | 참 | 거짓 | `s470`은 s47 조각 아님 |
| T10 | `K/sealed_s47/K9-2-3/sealed_s47/k92_record.json` | 참 | 참 | 뿌리 아래 같은 이름 폴더는 셈 |
| T11 | `K/sealed_s47/k92t/logs/f_f_off_jobs.log` | 참 | 거짓 | 상대 조각 `k92t`·`logs`·파일 이름에 s47 조각 없음 |
| T12 | `\\?\D:\VISSIM_runs\…\k92_b1\sealed_s47\K9-2-0\probe\sa\jobs\k92p0\TL3_1500_SAF_OBS_H3\k92_record.json` | 참 | 거짓 | 긴 경로 머리를 뗀 뒤 뿌리 아래 |
| T13 | `\\?\D:\…\sealed_s47\K9-2-1\probe\sa\jobs\k921\TL3_900_s47_SAF_OBS_H3\k92_record.json` | 참 | 참 | 같음, `_s47_` |
| T14 | `d:/vissim_runs/20261001_V3C3/REPORTS/k8/K92_B1/SEALED_S47/K9-2-0/x/TL3_1500_SAF_OBS_H3/k92_record.json` | 참 | 거짓 | 대소문자 무시로 뿌리 아래 |
| T15 | `K/sealed_s47_old/K9-2-0/x.json` | 참 | 참 | 형제 폴더(구분자 없음) → 모든 조각, `sealed_s47_old`에 `_s47_` |
| T16 | `K/sealed_s47x/K9-2-0/x.json` | 거짓 | 거짓 | 형제 폴더, s47 조각 없음 |
| T17 | `K/probe/sa/jobs/k92p/TL3_900_s47_SAF_OBS_H3/k92_record.json` | 참 | 참 | 봉인 밖, 그대로 |
| T18 | `K/probe/sa/jobs/k92p/TL3_1500_SAF_OBS_H3/k92_record.json` | 거짓 | 거짓 | 봉인 밖, 그대로 |
| T19 | `K/commit/K9-2-0/sealed_s47_index.json` | 참 | 참 | 봉인 밖, 그대로(`_s47_`) |
| T20 | `probe/sa/jobs/TL3_1500_SAF_OBS_H3/k92_record.json`(상대 경로) | 거짓 | 거짓 | 봉인 밖, 그대로 |
| T21 | `x/TL3_900_s47_SAF_OBS_H3/k92_record.json`(상대 경로) | 참 | 참 | 봉인 밖, 그대로 |
| T22 | `D:\VISSIM_runs/20261001_v3c3\reports/k8/k92_b1\sealed_s47/K9-2-0/x/TL3_1500_SAF_OBS_H3/k92_record.json`(구분자 섞임) | 참 | 거짓 | 구분자를 맞춘 뒤 뿌리 아래 |

- 봉인 밖 경로(T15–T22)의 결과는 옛·새가 모두 같습니다. 바뀌는 것은 봉인 뿌리와 그 아래 경로뿐입니다.
- **[검토] 규칙이 못 보는 꼴(한계)과, 실제 봉인 뿌리에서 그 꼴이 없는 근거.**
  - 못 보는 꼴 [실행 `RV31/rv_s47rule.py`, 합성 경로·합성 봉인 뿌리만]: seed 칸이 `'47'`이 아니고(칸 없음, 47.0 같은 실수, `v3c3-s47` 같은 글자) **동시에** 봉인 뿌리 아래 상대 경로에 s47 조각이 없는 기록(예: 폴더 `v3c3-s47`·`seed47`·`s47-run`·`s47.d`, 파일 이름 `k92_record_s47.json`); 읽지 못하는 기록(JSON 오류)이 s47 조각 없는 자리에 있을 때; 이름이 정확히 `k92_record.json`이 아닌 기록 파일(훑기가 읽지 않음, 보충 30 그대로). 이 꼴들은 판정기를 더 고치지 않고(D-K9-58은 `_seed47_path` 한 함수만 허용) 아래 사실과 §4.3 V2로 닫습니다.
  - 실제 봉인 뿌리 [읽음 `KB/vgates3/out/post.json` `/record_scan`, 검증 2차가 J·F 값 고정 뒤 열람 기록을 남기고 낸 값]: `k92_record.json` 134개 모두 seed 칸이 있고 글자로 `'31'` 42 · `'43'` 47 · `'47'` 45, 그리고 "seed = 47"과 "봉인 뿌리 아래 상대 경로에 s47 조각 있음"이 어긋나는 기록 0(`seed_field_vs_path` 0). 곧 실제 s47 기록 45개는 **두 길(seed 칸·경로) 모두로** 잡히고, s31·s43 기록 89개는 어느 길로도 s47로 세지 않습니다.
  - 실제 이름 [실행 `RV31/rv_idx31.py`, 봉인 뿌리 **밖**의 봉인 목록 `OK2/commit/K9-2-{0,1,2,3}/sealed_s47_index.json`의 `inventory` 이름만, 봉인 뿌리 파일 열기·목록 0]: 봉인 뿌리의 커밋 묶음 넷(K9-2-0…3) 파일 12,538개(3,573 · 4,072 · 4,072 · 821, 검증 2차의 봉인 목록 대조 개수와 같음) 가운데 정확히 `k92_record.json`인 것 134개(K9-2-0 26 · K9-2-1 54 · K9-2-2 54 · K9-2-3 0); 나머지 맨 위 둘(`a27` 실행 출력 1개, `k92t` F 잡 로그 3개, `OK2/a27/sealed_index.json`·`OK2/a30/sealed_k92t_index.json`)에는 record 이름이 없습니다. 그 134개 경로에 새 함수만 걸면(seed 칸 없이) s47 45개, 긴 경로 머리 꼴(`\\?\`)로도 45개, 옛 함수는 134개. 이름에 `record`가 든 다른 파일은 `k91_record.json` 212개뿐이고(§9-15), `k92_vissim_ref.json`은 0개입니다.
  - 기록을 쓰는 코드 [읽음 GWT8 `e27ceac8` `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_record.py:202-206`, `:215-218`]: 정상 기록은 늘 `seed`(잡의 seed)를 적고 `vissim`은 늘 null입니다(이유 = seed 47이면 `k92_blind_s47`, 아니면 `k92_vissim_ref`). 기록 만들기가 실패한 예비 기록(`:215-218`)만 `seed` 칸이 없습니다. 그 기록도 잡 폴더 이름(= 잡 라벨, seed 47이면 `_s47_`가 듦)이 s47 조각이므로 경로 길로 잡힙니다 [추론; 실제 134개에는 예비 기록이 없음 — seed 칸 없는 기록 0].
  - 그래서 s31·s43 기록을 s47로 세는 일과 실제 s47 기록을 놓치는 일은 이 봉인 뿌리에서 생기지 않습니다. 생겨도 scan31의 개수 조건(134/45/0, §2.4)이 STOP으로 바꿉니다: 놓치면 s47이 45보다 작아지고, s31·s43을 s47로 세면 그 기록의 `vissim_reason`이 `k92_vissim_ref`라 나쁨이 1 이상이 됩니다.

### 2.3 새 판정기 파일 [실행 sha256, `dry_a31.py static`]

| 파일 | sha256 | 크기 |
|---|---|---|
| `AD31/k92t31_judge.py`(새 판정기, LF) | `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c` | 53,192 B, 961줄 |
| `AD31/base/k92t30_judge.py`(보충 30 판정기 바이트 사본) | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` | 52,254 B |
| `AD31/A31_JUDGE.diff`(옛 → 새 통합 차이) | `fc9ce7b668936d07f52354d3a8f2e3274d68aff5f69d209bd53c75ad9be97e87` | 1,296 B, 26줄 |

- 새 판정기 = `AD30/k92t30_judge.py`의 사본에서 **`_seed47_path` 한 함수만** 바꾼 것입니다. 모듈 머리글·상수와 다른 최상위 함수 36개(모두 37개)의 글은 바이트 같습니다(최상위 함수 이름 집합 같음, 바뀐 것 = `['_seed47_path']`, 함수 밖 모듈 글 같음, 차이 덩어리 1개, 새 import 0) [실행 `dry/decl/dry_a31_static.json`]. 머리글이 "amendment 30"이라고 적힌 것도 그대로 둡니다(그 함수만 바꾸라는 결정 글을 따름).
- 차이(`A31_JUDGE.diff` 전문):

```diff
--- a30decl/k92t30_judge.py
+++ a31decl/k92t31_judge.py
@@ -301,7 +301,22 @@
 
 
 def _seed47_path(path):
-    parts = [p.lower() for p in re.split(r'[\\/]', str(path))]
+    """Amendment 31 (D-K9-58): an s47 piece is a path piece p (lower case) with p == 's47', p ending in '_s47',
+    '_s47_' in p, or p starting with 's47_' (the amendment-30 piece rule, unchanged).  A path at or under the sealed
+    root SEALED is read by its pieces RELATIVE to SEALED: the sealed root's own name ('sealed_s47') and every piece
+    above it are not pieces of that path; a deeper piece of the same name still counts.  Any other path is read by
+    all its pieces, as in amendment 30.  The long-path prefix \\\\?\\ is dropped first; the prefix test is
+    case-insensitive (os.path.normcase) and needs a separator after the root."""
+    s = str(path)
+    if s.startswith('\\\\?\\'):
+        s = s[4:]
+    full = os.path.normcase(os.path.abspath(s))
+    root = os.path.normcase(os.path.abspath(str(SEALED))).rstrip('\\/')
+    if full == root:
+        s = ''
+    elif full.startswith(root + os.sep):
+        s = full[len(root) + 1:]
+    parts = [p.lower() for p in re.split(r'[\\/]', s)]
     return any(p == 's47' or p.endswith('_s47') or '_s47_' in p or p.startswith('s47_') for p in parts)
```

- `scan_vissim_blind`(`k92t31_judge.py:323-387`; 봉인 부분 `:374-386`)과 `cmd_sealedscan`(`:410-417`)은 글 그대로입니다. 봉인 부분은 SEALED 아래 `k92_record.json`만 읽고(`seed`·`vissim`·`vissim_reason` 칸, 메모리 안), 출력은 개수·참거짓·나쁜 기록의 경로뿐입니다 [읽음].
- 이 사본은 커밋하지 않습니다(보충 30 판정기와 같이 스크래치 도구).

### 2.4 다시 돌리는 것 — `scan31` 하나 (`k92t31.py:405-433`)

- **다시 돌리는 것은 봉인 뿌리 기록 훑기 하나뿐입니다.** 명령(구동기 `chain31` 안에서 한 번, 자식 프로세스, 작업 폴더 AD31, BelowNormal, `PYTHONHASHSEED=0`):
  `python -B AD31/k92t31_judge.py sealedscan --dest OK2/a31/sealed_records_a31.json`
- **출력 이름(보관 파일을 덮지 않음)**: `OUT31/sealed_records_a31.json`(판정기 출력), `OUT31/scan31.json`(구동기 기록: 판정, rc, 개수, 기대 개수, 보관 파일 그대로 여부, 출력 sha), `OUT31/stages/scan31.json`, `OUT31/logs/scan31.log`(판정기 표준 출력 한 줄: 참거짓·개수), `OUT31/steps31.jsonl` 한 줄. **`OUTK/STOP_a30_post.json`·`OUTK/judge/sealed_records.json`은 보관으로 그대로 둡니다**(구동기가 실행 뒤 두 파일 sha를 다시 봄). OUTK에는 아무것도 쓰지 않습니다(`OUTK/stages/post.json`도 만들지 않음).
- **전에 보는 것**: 보충 31 고정(`a31_sha`), check31 기록 참, J·F 값 고정(두 sha가 LOG에 있고 파일 sha 같음), 출력 이름이 없음.
- **열람 기록**: 실행 직전에 구동기가 LOG에 자동 줄을 씁니다: 파일 = `OK2/sealed_s47/**/k92_record.json`의 seed·vissim·vissim_reason 칸(판정기 메모리 안), 목적 = 보충 31 봉인 뿌리 기록 훑기(D-K9-58), 시각(초까지). 보충 25 §6.4·보충 30 §4.5의 열람 기록 꼴입니다.
- **PASS 조건(모두)**: 자식 rc = 0; 출력 `ok` = 참; `n_bad` = 0; `sealed_records` = `{files: 134, s47: 45, bad: 0, ran: 참}`; 보관 두 파일 sha 그대로. 하나라도 아니면 STOP(S-K10, S-K46).
- **개수 134·45를 조건에 넣는 까닭**: 관문 단계 실패 진단과 검증 2차가 같은 자료를 이미 셌습니다(seed 31 = 42, 43 = 47, 47 = 45; 폴더별 K9-2-0 26·K9-2-1 54·K9-2-2 54) [읽음 관문 보고 §3 표, 검증 2차 §6]. 개수가 달라지면 봉인 뿌리가 바뀌었거나 훑기가 파일을 빠뜨린 것이므로 STOP을 늘리는 쪽으로 둡니다. 이 개수는 데이터를 본 뒤에 적은 값입니다(공개).
- **다시 돌리지 않는 것**: 보충 30의 다른 모든 단계(check30·seal30·f30·jb·post30의 봉인 k92t 목록 대조와 앞 기록 대조), 시작 훑기, J·F 판정, VISSIM 기준 도구. 기반·보충 30 구동기(`KT/k92t.py`, `AD30/k92t30.py`)의 명령은 이 보충 고정 뒤 하나도 돌리지 않습니다(S-K49).

### 2.5 합성 확인 [실행 `AD31/dry/decl/`]

| 확인 | 내용 | 결과 |
|---|---|---|
| 진리표 | §2.2 T1–T22를 옛·새 함수에 | 22/22 기대와 같음 |
| 합성 봉인 뿌리 A(실제 꼴 흉내, 뿌리 이름 `sealed_s47`) | 기록 6개(seed 47 블라인드 3, seed 31·43 VISSIM 쪽 있음 3) + 기록 아닌 파일 2 | 새: 6/3/0, ok 참. 옛: 6/6/3, ok 거짓(실제 STOP과 같은 꼴) |
| 합성 봉인 뿌리 B(위반 꼴) | seed 47인데 VISSIM 값 있음, seed 없이 `000900_s47` 아래 VISSIM 값 있음, 같은 자리 블라인드, 뿌리 아래 `sealed_s47` 폴더의 seed 31, seed "47"(글자) 블라인드, seed 31 VISSIM 값 | 새: 6/5/3, ok 거짓(위반 셋을 잡음). 옛: 6/6/4 |
| 망가뜨림 M1–M8 | M1 옛 함수, M2 긴 경로 머리 안 뗌, M3 대소문자 구별, M4 뿌리 뒤 구분자 안 봄, M5 `p == 's47'` 뺌, M6 모든 `sealed_s47` 조각 뺌, M7 부모 폴더 이름만, M8 봉인 아래는 경로로 안 셈 | 8/8 잡음(진리표 줄 또는 합성 개수가 달라짐) |
| 명령줄 | 새 판정기 자신의 `main()`에 `sealedscan --dest`(SEALED만 합성 뿌리로 바꿈) | A: rc 0, 6/3/0; B: rc 3, 6/5/3 |
| 구동기 합성 구동 | `k92t31.py stage_scan31`을 합성 판정기 사본(SEALED 줄만 합성 뿌리)·합성 보관 파일에 | A(기대 6/3/0) PASS, A(기대를 7로) STOP·`STOP_a31_scan31.json`, B STOP; LOG 열람 줄 있음 |

- 출력: `dry_a31_truth.json` `f044d4571f766e055acf2e141b8d7f469a39d4feb659e7ad3dc1d085e91bd29f`, `dry_a31_drv.json` `a380d78de7373e0e1482c3263d3fd586dfb0631da23975c539edadd02639ba69`, `dry_a31_static.json` `32ed47f297605608fe1eb784b76823518243419b6e9229da947211a29cc11978`.

---

## 3. jb_unit 규칙 (D-K9-59)

### 3.1 무엇 [읽음 관문 보고 §4, 검증 2차 §5]

- jb_unit(`steps.jsonl` 79줄, rc=1, 107.2 s): 요약 "2 failed, 95 passed, 92 subtests passed". 실패 둘 = `test_stopline_wiring.py::ConfigFlagTests::test_default_output_is_byte_identical`, `::test_arms_add_exactly_the_key`. 두 시험은 `make_config_n31.build()`의 바이트가 트리의 `config_n31_v2.json`과 같은지 봅니다. K9-1 같은 시험(`V4/sa/unit_k91t.log`)은 "97 passed"였습니다(그 트리의 설정 파일은 `319d07aa…`).
- 기반 구동기 `stage_jb`는 이 줄에 `must()`를 쓰지 않아 멈추지 않았습니다(주석 "failures are read by sa_gates from the log"). 보충 30 §5.3은 "모든 단계 실행 rc≠0 → STOP"이라고 적었습니다. 두 글이 어긋났습니다.
- J-b 판정 잎 45개는 같았습니다. 두 실패는 판정 단위 항목의 이름 꼴에 걸리지 않습니다 [읽음 관문 보고 §4].
- 4c 시험 파일 넷은 b9734abe와 e27ceac8에서 블롭이 같습니다 [실행 `git ls-tree`: `7b93f4f7`·`43f85d6a`·`baa8e7d0`·`ba8b437f` 모두 같음; `check31_decl.json` `/info/C11_blobs_equal` 넷 참]. K9-2가 바꾼 것은 시험이 부르는 코드(`runtime_setup.py`·`signal_head_observation.py`·하네스 `sa_*`)와 `make_config_n31.py`(함수 더함, `build()` 그대로) 등입니다 [실행 `git diff --stat b9734abe e27ceac8`, 31파일].

### 3.2 판정 규칙 (보충 30 §5.3을 jb_unit 한 줄에 한해 대신함)

- **PASS**: 아래 §3.3 정의로 셀 때
  - (가) 두 로그에 모두 있는 시험(시험 이름 = pytest 마디 이름)마다 결과가 같고,
  - (나) K9-2 로그에만 있는 시험은 모두 통과(행 결과 = PASSED 하나, 실패 항목 0)이고,
  - (다) b9734abe 로그에만 있는 시험이 0개입니다.
- **FAIL**: 위 가운데 하나라도 거짓. → STOP(S-K47), 사용자가 정합니다.
- **INCOMPLETE**: 어느 로그든 §3.3 해석 점검(P1–P10) 하나라도 거짓, 종료 코드가 0·1이 아니거나 로그와 어긋남(1 ⇔ 실패·오류 하나 이상), `platform` 줄이 서로 다름, `rootdir:` 줄이 자기 트리 뿌리가 아님, 기준 실행이 1,800 s 안에 끝나지 않음, 기준 실행을 만들지 못함. → STOP(S-K47).
- (다)는 D-K9-59 글에 없는 조건입니다. 시험 파일 넷의 바이트가 두 커밋에서 같으므로 한쪽에만 있는 시험은 생기지 않아야 합니다 [실행 §3.1]. 생기면 수집이 달라진 것이므로 STOP을 늘리는 쪽으로 둡니다. 보충 24 U 규칙(`k92_gates.judge_u`, `only_base` → 거짓)과도 같은 꼴입니다 [읽음 TREE `k92_gates.py:605-623`].
- 이 규칙의 판정기 = `AD31/k92t31_unit.py`(표준 라이브러리만, 프로젝트·하네스·k92t 구동기·판정기 import 0) [실행 static `imports`].

### 3.3 "같은 결과"의 정의 (`k92t31_unit.py:59-288`)

두 로그는 같은 명령(`python -B run_pytest_bn.py -v <넷>`)의 출력입니다. 시험마다 결과 = (행 결과 목록, 실패 항목 목록) 두 칸입니다.

- **행 결과 목록**: 그 시험의 `-v` 행에 찍힌 결과 낱말을 로그 순서대로 모은 것. 결과 낱말 없는 행(pytest 9가 하위 시험 앞에 찍는 "빈 행")은 아무것도 더하지 않습니다. 결과 낱말이 `[ n%]` 진행 표시와 함께 **혼자 한 줄**에 있으면 바로 앞의 빈 행 시험의 것입니다(시험이 자기 줄을 찍는 경우, 예: `K8_SA_CAPTURE_PROVENANCE`). 예: 통과 `['PASSED']`, 정리 단계 오류가 붙은 통과 `['PASSED', 'ERROR']`.
- **실패 항목 목록**: 그 시험의 "short test summary info" 줄(FAILED / ERROR / SUBFAILED)마다 `[종류, 꼬리표, 메시지]`. 꼬리표 = SUBFAILED와 시험 이름 사이 글자(예: `[B]`, `(i=1, tag='t')`), 그 밖은 빈 글자. 메시지 = FAILURES / ERRORS 절에서 그 항목에 짝지어진 덩어리의 **첫 `E` 줄**. 덩어리와 항목은 순서대로 짝짓습니다(FAILED·SUBFAILED ↔ FAILURES, ERROR ↔ ERRORS). 요약 줄 끝의 메시지는 터미널 폭에서 잘리므로 쓰지 않습니다.
- **정규화**(보충 24 U 규칙 `k92_gates._norm_msg` 글 그대로 [읽음 TREE `k92_gates.py:594-602`]): 역슬래시 → `/`; 뿌리 목록의 각 뿌리 → `<root>`(긴 것부터, 대소문자 무시); `0x<16진>` → `0x?`; `pytest-<수>` → `pytest-N`. 그 뒤 300자로 자릅니다(U 규칙은 자른 뒤 정규화; 이 판은 정규화 뒤 자름 — 뿌리 길이가 달라도 같은 자리에서 자르려는 것). 꼬리표에도 같은 정규화를 씁니다. 뿌리 목록(양쪽에 모두 씀) = WT, TREE, UB, JB, CAP, WT의 git 폴더, jb_unit의 `GIT_DIR`(`D:/VISSIM-merge/repo/.git/worktrees/sim3-n31-k8`).
- **같음** = 두 칸이 정확히 같음(실패 항목 목록은 정렬해서 비교).
- **보고만**: 최종 줄의 "subtests passed" 수, 통과가 아닌 공통 시험 목록(알려진 실패), 두 쪽 개수.
- **해석 점검(P1–P10)**, 하나라도 거짓이면 그 로그는 INCOMPLETE:
  - P1 `collected N items` 줄이 있고 수집 오류가 없음.
  - P2 행은 그 줄과 첫 `=== … ===` 절 줄 사이에서만 읽음.
  - P3 혼자인 결과 낱말 앞에는 빈 행이 있음.
  - P4 실행 부분 끝에 결과 없는 빈 행이 남지 않음.
  - P5 결과가 하나 이상인 시험 수 = N.
  - P6 최종 줄 `=== … in <초>s ===`가 있고 `Interrupted` 줄이 없음.
  - P7 최종 개수: passed = PASSED 낱말 수, failed = FAILED 낱말 수 + SUBFAILED 항목 수, error(s) = ERROR 낱말 수, skipped = SKIPPED, xfailed = XFAIL, xpassed = XPASS(없으면 0).
  - P8 FAILED 항목의 시험 이름 모음 = FAILED 낱말의 시험 이름 모음(ERROR도 같음), SUBFAILED 항목의 시험은 행에 있음.
  - P9 FAILURES 덩어리 수 = FAILED + SUBFAILED 항목 수, ERRORS 덩어리 수 = ERROR 항목 수.
  - P10 짝지은 덩어리 제목에 그 시험의 마지막 `::` 조각이 들어 있음(SUBFAILED는 제목이 꼬리표로 끝남). 덩어리 제목 = `_+ <제목> _+` 꼴 줄 가운데 제목이 `_`·빈칸만이 아닌 것(pytest의 `_ _ _` 프레임 구분 줄은 제목 아님).
- **비교하지 않는 것(한계, 공개)**: 건너뜀 까닭(`-v` 로그에 없음), 첫 `E` 줄 뒤의 메시지 줄, 하위 시험별 통과(수만 보고). 보충 24 U 규칙은 junit XML에서 건너뜀 메시지까지 봤습니다. jb_unit은 junit 없이 `-v` 로그만 남겼으므로 이 판은 그 로그에서 볼 수 있는 것만 봅니다.

### 3.4 기준 결과를 만드는 법 (`k92t31.py:437-547` `base_env`·`stage_unit31`)

- **도구 고정**: 구동기 `AD31/k92t31.py`와 비교기 `AD31/k92t31_unit.py`의 sha는 보충 31 고정 목록(§8)에 들고, 적용 G1에서 LOG에 고정된 뒤에만 기준 실행을 합니다. 기준 실행 뒤 두 파일을 고치면 S-K12.
- **순서(한 번, 사슬 안)**:
  1. 앞 확인: 보충 31 고정, check31·scan31 기록 참, GWT8 상태(head `e27ceac8`, 브랜치, status 0줄)·K8 브랜치 = `b9734abe`, WT 자리·관리 폴더 없음·`git worktree list`에 없음, 선택 = 넷(b9734abe에 `git cat-file -e`로 있는 파일만; 지금 넷 모두 있음).
  2. 만들기: `git -C GWT8 worktree add --detach D:/VISSIM-merge/k8_gate_trees/k92b1/a31_wt_b9734abe b9734abe1c83f95c9cec5fca5e42b7b18cd45991`(rc 0). 브랜치를 만들지 않습니다(`--detach`). K8 브랜치·GWT8 작업 파일은 건드리지 않습니다. 자리 `TK/a31_wt_b9734abe`는 보충 27 §2.1의 `TK/<이름>` 꼴이고, 이 트리는 결정 출력을 만들지 않으며 N 비교에 쓰지 않습니다.
  3. 만든 뒤 확인: WT head = b9734abe, WT status 0줄, GWT8 상태·K8 브랜치 그대로. WT의 git 폴더를 기록.
  4. 보고만: WT 대 `TK/b9_ref`(git archive b9734abe) 바이트 비교(캐시·`.git` 파일 뺌; 바뀜·한쪽 개수와 이름 20개). 예상 = 차이 0(새 작업 트리는 archive와 같은 줄바꿈) [추론, §3.6-1].
  5. 기준 실행: 아래 환경으로 `python -B SP/k8b_impl/run_pytest_bn.py -v <넷>`, 작업 폴더 = WT, 표준 출력·오류 → `UB/unit_b9734abe.log`, BelowNormal, 시간 상한 1,800 s(jb_unit 107.2 s의 약 17배). 환경 줄 기록 `UB/unit_b9734abe.meta.txt`(jb_unit `.meta.txt`와 같은 꼴).
  6. 보고만: 실행 뒤 WT의 `git status --porcelain --untracked-files=all` 줄 수와 앞 20줄.
  7. 지우기(앞에서 무슨 일이 있어도 `finally`에서): `git -C GWT8 worktree remove --force D:/…/a31_wt_b9734abe`. `--force`는 시험이 만든 추적 밖 파일 때문에 필요합니다. 그 뒤 WT 폴더 없음, 관리 폴더 없음, `git worktree list`에 없음, GWT8 상태·K8 브랜치 그대로를 확인합니다. 하나라도 거짓이면 STOP(S-K48). `git worktree prune`은 쓰지 않습니다(다른 작업 트리 관리 폴더를 지울 수 있음).
  8. 판정: `python -B AD31/k92t31_unit.py judge --base UB/unit_b9734abe.log --new OUTK/jb/sa/unit_k92t.log --base-root WT --new-root TREE --base-rc <기준 rc> --new-rc 1 --roots <JSON> --files <JSON> --dest OUT31/unit_judge.json`. K9-2 쪽 rc 1은 `steps.jsonl`의 `jb_unit` 줄 하나에서 읽습니다(check31 C12).
- **환경**(jb_unit의 환경 `k92t30.py:288-293`·`:425-443`에서 트리에 묶인 값만 기준 쪽으로 옮김):

| 변수 | jb_unit(K9-2) | 기준 실행(b9734abe) |
|---|---|---|
| 작업 폴더 / `K8G_ROOT` | TREE | WT |
| `K8G_OUT` | JB(`OUTK/jb`) | UB(`OUT31/unit_base`) |
| `TMP`·`TEMP` | `JB/tmp` | `UB/tmp` |
| `GIT_DIR` | GWT8 작업 트리의 git 폴더(그 HEAD = 시험하는 커밋 e27ceac8) | WT의 git 폴더(그 HEAD = 시험하는 커밋 b9734abe) |
| `K8_SA_CAPTURE_ROOT` | CAP | CAP(같은 포착, 읽기만) |
| `K8_SA_BASE_REV`, `NUMBA_NUM_THREADS` | `ec063ffa`, `1` | 같음 |
| `PYTHONHASHSEED`, `PYTHONDONTWRITEBYTECODE`, `PYTHONUTF8` | `0`, `1`, `1` | 같음 |
| 지운 변수 | `RW_`·`K8_`·`K8G_`·`K92A_`로 시작하는 것 | 같음 |
| 파이썬 / 발사기 | Python312, `run_pytest_bn.py`(`fe4451e4…`) | 같음 |

- **같은 포착 뿌리를 쓰는 까닭**: 포착 시험(`test_stopline_approach_captured.py`)은 포착 뿌리의 `TL3/002700/{SAF,BASE}`·`T9C/002700/BASE`를 읽습니다 [읽음 `:54-125`]. 같은 입력에 코드만 다르게 해야 "K9-2 커밋이 시험 결과를 바꿨는가"를 봅니다. 포착 뿌리는 J-b 산출(봉인 아님)이고 시험은 읽기만 합니다(임시 폴더는 `TMP`) [읽음 `:530-541`]. K9-2가 그 포착에 남긴 것은 설정 값(`cfg.network`의 용량 값·`head_floor_seed` 사전)이고 새 클래스는 없습니다 [읽음 `runtime_setup.py`·`signal_head_observation.py` 차이] → b9734abe 코드로 풀 수 있을 것으로 봅니다 [추론].
- **기준 실행이 쓰는 곳**: WT(시험의 임시 폴더, 지움), UB, `OUT31`. OUTK·CAP·SEALED·TREE·GWT8 쓰기 0 [읽음 시험 글; 추론].

### 3.5 합성 확인 [실행 `AD31/dry/decl/dry_a31_unit.json` `85e74463…`, `dry_a31_drv.json` `a380d78d…`]

- 합성 시험 파일 넷(이름은 4c 넷과 같음, 내용은 합성: 통과, 자기 줄 찍기, 건너뜀, 하위 시험 통과·실패(뿌리 경로가 든 메시지), 바이트 비교 실패, 정리 단계 오류, xfail)을 두 뿌리(이름 길이 다름)에서 jb_unit 명령 꼴로 돌린 로그로 판정했습니다.

| 사례 | 내용 | 기대 | 결과 |
|---|---|---|---|
| U1 | 두 쪽 같음(알려진 실패·하위 시험 실패·정리 오류 포함) | PASS | PASS |
| U2 | 통과하던 시험이 K9-2 쪽에서 실패 | FAIL | FAIL |
| U3 | K9-2 쪽에 새 시험(통과) | PASS | PASS |
| U4 | K9-2 쪽에 새 시험(실패) | FAIL | FAIL |
| U5 | 기준 쪽에만 있는 시험 | FAIL | FAIL |
| U6 | 같은 시험이 다른 메시지로 실패 | FAIL | FAIL |
| U7 | K9-2 로그 끝(최종 줄) 잘림 | INCOMPLETE | INCOMPLETE |
| U8 | K9-2 rc를 0으로(실패 있음) | INCOMPLETE | INCOMPLETE |
| U9 | 기준 뿌리를 다른 이름으로 | INCOMPLETE | INCOMPLETE |
| U10 | 하위 시험 실패 꼬리표가 다름 | FAIL | FAIL |
| U11 | U1 로그 해석(자기 줄 찍기·정리 오류·xfail·건너뜀) | PASS | PASS |
| U12 | 최종 줄 passed 수 +1 | INCOMPLETE | INCOMPLETE |
| U13 | FAILURES·ERRORS 덩어리 제목 바꿔치기 | INCOMPLETE | INCOMPLETE |
| U14 | 두 쪽 모두 `mkdtemp` 무작위 이름이 든 메시지로 실패 | FAIL | FAIL |

- U14는 한계를 보입니다: 정규화는 무작위 임시 이름을 지우지 않습니다. 알려진 두 실패의 메시지에는 무작위 글자가 없습니다(바이트 비교 `assertEqual`의 줄인 repr) [읽음 `test_stopline_wiring.py:474-502`].
- 망가뜨림 UM1–UM8(비교기 글 한 곳씩): 행만 비교, 기준에만 있는 시험 무시, 새 시험 통과 안 봄, 뿌리 정규화 없음, 해석 점검 무시, rc 점검 무시, rootdir 점검 무시, 혼자인 결과 낱말 무시 → 8/8 잡음.
- 명령줄: `k92t31_unit.py judge …`(뿌리·파일 목록을 JSON 낱말로) 결과 = 함수 직접 호출 결과(같음, rc 0, PASS).
- 구동기 합성 구동(`drv`): 합성 git 저장소(커밋 base = U1 시험, 커밋 head = README + 시험)를 만들고 구동기 상수를 메모리에서 합성 자리로 바꿔 `stage_unit31`을 그대로 돌렸습니다. "같음"(head 시험 = base 시험) → PASS·종료 0, "바뀜"(head에서 통과 시험 실패) → FAIL·`STOP_a31_unit31.json`·종료 3. 두 경우 모두 임시 작업 트리를 만들고(HEAD = base, `GIT_DIR` = 그 트리의 git 폴더) 지웠고, 관리 폴더 없음·목록에 없음·저장소 상태 그대로였습니다. WT 대 b9_ref 보고는 0/0/0(합성 저장소는 `core.autocrlf=false`).

### 3.6 알려진 사실·한계

1. **CR 꼴**: GWT8 작업 트리는 10파일을 LF로 갖고 있고 `git archive`는 CRLF로 냅니다 [실행 `dry/decl/fact_wt_vs_archive.json` `83f65d57…`: GWT8 대 TREE 바뀜 10 = `TK/cr_only_files.json` 목록과 같은 10개, 한쪽 0, CR을 빼면 10/10 같음; `git ls-files --eol` 표본 둘(`stopline_approach.py`·`scripts/decision_hold.py`): 블롭 LF·속성 없음]. GWT8의 LF는 그 파일을 쓰고 커밋한 작업 트리에 남은 바이트로 보입니다 [추론]. 새로 꺼낸 작업 트리는 시스템 `core.autocrlf=true`(`C:/Program Files/Git/etc/gitconfig`)에 따라 archive와 같은 CRLF를 씁니다 [실행 합성 `dry/decl/autocrlf_probe.json` `cb495201…`]. 그래서 WT의 이 10파일도 CRLF로 TREE와 같을 것으로 봅니다 [추론]. 다르더라도, 그 가운데 4c 시험이 부르는 것은 `evaluation/controllers/stopline_approach.py`(실행 코드)와 `lane_offramp_runtime.py`(시험이 `read_text`로 읽어 `ast`·글자 세기)입니다. 파이썬 실행과 `read_text`는 줄바꿈을 가리지 않고, 시험의 다른 원문 비교는 `splitlines()`를 씁니다 [읽음 `test_stopline_wiring.py:289-341`]. 하네스의 S3 대조도 `\r\n`을 `\n`으로 바꿔 읽습니다 [읽음 `sa_s3parity.py:92`]. 그래서 영향이 없을 것으로 봅니다 [추론]. 시험 결과가 다르면 FAIL → STOP이고, 보고 항목(WT 대 b9_ref)이 원인 후보를 보입니다.
2. **이미 아는 것**: K9-2 쪽 요약(2 failed, 95 passed, 92 subtests passed)은 관문 단계·검증 2차가 읽었습니다(이 Declare 단계는 그 로그 내용을 열지 않았음). 메인 세션이 10-22에 b9734abe 임시 작업 트리에서 `ConfigFlagTests`만 돌려 같은 두 실패를 봤습니다. 그 실행은 고정 도구가 아니었으므로 참고로만 두고, 판정은 이 보충의 고정 도구가 냅니다.
3. **설정 정합 문제**(`make_config_n31.build()`가 `config_n31_v2.json`을 다시 못 만듦)는 고치지 않고 묶음 2 목록에 둡니다(D-K9-59). 코드 변경 0.
4. 이 규칙은 J-b 판정(45/45 같음, `judge/jb.json`)을 바꾸지 않습니다. jb_unit 줄의 처리만 정합니다.
5. `git worktree add`는 저장소 `.git/worktrees/` 아래에 관리 폴더를 만들고, `worktree remove`가 지웁니다. 브랜치·참조·커밋은 만들지 않습니다 [추론; 합성 구동에서 확인].
6. [검토] **GWT8·K8 브랜치를 건드릴 길이 없음** [읽음·실행]: 실제 저장소에 쓰는 git 명령은 구동기의 `worktree add --detach`(커밋 sha로, 브랜치 이름 아님)와 `worktree remove --force`(자리 = 상수 `TK/a31_wt_b9734abe`, GWT8 아님; `k92t31.py:52-54`, `:471-472`, `:513-514`) 둘뿐입니다. 구동기의 다른 git 호출은 `--no-optional-locks` 읽기입니다(`:180-185`). 4c 시험이 부르는 git은 `git -C ROOT log`·`git -C ROOT show <rev>:<경로>` 읽기뿐이고, 시험이 부르는 코드 쪽 git도 `rev-parse` 읽기뿐입니다 [읽음 b9734abe `test_stopline_wiring.py:44-78`; 넷의 `subprocess` 줄; `git grep`으로 찾은 b9734abe 코드(`diagnostics/sdmpc_n31_20260924`·`evaluation`·`src`)의 git 호출 17곳 가운데 쓰는 명령은 `tools/tests/launch_world.py`(자기 합성 저장소를 `git init`해 씀, 금지 시험 `test_tools_launch.py` 몫)뿐이고 4c가 부르지 않음; 나머지는 `show`·`log`·`rev-parse`·`archive`·`check-attr`·`apply --check`·`status` 읽기]. 저장소에 켜진 훅 0(`.git/hooks`에 `.sample`만), `core.hooksPath` 없음, b9734abe의 `.gitattributes`에 `filter=lfs`·`export-ignore` 0, 심볼릭 링크·서브모듈 0, 가장 긴 경로 185자(WT 뿌리 52자를 더해 237자 < 260) [실행 `git config`·`ls-tree`]. 그래서 `worktree add`가 LFS 내려받기·훅 실행·긴 경로 실패를 일으킬 자리가 없습니다.
7. [검토] **pytest 뿌리**: 트리와 그 위(`TK/a27`, `TK`, `D:/VISSIM-merge/k8_gate_trees`, `D:/VISSIM-merge`, `D:/`)에 `pytest.ini`·`pyproject.toml`·`tox.ini`·`setup.cfg`·`setup.py`·`conftest.py`가 없습니다 [실행]. 이때 pytest는 작업 폴더를 `rootdir`로 잡으므로(합성 실행 `dry/decl/cli_unit/*.log`의 `rootdir:` 줄과 같은 꼴) 두 쪽 모두 자기 트리 뿌리가 `rootdir`이고 시험 이름이 `diagnostics/…/tests/<파일>::…` 꼴입니다 [추론; K9-2 쪽 로그 내용은 열지 않음]. 아니면 비교기가 INCOMPLETE(P1·P5·`rootdir` 점검) → STOP입니다.
8. [검토] **시간 상한의 끝**: 1,800 s가 지나면 `subprocess.run`은 직접 자식(`run_pytest_bn.py`의 python)만 끕니다. 그 아래 자식(시험이 띄운 `probe`·`sa_worker` python)이 남아 WT 파일을 잡고 있으면 `worktree remove`가 실패할 수 있습니다. 그때는 S-K47·S-K48 STOP이고, G3가 남은 python 프로세스(PID·명령 줄 이름)를 보고에 적습니다. 남은 WT와 프로세스는 사용자 결정 없이 지우거나 끄지 않습니다.

---

## 4. 적용 순서와 그 뒤

공통: 보충 24 §3.1-4 그대로(무거운 Python 한 번에 하나, BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, 5분 넘는 단계는 WMI 분리 `KI/launch.ps1`, 기다림 확인 한 번에 9분 이하, 자기 PID만 끔, C:·D: 8 GB 밑이면 멈춤). 발사 줄: `powershell -NoProfile -File KI/launch.ps1 -Tag k92t31_chain -Script ..\a31decl\k92t31.py -ArgLine chain31`(태그 로그 `OK2/logs/k92t31_chain.txt`, 새 이름).

### 4.1 check31 — 사전 점검 (읽기만, 닫힌 목록; `k92t31.py:325-401`)

| # | 점검 |
|---|---|
| C1 | 보충 24–30 sha = `.sha256` = §0, 고정점 24–30 sha = §0 |
| C2 | 보충 31 sha = `.sha256` = 고정점 31 글 안의 64자 sha(`a31_sha`; apply만) |
| C3 | 결정 기록 앞 193줄 sha = `09974cfc…`(덧붙임만 허용) |
| C4 | GWT8 head = `e27ceac8…`, 브랜치 `claude/k92-b1-20261016`, K8 브랜치 = `b9734abe…`, status 0줄, `b9734abe..HEAD` = 6, 원격 k92 0 |
| C5 | `KB/k92t_pins.sha256` = `38a2ce14…` 56줄 OK; `KB/a30_pins.sha256` = `7afabd03…` 83줄 OK |
| C6 | `KB/a31_pins.sha256`(§8) 모든 줄 OK, 구동기·판정기·비교기 줄이 지금 sha로 들어 있음, 목록 sha가 고정점 31 글 안에 있음(apply만) |
| C7 | OUTK 보관 기록 26개 sha = `RECORDED31`(§8 101–115줄과 `k92t31.py:91-117`), OUT30 둘·`k92t30_chain.txt` sha = `OTHER31`; STOP 파일 = {`STOP_a30_post.json`, `STOP_f.json`}; 단계 기록 = 7개 이름; 판정 파일 = 7개 이름; `steps.jsonl` 102줄 |
| C8 | J·F 값 고정(두 sha가 LOG에, 두 파일 sha 같음) |
| C9 | 봉인 뿌리 맨 위 = 여섯; `SEALED/k92t/logs` = F 잡 로그 세 이름·크기(4,971 / 4,996 / 4,936 B) |
| C10 | OUT31 없음; WT 자리·관리 폴더 없음, `git worktree list`에 없음 |
| C11 | b9734abe에 4c 넷이 모두 있음(선택 = 넷); 넷의 블롭이 e27ceac8과 같은지는 보고 |
| C12 | `TK/a27/k92t.build.json` = `a1e98fa7…`·TREE 있음; `run_pytest_bn.py` = `fe4451e4…`; AD30 판정기와 그 사본 = `a1937942…`; `steps.jsonl`의 `jb_unit` 줄 하나 rc 1; CAP 있음 |
| C13 | VISSIM 0, 남의 러너·재생 프로세스 0(`KI/k92lib.py` `census`) |
| C14 | C:·D: 여유 ≥ 8 GB |

- 출력 `OUT31/check31.json`(OUT31을 처음 만드는 파일). 거짓이 하나라도 있으면 `OUT31/STOP_a31_check31.json`(S-K49).
- Declare 판 상태에서 `--mode decl`은 43점검 거짓 0입니다(C2·C6은 decl에서 셈하지 않음) [실행 `dry/decl/check31_decl.json` `05ec8b48…`].

### 4.2 적용 단계 (Apply A31; 하나라도 거짓이면 STOP, 다시 돌리지 않고 보고)

| # | 내용 | 통과 조건 |
|---|---|---|
| G0 사전 확인 | 보충 31 sha = `.sha256` = 고정점 31(64자). 결정 기록 앞 193줄 sha. 보충 24–30·고정점 sha(§0). `KB/k92t_pins.sha256` 56/56, `KB/a30_pins.sha256` 83/83. 고정점이 정한 기대 고정 목록(Declare 판은 `AD31/a31_pins.expected.sha256`)에 `sha256sum -c` 전부 OK·종료 0. GWT8 상태(C4). python·VISSIM 0. 드라이브 | 모두 참 |
| G1 고정 | 기대 고정 목록 바이트를 `KB/a31_pins.sha256`에 씀, `cmp` 같음, `sha256sum -c` 전부 OK, 그 sha·줄 수와 구동기·판정기·비교기 sha를 LOG 한 항목에 | 같음·OK·종료 0 |
| G2 사슬 | 발사 전 `sha256sum -c KB/a31_pins.sha256` OK → WMI `-Tag k92t31_chain -ArgLine chain31` → 기다림(9분 이하 간격, 프로세스 유무·`OUT31/stages/*.json`·`STOP_a31_*.json`·`steps31.jsonl` 이름·rc 칸만 봄; 로그 걸러 읽기 금지) | `OUT31/chain31.json` 있음, `OUT31/stages/unit31.json` `ok` 참, `STOP_a31_*` 0 |
| G3 마무리 | 끝 대조(`KB/a31_pins.sha256` 전부 OK), GWT8 head·status·K8·원격·`git worktree list`(WT 없음), [검토] python·VISSIM 프로세스 개수(남은 python은 PID·이름을 보고, §3.6-8), 보고서 `KB/GATES_K92B1_A31.md`(사본 `OK2/GATES_K92B1_A31.md`), LOG | 대조 OK, status 0줄, head = K9-2-5, 커밋 6개, 푸시 0, WT 없음 |

- **사슬 순서(`chain31`, 한 번)**: check31(apply) → 스냅숏 s35 → scan31 → s36 → unit31 → s37 → `OUT31/chain31.json`·LOG "사슬 끝". 스냅숏 이름 `OK2/snap/s35_a31_check.json`·`s36_a31_scan.json`·`s37_a31_unit.json`(기준 s02; 다르면 S-K11). `chain31`은 OUT31이 있으면 시작하지 않습니다.
- G2의 "종료 코드"는 `OUT31/steps31.jsonl`의 `rc` 칸입니다. 사슬 프로세스가 `chain31.json`도 `STOP_a31_*.json`도 없이 끝나면 G2 거짓 → STOP(S-K49). 진단으로 `OK2/logs/k92t31_chain.txt`(구동기 표준 출력: 단계 이름·rc·개수·판정만)의 끝을 열 수 있고 LOG에 파일·분·목적을 적습니다.
- G2 가운데 STOP하면 G3의 끝 대조·GWT8 점검·`git worktree list` 확인·보고서·LOG는 하고 사용자에게 넘깁니다. WT가 남아 있으면 지우지 않고(S-K48) 보고합니다.
- 보고서 머리에는 `GATES_K92B1_A30.md` 머리 공개(보충 27 §8·§13, 28 §9, 29 §11, 30 §10)와 이 보충 §5·§9를 옮겨 적습니다. jb_unit 줄은 "보충 31 §3 규칙(보충 30 §5.3을 이 줄에 한해 대신함)"으로 적습니다.
- 시간 어림 [추론]: check31 약 1분, 스냅숏 셋 × 약 1분, scan31 수 초, 작업 트리 만들기 1–3분, WT 대 b9_ref 보고 1–3분(2.1 GB 둘), 기준 pytest 약 2분(jb_unit 107.2 s), 지우기 1분 안, 판정 수 초. 합 약 10–15분.

### 4.3 독립 검증 A31 (보충 31 사슬 PASS 뒤; D-K9-60, 보충 24 §5.4)

- **때**: G3 보고서가 사슬 PASS(scan31·unit31 PASS)를 적은 뒤. 다른 결과면 하지 않습니다.
- **누가·도구**: 적용 단계와 다른 독립 검증 단계. 도구는 **새 파일**입니다. `vg_*`·`vg3_*`·`vglib`의 바이트 사본이 아니고, 그것들을 import하지 않습니다. 하네스(`sa_*`·`k92_*`·`k8b_*`), k92t 구동기·판정기(기반·30·31), `k92t31_unit.py`도 import하지 않습니다. 규칙은 이 보충·보충 29 §5의 글에서 따로 구현합니다.
- **고정**: 도구 sha256을 LOG에 적은 **뒤에만** 아래 자료를 처음 읽습니다: OUT31 출력(`UB/unit_b9734abe.log`·`OUT31/unit31_run.json` 포함), 봉인 뿌리 기록, G-K4 행의 원자료(옛·새 쪽 잡 파일), `rjg4.json`, [검토] K9-2 쪽 jb_unit 로그 `OUTK/jb/sa/unit_k92t.log`(V3이 읽음; OUT31 밖이라 따로 적음), CAP 파일 바이트와 기준 `KB/a31review/out/cap_manifest.json`(V4). 고정 전 시험은 합성 입력에서만 합니다. 첫 실행 뒤 도구를 고치면 결과와 무관하게 STOP(S-K12, S-K50).
- **할 일**:
  - V1 **G-K4 plant 원자료 재계산(D-K9-60)**: 보충 29 §5 글 그대로 — 행 K9-2-1 W·K9-2-2 B1 × {`TL3_1500_SAF_OBS_H3`, `TL3_1050_s43_SAF_OBS_H3`}, 옛 쪽 `OK2/probe_a25/plant/sa/jobs/k92p{W,B1}/<잡>`, 새 쪽 `SEALED/K9-2-{1,2}/plant/new/sa/jobs/k92{1,2}g4{W,B1}/<잡>`의 `summary.json`·`k92_record.json`, G0 plant G5 규칙(숫자 잎 비트 같음, 문자열 잎은 sha·hash 키와 보충 29 §5의 뿌리 넷 경로 글자 밖에서 같음, 한쪽 잎 0 → PASS; 숫자만 상대 1e-9 안 → EXPLAIN; 그 밖 FAIL). 통과 = 4행 모두 기록 `OK2/a27/judge/rjg4.json`(`246f28aa…`) plant 행 `verdict` = PASS와 파일별 `parts.<파일>.verdict` = PASS와 같음. v3c3-s47 잡 파일은 열지 않습니다.
  - V2 **봉인 훑기 다시 셈**: 봉인 뿌리의 `k92_record.json`을 §2.2 규칙(따로 구현)으로 세어 `OUT31/scan31.json`·`sealed_records_a31.json`의 판정·개수(134/45/0)와 같음. [검토] 같은 훑기에서 두 가지를 더 셉니다(§2.2 한계를 판정기 고침 없이 닫으려는 것, STOP을 늘리는 쪽): (가) seed 칸 값(글자로 바꾼 것)별 개수 = `{'31': 42, '43': 47, '47': 45}`(seed 칸이 없거나 다른 값인 기록 0), (나) "seed 칸 = `'47'`"과 "봉인 뿌리 아래 상대 경로에 s47 조각 있음"이 어긋나는 기록 0. 둘 가운데 하나라도 아니면 V2 다름 → STOP(S-K50). 이 값들은 검증 2차가 이미 낸 값입니다(`vgates3/out/post.json` `/record_scan`, 공개 P6).
  - V3 **jb_unit 판정 다시 셈**: `UB/unit_b9734abe.log`와 `OUTK/jb/sa/unit_k92t.log`를 §3.3 규칙(따로 구현)으로 읽어 `OUT31/unit_judge.json`의 판정, 공통·다름·한쪽 목록, 통과 아닌 공통 목록과 같음.
  - V4 **보관 그대로**: OUTK 보관 기록 26개·OUT30 둘·`k92t30_chain.txt` sha 같음(C7), 봉인 뿌리 맨 위 여섯(C9), WT 자리·관리 폴더 없음·`git worktree list`에 없음, K8 브랜치 `b9734abe`, GWT8 head·status. [검토] 그리고 J-b 포착 뿌리 CAP(`OUTK/jb/sa/cap/k92t`, 기준 실행이 읽은 자리)의 파일 목록·크기·바이트 sha256이 검토가 보충 31 데이터 전에 만든 기준 `KB/a31review/out/cap_manifest.json`(파일 3,944개, 1,690,146,202 B, 목록 sha256 `5340ac03da81742dd864044f9922a75bed1e542147249d4a8699a6432e273038`; 파일 sha256은 고정점에)과 같음 — 파일이 늘거나 줄거나 바이트가 다르면 V4 다름 → STOP(S-K50). 이 기준은 J-b가 남긴 복사 기록 `OUTK/jb_copies.json`의 `caps` 960개와 바이트가 모두 같았습니다 [실행 `RV31/rv_capx.py`: 같음 960, 다름 0, 없음 0]. 기준 실행이 CAP를 읽기만 한다는 글(§3.4 "기준 실행이 쓰는 곳")의 확인입니다.
- **통과**: V1–V4 모두 같음·참 → PASS. 하나라도 다르면 STOP(S-K50; V1 다름은 S-K40도), 사용자가 정합니다.
- **열람 기록**: 봉인 기록·G-K4 행 파일을 열 때마다 LOG에 파일·시각(분까지)·목적("보충 31 독립 검증 V1/V2")을 적습니다(보충 25 §6.4).
- 검증 2차의 G-K4 재계산(`vgates3/out/gk4_plant.json` `3999f0cc…`, 4행 PASS)과 사후 재계산(`vgates3/out/post.json` `758c72ce…`)은 **참고 기록**으로만 둡니다(D-K9-60). V1·V2를 대신하지 않습니다.

### 4.4 K92_GATES_PASS와 V-B, VerifyVB

- **K92_GATES_PASS**(보충 24 §6 :361, 보충 30 §8로 넓힘)는 이 보충 뒤 다음이 모두 참일 때입니다: 커밋 관문(보충 27–29), J-0·J-a·J-b·F-1–F-3 PASS, 보충 30의 check30·seal30·fcount·지속성 `complete`, 보충 30 post30의 봉인 k92t 목록 대조·앞 기록 대조(참, 기록 그대로), **post30 봉인 훑기 대신 scan31 PASS**, **unit31 PASS**, **독립 검증 A31 PASS**, 그리고 검증 2차의 J·F 재계산 일치(기록).
- **V-B**: 보충 24 §14.1 그대로, 보충 27 §6.2·보충 29 §6.2가 바꾼 대로(트리 `TK/vb_e27ceac8` = `git archive` K9-2-5 + CR 고침(C), 첫 사슬 계산 전 `cr_pair(FRZ_K8b, V-B 트리)`·`cr_pair(FRZ_K8, V-B 트리)` 참; VB-I1 비교기 = K9-2-5 `k92_compare.compare`, 옛 뿌리 = 그 사슬 런의 동결본; 구동기 `KB/k92_vb/vb_chain.py`와 재계산기는 첫 사슬 계산 전에 sha를 LOG에 고정; 출력 `OK2/vb/`, 보고서 `KB/k92_vb/K92_VB_REPORT.md`; VB_INCOMPLETE → STOP). D-K9-37·D-K9-60이 순서를 정했으므로 K92_GATES_PASS 뒤 다시 묻지 않고 V-B로 갑니다.
- **VerifyVB**: V-B 보고 뒤 독립 검증 단계. 도구는 새 파일이고 V-B 구동기·재계산기·하네스를 import하지 않으며, V-B 출력을 처음 읽기 전에 sha를 LOG에 고정합니다. VB-I1–VB-I6 판정과 VB-M 표를 결정 JSON·`k92_record.json`에서 다시 내 V-B 보고와 같아야 합니다. 다르면 STOP(S-K50).
- **V-A·푸시**: VerifyVB 뒤 사용자 결정(승격 방식 포함, 보충 24 §14.2). 이 보충과 이 워크플로에서는 V-A 행동 0(S-K13).

---

## 5. 공개 (보고서 머리에 옮김)

- **P1 데이터 뒤 판정기 고침(D-K9-58)**: `_seed47_path` 한 함수를 보충 30 사후 데이터(`sealed_records.json` `517582ad…`)를 본 뒤 고쳤습니다. 보충 24 S-K12의 예외이며 사용자 결정입니다. 고친 규칙의 결과는 관문 단계 실패 진단과 검증 2차 재계산으로 이미 알려져 있습니다(블라인드 아님). 개수 조건(134/45/0)도 그 자료를 본 뒤 적었습니다.
- **P2 보충 30 §5.3 바꿈(D-K9-59)**: "모든 단계 실행 rc≠0 → STOP"을 jb_unit 한 줄에 한해 §3 규칙으로 대신합니다. 다른 단계에는 §5.3이 그대로입니다. 기반 구동기가 그 줄에서 멈추지 않아 J-b가 끝까지 돌았고, jb_unit 판정은 J-b 값 뒤에 합니다.
- **P3 메인 세션 `grep -rl`(D-K9-58 근거 줄)**: 10-22, J·F 값 고정 뒤, jb_unit 로그 자리를 찾으려 `OK2` 아래에서 `grep -rl`을 돌렸다가 멈췄습니다. 출력은 파일 이름뿐이고 내용 출력은 0입니다. 봉인 뿌리 파일도 걸러 읽혔을 수 있습니다(보충 25 §6.4의 뜻으로 "엶"). J·F 값 고정 뒤였으므로 여는 것 자체는 허용이지만, 그때 LOG에 파일·분·목적을 적지 않았습니다. 무엇을 찾았는지(찾는 글자)는 결정 기록에 없습니다.
- **P4 검증 2차 공개 수용(D-K9-61)**: (가) 도구 고정 전에 작업 지시 글에 관문 보고 요약(F 수치, J-b 45/45, 사후 STOP 진단)이 있었고, `steps.jsonl`의 이름·rc·초·일부 argv, OUTK 파일 이름, LOG post30 줄 개수 세기 한 번, V4의 J-a 옛 쪽 `summary.json` 블록 값을 봤습니다. (나) J-b 재현 사본 폴더를 `OK2/vg3t` → `OK2/vg3r`로 이름만 바꿨고, `vgates3/out/jb_repro.json` 안의 경로 글자는 옛 이름을 가리킵니다. (다) M2·M3의 VISSIM 쪽(머리 통과 수)은 FZP에서 다시 세지 않았습니다(M1은 97프레임 같음). `OK2/vg3r/jbcopy`(4.1 GB)는 다른 임시 트리와 함께 K9-2가 끝날 때까지 지우지 않습니다.
- **P5 이 Declare 단계**: OUTK 파일(jb_unit 로그 포함)은 바이트 sha만 셌고 내용은 열지 않았습니다. `check31 --mode decl`은 `steps.jsonl`의 줄을 읽어 `jb_unit` 줄의 이름·rc만 봅니다. 봉인 뿌리는 맨 위 이름과 `k92t/logs` 세 파일의 이름·크기만 봤습니다. 코드 트리 바이트 대조(GWT8 대 TREE)를 두 번 했습니다(같은 결과, 첫 출력 파일은 정리 때 지워 다시 냄). 합성 시험·합성 저장소만 돌렸습니다.
- **P6 결과 짐작**: scan31의 개수는 이미 알려졌고, jb_unit의 K9-2 쪽 요약과 두 실패의 b9734abe 재현(메인 세션, 참고)도 알려졌습니다. 이 보충의 판정은 그것을 고정 도구로 다시 내는 일입니다.

---

## 6. STOP 규칙 (보충 24 §8·25 §9·26 §7·27 §11·28 §7·29 §8·30 §7에 더함)

- **S-K46** 봉인 훑기(scan31): 판정이 PASS가 아님(자식 rc ≠ 0, `ok` 거짓, `n_bad` ≠ 0, 개수 ≠ 134/45/0, 보관 두 파일 sha 바뀜, 출력 이름이 이미 있음, J·F 값 고정 아님) → STOP(S-K10과 함께), 사용자가 정함.
- **S-K47** jb_unit: unit31 판정이 FAIL 또는 INCOMPLETE, b9734abe의 선택이 넷이 아님, 기준 pytest가 1,800 s를 넘음, 기준 실행을 만들지 못함 → STOP, 사용자가 정함.
- **S-K48** 임시 작업 트리: 만들기 전 GWT8·K8 상태가 다름, WT 자리·관리 폴더·목록 항목이 이미 있음, `worktree add` rc ≠ 0, WT head ≠ b9734abe 또는 status가 깨끗하지 않음, 만든 뒤·지운 뒤 GWT8·K8 상태가 다름, 지운 뒤 WT 폴더·관리 폴더·목록 항목이 남음, 선언한 자리 밖에 작업 트리를 만듦, 실제 저장소에 선언 밖 git 명령(쓰는 명령은 `worktree add --detach`·`worktree remove --force` 둘뿐; `worktree prune`·`branch`·`checkout`·`reset` 등 금지)을 씀 → STOP·보고(남은 WT는 사용자 결정 없이 지우지 않음).
- **S-K49** 이어 하기·사전 점검: check31 거짓(C1–C14 하나라도); 보충 31 sha·고정점 다름; `KB/a31_pins.sha256`·`a30_pins`·`k92t_pins` 대조 다름(발사 전·끝); OUTK·SEALED·TREE에 씀; 보관 출력(`STOP_a30_post.json`, `judge/sealed_records.json`)을 덮거나 바꿈; 보충 31 고정 뒤 기반·보충 30 구동기 명령을 돌림; `chain31`을 OUT31이 있는 상태에서 다시 돌림; `chain31` 밖에서 `check31 --dest`를 OUT31·OUTK 안으로 씀; 사슬이 `chain31.json`·STOP 파일 없이 끝남 → STOP, 사용자가 정함.
- **S-K50** 독립 검증 A31·VerifyVB: 다시 낸 결과가 기록과 다름(V1–V4, VB 재계산), 도구 sha를 첫 읽기 뒤에 고정, 첫 실행 뒤 도구 고침 → STOP, 사용자가 정함.
- 그대로: S-K10(사후 훑기; 이 보충에서는 scan31), S-K11(스냅숏 다름·봉인 시드·쓰기 금지 뿌리), S-K12(데이터 뒤 판정기·구동기·기준 변경; **예외는 D-K9-58의 `_seed47_path` 하나뿐**이고, 보충 31 고정 뒤 새 구동기·판정기·비교기 변경은 S-K12), S-K13(V-A 행동), S-K14(드라이브), S-K40(G-K4 plant 다름), S-K45(검증 도구). 보충 24–30의 나머지 규칙도 그대로입니다.

---

## 7. 보충 24–30이 바뀌는 곳 (그 밖은 그대로 구속)

| 자리 | 옛 내용 | 이 보충 | 근거 |
|---|---|---|---|
| 보충 30 §3.3·§4.5 사후 봉인 훑기 판정기(`scan_vissim_blind` → `_seed47_path`) | 기반 함수 글 그대로, 경로 전체의 조각 | 새 판정기 `AD31/k92t31_judge.py`: `_seed47_path` 한 함수만 — 봉인 뿌리 아래는 상대 경로 조각(뿌리 이름 제외), 그 밖은 그대로(§2.2) | D-K9-58 |
| 보충 30 §4.5 post30 (1) | 봉인 훑기 → `OUTK/judge/sealed_records.json`, ok 거짓이면 STOP | scan31 한 번(§2.4), 출력 `OUT31/sealed_records_a31.json`, PASS = ok·개수 134/45/0; 옛 출력·`STOP_a30_post.json`은 보관; post30의 (2)(3)은 기록 그대로(참) | D-K9-58 |
| 보충 24 S-K12(:400) | 데이터 뒤 판정기 변경 → STOP | `_seed47_path` 하나만 사용자 결정 예외(공개 P1) | D-K9-58 |
| 보충 30 §5.3(O7′) "모든 단계 실행 rc≠0 → STOP" | jb_unit 포함 | jb_unit 한 줄만 §3 규칙(b9734abe와 시험별 같음 + 새 시험 통과 + 기준에만 있는 시험 0) | D-K9-59 |
| 보충 30 §4.5·보충 29 §5 G-K4 plant 원자료 재계산 시점·누가 | post30 끝 뒤, k92t 독립 검증기 | 보충 31 사슬 PASS·G3 보고 뒤, 독립 검증 A31(도구는 첫 읽기 전 고정, §4.3 V1); 검증 2차 재계산은 참고 기록 | D-K9-60 |
| 보충 24 §6 K92_GATES_PASS(보충 30 §8로 넓힌 것) | … + post30 PASS | post30 봉인 훑기 대신 scan31 PASS, + unit31 PASS, + 독립 검증 A31 PASS(§4.4) | D-K9-58–60 |
| 보충 30 §10-15 봉인 뿌리 맨 위 여섯의 대조 | 다음 검증이 도구 고정 전 정함 | 사전 점검 C9(맨 위 여섯 이름, `k92t/logs` 세 파일 이름·크기)와 독립 검증 V4 | 보충 30 §10-15 |
| 보충 24 §14.1 V-B 뒤 | V-B 보고 → 사용자 V-A 질문 | V-B → VerifyVB(§4.4) → 사용자 V-A·푸시 결정 | D-K9-60 |

- 바꾸지 않는 것: F-1–F-3·J-0·J-a·J-b의 정의·문턱·표본·팔과 그 판정 파일, 지속성 보고, 봉인 이동(seal30), 비교 규칙(보충 21·27·29), G-K4 plant 재계산 규칙(보충 29 §5), 봉인 시드·블라인드 규칙, 커밋 K9-2-0…5와 그 관문 기록, V-B 정의(보충 24 §14.1·27 §6.2·29 §6.2). 푸시 0(V-A 사용자 결정 뒤에만). 코드 변경 0(설정 정합은 묶음 2 목록).

---

## 8. 고정 목록 (G1; `KB/a31_pins.sha256`, 133줄)

- 줄 꼴: `<sha256 64자> *<절대 경로, / 구분>`, LF, CR 0, 끝 줄바꿈 있음(보충 30 §9와 같음).
- **기대 파일** `AD31/a31_pins.expected.sha256`: sha256 `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e`, 133줄, 23,474 B [실행 `sha256sum -c` 133/133 OK]. G1이 쓰는 `KB/a31_pins.sha256`은 이 바이트와 같아야 합니다(반박 검토가 파일을 고치면 고정점이 새 기대 파일과 sha를 정합니다).
- **고정점 31이 적어야 하는 것(구동기가 기계로 봄)**: 고정판 보충 31의 sha256(64자; `a31_sha`)과 기대 고정 목록의 sha256(64자; check31 C6). Declare 판 보충 31의 sha는 고정점에 64자로 적지 않습니다(앞 16자만; 보충 29 §14.1 V4와 같은 까닭).
- C6 글자 점검 [실행 `dry/dev/make_pins_a31.py`]: 구동기를 `launch.ps1` 경로 꼴(`KI/../a31decl/k92t31.py`)로 불러 낸 구동기·판정기·비교기의 `'<sha> *<경로>'` 글자 셋이 기대 파일 안에 그대로 있음(참, 참, 참).
- **1–83줄** = `KB/a30_pins.sha256`(`7afabd03…`)의 83줄 그대로(1–56줄 = `KB/k92t_pins.sha256`; 57–83줄 = 보충 30 도구·확인 출력·OUTK 이어 받는 기록 11개·`k92t_chain.txt`·스냅숏 s02·s28).
- **84–133줄**:

| 줄 | 파일 | sha256 |
|---|---|---|
| 84 | `KB/a30_pins.sha256` | `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e` |
| 85 | `AD31/k92t31.py`(새 구동기) | `63b5aa229eeaf013f2136a838cf9e5be163a087771fc3a71ea3202b0ad12b53d` |
| 86 | `AD31/k92t31_judge.py`(새 판정기) | `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c` |
| 87 | `AD31/k92t31_unit.py`(jb_unit 비교기) | `a1d82bffb71660361b07b19a823c1ff79286d2add90a0a58fdda8376cc03c6e2` |
| 88 | `AD31/dry_a31.py`(데이터 없는 확인) | `15183681dc34316b92ae812ddad0d2c0eb3ae31d545037ed6023351b5678ac39` |
| 89 | `AD31/A31_JUDGE.diff` | `fc9ce7b668936d07f52354d3a8f2e3274d68aff5f69d209bd53c75ad9be97e87` |
| 90 | `AD31/base/k92t30_judge.py` | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` |
| 91 | `AD31/dry/fact_wt_vs_archive.py` | `2350b915391200fede098f38aabe5f5c92480b217a0c262df8c43376ce50f9e9` |
| 92–98 | `AD31/dry/decl/` `dry_a31_static.json` / `dry_a31_truth.json` / `dry_a31_unit.json` / `dry_a31_drv.json` / `dry_a31_drive.json` / `check31_decl.json` / `fact_wt_vs_archive.json` | `32ed47f2…` / `f044d457…` / `85e74463…` / `a380d78d…` / `f100dd6a…` / `05ec8b48…` / `83f65d57…`(64자는 §11) |
| 99–100 | `AD31/dry/autocrlf_probe.py` / `AD31/dry/decl/autocrlf_probe.json` | `b6f5a1e5…` / `cb495201…`(64자는 §11) |
| 101–115 | OUTK `STOP_a30_post.json`, `stages/{seal30,f,jb}.json`, `judge/{f_jobs,f,jb,sealed_records}.json`, `f_persist30/sa/k92_vissim_ref.json`, `jb_copies.json`, `jb/sa/gates/gates_k92t.json`, `jb/sa/unit_k92t.log`, `jb/sa/unit_k92t.meta.txt`, `steps.jsonl`, `driver.log` | `k92t31.py:91-117` `RECORDED31`의 같은 값 |
| 116–118 | `OUT30/check30.json`, `OUT30/sealed_k92t_index.json`, `OK2/logs/k92t30_chain.txt` | `f5b35a85…` / `3946b3fc…` / `7b734c3c…` |
| 119–124 | 스냅숏 `OK2/snap/s29_a30_check`·`s30_a30_seal`·`s31_a30_after_f`·`s32_a30_after_jb`·`s34_a30_gates_stop`·`s34b_a31decl` `.json` | `4c6a4406…` / `ce9d64ff…` / `b1b21c07…` / `61626480…` / `c3b4c0a3…` / `bb3fe248…` |
| 125–127 | `KB/GATES_K92B1_A30.md`, `KB/VERIFY_GATES_K92B1_r2.md`, `KB/GATES_K92B1.md` | `167e9e18…` / `5f7c1256…` / `3f3a069a…` |
| 128 | `OK2/a27/judge/rjg4.json`(G-K4 기록) | `246f28aa8cae77281d414a8cf774bd6c6c688d6929b726baf1e83c69448a82ec` |
| 129 | `TK/b9_ref.build.json` | `cace6ada47ef55e8a57c3e1d0f4b9e235b67cfa77c9508c9fbf884b41a2d7b2e` |
| 130–132 | `KB/vgates3/vg3_pins.sha256`, `vgates3/out/gk4_plant.json`, `vgates3/out/post.json`(검증 2차 참고 기록) | `a864482c…` / `3999f0cc…` / `758c72ce…` |
| 133 | `KB/a30apply/diag_sealedscan.py`(관문 단계 실패 진단 도구, 참고) | `bdac6ad09b825d02494e8b376f19667abc686554a353cf5c5baf4c7edafe2cb1` |

- 목록에 넣지 않는 것(창 안에서 바뀜): `KB/LOG.md`, 결정 기록(앞 193줄만 C3이 봄), 보충 31 자신과 고정점(구동기 `a31_sha`가 봄), OUT31·`OK2/snap/s35–s37`(적용 출력), 봉인 뿌리 파일(C9가 이름·크기만 봄).
- **고정 창**: G1부터 G3 끝 대조까지. 그 안에서 133개 가운데 하나라도 바이트가 바뀌면 S-K49. 발사 전·끝에 `sha256sum -c KB/a31_pins.sha256` 133줄 OK·종료 0.

---

## 9. 알려진 사실·한계 (G3 보고서·다음 검증 보고서 머리에 옮김)

1. **데이터를 본 뒤의 보충**: 보충 30 사후 STOP과 그 실패 진단, 검증 2차 결과를 본 뒤입니다. F·J-b 판정 값은 바꾸지 않습니다.
2. **판정기 예외 하나**: S-K12의 예외는 `_seed47_path`뿐입니다(P1).
3. **scan31은 블라인드 점검이 아님**: 개수 134/45/0은 이미 셌던 값입니다(P6).
4. **jb_unit 판정 시점**: J-b 값 뒤입니다(P2).
5. **CR 꼴 10파일**(§3.6-1): GWT8 작업 트리는 LF, archive(TREE)는 CRLF. 새 WT는 archive와 같은 CRLF일 것으로 봄 [추론; 합성 확인]; 달라도 시험 영향은 없을 것으로 봄 [추론]; 보고 항목이 실제를 보입니다.
6. **비교 범위**: 건너뜀 까닭·첫 `E` 줄 뒤 메시지·하위 시험별 통과는 비교하지 않습니다(§3.3). 무작위 임시 이름이 든 메시지는 같은 실패라도 다르게 셉니다(U14).
7. **같은 포착 입력**: 포착 시험은 K9-2 트리가 만든 J-b 포착을 b9734abe 코드로 읽습니다(§3.4). 이것은 "같은 입력, 다른 코드" 비교입니다.
8. **메인 세션의 b9734abe 실행(10-22)**: 고정 도구가 아니었고 참고로만 둡니다.
9. **`git worktree` 관리 폴더**: 만들고 같은 단계 안에서 지웁니다. 실패하면 남은 것을 지우지 않고 보고합니다(S-K48).
10. **D-K9-44 계속**: 기존 어댑터는 결정마다 봉인 시드·v3c3-s47 이름 파일의 sha를 계산합니다(기록만, 고침은 묶음 2).
11. **설정 정합**(`make_config_n31.py`·`config_n31_v2.json`)은 묶음 2 목록입니다(D-K9-59).
12. **메인 세션 `grep -rl`**(P3)과 **검증 2차 공개**(P4)를 받아들였습니다.
13. **임시 트리 보관**: `OK2/vg3r/jbcopy`(4.1 GB)와 다른 임시 트리(`TK/a31decl/su`·`drv` 합성 트리 포함)는 K9-2가 끝날 때 함께 정리 결정을 합니다(D-K9-61).
14. 보충 24 §2.6의 한계 1–13, 보충 25 §11, 보충 26 §10, 보충 27 §13, 보충 28 §9, 보충 29 §11, 보충 30 §10, `GATES_K92B1_A30.md` 머리 공개 N1–N7은 그대로입니다.
15. [검토] **훑기가 읽는 범위**: 봉인 뿌리 기록 훑기는 이름이 정확히 `k92_record.json`인 파일만 읽습니다(보충 25 §6.5·보충 30 그대로, 이 보충은 바꾸지 않음). 봉인 뿌리에는 그 밖에 `k91_record.json` 212개가 있습니다 [실행 `RV31/rv_idx31.py`·`rv_idxnames.py`, 봉인 목록의 이름만]. 이 파일은 K9-1 꼴 기록(요약의 `k91` 칸을 옮긴 것: `keyed`·`top`·`blocks`)이고 VISSIM 쪽 칸이 없습니다 [읽음 GWT8 `e27ceac8` `sa/sa_worker.py:392-399`]. 블라인드 규칙(VISSIM 쪽 null)은 `k92_record.json`에만 걸립니다.
16. [검토] **seed 칸·경로 두 길**: 판별 규칙의 한계(§2.2 [검토])는 실제 봉인 뿌리에서 닿지 않습니다(seed 칸 134/134 있음, 두 길 어긋남 0). 독립 검증 V2가 이것을 다시 셉니다(§4.3).

---

## 10. 자체 점검

1. **빈 칸**: "나중에 정함"·자리표가 없습니다. 아직 생기지 않은 값은 규칙으로 정했습니다: 보충 31 자신의 sha(`.sha256`·고정점 31), `KB/a31_pins.sha256`(G1 = 기대 파일 바이트), OUT31 기록(구동기가 쓰고 LOG에 sha), 독립 검증 도구 sha(첫 읽기 전 LOG), V-B·VerifyVB 도구 sha(첫 계산·첫 읽기 전 LOG).
2. **D-K9-58**: 판별 규칙 글(§2.2), 닫힌 진리표 22줄(§2.2), 새 판정기 = 사본 + 한 함수(§2.3, 차이 전문), 다시 돌리는 명령 하나와 출력 이름·보관(§2.4), 데이터 뒤 고침 공개(P1).
3. **D-K9-59**: 규칙(§3.2), "같은 결과"(§3.3), 기준 결과를 만드는 법(고정 도구, 임시 분리 작업 트리, 같은 선택을 b9734abe에 있는 파일로, 지우기; §3.4), 다르면 STOP(S-K47), 보충 30 §5.3 바꿈 공개(P2), 설정 정합은 묶음 2.
4. **D-K9-60**: 순서 적용 → 봉인 훑기 → jb_unit → 보고(§4.2) → 독립 G-K4 재계산(도구 먼저 고정, §4.3) → V-B → VerifyVB(§4.4); 검증 2차 재계산은 참고.
5. **D-K9-61**: P4, §9-13.
6. **새 STOP 규칙**: S-K46–S-K50(§6). **고정 목록**: §8(133줄).
7. **합성 확인만**: 새 도구는 합성 입력·합성 저장소에서만 돌렸고, 읽기 전용 사전 점검(`check31 --mode decl`)만 실제 자리를 읽었습니다(sha·이름·개수).
8. 판정 말 없음, 결과는 PASS·FAIL·보류·INCOMPLETE·STOP과 숫자.
9. [검토] 반박 검토가 고친 곳·확인·남은 것은 §12에 있습니다.

---

## 11. 파일 (AD31 = `KB/a31decl`)

| 파일 | sha256 |
|---|---|
| `k92t31.py`(새 구동기, LF, 609줄) | `63b5aa229eeaf013f2136a838cf9e5be163a087771fc3a71ea3202b0ad12b53d` |
| `k92t31_judge.py`(새 판정기, LF, 961줄) | `9dfc0b208c4f2fbd1abcd1eeb04bc066e29599aef63c5a5d59521a3311ee1d2c` |
| `k92t31_unit.py`(jb_unit 비교기, LF, 321줄) | `a1d82bffb71660361b07b19a823c1ff79286d2add90a0a58fdda8376cc03c6e2` |
| `dry_a31.py`(데이터 없는 확인, LF) | `15183681dc34316b92ae812ddad0d2c0eb3ae31d545037ed6023351b5678ac39` |
| `A31_JUDGE.diff` | `fc9ce7b668936d07f52354d3a8f2e3274d68aff5f69d209bd53c75ad9be97e87` |
| `base/k92t30_judge.py`(보충 30 판정기 사본) | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` |
| `dry/fact_wt_vs_archive.py`(작업 트리 대 archive 사실 확인) | `2350b915391200fede098f38aabe5f5c92480b217a0c262df8c43376ce50f9e9` |
| `dry/decl/dry_a31_static.json` | `32ed47f297605608fe1eb784b76823518243419b6e9229da947211a29cc11978` |
| `dry/decl/dry_a31_truth.json` | `f044d4571f766e055acf2e141b8d7f469a39d4feb659e7ad3dc1d085e91bd29f` |
| `dry/decl/dry_a31_unit.json` | `85e74463931d87044fdaac3bbf0cdcb9bf6fd7a5662d4fdd3032a75c5c201512` |
| `dry/decl/dry_a31_drv.json` | `a380d78de7373e0e1482c3263d3fd586dfb0631da23975c539edadd02639ba69` |
| `dry/decl/dry_a31_drive.json` | `f100dd6a52f6525cb0000e8feac450261c0a7ddcf298c745400eca4818a88c4d` |
| `dry/decl/check31_decl.json`(사전 점검 decl, 43점검 거짓 0) | `05ec8b48fe31c7cfe170bf851350e02f3371d016138007810facce42f1544c7e` |
| `dry/decl/fact_wt_vs_archive.json`(바뀜 10·한쪽 0) | `83f65d572cb0e6ab0d52181e8dd6bed6ee7b0c9ba5f5a184b1ad00a099619000` |
| `dry/autocrlf_probe.py`(합성 저장소 줄바꿈 확인) / `dry/decl/autocrlf_probe.json` | `b6f5a1e52fb4cbc7cd6f417a8ccc3cd510faa4f336965b88c37e4ffe5506e6a6` / `cb495201b81178d270be7466d0d0953d868d9debd17d31cb2ac558aac106738c` |
| `dry/decl/cli_sealedscan_A.json` / `_B.json`, `cli_unit/`, `mutants_unit/`, `synth_scan/`, `check31_decl.log`, `dry_a31_drv.stdout.txt`(합성·보조 출력, 고정 목록 밖) | `c97187d1…` / `c06c980d…` / — / — / — / `1b364c46…` / `91efa748…` |
| `a31_pins.expected.sha256`(133줄) | `bf1ca001e8c8a4215512582871ddf439971aff04887267a0b797b3496ddc6d4e` |
| `dry/dev/`(`project_fn.txt`·`fix_project.py`·`make_pins_a31.py`·`fix_text_crlf.py`, 개발 도우미; 마지막 둘은 고정 목록과 이 글의 숫자를 고친 도우미), `dry/dev0/`(pytest 출력 꼴 확인, 합성) | — |
| 합성 트리 `TK/a31decl/su`(U 사례), `TK/a31decl/drv`(합성 git 저장소·합성 봉인 뿌리·`autocrlf_probe`) | — |

- 새 도구·차이 파일·기대 고정 목록·확인 출력 JSON과 이 글은 줄 끝 LF, CR 0입니다. 기반 사본은 보충 30 바이트 그대로(LF)입니다 [실행].

---

## 12. 반박 검토 (ReviewDeclare, 2026-10-22 02:27–02:5x KST) — 고친 곳과 확인

- 검토는 Declare 판(`SP/K8_PREDECLARATION_AMENDMENT_31_r1.md`, `8a76e210230b69c0c21627f13eb7459e04f044d5ac62feac3cdcb2dd5c3d0cbc`; 사본 `RV31/r1/K8_PREDECLARATION_AMENDMENT_31_declare.md` 같은 바이트)을 읽고 다음을 했습니다: §0 sha 대조, 판정기 차이 다시 냄, 새 `_seed47_path`의 적대 경로 시험(합성 경로·합성 봉인 뿌리), 봉인 뿌리 **밖** 봉인 목록의 실제 이름에 규칙을 건 개수, 기록을 쓰는 코드 읽기, 구동기 `stage_unit31`·`base_env`와 4c 시험·`k8common`의 git·쓰기 자리 읽기, 저장소 훅·속성·경로 길이 확인, pytest 뿌리 조건 확인, J-b 포착 뿌리 바이트 기준 만들기, 새 데이터 0 확인(파일 시각), 검토 끝 `check31 --mode decl`.
- 하지 않은 일: VISSIM·COM·러너·동결·결정 재생·plant 잡 0. 실제 저장소 임시 작업 트리 0, b9734abe 시험 실행 0, 4c 시험 실행 0. 판정기·비교기를 실제 봉인 기록·jb_unit 로그에 부른 일 0. 봉인 뿌리 파일 내용 열람 0, jb_unit 로그 내용 열람 0. OUTK·봉인 뿌리·TREE·GWT8·저장소 `.git`·K8 브랜치·AD31 쓰기 0. 봉인 시드·codex 64cf 숫자 0. 커밋·브랜치·푸시 0. 금지 시험 0. 무거운 일 둘(CAP 바이트 목록, `check31 --mode decl`)은 `KI/launch.ps1`로 WMI 분리·BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번에 하나. 끈 프로세스 0. 끝에 python·VISSIM 0.
- 봉인 관련 공개: (가) 메타데이터 `find -newermt`로 봉인 뿌리의 10-21 23:42 뒤 바뀐 파일 수를 셌습니다(이름 출력 0, 개수 0). (나) 봉인 뿌리 밖의 봉인 목록 파일 여섯(`OK2/commit/K9-2-{0,1,2,3}/sealed_s47_index.json`, `OK2/a27/sealed_index.json`, `OK2/a30/sealed_k92t_index.json`)의 이름을 읽어 개수만 냈습니다. (다) 검증 2차 출력 `vgates3/out/post.json`의 `record_scan` 개수, `OUTK/jb_copies.json`의 `caps` 목록(경로·크기·sha), `OK2/a27/judge/rjg4.json`의 키 이름(값 아님)을 읽었습니다. 모두 J·F 값 고정 뒤이고, LOG에 적었습니다(2026-10-22 02:27 항목과 그 아래 줄).

### 12.1 고친 곳 (모두 글; 코드·문턱·판정 정의·고정 목록 바이트는 그대로)

| # | 구멍 | 고침 | 자리 |
|---|---|---|---|
| R1 | 새 판별 규칙이 못 보는 꼴(seed 칸이 `'47'`이 아니면서 s47 조각 없는 자리의 기록: 폴더 `v3c3-s47`·`seed47`·`s47-run`·`s47.d`, seed 47.0·`v3c3-s47` 글자, JSON 오류, 다른 파일 이름)과, 그 꼴이 실제 봉인 뿌리에 없다는 근거가 글에 없었습니다. "실제 s47 기록을 놓치지 않음"이 [추론]뿐이었습니다 | 합성 시험으로 한계를 적고, 실제 근거 셋(검증 2차 seed 칸 분포 `'31'` 42 · `'43'` 47 · `'47'` 45와 두 길 어긋남 0; 봉인 목록 이름에 새 함수만 건 개수 45, 옛 134; 기록 쓰는 코드는 seed를 늘 적고 예비 기록도 잡 라벨 조각으로 잡힘)과 개수 조건이 STOP으로 바꾸는 길을 적음 | §2.2 [검토] |
| R2 | 독립 검증 V2가 같은 규칙만 다시 세므로 규칙 자체의 한계는 검증에서도 닫히지 않았습니다 | V2에 seed 칸 값별 개수 `{'31': 42, '43': 47, '47': 45}`와 "seed = 47"·"상대 경로 조각" 어긋남 0을 더함(다르면 STOP, STOP을 늘리는 쪽). 판정기는 바꾸지 않음(D-K9-58 범위) | §4.3 V2, §9-16 |
| R3 | 독립 검증의 "처음 읽기 전 고정" 목록에 K9-2 쪽 jb_unit 로그(OUTK, V3이 읽음)가 빠졌습니다 | 목록에 더함(CAP 바이트·기준 목록도) | §4.3 고정 |
| R4 | 기준 실행이 J-b 포착 뿌리 CAP(OUTK 안)를 읽기만 한다는 글이 [읽음·추론]뿐이고, 실행 뒤 대조할 기준이 없었습니다(스냅숏은 OK2를 빼고, OUTK 보관 기록 26개에 CAP는 없음) | 검토가 보충 31 데이터 전에 CAP 바이트 목록을 만들고(3,944파일, 목록 sha `5340ac03…`; J-b 복사 기록 `caps` 960개와 바이트 같음), V4가 실행 뒤 같음을 봄 | §4.3 V4 |
| R5 | GWT8·K8 브랜치를 건드리지 않는다는 근거(쓰는 git 명령 둘, 시험의 git은 읽기, 훅·LFS·긴 경로)가 [추론]뿐이었습니다 | 읽은·실행한 근거를 적음 | §3.6-6 |
| R6 | 두 쪽 pytest `rootdir`가 자기 트리 뿌리라는 전제(비교기 INCOMPLETE 조건)의 근거가 없었습니다 | 트리와 그 위에 pytest 설정 파일·`setup.py`·`conftest.py` 없음 확인, 합성 실행과 같은 꼴 | §3.6-7 |
| R7 | 1,800 s 상한에서 손자 프로세스가 남는 경우의 처리가 없었습니다 | STOP·보고, 사용자 결정 없이 지우거나 끄지 않음; G3가 python·VISSIM 개수를 적음 | §3.6-8, §4.2 G3 |
| R8 | 훑기 범위 밖 `k91_record.json` 212개가 공개되지 않았습니다 | 범위(이름이 정확히 `k92_record.json`)와 그 파일에 VISSIM 칸이 없음을 적음 | §9-15 |

- R1–R8은 판정 정의·문턱·표본을 바꾸지 않습니다. R2·R4는 독립 검증에 STOP을 늘리는 조건을 더한 것이고(그 값들은 이미 알려짐, 공개 P6), 나머지는 공개·근거입니다. 새 구동기·판정기·비교기·`dry_a31.py`·차이 파일·확인 출력·기대 고정 목록(§8, `bf1ca001…`, 133줄)은 바꾸지 않았습니다.

### 12.2 다시 확인했고 문제없는 것

1. §0 sha 모두 같음, 기대 고정 목록 133/133 OK, `KB/k92t_pins.sha256` 56/56, `KB/a30_pins.sha256` 83/83, §11 파일 sha 같음 [실행].
2. **판정기 차이**: `diff AD30/k92t30_judge.py AD31/k92t31_judge.py` = `_seed47_path` 한 덩어리(옛 304줄 → 새 304–319줄)뿐, 기반 사본 = AD30 바이트(`a1937942…`), `A31_JUDGE.diff`가 그 차이 [실행]. `scan_vissim_blind`·`cmd_sealedscan`·`main` 글 그대로이고, 봉인 훑기는 `lp()`(`os.path.abspath`, `resolve` 없음)로 걸으므로 새 함수의 뿌리 맞춤과 같은 꼴입니다 [읽음 `k92t31_judge.py:168-170`, `:374-386`].
3. **적대 경로** [실행 `RV31/rv_s47rule.py` → `out/rv_s47rule.json` ok]: 진리표 T1–T22 옛·새 22/22; 더한 경로 24개(깊은 `s47` 폴더, 대문자 `S47`·`_S47`·`_S47_`, 뿌리와 같은 이름의 깊은 폴더, `s47_`로 시작하는 파일 이름, `_s47.json`으로 끝나는 파일 이름(거짓, 한계), `v3c3-s47`·`seed47`·`s47-run`·`s47.d`·`s470`(거짓, 한계), 겹친 구분자, 뿌리 안·밖의 `..`, 뿌리 끝 구분자, 긴 경로 머리와 소문자, 앞으로 빗금, 뿌리 이름 대문자, 앞으로 빗금 긴 경로 머리(뗄 수 없어 모든 조각 → 참, STOP 쪽; `lp()`는 이 꼴을 만들지 않음), pathlib 인자) 모두 기대와 같음; 합성 봉인 뿌리 12기록(seed 없음+조각, seed 없음+하이픈 폴더, seed 47.0, s43+깊은 `s47` 폴더, JSON 오류 둘, 다른 파일 이름, seed `"47"`, seed `v3c3-s47`) — 새 판정기 자신의 `scan_vissim_blind`가 기대대로 11/5/3, 옛 판정기 11/11/9.
4. **실제 이름** [실행 `RV31/rv_idx31.py` → `out/rv_idx31.json` ok]: §2.2 [검토]의 개수(134; 새 45, 옛 134; K9-2-0 26 · K9-2-1 54 · K9-2-2 54 · K9-2-3 0).
5. **새 데이터 0** [실행 파일 시각]: OUT31 없음; OUTK 마지막 수정 10-21 23:34:09(`STOP_a30_post.json`·`driver.log`·`steps.jsonl`), 10-21 23:42 뒤 바뀐 파일 OUTK 0 · 봉인 뿌리 0 · OUT30 0, 10-22 00:40 뒤 `vg3r`·`vg3t` 0; OK2에서 10-22 00:40 뒤 바뀐 파일은 Declare의 넷(`logs/a31decl_fact_wt.txt`·`a31decl_fact_wt2.txt`·`a31decl_snap.txt`, `snap/s34b_a31decl.json`)과 이 검토의 WMI 로그 둘(`logs/rv31_capman.txt`·`rv31_check31.txt`)뿐; `TK/a31_wt_b9734abe`·관리 폴더 없음, `git worktree list`에 없음; AD31의 확인 출력은 합성 뿌리 경로뿐(`cli_sealedscan_A/B` 6/3/0·6/5/3); LOG에 scan31·unit31 줄 0.
6. **GWT8·K8**: head `e27ceac8`, 브랜치 `claude/k92-b1-20261016`, status 0줄, K8 `b9734abe`, `b9734abe..HEAD` 6, 원격 k92 0 [실행]. 4c 시험 블롭 넷 두 커밋 같음, `config_n31_v2.json` 블롭 `268ae471` 두 커밋 같음 [실행].
7. **기준 실행 환경**: jb_unit 환경(`AD30/k92t30.py:288-293`, `:425-443`)과 `k92t31.py:437-443`이 트리에 묶인 값(`K8G_ROOT`·`K8G_OUT`·`TMP`·`TEMP`·`GIT_DIR`)만 다름; 같은 발사 방법(WMI, `launch.ps1`), 같은 파이썬·발사기 [읽음].
8. **포착 시험은 CAP를 읽기만**: 없으면 건너뜀(쓰지 않음), 일꾼 출력은 `tempfile.mkdtemp` = `UB/tmp` [읽음 b9734abe `test_stopline_approach_captured.py:105-120`, `:518-541`, `k8_gates/k8common.py:62-80`, `:126-173`]. 4c 시험의 다른 임시 폴더는 트리 안 tests 폴더(WT, 지움)입니다 [읽음 `test_stopline_approach.py:111-137`, `test_stopline_evidence.py:132-147`].
9. **스냅숏**: `KI/k92snap.py:15-27` 뿌리는 OK2·TK를 빼므로 OUT31·WT가 s35–s37을 다르게 만들지 않음 [읽음].
10. **G-K4 재계산 순서·고정**: 사슬 PASS·G3 보고 뒤, 새 도구, 첫 읽기 전 LOG 고정, 규칙 = 보충 29 §5 그대로; 기록 `rjg4.json`의 칸 이름(`rows/plant_K9-2-{1,2}_<잡>/verdict`, `parts/{summary.json,k92_record.json}/verdict`)이 V1 글과 맞음 [읽음 키 이름만]. D-K9-60("봉인 점검 PASS 뒤")보다 늦은 자리(unit31 PASS 뒤)이고 STOP을 늘리는 쪽입니다. 검증 2차 재계산은 참고 기록입니다.
11. **V-B 시작 조건**: K92_GATES_PASS(커밋 관문, J·F, 보충 30 단계, scan31·unit31·독립 검증 A31 PASS) 뒤에만, D-K9-37·D-K9-60 순서; V-A·푸시 0 [읽음 §4.4].
12. **고정 장치**: `a31_sha`(`k92t31.py:202-211`)는 보충 31 sha = `.sha256` 첫 낱말 = 고정점 안 64자 낱말을, C6(`:355-362`)은 기대 목록 sha가 고정점 안에 64자로 있고 구동기·판정기·비교기 줄이 목록에 있음을 봅니다. 고정점에는 고정판 sha와 기대 목록 sha만 64자로 적고, Declare 판 sha는 앞 16자만 적습니다.
13. **검토 끝 사전 점검**: `check31 --mode decl`(WMI `rv31_check31`) 43점검 거짓 0, C: 42.6 GB · D: 416.6 GB, VISSIM 0 [실행 `RV31/out/check31_rv.json`].

### 12.3 남은 것 (막힘 아님)

1. 구동기 머리말 글이 사전 점검을 "C1-C15"라고 적습니다(`k92t31.py:326`). 실제 점검은 C1–C14입니다(§4.1). 판정에 영향 없고, 고정 목록 바이트를 지키려고 고치지 않았습니다.
2. 판별 규칙의 한계(§2.2 [검토])는 판정기에서 고치지 않았습니다(D-K9-58은 `_seed47_path` 한 함수, 이 글의 규칙 글 그대로). 실제 자료에서 닿지 않음과 V2로 닫습니다. 묶음 2에서 판정기를 손볼 때 "seed 칸 없음·다른 값 → 나쁨"을 넣을지는 사용자가 정할 일입니다.
3. scan31은 기록 JSON 전체를 메모리에 읽습니다(s47 기록의 모형 값 포함). 출력은 개수·참거짓·나쁜 기록 경로뿐이고, J·F 값 고정 뒤라 허용되며, 열람 줄은 구동기가 LOG에 씁니다(§2.4).

### 12.4 검토 도구와 출력 (RV31 = `KB/a31review`; sha는 고정점 `KB/AMENDMENT31_FIXED.md`에 적음)

| 파일 | 무엇 |
|---|---|
| `rv_s47rule.py` / `out/rv_s47rule.json` | 새·옛 `_seed47_path` 적대 경로 24 + 진리표 22 + 합성 봉인 뿌리 12기록(합성만; 합성 트리 `TK/a31review/syn`은 만들고 지움) |
| `rv_idx31.py` / `out/rv_idx31.json` | 봉인 목록(봉인 뿌리 밖) 이름에 새·옛 함수를 건 개수 |
| `rv_idxnames.py` | record가 든 바닥 이름별 개수(LOG에 sha 적기 전에 한 번 돌림, 공개) |
| `rv_capman.py` / `out/cap_manifest.json` | CAP 바이트 목록(V4 기준) |
| `rv_capx.py` | CAP 목록 대 `jb_copies.json` `caps` 대조(개수만) |
| `out/check31_rv.json` | 검토 끝 `check31 --mode decl` |
| `r1/K8_PREDECLARATION_AMENDMENT_31_declare.md` | Declare 판 사본(`8a76e210…`) |
