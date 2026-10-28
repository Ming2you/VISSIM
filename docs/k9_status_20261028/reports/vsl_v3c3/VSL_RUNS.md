# VSL_RUNS — v3c3 고정 VSL 단독 런 3개: 실행 기록 (2026-10-27 KST)

- 무엇: D-K9-95 의 VISSIM 런 3개(v3c3-s31·s41·s43)를 띄우고 끝까지 돌린 기록입니다. 팔 정의·비교 규칙은 런 전에 고정한 `PRE_VSL.md`(sha256 27452ae6…)를 그대로 따랐습니다.
- 이 문서는 "런이 선언대로 돌았는가" 만 다룹니다. Ω·④·셀 지표 같은 비교 숫자는 아직 내지 않았습니다(PRE_VSL §7.3 분석 단계, 이 문서 밖).
- 표시: **[실행]** 이번에 돌려서 확인 · **[읽음]** 파일·코드를 읽어 확인 · **[추론]** 시험하지 않은 판단 · **[계산]** 이 문서의 산술.
- 경로 줄임: VS = `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/vsl_v3c3`, RR = `D:/VISSIM_runs/20261027_vsl_v3c3`(런 뿌리), V3 = `D:/VISSIM_runs/20261001_v3c3`(NC3), SIM3 = `D:/VISSIM-merge/sim3/diagnostics`(러너, 읽기만).

## 0. 줄임말 (처음 한 번)

- VSL = 가변 제한속도. DSD = VISSIM 희망속도 결정점(표지 자리). 분포 91 = 희망속도 90–92 km/h 균등 분포.
- NC3 = 같은 시드의 v3c3 무제어 런(`V3/s<S>_v3c3nc/run`).
- FZP = VISSIM 차량 궤적 기록(5 s 간격). LDP = 신호 상태 초별 기록.
- WMI = Windows 관리 도구. 여기서는 `Win32_Process.Create` 로 프로세스를 이 세션과 떼어 띄우는 데 씀. PID = 프로세스 번호.

## 1. 쉬운 요약

1. 런 3개가 모두 끝까지 돌았습니다 [실행]. 시드마다 한 번씩만 띄웠고, 멈춤·재발사·kill 은 0 번입니다.
2. VSL 명령은 선언대로 들어갔습니다 [실행]. 900 s 에 DSD 63–66 × 차종 4개 = 16곳에 분포 91 을 썼고, 다시 읽은 값도 91 입니다. 9,000 s 에도 91 이었습니다. 미터 쓰기는 0 입니다.
3. 900 s 전에는 NC3 와 같았습니다 [실행]. 895.1 s 까지 FZP 행 수와 sha256 이 세 시드 모두 같습니다. 처음 다른 행은 세 시드 모두 905.1 s 이고, 그 행은 표지를 막 지난 차의 희망속도가 90–92 km/h 로 바뀐 행입니다.
4. 다음 일은 PRE_VSL §7.3 분석입니다(비교 숫자). 이 문서에는 비교 숫자가 없습니다.

## 2. 발사

### 2.1 발사 전 확인 [실행]

- `PRE_VSL.md` sha256 다시 확인: 27452ae62ae84e7c1cbe4717f1c8777b3c18b5a3f5d18b7cd5da033d83a3faf1(같음).
- `VS/SHA256SUMS_VSL.txt`(cf43058d…) 62줄 모두 OK. 런 뒤에도 다시 62줄 모두 OK(준비 폴더 고정 파일이 안 바뀜).
- sim3 러너 4개 sha 가 발사기 고정값과 같음: fast_nc_run.ps1 269345da…, fast_nc_runner.vbs bf07acda…, fast_fixed_profile_verify.py 91441391…, validate_native_signal_record.py 4a647072….
- 발사기 드라이런 다시 돌림(10:57): 고정 시험 `VS/tools/test_vsl_launcher.py`(b1725433…)에서 출력 폴더 줄 하나만 바꾼 사본(`VS/logs/recheck_launcher_1057/test_vsl_launcher_recheck.py`, c1b8b3fb…)으로 시나리오 9개 모두 PASS(11.5 s). WMI·kill·VISSIM 0. 앞 시험 결과 파일(`VS/dryrun/test_result.json`)은 건드리지 않음.
- 시작 상태: PC VISSIM 0개, RR 에 `_launcher`·run 폴더 없음, 디스크 C 24 GB·D 222.4 GB.

