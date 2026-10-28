# K8 보충 30 (Declare 판) — K9-2 묶음 1: 판정 단계 k92t 이어 하기 — F 지속성 보고 좁힘(T−450 ≥ 900, D-K9-56), 기존 F 데이터로 F 판정 → J-b → 사후, v3c3-s47 F 잡 로그 봉인 이동과 잡 정상 셈(D-K9-57 ⑤), 조작화·공개 ①–④, 봉인 열기·G-K4 plant 원자료 재계산 시점(D-K9-55) (2026-10-21)

- **상태: Declare 판.** 반박 검토(ReviewDeclare)가 이 글을 검토해 고정판과 고정점 파일 `KB/AMENDMENT30_FIXED.md`를 만듭니다. 고정점에 적힌 sha와 다른 보충 30으로는 어떤 단계(이어 하기 점검, 봉인 이동, F 판정, J-b, 사후)도 하지 않습니다. 새 구동기 `AD30/k92t30.py`가 이것을 기계로 봅니다: `chain30`·`seal30`·`check30 --mode apply`는 보충 30 sha = `.sha256` = 고정점 글 안의 64자 sha가 아니면 시작하지 않습니다(`k92t30.py:499-508` `a30_sha`, `:811-832` `chain30`) [읽음].
- 이 파일의 sha256을 `SP/K8_PREDECLARATION_AMENDMENT_30.md.sha256`에 적습니다.
- **쓸 때 상태** [실행 2026-10-21 10:37–11:2x KST]: GWT8 head = K9-2-5 `e27ceac86c01c1dcfd5b2bb2d9b522be3dc33c0d`(브랜치 `claude/k92-b1-20261016`, `b9734abe..HEAD` = 커밋 6개), K8 브랜치 = `b9734abe`, `git status --porcelain` 0줄, 원격 k92 참조 0, 푸시 0. 판정 단계 출력 `OUTK`는 STOP 그대로입니다: `STOP_f.json` `ebff59c9…`, 단계 기록 start·prep·j0·ja 넷, 판정 파일 j0·ja·jwall 셋, `steps.jsonl` 59줄 `7edd53c9…`, `driver.log` 3,434 B `8140fd2f…`, `f_vref` 결과 `09f9194b…`, `f_persist` 폴더 없음, `OUT30`(`OK2/a30`) 없음, 봉인 뿌리 맨 위 폴더 다섯(K9-2-0…3, a27). F 판정 값·J-b·사후 출력 0개 [실행 `AD30/dry/decl/check30_decl.json`].
- **구속**: 보충 1–29의 규칙·식·값·문턱·관문·표본은 §8 표에 적은 자리만 빼고 **그대로** 구속합니다.
- **알리는 말(먼저 읽을 것)**:
  1. 이 보충은 k92t 데이터 일부를 **본 뒤**에 씁니다. 시작 훑기·J-0·J-a·J 잡 벽시계 짝은 판정 값이 이미 있습니다(모두 PASS, `KB/GATES_K92B1.md`). F 판정 값과 J-b 값은 아직 아무도 계산하지 않았습니다. 이 보충은 F 판정 정의(F-1·F-2·F-3의 식·문턱·표본·팔)를 바꾸지 않습니다. 바꾸는 것은 보고 전용 항목 하나(지속성 MAE)의 상태 범위, 구동기, 봉인 범위, 해석의 글뿐입니다.
  2. 지속성 보고는 보충 24 §5.3(:347)이 선언한 22상태에서 **21상태로 줄어듭니다**. T=1,050 한 상태는 "측정 불가(T_FROM=900)"로 적습니다(§2).
  3. 독립 검증기의 도구 고정 시점: 보충 24 §3.1-8(:216)은 "J·F 모듈은 판정 단계 시작 전에 고정"이라고 적었습니다. 첫 VerifyGates 도구는 k92t 시작(10-20 21:45:53) **뒤**(10-21 07:2x)에 고정되었고, 다음 검증도 그 시각 전으로 돌아갈 수 없습니다. 이 보충은 D-K9-57 ④의 "데이터 전"을 "그 도구가 다시 내는 k92t 산출을 처음 읽기 전"으로 읽고, 이것이 §3.1-8 글보다 늦은 고정임을 공개합니다(§5.4, §10-6). 사용자가 다르게 정하려면 고정 전에 바꿔야 합니다.
- 표시: [실행] 이번에 돌려서 확인, [읽음] 문서·코드에서 확인, [추론] 시험하지 않은 판단, [계산] 산술.
- 이 보충은 판정 말을 쓰지 않습니다. 결과는 PASS / FAIL / 보류 / INCOMPLETE / STOP과 숫자로만 적습니다. 교통 성능 판정이 아닙니다.

## 줄임말 (처음 한 번만 풉니다)

- SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. KB = `SP/k92/bundle1`. KI = `KB/impl`(구현 도우미, 바꾸지 않음). KT = `KB/k92t`(기반 구동기·판정기, 바꾸지 않음). KPA = `KB/k92_probe_a25`.
- **AD30** = `KB/a30decl` — 이 보충의 새 구동기·판정기·확인 도구·확인 출력 폴더(§12).
- TK = `D:/VISSIM-merge/k8_gate_trees/k92b1`. **TREE** = `TK/a27/k92t`(git archive K9-2-5 `e27ceac8`, k92t 판정기 트리). K925 = `TK/a27/k925`(같은 바이트의 K9-2-5 판정기 트리). **TC30** = `TK/a30decl/tc`(이 판의 합성 시험이 `k92_gates`를 불러오는 1.7 MB 사본, `K925`의 `k8_gates` 폴더 복사).
- OK2 = `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_b1`. **OUTK** = `OK2/k92t`(판정 단계 출력 뿌리). **OUT30** = `OK2/a30`(이 보충의 이어 하기 기록, 지금 없음). **SEALED** = `OK2/sealed_s47`(봉인 뿌리). V4 = `D:/VISSIM-merge/k8_gates_out_v4`(K9-1 판정 산출, 읽기만).
- GWT8 = 커밋 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`. SA = `diagnostics/sdmpc_n31_20260924/k8_gates/sa`.
- **k92t** = 보충 24 §5의 판정 단계. **J** = K9-1 판정 상태 불변 관문(J-0 정적, J-a 기준 확인, J-b 판정 잎). **F** = 충실도 관문(F-1·F-2·F-3, v3c3-s47 주 표본 22상태). **NC** = 무제어 런.
- **VR** = VISSIM 기준 도구 `SA/k92_vissim_ref.py`(`f3fcc574…`). **U4 측정기** = VR이 쓰는 헤드 통과 측정기 `diagnostics/sdmpc_n31_20260924/k8b/u4/derive_head_saturation.py`. **T_FROM** = 그 측정기가 받는 창의 가장 이른 시작(900 s, `:72`). **FZP** = VISSIM 차량 궤적 파일.
- **지속성 보고** = 보충 24 §5.3 "보고만" 목록(:347)의 "M1 persistence MAE": 주 표본 상태 T마다 VISSIM M1을 "T 시점 값이 T+450까지 그대로"로 예측했을 때의 평균 절대 오차. VISSIM M1(T) = VR 상태 T−450의 `m1_T450`(프레임 T+0.1), VISSIM M1(T+450) = VR 상태 T의 `m1_T450`.
- SAF-K91 = K9-1 판정 팔(`5f0d0e40…`). SAF-K92b1 = 두 키(W·H-b)를 더한 팔(`65cac7ea…`). BASE = K9-1 기준 팔(`319d07aa…`). F 팔 = OFF(SAF-K91)·W(`d179f01d…`)·B1(SAF-K92b1).
- **기반 구동기** = `KT/k92t.py`(`b07ffb56…`), **기반 판정기** = `KT/k92t_judge.py`(`eb4c113a…`) — k92t 데이터 전에 고정, start…ja를 돌리고 F에서 멈춤. **새 구동기** = `AD30/k92t30.py`, **새 판정기** = `AD30/k92t30_judge.py`.
- 새 구동기의 단계 이름: **check30**(이어 하기 점검, 읽기만), **seal30**(F 잡 로그 봉인 이동), **f30**(잡 정상 셈 → 지속성 VR → F 판정; 단계 기록 이름은 `f`), **jb**(기반과 같은 J-b), **post30**(사후; 단계 기록 이름은 `post`), **chain30**(이것들을 차례로 한 번).
- **F 잡 로그** = `OUTK/logs/f_f_off_jobs.log`·`f_f_w_jobs.log`·`f_f_b1_jobs.log`(F 잡 자식의 표준 출력; 결정 기록 D-K9-57 ⑤의 `OUTK/logs/f_*_jobs.log`).
- **J·F 값 고정** = `judge/f.json`과 `judge/jb.json`의 sha가 둘 다 `KB/LOG.md`에 적힌 순간(§4.5).
- 시드는 망 접두어를 붙입니다(v3c3-s31 등). 봉인 시드 37/59/61/67은 열지 않습니다. codex 64cf-s59·s61·s67 숫자는 쓰지 않습니다.

---

## 0. 근거 문서 [실행: sha256, 2026-10-21 10:37–11:2x KST]

| 문서 | sha256 |
|---|---|
| 결정 기록 `SP/K9_1_J1_NOTES_20261013.md`(182줄; D-K9-56·57 :176-182) | `eae2e6faf3c13dc42e84ef545fef734ad5ed9650946de72a76cb392b028c8d99` |
| 관문 보고(STOP) `KB/GATES_K92B1.md` | `63dd35e29ced298c9e7538f0aeefe7e48871e6197285b3994fa2e51683a03b60` |
| 관문 보고 독립 검증 `KB/VERIFY_GATES_K92B1.md` | `b9e90cd23975cf8234562bac1e601df49d846cb6a7886ea808bc84172db808cc` |
| 보충 24 / 25 / 26 고정판 | `d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc` / `4fd7b599fe0f6131143e911dd3ab2be264a175e3f90b185bade9482d60b9ff8e` / `8f8356168a299c07960d86ef12aa9f7af6f2f040af08ba75e5233a5819edba37` |
| 보충 27 / 28 / 29 고정판 | `4ce8b27a2ebf08aa0e8ac3f647b4e4336a98f7be7ec8d6f006a0fd1d12005a13` / `9881eb40c1129af0cdff48026dc8656b4235d43f0eb80566e4be9b66d9ac345e` / `4bd6dc8de8b0a4a4ab0b8703c07d7a73d244c4a622b81585f06dc69d6d83599d` |
| 고정점 24 / 25 / 26 | `fbc3d59fe2e47fec00d87262d624aa9a163ed02e113609b06173841397df101a` / `d1338fbc40a2efaf6997667f59e7bd709951e1fd3f2b1a8a0a0881794c3d24ed` / `6edc55acd5aa0976701456d956e33f33c52ae0853535f6a4d8cb8bf26a354581` |
| 고정점 27 / 28 / 29 | `394ab15fdea0d945a3b766c208e692ee7e1086fca3c178f6b423079d71fedcdb` / `14451cf4d46c5c0095bc896134112148ba5700ee70b2ed78b8ee38d0e62e20e5` / `3ba1d0bdaab8a0189f903d10fc1024baed770080542cbd841f79d3a56df58e43` |
| k92t 고정 목록 `KB/k92t_pins.sha256`(56줄, 지금 56/56 OK) | `38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd` |
| 기반 구동기 `KT/k92t.py` / 기반 판정기 `KT/k92t_judge.py`(= `AD30/base/` 사본) | `b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec` / `eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e` |
| 이어 받는 OUTK 기록(§4.1 C8): `STOP_f.json` / `k92_judging_stage.json` / `start/scans.json` | `ebff59c96596baca6039647e3902b88881a45fe6227b7da438e99afe420d3f17` / `34e63a991451ef8c3f1be0ef6f4765f009abc19745fe7e546ffaeda43fd1aaa5` / `410fde88da1e97e0434d3df59f292a904ed87c153a17bb209ec918b7a074bfb8` |
| `stages/start.json` / `prep.json` / `j0.json` / `ja.json` | `f3ed1dcea6f86b6c750368e9b5b2082331a9c85f18d435b9eac6af46744eef13` / `9ef3a7edd7e5a7c1d5938161c27c1f1bde5394da84d7cc61181876d78cfbc533` / `3845def6bbc0d95935fac27f36a24b13a5938d111aa11f1f7d93548f3f216631` / `b40593bb34f45074546d58c808912ee4cffa6ff95dd0b5d3ac3543c89368b03c` |
| `judge/j0.json` / `ja.json` / `jwall.json` | `24ee9d3b66d16618f9c6bc255bcabaecbcbaa2a653c985a9fb0315d68a85aab1` / `74806cb0683582bc20eccb68eb086363a0ac0e8d100d2c6c5d48436da14b4d5c` / `1fb5c60454169b9f10014691a9fae9aa4697ac5bd26323e146149b6600fb615a` |
| `f_vref/sa/k92_vissim_ref.json`(내용 열지 않음) | `09f9194b308703db4d1da87cc10e458fca85872fd1189ef5fda7b2bc8f3b601a` |
| `steps.jsonl`(59줄) / `driver.log`(3,434 B) = `OK2/logs/k92t_chain.txt` | `7edd53c959da62362d948a62d2a15ff0030738d3e0a19dd9a7cc93e60a32ed69` / `8140fd2fa2d04a3781d8a3068a7171be0e6a22d34ced1d3d45cb78e12d22d728` |
| F 잡 로그(내용 열지 않음, 바이트 sha만): `f_f_off_jobs.log` 4,996 B / `f_f_w_jobs.log` 4,936 B / `f_f_b1_jobs.log` 4,971 B | `84a72fcb570c329558f091ea042513bfe4477638669d85e7c3284b101b563c3b` / `56293384819e5e7afd22e054502cc97e0e45aa7b06e4c90052b79768a8f885c5` / `6218e3dfac46b715401407cfc9e3982d2371322ba6bc207eac0c3ac12eea3935` |
| OUTK 파일 목록(18,019파일, 4,223,333,998 B; 상대 경로·크기·sha) `AD30/out/outk_inventory_decl.json` | `33101cd1b43b8be8dcf020f4e4c559d21329d3e67b7333afe0519975ecfa0dfc` |
| 작업 기록 `KB/LOG.md`(이 단계 첫 항목 덧붙임 전, 169,011 B) | `09656a590ee6c8508bc2b7271066e9aabdb4bcb1fde1ba303bc2231244e14fca` |
| 읽기 전용 뿌리 스냅숏 `OK2/snap/s28_a30decl.json`(이 단계 앞, s02 대비 SAME) / `s28b_a30decl_after.json`(이 단계 끝, s02 대비 SAME) | `c94eb83fdef3800b38722ba630408e44936f713e4c4bde22ec83ab09cdc556a5` / `218a54dd7e0b941914efebef89a6af7954dee88e202fae1f3266396b6cf5da14` |

### 0.1 이 판을 쓰며 한 일 [실행]

- **읽기**: 위 문서; 기반 구동기·판정기; TREE의 `k92_vissim_ref.py`(:95-182), U4 측정기 `derive_head_saturation.py`(:60-80, :365-395), `sa_jobs.py`(:375-392 SA_JOB 줄), `sa_capture.py`·`sa_cap_child.py`·`sa_worker.py`의 출력 줄(`print`만 찾음), `k92_gates.py` `f_judge`(:861-887)와 import 줄; KI `k92lib.py`·`launch.ps1`·`k92snap.py`; OUTK의 이름·크기·시각, `steps.jsonl`(단계 이름·종료 코드·시간·VISSIM 개수), `STOP_f.json`(값 없음).
- **열지 않음**: F 잡·포착 폴더의 파일 내용, `f_vref` 결과 내용, F 잡 로그 세 개의 내용(바이트 sha만), 봉인 뿌리의 파일 내용, `logs/f_vref.log`·`f_persist.log`의 내용(sha만). v3c3-s47 결과 값 0.
- **쓰기**: AD30(새 구동기·판정기·확인 도구·기반 사본·확인 출력·기대 고정 목록); TC30(1.7 MB 사본); `OK2/snap/s28_a30decl.json`·`s28b_a30decl_after.json`; `OK2/logs/a30decl_inv.txt`·`a30decl_drive.txt`·`a30decl_drive2.txt`(WMI 발사 표준 출력, 값 없음); `KI/wmi_launch_lines.txt`(launch.ps1이 한 줄씩 덧붙임); 이 글과 `.sha256`; `KB/LOG.md` 덧붙임. OUTK·TREE·봉인 뿌리·GWT8 쓰기 0.
- **확인 실행**: `dry_a30.py static`·`synth`(앞에서), `k92t30.py inv`(OUTK 파일 목록, WMI 분리 `-Tag a30decl_inv`, 약 1분), `dry_a30.py drive`(WMI 분리 `-Tag a30decl_drive`, 약 3분: `check30 --mode decl`, `seal30 --dry-run`, 지속성 인자 셈; 선언 출력은 다시 돌린 `-Tag a30decl_drive2`, 약 3분). 모두 BelowNormal·`PYTHONHASHSEED=0`·`python -B`, 한 번에 하나, 발사 때 python·VISSIM 0.
- **개발 중 공개**(AD30/dry 아래): `decl0` = 첫 선언 출력(static·synth·drive). 그 뒤 새 구동기의 주석·메시지 글자 다섯 곳(절 번호 `section 5` → `5.3`, `4.4` → `4.5` 셋, `2.2` → `2.3`)을 이 글의 절 번호에 맞췄고, 바이트가 바뀌어 static·synth·drive를 `decl`로 다시 돌렸습니다(판정·인자·점검 줄은 그대로). `decl0`은 보관이고 고정 목록에 넣지 않습니다. `dev1` static PASS(보관). `dev1` 첫 synth는 망가뜨림 사본이 `dry/dev1/mutants`에 놓여 KPA 상대 경로를 못 찾아 예외로 끝났고(합성 출력만 있음), 그 출력(`dev1/synth`·`mutants`·`k8g_out`)은 지웠습니다. `dev2` synth는 망가뜨림 M4에서 MAE가 None이라 내 점검 줄이 예외를 냈고, 폴더째 지웠습니다(합성 출력만). 두 고침은 확인 도구 `dry_a30.py`에만 했고(망가뜨림 사본의 KPA 경로를 실제 KPA로, MAE 점검을 None에 안전하게), 새 구동기·판정기는 바꾸지 않았습니다. `dev3` synth PASS(보관). 선언 출력은 `dry/decl/`입니다.
- **하지 않은 일**: VISSIM·COM·러너·동결 0. 결정 재생·plant 잡·포착 0. VR 실행 0(지속성 인자는 문자열로만 셈). k92t 판정기를 실제 k92t 산출에 부른 일 0. 커밋·브랜치·푸시 0. 금지 시험 0(돌린 시험 없음; 합성 확인은 `dry_a30.py` 자체). 봉인 시드·봉인 로그·v3c3-s47 결과 값 열람 0.

---

## 1. 사용자 결정 원문 [읽음 결정 기록 :176-182, 표 행 그대로]

근거 줄(:177): `k92/bundle1/GATES_K92B1.md` (63dd35e29ced298c…), `k92/bundle1/VERIFY_GATES_K92B1.md` (b9e90cd23975cf82…). K9-2-5 e27ceac8 커밋·검증 3차 결함 0. k92t: 시작 훑기 PASS, J-0 PASS(T=1·150 같은 실패 2 포함 해석), J-a 23/23 PASS, J 벽시계 중앙 0.980 PASS. F: 보고 전용 지속성 MAE 의 VISSIM 기준(T−450) 도구가 U4 측정기 T_FROM=900 때문에 T=1050 의 600 s 창을 못 재 rc=1 → STOP(F 판정 데이터 3팔×38잡·VISSIM 기준은 있으나 미계산·미열람).

| # | 질문 | 사용자 답 | 효과 |
|---|---|---|---|
| D-K9-56 | F 단계를 어떻게 이어 갈까요? | **지속성 보고를 좁히고 기존 F 데이터로 진행 (Recommended)** | 보충 30(F 값 보기 전): T−450 < 900 인 상태는 지속성 보고를 '측정 불가(T_FROM=900)'로 표시하고 나머지만 보고(보고 전용 지표, 판정 정의 불변). 기존 F 데이터로 F 판정 → J-b(약 12 h) → 사후 |
| D-K9-57 | 해석·공개 사항 ①–⑤ | **권장안 일괄 (Recommended)** | ① J-0 의 T=1·150 은 옛·새 쪽이 같은 실패이므로 통과로 셈(글자 그대로 59/61, K9-1 기록도 59/59 — 공개) ② J-b 는 같은 코드 트리 안 비교가 필요한 BASE 실행만 재실행 ③ 봉인 뿌리 기록 훑기는 J·F 값 고정 뒤 ④ 검증자 J-a 도구의 사후 수정(vg_ja → vg_ja2)은 공개하고, 다음 검증에서 데이터 전에 고정한 새 도구로 J-a 를 다시 셈 ⑤ k92t 의 s47 잡 로그(OUTK/logs/f_*_jobs.log)도 봉인 대상으로 보고 봉인 폴더로 옮김, 잡 정상 여부는 종료 코드·요약 파일로만 셈, 앞서 열람 가능성은 공개 |

D-K9-55(:174, 보충 29 §5): G-K4 plant 행의 원자료 독립 재계산은 k92t에서 J·F 값 고정 뒤. 이 보충은 그 시점을 §4.5에서 기계로 정합니다.

---

## 2. 지속성 보고 좁힘 (D-K9-56)

### 2.1 무엇이 멈췄나 [읽음·실행]

- 기반 구동기는 F 단계에서 VR을 `--states 47:<T−450, 주 표본 22개>`로 한 번 불렀습니다(`KT/k92t.py:631-634`, 출력 뿌리 `OUTK/f_persist`). 첫 상태 600에서 VR이 SystemExit 했고(`k92_vissim_ref.py:119-122`, "window (600.1, 750.1) found 0 times for 1090201"), 구동기 `must()`가 STOP했습니다(`k92t.py:248-250`; `STOP_f.json` "persist rc=1"). `OUTK/f_persist` 폴더는 생기지 않았습니다 [실행 `ls`].
- 원인 [읽음 + VerifyGates 실행]: U4 측정기는 창 (a, b]를 `a ≥ T_FROM(900) and b ≤ T_END(9000) and b − a ≥ 1`일 때만 셉니다(`derive_head_saturation.py:72-73`, `:379`). 상태 T−450 = 600의 창 시작 600.1 < 900이라 그 창의 주기가 0개입니다. VerifyGates가 v3c3-s43 T=600으로 같은 끝 줄(rc 1), T=1,050으로 rc 0을 다시 만들었습니다(`VERIFY_GATES_K92B1.md` §6).
- 이 항목은 보고 전용입니다. F 판정기(`k92t_judge.py:759-767`)는 지속성 파일을 읽지 않습니다 [읽음].

### 2.2 좁힌 정의 (닫힌 목록) [계산]

- **측정 조건**: 주 표본 상태 T는 **T − 450 ≥ 900**일 때만 지속성 오차를 셉니다(U4 측정기가 상태 T−450의 창 (T−450+0.1, T−450+450.1]을 받는 조건; 150의 배수에서 `T−450+0.1 ≥ 900` ⇔ `T−450 ≥ 900`).
- **측정 불가 상태**: T = **1,050**(T−450 = 600) 한 개. 보고 글자: 한국어 보고서 **"측정 불가(T_FROM=900)"**, 판정기 JSON **`"not measurable (T_FROM=900)"`**(`k92t30_judge.py:152-153` `PERSIST_LABEL`·`PERSIST_LABEL_KO`). 이 상태는 VR에 묻지 않습니다(값 없음, 0으로도 세지 않음).
- **측정 상태(21)**: 1,650, 1,950, 2,400, 3,300, 3,750, 3,900, 4,650, 5,100, 5,550, 6,000, 6,150, 6,450, 6,600, 6,900, 7,050, 7,350, 7,500, 7,800, 7,950, 8,250, 8,400.
- **VR에 넘기는 상태(T−450, 21)**: 1,200, 1,500, 1,950, 2,850, 3,300, 3,450, 4,200, 4,650, 5,100, 5,550, 5,700, 6,000, 6,150, 6,450, 6,600, 6,900, 7,050, 7,350, 7,500, 7,800, 7,950. 가장 이른 창 (1,200.1, 1,350.1], 가장 늦은 끝 8,400.1 — 모두 [900, 9,000] 안 [계산]. 주 표본 VR(`f_vref`)이 이미 끝 8,850.1까지 rc 0으로 쟀으므로 FZP 길이로 막힐 자리는 없을 것으로 봅니다 [추론].
- **겹침 15**: 위 VR 상태 가운데 1,950, 3,300, 4,650, 5,100, 5,550, 6,000, 6,150, 6,450, 6,600, 6,900, 7,050, 7,350, 7,500, 7,800, 7,950은 그 자체가 주 표본 상태입니다. 같은 FZP의 같은 프레임(T−450+450.1)이므로 지속성 파일의 `m1_T450`은 `f_vref`의 같은 상태 `m1_T450`과 같아야 합니다.

### 2.3 도구를 부르는 법 (한 번, 정확한 인자)

- 새 구동기 `persist_argv()`(`k92t30.py:585-590`)가 만드는 한 줄뿐입니다:
  `python -B TREE/SA/k92_vissim_ref.py --root TREE --out OUTK/f_persist30 --states 47:1200,1500,1950,2850,3300,3450,4200,4650,5100,5550,5700,6000,6150,6450,6600,6900,7050,7350,7500,7800,7950 --gates-stage k92t --declaration-sha d46db6dc3959b19525f0fce77ead5432682e3de0ef8060cdc3da09661559aadc`
  [실행 `AD30/dry/decl/dry_a30_drive.json` `/persist`: 21상태, 최소 1,200, 시드 47만, 판정기 상수와 같음, 이 글의 목록과 같음].
- 단계 이름 `f_persist30`, 출력 뿌리 **`OUTK/f_persist30`**(새 폴더; 있으면 STOP). 표준 출력 `OUTK/logs/f_persist30.log`(VR은 상태 목록·sha 앞 16자·초만 찍고 값을 찍지 않음, `k92_vissim_ref.py:154`, `:164`, `:176-177` [읽음]).
- `persist_argv()`는 상태 목록이 21개가 아니거나 900보다 작은 상태가 있거나 측정 불가 상태가 (1,050) 아니면 SystemExit 합니다(구동기 자체 가드).
- **건너뛰는 것**: 기반의 `--states 47:<22>` 호출, 출력 뿌리 `OUTK/f_persist`, 상태 600. 기반의 실패 기록(`steps.jsonl`의 `f_persist` rc 1, `logs/f_persist.log`, `STOP_f.json`)은 그대로 둡니다.
- VR은 주 표본 v3c3-s47 NC FZP를 k92t 안에서 읽습니다(보충 24 §3.1-3b가 허용하는 자리). 결과 파일은 `OUTK/f_persist30/sa/k92_vissim_ref.json` 하나입니다.

### 2.4 보고 꼴 (`k92t30_judge.py:815-849` `persistence_report`, F 판정 파일 `report_persistence_M1_450`)

- `n`(측정 수), `mae`, `states`(22상태마다 `measured` / `not measurable (T_FROM=900)` / `missing`), `measured`(목록), `not_measurable`(`{"1050": "not measurable (T_FROM=900)"}`), `label_ko`, `missing`, `vr_states_declared`(21), `vr_states_in_file`, `vr_state_keys_not_int`, `vr_states_equal_declared`, `overlap_with_f_vref`(`{n: 15, n_equal}`), `identity_ok`, `complete`.
- 상태별 지속성 오차 값은 파일에 적지 않습니다(기반과 같이 n·MAE만).
- **`complete` 참 조건(모두)**: 지속성 파일의 s47 망 동일성 원래 sha = `1895ca30…`(보충 25 §3.3-9), 상태 열쇠가 모두 정수 글자, 열쇠 집합 = 선언 21개와 정확히 같음, 21상태 모두 정수 `m1_T450`과 OFF 팔 VISSIM 쪽(M1 T+450)이 있음, 겹침 15개 모두 `f_vref`와 같음.
- `complete`가 거짓이면 구동기가 F 판정 파일을 쓴 **뒤** STOP합니다(S-K43). F 판정 칸(verdict, F-1·F-2·F-3, n)은 이 값에 따라 바뀌지 않습니다.
- 보고서 글: "지속성 MAE(보고 전용): 21상태(T−450 ≥ 900), T=1,050은 측정 불가(T_FROM=900)". 보충 24 §5.3이 선언한 22상태보다 1개 적음을 같은 줄에 적습니다.

### 2.5 바뀌지 않는 것

- F-1·F-2·F-3의 식·문턱(보충 24 :343-345), 주 표본 22상태·둘째 표본 16상태(:336-337), 팔 OFF·W·B1, 지표 M1·M2·M3(:341), VISSIM 기준(`f_vref`), 판정 함수 `k92_gates.f_judge`(TREE, 함수 글 K9-2-0부터 같음), INCOMPLETE 규칙(OFF·B1 주 표본 하나라도 없으면 INCOMPLETE), 보고 전용 목록의 나머지(T+150 판, W 팔, 상태별 표, 부트스트랩, OUTW·`SC109_E_out`, 노출 뺀 판, 둘째 표본, 묶임 수).
- F 판정의 입력 데이터: 기반 구동기가 만든 세 팔 포착 38·잡 38과 `f_vref`(`09f9194b…`)를 그대로 씁니다. 다시 만들지 않습니다.

---

## 3. 새 구동기·판정기 (새 고정; 커밋 안 함)

### 3.1 파일 [실행 sha256]

| 파일 | sha256 | 크기 |
|---|---|---|
| `AD30/k92t30.py`(새 구동기, LF) | `8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4` | 50,442 B, 877줄 |
| `AD30/k92t30_judge.py`(새 판정기, LF) | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` | 52,254 B, 946줄 |
| `AD30/dry_a30.py`(데이터 없는 확인 도구) | `c685b5bad597de6769c29178d737ec1837c18a58c31f51e3a51817e7f792901d` | 21,314 B |
| `AD30/A30_DRIVER.diff`(기반 → 새, 두 파일 통합 차이; 기반 바이트는 CRLF → LF 뒤 비교) | `a9d5087d81d01b50695ecc945bd6eb40579f02fb8dff9dbe5e215b797bbeaaa7` | 77,321 B, 1,265줄 |
| `AD30/base/k92t.py` / `base/k92t_judge.py`(기반 바이트 사본, CRLF) | `b07ffb56…` / `eb4c113a…`(§0) | 48,196 / 46,124 B |

