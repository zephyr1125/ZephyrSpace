@echo off
setlocal
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -ExecutionPolicy Bypass -File ".\scripts\generate_daily_report.ps1" -OpenAfterCreate -OverwriteExisting
set EXIT_CODE=%ERRORLEVEL%
echo.
if %EXIT_CODE% neq 0 (
    echo Failed to regenerate daily report. Check the output above.
) else (
    echo Daily report regenerated.
)
pause