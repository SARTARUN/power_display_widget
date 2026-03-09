# Python System Monitor Overlay

A highly transparent, minimalist, and lightweight system monitor overlay for Windows. It floats above your other windows to give you real-time tracking of your CPU, GPU, Temperature, and RAM usage.

## Features
- **Ultra-Compact Design**: Takes up minimal screen space.
- **Click-Through Mode**: Can be made completely unclickable so it never gets in the way of your games or work.
- **Dynamic Colors**: Text colors change based on system loads and temperatures.
- **Auto-Positioning**: Automatically snaps to the top-right of your main display.

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
If you want the overlay to launch automatically every time you log into Windows:
1. Right-click the `overlay.pyw` file and select **Create shortcut**.
2. Press `Windows Key + R` to open the **Run** dialog.
3. Type `shell:startup` and press **Enter**. This will open your user's Startup folder.
4. Drag and drop (or cut and paste) the new `overlay.pyw - Shortcut` file into this Startup folder.

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