- 기반 파일은 CRLF, 새 파일은 LF입니다. 차이 파일은 기반을 LF로 바꾼 뒤 만든 것입니다 [실행 `dry_a30.py static`].

### 3.2 구동기 바뀜 (닫힌 목록) [실행 `AD30/dry/decl/dry_a30_static.json` `/driver`]

- **그대로(소스 글 바이트 같음, 17개)**: `now`, `log`, `sha`, `write`, `read`, `space`, `env_for`, `step`, `tool`, `must`, `git`, `copy_file`, `copy_tree_rec`, `table_path`, `_arm_of`, `jb_copies`, `snap`.
- **바뀜(6)**:
  - `stage_jb`: 판정기 경로 한 토큰만(`str(HERE / 'k92t_judge.py')` → `str(JUDGE)`) [실행 `stage_jb_only_judge_path` 참]. J-b 정의·순서·명령은 기반 그대로(§4.4).
  - `require_prev`(`:263-279`): 허용되는 STOP 파일은 기반 `STOP_f.json`(기록 바이트) 하나뿐, 기반 단계 기록 start·prep·j0·ja는 기록 바이트와 같아야 함, 새 단계(seal30·f·jb·post)는 `driver = k92t30`·`amendment30_sha256` = 보충 30 sha인 기록이 있어야 함.
  - `stop`(`:246-253`): 새 STOP 파일 이름 `OUTK/STOP_a30_<단계>.json`(기반 `STOP_f.json`은 그대로 둠), LOG 글 "k92t30 구동기".
  - `finish`(`:256-260`): 단계 기록에 `driver`, `driver_sha256`, `judge_sha256`, `amendment30_sha256`을 더함.
  - `log_md`(`:227-231`): 기반 글의 "k92t 구동기"를 "k92t30 구동기"로 바꿔 적음(값 0, 판정·개수·sha만 — 기반과 같음).
  - `main`: 명령 `check30`·`inv`·`seal30`·`chain30`·`status30`만.
