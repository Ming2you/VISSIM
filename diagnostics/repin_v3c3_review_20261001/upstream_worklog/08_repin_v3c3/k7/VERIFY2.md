# K7 독립 검증 2 (수정 선언 1 · 재관문 · 동결 · 푸시 · 발사 줄)

- 작성 2026-10-01 19:1x KST. 읽기 전용 검증입니다. 제 코드와 결과는 모두 `reports/k7/verify2/`에 있습니다(v1–v8 `.py` + `.json`).
- 대상: 원격 `origin/claude/repin-v3c3-20261001` = **`6c4c740009f7ad9c6c0c275f8715839614ec6838`**(`git ls-remote`로 직접 조회) = W HEAD = GWT7 HEAD.
- 입력: `K7_AMENDMENT_1.md`(sha256 `1b1d3955…`, sidecar와 같음), `K7_FIX.md`(`7780ecfa…`), `K7_REGATE.md`(`354a665e…`), `K7_FREEZE_PUSH.md`(`aac14aa4…`). 사전 선언 `fad31d70…`, 1차 관문 보고 `a8b1ab6d…`는 바뀌지 않았습니다 [실행 `v1_timeline.json`].
- 실행 조건: 모든 Python은 `-B`, `PYTHONDONTWRITEBYTECODE=1`, BELOW_NORMAL(0x4000)입니다. git은 `--no-optional-locks` 읽기만 썼습니다. 작업 트리에서는 아무것도 import하거나 실행하지 않았습니다. 생성기 재실행은 `git archive`로 스크래치에 꺼낸 사본에서 했고, 끝난 뒤 지웠습니다.
- 하지 않은 것: 커밋, 푸시, 동결, VISSIM 시작·종료(19:03에 VISSIM 0개 확인만), 금지 시험, s37/59/61/67 결과 열람, 다른 작업 트리 쓰기.
- 표기: **[실행]** 직접 돌려 확인 · **[읽음]** 파일·코드에서 확인 · **[추론]** 시험하지 않은 판단.

## 0. 판정 요약

| # | 점검 | 판정 | 근거 |
|---|---|---|---|
| 1 | 수정 선언이 수정·재실행보다 먼저 | **확인** | §1 시간표. 선언 17:47:17 → 첫 수정 파일 17:48:26 → 커밋 17:53/17:58 → GWT7 이동 18:05:46 → 재관문 첫 파일 18:06:03 |
| 2 | O-3 소속 = v3c1 23개 | **확인** | §2. (a)–(g) 독립 재판정 26/26 통과. 생성기를 git archive 사본에서 다시 돌려도 `43247697`. 거부 탐침 2/2 |
| 3 | O-5 수정 기준 값 | **확인** | §3. 원시 tangent JSON에서 다시 판정: 4상태 모두 항목 1–5 통과. 최대 상대 편차 2.34e-13. κ는 speed_scale에서 따로 유도해 같음(상대 2.6e-15) |
| 4 | FRZ_K7 내용 = 원격 head | **확인** | §4. 10,332 / 10,332. 원시 같음 5,671 + checkout 필터 뒤 같음 4,661, 불일치 0, 누락·초과 0 |
| 5 | 발사 줄 | **확인** (사소한 단서 1) | §5. 검사 77/77 통과. cwd, PYTHONHASHSEED, 이름, 로그, 좌석, RM = v3c1 형식 |
| 6 | K7 diff의 재핀 목록 충족 | **확인** | §6. 목록 52항목 중 저장소 안 항목은 K1–K6 또는 K7 diff가 모두 덮음. 살아 있는 v3c1 망 sha·경로 핀 0. 110 전용 가정 0 |

- **남은 단서** (§7): ① O-5 사후 변경의 결정 주체가 사용자 본인 발화로는 기록되지 않았습니다. ② 사전 선언의 단일 호출 연산 수(48/10)와 실측(47/9)이 다릅니다(d1 38은 같음). ③ 3a/3b가 같은 wmi 로그 파일을 씁니다.

## 1. 수정 선언이 먼저인가 [실행 `verify2/v1_timeline.py`, git reflog·커밋 시각]

