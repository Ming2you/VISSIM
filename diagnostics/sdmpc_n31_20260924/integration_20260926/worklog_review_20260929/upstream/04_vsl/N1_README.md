# N1 — FW_E native VSL 계단 실험 (실행 폴더)

- **승인:** 2026-09-27 사용자 결정. `N1_DESIGN.md` 개정 3 그대로, 사양 `n1_plan_v3.json`(sha `0db0d1c6…`).
  - 핵심 16런 = 시드 41/43/47/53 × {c90, c100, c80, 대조(S5 펄스)}
  - 배치 B1 c90 → B2 c100 → B3 c80 → B4 대조. 50–70은 나중에 (a)로 처리. B5(s31)는 조건부. N1-R은 보류.
- **상태 (2026-09-27 23:47):**
  - 도구 1–6 작성, 건조 시험 D1–D9 모두 통과 → `reports/dry_tests.json` (sha `51e47e20…`)
  - 분석 동결 영수증 → `reports/analysis_freeze.json` (sha `3b54d484…`; 도구 1–6과 계획 JSON의 sha256)
  - 16개 팔 빌드·컴파일 완료 (`<팔>/prepared/`, 동결된 빌더로 만듦)
  - **VISSIM·cscript·`fast_nc_run.ps1 -Execute`는 하나도 띄우지 않았습니다.** 발사는 메인 세션이 §3의 WMI 명령으로 합니다.
- 설계 문서: `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/fwe-struct/p0/N1_DESIGN.md`

---

## 1. 폴더

| 경로 | 내용 |
|---|---|
| `scripts/` | 도구. `n1_common.py`(공용·안전 가드), `n1_build.py`(1 빌더), `n1_queue.py`(2 발사 큐), `n1_g0.py`(3 G0·G1·G2), `n1_extract.py`(4 EO 추출), `n1_fzp_pass.py`(5 DESSPEED·차로 패스), `n1_moments.py`(6a 모멘트 M1–M7), `n1_fit.py`(6b 짝·규칙·L0–L4 적합·LOSO/LOLO). 지원: `n1_dry_tests.py`, `n1_freeze.py` |
| `reports/dry_tests.json` | 건조 시험 결과 (D1–D9) |
| `reports/analysis_freeze.json` | 분석 동결 영수증 |
| `reports/dry/` | 건조 시험 산출물 (G0 선례, 추출기 재추출, FZP 패스, 큐 모의, WMI 탐침, 적합 자체시험) |
| `reports/nc_moments/` | 짝 NC(v3b, 시드 31/41/43/47/53) 모멘트. 적합 입력이며 영수증에 sha가 있습니다 |
| `reports/superseded_dryrun1/`, `reports/superseded_dev_build_s41_c90/` | 옛 빌드·건조 시험(1차 시도는 D8 WMI 탐침에서 stderr 디코딩 결함으로 멈춤 → 고친 뒤 전체를 다시 돌림). 쓰지 않음. 지워도 됩니다 |
| `s41_c90/` … `s53_placebo/` (16개) | `source/`(v3b 망 사본 + 한 줄 편집 + 자산 + 프로필), `prepared/`(`fast_fixed_profile.prepare`), `build_receipt.json`. 발사 뒤 `run/`, `launch.log`, `g0.json`, `g12.json`, 분석 뒤 `eo/`, `fzp_pass/`, `moments.json` |
| `queue.log`, `queue_state.json`, `launch_lines.txt`, `queue_stdout.log`, `queue.lock` | 큐가 씁니다 |
| `STOP` | 큐 멈춤 표시(JSON: 이유). 있으면 큐가 멈추고, 새로 시작하지도 않습니다 |

---

## 2. 발사 전 확인 (메인 세션)

1. PC 전체 VISSIM 수: `@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count`. 다른 작업의 런도 4석에 포함됩니다. 큐가 자리를 기다리므로 0이 아니어도 됩니다.
2. D: 여유 30 GB 이상 (16런 약 20 GB).
3. `STOP` 파일이 없어야 하고, `reports/dry_tests.json`의 `passed`가 `true`, `reports/analysis_freeze.json`이 있어야 합니다.
4. N1 동안 워치독·ps1·cscript 시험 묶음은 금지합니다(전역 kill 사고 방지). 다른 무거운 계산도 가능하면 피합니다(ps1의 300 s 무진행 종료 방지).

## 3. 큐 발사 명령 (WMI, 세션과 분리) — 메인 세션이 PowerShell 도구로 한 번 실행

```powershell
$cl = 'cmd.exe /c C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B D:/VISSIM_runs/20260927_n1_vsl/scripts/n1_queue.py --run >> D:/VISSIM_runs/20260927_n1_vsl/queue_stdout.log 2>&1'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cl; CurrentDirectory = 'D:/VISSIM_runs/20260927_n1_vsl'}
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
```

