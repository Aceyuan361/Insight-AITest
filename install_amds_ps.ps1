# Apple Mobile Device Support 自动安装脚本
$ErrorActionPreference = "Stop"

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "Apple Mobile Device Support 安装工具" -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# 创建临时目录
$tempDir = Join-Path $env:TEMP "iTunes_Installer_$(Get-Random)"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
Write-Host "[临时目录] $tempDir" -ForegroundColor Gray

try {
    # 方法1: 尝试从苹果官网下载
    Write-Host ""
    Write-Host "[1/4] 正在下载 iTunes 安装包..." -ForegroundColor Yellow
    Write-Host "下载地址: https://www.apple.com/itunes/download/win64" -ForegroundColor Gray

    $installerPath = Join-Path $tempDir "iTunes64Setup.exe"

    # 使用 ProgressPreference 加速下载
    $ProgressPreference = 'SilentlyContinue'
    Invoke-WebRequest -Uri "https://www.apple.com/itunes/download/win64" -OutFile $installerPath -UseBasicParsing
    $ProgressPreference = 'Continue'

    if (Test-Path $installerPath) {
        $fileSize = (Get-Item $installerPath).Length / 1MB
        Write-Host "[成功] 下载完成 ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green

        # 方法2: 使用 7-Zip 解压（如果安装了）
        Write-Host ""
        Write-Host "[2/4] 正在解压安装包..." -ForegroundColor Yellow

        $extractDir = Join-Path $tempDir "Extracted"
        New-Item -ItemType Directory -Path $extractDir -Force | Out-Null

        # 检查是否安装了 7-Zip
        $sevenZip = "C:\Program Files\7-Zip\7z.exe"
        if (Test-Path $sevenZip) {
            Write-Host "[解压] 使用 7-Zip..." -ForegroundColor Gray
            & $sevenZip x $installerPath -o"$extractDir" -y | Out-Null
        } else {
            Write-Host "[解压] 使用内置命令..." -ForegroundColor Gray
            # 尝试直接运行安装程序并提取
            Start-Process -FilePath $installerPath -ArgumentList "/extract:`"$extractDir`"" -Wait
        }

        # 查找 MSI 文件
        Write-Host ""
        Write-Host "[3/4] 查找驱动组件..." -ForegroundColor Yellow

        $msiFile = Get-ChildItem -Path $extractDir -Recurse -Filter "AppleMobileDeviceSupport*.msi" -ErrorAction SilentlyContinue | Select-Object -First 1

        if ($msiFile) {
            Write-Host "[找到] $($msiFile.Name)" -ForegroundColor Green

            # 安装驱动
            Write-Host ""
            Write-Host "[4/4] 正在安装 Apple Mobile Device Support..." -ForegroundColor Yellow

            $installArgs = @(
                "/i",
                "`"$($msiFile.FullName)`"",
                "/qb",  # 静默安装
                "/norestart"
            )

            $process = Start-Process -FilePath "msiexec.exe" -ArgumentList $installArgs -Wait -PassThru

            if ($process.ExitCode -eq 0) {
                Write-Host ""
                Write-Host "========================================" -ForegroundColor Green
                Write-Host "安装成功！" -ForegroundColor Green
                Write-Host "========================================" -ForegroundColor Green
                Write-Host ""
                Write-Host "下一步操作:" -ForegroundColor Cyan
                Write-Host "1. 重新连接 iOS 设备" -ForegroundColor White
                Write-Host "2. 运行: tidevice list" -ForegroundColor White
                Write-Host ""
            } else {
                throw "安装失败，退出码: $($process.ExitCode)"
            }
        } else {
            Write-Host "[未找到] AppleMobileDeviceSupport.msi" -ForegroundColor Red
            Write-Host ""
            Write-Host "备选方案:" -ForegroundColor Yellow
            Write-Host "1. 手动打开文件夹并查找 MSI 文件: $extractDir" -ForegroundColor White
            Write-Host "2. 或安装完整 iTunes" -ForegroundColor White
        }
    } else {
        throw "下载失败"
    }
} catch {
    Write-Host ""
    Write-Host "[错误] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "备选方案:" -ForegroundColor Yellow
    Write-Host "1. 手动下载 iTunes: https://www.apple.com/itunes/download/win64" -ForegroundColor White
    Write-Host "2. 使用此链接提取独立驱动:" -ForegroundColor White
    Write-Host "   https://support.apple.com/kb/DL8371" -ForegroundColor White
    Write-Host ""
} finally {
    # 询问是否清理临时文件
    Write-Host "临时文件保留在: $tempDir" -ForegroundColor Gray
    Write-Host "安装完成后可手动删除" -ForegroundColor Gray
    Write-Host ""
}
