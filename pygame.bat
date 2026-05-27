@echo off
setlocal

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
set "VENV_DIR=%ROOT_DIR%\.venv"

if not defined PYTHON_BIN set "PYTHON_BIN=python"

where %PYTHON_BIN% >nul 2>nul
if errorlevel 1 (
  echo Error: %PYTHON_BIN% was not found in PATH.
  exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Creating virtual environment at %VENV_DIR%
  %PYTHON_BIN% -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 1
)

call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 exit /b 1

echo Installing dependencies from requirements.txt
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r "%ROOT_DIR%\requirements.txt"
if errorlevel 1 exit /b 1

echo Launching pygame_haxima...
python -m pygame_haxima
exit /b %errorlevel%
