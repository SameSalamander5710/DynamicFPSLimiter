# CHANGELOG

## [v4.2.1] - 2025-XX-XX

### To Add
- Popup if no RTSS; also info about downloading only from GitHub.
- Tray functions

### Added
- New feature specific for 'ratio' method. (Add explanation)

### Fixed
- Loss of green colour for start button after clicking it twice.

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