### 2.2 발사기와 런 [실행]

| 항목 | 값 | 근거 |
|---|---|---|
| 발사기 | `VS/tools/vsl_launcher.ps1` sha256 cbc37aff…, PID 20992 | `RR/vsl_launcher_start_receipts.log` |
| 발사기 시작 | 10:57:02, `vsl_launcher_start.ps1`(d038e32c…) → WMI RV=0 | 같은 파일 |
| s31_run1 | 10:57:04 발사(WMI RV=0, cmd PID 47896, 앞 VISSIM 0) | `RR/vsl_launcher.log`, `RR/wmi_launch_lines_vsl.txt` |
| s41_run1 | 10:58:05 발사(RV=0, cmd PID 43392, 앞 VISSIM 1) | 같음 |
| s43_run1 | 10:59:06 발사(RV=0, cmd PID 54996, 앞 VISSIM 2) | 같음 |
| 끝 기록 | 12:38:04 s31 done · 12:40:05 s41 done · 12:40:05 s43 done · 12:40:05 EXIT | `RR/vsl_launcher.log`, `RR/_launcher/end_s*_run1.json` |

- 발사 줄은 `RR/launch_lines_vsl.txt`(0456cf45…)의 줄과 글이 같습니다(`fast_nc_run.ps1 -Prepared RR\s<S>\prepared -Output RR\s<S>\run -Execute -MinimumFreeGiB 8 -AllowConcurrent`).
- 시드마다 표지 `_launcher/launched_s<S>_run1.json` 이 하나씩만 있습니다. run2(재발사) 표지·`backstop_kill_*`·`LAUNCH_STOPPED.json` 은 없습니다.

| 시드 | cscript PID | VISSIM PID | 시작 → 끝 (KST) | 벽시계 | 첫 진행 | progress.csv 행 사이 최대 | run 폴더 |
|---|---|---|---|---|---|---|---|
| v3c3-s31 | 20448 | 49048 | 10:57:05 → 12:37:33 | 100.5분 | 10:57:46 (sim 25.1 s) | 6.1 s | 1.2 GB |
| v3c3-s41 | 23272 | 39172 | 10:58:06 → 12:39:39 | 101.6분 | 10:58:47 (sim 20.1 s) | 6.1 s | 1.2 GB |
| v3c3-s43 | 31540 | 55456 | 10:59:07 → 12:39:43 | 100.6분 | 10:59:48 (sim 5.1 s) | 6.1 s | 1.2 GB |

- 근거: 각 `RR/s<S>/run/run.json`(started·finished·cscript_pid·vissim·first_native_progress), `progress.csv` [실행]. 벽시계는 [계산].
- 5분 무진행 규칙(사용자 방침): 행 사이 최대 6.1 s 라 한 번도 걸리지 않았습니다. 9분 이하 간격으로 진행을 읽었고(진행 나이 0–4 s), kill 은 0 번입니다 [실행].
- PC 전체 VISSIM: 우리 3개에 더해 다른 세션 VISSIM 1개(PID 32060, 11:25:15 생성)가 한동안 있어 최대 4개였습니다. 세기만 하고 건드리지 않았습니다 [실행]. 12:40 에 PC VISSIM 0개.
- 디스크: 런 동안 C 24 GB·D 213 GB 이상 [실행].

## 3. 런 점검 (PRE_VSL §6.2 V1·V2·V3)

- 도구: `VS/tools/vsl_runcheck.py` sha256 e0da7f03dc34afab1b3d8d828b2fa163c3d6de96dffb9b93496b2134be3677e8. 런이 끝나기 전(11:00 LOG)에 sha 를 고정했습니다. §6.2 의 V1·V2·V3 정의를 그대로 옮겼고 새 정의는 없습니다. 합성 시험 PASS(`VS/selftest/runcheck/test_runcheck.py`, 087d1cef…).
- V3 첫 다른 행은 고정 도구 `vsl_firstdiff.py`(a8ec13d9…)를 공유 잠금 아래에서 돌렸습니다(§3.3).
- 출력: `VS/out/runcheck/runcheck.json` sha256 2ec689c97cbed588a1db8923dd724d41b794c2fe477c21bfbd6398da5aa0dc1f.

