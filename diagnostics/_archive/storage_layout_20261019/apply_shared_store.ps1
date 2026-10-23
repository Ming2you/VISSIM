param(
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$ExpectedSha256,
    [switch]$Execute,
    [switch]$TestFixture
)
$ErrorActionPreference = 'Stop'
$planFile = [IO.Path]::GetFullPath($PlanPath)
if ((Get-FileHash -LiteralPath $planFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ExpectedSha256.ToLowerInvariant()) { throw 'Migration plan changed.' }
$plan = Get-Content -LiteralPath $planFile -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
if ($plan.schema -ne 'vissim-shared-store-migration/v1' -or $plan.status -ne 'planned_not_applied') { throw 'Unexpected migration schema/state.' }
$audit = Split-Path -Parent $planFile
$journalPath = Join-Path $audit 'migration_journal.jsonl'
if (Test-Path -LiteralPath $journalPath) { throw 'Existing migration journal: inspect it; do not repeat.' }
$allowed = @('D:\VISSIM_runs\','E:\VISSIM_runs\','D:\VISSIM_runtime\','E:\VISSIM_runtime\')
$stores = @('D:\VISSIM_shared\','E:\VISSIM_shared\')
if ($TestFixture) {
    $fixtureRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'tests/fixtures')).TrimEnd('\') + '\'
    if (-not $planFile.StartsWith($fixtureRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Fixture must be in the dedicated test root.' }
    $allowed = @($fixtureRoot)
    $stores = @($fixtureRoot)
} else {
    $busy = @(Get-Process | Where-Object { $_.ProcessName -match '^(Vissim|cscript|wscript|robocopy|python|pythonw)$' })
    if ($busy.Count) { throw 'Native or audit process still active; migration refused.' }
}

if (-not ('VissimFileIdentity' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Runtime.InteropServices;
public static class VissimFileIdentity {
 [StructLayout(LayoutKind.Sequential)] struct Info {
   public uint attrs; public System.Runtime.InteropServices.ComTypes.FILETIME created,accessed,written;
   public uint volume,sizeHigh,sizeLow,links,indexHigh,indexLow;
 }
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetFileInformationByHandle(IntPtr h,out Info i);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateHardLinkW(string link,string target,IntPtr security);
 static string LongPath(string path) { return path.StartsWith(@"\\?\") ? path : @"\\?\"+Path.GetFullPath(path); }
 public static void Link(string link,string target) {
   if(!CreateHardLinkW(LongPath(link),LongPath(target),IntPtr.Zero)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
 }
 public static string Get(string path) {
   using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete)) {
     Info i; if(!GetFileInformationByHandle(f.SafeFileHandle.DangerousGetHandle(),out i)) throw new IOException("Cannot read NTFS file identity");
     return i.volume.ToString("x")+":"+i.indexHigh.ToString("x")+":"+i.indexLow.ToString("x");
   }
 }
}
'@
}
$checkedDirs = @{}
function Assert-NoReparse([string]$path) {
    $walkPath = $path
    while (-not (Test-Path -LiteralPath $walkPath)) { $walkPath = Split-Path -Parent $walkPath }
    $item = Get-Item -LiteralPath $walkPath -Force
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse path refused: $path" }
        if ($item -is [IO.FileInfo]) { $item = $item.Directory }
        else {
            if ($checkedDirs.ContainsKey($item.FullName)) { break }
            $checkedDirs[$item.FullName] = $true
            $item = $item.Parent
        }
    }
}
function Assert-Stamp($record) {
    $item = Get-Item -LiteralPath $record.path -Force
    if ($item -isnot [IO.FileInfo] -or $item.Length -ne [int64]$record.bytes -or $item.LastWriteTimeUtc.Ticks -ne [int64]$record.last_write_utc_ticks) { throw "File changed: $($record.path)" }
}
foreach ($pin in $plan.manifest_pins.GetEnumerator()) {
    if ((Get-FileHash -LiteralPath $pin.Key -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.Value) { throw "Manifest changed: $($pin.Key)" }
}
foreach ($group in $plan.groups) {
    $objectPath = [IO.Path]::GetFullPath($group.object)
    if (-not ($stores | Where-Object { $objectPath.StartsWith($_,[StringComparison]::OrdinalIgnoreCase) })) { throw "Outside named stores: $objectPath" }
    if ($group.sha256 -notmatch '^[0-9a-f]{64}$' -or (Split-Path -Leaf $objectPath) -ne $group.sha256) { throw 'Invalid object address.' }
    Assert-NoReparse $objectPath
    Assert-NoReparse $group.anchor.path
    Assert-Stamp $group.anchor
    foreach ($alias in $group.aliases) {
        $full = [IO.Path]::GetFullPath($alias.path)
        $exactRoot = [IO.Path]::GetFullPath($alias.allowed_root).TrimEnd('\') + '\'
        if (-not ($allowed | Where-Object { $exactRoot.StartsWith($_,[StringComparison]::OrdinalIgnoreCase) }) -or -not $full.StartsWith($exactRoot,[StringComparison]::OrdinalIgnoreCase)) { throw "Outside exact named experiment root: $full" }
        if ([IO.Path]::GetPathRoot($full) -ne [IO.Path]::GetPathRoot($objectPath)) { throw 'Hardlink cannot cross volumes.' }
        Assert-NoReparse $full
        if ($alias.exists) { Assert-Stamp $alias }
        elseif (Test-Path -LiteralPath $full) { throw "Previously removed path reappeared: $full" }
    }
}
if (-not $Execute) {
    @{status='validated_no_mutation';groups=@($plan.groups).Count;existing_aliases=$plan.existing_aliases;restore_aliases=$plan.restore_aliases} | ConvertTo-Json
    exit 0
}
$before = @(Get-PSDrive -Name C,D,E -ErrorAction SilentlyContinue | Select-Object Name,Free,Used)
$log = [IO.StreamWriter]::new($journalPath,$false,[Text.UTF8Encoding]::new($false))
$log.AutoFlush = $true
$converted = 0; $restored = 0; $objects = 0
try {
    foreach ($group in $plan.groups) {
        Assert-Stamp $group.anchor
        $objectPath = [IO.Path]::GetFullPath($group.object)
        $objectParent = Split-Path -Parent $objectPath
        if (-not (Test-Path -LiteralPath $objectParent)) { New-Item -ItemType Directory -Path $objectParent | Out-Null }
        if (Test-Path -LiteralPath $objectPath) {
            if ((Get-FileHash -LiteralPath $objectPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $group.sha256) { throw 'Existing object is corrupt.' }
        } elseif ($group.anchor.copy_required) {
            Copy-Item -LiteralPath $group.anchor.path -Destination $objectPath
            if ((Get-FileHash -LiteralPath $objectPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $group.sha256) { throw 'Copied object is corrupt.' }
        } else {
            [VissimFileIdentity]::Link($objectPath,$group.anchor.path)
            if ([VissimFileIdentity]::Get($objectPath) -ne [VissimFileIdentity]::Get($group.anchor.path)) { throw 'Anchor link identity mismatch.' }
        }
        $objectId = [VissimFileIdentity]::Get($objectPath)
        (Get-Item -LiteralPath $objectPath -Force).IsReadOnly = $true
        $objects++
        foreach ($alias in $group.aliases) {
            $full = [IO.Path]::GetFullPath($alias.path)
            if ($alias.exists) {
                Assert-Stamp $alias
                if ([VissimFileIdentity]::Get($full) -eq $objectId) { continue }
            } elseif (Test-Path -LiteralPath $full) { throw 'Unexpected alias appeared.' }
            $backup = $full + '.cas_old_' + [Guid]::NewGuid().ToString('N')
            if (Test-Path -LiteralPath $backup) { throw 'Backup collision.' }
            $log.WriteLine((@{event='prepared';path=$full;object=$objectPath;backup=$backup;existed=$alias.exists;sha256=$group.sha256;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress))
            if ($alias.exists) { Move-Item -LiteralPath $full -Destination $backup }
            try {
                [VissimFileIdentity]::Link($full,$objectPath)
                if ([VissimFileIdentity]::Get($full) -ne $objectId) { throw 'Alias identity mismatch.' }
            } catch {
                if (-not (Test-Path -LiteralPath $full) -and (Test-Path -LiteralPath $backup)) { Move-Item -LiteralPath $backup -Destination $full }
                throw
            }
            if ($alias.exists) {
                if ((Get-Item -LiteralPath $backup -Force) -isnot [IO.FileInfo]) { throw 'Backup must be an individual file.' }
                Remove-Item -LiteralPath $backup -Force
                $converted++
            } else { $restored++ }
            $log.WriteLine((@{event='linked_verified';path=$full;object=$objectPath;identity=$objectId;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress))
        }
        if (($objects % 100) -eq 0) { Write-Output "Shared objects $objects; replaced physical copies $converted; restored paths $restored" }
    }
} finally { $log.Dispose() }
$after = @(Get-PSDrive -Name C,D,E -ErrorAction SilentlyContinue | Select-Object Name,Free,Used)
$result = @{status='complete';utc=[DateTime]::UtcNow.ToString('o');objects=$objects;converted_copies=$converted;restored_paths=$restored;before_drives=$before;after_drives=$after;plan_sha256=$ExpectedSha256;journal=$journalPath;method='Read-only same-volume NTFS hardlinks, verified by file identity. No unique data removed.';native_launches=0}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $audit 'migration_completion.json') -Encoding UTF8
$result | ConvertTo-Json -Depth 8
