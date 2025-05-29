# Dynamic FPS Limiter v4.1

A lightweight companion app for RTSS that dynamically adjusts framerate limits based on real-time GPU and CPU usage. It's especially useful for reducing input latency when using frame generation tools like Lossless Scaling.

<p float="left">
  <img src="/docs/Images/DFL_v4.0.0_01.png" style="width: 450px; max-width: 45%;" />
</p>

## Installation

### To Build It Yourself,
If you'd like to inspect or customize the source code, follow the instructions in [BUILD.md](/src/BUILD.md)

### To Use Prebuilt Executable,
1. Download the `DynamicFPSLimiter_vX.X.X.zip` file from the latest release [here.](https://github.com/SameSalamander5710/DynamicFPSLimiter/releases)
2. Extract the zip file to a desired location
3. Run `DynamicFPSLimiter.exe`  as Administrator.
4. No additional configuration in RTSS is necessary.

> [!NOTE]
> - This app requires Rivatuner Statistics Server (RTSS) running in the background to function.
> - Since RTSS runs with elevated privileges, DynamicFPSLimiter must also be run as Administrator to function fully.

> [!CAUTION]
> - The executable in the release was packaged using PyInstaller and may be flagged by some antivirus software as a Trojan. 
> - You can find the VirusTotal report on the app's behaviour for the latest release (v4.0.0):
>   - [DynamicFPSLimiter_v4.0.0.zip](https://www.virustotal.com/gui/file/b1fcaa5d0854e68359837562bf3df99158d89a457e2839d8b5e7fea2a20e5c32/behavior)
>   - [DynamicFPSLimiter.exe](https://www.virustotal.com/gui/file/44bb6393c624da36c34e009c52f0057b92c65371f493196155fda6cdceab4d88/behavior)

## The Concept
This app was developed to enhance the gaming experience when using Lossless Scaling Frame Generation (LSFG). LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Typically, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This app solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. As a result, you get a smoother and more responsive gaming experience without compromising too much performance.


<p float="left">
  <img src="/docs/Images/DFL_v4.0.0_01.png" style="width: 450px; max-width: 45%;" />
</p>

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
