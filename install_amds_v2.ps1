$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'

Write-Host "=== Apple Mobile Device Support Installer ===" -ForegroundColor Cyan
Write-Host ""

$tempDir = Join-Path $env:TEMP "iTunes_Installer_$(Get-Random)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

try {
    Write-Host "[1/4] Downloading iTunes setup..." -ForegroundColor Yellow
    $installerPath = Join-Path $tempDir "iTunes64Setup.exe"

    Invoke-WebRequest -Uri "https://www.apple.com/itunes/download/win64" -OutFile $installerPath -UseBasicParsing

    $fileSize = (Get-Item $installerPath).Length / 1MB
    Write-Host "[OK] Downloaded ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green

    Write-Host ""
    Write-Host "[2/4] Extracting installer..." -ForegroundColor Yellow

    $extractDir = Join-Path $tempDir "Extracted"
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

    $sevenZip = "C:\Program Files\7-Zip\7z.exe"
    if (Test-Path $sevenZip) {
        & $sevenZip x $installerPath -o"$extractDir" -y | Out-Null
    } else {
        Start-Process -FilePath $installerPath -ArgumentList "/extract=`"$extractDir`"" -Wait
    }

    Write-Host ""
    Write-Host "[3/4] Searching for driver MSI..." -ForegroundColor Yellow

    $msiFile = Get-ChildItem -Path $extractDir -Recurse -Filter "AppleMobileDeviceSupport*.msi" -ErrorAction SilentlyContinue | Select-Object -First 1

    if ($msiFile) {
        Write-Host "[OK] Found: $($msiFile.Name)" -ForegroundColor Green

        Write-Host ""
        Write-Host "[4/4] Installing driver..." -ForegroundColor Yellow

        $process = Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$($msiFile.FullName)`" /qb /norestart" -Wait -PassThru

        if ($process.ExitCode -eq 0) {
            Write-Host ""
            Write-Host "=== Installation Successful ===" -ForegroundColor Green
            Write-Host ""
            Write-Host "Next steps:" -ForegroundColor Cyan
            Write-Host "1. Reconnect your iOS device" -ForegroundColor White
            Write-Host "2. Run: tidevice list" -ForegroundColor White
            Write-Host ""
        } else {
            Write-Host "[ERROR] Installation failed. Code: $($process.ExitCode)" -ForegroundColor Red
        }
    } else {
        Write-Host "[ERROR] Driver MSI not found" -ForegroundColor Red
        Write-Host "Extracted location: $extractDir" -ForegroundColor Yellow
    }

} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual download: https://www.apple.com/itunes/download/win64" -ForegroundColor Yellow
}

Write-Host "Temp files: $tempDir" -ForegroundColor Gray
