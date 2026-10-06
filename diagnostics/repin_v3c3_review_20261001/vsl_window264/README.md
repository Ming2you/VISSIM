# 다른 컴퓨터 실행: SDMPC + 시간창 고정 VSL90

2026-10-06 사용자 승인 설정. 이 폴더의 `config.json`을 사용한다. 이전 queue/STOP/결과 폴더를 복사해 재시작하지 않는다. 현재 이 컴퓨터의 `20261006_urban_storage40_fixed90_s29_9000` 런은 기존 900초 이후 고정90 정책으로 계속 실행 중이며 변경하지 않았다.

## 이번 실행 조건

- 정본 FW80 / urban90, seed29, 9,000초. 입력·경로·신호 시간 규약과 망은 유지한다. network SHA256: `64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc`.
- SDMPC는 900초부터 green·offset·8개 RM을 선택한다. 제어 주기150초, 예측450초/3블록. VSL은 최적화하지 않는다.
- **동측 기존 병목 VSL 구역 `FW_E__seg13`: `1800 <= t < 5700`이면90, 그 밖에는110km/h.** 실제 구역 주소는 parent21의 seg13·14이다. 31개 물리 셀의 13·14라는 뜻이 아니다. 두 방향 입구와 나머지 구역은110이다. 숫자는 희망속도 분포 명령이며 모든 차량의 실제 속도를 뜻하지 않는다.
- 5,700초 명령에서110으로 복귀한다. 미래 예측 블록에도 각 블록 시작시각의 명령을 넣는다. 예: 1,650초 예측 `[110,90,90]`, 5,550초 예측 `[90,110,110]`. 실제 writer에는 첫 블록만 전달한다.
- 제어 계산 실패 시 직전 적용 green·offset·RM을 유지하되, VSL 시간창은 현재 시각에 맞춘다. 관측·실행 오류를 성공으로 덮지 않으며 실패 로그를 남긴다.
- Ω는 접근도로 포함701개 링크. 66 포함, 38·67 출구도로를 새로 추가하지 않는다. 목적함수는 Ω 체류 TTT이며 N_P/N_UF 정의는 유지한다. 외부 대기는 진단이다.
- 기존 RM 최소 녹색2초, 변경폭2초, 적·녹만 사용, 도시17개 신호 관측 차로 저장90% guard, 40번 좌회전 차로 투영을 포함한다. guard는 관측 기반 제약이며 미래 spillback을 완전히 방지한다는 보장은 아니다.

## 시간창의 근거와 검증 범위

무제어 seed29의 150초 차량 스냅샷에서 셀 평균속도60km/h 미만·3대 이상으로 확인했다. 앞 램프군은 대략1,350–7,950초, 램프 사이2,250–5,400초, 뒤 램프군1,950–5,250초가 주요 저속 기간이었다(5,550초에도 일부 저속). 1,800–5,700초는 이번 VSL 대상인 뒤쪽 병목을 겨냥한 비교 후보다. 망 전체 혼잡이5,700초에 끝난다는 뜻이나 최적 시간창이라는 뜻은 아니다. `nc_congestion_timing.json` 참조.

- 단위·CScript 회귀 검사38개 PASS. 실제 runner의 Python3.12 환경에서는 기존 QP 회귀까지44개 및14개 하위 검사 PASS. ON/OFF 경계, 미래3블록, 실패 시 종료시각 복귀, 기존 저장·차로·RM 제약 포함.
- 저장1,500초 및1,650초: 초기 Ω 재고 정합, 보호 초기 명령과3블록 writer·시간창 검사 PASS.
- 저장5,550초: 같은 검사 및450초 모델 예측1회 PASS. 실제 새 정책 폐루프 성능 검증은 아니다. 비교 상태는 기존 고정90 정책에서 가져왔고, 다른 정책의 가격을 이월하지 않는 오프라인 cold-price 검사였다. production 가격·적용 receipt 검사는 완화하지 않았다.
- canonical watchdog `PreflightOnly` PASS: VISSIM 시작0회. 실제 런에서는 freeze manifest를 추가 검증한다.
- 저장1,650초에서 기존 정책도 SC6 p4=19.999초(최소20초)로 실패한 반올림 문제를 재현했다. 기존 물리 투영으로 최대2ms 이하 정밀도 오차만 복구하고, 원래 변경 한도·3블록 제약을 그대로 재검사한다. 큰 위반은 여전히 실패한다. 수정 후 같은 상태 PASS.
- **새 시간창의 native 실행 및 TTT 개선은 아직 미검증이다.** 실행 완료 후 LDP·VSL 적용 readback, 동일701영역 TTT·유출·삭제·미삽입·잔여 차량으로 판단해야 한다.

