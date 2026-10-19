@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo Setting up the game for first use...
    where py >nul 2>&1
    if errorlevel 1 (
        where python >nul 2>&1
        if errorlevel 1 (
            echo Python was not found. Install Python, then run this file again.
            echo Download Python from https://www.python.org/downloads/
            pause
            exit /b 1
        )
        python -m venv venv
    ) else (
        py -m venv venv
    )
    if errorlevel 1 (
        echo Could not create the project virtual environment.
        pause
        exit /b 1
    )

    echo Installing the game requirements. This may take a few minutes...
    "venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Could not install the game requirements. Check your internet connection and try again.
        pause
        exit /b 1
    )
)

"venv\Scripts\python.exe" "main.py"
if errorlevel 1 (
    echo.
    echo The game stopped with an error. Read the traceback above.
) else (
    echo.
    echo The game has closed.
)
pause
