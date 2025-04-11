# Dynamic FPS Limiter v2.0
A GUI app to assess GPU usage and dynamically adjust frame rate limits via RTSS using AutoHotKey. 

> [!NOTE]
> - This app requires Rivatuner Statistics Server (RTSS) to function.

## Table of Contents
- [The Concept](#the-concept)
- [Installation](#installation)
- [Setup](#setup)
- [What The App Does](#what-the-app-does)
- [Troubleshooting](#troubleshooting)

## The Concept
This app was developed to enhance the gaming experience when using Lossless Scaling Frame Generation (LSFG). LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Typically, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This app solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. As a result, you get a smoother and more responsive gaming experience without compromising too much performance.

<img src="/Docs/Images/DynamicFPSLimiter_01.png" style="width: 450px; max-width: 100%;" />

For more example images, check [here.](/Docs/Examples.md)

- **Global Dynamic FPS Cap:**
  - Outside its use with Lossless Scaling (LSFG), this app can be used to set a general, game-agnostic dynamic FPS cap for your global profile. Simply set the RTSS frame rate limit and ‘Max FPS limit’ to your monitor’s refresh rate before launching a game, and the app will automatically adjust your FPS to keep GPU usage below your desired threshold.
- **Improved Adaptive Frame Generation (AFG) Experience:**
  - For a better experience with adaptive frame generation (AFG) from Lossless Scaling, set both the AFG target and ‘Max FPS limit’ to the same value. The app will then adjust the base FPS to reach an equilibrium, ensuring enough GPU headroom is available to minimize potential input delays.

## Installation

> [!CAUTION]
> - Unlike the previous iteration of the idea using scripts, this app does not require the installation of AutoHotKey (AHK), Python, or any changes to PowerShell policies.
> - **HOWEVER**, the app uses AHK internally to send the hotkey presses to RTSS. This can get flagged by games with Anti-cheat, so please use with caution!


1. Download the `DynamicFPSLimiter_vX.X.X.zip` file from the latest release [here.](https://github.com/SameSalamander5710/DynamicFPSLimiter/releases)
2. Extract the zip file to a desired location
3. Run `DynamicFPSLimiter.exe`

## Setup

1. Configure RTSS hotkeys
    - First, install and set up hotkeys in RTSS to increase or decrease the framerate limit by a fixed amount (e.g., ±5 FPS). For detailed instructions, see [RTSS Hotkey Setup](/Docs/RTSS_Hotkey_Setup.md).
2. Before starting, make sure of the following:
    - The framerate limit in RTSS matches the 'Max FPS limit' value in DynamicFPSLimiter.
    - The 'frame rate step' and hotkeys in the app are the same as those configured in RTSS.
    - Test that your RTSS hotkeys are working by clicking the ‘Dec. limit’ or ‘Inc. limit’ buttons in the app:
  <img src="/Docs/Images/RTSS_11.png" style="width: 6000px; max-width: 100%;" />

3. Once everything is set up, you're good to go!
   - Click **'Start'** either before or after launching the game, and the app will begin adjusting the framerate limit in RTSS automatically.

> [!TIP]
> - The hotkey presses are sent **globally**, which means they will also affect your game while it's running. To avoid unintended inputs, choose hotkeys that **aren’t already bound in-game**, and avoid keys that could interfere with typing in chat or search boxes.
>
> - For key naming reference, check out the [AutoHotkey v2 Send documentation](https://www.autohotkey.com/docs/v2/lib/Send.htm).

## What The App Does

The DynamicFPSLimiter app uses a simple PowerShell command to monitor GPU usage in real-time and dynamically adjust the frame limit based on system load.

How It Works (with ~default~ random values, but this customizable):
- **When GPU usage exceeds 80% for 2 consecutive seconds:**
  - The app reduces the frame limit by 5 FPS (or multiples of 5) to bring the FPS below the average of the last two seconds when GPU usage was high.
  - Example: If the FPS drops from a capped 60 FPS to 48 FPS, the new frame limit will be set to 45 FPS.
- **When GPU usage drops below 70% for 2 consecutive seconds:**
  - The app increases the frame limit by 5 FPS. This continues as long as the GPU load stays below 70%, until the original frame cap is reached.
- **If GPU usage or FPS drops below 20% or 20 FPS respectively:**
  - The app does not trigger any FPS cap change. This is to prevent loading screens or other low-performance states from unnecessarily affecting the FPS cap.
- **Frame rate adjustments** (increases/decreases by 5 FPS) are triggered using **hotkeys set in RTSS**.
- The app checks **GPU usage and FPS every second**, so time delays should be set as integer multiples of 1 second.


## Troubleshooting

Check out the [Troubleshooting Guide](/Docs/Troubleshooting.md) for a list of known bugs, common problems, and their solutions.

## Disclaimer

- This app is a personal project created for fun and is **not officially affiliated** with RTSS, AutoHotKey, or Lossless Scaling.
- As a hobby project, **updates and bug fixes may be delayed** or may not be provided regularly.

## v1.0 

For the older interaction of the same idea, see: [DynamicFPSLimiter v1.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/legacy-main)

## Miscellaneous

For the reddit post associated with the release, see [https://www.reddit.com/r/losslessscaling/comments/1jtliw4/dynamicfpslimiter_v20_gui_app_to_automatically/](https://www.reddit.com/r/losslessscaling/comments/1jtliw4/dynamicfpslimiter_v20_gui_app_to_automatically/)
