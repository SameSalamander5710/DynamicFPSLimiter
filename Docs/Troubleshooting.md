# Troubleshooting

Having issues? Here's a list of common problems and how to address them.

## 1. GUI Performance Impact
The app uses GPU resources to render its GUI. On lower-end systems or when GPU load is high, this might slightly affect performance.

**Solution:**

Keep the app running minimized to reduce GPU impact.

## 2. Conflicts with Lossless Scaling

When running Lossless Scaling alongside this app—especially on multi-monitor setups—you might notice slideshow-like behavior in LS.

**Solution:**

If this happens, keep the DynamicFPSLimiter app minimized during gameplay to avoid this conflict.

## 3. App Hangs on Startup

In rare cases, the app may freeze or hang within the first few seconds after starting.

**Solution:**

If this occurs, simply close the app and restart it. There is currently no fix for this.

## 4. FPS Cap Display Out of Sync

This issue has been potentially fixed, but may still occur in rare cases. Sometimes the *Current FPS Cap* displayed in the app can fall out of sync with the actual frame rate limit in RTSS—typically if the app is stopped and restarted mid-session.

**Solution:**

Click Stop, manually adjust the FPS cap in RTSS as needed, and then Start again.

## 5. Dual GPU Systems

The app calculates GPU usage by summing '3D Engine' and 'Copy' loads for each GPU and then selecting the highest value. This hasn't been fully tested on systems where Lossless Scaling runs on a secondary GPU.

**Behavior to expect:**

If any one GPU is above the upper usage threshold, the FPS will decrease to reduce GPU loads. The app will only allow an FPS increase when both GPUs are below the lower threshold. This could result in conservative FPS modulation.

## 6. Game Drops to Very Low FPS After Starting

If your game suddenly drops to extremely low FPS right after launching the app, it's likely due to an incorrect RTSS profile or cap setting.

**Example:**

If your RTSS profile starts with a limit of 0 (uncapped), and the app sends a "increase FPS" command of 5, your FPS cap becomes 5.

**Solution:**

Make sure RTSS is configured with a valid starting cap for the correct game profile.

### Still Need Help?

If none of the above resolves your issue, feel free to open a post in the Issues or Discussions section on GitHub.
