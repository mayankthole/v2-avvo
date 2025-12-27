@echo off
cd /d "%~dp0"

title Avvo Scraper

echo.
echo ========================================
echo    AVVO SCRAPER - Starting...
echo ========================================
echo.

REM Try to find Python
set PYTHON_CMD=

REM Method 1: Try standard commands
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto found_python
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto found_python
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto found_python
)

REM Method 2: Try common Python 3.13 locations
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto found_python
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe" (
    set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe"
    goto found_python
)

if exist "C:\Python313\python.exe" (
    set PYTHON_CMD="C:\Python313\python.exe"
    goto found_python
)

if exist "%ProgramFiles%\Python313\python.exe" (
    set PYTHON_CMD="%ProgramFiles%\Python313\python.exe"
    goto found_python
)

REM Python not found - show detailed error
echo.
echo ========================================
echo    ERROR: Python Not Found
echo ========================================
echo.
echo Python 3.13.1 is installed but Windows cannot find it.
echo This usually means Python is not in your PATH.
echo.
echo QUICK FIX - Add Python to PATH:
echo   1. Press Windows Key + R, type: sysdm.cpl
echo   2. Go to Advanced tab -^> Environment Variables
echo   3. Under System Variables, find "Path" and click Edit
echo   4. Click New and add these two paths:
echo      C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313
echo      C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\Scripts
echo   5. Click OK on all windows
echo   6. Close this window and try again
echo.
echo ========================================
echo.
pause
exit /b 1

:found_python

:found_python
echo [OK] Found Python
%PYTHON_CMD% --version
if errorlevel 1 (
    echo [ERROR] Python found but version check failed!
    echo.
    pause
    exit /b 1
)
echo.

REM Check if pip is available
echo [CHECK] Verifying pip...
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] pip is not available.
    echo Please reinstall Python and make sure pip is included.
    echo.
    pause
    exit /b 1
)
echo [OK] pip is available
echo.

REM Check and install dependencies
echo [CHECK] Checking dependencies...
set DEPS_MISSING=0

%PYTHON_CMD% -c "import undetected_chromedriver" >nul 2>&1
if errorlevel 1 set DEPS_MISSING=1

%PYTHON_CMD% -c "import selenium" >nul 2>&1
if errorlevel 1 set DEPS_MISSING=1

%PYTHON_CMD% -c "import bs4" >nul 2>&1
if errorlevel 1 set DEPS_MISSING=1

%PYTHON_CMD% -c "import pandas" >nul 2>&1
if errorlevel 1 set DEPS_MISSING=1

%PYTHON_CMD% -c "import lxml" >nul 2>&1
if errorlevel 1 set DEPS_MISSING=1

if %DEPS_MISSING% equ 1 (
    echo [INSTALL] Installing required packages...
    echo This may take 2-3 minutes, please wait...
    echo.
    
    echo Upgrading pip...
    %PYTHON_CMD% -m pip install --quiet --upgrade pip
    if errorlevel 1 (
        echo [WARNING] pip upgrade failed, continuing...
    )
    
    echo Installing packages...
    %PYTHON_CMD% -m pip install --no-cache-dir -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies.
        echo.
        echo Try running manually:
        echo   %PYTHON_CMD% -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    
    echo Verifying installation...
    %PYTHON_CMD% -c "import undetected_chromedriver; import selenium; import bs4; import pandas; import lxml" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Some packages may not have installed correctly
        echo Try running: %PYTHON_CMD% -m pip install -r requirements.txt
    ) else (
        echo [OK] Dependencies installed and verified!
    )
) else (
    echo [OK] All dependencies are already installed
)
echo.

REM Check if required files exist
if not exist "avvo_scraper_direct_to_csv.py" (
    echo [ERROR] avvo_scraper_direct_to_csv.py not found!
    echo Make sure all files are in the same folder.
    pause
    exit /b 1
)

if not exist "html_to_csv_converter.py" (
    echo [ERROR] html_to_csv_converter.py not found!
    echo Make sure all files are in the same folder.
    pause
    exit /b 1
)

if not exist "urls.txt" (
    echo [WARNING] urls.txt not found!
    echo Creating sample urls.txt file...
    (
        echo # Add one URL per line
        echo # Lines starting with # are ignored
        echo # Optional: Add DAYS_BACK=365 to set review date filter
        echo.
        echo https://www.avvo.com/attorneys/28204-nc-michael-demayo-1742166.html
    ) > urls.txt
    echo [OK] Created urls.txt - please add your URLs and run again.
    pause
    exit /b 1
)

echo ========================================
echo    Starting Scraper...
echo ========================================
echo.

REM Run the scraper
%PYTHON_CMD% avvo_scraper_direct_to_csv.py

set SCRAPER_EXIT=%errorlevel%

echo.
echo ========================================
if %SCRAPER_EXIT% equ 0 (
    echo    Scraping Completed!
) else (
    echo    Scraping Finished (with errors)
)
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
exit /b %SCRAPER_EXIT%

