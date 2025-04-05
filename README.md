[README and documentation for new app in progress]

# DynamicFPSLimiter v2.0! 
A GUI app to assess GPU usage and dynamically adjust frame limits via RTSS using hotkeys.

# The Concept
This app was developed to enhance the gaming experience when using Lossless Scaling Frame Generation (LSFG). LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Typically, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This app solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. As a result, you get a smoother and more responsive gaming experience without compromising too much performance.

## Table of Contents
- [Installation](#installation)
- [What The App Does](#what-the-app-does)
- [Requirements](#requirements)
- Miscellaneous

## Detailed Instructions
- Setting up Hotkeys in RTSS
- What each option does

## Installation

> [!CAUTION]
> The app uses an AutoHotKey (AHK) library within Python to send the hotkey presses to RTSS. This may get flagged by games with Anti-cheat, so please use with caution!

1. Download the `DynamicFPSLimiter.zip` file from the latest release (Add link)
2. Extract the zip file to the desired location
3. Run `DynamicFPSLimiter.exe`

## Requirements
Set up working Hotkeys in RTSS to increase/decrease frame limit by a set amount (e.g.: Increase/Decrease by 5). Find more information here (Add link)

## What The App Does

This script uses PowerShell to monitor GPU usage in real-time and dynamically adjust frame limits based on system load. 

Example of how it works with the default values (all values can be adjusted in the app):
- If GPU usage exceeds 80% for 2 consecutive seconds, the app reduces the frame limit by 5 or its multiples.
  - It adjusts the frame cap by multiples of 5 required to get below the average FPS of the last two seconds where the GPU usage is beyond the threshold. For example, if the FPS drops from a capped 60 FPS to 48 FPS, then it sets the new frame limit to 45 fps.
- If GPU usage drops below 70% for 2 consecutive seconds, the app increases the frame limit by 5. This happens incrementally as long as the GPU load stays below 70%, until the original frame cap is met.
- Frame rate adjustments (inc./dec. by '5') are triggered via hotkeys set in RTSS (Rivatuner Statistics Server).
- The GPU usage and FPS are checked every 1 second, so the time delays need to be set in integer multiples of 1.
