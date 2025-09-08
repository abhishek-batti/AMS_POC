@echo off
if not exist .venv (
    echo Creating Python virtual environment...
    python -m venv .venv
    echo Virtual environment created in .venv
) else (
    echo Virtual environment already exists.
)
echo Activating virtual environment...
call .venv\Scripts\activate
if exist requirements.txt (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
    echo Dependencies installed.
) else (
    echo No requirements.txt found, skipping dependency installation.
)
echo Virtual environment activated.
echo To deactivate, run: deactivate