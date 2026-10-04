# K7 푸시 · 동결 · 사전점검 · 발사 줄 (GB-4)

- 작성 2026-10-01 18:4x KST. 대상 K7 = **`6c4c740009f7ad9c6c0c275f8715839614ec6838`**(W `D:/VISSIM-merge/sim3-n31-v3c3`, 브랜치 `claude/repin-v3c3-20261001`).
- 기준 문서
  - 사전 선언 `K7_GB_J1_PREDECLARATION.md`: sha256 `fad31d70…`, sidecar와 같음
  - 수정 선언 `K7_AMENDMENT_1.md`: sha256 `1b1d3955…`, sidecar와 같음
  - 위 두 sha는 이 단계 시작 때 다시 계산했습니다 [실행].
- 이 단계에서 한 일: 푸시, FRZ_K7 동결, R-obs3·J1 ×3 사전점검, 발사 줄 작성.
- **하지 않은 일**: VISSIM 시작·종료, 발사, 커밋, 기존 `frozen/*` 수정, 다른 작업 트리 쓰기, 금지 시험, s37/59/61/67 결과 열람.
  - s37 NC는 `run.json`의 `completed`·`exit_code` 두 필드만 읽었습니다.
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단. `PREDECL:<줄>`은 사전 선언의 줄 번호입니다.
- 증거 폴더: `D:/VISSIM_runs/20261001_v3c3/reports/k7/freeze/`

## 0. 판정: GB-4 통과

GB-4 통과 조건(`PREDECL:234-246`)을 하나씩 확인했습니다.

| 조건 | 결과 | 근거 |
|---|---|---|
| O 전부 통과 → 푸시 | **통과** | `K7_REGATE.md` all_pass = true(수정 선언 1 기준). 원격 head = `6c4c740…` (§2) |
| `FREEZE_OK … head=<K7>` | 통과 | `FREEZE_OK … sha256=cacdd3b0… files=10332 … head=6c4c7400… status_entries=0` |
| `FREEZE_VERIFIED … head=<K7>` | 통과 | 4회 모두 같음(R-obs, J1 s31/s41/s43) |
| `LAUNCH_PLAN_DETAIL … network_sha=3de889f0… detectors=294 controller=no-control` | 통과 | plan sha `df00c5c1…` |
| `NETCOPY … sha256=3de889f0… sig=42` | 통과 | `NETWORK_COPY_OK`, 이어서 `NETWORK_OK` |
| `PREFLIGHT PROVENANCE_OK` | 통과 | run_id `7c8463e9…`, freeze `cacdd3b0…` |
| `EXIT … code=0` | 통과 | `PS_EXIT=0` |
| 가족 검사(`launch_plan.py:136-140`)가 거부하지 않음 | 통과 | `LAUNCH_PLAN_OK`, `warnings []` |
| FRZ_K7 `FREEZE.json` `git.head` = `origin/claude/repin-v3c3-20261001` | 통과 | 둘 다 `6c4c740…`, branch `claude/repin-v3c3-20261001`, status 0 |
| (과제 지시) FRZ 튜닝 sha = W | 통과 | 핵심 8파일이 FRZ = W 작업본 = HEAD filtered blob = FREEZE 표로 일치. 전체 표 10,332파일에서 누락·초과·불일치 0/0/0 (§4) |
| (과제 지시) J1 ×3 사전점검 | 통과 | `FREEZE_VERIFIED`, `LAUNCH_PLAN_DETAIL … network_sha=3de889f0… controller=wu-link`, `NETCOPY … sig=42`, `PROVENANCE_OK`, `EXIT code=0` (§5) |

- **FRZ_K7** = `D:\VISSIM-merge\frozen\sdmpc31_6c4c7400_202610011831`
  - `FREEZE.json` sha256 `cacdd3b0a8bdc15943574a6ef65afb6741287ae8cc0c5b0b041167483ec1d385`
  - tree_sha256 `2934dda7958f405b76402e4f18d1948dfdc8aa0740701f326b4df54265e137cf`
  - 10,332파일, 2,138,398,718 B
