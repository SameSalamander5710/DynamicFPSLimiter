# Dynamic FPS Limiter v3.0
A GUI app to assess GPU usage and dynamically adjust frame rate limits via RTSS. 

> [!NOTE]
> - This app requires Rivatuner Statistics Server (RTSS) to function.
> - RTSS runs as an elevated process, so DynamicFPSLimiter must be run with administrator privileges for full functionality.

- Now uses [@xanderfrangos](https://github.com/xanderfrangos)'s [rtss-cli.exe](https://github.com/xanderfrangos/rtss-cli) to directly modify RTSS framerate limits—no more reliance on AutoHotkey or RTSS hotkeys.
  - All framerate control functionality is now fully handled within the DynamicFPSLimiter app—no manual updates in RTSS required.
- Added `Detect Render GPU` button: Automatically detects the GPU used for game rendering by checking which GPU has the highest "3D engine" utilization at the time of clicking. Run this while the game is active to detect the render GPU.
- Added `Profiles` functionality: Lets users manually create target profiles that are already configured in RTSS. This is required to make changes to non-Global target profiles in RTSS.

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


<p float="left">
  <img src="/Docs/Images/DFL_v3.0.0_01.png" style="width: 450px; max-width: 45%;" />
</p>

For more example images, check [here.](/Docs/Examples.md)

- **Global Dynamic FPS Cap:**
  - Outside its use with Lossless Scaling (LSFG), this app can be used to set a general, game-agnostic dynamic FPS cap for your global profile. Simply set the ‘Max FPS limit’ to your monitor’s refresh rate before launching a game, and the app will automatically adjust your FPS to keep GPU usage below your desired threshold.
- **Improved Adaptive Frame Generation (AFG) Experience:**
  - For a better experience with adaptive frame generation (AFG) from Lossless Scaling, set both the AFG target and ‘Max FPS limit’ to the same value. The app will then adjust the base FPS to reach an equilibrium, ensuring enough GPU headroom is available to minimize potential input delays.

## Installation

1. Download the `DynamicFPSLimiter_vX.X.X.zip` file from the latest release [here.](https://github.com/SameSalamander5710/DynamicFPSLimiter/releases)
2. Extract the zip file to a desired location
3. Run `DynamicFPSLimiter.exe` with admin privileges.

## Setup

1. Install RTSS and make sure framerate limits are being enforced in general.
2. If you're using non-Global profiles in RTSS, then in the DynamicFPSLimiter app, create a profile with the same name as the one you've set up in RTSS
3. Once everything is set up, you’re good to go!
   - Click **'Start'** either before or after launching the game. The app will automatically set the target FPS limit and begin adjusting the framerate limit in RTSS.
   - **Note:** Any changes in the app must be made before clicking **'Start'**. Changes made during operation may not be applied.

## What The App Does

The DynamicFPSLimiter app uses a simple PowerShell command to monitor GPU usage in real-time and dynamically adjust the frame limit based on GPU load.

How It Works (with ~default~ random values, but this customizable):
- **When GPU usage exceeds 80% for 2 consecutive seconds:**
  - The app reduces the frame limit by 5 FPS (or multiples of 5) to bring the FPS below the average of the last two seconds when GPU usage was high.
  - Example: If the FPS drops from a capped 60 FPS to 48 FPS, the new frame limit will be set to 45 FPS.
- **When GPU usage drops below 70% for 2 consecutive seconds:**
  - The app increases the frame limit by 5 FPS. This continues as long as the GPU load stays below 70%, until the original frame cap is reached.
- **If GPU usage or FPS drops below 20% or 20 FPS respectively:**
  - The app does not trigger any FPS cap change. This is to prevent loading screens or other low-performance states from unnecessarily affecting the FPS cap.
- The app checks **GPU usage and FPS once every second**.


## Troubleshooting

Check out the [Troubleshooting Guide](/Docs/Troubleshooting.md) for a list of known bugs, common problems, and their solutions.

## Disclaimer

- This app is a personal project created for fun and is **not officially affiliated** with RTSS or Lossless Scaling.
- As a hobby project, **updates and bug fixes may be delayed** or may not be provided regularly.

## Older versions 

For the older interaction of the same idea, see: 
1. [DynamicFPSLimiter v1.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v1.0)
2. [DynamicFPSLimiter v2.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v2.0)

## Miscellaneous


