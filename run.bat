@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo   WSL版 音声文字起こしツール
echo ============================================
echo.

wsl.exe --cd "%~dp0" -- bash -lc "bash ./wsl/setup.sh"

if errorlevel 1 (
    echo.
    echo [エラー] 処理に失敗しました。
    pause
    exit /b 1
)

echo.
echo 処理が完了しました。
echo translate\results フォルダ内の *_result.csv を確認してください。
pause