- `RV=0`이면 성공입니다. PID는 큐를 감싼 `cmd.exe`입니다. 큐 파이썬은 스스로 BELOW_NORMAL로 내려갑니다.
- 큐가 살아 있는지: `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -like '*n1_queue.py*' | Select-Object ProcessId, CommandLine`
- 큐가 하는 일 (`n1_queue.py` 머리말)
  - 배치 순서 B1 → B2 → B3 → B4. 앞 배치 4런이 모두 G0·G1·G2를 통과해야 다음 배치를 띄웁니다.
  - 런 하나 = WMI `Win32_Process.Create`로 `cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:/VISSIM-merge/sim3-n31/diagnostics/fast_nc_run.ps1 -Prepared <팔>/prepared -Output <팔>/run -Execute -MinimumFreeGiB 8 -AllowConcurrent -Python C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe > <팔>/launch.log 2>&1`. 정확한 줄은 각 `build_receipt.json`의 `launch_command`, 실제 발사 기록은 `launch_lines.txt`에 있습니다.
  - 띄우기 전 PC 전체 VISSIM 수 < 4를 확인하고, 아니면 기다립니다. 런 간격은 45 s 이상이고, 앞 런의 소유권 확인 뒤에 띄웁니다(모의 시험에서 50 s).
  - 소유권: 발사 후 120 s 안에 `run/run.json`의 `vissim`이 채워져야 합니다. 아니면 STOP합니다. **어떤 프로세스도 죽이지 않습니다.**
  - 좌석 경합(5번째 COM 생성 거부)은 그 런을 `run_seatrace1`로 옮기고 자리가 나면 한 번만 다시 띄웁니다. 두 번째면 STOP합니다.
  - G0: 각 런의 `run/progress.csv`가 2,750 s를 넘으면 검사합니다(시작 후 약 30분). 모든 배치의 모든 런에 합니다. IDENTICAL이 아니면 STOP(도는 런은 그대로 둠). 읽기 오류는 두 번까지 다시 시도합니다.
  - 완료 시 G1/G2. 실패하면 `run_fail1`로 옮기고 한 번 다시 띄웁니다. 두 번째 실패면 STOP합니다.

## 4. 감시

- `C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B D:/VISSIM_runs/20260927_n1_vsl/scripts/n1_queue.py --status` (읽기 전용 요약)
- `queue.log` 끝부분, `queue_state.json`, 각 런의 `run/progress.csv`와 `run/run.json`
- 실패 진단은 `run/stderr.txt`부터 봅니다. `run.json`의 "identity" 메시지는 동시 실행에서 원인을 가립니다.
- 예상 시간: 런당 약 1.5–1.8 h, 배치 넷 약 6.5–7.5 h.

## 5. 멈춤과 재시작

- `STOP` 파일에 이유가 있습니다. 큐는 도는 런을 건드리지 않고 끝납니다. 소유가 확인되지 않은 VISSIM은 죽이지 말고 사용자에게 보고합니다.
- 메인 세션이 큐를 멈추려면 `STOP` 파일을 만들면 됩니다(다음 폴링, 최대 30 s 안에 멈춤).
- 재시작: 원인을 확인하고 사용자 판단을 받은 뒤 `STOP`을 지우고 §3 명령을 다시 실행합니다. 큐는 디스크 상태에서 재개합니다. 끝난 런은 게이트를 다시 확인하고, 도는 런에는 다시 붙고, `run_fail*`·`run_seatrace*` 폴더 수를 시도 횟수로 셉니다.
- G0 실패 시 설계 §3.4: 같은 N1 망 + 빈 프로필로 자체 NC 팔 4런을 더하는 안은 **사용자 재승인 뒤**입니다.

## 6. 분석 (B4까지 끝난 뒤, 한 번에 하나씩)

도구 4–6은 `reports/analysis_freeze.json`과 자기 바이트가 같을 때만 N1 런을 읽습니다(`n1_common.require_freeze`).

```bash
PY=C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
PY12=C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe
cd D:/VISSIM_runs/20260927_n1_vsl/scripts
for t in s41_c90 s43_c90 s47_c90 s53_c90 s41_c100 s43_c100 s47_c100 s53_c100 s41_c80 s43_c80 s47_c80 s53_c80 s41_placebo s43_placebo s47_placebo s53_placebo; do
  $PY -B n1_extract.py --arm $t && $PY -B n1_fzp_pass.py --arm $t && $PY12 -B n1_moments.py --arm $t || break
done
$PY12 -B n1_fit.py --run          # -> reports/fit_results.json, reports/fit_summary.txt (k=4 판정)
```

