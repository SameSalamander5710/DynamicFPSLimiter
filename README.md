# DynamicFPSLimiter
A PowerShell script to assess GPU usage and dynamically use AutoHotKey (AHK) to alter FPS limits via RivaTuner Statistics Server (RTSS)

# Requirements
- Install RTSS (https://www.guru3d.com/download/rtss-rivatuner-statistics-server-download/)
  - I've only tested this with individual application profiles, for both the base FPS and hotkeys.
  - Set up two hotkeys, one to reduce the frame limit by x amount, and the other to increase by the same amount
  - Enable HotkeyHandler in the Plugins tab of RTSS setup
- Install AutoHotKey v2 (https://www.autohotkey.com/)
  - Note down the installation directory, which needs to be updated in 'DynamicFPSLimit.ps1'
- PowerShell:
  - Might require changing the PowerShell Execution Policy to run the file.
    - Open PowerShell as Administrator:
    - Check current policy with 'Get-ExecutionPolicy'
    - Change policy with 'Set-ExecutionPolicy RemoteSigned -Scope CurrentUser'
    - When prompted, type Y to confirm the change
    - **NOTE!** It is generally not safe to allow this and run scripts off the internet. Read the contents of the .ps1 files here, and if satisfied, proceed.
    - If blocked, use can unblock the script using 'Unblock-File -Path "DynamicFPSLimit.ps1"'
  
# The concept
This was primarily made to enhance the gaming experience when running Lossless Scaling Frame Generation (LSFG) on a single GPU. Currently, on a single GPU system, LSFG provides the best experience when running a game with an FPS cap that leaves enough GPU headspace for LSFG to work. If the GPU usage hits 100% (which may also cause the base FPS of the game to drop), you MAY start experiencing input lag, which is undesirable. To do this however, you either set a frame cap just below the average FPS, but experience input lag in those instances when the FPS goes down due to 100% GOU utilization, or you set a frame cap much below the least seen FPS ranges, in which case you leave behind a chunk of GPU performance and fps for the average area. With this script, you can dynamically reduce the base FPS of the game in the demanding regions, while enjoying the higher frame rates in the other areas, thus providing an overall better experience.
