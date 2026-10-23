$ErrorActionPreference='Stop'
$audit=[IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')
$done=Get-Content -LiteralPath (Join-Path $audit 'migration_completion.json') -Raw | ConvertFrom-Json -AsHashtable
if ($done.status -ne 'complete') {throw 'Migration is not complete'}
$owner=Get-Content -LiteralPath (Join-Path $audit 'migration_attempt_2_launch.json') -Raw | ConvertFrom-Json -AsHashtable
$ownerCreated=if ($owner.created_utc -is [DateTime]) {$owner.created_utc.ToUniversalTime()} else {[DateTimeOffset]::Parse([string]$owner.created_utc).UtcDateTime}
$running=Get-Process -Id ([int]$owner.pid) -ErrorAction SilentlyContinue
if ($running -and [math]::Abs(($running.StartTime.ToUniversalTime()-$ownerCreated).TotalMilliseconds) -lt 1) {throw 'Migration owner still running'}
if (Test-Path -LiteralPath (Join-Path $audit 'audit_compression_complete.json')) {throw 'Completed audit compression must be reused'}
function Assert-AuditFile([string]$path) {
    $full=[IO.Path]::GetFullPath($path)
    if (-not $full.StartsWith($audit+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'Outside this audit directory'}
    $walk=Get-Item -LiteralPath $full -Force -ErrorAction SilentlyContinue
    if (-not $walk) {$walk=Get-Item -LiteralPath (Split-Path -Parent $full) -Force}
    while ($walk) {
        if (($walk.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'Reparse path refused'}
        if ($walk -is [IO.FileInfo]) {$walk=$walk.Directory} else {$walk=$walk.Parent}
    }
}
$before=(Get-PSDrive -Name C).Free
$records=@()
foreach ($name in @('migration_plan.json','migration_plan_reviewed.json','migration_journal.jsonl')) {
    $raw=Join-Path $audit $name
    $archive=$raw+'.gz';$temp=$archive+'.partial';$backup=$raw+'.raw_backup'
    foreach ($path in @($raw,$archive,$temp,$backup)) {Assert-AuditFile $path}
    if ((Test-Path -LiteralPath $archive) -or (Test-Path -LiteralPath $temp) -or (Test-Path -LiteralPath $backup)) {throw 'Existing archive attempt; preserve and inspect it'}
    $item=Get-Item -LiteralPath $raw -Force
    if ($item -isnot [IO.FileInfo] -or $item.Length -lt 1000000) {throw 'Unexpected raw audit file'}
    $length=$item.Length;$ticks=$item.LastWriteTimeUtc.Ticks
    $hash=(Get-FileHash -LiteralPath $raw -Algorithm SHA256).Hash.ToLowerInvariant()
    $inputStream=[IO.File]::OpenRead($raw)
    $outputStream=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    $gzip=[IO.Compression.GZipStream]::new($outputStream,[IO.Compression.CompressionLevel]::Optimal,$false)
    try {$inputStream.CopyTo($gzip,1048576)} finally {$inputStream.Dispose();$gzip.Dispose();$outputStream.Dispose()}
    $verifyStream=[IO.File]::OpenRead($temp)
    $inflate=[IO.Compression.GZipStream]::new($verifyStream,[IO.Compression.CompressionMode]::Decompress,$false)
    $hasher=[Security.Cryptography.SHA256]::Create()
    try {$roundtrip=[Convert]::ToHexString($hasher.ComputeHash($inflate)).ToLowerInvariant()} finally {$hasher.Dispose();$inflate.Dispose();$verifyStream.Dispose()}
    if ($roundtrip -ne $hash) {throw 'Archive round-trip hash failed; raw data retained'}
    $now=Get-Item -LiteralPath $raw -Force
    if ($now.Length -ne $length -or $now.LastWriteTimeUtc.Ticks -ne $ticks) {throw 'Raw audit changed during compression'}
    Move-Item -LiteralPath $temp -Destination $archive
    $record=@{schema='vissim-compressed-audit-pointer/v1';event='archived_audit';status='completed_archive_do_not_execute';archive=$archive;uncompressed_sha256=$hash;original_bytes=$length;compressed_bytes=(Get-Item -LiteralPath $archive).Length;compressed_sha256=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant();utc=[DateTime]::UtcNow.ToString('o')}
    Move-Item -LiteralPath $raw -Destination $backup
    [IO.File]::WriteAllText($raw,($record | ConvertTo-Json -Compress)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
    $pointer=Get-Content -LiteralPath $raw -Raw | ConvertFrom-Json -AsHashtable
    if ($pointer.uncompressed_sha256 -ne $hash -or $pointer.archive -ne $archive) {throw 'Pointer validation failed; backup retained'}
    if ((Get-Item -LiteralPath $backup -Force) -isnot [IO.FileInfo]) {throw 'Backup must be an individual audit file'}
    Remove-Item -LiteralPath $backup -Force
    $records+=$record
    $record | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $audit 'audit_compression_journal.jsonl') -Encoding UTF8
}
$result=@{status='complete';records=$records;original_bytes=($records.original_bytes | Measure-Object -Sum).Sum;compressed_bytes=($records.compressed_bytes | Measure-Object -Sum).Sum;drive_c_free_before=$before;drive_c_free_after=(Get-PSDrive -Name C).Free;proof='Every archive was decompressed and SHA256 matched before removing its raw copy. Small pointer files retain the no-repeat guards.'}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $audit 'audit_compression_complete.json') -Encoding UTF8
$result | ConvertTo-Json -Depth 6