### 3.1 V1 런 완료 [실행]

| 시드 | completed | exit_code | 검증 exit | fixed_validation passed | STAGE=SIM_DONE | SIM_SEC=9000 | 쓴 시도 |
|---|---|---|---|---|---|---|---|
| v3c3-s31 | true | 0 | 0 | true | 있음 | 있음 | run(1차) |
| v3c3-s41 | true | 0 | 0 | true | 있음 | 있음 | run(1차) |
| v3c3-s43 | true | 0 | 0 | true | 있음 | 있음 | run(1차) |

- 그 밖 [실행]: run.json `error` null, `owned_native_alive` false(VISSIM 이 끝에 닫힘), FZP 1개씩(s31 1,149,552,072 B · s41 1,178,158,159 B · s43 1,162,376,857 B). run.json 의 prepared_sha256 = LOG 고정값(79eefd75… · 27ccd7ba… · 36170f2d…), runner_sha256 = bf07acda….
- 저장 설정 다시 읽기(`readback.csv`) [실행]: RandSeed = 31·41·43(시드별 맞음), SimRes 10, SimPeriod 9,001, FZP 간격 50 단계(5 s)·5 s 부터. s31 은 rule-RM s31 의 readback.csv 와 글이 같습니다. NC3 readback.csv 의 RandSeed·SimRes·NumRuns·FZP 두 줄과 값이 같습니다(NC3 파일에는 SimPeriod 줄이 없음; fixed_profile 모드만 그 줄을 씀).

### 3.2 V2 명령 [실행]

| 시드 | 쓰기 행 | 쓰기 내용 | 미터 쓰기 | 0 s DSD 63–66 | 9,000 s DSD 63–66 |
|---|---|---|---|---|---|
| v3c3-s31 | 16 | 900 s · vsl · DSD 63/64/65/66 × 차종 10/20/30/70 · expected 91 = actual 91 · ok 1 | 0 | 110 (16곳) | 91 (16곳) |
| v3c3-s41 | 16 | 같음 | 0 | 110 | 91 |
| v3c3-s43 | 16 | 같음 | 0 | 110 | 91 |

- 근거: `RR/s<S>/run/fixed_readback.csv`(1,744행 = 처음 864 + 쓰기 16 + 끝 864). 세 시드 파일 바이트가 같습니다(sha256 8185c88302130eeb61bc9c3d59ce039ef405ee11e5519578840398391f5e1ee7).
- 러너 검증기(`SIM3/fast_fixed_profile_verify.py`)도 통과했습니다(`fixed_validation.json`): event_readbacks 16, snapshot 주소 864, 쓰지 않은 DSD·SG 상태 sha 가 앞뒤 같음(93d33a9c…, 세 시드 같음), LDP 450,000행, 미터 표본 검사 0(미터 쓰기 없음).
- 러너 stdout 에 `SIM_SEC=900` 이 찍힌 뒤 이벤트 쓰기에서 멈춤(`Die`) 없이 9,000 s 까지 갔습니다(`RR/s<S>/run/stdout.txt`) [실행]. VBS 는 이벤트 주소가 처음 스냅샷에 없으면 멈추게 되어 있습니다 [읽음 `SIM3/fast_nc_runner.vbs:365`].
- 미터는 native OFF 그대로입니다: 망 폴더의 `VISSIG_Controller.dll.err` 가 "SC 9101–9108 신호 프로그램 없음" 이고, NC3 준비 폴더의 같은 파일과 글이 같습니다 [실행].

### 3.3 V3 900 s 전 짝 [실행]