- **뺌(14)**: `stage_pre`, `stage_tree`, `stage_start`, `child`, `run_child`, `job_item`, `prep_root`, `stage_prep`, `stage_j0`, `stage_ja`, `stage_f`, `stage_post`, `chain`, `status`. 새 구동기로는 시작 훑기·prep·J-0·J-a·F 잡을 다시 돌릴 수 없습니다.
- **새(14)**: `wjson`, `a30_sha`(`:499-508`), `pins_check`, `inventory`(`:524-534`), `inv_diff`, `f_labels`, `f_inputs_check`(`:551-582`), `persist_argv`(`:585-590`), `stage_check30`(`:593-679`), `stage_seal30`(`:682-732`), `stage_f30`(`:735-774`), `stage_post30`(`:777-808`), `chain30`(`:811-832`), `status30`.
- **상수**: 바뀜 `ROOTS`(`f_persist` → `f_persist30`), `ORDER`(`start, prep, j0, ja, seal30, f, jb, post`); 뺌 `KOUT`, `PAIR_STATES`; 더함 34개(§0 값들, `F_JOB_LOGS`, `F_STEPS_RC0`, `PERSIST_*`, `SNAPS30` 등; 목록 `dry_a30_static.json` `/driver_constants`).
- 구동기 머리말 O5′·O7′·O8′(`:48-51`, `:65-66`, `:69-71`)은 이 보충 §2·§5.3·§4.5와 같은 뜻입니다.

### 3.3 판정기 바뀜 (닫힌 목록) [실행 `dry_a30_static.json` `/judge`]

- **그대로(32개 함수 소스 글 바이트 같음)**: 시작 훑기(`scan_sealed`, `_scan_lines`, `scan_leak`, `_seed47_path`, `scan_vissim_blind`, `scan_primary_absent`, `cmd_scans`), `cmd_sealedscan`, J-0(`harness`, `_cap_rec`, `_signature`, `_sa_state`, `_caps`, `_leaf_paths`, `j0_state`, `cmd_j0`), J-a(`_numeric_same`, `cmd_ja`), `cmd_jwall`, J-b(`judged_items`, `cmd_jb`), F 도우미(`_rec`, `_cap_meta`, `_lab`, `f_rows`, `as450`, `table`), 공용(`sha_file`, `lp`, `read_json`, `write_json`, `canon`).
- **바뀜(2)**: `cmd_f` — (가) 지속성 파일 뿌리 `OUTK/f_persist30`, (나) 지속성 계산을 `persistence_report`로(§2.4), (다) 결과에 `amendment30: true`, `job_counts`(§4.2) 칸을 더함, (라) 끝 줄에 지속성 `complete`·측정 수·측정 불가 목록. 그 밖의 F 계산 줄(판정 칸, 표, T+150, W, 노출 판, 둘째 표본)은 글 그대로. `main` — 명령 `sealedscan`·`jb`·`fcount`·`f`만(`scans`·`j0`·`ja`·`jwall` 함수는 남지만 부를 수 없음).
- **새(3)**: `job_counts`(`:770-799`), `cmd_fcount`(`:802-812`), `persistence_report`(`:815-849`).
- **상수 더함(8)**: `PERSIST_NAME`, `T_FROM_U4`, `PERSIST_LABEL`, `PERSIST_LABEL_KO`, `PERSIST_MEASURED`, `PERSIST_NOT`, `PERSIST_VR_STATES`, `PERSIST_OVERLAP`. 기반 상수 바뀜·뺌 0.
- J-0·J-a·J 벽시계 판정은 기반 판정기가 이미 냈습니다(`judge/j0.json`·`ja.json`·`jwall.json`). 새 판정기는 다시 내지 않습니다.
- 머리말: F 줄의 "K9-2-0 blob, unchanged since"를 "함수 글은 K9-2-0부터 같음, 파일 블롭은 K9-2-4·5에서 바뀜"으로 고쳤습니다(VerifyGates §9-5).

### 3.4 데이터 없는 확인 [실행 `AD30/dry/decl/`]

| 확인 | 내용 | 결과 | 출력 sha256 |
|---|---|---|---|
| static | `compile` 3/3, CR 0, 기반 사본 = KT 고정 바이트, 함수 소스 글 대조(§3.2·§3.3의 같음·바뀜·뺌·새 목록이 선언과 정확히 같음), `stage_jb` 토큰 하나, 차이 파일 생성 | ok 참 | `319810d8274be5e74984194e2284f4d0981dc7c06d4cb1464a021413acdc10e6` |
| synth | 합성 입력(무작위 시드 30, 실제 값 0)으로 새 판정기 `cmd_f`·`cmd_fcount`의 사례 S1–S8(아래), 망가뜨림 M1–M7 | 사례 8/8 기대와 같음, 망가뜨림 7/7 잡음, TC30 = K925 `k8_gates` 바이트 같음 | `d4e18b3607b7121fc595e7a3169f72fd2ce572156843d2276acfd0706e757aee` |
| drive | `check30 --mode decl`(C1–C15, §4.1; C2·C6은 고정 전이라 보고만), `seal30 --dry-run`(세 파일 크기·sha 같음, 봉인 뿌리 맨 위 다섯, `k92t` 폴더 없음), 지속성 인자 | ok 참(check30 거짓 0, seal 3/3) | `ac43a43fa42690d967ad4d7066a96dd5b3503658a5ff12d85bd3dbd59df9d3d9` |
| check30 decl 출력 / seal30 dry 출력 | — | — | `cfe7bc30c3dadd93ed2a4850842b362560d390ca30c62fc32007ab65e719b889` / `d98b5f402367e36150f0e7b1c94fd6b0b5c35aa0d23ea07c6cfd1e184a93bd3b` |

- 합성 사례(기대 = (F 판정, 지속성 `complete`, 지속성 n, fcount 판정)): S1 바른 입력 (PASS, 참, 21, PASS) + 1,050 글자·측정 목록 21·MAE를 이 글로 따로 셈한 값과 1e-12 안·겹침 15/15·잡 수 전부 참; S2 지속성 파일에 600 더함 (PASS, 거짓, 21, PASS); S3 1,200 뺌 (PASS, 거짓, 20, PASS); S4 겹침 1,950 하나 다름 (PASS, 거짓, 21, PASS); S5 망 동일성 sha 다름 (PASS, 거짓, 21, PASS); S6 W 팔 s47 잡 하나 summary ok 거짓 (PASS, 참, 21, INCOMPLETE); S7 OFF 팔 s47 기록 하나 없음 (INCOMPLETE, 없음, 없음, INCOMPLETE); S8 정수 아닌 상태 열쇠 (PASS, 거짓, 21, PASS).
- 망가뜨림(각각 판정기 글 한 곳): M1 측정 조건을 `T−450 ≥ 0`으로(S1·S6에서 잡힘), M2 겹침 조건 빼기(S4), M3 잡 수에서 summary `ok is True`를 `is not None`으로(S6), M4 뿌리를 `f_persist`로(7사례), M5 상태 집합 조건 빼기(S2), M6 망 동일성 조건 빼기(S5), M7 정수 열쇠 조건 빼기(S8).
- 합성 입력은 판정기 상수가 아니라 이 글의 값(주 표본·둘째 표본·망 sha·`f_persist30`·21상태·글자)으로 만듭니다(`dry_a30.py` 머리 상수).

---

## 4. 이어 하기 규칙 (k92t, 기반 기록 유지)

- **유지(다시 돌리지 않음)**: 시작 훑기(`start/scans.json`), prep, J-0(`judge/j0.json`), J-a(`judge/ja.json`), J 잡 벽시계 짝(`judge/jwall.json`), 그 단계 기록 넷, 판정 단계 시작 기록(`k92_judging_stage.json`), 기반 STOP 기록(`STOP_f.json`). 판정 단계 시작 시각은 10-20 21:45:53 그대로입니다(보충 24 §5.1).
- **순서(`chain30`, 한 번)**: check30(apply) → 스냅숏 s29 → seal30 → s30 → f30 → s31 → jb → s32 → post30 → s33. 하나라도 STOP이면 그 자리에서 멈추고 다음 단계 없음, 다시 돌리지 않음(사용자 결정). `chain30`은 OUT30이나 새 단계 기록이 하나라도 있으면 시작하지 않습니다(`k92t30.py:814-815`).
- 스냅숏 이름: `s29_a30_check`, `s30_a30_seal`, `s31_a30_after_f`, `s32_a30_after_jb`, `s33_a30_post`(모두 `OK2/snap/`, 기준 s02; 다르면 S-K11). 기반의 s27은 `s27_k92t_stop_f`로 이미 있습니다.

### 4.1 check30 — 이어 하기 점검 (읽기만, 닫힌 목록 C1–C15; `k92t30.py:593-679`)

