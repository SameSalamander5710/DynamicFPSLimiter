# Ensure you have pyinstaller installed
# Ensure the required modules (found in requirements.txt) are installed in the environment
# To make the executable, I use the following in cmd from the main repo folder

pyinstaller Source\DFL_v3.py ^
    --onedir --uac-admin --clean --noconsole ^
    --name DynamicFPSLimiter ^
    --icon=Source\DynamicFPSLimiter.ico ^
    --version-file=Source\version.txt ^
    --add-data "Source\DynamicFPSLimiter.ico:." ^
    --add-data "Source\rtss-cli.exe:." ^
    --distpath Output\dist ^
    --workpath Output\build