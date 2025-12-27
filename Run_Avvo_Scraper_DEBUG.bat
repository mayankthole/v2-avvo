@echo off
cd /d "%~dp0"

title Avvo Scraper - DEBUG MODE

echo.
echo ========================================
echo    AVVO SCRAPER - DEBUG MODE
echo ========================================
echo.
echo This window will stay open so you can see any errors.
echo.
pause

echo.
echo Testing Python detection...
echo.

REM Try to find Python
set PYTHON_CMD=

echo Trying 'python' command:
python --version 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    echo [SUCCESS] Found: python
    goto found_python
) else (
    echo [FAILED] 'python' command not found
)

echo.
echo Trying 'py' command:
py --version 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    echo [SUCCESS] Found: py
    goto found_python
) else (
    echo [FAILED] 'py' command not found
)

echo.
echo Trying 'python3' command:
python3 --version 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    echo [SUCCESS] Found: python3
    goto found_python
) else (
    echo [FAILED] 'python3' command not found
)

echo.
echo Trying common Python 3.13 locations:
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    echo [SUCCESS] Found at: %LOCALAPPDATA%\Programs\Python\Python313\python.exe
    goto found_python
) else (
    echo [NOT FOUND] %LOCALAPPDATA%\Programs\Python\Python313\python.exe
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe"
    echo [SUCCESS] Found at: %LOCALAPPDATA%\Programs\Python\Python313-32\python.exe
    goto found_python
) else (
    echo [NOT FOUND] %LOCALAPPDATA%\Programs\Python\Python313-32\python.exe
)

echo.
echo ========================================
echo    ERROR: Python Not Found
echo ========================================
echo.
echo Python could not be found. Please check:
echo 1. Is Python installed?
echo 2. Is Python in your PATH?
echo.
echo To fix PATH:
echo 1. Press Windows Key + R, type: sysdm.cpl
echo 2. Advanced -^> Environment Variables
echo 3. Edit Path variable
echo 4. Add: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313
echo 5. Add: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts
echo.
pause
exit /b 1

:found_python
echo.
echo ========================================
echo    Python Found!
echo ========================================
echo.
echo Using: %PYTHON_CMD%
echo.
%PYTHON_CMD% --version
echo.

echo Checking pip...
%PYTHON_CMD% -m pip --version
if errorlevel 1 (
    echo [ERROR] pip not available
    pause
    exit /b 1
)
echo [OK] pip is available
echo.

echo Checking files...
if not exist "avvo_scraper_direct_to_csv.py" (
    echo [ERROR] avvo_scraper_direct_to_csv.py not found!
    pause
    exit /b 1
)
if not exist "html_to_csv_converter.py" (
    echo [ERROR] html_to_csv_converter.py not found!
    pause
    exit /b 1
)
if not exist "urls.txt" (
    echo [WARNING] urls.txt not found - will create it
) else (
    echo [OK] urls.txt found
)
echo.

echo Checking dependencies...
%PYTHON_CMD% -c "import undetected_chromedriver" 2>&1
if errorlevel 1 (
    echo [WARNING] Dependencies not installed
    echo Would you like to install them now? (Y/N)
    choice /C YN /N /M "Install dependencies"
    if errorlevel 2 goto skip_install
    if errorlevel 1 goto install_deps
) else (
    echo [OK] Dependencies are installed
)

:skip_install
echo.
echo ========================================
echo    Ready to Run
echo ========================================
echo.
echo Press any key to start scraping...
pause >nul

echo.
echo Starting scraper...
echo.
%PYTHON_CMD% avvo_scraper_direct_to_csv.py

echo.
echo ========================================
echo    Finished
echo ========================================
echo.
pause
exit /b 0

:install_deps
echo.
echo Installing dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Installation failed
    pause
    exit /b 1
)
echo [OK] Dependencies installed
goto skip_install

