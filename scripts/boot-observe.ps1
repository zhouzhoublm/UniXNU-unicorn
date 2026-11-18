# Observe USB VID/PID during a UniXNU bring-up boot.
# Read-only: this script only queries PnP devices; it never writes to the phone.
# Rationale: 'adb devices' reports ghost devices while the board is in UEFI.
# A USB VID/PID timeline is the reliable way to tell firmware states apart.
#
# Usage (PowerShell):
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\boot-observe.ps1 ^
#       -Seconds 120 -Interval 5 -OutFile evidence\boot-usb.csv
param(
    [int]$Seconds = 120,
    [int]$Interval = 5,
    [string]$OutFile = "boot-usb.csv",
    [string]$Pattern = "VID_18D1&PID_4EE7|VID_05C6&PID_F000|VID_1209&PID_0001"
)

$ErrorActionPreference = "SilentlyContinue"
if ($Interval -lt 1) { $Interval = 1 }
$deadline = (Get-Date).AddSeconds($Seconds)
$rows = New-Object System.Collections.Generic.List[string]
$rows.Add("elapsed_s,usb_devices")
Write-Host "Observing USB for $Seconds seconds, sample every $Interval s"
Write-Host "Patterns: $Pattern"

while ((Get-Date) -lt $deadline) {
    $elapsed = [int]((Get-Date) - ($deadline.AddSeconds(-$Seconds))).TotalSeconds
    $ids = @()
    $devices = Get-PnpDevice -Class USB
    foreach ($d in $devices) {
        $iid = [string]$d.InstanceId
        if ($iid -match $Pattern) { $ids += $iid }
    }
    $line = "{0},{1}" -f $elapsed, ($ids -join ";")
    $rows.Add($line)
    Write-Host $line
    Start-Sleep -Seconds $Interval
}

$dir = Split-Path -Parent $OutFile
if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}
$full = [System.IO.Path]::GetFullPath($OutFile)
[System.IO.File]::WriteAllLines($full, $rows)
Write-Host "Saved: $full"