| # | 점검 |
|---|---|
| C1 | 보충 24–29 sha = `.sha256` = §0, 고정점 24–29 sha = §0 |
| C2 | 보충 30 sha = `.sha256` = 고정점 30 글 안의 64자 sha(`a30_sha`) |
| C3 | 결정 기록 앞 182줄 sha = `eae2e6fa…`(덧붙임만 허용) |
| C4 | GWT8 head = `e27ceac8…`, 브랜치, K8 `b9734abe`, status 0줄, 원격 k92 0 |
| C5 | `KB/k92t_pins.sha256` = `38a2ce14…`, 56줄 모두 OK |
| C6 | `KB/a30_pins.sha256`(§9) 모든 줄 OK, 새 구동기·판정기 줄이 지금 sha로 들어 있음, 그 목록 파일 sha가 고정점 30 글 안에 있음 |
| C7 | `TK/a27/k92t.build.json` = `a1e98fa7…`; TREE 대 K925 바이트 비교(캐시 `__pycache__`·`__tangentcache__`·`.pytest_cache` 뺌, `KI/k92lib.py:250-271`) 다름·한쪽 0; VR sha = `f3fcc574…` |
| C8 | §0의 이어 받는 OUTK 기록 11개 sha 같음; STOP 파일 = `STOP_f.json` 하나; `stages/` = start·prep·j0·ja 넷; `judge/` = j0·ja·jwall 셋; `steps.jsonl` 정확히 59줄·sha 같음; `driver.log` 3,434 B·sha 같음; `OK2/logs/k92t_chain.txt` sha 같음 |
| C9 | `steps.jsonl` 첫 59줄의 F 단계 24개(prep_f 9, arms 2, 세 팔 × {포착 s47·s31·s43, 잡} 12, f_vref 1)가 각각 정확히 한 줄 rc 0·VISSIM 전후 0, `f_persist` 한 줄 rc 1, 그 밖 F 단계 이름 0 |
| C10 | 세 팔의 잡 폴더 이름 38개 = 선언 라벨, 포착 폴더 38개 = 선언 태그(각 `SAF` 하위), `f_vref` 파일 = `sa/k92_vissim_ref.json` 하나·sha 같음, `OUTK/f_persist`·`OUTK/f_persist30` 없음 |
| C11 | `OUTK/logs/f_*_jobs*.log` = F 잡 로그 셋, 크기·sha = §0 |
| C12 | 봉인 뿌리 맨 위 = K9-2-0·K9-2-1·K9-2-2·K9-2-3·a27(다섯), OUT30 없음 |
| C13 | OUTK 파일 목록(경로·크기·sha) = `AD30/out/outk_inventory_decl.json`(18,019파일)과 다름·한쪽 0 |
| C14 | VISSIM 0, 남의 러너·재생 프로세스 0(`KI/k92lib.py` `census`) |
| C15 | C:·D: 여유 ≥ 8 GB |

- 출력 `OUT30/check30.json`(OUT30을 처음 만드는 파일). 거짓이 하나라도 있으면 `STOP_a30_check30.json`(S-K41).
- 이 Declare 판 상태에서 `--mode decl`은 C1–C15 거짓 0입니다(C2·C6은 보고만, C12의 OUT30 조건은 decl에서 면제) [실행 `check30_decl.json`].

### 4.2 seal30 — F 잡 로그 봉인 이동과 잡 정상 셈 (D-K9-57 ⑤; `k92t30.py:682-732`)

- **옮기는 파일(닫힌 목록, 셋)**: `OUTK/logs/f_f_off_jobs.log`, `f_f_w_jobs.log`, `f_f_b1_jobs.log`(크기·sha §0). 이 파일에는 F 잡마다 하네스의 `SA_JOB <라벨> exit=… wall=… ok=… objective=<값>` 줄(`sa_jobs.py:385-386`)과 구동기 자식의 `K92T_JOB <뿌리> <라벨> ok=<…>` 줄(기반 `k92t.py:446-447`)이 있습니다 [읽음 코드; 파일은 열지 않음]. 라벨에 v3c3-s47 주 표본 22상태가 들어 있습니다(둘째 표본 s31·s43 잡 줄도 섞여 함께 봉인).
- **옮길 곳**: `SEALED/k92t/logs/<같은 이름>`. 새 하위 폴더 `SEALED/k92t`는 seal30이 처음 만듭니다(있으면 STOP).
- **방법**: 옮기기 전 크기·바이트 전체 sha = §0, 봉인 뿌리 맨 위 = 다섯, `SEALED/k92t` 없음 → 같은 D: 볼륨 안 `os.replace` 셋 → 옮긴 뒤 크기·sha 같음, 원래 자리 없음, 봉인 뿌리 맨 위 = 다섯 + `k92t`. 파일 내용을 글로 읽지 않습니다(sha 계산만). 옮기기 실패는 STOP(파일 이름과 예외 종류만).
- **목록(봉인 뿌리 밖)**: `OUT30/sealed_k92t_index.json` — 파일마다 이름, 원래·새 경로, 크기, sha256, 원래 수정 시각, 옮긴 시각, 옮긴 뒤 점검 셋, 보충 30 sha. LOG에는 파일 수·참거짓·목록 sha만 적습니다.
- **기반 기록과의 관계**: `steps.jsonl`의 세 F 잡 줄의 `log` 칸은 옛 경로를 가리킨 채 둡니다(그 기록은 고치지 않음). 새 경로는 목록 파일로만 찾습니다.
- **잡 정상 셈(사람·에이전트는 로그를 보지 않음)**:
  1. **종료 코드**: `steps.jsonl` 첫 59줄의 F 단계 24개 rc 0·VISSIM 0(C9). 구동기가 이름·숫자 칸만 읽습니다.
  2. **요약 파일**: f30 첫 걸음 `k92t30_judge.py fcount`(`:802-812`, `job_counts` `:770-799`)가 세 팔 × {s47 주 22, s31 8, s43 8}마다 잡 폴더 수, `summary.json`의 `ok`가 참인 수, `k92_record.json`이 있는 수, 그 `errors`가 빈 수, `capture.json` ok 수를 셉니다. 출력은 개수뿐입니다(`OUTK/judge/f_jobs.json`). 모든 칸이 계획 수와 같아야 PASS, 아니면 INCOMPLETE → STOP(S-K44). 이 셈은 F 판정 전·지속성 VR 전입니다.
  3. 같은 개수를 F 판정 파일 `job_counts` 칸에도 적습니다.
- 기반 관문 보고의 "summary ok 38/38, 구동기 줄로만 셈"(`GATES_K92B1.md` §3)은 위 2로 바꿔 보고합니다(§5.5 공개).
- **봉인하지 않는 k92t 로그(까닭)** [읽음 코드]: `f_*_cap_s47.log` 등 포착 로그 — `SA_CAPTURE … exit= wall= out=` 줄만(`sa_capture.py:228`, `sa_cap_child.py:269-285`); `f_vref.log`·`f_persist.log`·`f_persist30.log` — VR 상태 목록·sha 앞자리·초만(`k92_vissim_ref.py:154`, `:164`, `:176-177`, SystemExit 글); `prep_f_*` — 상태 준비; J 로그(`j0_*`, `ja_*`, J-b의 `jb_*`) — K9-1 판정 상태(TL3m GRID9 등)이고 F 주 표본이 아님(K9-1 V4 기록과 같은 꼴). J-b 로그의 v3c3-s47 GRID9 잡 줄도 이 까닭으로 봉인하지 않습니다.
- **F 데이터 폴더(옮기지 않음, 열지 않음)**: `OUTK/f_off|f_w|f_b1/sa/{jobs,cap}/k92t/` 아래 v3c3-s47 라벨·태그 폴더의 모든 파일(데이터 파일과 잡 폴더 `log.txt` 포함), `OUTK/f_vref/**`, `OUTK/f_persist30/**`는 J·F 값 고정 전 사람·에이전트·감시 스크립트가 열지 않습니다(이름·크기·수정 시각·바이트 전체 sha만, 보충 25 §6.4와 같은 꼴). 고정된 판정기(`fcount`·`f`)와 VR만 메모리에서 읽습니다.

### 4.3 f30 — 기존 F 데이터로 F 판정 (`k92t30.py:735-774`)

1. `a30_sha`, `require_prev('f')`(seal30 기록 필요), VR sha = `f3fcc574…`(아니면 S-K21), `f_inputs_check`(C9·C10 다시) 참, `judge/f_jobs.json`·`judge/f.json`·`OUTK/f_persist30` 없음.
2. **fcount** → PASS가 아니면 STOP(S-K44). LOG: 판정과 파일 sha.
3. **지속성 VR**(§2.3, 단계 `f_persist30`) → rc ≠ 0이면 STOP(S-K43, INCOMPLETE).
4. **F 판정** `k92t30_judge.py f --tree TREE --dest OUTK/judge/f.json`(자식, cwd = TREE의 SA). LOG에 판정·F-1·F-2·F-3·n·지속성 측정 수·측정 불가 목록·`complete`·파일 sha("F 판정 값 고정").
5. 판정이 PASS가 아니면 STOP: FAIL → STOP_ASK_F(S-K9), INCOMPLETE → STOP. PASS이고 지속성 `complete`가 거짓이면 STOP(S-K43). 아니면 단계 기록 `stages/f.json`(f.json·f_jobs.json·지속성 파일 sha).
- 다시 돌리지 않는 것: F 포착·잡(세 팔 각 38), `f_vref`, 팔 파일, prep.

### 4.4 jb — J-b (D-K9-57 ②; 기반 `stage_jb` 그대로, 판정기 경로만 새 파일)

- 판정 정의: 보충 24 §5.2 J-b 행(:326) 그대로 — `gates_k91t.json`(`4e59f61d…`)의 G-EB-2·3·4·5·6·7·8·13·14 항목 가운데 `pass_`가 null 아닌 것 전부를 SAF-K92b1로 다시 계산해 repr 같음. 다르면 STOP_ASK_J, 판정 파일 없으면 INCOMPLETE → STOP.
- **다시 돌리는 BASE 실행(닫힌 목록, 같은 코드 트리 안 비교가 필요한 것만)**: ROBS61 BASE T=1·150 × v3c3-s31·s43·s47(같은 실패 규칙이 예외 줄의 코드 트리 경로를 비교함), TL3 BASE 2,700과 T9C BASE 2,700(T9b·T9c 포착 상태 시험), full BASE 2,700·4,950 hooks(G-EB-13 양성 대조; hookcount가 TREE의 줄 패치를 기대함). 모두 jb 뿌리에서 TREE로.
- **복사(k91t 산출 바이트)**: 그 밖의 모든 BASE·SAG 잡 폴더, BASE·SAG·BASE_fhoff 포착 폴더(위 다시 돌림 여덟 뺌), `full/002700_BASE`, `sa/fzp`, `opt1v2`, G-EB-13 검토 입력 `leader_review_k91t.json`(`ba80564c…`).
- **SAF-K92b1로 다시 돌리는 것**: K9-1 사슬의 SAF 실행 전부(포착 robs61 s43·s47, fh, fh `--fh-disabled --seeds 31`, fh `--frames T-150,T,T+150`; 4c 단위 시험 넷(선언 시험, 금지 시험 아님); 가족 tl3·long·tl3m·fh·dp·adfull·tl3 hooks 2,700·c11·tan·h4·h0·h3·h5 `--arms SAF`; full SAF 2,700·4,950 hooks; `sa_hookcount.py`; `sa_gates.py --only <위 게이트>`). J-0이 만든 SAF 포착과 J 짝의 SAF-K92b1 잡 11개는 jb 뿌리에 이미 있어 하네스가 건너뜁니다(포착 `capture.json` 있음 → `SA_CAPTURE_SKIP`, `sa_capture.py:198-199`; 잡 `summary.json` 있음 → `SA_JOB_SKIP`, `sa_jobs.py:350-353`) [읽음].
- 다시 돌리지 않는 것: compare g1·g9·h0·h4, sa_smoke, wallpairs, k84v3 바탕 트리 실행(어느 J-b 판정 항목도 읽지 않음).
- 비용 어림 약 12 h [추론, 보충 24 :326 어림 12–17 h].

