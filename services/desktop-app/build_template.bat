@echo off
REM ================================================
REM Build script for Calculator Qt Application
REM Requires: Qt5 with MinGW and CMake installed
REM ================================================

echo ================================================
echo Calculator Build Script
echo ================================================

REM Set Qt path - CHANGE THIS TO YOUR Qt INSTALLATION PATH
set QT_PATH=C:\msys64\mingw64
set MINGW_PATH=C:\msys64\mingw64

REM Add Qt and MinGW to PATH
set PATH=%QT_PATH%\bin;%MINGW_PATH%\bin;%PATH%

REM Create build directory
if not exist "build" mkdir build
cd build

echo.
echo [1/3] Running CMake configuration...
cmake -G "MinGW Makefiles" -DCMAKE_PREFIX_PATH="%QT_PATH%" ..

if %ERRORLEVEL% NEQ 0 (
    echo CMake configuration failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Building the project...
mingw32-make -j4

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Copying Qt DLLs for deployment...
windeployqt Calculator.exe

echo.
echo ================================================
echo Build completed successfully!
echo Executable: build\Calculator.exe
echo ================================================
echo.
echo Press any key to run the application...
pause >nul

Calculator.exe