| 시각 (KST) | 사건 | 출처 |
|---|---|---|
| 17:27:25 / 17:31:16 | 1차 관문 증거 끝 / `K7_OFFLINE_GATES.md`(O-9로 멈춤) | mtime |
| **17:47:17** | `K7_AMENDMENT_1.md` mtime. sidecar 기록은 17:47:26, "W HEAD 99dc641, status 0, no gate re-run started" | `K7_AMENDMENT_1.md.sha256` |
| 17:48:26 | `fix/` 첫 파일(`e_o3_generator.py`). pyc 증거 사본(17:04:51)은 원본 mtime을 유지한 복사본이라 예외 | mtime |
| 17:53:40 / 17:58:49 | 커밋 `91efffc`(O-3) / `6c4c740`(O-7). 작성자·커미터 Ming2you, 끝 줄 `Co-Authored-By` | `git log` |
| 18:05:46 | GWT7 `checkout 99dc641 → 6c4c740` | GWT7 HEAD reflog |
| 18:06:03 – 18:25:54 | `regate/` 파일 550개 전부 | mtime |
| 18:31:27 | 원격 추적 ref 생성 "update by push" | `refs/remotes/origin/...` reflog |
| 18:34:27 | FRZ_K7 `FREEZE.json` `created_at` | FREEZE.json |

- 선언 본문에는 수정 뒤에야 알 수 있는 값(`43247697`, `4e85cfd6`, `c60bde7c`, `91efffc`, `6c4c740`)이 하나도 없습니다 [실행]. 수정 전에 쓰였다는 기록과 맞습니다.
- 선언 §0(`K7_AMENDMENT_1.md:11`)은 두 변경이 결과를 본 뒤 조건을 약하게 하는 결정이라 O-9 보충 규칙(`PREDECL:228`) 밖이라고 공개합니다. 그 정당화는 결정 기록에만 기댑니다(§7 ①).

## 2. O-3: 소속 = v3c1 23개 [실행 `v2_o3_membership.py`, `v3_generator_check.py`]

- v3c1 표는 K6 `54d821c`의 blob `c2558392fed0…`이고, sha256 `95ea2732…`, 34,022 B입니다. 선언 §1.2와 같습니다.
- v3c3 표는 원격 head에서 sha256 **`43247697…`**입니다(`99dc641`에서는 `83326aca…`, 22개).

| 수정 기준 (`K7_AMENDMENT_1.md:55-66`) | 결과 |
|---|---|
| (a) `/movements` 이름 | v3c1 23개와 같음. 순서도 같음. `99dc641`은 정확히 `SC103_S_SC6_to_E` 하나가 빠진 22개였음 |
| (b) 23행의 `validation` 밖 | v3c1 행과 같음(키 순서 포함) |
| 행 `validation` = 검증표 `d8718b9d`의 커넥터 값 | 23/23 같음. v3c1 대비 바뀐 수치 리프 51개 |
| (c) `not_included_fzp_validation` | [(`SC107_N_SC1_to_W_SC1005`, [10610])]로 v3c1과 같음 |
| (d) 7개 키 | v3c1과 JSON 같음 |
| (e) 그 밖에 다른 키 | `generated`, `inputs`, `network`뿐 |
| (f) `membership_pin` | 새 키는 이것 하나이고 맨 끝. 23개. `source` = K6 commit·blob·sha256·경로와 같음. 알려진 초과는 1건: `SC103_S_SC6_to_E` [10096], v3c3 0.0544(n 5602) = 그 행 = 검증표, v3c1 0.0472(n 5611) = v3c1 행 |
| (g) 규칙 | 나머지 22행 모두 n ≥ 100, 비율 ≤ 0.05. `SC103_S_SC6_to_E`는 실제로 0.0544 > 0.05 |
| 생성기 상수 | `scripts/derive_unsignalized_turns.py:54` `MEMBERSHIP_PIN`의 이름 집합 = v3c1 23개(순서만 정렬). source 상수 = K6 객체 |
| (h) 재생성 | `git archive` 사본에서 `--check` exit 0, 다시 쓴 sha = `43247697`(커밋본과 같음) |
| (h) 거부 | 초과 선언을 비우면 → `:174` "missing ['SC103_S_SC6_to_E']". 미검증 회전을 핀에 넣으면 → "missing ['SC107_N_SC1_to_W_SC1005']". 둘 다 exit 1 |

