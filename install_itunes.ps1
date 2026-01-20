$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'

Write-Host "=== iTunes + Driver Installer ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will install iTunes (including the driver)." -ForegroundColor Yellow
Write-Host "You can uninstall iTunes later if needed." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to cancel, or" -ForegroundColor Red
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

$tempDir = Join-Path $env:TEMP "iTunes_Installer_$(Get-Random)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host ""
    Write-Host "[1/2] Downloading iTunes..." -ForegroundColor Yellow
    $installerPath = Join-Path $tempDir "iTunes64Setup.exe"

    Invoke-WebRequest -Uri "https://www.apple.com/itunes/download/win64" -OutFile $installerPath -UseBasicParsing

    $fileSize = (Get-Item $installerPath).Length / 1MB
    Write-Host "[OK] Downloaded ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green

    Write-Host ""
    Write-Host "[2/2] Installing iTunes and drivers..." -ForegroundColor Yellow
    Write-Host "This will open the installer window." -ForegroundColor Gray
    Write-Host ""

    Start-Process -FilePath $installerPath -Wait

    Write-Host ""
    Write-Host "=== Installation Complete ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Check if Apple Mobile Device Support is installed:" -ForegroundColor White
    Write-Host "   reg query `"HKLM\SOFTWARE\Apple Inc.\Apple Mobile Device Support`"" -ForegroundColor Gray
    Write-Host "2. Reconnect your iOS device" -ForegroundColor White
    Write-Host "3. Run: tidevice list" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
}