- 실행: `VS/tools/jobs_runcheck.json`(583d12be…, 데이터 전 고정)을 `vsl_heavy.ps1`(479a7e69…)로 WMI·BELOW_NORMAL 발사(12:40:24, PID 47724). 공유 잠금 `D:/VISSIM-merge/k8_gate_trees/heavy.lock` 이 다른 작업(o1o2, 뒤에 C1)에 잡혀 있어 30 s 마다 기다렸습니다(75번). 13:17:56 잠금을 얻어 세 작업(각 2.4–2.7 s, exit 0)을 돌리고 13:18:03 잠금을 지웠습니다. 기록 `VS/logs/runcheck_20261027/heavy.log`.

| 시드 | ≤ 895.1 s 행 수 VSL / NC3 | ≤ 895.1 s sha256 (VSL = NC3) | 같음 | 모든 행이 같은 마지막 프레임 | 첫 다른 행 시각 |
|---|---|---|---|---|---|
| v3c3-s31 | 387,397 / 387,397 | 734a2d88… | 예 | 900.1 s | 905.1 s |
| v3c3-s41 | 398,331 / 398,331 | b61cdb73… | 예 | 900.1 s | 905.1 s |
| v3c3-s43 | 393,558 / 393,558 | 86c06c73… | 예 | 900.1 s | 905.1 s |

- 근거: `VS/out/runcheck_firstdiff/firstdiff_s<S>.json`(e13e9600… · 5100ee6d… · 94417e24…).
- s31 의 895.1 s 접두 sha(734a2d88…)와 행 수(387,397)는 데이터 전 자체 시험에서 rule-RM s31 대 NC3 s31 로 본 값과 같습니다 [실행; LOG 10:44 항목].
- 그래서 세 시드 모두 "†접두 다름" 표시가 필요 없습니다.

### 3.4 첫 다른 행이 보여 주는 것 [실행 FZP 행 읽기]

- FZP 열 순서: SIMSEC; NO; 링크; 차로; POS; POSLAT; SPEED; …; DESSPEED(10번째) … [실행 FZP 머리줄].
- 세 시드 모두 첫 다른 행은 링크 2 위, 표지(링크 2 의 3,998.67 m)를 막 지난 차입니다. 다른 값은 희망속도와 그에 따른 위치·속도입니다.

| 시드 | 차량 | 차로 | 위치 VSL / NC3 (m) | 희망속도 VSL / NC3 (km/h) | 속도 VSL / NC3 (km/h) |
|---|---|---|---|---|---|
| v3c3-s31 | 4736 | 1 | 4,013.22 / 4,013.29 | 91.686 / 126.815 | 125.12 / 126.82 |
| v3c3-s41 | 5257 | 2 | 4,007.71 / 4,007.74 | 90.011 / 99.309 | 98.29 / 99.31 |
| v3c3-s43 | 3054 | 3 | 4,032.74 / 4,033.50 | 91.265 / 118.873 | 111.96 / 118.87 |

- 읽는 법 [추론]: 900 s 쓰기 뒤 표지를 처음 지난 차가 분포 91(90–92)에서 새 희망속도를 받았고, 그 차부터 궤적이 갈립니다. 쓰기가 실제 차량에 닿았다는 직접 증거입니다. 크기·방향에 대한 판단은 하지 않습니다.

## 4. 그 밖 확인 [실행]

- `.err`(VISSIM 메시지): 세 시드 모두 메시지 종류가 같은 시드 NC3 와 같습니다(차로변경 대기 끝 제거, 다음 링크 못 찾음, 여행시간 구간, 입력 미완료, VISSIG DLL 경고). 새 종류의 메시지는 없습니다. "error" 낱말이 든 줄은 VISSIG DLL 경고 한 줄뿐이고 NC3 에도 같은 줄이 있습니다. 메시지 개수는 교통 결과에 속하므로 여기서 비교하지 않습니다(분석 단계).
- 망 폴더 `baseline_s<S>_v3c3vsl.err`(200 B): "경로결정 1102 가 첫 커넥터 5.431 m 앞" 경고 한 줄. 같은 시드 NC3 의 망 .err 와 글이 같습니다.

## 5. 지킨 규칙·하지 않은 것