- 발사 줄: `D:/VISSIM_runs/20261001_v3c3/launch_lines_k7.txt` (sha256 `258ad77f…`). **발사하지 않았습니다.**

## 1. 시작 전 확인 [실행·읽음]

- **관문**
  - `K7_REGATE.md`(18:28)의 판정표는 O-0…O-8 모두 통과이고, all_pass = true입니다 [읽음].
  - 그 문서의 단서 두 개는 아래처럼 처리했습니다.
- **단서 1: O-5 결정 주체**
  - 이 단계의 과제 지시는 O-5 조건 4 수정을 "Offline-gate failures and the USER DECISION (2026-10-01 17:3x)" 묶음 안에 둡니다. 푸시도 "user-approved"로 적혀 있습니다 [읽음, 과제 지시].
  - 이 기록을 결정 주체의 기록으로 남깁니다. 다만 이 단계는 사용자 본인의 발화를 직접 확인할 수 없습니다. 이 단서는 공개합니다.
- **단서 2: s53 사후 확인(O-0, `PREDECL:65`)**
  - 메인 세션이 판정을 마쳤습니다. `reports/gb1_verdict.json`(17:39:19)에 s31/41/43/47/53/37 모두 pass, `"GB1": "PASS"`로 적혀 있습니다 [읽음].
  - `gb1_result_s37_sealed.json`은 판정어만 담은 봉인 형식입니다 [읽음].
- **NC 재실행**: s53, s37 모두 `run.json`이 `completed=True`, `exit_code=0`입니다(봉인 s37은 이 두 필드만 읽음) [실행].
- **좌석 상태**: VISSIM 프로세스는 18:30에 0개, 18:39에도 0개였습니다. 과제 지시가 말한 "NC 재실행이 18:00께까지 2석 점유"는 이미 끝났습니다 [실행].
- **트리**
  - W HEAD `6c4c740`, `status --porcelain --ignored` 0줄. GWT6 0줄, GWT7 0줄 [실행].
  - K7 커밋 7개(`8892c91…6c4c740`)는 모두 작성자·커미터가 `Ming2you <alsrjsrb1915@snu.ac.kr>`이고, `Co-Authored-By: Claude Opus 5.5` 트레일러가 있습니다 [실행].