### 4.5 post30 — 사후 (D-K9-57 ③, D-K9-55; `k92t30.py:777-808`)

- **J·F 값 고정의 정의**: `judge/f.json`과 `judge/jb.json`의 sha256 64자가 둘 다 `KB/LOG.md`에 있는 상태(f30·jb의 자동 LOG 줄). post30은 이것을 먼저 기계로 봅니다(아니면 STOP).
- **post30이 하는 일**: (1) 봉인 뿌리 `k92_record.json` 훑기(기반 판정기와 같은 함수 `scan_vissim_blind(sealed=True)`; VISSIM 쪽이 `null`·이유 `k92_blind_s47`인지, 이름·개수만), (2) 봉인 k92t 목록 대조(세 파일이 새 자리에 있고 크기·sha = 목록, 원래 자리 없음), (3) 이어 받은 기반 기록 11개 바이트 같음, (4) LOG에 "J·F 값 고정 확인 — 이제 봉인 로그는 보충 25 §6.4대로 열 수 있음, G-K4 plant 원자료 재계산은 독립 검증기 몫". 하나라도 거짓이면 STOP(S-K10, S-K42, S-K41).
- **J·F 값 고정 뒤에만 허용되는 것**:
  - 봉인 로그(기존 봉인 뿌리 + `SEALED/k92t/logs/` 셋)와 v3c3-s47 F 데이터 폴더(§4.2 끝)를 진단·보고용으로 엶 — 열 때마다 LOG에 파일, 시각(분까지), 목적(보충 25 §6.4).
  - **G-K4 plant 원자료 재계산(D-K9-55)**: 보충 29 §5 그대로(누가 = k92t 독립 검증기, 행 4개, 옛·새 쪽, 규칙, 통과 = 기록 판정과 같음, 다르면 S-K40). 시점 = post30 끝(LOG의 post30 줄) 뒤. 그 전에는 바이트 대조만.
- J·F 값 고정 전 k92t 실패 진단은 보충 25 §6.4의 예외로 열 수 있습니다. 그때도 LOG에 파일·시각(분까지)·목적을 적습니다.

### 4.6 시간 어림 [추론]

- check30 약 5–10분(TREE·K925 비교 4.2 GB, OUTK 목록 4.2 GB; Declare drive 약 3분), seal30 수 초, f30 약 3–5분(VR 약 1.5분, 기반 f_vref 89.5 s), jb 약 12 h, post30 수 분, 스냅숏 다섯 × 약 1분.

---

## 5. 조작화와 공개 (D-K9-57 ①–⑤)

### 5.1 ① J-0 "R-obs3 61/61" 글

- 보충 24 :324 J-0 행의 "G-EB-14 초기화 61/61 오류 0"을 다음으로 읽습니다(사용자 결정 D-K9-57 ①): R-obs3(v3c3-s31) ROBS61 상태 61개 가운데 **59개는 두 팔 모두 초기화 통과**, **T=1과 T=150 두 개는 두 팔이 같은 자리에서 같은 실패**(예외 줄과 런타임 프레임 서명이 같음, 보충 13 G-EB-14 규칙, 기반 판정기 `j0_state`)이면 통과로 셉니다. 합 61 → J-0 PASS.
- **공개(보고서마다 그대로)**: 글자 그대로 세면 59/61입니다. K9-1 기록(`gates_k91t.json` G-EB-14 `i_init`)도 시드마다 59/59이고 T=1·150은 따로 보고했습니다(보충 13 :26 "T=1·150 이 BASE 와 같은 위치·같은 예외로 실패하면 보충 9 선례대로 보고"). 실패 글: T=1 `FileNotFoundError … __missing_previous.json`, T=150 `ValueError: Previous command must be the immediately preceding action in this run` [읽음 VerifyGates §4].
- 기록 `judge/j0.json`(`24ee9d3b…`)은 그대로이고 다시 판정하지 않습니다.

### 5.2 ② J-b 범위 — §4.4.

### 5.3 ③ 봉인 뿌리 기록 훑기 — §4.5. 그리고 O7′

- 기반 구동기 머리말 O7("판정 입력을 빠뜨리는 rc≠0")은 코드(`must()`, 모든 rc≠0에서 STOP)보다 좁게 적혔습니다(VerifyGates §9-1). 이 보충은 코드대로 적습니다: **새 구동기의 모든 단계 실행은 rc ≠ 0이면 STOP**(INCOMPLETE). 기반 STOP의 근거는 보충 24 §6 INCOMPLETE(:365)·S-K12(:400)입니다.

### 5.4 ④ 검증자 J-a 다시 셈과 검증 도구 고정 시점

- **공개**: VerifyGates r1의 고정 J-a 도구 `vg_ja.py`(`ffa3d2dc…`)는 결정 2개를 보류로 냈고(사전 키 안의 `/` 경로 찾기 결함), 데이터를 본 뒤 고친 사본 `vg_ja2.py`(`eb0dacbc…`)는 PASS를 냈습니다. 이것은 보충 24 S-K12(독립 검증기를 데이터 뒤 바꿈)에 걸리는 일이며, 두 결과를 모두 기록으로 둡니다(`VERIFY_GATES_K92B1.md` §5, §9-6).
- **다음 검증의 J-a 다시 셈(규칙)**:
  1. **새 파일**로 씁니다. `vg_ja.py`·`vg_ja2.py`와 이름이 다르고, 그 바이트 사본이 아니며, 그 두 파일을 import하지 않습니다. 하네스·k92t 구동기·판정기도 import하지 않습니다(보충 24 §5.4).
  2. 정의는 글에서 따로 구현합니다: 잡 21개 = summary 숫자 잎 같음(K9-1 G5 제외 규칙), 결정 2개 = 보충 21 §6 결과 넷(N과 보충 27 §2.1·보충 29 §2.5의 K9-2 뿌리 규칙, HARD H1–H5, 허용 V ∪ R3 ∪ F − D, A_K92 네 조건(옛 뿌리 = `k8_gate_trees/k91t`), A_K92-M 쪽·깊이), 옛 쪽 = `V4/sa/{jobs,full}/k91t`, 새 쪽 = `OUTK/ja/sa/{jobs,full}/k92t`.
  3. **고정**: 그 도구의 sha256을 LOG에 적은 **뒤에만** k92t 산출(OUTK)이나 V4 k91t 산출에 처음 돌립니다. 고정 전 시험은 합성 입력에서만 합니다.
  4. **한 번** 돌려 23항목을 냅니다. 통과 = 항목마다 `judge/ja.json`의 판정과 같음(잡 21 SAME, 결정 2 PASS·HARD 같음·미분류 0). 하나라도 다르면 STOP(S-K45, 사용자 결정).
  5. 첫 실행 뒤 그 도구를 고치면 결과와 무관하게 STOP(S-K12, S-K45). 결함이 보이면 고치지 않고 보고합니다.
- **검증 도구 고정 시점의 읽기(공개)**: 보충 24 §3.1-8(:216) "J·F 모듈은 판정 단계 시작 전에 고정"은 k92t가 10-20 21:45:53에 시작했으므로 이제 지킬 수 없습니다. 첫 VerifyGates의 도구 고정(10-21 07:2x, LOG 그 항목)도 그 시각 뒤였습니다. 이 보충은 다음 검증의 모든 모듈(J-a 다시 셈, F 다시 셈, J-b 다시 셈, 사후 훑기 대조, G-K4 plant 원자료 재계산)에 같은 규칙을 씁니다: **"그 모듈이 다시 내는 k92t 산출을 처음 읽기 전에 sha를 LOG에 고정"**. 이것이 §3.1-8 글보다 늦은 고정임을 보고서 머리에 적습니다(§10-6).

### 5.5 ⑤ 앞서 열람 가능성 공개

- 기반 관문 단계(Gates)는 F 잡 정상 여부를 "구동기 줄로만 셈(ok 38/38)"이라고 적었습니다(`GATES_K92B1.md` §3). 그 줄(`K92T_JOB`)은 F 잡 로그 셋에만 있습니다. 보충 25 §6.4는 걸러 읽기(`grep` 등)도 "엶"으로 봅니다. 같은 파일에는 v3c3-s47 F 잡 22개 × 3팔의 `SA_JOB … objective=<값>` 줄이 있습니다. 그 걸러 읽기가 SA_JOB 줄을 화면에 냈는지는 기록이 없습니다. 그래서 **v3c3-s47 F 잡 목적값이 Gates 단계의 화면에 나왔을 가능성**을 공개합니다 [추론; 확인할 기록 없음]. 목적값은 F 지표(M1·M2·M3)가 아닙니다.
- 기반 구동기 자신은 이 로그를 쓰기만 하고 다시 읽지 않습니다(`k92t.py:215-236` `step`). VerifyGates는 열지 않았다고 적었습니다(§10). 이 Declare 판은 바이트 sha만 셌습니다.
- 그 밖에 Gates 단계는 실패 진단으로 `logs/f_persist.log`의 끝 줄 하나를 "07:0x"에 열었습니다(분 미상; VR 글이고 값 없음). 앞으로는 분까지 적습니다(§4.5).

---

## 6. 적용 순서 (Apply 단계; 하나라도 거짓이면 STOP, 다시 돌리지 않고 보고)

공통: 보충 24 §3.1-4 그대로(무거운 Python 한 번에 하나, BELOW_NORMAL, `python -B`, `PYTHONHASHSEED=0`, 5분 넘는 단계는 WMI 분리 `KI/launch.ps1`, 기다림 확인 한 번에 9분 이하, 자기 PID만 끔, C:·D: 8 GB 밑이면 멈춤). 발사 줄: `powershell -NoProfile -File KI/launch.ps1 -Tag <태그> -Script ..\a30decl\k92t30.py -ArgLine <명령>`(태그 로그 `OK2/logs/<태그>.txt`는 새 이름만).

