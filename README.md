# Dynamic FPS Limiter v4.0

A lightweight companion app for RTSS that dynamically adjusts framerate limits based on real-time GPU and CPU usage. It's especially useful for reducing input latency when using frame generation tools like Lossless Scaling.

> [!NOTE]
> - This app requires Rivatuner Statistics Server (RTSS) running in the background to function.
> - Since RTSS runs with elevated privileges, DynamicFPSLimiter must also be run as Administrator to function fully.

## Table of Contents
- [The Concept](#the-concept)
- [Installation](#installation)
- [Troubleshooting](#troubleshooting)

## The Concept
This app was developed to enhance the gaming experience when using Lossless Scaling Frame Generation (LSFG). LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Typically, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This app solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. As a result, you get a smoother and more responsive gaming experience without compromising too much performance.


<p float="left">
  <img src="/docs/Images/DFL_v4.0.0_01.png" style="width: 450px; max-width: 45%;" />
</p>

- **Global Dynamic FPS Cap:**
  - Outside its use with Lossless Scaling (LSFG), this app can be used to set a general, game-agnostic dynamic FPS cap for your global profile. Simply set the ‘Max FPS limit’ to your monitor’s refresh rate before launching a game, and the app will automatically adjust your FPS to keep GPU usage below your desired threshold.
- **Improved Adaptive Frame Generation (AFG) Experience:**
  - For a better experience with adaptive frame generation (AFG) from Lossless Scaling, set both the AFG target and ‘Max FPS limit’ to the same value. The app will then adjust the base FPS to reach an equilibrium, ensuring enough GPU headroom is available to minimize potential input delays.

## Installation

### To Build It Yourself,
If you'd like to inspect or customize the source code, follow the instructions in [BUILD.md](/src/BUILD.md)

### To Use Prebuilt Executable,
1. Download the `DynamicFPSLimiter_vX.X.X.zip` file from the latest release [here.](https://github.com/SameSalamander5710/DynamicFPSLimiter/releases)
2. Extract the zip file to a desired location
3. Run `DynamicFPSLimiter.exe`  as Administrator.
4. No additional configuration in RTSS is necessary.

> [!CAUTION]
> - The executable in the release was packaged using PyInstaller and may be flagged by some antivirus software as a Trojan. 
> - You can find the VirusTotal report on the app's behaviour for the latest release (v4.0.0):
>   - [DynamicFPSLimiter_v4.0.2.zip](https://www.virustotal.com/gui/file/d3b5bf17bfc9b77d6cc86685769c921239c9ea1bdae64f1bf63887a3353d40bf/behavior)
>   - [DynamicFPSLimiter.exe](https://www.virustotal.com/gui/file/d09875d3eb17335e28336e3a499b640928b6bed129af43175e74ec5ebd29667c/behavior)

## Troubleshooting

Check out the [Troubleshooting Guide](/docs/Troubleshooting.md) for a list of known bugs, common problems, and their solutions.

# Under the hood

To learn more about the internal logic, including how GPU/CPU usage is monitored and how framerate limits are calculated and applied, check out the [How It Works](docs/HOW_IT_WORKS.md) guide.

## Disclaimer

- This app is a personal project created for fun and is **not officially affiliated** with RTSS or Lossless Scaling.
- As a hobby project, **updates and bug fixes may be delayed** or may not be provided regularly.

## Older versions 

For the older interactions or versions of the same idea, see:
1. [DynamicFPSLimiter v1.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v1)
2. [DynamicFPSLimiter v2.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v2)
3. [DynamicFPSLimiter v3.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v3)

## License

This project is currently licensed under the Apache License 2.0. See the [LICENSE](./LICENSE.txt) file for details.

Previously licensed under the MIT License. The project was relicensed to Apache 2.0 on April 25, 2025 to provide clearer legal protections and attribution requirements.

<!-- ## Miscellaneous -->
