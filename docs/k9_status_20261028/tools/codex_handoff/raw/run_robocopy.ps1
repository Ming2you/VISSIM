# Copy the codex handoff folder from the shared drive (read only) to the local copy root, excluding sealed/.
# Launched detached via WMI Win32_Process.Create with BELOW_NORMAL priority; robocopy inherits it.
$src = 'Y:\99_임시휴지통\20261024'
$dst = 'D:\VISSIM_handoff\20261024'
$raw = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\raw'
$log = Join-Path $raw 'robocopy_20261025.log'
$state = Join-Path $raw 'robocopy_state.json'
$rargs = @($src, $dst, '/E', '/XD', 'sealed', '/COPY:DAT', '/DCOPY:T', '/R:3', '/W:10', '/MT:8', '/NP', '/BYTES', '/XJ', "/UNILOG:$log")
$cmdline = 'robocopy.exe ' + (($rargs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' ')
$start = Get-Date
$s = [ordered]@{ wrapper_pid = $PID; priority = (Get-Process -Id $PID).PriorityClass.ToString(); command = $cmdline;
                 start = $start.ToString('yyyy-MM-dd HH:mm:ss.fff zzz'); status = 'running' }
($s | ConvertTo-Json) | Set-Content -Encoding UTF8 -LiteralPath $state
& robocopy.exe @rargs | Out-Null
$code = $LASTEXITCODE
$end = Get-Date
$s.status = 'done'
$s.exit_code = $code
$s.end = $end.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
$s.seconds = [math]::Round(($end - $start).TotalSeconds, 1)
($s | ConvertTo-Json) | Set-Content -Encoding UTF8 -LiteralPath $state