- 시간: 추출 1회 약 1분, FZP 패스 약 30초, 모멘트 수 초, 적합 약 3분(LOSO/LOLO 포함).
- 판정 규칙은 `n1_plan_v3.json` declared_rules입니다. 계획 문구에 없는 구현 선택은 `n1_fit.py`의 `IMPLEMENTATION_CHOICES`에 있고, 영수증에도 있습니다.

## 7. B5 (s31, 조건부)

- `reports/fit_results.json`의 `k4_core.B5_rule.launch_B5_plan_rule`이 `true`일 때만, 사용자 승인 뒤에 합니다.
  - 계획 문구는 B1 절반값 2.9/3.2 %(전원 노출)를 씁니다. 노출 가중 절반값(약 2.38/2.62 %)으로 본 결과는 `launch_B5_exposure_weighted_sensitivity`에 있습니다. 둘이 다르면 사용자가 정합니다.
- 절차
  1. `$PY -B n1_build.py --arms s31_c100,s31_c90,s31_c80,s31_placebo`
  2. §3 명령에서 `--run` 뒤에 `--batches optional_B5`를 붙여 WMI로 발사
  3. s31 네 팔 분석(§6 루프)
  4. 기존 `reports/fit_results.json`·`fit_summary.txt`를 `*_k4_before_b5.*`로 이름을 바꾼 뒤 `$PY12 -B n1_fit.py --run --with-b5` (k=4 판정은 그대로, k=5는 보고용)

## 8. 건조 시험 요약 (`reports/dry_tests.json`)

| 시험 | 결과 |
|---|---|
| D1 빌드·컴파일 16팔 | 망 sha가 계획과 같음(편집 1줄), 이벤트 행 272/272/544/32, ps1 무-Execute 검사 통과, run 폴더 안 만듦 |
| D2 G0 검사기 | v2 선례 재현: NC 대 fix90 1,200 s 접두 동일(607,536행, sha `ad68454f`), fix90 대 fix70 1,350 s 동일(727,999행), NC 대 fix90 1,350 s는 다름(음성 대조). v3b NC 5시드 참조 모두 IDENTICAL. v2 런을 v3b 참조와 비교하면 DIFFERENT. G1/G2 함수는 v2 fix90에서 통과 |
| D3 추출기 | s31_v3bnc 재추출이 기존 EO 파일 8개와 바이트 동일 |
| D4 FZP 패스 | EO 교차 수와 598창 모두 일치. 가상 c90 일정의 노출 몫 B2 0.817, B1 0.829(램프 유량 계획값 0.818/0.830) |
| D5 NC 모멘트 | `n1_power2.json` 240개 값과 차이 0, M5가 `n1_capdrop_nc.json`과 10건 모두 같음, 계획 power_t 합동값(B2 6,904.1/55.9/56.1/67.4 등) 재현 |
| D6 적합 자체시험 | 참 0 → L0 기각·L4 선택·Carlson 계열 기각, 참 L0 → L0 비기각·L0 선택(χ² ≈ 0), 잡음 넣어도 같음. t·χ² 상수는 scipy와 1e-9 안, 혼합 용량은 `rv_exposure.json`과 3e-11 안 |
| D7 큐 모의 | 9개 상황(정상, 좌석 경합, G0 실패, 소유권 없음, COM 거부 1·2회, G1/G2 실패 1·2회, 사용자 STOP) 모두 기대대로. PC 전체 VISSIM 최대 4, 간격 50 s. 실제 읽기 경로(tasklist, BOM run.json, progress.csv, G0, G1/G2)를 v2 fix90에서 읽기 전용으로 확인 |
| D8 WMI 탐침 | 무해한 `cmd.exe /c echo`를 WMI로 띄워 슬래시 경로 리다이렉트 확인(RV 0) |
| D9 위생 | 저장소와 읽은 런 폴더에 새 파일 없음. 우선순위 BELOW_NORMAL(0x4000) 확인 |

## 9. 지킬 것

- fit 시드만 씁니다(31/41/43/47/53). s37, v3b RM 팔, 봉인 시드 59/61/67은 열지 않습니다(`n1_common.forbid`가 막음).
- 저장소(`D:/VISSIM-merge/*`)와 다른 `D:/VISSIM_runs/*` 폴더에는 쓰지 않습니다(`n1_common.writable`이 막음). 파이썬은 항상 `-B`로 돌립니다.
- 도구를 고치면 동결 영수증과 달라져 도구 4–6이 N1 자료를 읽지 않습니다. 고쳐야 하면 새 영수증과 이유를 남기고 사용자에게 알립니다.
