@echo off
REM ============================================================
REM  build.bat — Build WhisperDesk for Windows distribution
REM
REM  Usage:
REM    Double-click this file  OR  run it from a terminal:
REM      cd whisperdesk
REM      build.bat
REM
REM  Output: dist\WhisperDesk\WhisperDesk.exe (+ support files)
REM  To create an installer after this, run installer.iss in Inno Setup.
REM ============================================================

echo.
echo  ==========================================
echo   WhisperDesk — Windows Build Script
echo  ==========================================
echo.

REM ── 1. Check Python ───────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)
echo  [OK] Python found

REM ── 2. Check / install PyInstaller ────────────────────────────────────────
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo  [ERROR] PyInstaller installation failed.
        pause
        exit /b 1
    )
)
echo  [OK] PyInstaller ready

REM ── 3. Check all app dependencies are installed ───────────────────────────
echo  [INFO] Checking app dependencies...
python -c "import PyQt6, whisper, sounddevice, soundfile, numpy, torch" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing missing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo  [ERROR] Dependency installation failed. Check requirements.txt.
        pause
        exit /b 1
    )
)
echo  [OK] All dependencies present

REM ── 4. Clean previous build ───────────────────────────────────────────────
echo  [INFO] Cleaning previous build output...
if exist build\WhisperDesk   rmdir /s /q build\WhisperDesk
if exist dist\WhisperDesk    rmdir /s /q dist\WhisperDesk

REM ── 5. Run PyInstaller ────────────────────────────────────────────────────
echo.
echo  [INFO] Running PyInstaller (this takes 10-20 minutes first time)...
echo  [INFO] You will see many warnings — that is normal for torch/whisper.
echo.

pyinstaller whisperdesk.spec

if errorlevel 1 (
    echo.
    echo  [ERROR] PyInstaller build failed. See output above for details.
    pause
    exit /b 1
)

REM ── 6. Verify output ──────────────────────────────────────────────────────
if not exist "dist\WhisperDesk\WhisperDesk.exe" (
    echo  [ERROR] WhisperDesk.exe not found after build. Something went wrong.
    pause
    exit /b 1
)

REM ── 7. Copy extra files into dist folder ──────────────────────────────────
echo  [INFO] Copying README and license into dist folder...
copy /Y README.md  "dist\WhisperDesk\README.md"  >nul 2>&1
copy /Y ..\LICENSE "dist\WhisperDesk\LICENSE.txt" >nul 2>&1

REM ── 8. Create a zip of the dist folder ────────────────────────────────────
echo  [INFO] Creating WhisperDesk-Windows.zip...
powershell -Command "Compress-Archive -Path 'dist\WhisperDesk' -DestinationPath 'dist\WhisperDesk-Windows.zip' -Force"

echo.
echo  ==========================================
echo   BUILD COMPLETE
echo  ==========================================
echo.
echo   Executable : dist\WhisperDesk\WhisperDesk.exe
echo   Zip archive: dist\WhisperDesk-Windows.zip
echo.
echo   To create a proper installer, open installer.iss
echo   in Inno Setup and click Build ^> Compile.
echo.
pause
