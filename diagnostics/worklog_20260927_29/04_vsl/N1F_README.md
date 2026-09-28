# N1F 1단계 — FW_E 고정(단일값) 희망속도 VSL 실험 (실행 폴더)

- **승인:** 2026-09-28 사용자 결정 (구속력 있음)
  - VSL 준수 주 모형은 단일값(고정) 희망속도로 바꾸기로 했습니다. 다만 SDMPC 망과 핀은 N1F 결과가 나올 때까지 바꾸지 않습니다. `D:/VISSIM-merge/*`는 편집하지 않습니다.
  - 승인 범위는 0단계와 1단계입니다.
    - 0단계: VISSIM 없이 기존 N1 팔과 v3b NC로 네 지표를 냅니다. 별도 워크플로가 `stage0/`에서 합니다. 이 폴더의 N1F 도구는 `stage0/`에 쓰지 않습니다.
    - 1단계: 8런입니다. 팔 c90f(새 분포 91 = 90–92 균등)와 c90r(새 분포 94 = 93–95 균등), 시드 41/43/47/53, 명령 일정은 N1 c90과 같습니다.
  - 세부 묶음: 폭은 ±1 km/h 균등입니다. 110은 "VSL 꺼짐 = NC 분포 98–140"으로 둡니다. 램프(R)·HGV(H)는 바꾸지 않고, 붕괴 전 작동(P)은 넣지 않습니다. 조화 지표는 보고 전용입니다.
  - **승인되지 않은 것:** s31(보고용 팔은 별도 승인), 2단계(c90e, c80f, c100f, c80n). 2단계는 계획 JSON에 `stage2_not_approved`로 적기만 했습니다. prepared 폴더와 큐 항목은 없습니다.
- 설계 근거: `C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/vsl-fixed-dsd/VSL_FIXED_DSD_REVIEW.md` §4(설계, G0–G4, D1–D6, 검증 보정 V1–V11)와 §5(경로 a3)
- 사양: `plan/n1f_plan_v1.json` (sha `3e27ac15…`)
- 사전 선언: `reports/PREDECLARATION.md`, 분석 동결 영수증 `reports/analysis_freeze.json`
- **상태 (2026-09-28 17:07):** 도구 작성, 건조 시험 전체 통과(16:46–17:05), 분석 동결(17:06:16, sha `58621873…`), 8팔 빌드 완료(G3 통과). 발사 전입니다.
- **VISSIM, cscript, 큐, `fast_nc_run.ps1 -Execute`는 하나도 띄우지 않았습니다.** 큐 발사는 메인 세션이 §3의 WMI 명령으로 합니다.

---

## 1. 폴더

| 경로 | 내용 |
|---|---|
| `plan/n1f_plan_v1.json` | 사전 선언 계획. 팔, 분포 블록(정확한 XML), 일정, 창, 관문 G0–G4, 판정 규칙 D1–D6, 멈춤 규칙 |
| `scripts/` | N1 도구 사본(`n1f_*`, 루트는 스크립트 위치에서 정함). `n1f_common.py`(공용·안전 가드), `n1f_build.py`(1 빌더 + G3), `n1f_queue.py`(2 큐), `n1f_g0.py`(3 G0·G1·G2), `n1f_extract.py`(4 EO 추출), `n1f_fzp_pass.py`(5 M6·차로·**G4**), `n1f_moments.py`(6a 모멘트), `n1f_harmonise.py`(7 조화 지표, 신규), `n1f_fit.py`(6b 짝 1·2, D1–D4, 조건부 D6). 지원: `n1f_make_plan.py`, `n1f_dry_tests.py`, `n1f_freeze.py` |
| `s41_c90f` … `s53_c90r` (8개) | `source/`(v3b 망 → N1 한 줄 편집 → 분포 블록 삽입 + 자산 + 프로필), `prepared/`(`fast_fixed_profile.prepare`), `build_receipt.json`(G3 두 번, 단계 규칙, 외부 경로 검사, ps1 무-Execute 출력, 발사 줄). 발사 뒤 `run/`, `launch.log`, `g0.json`, `g12.json`, 분석 뒤 `eo/`, `fzp_pass/`(+`g4.json`), `moments.json`, `harmonise.json` |
| `reports/dry_tests.json`, `reports/dry/` | 건조 시험 결과와 산출물 |
| `reports/nc_moments/`, `reports/n1_ref_moments/`, `reports/harmonise_ref/` | 런 전에 만든 분석 입력(NC 4시드, N1 c90·대조 8팔, N1 c90 조화 기준 4팔). sha가 동결 영수증에 있습니다 |
| `reports/analysis_freeze.json`, `reports/PREDECLARATION.md` | 동결 영수증과 사전 선언 |
| `reports/superseded_dryrun1/` | 1차 건조 시험(개별 11개는 통과, 도중 도구 수정으로 전체 판정 false). 쓰지 않습니다. `WHY.txt` 참고 |
| `stage0/` | **다른 워크플로(0단계)의 폴더입니다.** N1F 도구는 여기에 쓰지 않습니다(`n1f_common.writable`이 막음) |
| `queue.log`, `queue_state.json`, `launch_lines.txt`, `queue_stdout.log`, `queue.lock`, `STOP` | 큐가 씁니다(`STOP`은 멈춤 표시) |