- **하류**
  - 후보 config 두 벌의 `/urban/movements/unsignalized_evidence`는 경로와 sha256 = 새 표입니다.
  - 배포 `config_n31_v2.json`(`319d07aa`), `plant_n31_v2.json`(`b119d6d9`), `reference_config_n31_v2.json`(`add58bc4`)
    - `99dc641`과 바이트가 같습니다.
    - 세 파일 모두 `unsignalized_turns` / `unsignalized_evidence` 문자열이 0개입니다. 배포 경로는 이 표를 읽지 않습니다 [실행].

## 3. O-5: 수정된 조건 4 [실행 `v4_o5_judge.py`; 입력은 `regate/o5/out/tangent_{L2,KA,L1}.json`]

- 재관문 하네스(`o5_compare.py`)는 import하지 않고, 원시 출력에서 바로 판정했습니다.

| 상태 | 1 primal hex L2=KA=L1 (양 도로) | 2 FW_W 0열·Trace L2=KA·법칙 호출 0 | 3 사건 4종 L2=KA, n_L2=n_KA | 4 κ 비례 (리프 148) | 최대 상대 편차 | 5 0 아님·L2≠L1 |
|---|---|---|---|---|---|---|
| 900 | 통과 | 통과 | 통과 (n 27,809) | 위반 0 | 1.80e-14 | 144개 0 아님, 통과 |
| 3600 | 통과 | 통과 | 통과 | 위반 0 | 8.46e-15 | 통과 |
| 4800 | 통과 | 통과 | 통과 | 위반 0 | 5.55e-14 | 통과 |
| 6300 | 통과 | 통과 | 통과 | 위반 0 | **2.34e-13** | 통과 |

- **κ 독립 유도**
  - 설치된 L2 `speed_scale`(80/90/100 매듭 + (110, 1))의 3차 Lagrange 도함수에서 κ = 110·s′(110) = 1.1924542785990402를 얻었습니다.
  - 선언값 1.1924542785990433과 상대 2.6e-15 차이입니다.
  - 처음 쓴 식 1 + 110·s′(110)은 1만큼 틀렸고 고쳤습니다(L2 자유속도 = 110·s(c), KA = c) [실행, 스크립트에 남김].
- **항목 6 (보고만)**
  - ΔOps 편차는 +4/−12/−10/−20, ΔEntries 편차는 −133/−336/−267/−211입니다(n×38 = 1,056,742 기준).
  - 이 값은 재관문 보고 §6 표, 수정 선언 §2.1 표와 정확히 같습니다.
- **1차 관문과의 비교**
  - `gates/o5/out/tangent_*.json`과 `ad110`·`trace`·`law_calls` 값이 세 벌 모두 같습니다.
  - 재관문의 `max_rel_dev` 4개는 제 계산과 비트까지 같습니다.
- 옛 조건 4의 n×d1 등식(`PREDECL:159-163`)으로 판정하면 4상태 모두 실패합니다. 통과는 선언 §2.2(`K7_AMENDMENT_1.md:97-104`)에만 기댑니다.
- 선언 §2.2를 과제 지시와 맞춰 봤습니다 [읽음]
  - 과제 지시: primal 비트 동일, FW_W 동일, 사건 수 동일, κ 상대 1e-9, 연산 수 차이와 0 상쇄 설명은 기록만.
  - 선언 §2.2는 여기에 n_L2 = n_KA와 "0 아님·L2≠L1"을 구속으로 더 남겼습니다. 지시보다 약하지 않습니다.

## 4. FRZ_K7 = 원격 head [실행 `v5_frz_vs_remote.py`, 402 s]

- 기준
  - `ls-remote` head `6c4c740…`
  - FREEZE.json `git.head` 같음, branch 같음, `status_entries` 0
  - FREEZE.json sha256 `cacdd3b0…`(발사 줄 머리 주석과 같음)
- 방법
  - 원격 head 트리(`ls-tree -r`)의 blob을 `cat-file --batch`로 모두 꺼냈습니다.
  - 원시 바이트가 FRZ 파일과 다르면 `cat-file --filters <head>:<path>`(checkout 렌더링, `core.autocrlf=true`)로 다시 비교했습니다.
  - `--batch --filters`는 머리의 크기가 필터 전 값이라 스트림이 어긋났습니다. 그래서 이 방식으로 바꿨습니다.
