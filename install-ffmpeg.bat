@echo off
chcp 65001 >nul
echo ============================================================
echo Установка FFmpeg для FFmpegGUI
echo ============================================================
echo.

:: Создаём папку установки
set "INSTALL_DIR=%USERPROFILE%\FFmpegGUI\ffmpeg"
echo Создание папки: %INSTALL_DIR%
mkdir "%INSTALL_DIR%" 2>nul
if exist "%INSTALL_DIR%" (
    echo [OK] Папка создана
) else (
    echo [ERROR] Не удалось создать папку
    pause
    exit /b 1
)
echo.

:: Скачиваем FFmpeg
echo Скачивание FFmpeg...
echo URL: https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip
echo.

powershell -Command "& {
    $ProgressPreference = 'SilentlyContinue'
    $url = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'
    $zip = '$env:TEMP\ffmpeg.zip'
    
    Write-Host 'Загрузка...'
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    
    Write-Host 'Распаковка...'
    Expand-Archive -Path $zip -DestinationPath '$env:TEMP\ffmpeg-extract' -Force
    
    # Находим папку с bin
    $binFolder = Get-ChildItem -Path '$env:TEMP\ffmpeg-extract' -Directory | Select-Object -First 1
    Copy-Item -Path "$($binFolder.FullName)\bin\*\" -Destination '%INSTALL_DIR%' -Force
    
    Write-Host 'Готово!'
    Write-Host ''
    Write-Host 'FFmpeg установлен в: %INSTALL_DIR%'
    Write-Host 'Файлы:'
    Get-ChildItem -Path '%INSTALL_DIR%' | ForEach-Object { Write-Host '  ' $_.Name }
}"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Установка завершена успешно!
    echo.
    echo Проверка файлов:
    if exist "%INSTALL_DIR%\ffmpeg.exe" (
        echo   [OK] ffmpeg.exe найден
    ) else (
        echo   [ERROR] ffmpeg.exe не найден
    )
    if exist "%INSTALL_DIR%\ffprobe.exe" (
        echo   [OK] ffprobe.exe найден
    ) else (
        echo   [ERROR] ffprobe.exe не найден
    )
) else (
    echo.
    echo [ERROR] Ошибка установки
)

echo.
echo ============================================================
pause