---

## 2. 발사 전 확인 (메인 세션)

1. PC 전체 VISSIM 수: `@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count`. 다른 작업의 런(v3c1 RM, SDMPC R-obs 등)도 4석에 포함됩니다. **큐가 매 발사 전에 4 미만이 될 때까지 기다리므로** 지금 4석이 차 있어도 띄워도 됩니다. 다만 도는 런의 우선권은 그 런들에 있습니다.
2. D: 여유 30 GB 이상(8런 약 11 GB).
3. `STOP` 파일이 없어야 합니다. `reports/dry_tests.json`의 `passed`가 `true`, `reports/analysis_freeze.json`이 있어야 합니다. 큐는 동결 영수증과 도구·계획 바이트가 다르면 시작하지 않습니다.
4. 도는 동안 워치독·ps1·cscript 시험 묶음은 금지합니다(전역 kill 사고 방지). 무거운 계산도 가능하면 피합니다(ps1의 300 s 무진행 종료 방지).

## 3. 큐 발사 명령 (WMI, 세션과 분리) — 메인 세션이 PowerShell 도구로 한 번 실행

```powershell
$cl = 'cmd.exe /c C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B D:/VISSIM_runs/20260928_n1f_vsl/scripts/n1f_queue.py --run >> D:/VISSIM_runs/20260928_n1f_vsl/queue_stdout.log 2>&1'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cl; CurrentDirectory = 'D:/VISSIM_runs/20260928_n1f_vsl'}
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
```