- VISSIM 런은 선언한 3개뿐, 시드마다 1번. 다른 세션 VISSIM 은 세기만 함. 이름으로 죽이기 0, kill 0 [실행].
- 무거운 python(FZP 읽기)은 공유 잠금 아래 BELOW_NORMAL, PYTHONHASHSEED=0, python -B 로만 돌렸습니다. 잠금은 우리 토큰일 때만 지웠습니다 [실행 heavy.log]. `vsl_runcheck.py` 는 작은 파일만 읽어 잠금 밖에서 돌렸습니다.
- 커밋·푸시 0. GWT8·sim3·frozen·NC3·rule-RM 런 폴더·Y: 쓰기 0. 쓰기는 VS, RR(런 출력), 그리고 이 문서의 사본(`V3/reports/k8/vsl_v3c3/`)뿐입니다.
- 금지 시험 0. sealed/ 열기 0. 봉인 시드 자료 0.
- PRE_VSL 의 팔 정의·비교 규칙·도구는 바꾸지 않았습니다. 런 뒤에 고친 도구는 없습니다.

## 6. 다음 (PRE_VSL §7.3, 이 문서 밖)

1. `python -B VS/tools/vsl_analysis_jobs.py` → `jobs_analysis.json`(sha 를 LOG 에).
2. `vsl_heavy.ps1` 로 공유 잠금 아래 vsl_vhr → fwe_scan·vsl_cell_scan·vsl_firstdiff → vsl_metrics run. V6(B 칸 72개 재현)이 하나라도 다르면 숫자를 내지 않고 멈춥니다.
3. 세 시드 모두 1차 런을 씁니다(`_launcher/end_s<S>_run2.json` 없음 → run 폴더).

## 7. 파일

| 파일 | sha256 |
|---|---|
| `RR/s31/run/run.json` | 36a01b2241ab5afe2a6a8727a003861bed25ee1d5dc7db94c8ed954015e21789 |
| `RR/s41/run/run.json` | 66de3c894e4b14b58a34fdf62dcfde2fe9f87f8ad5ba2daecf8ae474aaa16d33 |
| `RR/s43/run/run.json` | fe668539b572d7eb0f233988b25ee846f48f9bb5f4c71506c815f46ba6aa3658 |
| `RR/s{31,41,43}/run/fixed_readback.csv` | 8185c88302130eeb61bc9c3d59ce039ef405ee11e5519578840398391f5e1ee7 (세 시드 같음) |
| `RR/s31/run/fixed_validation.json` | d9a9afeec99cd45b11beac3f3658e3cd44178a90c93c4acd8de9a72b6d691632 |
| `RR/s41/run/fixed_validation.json` | 8691f0bd31ea360ba5a3a1b8b0f75f262d1f533545ce3d3d7d029166fa65f101 |
| `RR/s43/run/fixed_validation.json` | 5b5b92741ec1b8c0e6e8f1c6b6cf4d726f7ce195f8a72d8323f73082aadd4525 |
| `VS/tools/vsl_runcheck.py` | e0da7f03dc34afab1b3d8d828b2fa163c3d6de96dffb9b93496b2134be3677e8 |
| `VS/tools/jobs_runcheck.json` | 583d12bef2aeadcac4827e9e35cc03942066e403cb63183cc6cfd7e8ae478477 |
| `VS/out/runcheck/runcheck.json` | 2ec689c97cbed588a1db8923dd724d41b794c2fe477c21bfbd6398da5aa0dc1f |
| `VS/out/runcheck_firstdiff/firstdiff_s31.json` | e13e96009fe68dd0378cdc2612fe5dfdd2be940cd52dc0c66e9bca6a7c8c5fdf |
| `VS/out/runcheck_firstdiff/firstdiff_s41.json` | 5100ee6d20ba9a50b642eb9b6fbba5e3917d636566a0b90b873ffbcfbe638927 |
| `VS/out/runcheck_firstdiff/firstdiff_s43.json` | 94417e24139682aacdf128046f4d1508576e566d9bef14795d27f5ab7c11c46f |
| FZP | `RR/s<S>/run/vissim_eval/baseline_s<S>_v3c3vsl_001.fzp` |
| 기록 | `VS/LOG.md`(10:57·11:00·11:28·12:42·13:20 항목), `RR/vsl_launcher.log`, `RR/wmi_launch_lines_vsl.txt`, `RR/vsl_launcher_start_receipts.log` |