| # | 내용 | 통과 조건 |
|---|---|---|
| G0 사전 확인 | 보충 30 sha = `.sha256` = 고정점 30(64자). 결정 기록 앞 182줄 sha = `eae2e6fa…`. 보충 24–29·고정점 sha(§0). `KB/k92t_pins.sha256` 56/56 OK. 고정점에 적힌 기대 고정 목록(Declare 판은 `AD30/a30_pins.expected.sha256`, 검토가 고치면 고정점이 정한 파일)에 `sha256sum -c` 전부 OK·종료 0. GWT8 상태(C4). python·VISSIM 0. 드라이브 | 모두 참 |
| G1 고정 | 기대 고정 목록 바이트를 `KB/a30_pins.sha256`에 씀, `cmp` 같음, `sha256sum -c` 전부 OK, 그 sha·줄 수를 LOG 한 항목에 | 같음·OK·종료 0 |
| G2 사슬 | 발사 전 `sha256sum -c KB/a30_pins.sha256` OK → WMI `-Tag k92t30_chain -ArgLine chain30` → 기다림(9분 이하 간격, 프로세스 유무·`OUTK/stages/*.json`·`STOP_a30_*.json`·종료 코드만 봄; 로그 걸러 읽기 금지) | `OUTK/stages/post.json` `ok` 참, `STOP_a30_*` 0 |
| G3 마무리 | 끝 대조(`KB/a30_pins.sha256` 전부 OK), GWT8 head·status·K8·원격, 보고서 `KB/GATES_K92B1_A30.md`(사본 `OK2/GATES_K92B1_A30.md`), LOG | 대조 OK, status 0줄, head = K9-2-5, 커밋 6개, 푸시 0 |

- G2 가운데 STOP하면 G3의 끝 대조·GWT8 점검·보고서·LOG는 하고 사용자에게 넘깁니다.
- 보고서 머리에는 `GATES_K92B1.md` 머리 공개 1–6, 보충 27 §8·§13, 보충 28 §9, 보충 29 §11, 이 보충 §10을 옮겨 적습니다. 지속성 보고 줄은 §2.4 글로, J-0 줄은 §5.1 글로 적습니다.
- 독립 검증(§5.4)·G-K4 plant 원자료 재계산(§4.5)·V-B·V-A는 이 순서에 들지 않습니다. V-B는 K92_GATES_PASS(보충 24 §6) 뒤, V-A는 사용자 결정 뒤입니다.

---

## 7. STOP 규칙 (보충 24 §8·25 §9·26 §7·27 §11·28 §7·29 §8에 더함)

- **S-K41** 이어 하기 위반: check30 거짓(C1–C15 하나라도); 보충 30 sha·고정점 다름; `KB/a30_pins.sha256`·`KB/k92t_pins.sha256` 대조 다름(발사 전·끝); 보충 30 고정 뒤 기반 구동기 `KT/k92t.py`나 기반 판정기로 k92t 단계를 돌림; `chain30`을 새 기록이 있는 상태에서 다시 돌림; F 입력(이름·종료 코드·`f_vref` sha·OUTK 파일 목록) 다름; 이어 받은 기반 기록 바이트가 바뀜; 허용 밖 STOP 파일 → STOP, 사용자가 정함.
- **S-K42** 봉인 위반: 옮길 파일 집합이 셋과 다름, 옮기기 전·뒤 크기·sha 다름, 봉인 뿌리 맨 위가 선언과 다름, `SEALED/k92t`가 이미 있음, 옮기기 실패, post30 목록 대조 거짓, J·F 값 고정 전에 F 잡 로그(새 자리 포함)나 v3c3-s47 F 데이터 폴더 파일을 엶(걸러 읽기 포함; k92t 실패 진단 예외는 LOG에 파일·분까지 시각·목적이 있을 때만) → STOP·보고(보충 25 S-K23과 같은 처리).
- **S-K43** 지속성: VR 호출 상태가 §2.2의 21개와 다름(600 포함), VR rc ≠ 0, 지속성 보고 `complete` 거짓 → STOP(INCOMPLETE). F 판정 칸은 바꾸지 않습니다.
- **S-K44** 잡 정상 셈: `fcount` 판정이 PASS가 아님(어느 팔·표본 무리든 계획 수와 다름) → STOP(INCOMPLETE), 지속성 VR·F 판정 전.
- **S-K45** 검증 도구: 다음 검증의 J-a 다시 셈 결과가 `judge/ja.json`과 다름, 또는 그 도구(그리고 F·J-b·사후·plant 모듈)의 sha를 첫 읽기 뒤에 고정했거나 첫 실행 뒤 고침 → STOP, 사용자가 정함.
- 그대로: S-K8(J-b 다름 → STOP_ASK_J), S-K9(F 거짓 → STOP_ASK_F), S-K10(사후 훑기), S-K11(스냅숏 다름·봉인 시드·쓰기 금지 뿌리), S-K12(데이터 뒤 판정기·구동기·기준 변경; 이 보충의 새 구동기·판정기는 보충 30 고정 뒤 첫 보충 30 데이터(check30 apply 출력) 전에 고정하며, 그 뒤 변경은 S-K12), S-K14(드라이브), S-K21(VR sha), S-K23(보충 25 봉인), S-K40(plant 재계산 다름). 보충 24–29의 나머지 규칙도 그대로입니다.

---

## 8. 보충 24–29가 바뀌는 곳 (그 밖은 그대로 구속)

| 자리 | 옛 내용 | 이 보충 | 근거 |
|---|---|---|---|
| 보충 24 §5.3 보고 목록(:347) "M1 persistence MAE" | 주 표본 22상태(암묵) | T−450 ≥ 900인 21상태만 측정, T=1,050 = "측정 불가(T_FROM=900)", 겹침 15 같음·완전성 점검, 불완전 → STOP(§2) | D-K9-56 |
| 보충 24 §5 k92t 구동기(기반 `KT/k92t.py`) | start…post 한 사슬, 기반 STOP 뒤 이어 하기 규칙 없음 | 새 구동기 `AD30/k92t30.py`로 check30 → seal30 → f30 → jb → post30(§3·§4); 기반 기록 유지 | D-K9-56 |
| 보충 24 §5 k92t 판정기(기반 `KT/k92t_judge.py`) | F 지속성 22상태, 잡 수 없음 | 새 판정기 `AD30/k92t30_judge.py`: `cmd_f` 지속성·잡 수, `fcount` 새 명령, J 함수 글 그대로(§3.3) | D-K9-56, D-K9-57 ⑤ |
| 보충 25 §6.2 봉인 대상 | k92t 전 봉인 실행 | + k92t의 F 잡 로그 셋을 `SEALED/k92t/logs/`로(§4.2), 목록은 `OUT30` | D-K9-57 ⑤ |
| 보충 25 §6.4 여는 규칙 | 봉인 로그 | + F 잡 로그 셋과 v3c3-s47 F 데이터 폴더도 같은 규칙, "J·F 값 고정" = f.json·jb.json sha가 LOG에 있음, 열람 시각은 분까지 | D-K9-57 ③⑤, D-K9-55 |
| 보충 24 :324 J-0 "61/61 오류 0" | 글자 그대로 | 59 + 같은 실패 2 = 61로 셈, 글자 그대로 59/61 공개(§5.1) | D-K9-57 ① |
| 기반 구동기 머리말 O7 | "판정 입력을 빠뜨리는 rc≠0" | 모든 rc≠0 → STOP(코드대로, O7′) | VerifyGates §9-1 |
| 보충 24 §3.1-8 독립 검증기 J·F 모듈 고정 시점 | 판정 단계 시작 전 | 다음 검증 모듈은 "그 모듈이 다시 내는 k92t 산출을 처음 읽기 전" — 글보다 늦음을 공개(§5.4) | D-K9-57 ④ |
| 보충 29 §5 G-K4 plant 원자료 재계산 시점 | "J·F 판정 값 고정 뒤" | 같은 뜻, 기계 조건 = post30 끝(§4.5) | D-K9-55 |
| 보충 24 §6 K92_GATES_PASS | J-0·J-a·J-b·F-1–F-3 PASS, 독립 검증 일치 | 같음 + 이 보충의 check30·seal30·fcount·지속성 `complete`·post30 PASS(새 조건은 모두 STOP을 늘리는 쪽) | D-K9-56·57 |

- 바꾸지 않는 것: F-1·F-2·F-3의 식·문턱·표본·팔·VISSIM 기준, J-0·J-a·J-b의 정의·문턱(보충 24 §5.2), J 잡 벽시계 문턱 1.0158, G-K4 plant 재계산 규칙(보충 29 §5), 봉인 시드·블라인드 규칙, 커밋 K9-2-0…5와 그 관문 기록, 비교 규칙(보충 21·27·29). 푸시 0(V-A 사용자 결정 뒤에만).

---

## 9. 고정 목록 (G1; `KB/a30_pins.sha256`, 83줄)

- 줄 꼴: `<sha256 64자> *<절대 경로, / 구분>`, LF, CR 0, 끝 줄바꿈 있음(보충 29 §10과 같음).
- **기대 파일** `AD30/a30_pins.expected.sha256`: sha256 `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e`, 83줄, 14,537 B [실행 `sha256sum -c` 83/83 OK]. G1이 쓰는 `KB/a30_pins.sha256`은 이 바이트와 같아야 합니다(반박 검토가 파일을 고치면 고정점이 새 기대 파일과 sha를 정합니다).
- **고정점 30이 적어야 하는 것(구동기가 기계로 봄)**: 고정판 보충 30의 sha256(64자; `a30_sha`, `k92t30.py:499-508`)과 `KB/a30_pins.sha256`이 될 기대 파일의 sha256(64자; check30 C6, `k92t30.py:621-628`). Declare 판 보충 30의 sha는 고정점에 64자로 적지 않습니다(앞 16자만; 보충 29 §14.1 V4와 같은 까닭 — 되돌린 파일이 통과하지 않게).
- C6 문자열 점검 [실행]: 새 구동기를 불러 `pins_check(기대 파일)` = 83줄·틀린 줄 0, 구동기·판정기의 `'<sha> *<경로>'` 글자가 기대 파일 안에 그대로 있음(참, 참).
- **1–56줄** = `KB/k92t_pins.sha256`(`38a2ce14…`)의 56줄 그대로(기반 구동기·판정기, KI `launch.ps1`·`k92lib.py`·`k92snap.py`, `run_pytest_bn.py`, 기반 pre·tree 기록, `gates_k91t.json`, `leader_review_k91t.json`, V4 `vissim_ref.json`, `k925_blobs.json`, P0-4 두 파일, K9-1 BASE, TREE의 하네스·판정 파일 39개).
- **57–83줄**:

| 줄 | 파일 | sha256 |
|---|---|---|
| 57 | `KB/k92t_pins.sha256` | `38a2ce147795bbe7613fa5b6633441b31b814e781d1948e550753db776ed7cdd` |
| 58 | `AD30/k92t30.py` | `8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4` |
| 59 | `AD30/k92t30_judge.py` | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` |
| 60 | `AD30/dry_a30.py` | `c685b5bad597de6769c29178d737ec1837c18a58c31f51e3a51817e7f792901d` |
| 61 | `AD30/A30_DRIVER.diff` | `a9d5087d81d01b50695ecc945bd6eb40579f02fb8dff9dbe5e215b797bbeaaa7` |
| 62–63 | `AD30/base/k92t.py` / `base/k92t_judge.py` | `b07ffb56…` / `eb4c113a…` |
| 64 | `AD30/out/outk_inventory_decl.json` | `33101cd1b43b8be8dcf020f4e4c559d21329d3e67b7333afe0519975ecfa0dfc` |
| 65–69 | `AD30/dry/decl/` `dry_a30_static.json` / `dry_a30_synth.json` / `dry_a30_drive.json` / `check30_decl.json` / `seal30_dry.json` | §3.4 표 |
| 70–80 | OUTK 이어 받는 기록 11개(§0 순서: `STOP_f.json`, `k92_judging_stage.json`, `start/scans.json`, `stages/{start,prep,j0,ja}.json`, `judge/{j0,ja,jwall}.json`, `f_vref/sa/k92_vissim_ref.json`) | §0 |
| 81 | `OK2/logs/k92t_chain.txt` | `8140fd2fa2d04a3781d8a3068a7171be0e6a22d34ced1d3d45cb78e12d22d728` |
| 82 | `OK2/snap/s02_after_probe_stop.json`(스냅숏 기준) | `88a5e142872f9141b65c279622d3f3546dab1e7012a1b5e053e679bcc755d5dd` |
| 83 | `OK2/snap/s28_a30decl.json` | `c94eb83fdef3800b38722ba630408e44936f713e4c4bde22ec83ab09cdc556a5` |

- 목록에 넣지 않는 것(창 안에서 바뀜): `OUTK/steps.jsonl`·`driver.log`(덧붙음; 첫 59줄·첫 3,434 B는 check30이 봄), F 잡 로그 셋(옮겨짐; sha는 구동기 상수 `F_JOB_LOGS`와 §0), `KB/LOG.md`, 보충 30 자신과 고정점(구동기 `a30_sha`가 봄).
- **고정 창**: G1부터 G3 끝 대조까지. 그 안에서 83개 가운데 하나라도 바이트가 바뀌면 S-K41. 발사 전·끝에 `sha256sum -c KB/a30_pins.sha256` 83줄 OK·종료 0.

---

## 10. 알려진 사실·한계 (G3 보고서·다음 검증 보고서 머리에 옮김)

1. **데이터를 본 뒤의 보충**: J-0·J-a·J 벽시계 PASS를 본 뒤입니다. F·J-b 값은 아직 없습니다. F 판정 정의는 그대로입니다.
2. **지속성 보고 21/22**: 보충 24 §5.3이 선언한 보고 항목이 한 상태 줄었습니다. 원인은 기반 설계가 U4 측정기 T_FROM을 보지 못한 결함(`GATES_K92B1.md` §4-9)이고, VerifyGates가 s43으로 원인을 다시 만들었습니다.
3. **새 점검 셋은 STOP을 늘리는 쪽**: 겹침 15 같음(지속성), `fcount`(W 팔·둘째 표본 잡까지 정상이어야 함 — 보충 24 §6 INCOMPLETE 규칙을 보고 항목에도 기계로 적용), check30의 OUTK 파일 목록 대조.
4. **v3c3-s47 F 잡 목적값 노출 가능성**(§5.5). 확인할 기록이 없습니다.
5. **J-0 글자 그대로 59/61**(§5.1). K9-1 기록도 같은 꼴(59/59 + T=1·150 따로)입니다.
6. **검증 도구 고정 시점**: 보충 24 §3.1-8 "판정 단계 시작 전"은 첫 VerifyGates(10-21 07:2x 고정)도, 다음 검증도 지킬 수 없습니다. 다음 검증은 "처음 읽기 전 고정"(§5.4)입니다. 첫 VerifyGates의 J-a 도구 사후 수정(vg_ja → vg_ja2)은 S-K12 꼴이며 기록으로 둡니다.
7. **VerifyGates의 대표 잡 다시 돌리기 DIFFERENT**(출력 뿌리 경로에서 나온 해시·시간 값)는 그 검증의 기록으로 남습니다. 이 보충은 그 비교 규칙을 바꾸지 않습니다. 다음 검증이 다시 돌리기 비교를 하면 그 규칙은 도구 고정 전에 정합니다.
8. **TREE의 실행 캐시**: J-a·J-b가 `__tangentcache__/*.mcode`를 만듭니다(지금 90개). 트리 대조(C7)는 기반과 같이 캐시 폴더를 뺍니다. 커밋 파일 10,569개는 블롭과 같습니다(VerifyGates §9-4).
9. **D-K9-44 계속**: 기존 어댑터는 결정마다 봉인 시드·v3c3-s47 이름 파일의 sha를 계산합니다. J-b의 full hooks 결정·포착에서도 그대로 일어납니다(기록만, 고침은 둘째 묶음).
10. **이름 바꾼 판정기**: J-0·J-a·J 벽시계는 기반 판정기 `eb4c113a…`가, F·J-b·사후는 새 판정기가 냅니다. 두 파일의 공유 함수 글은 바이트 같습니다(§3.3).
11. **STOP 파일 둘**: 기반 `STOP_f.json`은 OUTK에 남습니다. 새 STOP은 `STOP_a30_<단계>.json`입니다.
12. **OUTK 파일 목록에 v3c3-s47 라벨 이름**이 들어 있습니다(`AD30/out/outk_inventory_decl.json`, 이름·크기·sha만, 값 0). 보충 25 §6.5-4 새는 줄 규칙(이름 꼴 + 값 꼴·잡 줄 꼴)에 걸리는 줄은 없습니다(JSON 파일이고 값 꼴 없음) [추론].
13. **4c 단위 시험**(J-b 안): 선언된 시험 넷(`test_stopline_*`)이며 금지 시험이 아닙니다.
14. 보충 24 §2.6의 한계 1–13, 보충 25 §11, 보충 26 §10, 보충 27 §13, 보충 28 §9, 보충 29 §11, `GATES_K92B1.md` 머리 공개 1–6은 그대로입니다.

---

## 11. 자체 점검

1. **빈 칸**: "나중에 정함"·자리표가 없습니다. 아직 생기지 않은 값은 규칙으로 정했습니다: 보충 30 자신의 sha(`.sha256`·고정점 30), `KB/a30_pins.sha256`(G1 = 기대 파일 바이트), OUT30 기록·판정 파일·단계 기록(구동기가 쓰고 LOG에 sha), 다음 검증 도구 sha(첫 읽기 전 LOG).
2. **D-K9-56**: 좁힐 상태(1,050 하나, §2.2), 글자(§2.2), 도구 호출·건너뜀(§2.3), 보고 꼴(§2.4), F-1–F-3 불변(§2.5), 기존 F 데이터로 F 판정 → J-b → 사후(§4).
3. **D-K9-57 ①**: §5.1 글. **②**: §4.4 닫힌 목록. **③**: §4.5(J·F 값 고정 뒤 post30). **④**: §5.4(공개 + 새 도구 규칙 + 고정 시점). **⑤**: §4.2(옮길 셋, 자리, 방법, 목록, 잡 정상 셈 = 종료 코드 + 요약 파일), §5.5(열람 가능성).
4. **D-K9-55**: §4.5(post30 끝 뒤, 보충 29 §5 그대로).
5. **구동기 변경과 새 고정**: §3, §9. **STOP 규칙**: §7(S-K41–S-K45).
6. **이어 하기 규칙**: 유지할 기록(§4 머리), 순서(§4), 점검(§4.1).
7. 판정 말 없음, 결과는 PASS·FAIL·보류·INCOMPLETE·STOP과 숫자.

---

## 12. 파일 (AD30 = `KB/a30decl`)

| 파일 | sha256 |
|---|---|
| `k92t30.py`(새 구동기) | `8f28171e7a3721a73f71216ca2823d179b78914dfbf70ef309a2b70fb5223ec4` |
| `k92t30_judge.py`(새 판정기) | `a1937942f06cb7d7e0be400dfc367691e9e6575061ed5aa00cee370f697fe7bf` |
| `dry_a30.py`(데이터 없는 확인) | `c685b5bad597de6769c29178d737ec1837c18a58c31f51e3a51817e7f792901d` |
| `A30_DRIVER.diff` | `a9d5087d81d01b50695ecc945bd6eb40579f02fb8dff9dbe5e215b797bbeaaa7` |
| `base/k92t.py` / `base/k92t_judge.py` | `b07ffb56789c30c8ef2f60f098ae7212fec52eec8a307b959bf26c44c6f02bec` / `eb4c113a6b7194cdf00d193d5faf07b426aae61a49ff84ae442bcf29b59fb28e` |
| `out/outk_inventory_decl.json` | `33101cd1b43b8be8dcf020f4e4c559d21329d3e67b7333afe0519975ecfa0dfc` |
| `dry/decl/dry_a30_static.json` / `dry_a30_synth.json` / `dry_a30_drive.json` | `319810d8274be5e74984194e2284f4d0981dc7c06d4cb1464a021413acdc10e6` / `d4e18b3607b7121fc595e7a3169f72fd2ce572156843d2276acfd0706e757aee` / `ac43a43fa42690d967ad4d7066a96dd5b3503658a5ff12d85bd3dbd59df9d3d9` |
| `dry/decl/check30_decl.json` / `seal30_dry.json` | `cfe7bc30c3dadd93ed2a4850842b362560d390ca30c62fc32007ab65e719b889` / `d98b5f402367e36150f0e7b1c94fd6b0b5c35aa0d23ea07c6cfd1e184a93bd3b` |
| `dry/decl/synth/`·`dry/decl/mutants/`(합성 입력·망가뜨림 사본, 실제 값 0) | — |
| `dry/dev1/dry_a30_static.json`, `dry/dev3/`(개발 실행, 보관; §0.1) | — |
| `a30_pins.expected.sha256`(83줄) | `7afabd03f315c8925c4a8bb1b1566d246cbfb9273470876963df9e7fe4f3d30e` |
| TC30 `D:/VISSIM-merge/k8_gate_trees/k92b1/a30decl/tc`(K925 `k8_gates` 사본 1.7 MB, 비교하는 출력을 만들지 않음) | — |
| `OK2/logs/a30decl_inv.txt` / `a30decl_drive.txt` / `a30decl_drive2.txt`(발사 표준 출력, 값 없음) | — |
| `dry/decl0/`(첫 선언 출력, 보관; §0.1) | — |

- 새 구동기·판정기·확인 도구·차이 파일·기대 고정 목록·확인 출력 JSON과 이 글은 줄 끝 LF, CR 0입니다. 기반 사본 둘은 기반 바이트 그대로 CRLF입니다 [실행].