- `RV=0`이면 성공입니다. PID는 큐를 감싼 `cmd.exe`입니다. 큐 파이썬은 스스로 BELOW_NORMAL로 내려갑니다(typed ctypes, 읽어서 확인).
- 발사 기록은 메인 세션이 `queue_wmi_launch.txt`에 남기기를 권합니다(N1 관례).
- 큐가 살아 있는지: `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -like '*n1f_queue.py*' | Select-Object ProcessId, CommandLine`
- 큐가 하는 일 (`n1f_queue.py` 머리말; 큐 논리는 N1과 같은 코드)
  - 배치는 `stage1` 하나이고 순서는 s41/s43/s47/s53 c90f → s41/s43/s47/s53 c90r입니다.
  - 런 하나 = WMI `Win32_Process.Create`로 `cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:/VISSIM-merge/sim3-n31/diagnostics/fast_nc_run.ps1 -Prepared <팔>/prepared -Output <팔>/run -Execute -MinimumFreeGiB 8 -AllowConcurrent -Python C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe > <팔>/launch.log 2>&1`. 정확한 줄은 각 `build_receipt.json`의 `launch_command`, 실제 발사 기록은 `launch_lines.txt`에 남습니다.
  - **띄우기 전마다 PC 전체 VISSIM 수 < 4를 확인하고, 아니면 기다립니다.** 런 간격은 45 s 이상이고, 앞 런의 소유권 확인 뒤에 띄웁니다.
  - 소유권: 발사 후 120 s 안에 `run/run.json`의 `vissim`이 채워져야 합니다. 아니면 STOP합니다. **어떤 프로세스도 죽이지 않습니다.**
  - 좌석 경합(5번째 COM 생성 거부)은 그 런을 `run_seatrace1`로 옮기고 자리가 나면 한 번만 다시 띄웁니다. 두 번째면 STOP합니다.
  - G0: 각 런의 `run/progress.csv`가 2,750 s를 넘으면 검사합니다(시작 후 약 30분). IDENTICAL이 아니면 STOP합니다(도는 런은 그대로 둠).
  - 완료 시 G1/G2. 실패하면 `run_fail1`로 옮기고 한 번 다시 띄웁니다. 두 번째 실패면 STOP합니다.
  - 큐 시작 때 자기 환경의 `RW_*` 이름을 `queue.log`에 적습니다. 지금 레지스트리에는 `RW_PYTHON_EXE`가 있지만, 고정 프로필 경로의 핀된 ps1·VBS·파이썬 파일에는 `RW_` 토큰이 하나도 없어서 런에 닿지 않습니다(건조 시험 D9).

## 4. 감시

- `C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -B D:/VISSIM_runs/20260928_n1f_vsl/scripts/n1f_queue.py --status` (읽기 전용 요약)
- `queue.log` 끝부분, `queue_state.json`, 각 런의 `run/progress.csv`와 `run/run.json`
- 실패 진단은 `run/stderr.txt`부터 봅니다. `run.json`의 "identity" 메시지는 동시 실행에서 원인을 가립니다.
- 예상 시간: 런당 약 1.3–1.5 h(N1 실측). 4석이 비어 있으면 8런은 약 2.8–3.0 h이고, 다른 작업이 좌석을 쓰면 늘어납니다.

## 5. 멈춤과 재시작

- `STOP` 파일에 이유가 있습니다. 큐는 도는 런을 건드리지 않고 끝납니다. 소유가 확인되지 않은 VISSIM은 죽이지 말고 사용자에게 보고합니다.
- 메인 세션이 큐를 멈추려면 `STOP` 파일을 만들면 됩니다(다음 폴링, 최대 30 s 안에 멈춤).
- 재시작: 원인을 확인하고 사용자 판단을 받은 뒤 `STOP`을 지우고 §3 명령을 다시 실행합니다. 큐는 디스크 상태에서 재개합니다.
- G0 실패 시(N1 §3.4): 큐가 멈춥니다. "N1F 망 + 빈 프로필로 자체 NC 팔을 더 돌리는" 대안은 **사용자 재승인 뒤**입니다.
- G3 실패는 빌드 단계에서 이미 걸러집니다(8팔 모두 통과). G4 실패는 분석 단계에서 적합기가 D1–D6을 거부합니다.

## 6. 분석 (8런이 모두 G0·G1·G2를 통과한 뒤, 한 번에 하나씩)

도구 4–7은 `reports/analysis_freeze.json`과 자기 바이트가 같을 때만 N1F 런을 읽습니다(`n1f_common.require_freeze`).

```bash
PY=C:/Users/TRLAB/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe
PY12=C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe
cd D:/VISSIM_runs/20260928_n1f_vsl/scripts
for t in s41_c90f s43_c90f s47_c90f s53_c90f s41_c90r s43_c90r s47_c90r s53_c90r; do
  $PY -B n1f_extract.py --arm $t && $PY -B n1f_fzp_pass.py --arm $t && $PY12 -B n1f_moments.py --arm $t && $PY12 -B n1f_harmonise.py --arm $t || break
done
$PY12 -B n1f_fit.py --run        # -> reports/fit_results.json, reports/fit_summary.txt
```

