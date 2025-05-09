# How It Works

The Dynamic FPS Limiter app dynamically adjusts the FPS cap in real-time based on GPU and CPU usage to optimize performance and reduce input lag. Below is an explanation of the logic used to determine when to increase or decrease the FPS cap.

---

## Key Variables
- **GPU Usage Thresholds**:
  - `gpucutofffordecrease`: The GPU usage percentage above which the FPS cap is decreased.
  - `gpucutoffforincrease`: The GPU usage percentage below which the FPS cap is increased.

- **CPU Usage Thresholds**:
  - `cpucutofffordecrease`: The CPU usage percentage above which the FPS cap is decreased.
  - `cpucutoffforincrease`: The CPU usage percentage below which the FPS cap is increased.

- **Delays**:
  - `delaybeforedecrease`: The number of consecutive seconds the usage must exceed the decrease threshold before lowering the FPS cap.
  - `delaybeforeincrease`: The number of consecutive seconds the usage must stay below the increase threshold before raising the FPS cap.

- **Other Parameters**:
  - `minvalidgpu` and `minvalidfps`: Minimum valid GPU usage and FPS values to prevent adjustments during loading screens or other low-performance states.

---

## Logic for Adjusting FPS Cap

### 1. **Decrease FPS Cap**
The app decreases the FPS cap when:
- GPU usage exceeds `gpucutofffordecrease` for at least `delaybeforedecrease` seconds, **or**
- CPU usage exceeds `cpucutofffordecrease` for at least `delaybeforedecrease` seconds.

If either condition is met:
- The FPS cap is reduced by a multiple of `capstep`, calculated as:

`X = ceil(((maxcap + CurrentFPSOffset) - fps_mean) / capstep)`

- `X` ensures the FPS cap is reduced proportionally to the difference between the current FPS and the target FPS. `X` takes a minimum value of 1.
- The new FPS cap is clamped to ensure it does not go below `mincap`.

---

### 2. **Increase FPS Cap**
The app increases the FPS cap when:
- GPU usage stays below `gpucutoffforincrease` for at least `delaybeforeincrease` seconds, **and**
- CPU usage stays below `cpucutoffforincrease` for at least `delaybeforeincrease` seconds.

If both conditions are met:
- The FPS cap is increased by `capstep`.
- The new FPS cap is clamped to ensure it does not exceed `maxcap`.

---

## Failsafe Mechanisms
1. **Ignore Low Usage**:
 - Adjustments are skipped if GPU usage is below `minvalidgpu` or FPS is below `minvalidfps`. This prevents adjustments during loading screens or other low-performance states.

2. **Clamping FPS Cap**:
 - The FPS cap is always clamped between `mincap` and `maxcap` to ensure stability.

3. **Delay Mechanism**:
 - The app uses `delaybeforedecrease` and `delaybeforeincrease` to avoid making rapid or unnecessary adjustments. This ensures the system has time to stabilize before changes are applied.

---

## Real-Time Monitoring
- The app continuously monitors GPU and CPU usage, as well as the current FPS, in real-time.

- **Polling Rate/Interval**:
  - The app collects GPU and CPU usage data at regular intervals, defined by `gpupollinginterval` and `cpupollinginterval` (in milliseconds), and stores them in rolling buffers.
  - For example, if `gpupollinginterval` is set to 100 ms, the app will query the GPU usage 10 times per second.
  - The polling interval determines how frequently the rolling buffers are updated with new data, upto a maximum length (e.g., 20 values for 2 second duration).

- **Percentile Calculation**:
  - To make decisions based on trends rather than outliers, the app calculates the percentile of the usage data stored in the rolling buffers.
  - The `gpupercentile` and `cpupercentile` settings define the percentile to be calculated (e.g., 70th percentile).
  - The percentile calculation ensures that the app reacts to sustained usage patterns rather than brief spikes or dips in usage.
  - For example, if the 70th percentile of GPU usage is 85%, it means that 70% of the recorded usage values are below 85%, and 30% are above it.

- **Adjustments Based on Trends**:
  - The app queries the percentile values every second and adds them to a new buffer.
  - These buffers are essentially lists that hold the most recent usage values for a fixed number of samples.
  - This is used to determine whether GPU or CPU usage has consistently `(delaybeforedecrease, delaybeforeincrease)` exceeded or fallen below the thresholds (`gpucutofffordecrease`, `gpucutoffforincrease`, `cpucutofffordecrease`, `cpucutoffforincrease`).
  - This approach ensures that adjustments to the FPS cap are based on sustained trends rather than transient fluctuations.

By combining rolling buffers, polling intervals, and percentile calculations, the app achieves a balance between responsiveness and stability, ensuring that FPS cap adjustments are both timely and reliable.

---

## Summary
The app dynamically adjusts the FPS cap to balance performance and responsiveness:
- **Decrease FPS Cap**: When GPU or CPU usage is too high, the FPS cap is lowered to reduce system load.
- **Increase FPS Cap**: When GPU and CPU usage are low, the FPS cap is raised to allow higher frame rates.

This logic ensures a smoother and more responsive gaming experience while preventing GPU/CPU saturation.

