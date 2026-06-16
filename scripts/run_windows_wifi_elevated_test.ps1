$ErrorActionPreference = "Continue"

$Repo = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Repo "logs"
$LogPath = Join-Path $LogDir "windows_wifi_elevated_test.log"
$Python = Join-Path $Repo ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $Repo

Start-Transcript -Path $LogPath -Force

Write-Host "ezShareCPAP elevated Windows Wi-Fi test"
Write-Host "Repo: $Repo"
Write-Host "Log:  $LogPath"
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "Python virtual environment not found at $Python"
    Stop-Transcript
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Running platform Wi-Fi unit tests..."
& $Python -m unittest tests.test_platform_wifi -v

Write-Host ""
Write-Host "Running live Windows Wi-Fi connect test for SSID 'ez Share'..."

Write-Host ""
Write-Host "Network state before live test:"
ipconfig
route print 192.168.4.1

$code = @'
import requests
from wifi_utils import ConnectionManager

m = ConnectionManager()
try:
    print("find", m.find_wifi_interface(), m.interface)
    m._connect_windows("ez Share", "88888888")
    print("connect ok")
    m._ensure_windows_host_route("192.168.4.1")
    print("host route ensured", m.windows_host_route)
    print("verify", m.verify_connection(max_attempts=5))
    print("http root check starting")
    response = requests.get("http://192.168.4.1/", timeout=15)
    print("root status", response.status_code)
    print("root preview", response.text[:300].replace("\r", "\\r").replace("\n", "\\n"))
    print("directory check starting")
    response = requests.get("http://192.168.4.1/dir?dir=A:", timeout=15)
    print("directory status", response.status_code)
    print("directory preview", response.text[:500].replace("\r", "\\r").replace("\n", "\\n"))
finally:
    if m.interface:
        print("leaving Wi-Fi connected for PowerShell diagnostics")
'@

$code | & $Python -

Write-Host ""
Write-Host "Network state while connected:"
ipconfig
route print 192.168.4.1
arp -a
Test-NetConnection 192.168.4.1 -Port 80 -InformationLevel Detailed

Write-Host ""
Write-Host "Disconnecting Wi-Fi after diagnostics..."
$wifiAdapter = Get-NetAdapter -Name "Wi-Fi" -ErrorAction SilentlyContinue
if ($wifiAdapter) {
    Get-NetRoute -DestinationPrefix "192.168.4.1/32" -ErrorAction SilentlyContinue |
        Where-Object { $_.InterfaceIndex -eq $wifiAdapter.ifIndex -and $_.NextHop -eq "0.0.0.0" } |
        Remove-NetRoute -Confirm:$false
}
netsh wlan disconnect interface="Wi-Fi"

Write-Host ""
Write-Host "Saved Wi-Fi profiles after test:"
netsh wlan show profiles

Stop-Transcript
Write-Host ""
Write-Host "Done. Results were written to $LogPath"
Read-Host "Press Enter to close"