- 시간(건조 시험 실측): 추출 약 90 s, FZP 패스(G4 포함) 약 40 s, 모멘트 약 1 s, 조화 약 35 s → 팔당 약 3분, 8팔 약 25분. 적합은 D6이 돌면 약 8–10분입니다.
- `n1f_fzp_pass`가 팔마다 `fzp_pass/g4.json`을 씁니다. 하나라도 G4가 실패하면 `n1f_fit`은 D1–D6을 내지 않고 "G4_failed"만 적습니다.
- D5(네 지표)는 0단계 도구로 냅니다. 0단계 도구의 대상 목록에는 N1F 팔이 없으므로, 확장본을 쓰고 그 sha를 부록 영수증(`reports/analysis_freeze_addendum_d5.json`)에 남긴 뒤 N1F 런을 읽습니다. D5는 서술 전용이라 어떤 판정도 D5에 기대지 않습니다.

## 7. 판정 규칙 요약 (정본은 `plan/n1f_plan_v1.json` declared_rules)

| ID | 무엇 | 규칙 |
|---|---|---|
| 짝 1 | 팔 − 같은 시드 v3b NC | N1 추정량·규칙 SE 그대로(κ는 N1 값 1.000을 다시 계산해 대조) |
| 짝 2 | 팔 − 같은 시드 N1 c90 | 같은 추정량. SE_between 하한은 N1 c90 시드 간 값과 NC 값 중 큰 것 |
| **D1 (주)** | B2 Δq/q(WA B2-SAT, q23), 짝 2 | "이득 없음": c90f − c90와 c90r − c90의 90% 상한이 둘 다 +3.0 % 미만. "조화가 방류를 올림": c90r − c90 하한 > 0이고 c90f − c90 추정 > 0. 둘 다면 `…_below_3pct`(D6 자동 실행 안 함). 나머지는 판정 불가. 주 추정과 내부 프레임 추정이 같은 결론일 때만. B1은 보고만. (V10: 참 효과 0이어도 판정 불가가 약 20–35 %) |
| D2 (보고) | 셀·프레임 안 sd, 차로 간 sd, 차로변경/대·km, HGV − 승용 (WC Z0, WA Z0; 셀 2–4, 셀·프레임 평균 ≥ 70) | 예측: c90f 셀·프레임 안 sd ≤ 3.0, 차로변경 < c90. 반증: c90f − c90 sd의 90% 상한 > −1.0이면 "단일값의 추가 조화는 작다" |
| D3 | M1 Z012, M2 | 예측: c90f 짝 1 M1 Z012 약 −21 … −23. c90r − c90이 M1 Z012나 M2에서 1.5 km/h를 넘으면 짝 2를 "산포만"으로 읽지 않고 N1 L1 수준 보정을 붙여 보고 |
| D4 (서술) | M3, M5, M7 | 판정 없음 |
| D5 (서술) | 네 지표 | 0단계 도구, 짝 1·2 |
| D6 | 고정 체제 plant 법칙 | D1 = "이득 없음"일 때만. L0, L1_N1, L1, L2, L3, frejo, L4, fallback을 c90f 짝 1로 적합, LOSO(4겹)로 선택(10 % 안이면 모수 적은 쪽). LOLO는 1단계에서 계산 불가 |

## 8. 건조 시험 요약 (`reports/dry_tests.json`, sha `9341c0f9…`, 2026-09-28 16:46–17:05, 전체 통과)

