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
