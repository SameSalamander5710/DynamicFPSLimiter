#Ensure you have pyinstaller installed by running: pip install pyinstaller

#To make the executable, I use the following in cmd from the main repo folder

pyinstaller Source\DFL_v3.py ^
    --onedir --uac-admin --clean --noconsole ^
    --name DynamicFPSLimiter ^
    --icon=Source\Resources\DynamicFPSLimiter.ico ^
    --version-file=Source\version.txt ^
    --add-data "Source\Resources:Resources" ^
    --distpath Output\dist ^
    --workpath Output\build