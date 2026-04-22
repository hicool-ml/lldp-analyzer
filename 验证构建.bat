@echo off
echo ======================================
echo LLDP Network Analyzer v2.0 - Build Verification
echo ======================================
echo.

echo [1/5] Checking executable file...
if exist "dist\LLDP_Analyzer_v2.exe" (
    echo [OK] Executable found: dist\LLDP_Analyzer_v2.exe
    for %%A in ("dist\LLDP_Analyzer_v2.exe") do echo [OK] File size: %%~zA bytes
) else (
    echo [ERROR] Executable not found!
    pause
    exit /b 1
)
echo.

echo [2/5] Checking required files...
if exist "lldp_icon.ico" (
    echo [OK] Icon file found
) else (
    echo [WARN] Icon file not found (optional)
)
echo.

echo [3/5] Checking Python dependencies...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Python is available for development
) else (
    echo [INFO] Python not found (not required for exe)
)
echo.

echo [4/5] Checking Npcap installation...
reg query "HKLM\SOFTWARE\Npcap" >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Npcap is installed
) else (
    echo [WARN] Npcap may not be installed - required for network capture!
    echo [INFO] Download from: https://npcap.com/
)
echo.

echo [5/5] Build summary:
echo [INFO] Build date: %date% %time%
echo [INFO] Executable: dist\LLDP_Analyzer_v2.exe
echo [INFO] Documentation: 测试构建结果.md
echo [INFO] Launcher: 启动LLDP分析器.bat
echo.

echo ======================================
echo Build Verification Complete!
echo ======================================
echo.
echo To run the application:
echo   1. Double-click: 启动LLDP分析器.bat
echo   2. Or run directly: dist\LLDP_Analyzer_v2.exe
echo   3. Run as Administrator for network access
echo.
pause