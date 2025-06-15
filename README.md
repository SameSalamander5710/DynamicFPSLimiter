# Dynamic FPS Limiter v4.2

A lightweight companion app for RTSS that dynamically adjusts framerate limits based on real-time GPU and CPU usage. It's especially useful for reducing input latency when using frame generation tools like Lossless Scaling.

<p align="center">
  <img src="docs/Images/v4.1.0_2025-05-31-09-50-18.gif" width="45%" />
  &nbsp;
  <img src="docs/Images/v4.1.0_2025-05-31-09-43-54.gif" width="45%" />
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
> - You can confirm whether the app is signed by me using the public certificate [here.](/src/Public_SameSalamander5710.cer).
> - You can find the VirusTotal report on the app's behaviour for the latest release (v4.2.0):
>   - [DynamicFPSLimiter_v4.2.0.zip](https://www.virustotal.com/gui/file/e76b8cd89b31b8f0e10070b9c71fc15f3fed730caaf36182d6998413f762c00b/behavior)
>   - [DynamicFPSLimiter.exe](https://www.virustotal.com/gui/file/a62744f65fdb10f2646d625240b50a634fa4a3e59d73e14fac74380d18546c06/behavior)


## The Concept
This app was developed to enhance gaming experience in situations where the GPU load/demand varies greatly during a session. This is especially useful when using Lossless Scaling Frame Generation (LSFG). LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Typically, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This app solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. As a result, you get a smoother and more responsive gaming experience without compromising too much performance.

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
