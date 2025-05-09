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

## 3. Dual GPU Systems

The app calculates GPU usage by summing '3D Engine' loads for each GPU and then selecting the highest value. For dual GPU systems, use 'Detect Render GPU' with the game running, to automatically detect the GPU rendering the game, based on the GPU with the highest "3D engine" utilization.

### Still Need Help?

If none of the above resolves your issue, feel free to open a post in the Issues or Discussions section on GitHub.
