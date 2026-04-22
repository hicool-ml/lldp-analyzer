@echo off
echo ======================================
echo LLDP Network Analyzer v2.0
echo ======================================
echo.
echo 正在检查管理员权限...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] 已获得管理员权限
) else (
    echo [ERROR] 需要管理员权限！
    echo 请右键点击此文件，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo.
echo 正在启动LLDP分析器...
echo.

REM 检查exe文件是否存在
if not exist "dist\LLDP_Analyzer_v2.exe" (
    echo [ERROR] 找不到 exe 文件！
    echo 请确保文件路径正确：dist\LLDP_Analyzer_v2.exe
    pause
    exit /b 1
)

REM 启动程序
cd /d "%~dp0"
start "" "dist\LLDP_Analyzer_v2.exe"

echo 程序已启动！
echo 如果遇到问题，请查看"测试说明.md"文件
timeout /t 3 >nul
