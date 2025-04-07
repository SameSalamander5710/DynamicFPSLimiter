# RTSS Hotkey Setup Guide

This guide will walk you through setting up hotkeys in RTSS (RivaTuner Statistics Server) to control the framerate limit dynamically.

## Step-by-Step Setup

### 1. Open the RTSS Application

Launch the RTSS application on your computer.

### 2. Access the RTSS Properties

At the bottom of the RTSS app, click **Setup** to open the RTSS properties window.

<img src="/Docs/Images/RTSS_01.png" width="45%" />

### 3. Enable Hotkeys Plugin

In the RTSS properties window:
- Navigate to the Plugins tab.
- Check the tick mark next to HotkeyHandler.dll to enable hotkey functionality.

<p float="left">
  <img src="/Docs/Images/RTSS_03.png" width="45%" />
  <img src="/Docs/Images/RTSS_04.png" width="45%" />
</p>

### 4. Open Hotkey Handler Properties

- Double-click on HotkeyHandler.dll or click on the Setup button at the bottom to open the Hotkey Handler properties window.

### 5. Configure Programmable Profile Modifier

- At the bottom of the Hotkey Handler properties window, under Profiles, click the three dots button (...) to open the Programmable Profile Modifier properties.

<img src="/Docs/Images/RTSS_05.png" width="45%" />

### 6. Set Framerate Increase Hotkey

- In the Preset dropdown menu, select increase framerate limit.
- Add a description that makes it easy to identify the hotkey later (e.g., "Increase framerate limit").
- Set the Target Profile as needed (this can be the profile for a specific game or empty for global profile).
- Set the Modifier Value to the framerate step value you want (e.g., increase by 5 FPS).

<p float="left">
  <img src="/Docs/Images/RTSS_06.png" width="45%" />
  <img src="/Docs/Images/RTSS_07.png" width="45%" />
</p>

> [!TIP]
> If you want to change the target profile between different games, you can add the game's name to the description. This way, you can copy-paste the description to apply the hotkey configuration for different profiles as needed.

<img src="/Docs/Images/RTSS_08.png" width="45%" />

### 7. Set Framerate Decrease Hotkey

- Repeat the previous steps for the next Programmable Profile Modifier, but this time select decrease framerate limit from the Preset dropdown menu.
- Set the appropriate Target Profile, Description, and Modifier Value for decreasing the framerate limit (e.g., increase by -5 FPS).

### 8. Assign Hotkey Buttons

- After setting up the increase and decrease modifiers, click on the input field labeled 'None' next to each modifier.
- Press the button on your keyboard or mouse that you want to use as the hotkey for each modifier.

<p float="left">
  <img src="/Docs/Images/RTSS_09.png" width="45%" />
  <img src="/Docs/Images/RTSS_10.png" width="45%" />
</p>

### 9. Finalize Hotkey Setup

- Once both hotkeys for increasing and decreasing the framerate limit are assigned, click OK to close the Hotkey Handler properties window.
- Click OK again in the RTSS properties window to save your settings.

### 10. Test the Hotkeys

Your hotkeys are now set! Confirm that they work by testing them with the DynamicFPSLimiter app. If the hotkeys increase and decrease the framerate limit as expected, you're ready to go.

Check [https://www.autohotkey.com/docs/v2/lib/Send.htm](https://www.autohotkey.com/docs/v2/lib/Send.htm) for AutoHotKey key names. 

<img src="/Docs/Images/RTSS_11.png" width="90%" />