## 다른 컴퓨터에서 실행

Windows + VISSIM2020 COM/라이선스, PowerShell7, Python3.12를 사용한다. 아래 경로는 해당 컴퓨터에 맞춘다. 기존 checkout의 미커밋 작업이 있으면 보존하고 별도 clone을 사용한다. 이 안내서는 이미 만들어진 큐를 켜지 않고 **새 결과 폴더에 1회** 실행한다.

```powershell
git clone --single-branch --branch codex/sdmpc31-upstream-20260926 https://github.com/Ming2you/VISSIM.git D:\VISSIM-window264
$repo = 'D:\VISSIM-window264'
$python = 'C:\Path\To\Python312\python.exe' # 실제 Python3.12 경로
$pwsh = (Get-Command pwsh).Source
$deps = 'D:\VISSIM-window264-deps'           # freeze 원본 밖
& $python -m pip install --target $deps -r "$repo\diagnostics\repin_v3c3_review_20261001\vsl_window264\requirements-runtime.txt"
if ($LASTEXITCODE) { throw 'Dependency install failed' }

$freezeLog = & $pwsh -NoProfile -File "$repo\tools\sdmpc31\freeze_worktree.ps1" `
  -Source $repo -FrozenRoot 'D:\VISSIM-runtime-window264' -Python $python
$freezeLog
if ($LASTEXITCODE) { throw 'Freeze failed; do not launch' }
$frz = ($freezeLog | Where-Object { $_ -like 'FRZ=*' } | Select-Object -Last 1).Substring(4)
$out = 'D:\VISSIM-runs-window264-s29-9000' # 기존 시도 없는 새 경로
$runner = "$frz\diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1"
& $pwsh -NoProfile -File $runner -Detached -FrozenTree $frz -ResultsRoot $out `
  -StatusPath "$out\native_status.json" -SimPeriod 9000 -Seed 29 -Arms sdmpc `
  -TuningRelativePath 'diagnostics/repin_v3c3_review_20261001/vsl_window264/config.json' `
  -PythonExe $python -PowerShellExe $pwsh -DependenciesPath $deps
if ($LASTEXITCODE) { throw 'Launch failed; inspect logs, do not automatically retry' }
```

실행 중 로그아웃하지 않는다. `-Detached`는 로그인 사용자의 1회 작업 스케줄러 실행이며 재시작/반복 트리거가 없다. 다른 VISSIM이 열려 있으면 종료하지 않고 시작을 거부한다. `STOP`, 중복 receipt, 소유 PID만 다루는 watchdog, 최초 실제진행300초 제한과 MaxAttempts1을 유지한다. 새 runner에만 Python/PowerShell/패키지 경로 인자를 추가했으며 기존 adapter·watchdog를 그대로 사용한다.

상태는 `$out/native_status.json`, `$out/detached_run.json`, `$out/sdmpc/launch.log`, `$out/sdmpc/runlog_sdmpc31_sdmpc9000_s29.txt`에서 확인한다. `SIM_DONE`/9,000초와 소유 프로세스 종료를 모두 확인해야 완료다. 실행 중 명령표만으로 native 전환 검증을 통과했다고 보지 않는다.

## 포함 범위

현재 받아들인 runtime 수정과 이 설정의 의존 JSON·신호·망은 Git에서 복원 가능하다. 저장 상태 검증에 실제 읽힌 파일과 추가 실행·테스트 입력의 Git 포함 여부를 확인했다. 큰 FZP·NPZ·차량/head 원자료·실행 중 결과는 올리지 않았다. `validation_summary.json`, 소형 검사 결과와 `runtime_files.json`에 확인 범위를 남겼다. 예전 AGENTS/CLAUDE의 현지 큐 지시는 현재 컴퓨터 기록이며 이 신규 원격 실행을 자동으로 시작하라는 지시가 아니다.
