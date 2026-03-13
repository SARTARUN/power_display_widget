# Python System Monitor Overlay
A highly transparent, minimalist, and lightweight system monitor overlay for Windows. It floats above your other windows to give you real-time tracking of your CPU, GPU, Temperature, and RAM usage.

## Features
- **Ultra-Compact Design**: Takes up minimal screen space (~4 MB memory usage).
- **Click-Through Mode**: Can be made completely unclickable so it never gets in the way of your games or work.
- **Dynamic Colors**: Text colors change based on system loads and temperatures.
- **Auto-Positioning**: Automatically snaps to the top-right of your rightmost display.
- **Multi-Monitor Support**: Detects all connected displays and positions correctly, even when a monitor is disconnected.
- **Boot-Safe GPU Monitoring**: Handles NVIDIA driver initialization delays at startup gracefully.

## Installation
1. Ensure you have Python installed.
2. Install the required dependencies:
   ```bash
   pip install psutil pynvml
   ```
   *(Note: `pynvml` is optional but highly recommended for NVIDIA GPU monitoring).*
3. Run the script:
   ```bash
   pythonw overlay.pyw
   ```

## Run on Startup (Windows)
For the most reliable startup with no delay, use **Task Scheduler**:

1. Open **Task Scheduler** → click *Create Basic Task* in the right panel.
2. Give it a name (e.g. `Overlay`) and click **Next**.
3. Trigger: select **When I log on**, click **Next**.
4. Action: select **Start a program**, click **Next**.
   - **Program/script**: path to `pythonw.exe`, for example:
     ```
     C:\Users\YourName\AppData\Local\Programs\Python\Python312\pythonw.exe
     ```
   - **Add arguments**: path to the script, for example:
     ```
     "C:\path\to\overlay.pyw"
     ```
5. Click **Finish**, then open the task's **Properties**:
   - **General** tab → check *Run only when user is logged on*.
   - **Conditions** tab → uncheck *Start the task only if the computer is on AC power*.

> **Note:** Unlike the Startup folder, Task Scheduler runs the program immediately at logon with no Windows-imposed delay.

## Controls & Shortcuts
The overlay starts in **Click-Through Mode** by default. Use the following shortcuts to interact with it:

- **Ctrl + Shift + Left Click**: Toggle between Click-Through and Interactive Mode. (The border turns green when interactive).
- **Left Click & Drag**: Move the overlay around your screen.
- **Right Click**: Close the application.
- **Double Left Click**: Toggle between "Compact" and "Normal" font sizes.

## Configuration
You can customize the overlay by editing the constants at the top of `overlay.pyw` (under the `# ===== CONFIGURATION =====` section):

| Setting | Default | Description |
|---|---|---|
| `REFRESH_RATE` | `1000` | How often the display updates, in milliseconds. Lower = faster but more CPU usage. |
| `ALPHA` | `0.75` | Transparency of the overlay. Range is `0.0` (invisible) to `1.0` (fully opaque). |
| `COMPACT_MODE` | `True` | Set to `False` to start in larger font mode by default. Can also be toggled at runtime with Double-Click. |
| `STARTUP_DELAY` | `5` | Seconds to wait before querying the GPU after launch. Prevents stale readings on boot while the NVIDIA driver finishes initializing. |

### Changing Colors
The display colors for each metric can be changed by editing the `COLORS` dictionary inside the `OverlayGUI` class:

```python
COLORS = {
    'cpu': '#5FB3FF',   # Blue  — CPU usage label
    'gpu': '#5FFFA6',   # Green — GPU usage label
    'temp': '#FFB85F',  # Amber — Temperature label
    'ram': '#FF8C5F',   # Orange — RAM usage label
}
```

Colors use standard hex color codes. You can pick colors from any color picker tool (e.g., [htmlcolorcodes.com](https://htmlcolorcodes.com)).

### Load Warning Thresholds (CPU, GPU, RAM)
By default, metric colors change dynamically based on load percentage. You can adjust these thresholds in the `_get_color()` method inside `OverlayGUI`:

```python
def _get_color(self, value, base_color):
    if value < 50:    # ← Below this: shows the normal base color
        return base_color
    elif value < 80:  # ← Below this: turns amber/yellow as a warning
        return self.COLORS['temp']
    else:             # ← Above this: turns red as a critical alert
        return '#FF5F5F'
```

| Load % | Color | Meaning |
|---|---|---|
| Below 50% | Base color (blue/green/orange) | Normal |
| 50% – 79% | Amber `#FFB85F` | Warning |
| 80% and above | Red `#FF5F5F` | Critical |

---

### Temperature Warning Thresholds (GPU)
GPU temperature uses its own separate color scale, adjustable in `_get_temp_color()`:

```python
def _get_temp_color(self, temp):
    if temp < 60:    # ← Below this: normal amber color
        return self.COLORS['temp']
    elif temp < 75:  # ← Below this: orange warning
        return '#FFA05F'
    else:            # ← Above this: red critical alert
        return '#FF5F5F'
```

| Temperature | Color | Meaning |
|---|---|---|
| Below 60°C | Amber `#FFB85F` | Normal |
| 60°C – 74°C | Orange `#FFA05F` | Warning |
| 75°C and above | Red `#FF5F5F` | Critical — check cooling |
