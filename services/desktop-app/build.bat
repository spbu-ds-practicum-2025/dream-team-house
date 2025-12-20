@echo off
setlocal

REM Build script for Dream Team House desktop app
set SCRIPT_DIR=%~dp0
set BUILD_DIR=%SCRIPT_DIR%build
set DIST_DIR=%SCRIPT_DIR%dist

if "%QT_DIR%"=="" (
    if "%Qt6_DIR%"=="" (
        echo Please set QT_DIR or Qt6_DIR to your Qt installation (e.g. C:\Qt\6.6.3\msvc2019_64).
        exit /b 1
    )
    set QT_DIR=%Qt6_DIR%
)

echo Using Qt from %QT_DIR%
set PATH=%QT_DIR%\bin;%PATH%

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

cmake -S "%SCRIPT_DIR%" -B "%BUILD_DIR%" -G "Ninja" -DCMAKE_PREFIX_PATH="%QT_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo CMake configuration failed.
    exit /b 1
)

cmake --build "%BUILD_DIR%" --config Release
if %ERRORLEVEL% NEQ 0 (
    echo Build failed.
    exit /b 1
)

if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"
copy "%BUILD_DIR%\bin\dream-team-desktop.exe" "%DIST_DIR%\"
windeployqt --release "%DIST_DIR%\dream-team-desktop.exe" --dir "%DIST_DIR%"

echo Build complete. Bundle is in %DIST_DIR%
