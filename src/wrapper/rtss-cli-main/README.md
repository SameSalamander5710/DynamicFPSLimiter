# rtss-cli

Manipulate various settings and features from Rivatuner Statistics Server (RTSS) via CLI. Intended for use in automation scripts, like Sunshine and AutoHotKey.

Available features include:

- Get and set profile properties.
- Show and hide the stats overlay.
- Disable and enable the framerate limiter.
- Update the global framerate limit value.

*Note: RTSS runs as an elevated process. rtss-cli may not work as expected unless you also execute it as an elevated process. It's possible for rtss-cli to work with normal permissions, but RTSS's UI may not update to reflect the changes.*

## Usage

The following commands are supported by rtss-cli:
```
property:set            set a profile property
property:get            print a profile property
overlay:set             set overlay visibility
overlay:get             return overlay visibility
overlay:toggle          toggle overlay state
limiter:set             set if limiter is active
limiter:get             print value of limiter status
limiter:toggle          toggle limiter status
limit:set               set framerate limit for global profile
limit:offset            offset framerate limit for global profile
limit:get               print framerate limit for global profile
```
Commands that require addition arguments are described below:

```
property:set <profile> <property> <value>

    <profile>           string, such as "App.exe" or "Global" (without quotes)
    <property>          string, such as "FramerateLimit" or "AppDetectionLevel" (without quotes)
    <value>             integer to assign as the new value

property:get <profile> <property>

    <profile>           string, such as "App.exe" or "Global" (without quotes)
    <property>          string, such as "FramerateLimit" or "AppDetectionLevel" (without quotes)

overlay:set <value>     0 or 1
limiter:set <value>     0 or 1
limit:set <value>       integer to set the framerate limit to
limit:offset <value>    integer to offset the framerate limit with
```

When using `property:set` or `property:get`, the following properties can be used:
```
AppDetectionLevel                       0..3	- Application detection level
Implementation                          0..1	- On-Screen Display rendering mode
EnableFloatingInjectionAddress          0..1	- Stealth mode
EnableDynamicOffsetDetection            0..1	- Custom Direct3D support
FramerateLimit                          ....	- Framerate limit
FontWeight                              ....	- font weight for Raster3D On-Screen Display rendering mode
EnableOSD                               0..1	- On-Screen Display support
EnableBgnd                              0..1	- On-Screen Display shadow
EnableStat                              ....	- Show own statistics
BaseColor, BgndColor                    ....	- On-Screen Display palette
PositionX, PositionY                    ....	- On-Screen Display position
ZoomRatio                               1..8	- On-Screen Display zoom
CoordinateSpace                         0..1	- On-Screen Display coordinate space
```

## Examples

Set FramerateLimit for a specific profile to 90 (prints "OK"):
```
rtss-cli.exe profile:set AppName.exe FramerateLimit 90
```
Get ZoomRatio for the global profile (prints the value):
```
rtss-cli.exe profile:get Global ZoomRatio
```
Toggle overlay visibility (prints the new status as 0 or 1):
```
rtss-cli.exe overlay:toggle
```
Get the current global framerate limit (prints the value):
```
rtss-cli.exe limit:get
```
## Build

```
cl rtss-cli.cpp /O1 /MD /link /DEFAULTLIB:advapi32.lib /DEFAULTLIB:user32.lib
```