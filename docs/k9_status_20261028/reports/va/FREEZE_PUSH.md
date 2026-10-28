# K9-2 V-A PushFreeze: 푸시 + 새 동결본 FRZ_K92 + 무제어 사전점검

- 작성 2026-10-23 08:4x KST. 보충 34 §4.1(푸시)과 §4.2(동결)만 했습니다.
- 표시: **[실행]** 이번에 직접 돌려 확인, **[읽음]** 파일에서 확인, **[추론]** 시험하지 않은 판단.
- 줄임말
  - SP = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8`. VA = `SP/k92/va`. REPVA = 보고 사본 자리 `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va`.
  - GWT8 = 작업 트리 `D:/VISSIM-merge/sim3-n31-k8`, 브랜치 `claude/k92-b1-20261016`.
  - K9-2-7 = 푸시한 head `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`(GB-7′ 목록 보충 커밋). K9-2-6 = `11d99c2a…`(승격 커밋).
  - FRZ_K92 = 이번 새 동결본(얼린 사본). FRZ_K8b = 앞 동결본 `D:/VISSIM-merge/frozen/sdmpc31_b9734abe_202610141821`(읽기만 함).
  - CFG = 배포 튜닝 `diagnostics/sdmpc_n31_20260924/config_n31_v2.json`. 이번 head에서는 묶음 B1 팔 바이트(sha256 `c8e3ee2c…1866`)입니다.
  - RVA = V-A RunsRoot `D:\VISSIM_runs\20261023_sdmpc31_k92`.
  - WMI = 윈도 관리 도구. `Win32_Process.Create`로 띄우면 세션이 끊겨도 프로세스가 살아남습니다.
  - WD = 감시 러너 `scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1`.
- 근거 선언: 보충 34 `SP/K8_PREDECLARATION_AMENDMENT_34.md` sha256 `a05592d48512a515fc254d70b8173360d448b0aa17afb3f63c98b52ef713205e`(고정점 `VA/AMENDMENT34_FIXED.md` `fef58eca…c167`, 고정 목록 `VA/a34_pins.sha256` `4e447416…0403`) [실행 08:28]. 푸시 조건 `:174-178`, 동결 조건 `:180-201`.
- 바로 앞 검증: `VA/VERIFY_PROMOTE_VA.md`(sha256 `e1dc6164…89b9`) `pass = true`, 검증 head `c20aff1d…` [읽음 `:4`, 끝 줄].
- 이 단계에서 **하지 않은 일**: 커밋, VISSIM 시작, 재생·오프라인 관문, V-A 사전점검·발사, FRZ_K8b·기존 `frozen/*` 수정, K8 브랜치 변경, 금지 시험, 봉인 시드(37·59·61·67) 자료, v3c3-s47 자료, codex 64cf 숫자, V-A 데이터(V-A 런은 아직 없음).

## 0. 판정: PASS (푸시 성공, 동결 성공, 선언 조건 모두 참)

| 조건 (보충 34 §4.1·§4.2) | 결과 | 근거 [실행] |
|---|---|---|
| 푸시 전: VerifyPromote `pass = true`, 검증 head = K9-2-7 | 참 | `VERIFY_PROMOTE_VA.md` 끝 줄 `pass = true`, 검증 head `c20aff1d…` = GWT8 HEAD |
| 푸시 전: `b9734abe..HEAD` = 8개, 순서 K9-2-7 … K9-2-0, 작성자·커미터 Ming2you, 끝 줄 `Co-Authored-By` | 참 | `c20aff1d`, `11d99c2a`, `e27ceac8`, `bfd609c0`, `b887f99f`, `2d5d95f0`, `7ed49cdf`, `1868b37c`. 8개 모두 `Ming2you <alsrjsrb1915@snu.ac.kr>`, 끝 줄 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` |
| 푸시 전: 두 새 커밋의 바뀐 경로 blob = 작업 바이트 | 참 | CFG ls-tree `b6ccd50d…` = 작업 `hash-object --no-filters`(sha256 `c8e3ee2c…1866`), `gb7_allowed.py` `1ca72d81…` = 작업(sha256 `61c70c22…f319`). 둘 다 `i/lf w/lf -text` |
| 푸시 전: K8 브랜치 `b9734abe…`, `status --porcelain` 0줄 | 참 | 로컬·원격 모두 `b9734abe…`, 0줄, stash 0 |
| 푸시 (새 원격 가지, 강제 없음) | 참 | `* [new branch] claude/k92-b1-20261016 -> claude/k92-b1-20261016`, exit 0 |
| `ls-remote` = K9-2-7 40자리 | 참 | `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d refs/heads/claude/k92-b1-20261016` |
| 푸시 뒤 K8 원격 가지 그대로 | 참 | `b9734abe1c83f95c9cec5fca5e42b7b18cd45991` |
| 동결 1. `FREEZE_OK … head=<K9-2-7> status_entries=0` 1줄, `FREEZE_DONE` | 참 | 각 1줄. `sha256=011f5be2… files=10569 bytes=2145948776` |
| 동결 2. `FREEZE_VERIFIED … sha256=<새 sha> … head=<K9-2-7>` 1줄 | 참 | 1줄 |
| 동결 3. `LAUNCH_PLAN_DETAIL … network_sha=3de889f0 detectors=294 controller=no-control sim_period=9000 seed=31` 1줄, plan 튜닝 sha, `warnings []`, `expected_env` 정책 | 참 | 1줄. plan `tuning.sha256` = `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`, `warnings []`, `RW_DECISION_ERROR_POLICY` = `hold_previous_on_exception` |
| 동결 4. `NETWORK_COPY_OK … sha256=3de889f0… sig=42`, `NETWORK_OK … sig=42` | 참 | 각 1줄. 사전점검 폴더 `network\`의 `.sig` 42개 |
| 동결 5. `PREFLIGHT PROVENANCE_OK … freeze=<새 sha>` 1줄; provenance 정책·튜닝·망 | 참 | 1줄. `env.RW_DECISION_ERROR_POLICY` = hold, `files.tuning.sha256` = `c8e3ee2c…`, `files.network.sha256` = `3de889f0…` |
| 동결 6. WD 줄 `RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)` 정확히 1개 | 참 | 1줄(`RW_DECISION_ERROR_POLICY`가 든 줄 전체도 1줄) |
| 동결 7. `PREFLIGHT_ONLY done; no VISSIM started`, `EXIT sdmpc31_v3c3_k92pre_s31 code=0` | 참 | 각 1줄(`EXIT` 줄 전체 1줄) |
| 동결 8. 이름 `sdmpc31_<K9-2-7 8자리>_<12자리 시각>`, `git.head` = 푸시 head, 브랜치, `status_entries 0` | 참 | `sdmpc31_c20aff1d_202610230833`, `c20aff1d…`, `claude/k92-b1-20261016`, 0. 로컬 `origin/claude/k92-b1-20261016` = `c20aff1d…` |
| 동결 9. 튜닝 sha: FRZ 파일 = FREEZE 표 = plan = provenance = GWT8 = `c8e3ee2c…1866`(blob `b6ccd50d…`); FRZ `gb7_allowed.py` = K9-2-7 blob 바이트 | 참 | 다섯 곳 모두 `c8e3ee2c…`, FRZ blob `b6ccd50d…`, 278,607 B. FRZ `gb7_allowed.py` blob `1ca72d81…` = K9-2-7 ls-tree, sha256 `61c70c22…` = 표 |
| 동결 10. FRZ_K92 대 FRZ_K8b `files` 바뀜·더함·없음 = `git diff --name-status b9734abe <K9-2-7>` M·A·D; A 21, M 12, D 0, 합 33; 33경로 FRZ blob = ls-tree blob | 참 | 바뀜 12 = M 12, 더함 21 = A 21, 없음 0 = D 0, 합 33. 33행 모두 FRZ `hash-object --no-filters` = ls-tree blob, FRZ sha256 = 표. 그 밖 10,536파일은 FRZ_K8b 표와 sha가 같음(줄 끝 포함) |
| 동결 11. `frozen/` 변화 = 새 폴더 + robocopy 로그뿐; FRZ_K8b `FREEZE.json` 그대로; FRZ_K92 안 캐시 0 | 참 | 34 → 36항목, 더함 2개, 없어짐 0, 임시 `.gitstate_*` 0. FRZ_K8b `6143d3eb…` 그대로. `__pycache__`·`*.pyc`·`__tangentcache__`·`.pytest_cache` 0 |
| 동결 12. 로그에 error·exception·fail·refuse·warning 낱말 0(정책 두 줄 제외) | 참 | 0줄 |

판정 도구: `VA/freeze/check_freeze_k92.py` sha256 `c79a530c798f4d443567f85c2ae09ea3adc8ae3408d467f1cf4eb26bdc9bbf98`(15,408 B). 동결 실행 **전에** LOG(08:32:48)와 `VA/freeze/freeze_pins.sha256`에 고정했습니다. K8b `check_freeze_k8r.py` 꼴이고 읽기 전용입니다. 키마다 §4.2 조건 번호(c1–c12) 또는 덧붙임(x)을 붙였고, `ALL_OK`는 모든 키가 참일 때만 나옵니다. 1회 실행(08:38:43–08:38:51) 결과: **CHECKS 62/62, 끝 줄 `ALL_OK`**, exit 0, 오류 출력 0 B. 결과 `VA/freeze/check_freeze_k92.json`(sha256 `6044019e…85e2`) [실행].

### 결과 값 (다음 단계 기대값)

- **푸시 head = `c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`** (K9-2-7). 원격 `https://github.com/Ming2you/VISSIM.git`, 가지 `claude/k92-b1-20261016`(새 가지). K8 가지 `b9734abe…`는 그대로.
- **FRZ_K92 = `D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833`**
  - `FREEZE.json` sha256 **`011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`** (1,670,995 B)
  - `tree_sha256` `9704503c8e0bb217a1564edfb27b0fc93284a2d2be1882ae87f37acb8429d857`
  - 10,569파일, 2,145,948,776 B. 만든 시각 `2026-10-23T08:38:01+09:00`.
  - `plan_subtree_files`: evaluation/ 2,798, scripts/ 422, src/ 0, plant/ 30, diagnostics/sdmpc_n31_20260924/ 302(FRZ_K8b 281 대비 +21 = 새 파일 21개).
- **튜닝 sha256 = `c8e3ee2c99b66c255b2279f0aa18eaafc18d4c7689e59e260109fac3b7d71866`** (blob `b6ccd50d96321e293f6ad9cf020e53ce1a8fbf5c`, 278,607 B). 보충 34 §4.2-3·9 기대값과 같음.
- 망 `3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e`, 검지 294행(`obs150_detectors_v2.csv` `108debbb…`), `.sig` 42개.
- 사전점검 폴더 `D:\VISSIM_runs\20261023_sdmpc31_k92\_preflight\sdmpc31_v3c3_k92pre_s31_20261023_083822`. plan sha256 `f29f095f73333ccd5c48dc903bfe551d37669e1a28ff89b203c910ab90d8524e`. provenance run_id `f8316d44c4514dcc920b70e5eb3dd8de`, sha256 `6b16cbb4…f0f6`.

## 1. 알릴 것 (공개)

1. **푸시 명령의 `-u`**. 보충 34 §4.1은 `git push origin claude/k92-b1-20261016`로 적었습니다(`:177`). 과제 글은 `git push -u origin …`였습니다. J1 선례(`SP/j1/FREEZE_PUSH.md:53`)와 과제 글을 따라 `-u`를 붙였습니다. 차이는 로컬 `.git/config`에 상류(upstream) 추적을 적는 것뿐입니다. 원격 결과와 선언 조건(새 가지, 강제 없음, 원격 head = K9-2-7)은 같습니다 [실행]. 상류 = `origin/claude/k92-b1-20261016`.
2. **판정 도구의 덧붙임 검사**. 선언 조건 1–12 말고도 K8b 꼴 덧붙임 검사(x)를 넣었습니다: plan의 freeze sha·head·root·검지·이름·제어기·시드·기간, `LAUNCH_PLAN_DETAIL` sha = plan 파일 sha, `RUN_DIR` = plan 폴더, provenance `workspace_root`, 튜닝 크기, `ROBOCOPY exit=1`, `OBS150 rows=294`, `no_global_kill=True`, `WATCHDOG_ARGS`의 `-NoGlobalKill … -PreflightOnly`, `LAUNCH … preflight_only=True`, 폴더 launch 로그 = 캡처 출력, RVA 안에는 `_preflight\<이 사전점검>` 하나뿐(런 이름 차지 안 함). 모두 참입니다. 덧붙임은 PASS를 더 어렵게만 합니다.
3. **판정 도구 고정 전에 한 일**. `ast.parse` 문법 확인 1회(실행 아님). 정규식 모양을 K8b 캡처 출력(`SP/j1/fix/freeze/k8r_freeze_preflight.out`)에 대 본 버림 스크립트 `VA/freeze/_regex_try_k8b.py`(`f58ec14c…`, 판정 아님) 1회. 이 동결의 자료는 고정 전에 없었습니다(동결은 고정 뒤 08:33:04 발사).
4. **판정 뒤 덧붙임 대조(판정 아님)**. `VA/freeze/_linecmp_k8b.py`로 이번 캡처 출력과 K8b 캡처 출력을 비교했습니다. 시각·경로·hex·이름·가지·개수를 지운 뒤 30줄 대 30줄이 모두 같습니다 [실행]. 즉 K8b 사전점검과 줄 모양이 같고, 새 줄이나 빠진 줄이 없습니다.
5. **동결 시간**. `FREEZE_DONE wall_sec=295.2`로 K8b(177.9)보다 깁니다. robocopy는 08:33:05–08:33:11(6초)에 끝났고, 나머지는 동결 도구가 FRZ와 GWT8을 둘 다 다시 해시한 시간입니다 [읽음 robocopy 로그 끝 "종료됨 … 오전 8:33:11"]. 더 걸린 까닭은 디스크·캐시 상태로 봅니다 [추론]. 판정 조건이 아닙니다.
6. **`FREEZE_TOOL` 줄 시각**. 동결 도구 줄이 모두 08:38:01로 찍혔습니다. 도구가 끝날 때 한꺼번에 내보내기 때문입니다. K8b도 같았습니다 [읽음 `k8r_freeze_preflight.out`].
7. **provenance의 `workspace_git_commit`이 빈 문자열**입니다. FRZ는 git 트리가 아니라서입니다. 지금까지 사전점검 모두 같습니다(`SP/j1/fix/FREEZE_PUSH_K8b.md:64`). head는 plan `freeze.head`와 `FREEZE.json git.head`로 이어집니다 [실행].
8. **FRZ_K92 안 팔 파일**. `config_n31_v2_k92b1.json`(A 경로, K9-2-3이 더함)과 CFG가 같은 바이트(`c8e3ee2c…`)입니다. 승격(K9-2-6)이 팔 바이트를 CFG로 복사했기 때문이고 예상한 일입니다 [실행 33행 표].
9. **스크립트·감시 러너 sha는 K8b와 같습니다**. provenance `files.main_vbs_runner` `bffb59f8…`, `files.watchdog_wrapper` `83c36301…`(= `FREEZE_PUSH_K8b.md:116-117` 값). `b9734abe..c20aff1d`에서 `scripts/`는 바뀌지 않았습니다 [실행 git diff]. 런타임에서 바뀐 것은 `evaluation/controllers/runtime_setup.py`(`70cca680`), `signal_head_observation.py`(`a6b5931e`), CFG입니다(K9-2-1·2·6).

## 2. 시작 전 확인 [실행 08:28]

- 재개 점검: LOG에 PushFreeze 줄 없음, `VA/freeze` 없음, `VA/FREEZE_PUSH.md` 없음, 원격 `claude/k92*` 0개, 상류 없음, `frozen/` 34항목에 K9-2 동결 없음(가장 늦은 것 FRZ_K8b), RVA 없음. 앞 시도 흔적 없음 → 처음부터.
- GWT8 HEAD `c20aff1d…`, 가지 `claude/k92-b1-20261016`, `status --porcelain=v1 --untracked-files=all` 0줄, stash 0.
- 도구 sha256(보충 34 §0 값과 같음): `run_sdmpc_n31.ps1` `600423f6…`, `freeze_worktree.ps1` `d5f3c024…`, `prepare_sdmpc31_network.py` `a4e506c3…`.
- 사용자·기계 환경 변수에 `RW_*`·`K8_*`·`K92_*` 없음(`RW_PYTHON_EXE` 하나만, 러너가 덮어씀).
- python·VISSIM·cscript 프로세스 0. 드라이브 여유 시작 C: 39.5 GB, D: 368.9 GB; 끝 C: 39.5 GB, D: 366.9 GB(둘 다 8 GB 위).

## 3. 푸시 [실행]

- 08:28:56 GWT8에서 `git push -u origin claude/k92-b1-20261016`. exit 0 (08:29:00).
  - 출력: `* [new branch]        claude/k92-b1-20261016 -> claude/k92-b1-20261016`, `branch 'claude/k92-b1-20261016' set up to track 'origin/claude/k92-b1-20261016'.`
- `git ls-remote origin refs/heads/claude/k92-b1-20261016` = **`c20aff1d7bf0c432cb4f20e2922bd406d857aa5d`** = HEAD = `origin/claude/k92-b1-20261016`. 동결 뒤(08:39) 다시 봐도 같음.
- `git ls-remote origin refs/heads/claude/k8-sc1001eb-defects-20261004` = `b9734abe…`(그대로).
- 푸시 뒤 GWT8 status 0줄. 순서는 선언대로 푸시(08:29) → 동결(08:33)입니다. D-K9-68(가지 푸시는 동결 준비 커밋 뒤, 폐루프 발사 전)과 맞습니다.

## 4. 동결 + 사전점검 [실행]

- **명령** (보충 34 §4.2 `:184` 글자 그대로, cwd = GWT8):
  ```
  cmd.exe /c set "PYTHONHASHSEED=0" && set "PYTHONDONTWRITEBYTECODE=1" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_k92pre_s31 -SimPeriod 9000 -Seed 31 -Controller no-control -RunsRoot D:\VISSIM_runs\20261023_sdmpc31_k92 > …\k92\va\freeze\k92_freeze_preflight.out 2>&1
  ```
- **띄운 방식**: 08:33:04 `Invoke-CimMethod -ClassName Win32_Process -MethodName Create`, ReturnValue 0, cmd PID 27584(내가 띄움), 우선순위 BelowNormal(16384), cwd `D:\VISSIM-merge\sim3-n31-k8`, 그때 VISSIM 0대. 발사 줄 `VA/freeze/wmi_freeze_launch.txt`. 08:38:28 끝(PID 사라짐). 짧은 확인(15초·10초 간격)으로 기다렸습니다.
- 러너는 감시 도구에 `-NoGlobalKill -MaxAttempts 1 -PreflightOnly`를 넘겼습니다(`WATCHDOG_ARGS` 줄, `OBS150 kill_policy=pid_only no_global_kill=True max_attempts=1`).
- **동결 로그** (`FREEZE_TOOL` 줄)
  - `FREEZE_START source=D:\VISSIM-merge\sim3-n31-k8 target=D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833 head=c20aff1d…`
  - `GIT_STATE head=c20aff1d… branch=claude/k92-b1-20261016 entries=0`
  - `ROBOCOPY exit=1`(복사 성공 코드). 요약: 파일 10,570 중 10,569 복사, 1개(56 B, 작업 트리 `.git` 연결 파일) 건너뜀, 실패 0. 디렉터리 978 중 5 건너뜀(무시된 캐시).
  - `FREEZE_OK path=…\FREEZE.json sha256=011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476 files=10569 bytes=2145948776 head=c20aff1d7bf0c432cb4f20e2922bd406d857aa5d status_entries=0`
  - `FREEZE_DONE wall_sec=295.2`, `FRZ=D:\VISSIM-merge\frozen\sdmpc31_c20aff1d_202610230833`
- **사전점검 로그**
  - 08:38:22 `FREEZE_VERIFIED … sha256=011f5be2… files=10569 head=c20aff1d…`
  - `LAUNCH_PLAN_OK plan=D:\VISSIM_runs\20261023_sdmpc31_k92\_preflight\sdmpc31_v3c3_k92pre_s31_20261023_083822\launch_plan.json`
  - `LAUNCH_PLAN_DETAIL sha256=f29f095f… root=<FRZ_K92> manifest=diagnostics/sdmpc_n31_20260924/plant_n31_v2.json network_sha=3de889f0 detectors=294 controller=no-control sim_period=9000 seed=31 gt=-`
  - `NETWORK_COPY_OK … sha256=3de889f0… sig=42 verify_only=0`, `NETWORK_OK … sig=42`
  - WD 줄: `RW_DECISION_FAIL_FAST=1`, **`RW_DECISION_ERROR_POLICY=hold_previous_on_exception (runtime.decision_error_policy)`**, `RW_MAINLINE_SG_ONLY=1`, `RW_QUEUE_COUNTER=1`, `RW_QUEUE_WINDOW=1` → OBS150이 0으로 덮음, `OBS150 cadence=decision150 … rows=294 … freeze=<FRZ_K92>\FREEZE.json`
  - `PROVENANCE_OK … run_id=f8316d44c4514dcc920b70e5eb3dd8de freeze=011f5be2…`
  - `PREFLIGHT_ONLY done; no VISSIM started`
  - 08:38:28 `EXIT sdmpc31_v3c3_k92pre_s31 code=0`
- 사전점검 폴더의 `launch_sdmpc31_v3c3_k92pre_s31.log`와 캡처 출력은 바이트가 같습니다(둘 다 sha256 `7ce83fd0…891e`, 30줄).
- **plan 내용**: 제어기·예열 no-control/no-control, 시드 31, 9000 s, control_start 900, interval 150, stall 2400, startup_stall 300. runner_config `lane_native_b110.vbs` `37c5021f…`, manifest `plant_n31_v2.json` `b119d6d9…`(mode v2), 망 원본 `baseline_s31_v3c3nc.inpx` `3de889f0…`. plan의 freeze = `011f5be2…`, head `c20aff1d…`, tree `9704503c…`.

## 5. 동결 차이 대조 (FRZ_K92 대 FRZ_K8b) [실행]

| 종류 | 경로 | FRZ_K92 sha256 / K9-2-7 blob (앞 8자리) |
|---|---|---|
| M | `diagnostics/sdmpc_n31_20260924/config_n31_v2.json` (CFG) | `c8e3ee2c` / `b6ccd50d` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/gb7_allowed.py` | `61c70c22` / `1ca72d81` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/README.md` | `0e146493` / `190f63d0` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_arms.py` | `578a8707` / `ee5ea52b` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_cap_child.py` | `10a77972` / `11c6aef2` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_capture.py` | `2b35d10e` / `8f9a65c6` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_jobs.py` | `53c5c0fc` / `567b940b` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/sa_worker.py` | `beca80c0` / `57859067` |
| M | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_sa_harness.py` | `eb581b04` / `86ce7e13` |
| M | `diagnostics/sdmpc_n31_20260924/make_config_n31.py` | `b707869a` / `26b6252d` |
| M | `evaluation/controllers/runtime_setup.py` | `70cca680` / `bcf7a777` |
| M | `evaluation/controllers/signal_head_observation.py` | `a6b5931e` / `37076a29` |
| A | `diagnostics/sdmpc_n31_20260924/config_n31_v2_k92b1.json` (CFG-B1) | `c8e3ee2c` / `b6ccd50d` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_a27.py` | `d4ab3f3d` / `01bff8a8` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_a29.py` | `cb816eab` / `1e345e86` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_cfgsnap/sitecustomize.py` | `79827465` / `50af3317` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_common.py` | `cb2a0335` / `bd40130a` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_compare.py` | `3e2da987` / `2b2b5523` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_gates.py` | `fb79ed57` / `79f0790d` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_record.py` | `1d1dfa36` / `aebc6f0e` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_replay.py` | `822dd78f` / `cd706dc4` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/k92_vissim_ref.py` | `f3fcc574` / `1f351efd` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_a27.py` | `0e39d5f8` / `b65acea0` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_a29.py` | `94a2a69b` / `b1b4605f` |
| A | `diagnostics/sdmpc_n31_20260924/k8_gates/sa/tests/test_k92_harness.py` | `752aada0` / `1899b60c` |
| A | `diagnostics/sdmpc_n31_20260924/k92/README.md` | `b190759a` / `7a733537` |
| A | `diagnostics/sdmpc_n31_20260924/k92/WORKLOG_20261016.md` | `d58ce984` / `c7cd52b9` |
| A | `diagnostics/sdmpc_n31_20260924/k92/build_k92_evidence.py` | `0a74d8e9` / `3c17712b` |
| A | `diagnostics/sdmpc_n31_20260924/k92/head_floor_seed_v3c3_robs_20261016.json` | `b9fa1d01` / `6ed42f16` |
| A | `diagnostics/sdmpc_n31_20260924/k92/inputs/u4_row_173_p3_v3b.json` | `435bb673` / `75cd34b6` |
| A | `diagnostics/sdmpc_n31_20260924/k92/sc109w_through_saturation_v3b_u4_20261016.json` | `b4b7294d` / `0399c369` |
| A | `diagnostics/sdmpc_n31_20260924/tests/test_k92_hb.py` | `b0b16c5b` / `9dca3de5` |
| A | `diagnostics/sdmpc_n31_20260924/tests/test_k92_w.py` | `ae31896b` / `5f81a4e1` |

- 바뀜·더함 집합 = git diff M·A 집합(정확히 같음). 없어진 경로 0 = D 0. 그 밖 10,536개 파일은 FRZ_K8b 표의 sha256과 같습니다(줄 끝 변화 없음).
- 위 33개 FRZ 파일의 `git hash-object --no-filters` = `git ls-tree c20aff1d` blob. 즉 FRZ_K92 바이트 = 푸시한 커밋 바이트. 증거 두 파일(`b4b7294d…`, `b9fa1d01…`)은 보충 34 §0 `:61` 값과 같습니다.
- 전체 64자리는 `VA/freeze/check_freeze_k92.json` `c10_frz_bytes_eq_commit_33`.

## 6. 위생 [실행]

- GWT8: HEAD `c20aff1d…`, status 0줄(푸시 뒤, 동결 뒤 모두). 이 단계는 커밋하지 않았습니다. K8 가지 로컬·원격 `b9734abe…` 그대로.
- `D:\VISSIM-merge\frozen\`: 34 → 36항목. 새것은 `sdmpc31_c20aff1d_202610230833\`와 `robocopy_sdmpc31_c20aff1d_202610230833.log` 둘뿐. FRZ_K8b와 다른 동결본은 건드리지 않았습니다(`FREEZE.json` `6143d3eb…` 그대로).
- RVA: 새로 생긴 것은 `_preflight\sdmpc31_v3c3_k92pre_s31_20261023_083822` 하나. V-A 런 이름 폴더 없음(차지하지 않음).
- 프로세스: 내가 띄운 cmd PID 27584(과 그 자식 powershell 7260·python 15420)은 스스로 끝났습니다. 끝난 뒤 VISSIM·cscript·python 0. VISSIM은 한 번도 뜨지 않았습니다(`-PreflightOnly`). 내가 띄우지 않은 프로세스는 건드리지 않았습니다.
- 확인 도구 python 실행: 판정 도구 1회(BelowNormal, `-B`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`). 그 밖은 모두 몇 초짜리 읽기(`-B`, `PYTHONDONTWRITEBYTECODE=1`): 동결 전 K8b 산출물 구조 보기 1회, 정규식 모양 시험(Git Bash가 역슬래시를 줄여 두 번 정규식 오류로 멈춘 뒤 파일판 `_regex_try_k8b.py` 1회), `ast.parse` 1회; 동결 뒤 판정 결과 요약 읽기 1회, plan·provenance 값 읽기 1회, `_linecmp_k8b.py` 1회. 시험(test) 실행 0.

## 7. 파일

`VA/freeze/`
- `push.out.txt`(`8205995e…`), `push_check.txt`(`16e74649…`)
- `k92_freeze_preflight.out`(캡처 출력, `7ce83fd0…`), `launch_sdmpc31_v3c3_k92pre_s31.log`(사전점검 폴더 로그 사본, 같은 바이트)
- `launch_plan_k92pre_s31.json`(`f29f095f…`), `run_provenance_sdmpc31_v3c3_k92pre_s31.json`(`6b16cbb4…`)
- `FREEZE_K92.json`(FRZ_K92 `FREEZE.json` 사본, `011f5be2…`)
- `wmi_freeze_launch.txt`(`c91f2a7c…`), `frozen_top_before.txt`(`81c9a046…`), `frozen_top_after.txt`(`3446604a…`)
- `check_freeze_k92.py`(`c79a530c…`), `freeze_pins.sha256`, `check_freeze_k92.json`(`6044019e…`), `check_freeze_k92.py.stdout.txt`(`3f6e588f…`), `check_freeze_k92.py.stderr.txt`(0 B)
- 버림 스크립트(판정 아님): `_regex_try_k8b.py`(`f58ec14c…`), `_linecmp_k8b.py`

REPVA 사본: `D:/VISSIM_runs/20261001_v3c3/reports/k8/k92_va/freeze/` — 이 문서(`FREEZE_PUSH.md`, 같은 바이트)와 위 파일들, `SHA256SUMS_FREEZE.txt`.

## 8. 다음 (보충 34 §5부터)

1. 오프라인 관문(§5.1 순서, Root = FRZ_K92): 기대값 head `c20aff1d…`, 튜닝 `c8e3ee2c…1866`, 망 `3de889f0…`, freeze `011f5be253fd31a5fb8342859b2b571375e49b4bbbbb42ea8f3ca93657b68476`. GB-7′·해시 A/B는 A(목록 sha `a8148f38…7af1`) ∪ E_K92(판정 함수 `VA/gates/gb7_k92decl.py` `d15e9cc0…fb11`)로 판정.
2. 관문 독립 검증 뒤 발사(§6): v3c3-s31·s41·s43 9,000 s, WMI, cwd = FRZ_K92, `-NoGlobalKill`, VISSIM PC 전체 4대 이하.
