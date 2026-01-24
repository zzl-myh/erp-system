@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 日志文件
set LOG_FILE=push_log.txt
echo ========== %date% %time% ========== >> %LOG_FILE%
echo ========== ERP 代码推送 ==========
echo ========== ERP 代码推送 ========== >> %LOG_FILE%

:: 检查 Git 是否可用
git --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Git 未安装或未配置到 PATH
    echo [错误] Git 未安装或未配置到 PATH >> %LOG_FILE%
    pause
    exit /b 1
)

:: 获取当前分支名
for /f "tokens=*" %%a in ('git rev-parse --abbrev-ref HEAD 2^>^&1') do set BRANCH=%%a
echo 当前分支: %BRANCH%
echo 当前分支: %BRANCH% >> %LOG_FILE%

:: 检查远程仓库
echo.
echo 远程仓库配置:
git remote -v
git remote -v >> %LOG_FILE% 2>&1

:: 检查是否有未提交的更改
echo.
echo 检查文件状态...
git status --porcelain > temp_status.txt
for %%i in (temp_status.txt) do set SIZE=%%~zi
if %SIZE% EQU 0 (
    echo 没有需要提交的更改
    echo 没有需要提交的更改 >> %LOG_FILE%
    del temp_status.txt
    pause
    exit /b
)
del temp_status.txt

:: 显示更改内容
echo.
echo 待提交的更改:
git status --short
git status --short >> %LOG_FILE%
echo.

:: 输入提交信息
set /p COMMIT_MSG="请输入提交信息: "

if "%COMMIT_MSG%"=="" (
    echo 提交信息不能为空
    echo 提交信息不能为空 >> %LOG_FILE%
    pause
    exit /b
)

echo 提交信息: %COMMIT_MSG% >> %LOG_FILE%

:: 执行 git add
echo.
echo 正在执行 git add...
git add . >> %LOG_FILE% 2>&1
if errorlevel 1 (
    echo [错误] git add 失败
    echo [错误] git add 失败 >> %LOG_FILE%
    pause
    exit /b 1
)
echo git add 成功

:: 执行 git commit
echo 正在执行 git commit...
git commit -m "%COMMIT_MSG%" >> %LOG_FILE% 2>&1
if errorlevel 1 (
    echo [错误] git commit 失败，请查看 %LOG_FILE%
    echo [错误] git commit 失败 >> %LOG_FILE%
    type %LOG_FILE%
    pause
    exit /b 1
)
echo git commit 成功

:: 执行 git push
echo 正在执行 git push origin %BRANCH%...
echo 执行: git push origin %BRANCH% >> %LOG_FILE%
git push origin %BRANCH% >> %LOG_FILE% 2>&1
if errorlevel 1 (
    echo.
    echo [错误] git push 失败！详细错误信息:
    echo [错误] git push 失败 >> %LOG_FILE%
    echo.
    type %LOG_FILE%
    echo.
    echo 可能的原因:
    echo 1. 远程仓库未配置: git remote add origin https://github.com/zzl-myh/erp-system.git
    echo 2. 需要设置上游分支: git push -u origin %BRANCH%
    echo 3. 认证失败: 检查 GitHub 账号密码或 SSH 密钥
    pause
    exit /b 1
)

echo.
echo ========== 推送成功 ========== 
echo 推送成功 >> %LOG_FILE%
echo 日志已保存到: %LOG_FILE%
echo 请到服务器执行部署脚本: ./deploy.sh
pause