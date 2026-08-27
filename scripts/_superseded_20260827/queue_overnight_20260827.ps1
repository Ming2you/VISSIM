<#
2026-08-27 밤샘 큐.
  0) plantfix_20260827 (B) 종료 대기
  1) 증량 망 4종의 **무제어** 런 — 2개씩 동시 (각 ~11분, 총 ~25분)
     fw12_ramp1 · fw12_ramp2 · fw14_ramp1 · fw14_ramp2
     첫 런이 망 검증을 겸한다 — relFlow 만 바꿨으니 경로는 안 깨졌을 것이나
     깨졌으면 1분 안에 실패한다.
  2) TTT 비교표와 세그먼트 밀도 요약 출력

제어 런은 여기 안 넣는다 — FD 재적합이 먼저이고 그건 판단이 필요하다.
#>
$ErrorActionPreference = "Continue"
$repo = "C:/Users/TRLAB/Desktop/찐찐막/VISSIM"
$py = "C:/ProgramData/Anaconda3/python.exe"
$launch = Join-Path $repo "scripts/launch_nc_variant_20260827.ps1"

Write-Output ("[{0}] (B) plantfix_20260827 종료 대기" -f (Get-Date -Format "HH:mm:ss"))
$prog = Join-Path $repo "evaluation/runs/plantfix_20260827/WATCHDOG_PROGRESS.txt"
for ($i = 0; $i -lt 200; $i++) {
  if (Test-Path $prog) {
    $txt = Get-Content $prog -Raw -ErrorAction SilentlyContinue
    if ($txt -match "OK plantfix_20260827" -or $txt -match "FAIL plantfix_20260827") { break }
  }
  Start-Sleep -Seconds 60
}
Write-Output ("[{0}] (B) 종료 확인 · 무제어 스윕 시작" -f (Get-Date -Format "HH:mm:ss"))
Start-Sleep -Seconds 20

$pairs = @(
  @(@("network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw12_ramp1.inpx","fw12_ramp1"),
    @("network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw14_ramp1.inpx","fw14_ramp1")),
  @(@("network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw12_ramp2.inpx","fw12_ramp2"),
    @("network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw14_ramp2.inpx","fw14_ramp2"))
)
foreach ($pair in $pairs) {
  $jobs = @()
  foreach ($arm in $pair) {
    $log = Join-Path $repo ("evaluation/runs/nc_" + $arm[1] + "_launch.log")
    $p = Start-Process -FilePath "powershell.exe" -PassThru -WindowStyle Hidden -ArgumentList @(
      "-NoProfile","-ExecutionPolicy","Bypass","-File",$launch,"-Net",$arm[0],"-Tag",$arm[1]) `
      -RedirectStandardOutput $log -RedirectStandardError ($log + ".err")
    $jobs += $p
    Write-Output ("  발사 {0} (pid {1})" -f $arm[1], $p.Id)
    Start-Sleep -Seconds 15
  }
  foreach ($j in $jobs) { $j.WaitForExit() }
  Write-Output ("[{0}] 쌍 완료" -f (Get-Date -Format "HH:mm:ss"))
}

Write-Output "=========================================================="
Write-Output "무제어 TTT 비교"
& $py (Join-Path $repo 'scripts/compare_runs_ttt.py') `
    nocontrol_s13_20260824 nc_fw12_ramp1_20260827 nc_fw12_ramp2_20260827 `
    nc_fw14_ramp1_20260827 nc_fw14_ramp2_20260827 `
    --base nocontrol_s13_20260824
Write-Output ("[{0}] 밤샘 큐 종료" -f (Get-Date -Format "HH:mm:ss"))