| 시험 | 결과 |
|---|---|
| D1 빌드·컴파일 8팔 | 망 sha가 계획과 같음. G3는 원본과 prepared 사본 모두 통과. 이벤트 272행, 값 {91, 110} / {94, 110}. 컴파일러가 91·94를 받음. 단계 최대 19 / 16. ps1 무-Execute 검사 통과, run 폴더 없음 |
| D10 블록 감사 | 8팔 G3 재감사 통과. 변조 6종은 모두 G3 실패(앞 바이트, 뒤 바이트, 블록 안 점, 94 누락, 100 뒤 삽입, 91 정적 참조). N1 망에 91·94 명령은 컴파일러가 거부. 110 → 85 한 계단은 거부(단계 규칙). 91 → 94 → 110은 수락. 같은 시드 c90f·c90r 망은 바이트가 같음 |
| D2 G0 검사기 | v3b NC 4시드 참조 IDENTICAL. 끝난 N1 c90 4팔 IDENTICAL(양성 대조). s41_c90을 s43 참조와 비교하면 DIFFERENT(음성 대조). G1/G2 함수는 N1 s41_c90에서 통과 |
| D3 추출기 | s41_v3bnc 재추출이 기존 EO 파일 8개와 바이트 동일 |
| D4 FZP 패스·G4 | N1 s41_c90 출력 재현(4개 파일은 바이트 동일, 2개 파일은 새 91·94 열을 빼면 행 동일이고 새 열은 0). G4 양성 대조(90 → 85–120) 1.000(492,627건). 음성 대조(NC s41에 91을 가정한 일정) 0.000(426,107건) → 실패 |
| D5 모멘트 | NC 4시드와 N1 c90·대조 8팔의 모멘트(M1–M7, M5, M6, supply)가 N1 파일과 같음 |
| D6 적합 자체시험 | κ = N1 값. 0 효과 → "이득 없음"·D6 실행. +5 % → "올림"·D6 안 함. 주/내부 불일치 → 판정 불가. c90r 속도 −3 → D3 표시 + 보정. G4 실패 → 거부. frejo 참값(A 0, E 1, α 0) 복원(χ² ≈ 0), LOSO 계산. t 상수는 scipy와 3e-10 안 |
| D7 큐 모의 | 10개 상황(정상, 다른 작업이 4석을 2 h 점유 → 120분에 첫 발사, 2석 점유, G0 실패, 소유권 없음, COM 거부 1·2회, G1/G2 실패 1·2회, 사용자 STOP) 모두 기대대로. PC 전체 VISSIM 최대 4, 4석일 때 발사 0, 간격 ≥ 45 s. 실제 읽기 경로를 끝난 N1 s41_c90에서 읽기 전용으로 확인(G0 IDENTICAL) |
| D8 WMI | 탐침은 띄우지 않았습니다(지시: 아무것도 발사하지 않음). `wmi_create`가 N1 함수와 글자까지 같고, N1이 이 함수로 20런을 띄웠습니다(RV 0) |
| D9 위생 | 저장소·N1·NC 폴더에 새 파일 없음, 바이트코드 없음. 핀된 러너 파일 5개의 `RW_` 0개. 레지스트리 환경에 `RW_PYTHON_EXE`(영향 없음). prepared 외부 경로는 망의 상속 속성 3개뿐(`evalOutDir`은 런 때 덮어씀, 나머지 둘은 표시용). `rule_runtime*` 파일 없음 |
| D11 조화 지표 | N1 c90 4팔에서 A_FACTS 산출물(`a3_fzp_speed_dist.py`)을 키마다 재현. c90 셀·프레임 안 sd: WC Z0 4.306, WA Z0 4.370(자유 필터 값과 같음; WA Z0 셀·프레임 100 % 자유) |

- 동결 영수증: `reports/analysis_freeze.json` (sha `58621873…`, 17:06:16). 사전 선언: `reports/PREDECLARATION.md`.

## 9. 지킬 것

- 핵심 시드 41/43/47/53만 씁니다. s37, RM 팔(v3b, v3c1), 봉인 시드 59/61/67은 열지 않습니다(`n1f_common.forbid`).
- 저장소(`D:/VISSIM-merge/*`), N1 트리(`D:/VISSIM_runs/20260927_n1_vsl`), `stage0/`, 다른 `D:/VISSIM_runs/*` 폴더에는 쓰지 않습니다(`n1f_common.writable`). 파이썬은 항상 `-B`로 돌립니다.
- 도구나 계획을 고치면 동결 영수증과 달라져 큐와 도구 4–7이 멈춥니다. 고쳐야 하면 새 영수증과 이유를 남기고 사용자에게 알립니다.
