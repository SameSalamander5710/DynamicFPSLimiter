# CHANGELOG

## [v5.0.0-beta.1] - 2025-11-15

### Added
- Integrated LibreHardwareMonitorLib (v0.9.4) for accurate monitoring of GPU usage, power draw, and temperature.
    - Supports Nvidia and AMD GPUs. Intel GPUs may use the previous Windows Performance Counter method as a fallback ("Legacy") option.
    - LibreHardwareMonitor (LHM) method now allows setting constraints individually per GPU, useful for multi-GPU systems.
- Added an Idle Mode that lowers the framerate limit of the active game window after a user-defined period of inactivity.
- Added session summary statistics for the LHM monitoring module.

### Changed
- Autopilot now defaults to also modifying the Global RTSS profile and automatically switches between the Global profile and game-specific profiles depending on the active window.

### Removed
- Removed an old mechanic that raised the framerate limit in multiple steps when GPU usage was far below the lower threshold due to compatibility issues.

## [v4.4.2-patch1] - 2025-08-11

### Fixed
- Temporary workaround: Disabled the currently unused GetFlags functionality to prevent errors experienced by some users.
    - This feature is reserved for potential future use and does not affect current app functionality.

## [v4.4.2] - 2025-08-09

### Added
- Moved the delay settings (before increase/decrease) from global preferences to profile-specific settings. These can now be changed directly in the app.

### Changed
- Default maximum and minimum framerate limits updated:
    - Maximum FPS limit increased from 60 to 114.
    - Minimim FPS limit increased from 30 to 40.
        - Given the vastly improved experience when using LSFG with a base 40 FPS vs 30 FPS (~101.00 ms vs ~144.91 ms end-to-end latency respectively<sup><a href="#v4.4.2_ref1">1</a></sup>, along with improved visuals), this serves as a subtle hint to avoid capping below 40 FPS when possible. The app still works the same and can be used with a 30 FPS cap if needed.
- Default 'delay before increase' value raised from 3 seconds to 10 seconds.:
    - The microstutter that occurs when the game stalls during a framerate limit change can affect each game differently. A 10-second delay provides a less dynamic but smoother experience for new users and likely results in better performance in most games. The app still works the same and can be used with a 3 second delay if needed.

