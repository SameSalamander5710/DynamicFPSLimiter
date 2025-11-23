# Dynamic FPS Limiter v5 (beta!)

A lightweight companion app for RTSS that leverages its profile-modification API to dynamically adjust framerate limits based on real-time GPU and CPU conditions. It uses LibreHardwareMonitor to read GPU/CPU usage, power draw, and temperatures, with Windows Performance Counters available as a fallback.

- Instead of relying on a fixed FPS cap set below average framerates, it intelligently raises the limit when performance headroom is available. This maintains consistently smooth frametimes, with the only trade-off being a brief stutter when the framerate limit transitions.
- With LibreHardwareMonitor support, you can now define power and temperature constraints as well, across all detected GPUs (Nvidia and AMD), making it particularly useful for multi-GPU setups.
- Especially effective for reducing input latency when using frame-generation tools like Lossless Scaling, by ensuring sufficient GPU headroom is always preserved.
- When paired with adaptive frame generation in Lossless Scaling, it provides a consistently high-refresh visual experience with reduced power draw and lower GPU temperatures.


<p align="center">
  <img src="docs/Images/v5.0.0-beta.1.1.gif" width="45%" />
</p>

## Installation

For the last stable build, check [DFL_v4](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v4).

### To Build It Yourself,
If you'd like to inspect or customize the source code, follow the instructions in [BUILD.md](/src/BUILD.md)

### To Use Prebuilt Executable,
1. Download the `DynamicFPSLimiter_vX.X.X.zip` file from the latest release [here.](https://github.com/SameSalamander5710/DynamicFPSLimiter/releases)
2. Extract the zip file to a desired location
3. Run `DynamicFPSLimiter.exe`  as Administrator.
4. **Recommended**: Add `DynamicFPSLimiter.exe`as an exclusion in RTSS to reduce the app's CPU performance overhead. 
    - This can be done by holding the **Shift** key and clicking **Add** in RTSS, while the app is running.
    - **Note**: While not strictly necessary, this step is strongly recommended if you have disabled 'passive waiting' for the Global profile in RTSS

Demo video to be featured soon! (Based on v5.0.0-beta.1)

> [!NOTE]
> - This app requires Rivatuner Statistics Server (RTSS) running in the background to function. Ensure RTSS is installed before running the app!
> - Since RTSS runs with elevated privileges, DynamicFPSLimiter must also be run as Administrator to function fully.

> [!CAUTION]
> - The executable in the release was packaged using PyInstaller and may be flagged by some antivirus software as a Trojan.
> - You can confirm whether the app is signed by me using the public certificate [here](/src/Public_SameSalamander5710.cer).

## The Concept
This app was initially developed to enhance gaming experience in situations where the GPU load/demand varies greatly during a session. This was especially useful when using Lossless Scaling Frame Generation (LSFG). In a single-GPU system, LSFG works best when the game runs with an FPS cap that leaves enough GPU headroom for frame generation. However, if GPU usage hits 100%—which may also cause the game’s base FPS to drop—you may experience input lag, which is undesirable.

Typically, you have two ways to set an FPS cap:
- Set a cap just below the average FPS – This works most of the time but can lead to input lag when FPS drops due to GPU saturation.
- Set a cap well below the lowest observed FPS – This ensures stability but sacrifices frame rate in less demanding scenes.

This app solves the issue by dynamically adjusting the base FPS limit in demanding areas, reducing input lag while still allowing higher frame rates in less intensive regions. In addition, the app can now monitor and respond to other parameters—such as power draw and temperature—if you choose to configure those constraints.

## Disclaimer

- This app is a personal project created for fun and is **not officially affiliated** with RTSS, Lossless Scaling, or LibreHardwareMonitor.
- As a hobby project, **updates and bug fixes may be delayed** or may not be provided regularly.

## Older versions 

For the older interactions or versions of the same idea/tool, see:
1. [DynamicFPSLimiter v1.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v1)
2. [DynamicFPSLimiter v2.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v2)
3. [DynamicFPSLimiter v3.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v3)
4. [DynamicFPSLimiter v4.0](https://github.com/SameSalamander5710/DynamicFPSLimiter/tree/DFL_v4)

## License

This project is currently licensed under the Apache License 2.0. See the [LICENSE](./LICENSE.txt) file for details.

Previously licensed under the MIT License. The project was relicensed to Apache 2.0 on April 25, 2025 to provide clearer legal protections and attribution requirements.

<!-- ## Miscellaneous -->
