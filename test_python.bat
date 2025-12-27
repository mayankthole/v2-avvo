@echo off
echo Testing Python installation...
echo.

echo Trying 'python' command:
python --version
if errorlevel 1 echo [FAILED] 'python' command not found
echo.

echo Trying 'py' command:
py --version
if errorlevel 1 echo [FAILED] 'py' command not found
echo.

echo Trying 'python3' command:
python3 --version
if errorlevel 1 echo [FAILED] 'python3' command not found
echo.

echo Current directory:
cd
echo.

echo Files in current directory:
dir /b *.py
echo.

pause

