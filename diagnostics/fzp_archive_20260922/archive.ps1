param([ValidateSet('Plan','Move')][string]$Mode = 'Plan')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')).TrimEnd('\')
$archive = 'E:\VISSIM_archive\20260922_fzp_1s\control-full-review'
$planPath = Join-Path $PSScriptRoot 'plan.json'
if ((Split-Path $root -Leaf) -ne 'control-full-review') { throw 'Wrong worktree' }
function Assert-InTree([string]$path, [string]$tree) {
    $full = [IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($tree.TrimEnd('\')+'\', [StringComparison]::OrdinalIgnoreCase)) { throw "Outside scope: $path" }
    $p = $full
    while ($p) {
        if ((Test-Path -LiteralPath $p) -and ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Reparse point: $p" }
        $parent = Split-Path $p -Parent
        if (-not $parent -or $parent -eq $p) { break }
        $p = $parent
    }
}
function Sample-Times([string]$path, [long]$offset) {
    $stream = [IO.File]::Open($path, 'Open', 'Read', 'ReadWrite')
    $reader = $null
    try {
        [void]$stream.Seek($offset, 'Begin')
        $reader = [IO.StreamReader]::new($stream)
        if ($offset -gt 0) { [void]$reader.ReadLine() }
        $times = [Collections.Generic.List[double]]::new()
        for ($i=0; $i -lt 150000 -and $times.Count -lt 8; $i++) {
            $line = $reader.ReadLine()
            if ($null -eq $line) { break }
            if ($line -match '^\s*(\d+(?:\.\d+)?)\s*;') {
                $t = [double]::Parse($Matches[1], [Globalization.CultureInfo]::InvariantCulture)
                if ($times.Count -eq 0 -or $t -ne $times[$times.Count-1]) { $times.Add($t) }
            }
        }
        return ,$times.ToArray()
    } finally { if ($reader) { $reader.Dispose() }; $stream.Dispose() }
}
function Write-Json($value, [string]$path) {
    $value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $path -Encoding utf8
}
if ($Mode -eq 'Plan') {
    if (Test-Path -LiteralPath $planPath) { throw 'Plan already exists' }
    Push-Location $root
    try {
        $paths = @(rg --files --hidden --no-ignore -g '*.fzp' -g '!**/.git/**' -g '!**/.plot_deps/**' -g '!**/.plot-deps/**' -g '!**/.review-deps/**' -g '!**/.review_deps/**' -g '!**/node_modules/**' -g '!**/.venv/**')
        if ($LASTEXITCODE -ne 0) { throw 'Incomplete inventory' }
        $tracked = @(git -c core.quotepath=false ls-files '*.fzp')
        if ($LASTEXITCODE -ne 0) { throw 'Cannot identify tracked files' }
    } finally { Pop-Location }
    $rows = @($paths | Sort-Object | ForEach-Object {
        $rel = $_.Replace('/', '\'); $path = Join-Path $root $rel
        Assert-InTree $path $root
        $f = Get-Item -LiteralPath $path
        $samples = @()
        if ($f.Length -ge 1MB) {
            foreach ($offset in @(0, [long]($f.Length/2), [Math]::Max([long]0, [long]($f.Length-4MB)))) {
                $ts = Sample-Times $path $offset
                $diffs = @(); for ($i=1; $i -lt $ts.Count; $i++) { $diffs += [Math]::Round($ts[$i]-$ts[$i-1], 5) }
                $samples += [pscustomobject]@{Offset=$offset;Times=$ts;Diffs=$diffs}
            }
        }
        $one = $samples.Count -eq 3
        foreach ($s in $samples) { if ($s.Diffs.Count -lt 1 -or @($s.Diffs | Where-Object { $_ -ne 1 }).Count -gt 0) { $one=$false } }
        $reason = if ($tracked -contains $rel.Replace('\','/')) {'tracked_fixture'} elseif ($f.Length -lt 1MB) {'small_fixture_or_sample'} elseif ($one) {'confirmed_1s_at_start_middle_end'} else {'non_1s_or_uncertain_interval'}
        if ($f.LastWriteTimeUtc -gt [DateTime]::UtcNow.AddMinutes(-10)) { $reason='recently_written_preserve' }
        [pscustomobject]@{RelativePath=$rel;Source=$path;Destination=(Join-Path $archive $rel);Bytes=$f.Length;MtimeTicks=$f.LastWriteTimeUtc.Ticks;Action=$(if ($reason -eq 'confirmed_1s_at_start_middle_end') {'archive'} else {'preserve'});Reason=$reason;Samples=$samples}
    })
    $plan = [ordered]@{CreatedUtc=[DateTime]::UtcNow.ToString('o');Root=$root;Archive=$archive;Policy='Only confirmed old 1-second FZP recordings. Preserve small fixtures and all non-FZP results. Copy, verify SHA256, then remove exact C source. No simulation-resolution change.';Rows=$rows}
    Write-Json $plan $planPath
    $rows | Group-Object Action,Reason | ForEach-Object { [pscustomobject]@{Group=$_.Name;Count=$_.Count;GB=([Math]::Round(($_.Group | Measure-Object Bytes -Sum).Sum/1e9,3))} } | ConvertTo-Json
    exit
}
$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if ($plan.Root -ne $root -or $plan.Archive -ne $archive) { throw 'Manifest scope changed' }
$move = @($plan.Rows | Where-Object Action -eq 'archive')
$total = ($move | Measure-Object Bytes -Sum).Sum
if ((Get-PSDrive E).Free -lt $total+2GB) { throw 'Insufficient E space' }
[Diagnostics.Process]::GetCurrentProcess().PriorityClass = 'Idle'
Assert-InTree (Join-Path $archive 'plan.json') 'E:\VISSIM_archive'
[void](New-Item -ItemType Directory -Path $archive -Force)
Copy-Item -LiteralPath $planPath -Destination (Join-Path $archive 'plan.json') -Force
$receiptPath = Join-Path $PSScriptRoot 'moved.jsonl'
$count=0; [long]$bytes=0; $started=[DateTime]::UtcNow
foreach ($row in $move) {
    Assert-InTree $row.Source $root; Assert-InTree $row.Destination $archive
    if ([IO.Path]::GetExtension($row.Source) -ne '.fzp') { throw 'Not FZP' }
    if (-not (Test-Path -LiteralPath $row.Source)) { throw "Source absent; inspect receipt before resuming: $($row.Source)" }
    $f=Get-Item -LiteralPath $row.Source
    if ($f.Length -ne $row.Bytes -or $f.LastWriteTimeUtc.Ticks -ne $row.MtimeTicks) { throw "Source changed: $($row.Source)" }
    $partial=$row.Destination+'.partial'
    if ((Test-Path -LiteralPath $row.Destination) -or (Test-Path -LiteralPath $partial)) { throw "Destination exists: $($row.Destination)" }
    [void](New-Item -ItemType Directory -Path (Split-Path $row.Destination -Parent) -Force)
    $source=[IO.File]::Open($row.Source,'Open','Read','Read')
    try {
        $dest=[IO.File]::Open($partial,'CreateNew','Write','None')
        try { $source.CopyTo($dest, 4MB); $dest.Flush($true) } finally { $dest.Dispose() }
        $source.Position=0
        $sha=[Security.Cryptography.SHA256]::Create()
        try { $sourceHash=[Convert]::ToHexString($sha.ComputeHash($source)).ToLowerInvariant() } finally { $sha.Dispose() }
        $destHash=(Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($sourceHash -ne $destHash -or (Get-Item -LiteralPath $partial).Length -ne $row.Bytes) { throw 'Copy verification failed; C source retained' }
    } finally { $source.Dispose() }
    $f=Get-Item -LiteralPath $row.Source
    if ($f.Length -ne $row.Bytes -or $f.LastWriteTimeUtc.Ticks -ne $row.MtimeTicks) { throw 'Source changed before deletion' }
    Move-Item -LiteralPath $partial -Destination $row.Destination
    [IO.File]::SetLastWriteTimeUtc($row.Destination, [DateTime]::new([long]$row.MtimeTicks, [DateTimeKind]::Utc))
    $receipt=[ordered]@{Source=$row.Source;Destination=$row.Destination;Bytes=$row.Bytes;SHA256=$sourceHash;VerifiedUtc=[DateTime]::UtcNow.ToString('o');Phase='verified_before_delete'}
    ($receipt | ConvertTo-Json -Compress) | Add-Content -LiteralPath $receiptPath -Encoding utf8
    Remove-Item -LiteralPath $row.Source
    if (Test-Path -LiteralPath $row.Source) { throw 'Source deletion failed' }
    $receipt.Phase='moved'; ($receipt | ConvertTo-Json -Compress) | Add-Content -LiteralPath $receiptPath -Encoding utf8
    $count++; $bytes += $row.Bytes
    Write-Json ([ordered]@{Status='running';Completed=$count;Planned=$move.Count;Bytes=$bytes;UpdatedUtc=[DateTime]::UtcNow.ToString('o');Last=$row.RelativePath}) (Join-Path $PSScriptRoot 'status.json')
    Write-Output ("{0}/{1} archived; {2:N2} GB" -f $count,$move.Count,($bytes/1e9))
}
$preserved=0
foreach ($row in @($plan.Rows | Where-Object Action -eq 'preserve')) {
    $f=Get-Item -LiteralPath $row.Source
    if ($f.Length -ne $row.Bytes -or $f.LastWriteTimeUtc.Ticks -ne $row.MtimeTicks) { throw "Preserved file changed: $($row.Source)" }
    $preserved++
}
Copy-Item -LiteralPath $receiptPath -Destination (Join-Path $archive 'moved.jsonl') -Force
$summary=[ordered]@{Status='complete';Moved=$count;Bytes=$bytes;Preserved=$preserved;Archive=$archive;SHA256Verified=$count;StartedUtc=$started.ToString('o');CompletedUtc=[DateTime]::UtcNow.ToString('o');CFreeBytes=(Get-PSDrive C).Free;EFreeBytes=(Get-PSDrive E).Free}
Write-Json $summary (Join-Path $PSScriptRoot 'status.json')
Write-Json $summary (Join-Path $archive 'status.json')
$summary | ConvertTo-Json
