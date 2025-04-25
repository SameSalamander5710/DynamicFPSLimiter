@echo off
REM Setup VS environment for x64
if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) else if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" (
    call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
) else (
    echo Error: Visual Studio Build Tools not found!
    echo Please install from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    exit /b 1
)

REM Compile the executable
cl rtss-cli.cpp /O1 /MD /link /DEFAULTLIB:advapi32.lib /DEFAULTLIB:user32.lib

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    exit /b 1
)

echo Build successful!
pause