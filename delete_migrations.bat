@echo off
setlocal EnableDelayedExpansion

rem Force execution from project root
cd /d "%~dp0"

echo ==========================================
echo Cleaning Django project
echo Root: %cd%
echo ==========================================

rem -------- Delete migration files --------
for /f "delims=" %%D in ('dir /s /b /ad migrations') do (
    if exist "%%D\__init__.py" (
        echo Cleaning migrations: %%D
        del /f /q "%%D\*.py"
        del /f /q "%%D\*.pyc"

        if not exist "%%D\__init__.py" (
            echo. > "%%D\__init__.py"
        )
    )
)

rem -------- Delete __pycache__ folders (deepest first) --------
for /f "delims=" %%P in ('dir /s /b /ad __pycache__ ^| sort /R') do (
    echo Removing cache: %%P
    attrib -r -h -s "%%P" /s /d
    rmdir /s /q "%%P"
)

echo ==========================================
echo DONE.
echo ==========================================
pause
