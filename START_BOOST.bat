@echo off
title FunPay Auto-Boost
cd /d "%~dp0"
echo  ================================================
echo   FunPay Auto-Boost is running
echo   Close this window to stop it
echo  ================================================
echo.
python funpay_boost.py
echo.
echo Script stopped. Press any key to close.
pause >nul
