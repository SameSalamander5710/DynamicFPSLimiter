# DynamicFPSLimiter
A PowerShell script to assess GPU usage and dynamically use AutoHotKey (AHK) to alter FPS limits via RivaTuner Statistics Server (RTSS)

# The Concept
This script was developed to enhance the gaming experience when using Lossless Scaling Frame Generation (LSFG) on a single GPU. LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Normally, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This script solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. As a result, you get a smoother and more responsive gaming experience without compromising too much performance.

# What This Script Does
This script uses PowerShell to monitor GPU usage in real-time and dynamically adjust frame limits based on system load. It helps maintain optimal performance by lowering the frame cap when GPU usage is high and restoring it when usage decreases.

Example of How It Works:
- If GPU usage exceeds 80% for 2 consecutive seconds, the script reduces the frame limit by X FPS.
- If GPU usage drops below 70% for 3 consecutive seconds, the script increases the frame limit by X FPS, up to the original cap.
- Frame rate adjustments are triggered via hotkeys set in RTSS (Rivatuner Statistics Server).
- By default, GPU usage is checked every 1 second, but this interval can be adjusted.

# Requirements
- Install RTSS (https://www.guru3d.com/download/rtss-rivatuner-statistics-server-download/)
  - This script has only been tested with individual application profiles for both the base FPS and hotkeys.
  - Set up two hotkeys in RTSS:
    - One to decrease the frame limit by X FPS.
    - One to increase the frame limit by X FPS.
  - Enable HotkeyHandler in the Plugins tab of the RTSS setup.
    - By default, '-' key decreases FPS by X, and '=' key increases FPS by X.
    - If you change these, update the two .ahk files accordingly. You can leave it as is unless these keys are used in the game.
  - Start the game with the higher base FPS limit.
- Install AutoHotKey v2 (https://www.autohotkey.com/)
  - Take note of the installation directory, as it needs to be updated in DynamicFPSLimit.ps1.
- PowerShell:
  - You may need to change the PowerShell Execution Policy to allow the script to run:
    - Open PowerShell as Administrator:
    - Check current policy with 'Get-ExecutionPolicy'
    - Change policy with 'Set-ExecutionPolicy RemoteSigned -Scope CurrentUser'
    - When prompted, type Y to confirm the change
    - **NOTE!** It is generally not safe to allow this and run scripts off the internet. Read the contents of the .ps1 files here, and if satisfied, proceed.
    - If blocked, use 'Unblock-File -Path .\DynamicFPSLimit.ps1'  to unblock the script

Handling Multiple GPUs:
    - If you have multiple GPUs, the script sums up total GPU utilization.
    - To target a specific GPU:
      - Run GetGPUInstance.ps1 to find the correct GPU instance.
      - Replace the instance ID in DynamicFPSLimit.ps1 accordingly.