- 결과
  - 트리 10,332(모두 100644 blob) = FRZ 파일 10,332(루트 FREEZE.json 제외)
  - 원시 같음 5,671, 필터 뒤 같음 4,661, **불일치 0**, 누락·초과 0
  - FREEZE 표 10,332개 = FRZ 바이트
  - FRZ 안 `__pycache__`/`*.pyc`/`__tangentcache__` 0
- 핵심 파일 sha(FRZ = 원격 = FREEZE 표)
  - config `319d07aa`, 후보 `4e85cfd6`/`c60bde7c`, plant `b119d6d9`, reference `add58bc4`
  - `lane_native_b110.vbs` `37c5021f`, 무신호 표 `43247697`, 러너 VBS `8c753c08`, 망 `3de889f0`
  - `derive_unsignalized_turns.py`는 FRZ가 CRLF 렌더링입니다(필터 뒤 같음, blob은 LF). `K7_FIX.md` §2.1 줄끝 기록과 맞습니다.

## 5. 발사 줄 `D:/VISSIM_runs/20261001_v3c3/launch_lines_k7.txt` (sha256 `258ad77f…`) [실행 `v8_launch_lines.py`, 검사 77/77]

| 항목 | 결과 |
|---|---|
| cwd | SDMPC 다섯 줄(1a `:43`, 2a `:66`, 2b `:69`, 3a `:78`, 3b `:81`) 모두 `D:\VISSIM-merge\frozen\sdmpc31_6c4c7400_202610011831`. 튜닝 상대 경로가 그 안에 있음. 발사기는 튜닝 위의 FREEZE.json으로 FRZ를 찾고 그리로 이동함(`run_sdmpc_n31.ps1:173`) |
| PYTHONHASHSEED | J1 네 줄은 `cmd.exe /c set "PYTHONHASHSEED=0" && powershell.exe …`로 시작함(hybrid 관행과 같은 머리). R-obs `:43`에는 없음(v3c1 R-obs와 같음) |
| 사전 선언 틀 | J1 네 줄이 `PREDECL:394` 틀에 `<S>`를 넣은 문자열과 정확히 같음. 2b·3a는 `-AllowConcurrentDev`가 `>` 앞에 붙음(`PREDECL:395`) |
| R-obs | v3c1 R-obs 발사 기록(`20260928_sdmpc31_v3c1/wmi_launch_lines.txt`)에서 이름과 RunsRoot만 바꾼 문자열과 같음. 이름 `sdmpc31_v3c3_nc_s31`(`PREDECL:37`), no-control, 9000 s, seed 31 |
| 이름·로그 | J1 = `sdmpc31_v3c3_j1_s{31,41,43}`, seed = 이름 끝. RunsRoot = `D:\VISSIM_runs\20261001_sdmpc31_v3c3`. 로그 = RunsRoot`\wmi_<Name>.log`. 실제 런 폴더 4개는 아직 없음(`_preflight\`만 있음). `-Freeze`·`-PreflightOnly` 없음 |
| 사전점검 대응 | `freeze/j1_preflight.out`의 `LAUNCH name=… seed=… controller=wu-link`와 `FREEZE_VERIFIED head=6c4c740…`, R-obs의 `robs_freeze_preflight.out:2,:12` 인자가 발사 줄과 같음 [읽음] |
| RM | 1b/1c/1d가 `launch_lines_rm.txt` 행과 같음. v3c1 `20260927_v3c1/launch_lines_rm.txt` 행에서 경로만 바꾼 것과도 같음. cwd `D:\VISSIM_runs\20261001_v3c3`. `run\`·`launch.log` 없음, `prepared\` 있음 |
| RM 러너 | `fast_nc_run.ps1` `269345da…`, `fast_nc_runner.vbs` `bf07acda…`가 v3c1·v3c3 RM 드라이런 영수증과 현재 파일에서 모두 같음. `rule_runtime.txt`(파이썬·`fast_fixed_profile.py`·900)는 v3c1과 v3c3 세 시드 모두 같은 내용 |
| 좌석 | `run_sdmpc_n31.ps1:84-86`(플래그 없음: 총 ≤ 3·dev 0, `-AllowConcurrentDev`: 총 ≤ 2·dev ≤ 1)로 묶음 순서를 다시 따져 봄 [실행 재생 + 추론]. 1a는 빈 PC에서 두 검사 모두 통과. RM 셋은 `START` 줄(`:237`, 재검사 통과 뒤) 다음에 띄우므로 총 4. 2a(0,0) 통과 → 2a VISSIM 제목이 뜬 뒤 2b(1,1) 통과. 3a(1,1) 통과 / 3b(0,0) 통과. 2b를 2a 재검사 전에 띄우면 2a 재검사가 dev = 0을 못 맞춰 이름이 소모됨(`:232` NOT_LAUNCHED). 파일의 순서 지시가 이것을 막음 |
| 해시 시드 전달 | 발사기는 `RW_*`만 지우고(`:205`) 감시기는 `Start-Process`로 cscript를 띄우므로(`run_real_world_single_watchdog_distributed_core17legs4b.ps1:911`) 환경이 이어집니다 [읽음·추론]. provenance에는 기록되지 않습니다(`PREDECL:401`, 이미 공개) |

- 19:03에 VISSIM 0개입니다 [실행 `Get-Process`]. 과제 문맥의 "NC 재실행 2석 ~18:00"은 이미 끝났습니다.

## 6. K7 diff와 재핀 목록 [실행 `v6_inventory_grep.py`, `v7_vsl_agreement.py`]

- **diff**
  - `54d821c..6c4c740` = 98항목(A 18, M 67, R 13). 망 `baseline_s31_v3c1nc.inpx → baseline_s31_v3c3nc.inpx`(R099), β·손 기록·도시 표 `*_v3c1_20260928 → *_v3c3_20261001`(R).
  - RA-1 추출 5시드(s53 = v3c2 대체), 포트 프로필 3파일, obs150 사이드카, `sig_manifest`가 들어 있습니다.
- **목록 52항목**(`repin_v3c2_inventory.json` `07028e24…`)
  - 저장소 밖 항목: N-1/2/3/6, V-11, RA-6.
  - K7 diff에 없는 저장소 항목(V-1 `freeway_fd.py`, V-2, V-9, R-1/2/4, H-1, P-1/2, E-1, `vsl_command_distribution.py`)은 모두 K1–K6(`9ed2ef0..54d821c`, 11파일 +664/−29)에서 바뀌었습니다.
  - "변경 없음" 항목(V-7 러너 VBS, V-8 `sdmpc.py`)은 `9ed2ef0`부터 K7까지 diff 0입니다. 빠진 항목은 없습니다.
- **남은 옛 망 sha·경로** (원격 head, `vendor` 제외)
  - v3c1 6시드 sha(`3eb06c63` s37 포함), v3c2 6시드 sha, 경로 7종(`v3c1nc`, `baseline_s31_v3c1`, `routing_v3c1`, `v3c1_nc_2026`, `20260927_v3c1`, `20260928_sdmpc31_v3c1`, `unsignalized_validation_v3c1`)을 셌습니다.
  - 살아 있는 후보 줄은 모두 이력 docstring·주석, 또는 계보 기록 상수입니다.
    - `repin_scenario_v2.py:133` `PREVIOUS_RUNTIME_NETWORK`은 영수증 `inputs.previous_runtime_network`(`:1602`)로만 쓰입니다.
    - `:442` `V3C1_EDIT_RECEIPT`는 v3c1이 더한 결정점의 출처 기록(`:638`, `:743`)입니다.
  - 배포 JSON 7개(config ×3, plant, reference, sig_manifest, base)에서 옛 토큰이 든 문자열 리프는 `description`/`_n31_note`/`qualification` 문구뿐입니다. 옛 토큰이 든 키는 0개입니다.
  - `.inpx` 참조는 v3c3 망 또는 `modi_eval_userfix Ver2.inpx`입니다. 후자는 `_canonical`·reference projection의 원본 망 이름이며, `99dc641`과 바이트가 같은 배포 파일 안에 있습니다.
  - `N31D/network/`에는 v3c3 inpx와 `sig_manifest.json`만 있습니다.
  - O-7 표 9행의 건수를 따로 다시 쟀습니다: 29/57, 6/6, 6/6, 5/5, 5/5, 21/123, 12/14, 13/20, 35/44. 보고(`REPIN_V3C3_REPORT.md` §5)와 모두 같습니다.
- **110 전용 가정**
  - 살아 있는 코드(테스트·문서·vendor 제외)에서 `[110]`, `{110}`, `== [max(`, `== 110`, `vsl_all110` 등을 찾았습니다.
  - 남은 것은 옛 스크립트 2개(`diagnose_vsl_channel_20260801.py`, `fit_fd_ver2_v2_20260907.py`)와 `make_reference_config.py:182`의 기준 망 `v_free != 110.0` 검사(최대값 확인)뿐입니다.
  - 명령 공간이 맞아야 하는 곳은 모두 맞습니다.
    - 튜닝 세 벌: `vsl_set` [80,90,100,110], 사상 {80:81, 90:91, 100:101, 110:110}, `max_vsl_step` 40
    - 그 사상의 상 = `lane_native_b110.vbs:34` `RW_ALLOWED_VSL_SPEEDS = "81,91,101,110"`
    - reference: `vsl_set` 같음, FW_E = L2(`speed_scale` 있음)
    - plant 핀: 망 `3de889f0`, 러너 `37c5021f`, reference `add58bc4`

## 7. 단서와 문제

1. **O-5 결정 주체** [읽음]
   - 선언 §0은 O-3만 "USER CHOSE"라는 원문이 있고, O-5는 주체를 메인 세션이 확인해야 한다고 적었습니다.
   - 재관문 보고 단서 1과 동결·푸시 보고 §1은 과제 지시 묶음("…and the USER DECISION")을 기록으로 삼고 푸시했습니다.
   - 이 검증도 같은 오케스트레이터 문구만 봅니다. **사용자 본인의 발화로 O-5 변경을 확인한 기록은 아직 없습니다.**
   - O-5 통과(그리고 GB-8의 판정 기준)는 이 결정에만 기댑니다. 메인 세션이 사용자에게 확인해 선언 기록에 적기를 권합니다.
2. **단일 호출 연산 수 불일치** (판정 영향 없음) [실행·읽음]
   - 사전 선언 `PREDECL:159`은 "L2 48, KA 10 → d1 = 38"이라고 적었습니다.
   - 1차와 재관문 `o5_judgement.json`의 `single_call_ops`는 둘 다 L2 47, KA 9입니다.
   - d1 = 38은 같아서 판정은 바뀌지 않습니다. 다만 어느 보고도 이 차이를 적지 않았습니다(셈 방식 차이로 보임 [추론]).
3. **3a/3b 로그 경로 공유** (사소)
   - 두 줄 모두 `wmi_sdmpc31_v3c3_j1_s43.log`에 `>`로 씁니다.
   - 3a가 첫 좌석 검사에서 거부(exit 5, 이름 미소모)된 뒤 3b를 쓰면, 거부 기록이 덮어써집니다.
   - 발사 기록 도우미 줄(`launch_lines_k7.txt:87-88`)이 시각·RV를 따로 남기므로 손실은 작습니다.
4. 그 밖에 구속 위반은 찾지 못했습니다.
   - W·GWT7(`6c4c740`)·GWT6(`54d821c`)는 모두 `status --porcelain --ignored` 0줄입니다.
   - GWT6의 떠도는 pyc는 없어졌고, 증거 사본 sha는 `6a7cdabd…`로 같습니다 [실행].

## 8. 산출물 (`reports/k7/verify2/`)

- `v1_timeline.{py,json}`: 보고 sha·mtime 시간표
- `v2_o3_membership.{py,json}`: DA-2 수정 기준 (a)–(g), 하류
- `v3_generator_check.{py,json}`: git archive 사본에서 `--check`·재생성·거부 탐침
- `v4_o5_judge.{py,json}`: O-5 항목 1–6, κ 유도
- `v5_frz_vs_remote.{py,json,stdout}`: FRZ 대 원격 head 전 파일
- `v6_inventory_grep.{py,json}`: 목록 충족, 옛 sha·경로, 110 패턴
- `v7_vsl_agreement.{py,json}`: 명령 공간 일치
- `v8_launch_lines.{py,json}`: 발사 줄 77개 검사, 좌석 재생
