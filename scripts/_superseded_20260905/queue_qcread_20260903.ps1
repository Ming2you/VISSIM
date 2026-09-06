<#
2026-09-03. 큐 카운터 읽기 전용 풀런 — 대조 자료 확보.

## 왜 읽기만 하나

오늘 세 팔이 전부 악화했다 (기준선 arm_rampclean 8339.0):
    arm_window  관측만 고침        +671.3
    arm_refine  탐색 해상도        +728.9
    arm_ingne   배분 자유도        +996.2   (p1 28.0 -> 40.0 으로 고착은 풀렸다)
    arm_nobeta  덜 반응하게        -386.1   <- 유일하게 이김

관측이 4.7~6.8배 왜곡된 상태에서 배분기를 '더 잘하게' 만들면 왜곡을 더 충실히 따라간다.
arm_ingne 의 p2 가 그 증거다 — 관측 66.4(실제 27.6, 편향 2.41배)를 믿고 28.7 -> 52.6초.
그래서 관측을 먼저 바로잡고, 그 위에서 배분을 다시 재야 한다(사용자 지시).

이 런은 **제어를 안 바꾼다**. 카운터를 읽어 상태 JSON 에 싣기만 한다.
어댑터는 여전히 파생 큐를 쓴다. 위험 0 이고 대조 자료만 얻는다.

## 내장 검증

제어가 비트 동일이므로 **arm_rampclean 의 8339.0 을 재현해야 한다.**
재현하면 (a) 카운터 추가가 시뮬을 안 흔든다 (b) 파이프라인이 결정론적이다 가 같이 확인된다.
벗어나면 망 편집이나 VBS 수정이 뭔가를 건드린 것이니 먼저 그걸 잡아야 한다.

## 스모크에서 이미 확인된 것

  카운터 읽기 686/686 성공 (표기 QLen(Current,Last) — 차종 차원 없음)
  램프 카운터 8개 = 0.0 이고 **그게 맞다**:
     .fzp 지상검증 미터 커넥터 정지차 0.0~0.7%, 평균속도 38~55 kph (미터 1800 개방)
     그런데 파생 관측은 같은 구간에 R_F_W 12.0 · R_D_W 5.0 을 '램프 큐' 로 보고
     = 재차 시간평균(12.5 · 6.2)과 일치 -> **우리는 큐가 아니라 재차를 세고 있다**
  진짜 대기는 미터 앞이 아니라 피더 링크 32 (정지 25.0% · 카운터 2012 QLen 62.1)

## 이 런에서 볼 것

  1 미터가 닫히는 구간 (앞선 런에서 R_D_W 22/37 결정 완전폐쇄) 에서 램프 카운터가 뜨는가
  2 도시 카운터 대 파생 큐: 결정시점 편향 4.7배가 실제로 사라지는가
  3 SC105 p1~p4 를 카운터로 보면 배분 근거가 어떻게 달라지는가
#>
param([int]$Seed = 13)
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_QUEUE_COUNTER = "1"
foreach ($v in @("RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG","RW_FORCE_STEPWISE",
                 "RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_MOVEMENT_PHASE_CORRECTION","RW_NARROW_AXIS_SG",
                 "RW_VALIDATION_FIXED_SIGNAL")) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
for ($i=0; $i -lt 60; $i++) { if (@(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count -eq 0) { break }; Start-Sleep -Seconds 20 }
$name = "qcread_x18_20260903"
Write-Output ("[{0}] {1} 시작 — 읽기 전용. 제어 비트 동일이므로 8339.0 을 재현해야 한다." -f (Get-Date -Format "HH:mm:ss"), $name)
& (Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1") `
    -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_outflow_d00_x18_20260901.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