- **발사 대상**
  - RM s31/s41/s37 폴더에 `run\`과 `launch.log`가 없고, `prepared\`는 있습니다 [실행].
  - `D:\VISSIM_runs\20261001_sdmpc31_v3c3`는 이 단계 전에는 없었습니다 [실행].
  - RM `rule_runtime.txt`가 가리키는 `C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`가 있습니다 [실행].
- **디스크**: D: 여유 870.1 GB [실행].

## 2. 푸시 [실행]

- 18:31:22에 W에서 `git push -u origin claude/repin-v3c3-20261001`을 돌렸고, exit 0입니다. 새 브랜치를 만들었습니다.
- `git ls-remote origin refs/heads/claude/repin-v3c3-20261001` = **`6c4c740009f7ad9c6c0c275f8715839614ec6838`**
- `origin/claude/repin-v3c3-20261001` = HEAD이고, upstream이 설정됐습니다. 푸시 뒤 W status는 0줄입니다.
- 순서는 GB-4대로입니다(`PREDECL:236-237`): 푸시(18:31:22) → 동결(18:31:47).

## 3. 동결 + R-obs3 사전점검 [실행] (`freeze/robs_freeze_preflight.out`)

- **명령**: W에서, 프로세스 우선순위 BelowNormal(자식에 상속), `PYTHONDONTWRITEBYTECODE=1`. 형식은 계획 §6.3 그대로입니다.
  ```
  powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 -Freeze -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_nc_s31 -SimPeriod 9000 -Seed 31 -Controller no-control -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3
  ```
- **도구 sha**
  - `run_sdmpc_n31.ps1` `600423f6…`
  - `freeze_worktree.ps1` `d5f3c024…`
  - `prepare_sdmpc31_network.py` `a4e506c3…`
- **동결 로그**
  - `GIT_STATE head=6c4c740… branch=claude/repin-v3c3-20261001 entries=0`
  - `ROBOCOPY exit=1`(복사 성공 코드)
  - `FREEZE_OK … files=10332 bytes=2138398718 head=6c4c740… status_entries=0`
  - `FREEZE_DONE wall_sec=158.8`
- **사전점검 로그**
  - 18:34:46 `FREEZE_VERIFIED … head=6c4c740…`
  - `LAUNCH_PLAN_DETAIL sha256=df00c5c1… root=<FRZ_K7> manifest=…/plant_n31_v2.json network_sha=3de889f0 detectors=294 controller=no-control sim_period=9000 seed=31 gt=-`
  - `NETWORK_COPY_OK … sha256=3de889f0257d998b… sig=42`
  - `NETWORK_OK`
  - watchdog `-PreflightOnly`(`OBS150 kill_policy=pid_only no_global_kill=True max_attempts=1`, `cadence=decision150 … rows=294`)
  - `PROVENANCE_OK … freeze=cacdd3b0…`
  - `PREFLIGHT_ONLY done; no VISSIM started`
  - `EXIT sdmpc31_v3c3_nc_s31 code=0`
- **plan 내용** [실행]
  - controller / warmup = no-control / no-control, seed 31, 9000 s, control_start 900, interval 150, stall 2400
  - 튜닝 `319d07aa…`, runner_config `lane_native_b110.vbs` `37c5021f…`
  - 망 원본 `diagnostics/sdmpc_n31_20260924/network/baseline_s31_v3c3nc.inpx` `3de889f0…`
  - `warnings []`
- **플랜이 차지한 폴더**: 사전점검 플랜은 `RunsRoot\_preflight\<Name>_<stamp>`만 차지합니다(`launch_plan.py:173-178`). 그래서 실제 런 폴더 `…\sdmpc31_v3c3_nc_s31`는 비어 있고, 발사할 수 있는 상태입니다 [실행 `ls`].

## 4. FRZ_K7 대 W [실행] (`freeze/frz_vs_w.py` → `frz_vs_w.json`, BELOW_NORMAL)

- `FRZ_VS_W OK`
  - FREEZE head = W HEAD = origin head = `6c4c740…`
  - FREEZE 표 10,332개를 W 작업본(동결 제외 규칙 적용)과 다시 해시했습니다. 누락 0, 초과 0, 불일치 0입니다.
- 핵심 파일마다 FRZ 사본, W 작업본, `git cat-file --filters HEAD:<f>`, FREEZE 표 값이 넷 다 같습니다. 값은 `K7_REGATE.md`의 기대값과 같습니다.

| 파일 | sha256 |
|---|---|
| `config_n31_v2.json` (배포 튜닝) | `319d07aa` |
| `config_n31_v2_urban_b1.json` | `4e85cfd6` |
| `config_n31_v2_urban_b1_u1u3.json` | `c60bde7c` |
| `plant_n31_v2.json` | `b119d6d9` |
| `reference_config_n31_v2.json` | `add58bc4` |
| `scenario/lane_native_b110.vbs` | `37c5021f` |
| `urban/unsignalized_turns_v3c3_20261001.json` | `43247697` |
| `scripts/run_real_world_stackelberg_controller.vbs` | `8c753c08` |

- FRZ_K7 안의 `__pycache__`/`*.pyc`/`__tangentcache__`는 사전점검 4회 뒤에도 0개입니다.

## 5. J1 사전점검 ×3 [실행] (`freeze/j1_preflight.out`)

- **조건**: FRZ_K7에서, `-Freeze` 없이(`PREDECL:392`), BelowNormal로 돌렸습니다. 발사 줄을 흉내 내려고 `PYTHONHASHSEED=0`을 설정했습니다(사전점검 결과에는 영향 없음 [추론]).
- **명령**: `run_sdmpc_n31.ps1 -PreflightOnly -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v3c3_j1_s<S> -SimPeriod 9000 -Seed <S> -Controller wu-link -RunsRoot D:\VISSIM_runs\20261001_sdmpc31_v3c3`

| 시드 | FREEZE_VERIFIED head | LAUNCH_PLAN_DETAIL | NETCOPY | PROVENANCE_OK run_id | EXIT |
|---|---|---|---|---|---|
| 31 | `6c4c740…` | plan `81cadff6…`, network_sha=3de889f0, detectors=294, controller=wu-link, seed=31 | `3de889f0…` sig=42 | `c954b18a…` | 0 |
| 41 | `6c4c740…` | plan `375cf94f…`, … controller=wu-link, seed=41 | `3de889f0…` sig=42 | `eb97b215…` | 0 |
| 43 | `6c4c740…` | plan `60938310…`, … controller=wu-link, seed=43 | `3de889f0…` sig=42 | `fde78b08…` | 0 |

- 세 plan 모두 같은 값입니다 [실행]
  - warmup no-control, control_start 900
  - 튜닝 `319d07aa`, freeze `cacdd3b0`/`6c4c7400`
  - `warnings []`
  - expected_env는 obs150 `decision150`, 검지기 `108debbb…` 294행입니다.
- 망은 세 시드 모두 s31 망 파일 `3de889f0`입니다. 시드는 러너가 COM `RandSeed`로 덮습니다(`PREDECL:417`; s41·s43에서의 동등성은 처음 시험한다는 단서는 `PREDECL:423`) [읽음].
- 사전점검 폴더만 생겼습니다. 실제 J1 런 폴더는 차지하지 않았습니다.
  - `_preflight\sdmpc31_v3c3_j1_s{31_20261001_183600, 41_20261001_183624, 43_20261001_183647}`

## 6. 트리 위생 [실행] (`freeze/o8_after_freeze.json`, regate `o8_snapshot.py` 사본; 기준 = `regate/o8_after.json` 18:25)

- **W**
  - HEAD `6c4c740`, `status --ignored` 0줄. 푸시 뒤, 동결 뒤, 사전점검 뒤 모두 0줄입니다.
  - W에서 돌린 것은 git 읽기·푸시와 동결 도구뿐입니다. 동결 도구는 `-B`이고, 출력은 W 밖에 씁니다.
- **GWT7**: `6c4c740`, 0줄, 캐시 0.
- **GWT6**: `54d821c`, 0줄.
- **다른 트리 5개**(`sim3-n31-v3c1`, `-urban-b2`, `-f10f11`, `-termcost`, `-hybrid`)와 GWT6: HEAD, status 줄 수, status sha, 파일 수, 바이트, 최신 mtime이 18:25 기록과 모두 같습니다.
- **`frozen/`**
  - 28 → 30항목. 새것은 `sdmpc31_6c4c7400_202610011831/`과 `robocopy_sdmpc31_6c4c7400_202610011831.log` 둘뿐입니다.
  - 기존 28항목은 변화 0입니다.
  - FRZ_K6 표 무결, 재해시 0/0/0, 캐시 0. FRZ_OLD 표 무결, 0/0/0, 캐시 119(전과 같음).
  - 동결 도구의 임시 `.gitstate_*.json`은 도구가 지웠습니다.
- 이 단계가 새로 만든 곳
  - `D:\VISSIM-merge\frozen\` 아래 위 두 항목
  - `D:\VISSIM_runs\20261001_sdmpc31_v3c3\_preflight\`(4폴더)
  - `reports/k7/freeze/`
  - `launch_lines_k7.txt`
  - 이 보고서

## 7. 발사 줄 (`D:/VISSIM_runs/20261001_v3c3/launch_lines_k7.txt`)

- 모두 `Invoke-CimMethod -ClassName Win32_Process -MethodName Create` 형식입니다. 세션과 분리해 띄웁니다(memory `vissim-launch-detached-from-session`).
- 문자열 대조 [실행]
  - RM 세 줄은 `launch_lines_rm.txt`의 해당 행과 문자열이 같습니다.
  - SDMPC 줄의 `-Tuning`/`-Name`/`-Seed`/`-Controller`/`-RunsRoot`는 §3·§5 사전점검 인자와 같습니다.

| 묶음 | 런 | 실행 위치(cwd) | 특이점 |
|---|---|---|---|
| 1a | R-obs3 `sdmpc31_v3c3_nc_s31` | FRZ_K7 | 계획 §6.3 형식. `PYTHONHASHSEED` 없음(v3c1 R-obs와 같음) |
| 1b–1d | RM s31, s41, s37(봉인) | `D:\VISSIM_runs\20261001_v3c3` | `fast_nc_run.ps1 … -AllowConcurrent` |
| 2a | J1 s31 | FRZ_K7 | `cmd.exe /c set "PYTHONHASHSEED=0" && powershell …`, 플래그 없음 |
| 2b | J1 s41 | FRZ_K7 | 같은 꼴 + `-AllowConcurrentDev` |
| 3a / 3b | J1 s43 | FRZ_K7 | 3a: J1 하나가 아직 돌 때 `-AllowConcurrentDev` / 3b: dev VISSIM 0일 때 플래그 없음 |

- **좌석 논리** [읽음 `run_sdmpc_n31.ps1:84-86`, `:145`, `:227-235`; `fast_nc_run.ps1:59`]
  - dev 런은 좌석을 두 번 검사합니다. 플랜 전에 한 번, VISSIM 시작 직전에 다시 한 번입니다.
    - 플래그 없음: 총 ≤ 3, dev = 0
    - `-AllowConcurrentDev`: 총 ≤ 2, dev ≤ 1
  - 재검사에서 거부되면 런 이름이 소모됩니다(`NOT_LAUNCHED.txt`).
  - RM(`-AllowConcurrent`)에는 자체 상한이 없습니다.
- **발사 순서**
  - **묶음 1**: R-obs를 먼저 띄웁니다(총 0, dev 0). 그 로그에 `START sdmpc31_v3c3_nc_s31`가 찍힌 뒤 RM 세 개를 띄웁니다. 총 4석이고, 지금 4석이 비어 있습니다.
  - **묶음 2**: 2a의 VISSIM 창 제목이 보인 뒤(dev 1) 2b를 띄웁니다. 2b를 먼저 띄우면 2a 재검사가 dev = 0을 요구하므로 2a가 거부됩니다 [추론, 코드 근거].
- **묶음 2의 전제**: 과제 지시는 "GB-6/GB-7 통과 뒤"라고 했습니다. 사전 선언 §3.2(`PREDECL:389`)와 §4 순서표는 **GB-4…GB-10 전부 통과 + R-obs3 S 통과**를 요구합니다. 더 엄격한 선언 쪽을 발사 줄 파일에 적었습니다.
- **발사 기록**: 파일 끝에 기록 도우미 줄을 두었습니다. 시각, ReturnValue, PID, VISSIM 수, cwd, 명령을 남깁니다(hybrid `wmi_launch_lines.txt` 형식).

## 8. 다음 (메인 세션)

1. **묶음 1 발사**: 지금 VISSIM 0개이므로 4석이 비어 있습니다. 각 발사 전에 VISSIM 수와 대상 폴더 부재를 다시 확인합니다.
2. **R-obs3 완료 뒤**: GB-5 → GB-6 → GB-7 → GB-8/9/10. 하나라도 실패하면 STOP입니다(`PREDECL:514-529`). GB-9의 도구는 FRZ_K7이고, Root는 GWT7(`6c4c740`, 0줄)입니다.
3. **GB-13**: 구속으로 올리려면 v3c3 RM 결과를 열기 **전에** v3c1 RM 대 v3c1 NC의 t_rw 전 바이트 동일성을 먼저 보여야 합니다. 봉인 s37 RM은 `run.json` 두 필드만 봅니다.
4. **J1**: 위 전제를 모두 통과한 뒤 묶음 2, 그다음 묶음 3을 띄웁니다. 사전점검은 이미 통과했고, 같은 FRZ_K7·같은 인자입니다.
5. **공개 단서**: O-5 통과는 수정 선언 §2.2에만 기댑니다. 그 결정 주체는 이 단계 과제 지시의 기록(§1)뿐입니다. 옛 조건 4로 판정하면 실패입니다(`K7_REGATE.md` §6).