### References
<a id="v4.4.2_ref1">1. </a>[CptTombstone's post on r/losslessscaling](https://www.reddit.com/r/losslessscaling/comments/1mhfjnq/curious_about_the_latency_impact_of_lsfg_at/)

## [v4.4.1] - 2025-07-26

### Added
- Cooldown period for FPS cap increase logic
    - Previously, when GPU usage stayed below the lower threshold for 3 continuous seconds (default `delaybeforeincrease`), the app began increasing the FPS cap once per second, leading to noticeable 1-second microstutters until GPU usage stabilized.
    - Now, after each FPS cap increase, the app enters a cooldown period (equal to `delaybeforeincrease`) before attempting another increase, only if the low GPU usage condition still holds.
    - Effect: This change spaces out FPS cap increases, making transitions from high-demand to low-demand scenes relatively smoother.
        - Example: If 3 FPS cap increases are needed:
            - Before: 3 microstutters over 3 seconds -> very jarring
            - Now: 3 microstutters over 9 seconds -> less intrusive

### Changed
- Interal: Autopilot’s monitoring loop is now decoupled from the GUI update loop.
- Increased internal wait times at various stages to reduce unnecessary polling and reduce CPU overhead.

### Fixed
- Reduced CPU usage when idle and minimized to tray
    - The app previously consumed more CPU when idle due to continuous GUI updates.
    - GUI updates are now paused when minimized, resulting in significantly lower CPU usage while the app is idle in the background.

## [v4.4.0] - 2025-07-20

### Added
- Autopilot mode
    - Automatically activates the corresponding profile when a saved application is detected and stops when focus shifts away from the game.
    - Includes alternate dark-mode tray icons to indicate Autopilot status when minimized.
    - Disables the Start/Stop buttons while active. To add a new profile:
        - Disable Autopilot
        - Manually start the Global profile (or any profile to copy it's existing settings)
        - Switch to and from the target game
        - Click 'Add process to profiles'
        - Re-enable Autopilot
    - A warning will appear if no non-Global profiles are available, as Autopilot requires at least one.
- README and in-app FAQ updated with CPU usage mitigation steps:
    - In some specific scenarios (e.g., RTSS 'passive waiting' disabled for Global profile and a Twitch stream running in Chrome), the app may use 20–30% CPU even when idle.
    - Adding `DynamicFPSLimiter.exe` as a profile in RTSS with application detection set to None can reduce CPU usage to 1–3%. Use the **Shift** key + **Add** to directly add an active process for exclusion in RTSS.

### Changed
- V-Sync enabled for the app's GUI
- Minor GUI rearrangement to accommodate the Autopilot checkbox.
- Updated tooltips and in-app FAQ entries.
- Minor refactoring of functions/modules
- Adjusted default values for cap_ratio and GPU usage thresholds.

### Fix
- Profile name field is now read-only but selectable for copy/paste.
    - Useful for integration with tools like Lossless Scaling via its "filter" feature.

## [v4.3.0] - 2025-07-06

### Added
- Minimize to Tray and Tray Features
    - Option to start the app minimized to the system tray.
    - Tray icon now supports click-to-toggle:
        - Green arrow: App is stopped — click to Start.
        - Red arrow: App is running — click to Stop.
    - Hovering over the tray icon shows the current status, including:
        - Selected profile
        - Active limit method
        - Maximum FPS defined by that method
    - Right-clicking the tray icon opens a menu to switch profiles and limit methods directly.
- Improved FPS limit ramp-up for 'ratio' method
    - When transitioning from high GPU usage (demanding scenes) to low GPU usage (light scenes), the FPS limit now increases more quickly (-> in lesser number of steps).
    - Previously, the app would raise the FPS limit in single steps, causing multiple adjustments (and therefore mini-stutters) before reaching the optimal value.
    - With this update, the FPS limit can now increase in larger steps when appropriate, reducing the number of transitions needed to reach the maximum cap. This is dictated by how low the GPU usage is when the increase limit conditions are triggered.
    - The behavior remains conservative to avoid overshooting and triggering limit reductions right after.
- RTSS installation prompt and download warning
    - If RTSSHooks64.dll is missing, the app now shows a pop-up guiding the user to install RTSS.
    - A warning message has also been added, recommending users download the app only from the official GitHub page, as third-party sites may host outdated or unsafe versions.

### Changed
- Custom title bar implemented
    - Replaced the default OS title bar with a custom one.
    - The maximize button has been removed, as maximizing previously caused layout issues.
- Code cleanup
    - Refactored various functions into separate modules for better organization and maintainability.

### Fixed
- Start button color issue
    - Resolved a bug where the green color of the Start button was lost after clicking it twice.

### Known issues
- Profile display name appears editable
    - Although the profile name field looks editable, changes are not saved.
    - This is currently only a temporary cosmetic change and has no functional effect.

## [v4.2.0] - 2025-06-15
### Added
- Support for fractional framerate values in the custom FPS limit input.

### Changed
- Uses simplified python script to directly use RTSSHooks64.dll.

### Fixed
- Deleting a profile on DFL now deletes the corresponding profile on RTSS.

## [v4.1.0] - 2025-05-31
### Added
- Support for custom FPS limit input.
- New methods for calculating FPS limits using ratio and step approaches.
    - Users can configure both custom and calculated limits separately, allowing two different cap settings under the same profile and easy switching between them.
- Overhauled GUI theme for an improved user experience.
- Option to launch the app with Windows startup.
- Ability to set the default profile that loads on app launch.
- Warning when FPS limits are set below the minimum valid value (configurable in `settings.ini`).

### Changed
- Updated internal logic to use lists (sets) for managing FPS limit values.
- Refactored several parts of the original code for better maintainability.

## [v4.0.0] - 2025-05-09
### Added
- Complete UI overhaul: Redesigned and simplified interface with proper DPI scaling and a more efficient window layout.
- CPU usage monitoring: Dynamic framerate limit adjustments can now factor in CPU usage.
- Process-based profile creation: Create profiles directly from currently running processes.
- Added a beta FAQ tab

### Changed
- Reworked GPU usage retrieval for more accurate and efficient monitoring (no longer uses PowerShell).
- No RTSS configuration required; simply keep RTSS running in the background.
- Improved profile handling and more intuitive controls for daily use.
- Switched from using `rtss-cli.exe` to a direct Python wrapper for RTSS communication.
- Refined framerate adjustment logic to better respond to real-time system load.
- Improved repository structure and build instructions.
- Removed build output from repository; they can only be found in the Releases.
- `.ini` files are now located back to the main app directory.
- Does not spawn any persistent subprocesses.

## [v3.0.2] - 2025-04-16
### Added
- Compatibility for newer systems with PowerShell 7.x instead of Windows PowerShell 5.x.
- When adding a new profile in DynamicFPSLimiter and hitting Start, the profile will be created in RTSS if it was not already present.

### Changed
- Various minor changes to make the app more anti-virus friendly, including changes to how directories/paths are read.
    - `.ini` files are now located within the `_internal` folder.
- Removed distributable files (output from pyinstaller) from the source to keep the repository clean.

### Fixed
- Deleting a profile now updates internally without needing to select another profile.

### Known Issues
- App default settings may not match the default "Global" profile settings, but this may be ignored.

## [v3.0.1] - 2025-04-15
### Added
- Version information included in the executable.

### Changed
- Removed 'Execution Policy Bypass' from the persistent hidden PowerShell process.
- Converted PowerShell commands to single-line statements for improved compatibility.
- Streamlined the build process for cleaner and easier release preparation directly from the source.

## [v3.0.0] - 2025-04-13
### Added
- Integrated with @xanderfrangos's `rtss-cli.exe` to directly modify RTSS framerate limits - no more reliance on AutoHotkey or RTSS hotkeys.
- All framerate control functionality is now fully handled within the DynamicFPSLimiter app - no manual updates in RTSS required.
- "Detect Render GPU" button: Automatically detects the GPU used for game rendering by checking which GPU has the highest "3D engine" utilization at the time of clicking. Run this while the game is active to detect the render GPU.
- Profiles functionality: Allows users to manually create target profiles that are already configured in RTSS. This is required to make changes to non-Global target profiles in RTSS.

### Note
- Since RTSS runs as an elevated process, the app must be run as administrator to function properly.

## [v2.0.1] - 2025-04-11
### Changed
- Switched from `Get-Counter` to `Get-CimInstance` for GPU usage retrieval, resulting in faster performance metrics.
- Now includes all `engtype` values (e.g., 3D, Copy, Video, Compute) for a more comprehensive and accurate GPU utilization figure.
- This change may also reduce the performance impact of the app during gameplay.
- Renamed the button "Delay before increase/decrease" to "Instances before inc./dec." for better alignment with its actual function.
- Updated related tooltips to reflect the new terminology and provide clearer guidance.

### Fixed
- Improved support for regional number formatting differences (e.g., handling both `.` and `,` as decimal separators) to address None% GPU usage readout.
- Enhanced robustness by stripping whitespace and enforcing UTF-8 encoding for PowerShell outputs.

## [v2.0.0] - 2025-04-07
### Added
- Introduced a user-friendly GUI version of the original scripts, making the app accessible to general (non-technical) users.