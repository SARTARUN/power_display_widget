# =============================================================================
# Python System Monitor Overlay
# Copyright (c) 2026 TP
# Licensed under the MIT License - see LICENSE file for details
# =============================================================================

import tkinter as tk
import psutil
import subprocess
import threading
import time
import queue
import logging
from dataclasses import dataclass
from enum import Enum
import ctypes
from ctypes import wintypes

# ===== LOGGING SETUP =====
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('overlay')

# Try to import pynvml
try:
    import pynvml
    PYNVML_AVAILABLE = True
except ImportError:
    PYNVML_AVAILABLE = False
    logger.warning("pynvml not installed, GPU monitoring will use nvidia-smi")

# ===== CONFIGURATION =====
REFRESH_RATE = 1000  # Update every 1 second
ALPHA = 0.75  # More transparent
COMPACT_MODE = True  # Set to False for larger display

# ===== DATA STRUCTURES =====
class DataType(Enum):
    """Types of monitoring data"""
    GPU_STATS = "gpu_stats"
    MEMORY = "memory"
    CPU = "cpu"

@dataclass
class MonitorData:
    """Container for monitor data with timestamp"""
    data_type: DataType
    value: any
    timestamp: float

# Thread-safe bounded queue for worker-to-GUI communication
data_queue = queue.Queue(maxsize=4) # Small buffer to prevent memory bloat if GUI lags

# ===== MONITOR CLASSES =====
class NvidiaGPUMonitor:
    """GPU monitoring using pynvml"""

    def __init__(self):
        self._cache = (0, 0)  # (utilization, temperature)
        self._last_query = 0
        self._min_interval = 0.5
        self._lock = threading.Lock()
        self._available = False
        self._handle = None

        if PYNVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self._handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                self._available = True
                logger.info("pynvml initialized successfully")
            except Exception as e:
                logger.warning(f"pynvml init failed: {e}")

        if not self._available:
            self._startupinfo = subprocess.STARTUPINFO()
            self._startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    def get_stats(self):
        """Get GPU utilization and temperature"""
        now = time.time()

        with self._lock:
            if (now - self._last_query) < self._min_interval:
                return self._cache

            if self._available and PYNVML_AVAILABLE:
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(self._handle)
                    temp = pynvml.nvmlDeviceGetTemperature(self._handle, pynvml.NVML_TEMPERATURE_GPU)
                    self._cache = (util.gpu, temp)
                    self._last_query = now
                except Exception:
                    self._available = False # Stop retrying, fall back to nvidia-smi
            else:
                try:
                    cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu",
                            "--format=csv,noheader,nounits"]
                    output = subprocess.check_output(cmd, startupinfo=self._startupinfo,
                                                    encoding='utf-8', timeout=1.5)
                    util, temp = output.strip().split(', ')
                    self._cache = (int(util), int(temp))
                    self._last_query = now
                except Exception as e:
                    logger.error(f"nvidia-smi failed: {e}")

        return self._cache

    def __del__(self):
        if self._available and PYNVML_AVAILABLE:
            try:
                pynvml.nvmlShutdown()
            except:
                pass

# ===== WORKER THREADS =====
def worker_gpu_stats():
    """Background GPU monitoring thread"""
    monitor = NvidiaGPUMonitor()
    # Get initial value immediately
    stats = monitor.get_stats()
    try:
        data_queue.put(MonitorData(DataType.GPU_STATS, stats, time.time()), timeout=0.1)
    except:
        pass

    while True:
        try:
            stats = monitor.get_stats()
            data_queue.put(MonitorData(DataType.GPU_STATS, stats, time.time()), timeout=0.1)
        except queue.Full:
            pass
        except Exception as e:
            logger.error(f"GPU worker error: {e}")
        time.sleep(0.8)

def worker_system_stats():
    """Background system monitoring thread"""
    # Get initial value immediately
    try:
        mem = psutil.virtual_memory()
        data_queue.put(MonitorData(DataType.MEMORY, mem.percent, time.time()), timeout=0.1)
    except:
        pass

    while True:
        try:
            # Memory stats
            mem = psutil.virtual_memory()
            data_queue.put(MonitorData(DataType.MEMORY, mem.percent, time.time()), timeout=0.1)
            # CPU stats
            cpu = psutil.cpu_percent(interval=1.0)  # blocking call — fine on background thread
            data_queue.put(MonitorData(DataType.CPU, cpu, time.time()), timeout=0.1)
        except queue.Full:
            pass
        except Exception as e:
            logger.error(f"System worker error: {e}")
        time.sleep(1.0)

# ===== GUI CLASS =====
class OverlayGUI:
    """Minimalistic overlay window - ultra compact"""

    COLORS = {
        'cpu': '#5FB3FF',
        'gpu': '#5FFFA6',
        'temp': '#FFB85F',
        'ram': '#FF8C5F',
    }

    def __init__(self):
        self._last_values = {
            'cpu': None,
            'gpu': None,
            'temp': None,
            'ram': None
        }

        self._topmost_counter = 0
        self._color_cache = {}
        self._click_through = True  # Start in click-through mode

        # Current data from workers
        self.current_gpu_data = (0, 0)
        self.current_ram = 0
        self.current_cpu = 0

        # Create window
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', ALPHA)
        self.root.config(bg='#1a1a1a')

        self.setup_ui()
        self.position_window()

        # Start workers before making click-through (faster initial data)
        t1 = threading.Thread(target=worker_gpu_stats, daemon=True)
        t2 = threading.Thread(target=worker_system_stats, daemon=True)
        t1.start()
        t2.start()

        # Small delay to let workers get first data
        self.root.after(100, self.make_click_through)
        # Start updates immediately
        self.root.after(200, self.update_stats)

    def make_click_through(self):
        """Make window click-through on Windows"""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # Get current window style
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            # Add WS_EX_TRANSPARENT (0x20) and WS_EX_LAYERED (0x80000)
            styles = styles | 0x80000 | 0x20
            # Set new style
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, styles)
            self._click_through = True
            logger.info("Click-through enabled")
        except Exception as e:
            logger.error(f"Failed to enable click-through: {e}")

    def make_clickable(self):
        """Make window clickable (for moving/closing)"""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # Get current window style
            styles = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            # Remove WS_EX_TRANSPARENT (0x20)
            styles = styles & ~0x20
            # Set new style
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, styles)
            self._click_through = False
            logger.info("Click-through disabled")
        except Exception as e:
            logger.error(f"Failed to disable click-through: {e}")

    def toggle_click_through(self, event=None):
        """Toggle between click-through and interactive mode"""
        if self._click_through:
            self.make_clickable()
            # Visual feedback - brighter border
            self.main_frame.config(highlightbackground='#00FF00', highlightthickness=2)
            # Auto-revert after 5 seconds
            self.root.after(5000, self.revert_to_click_through)
        else:
            self.make_click_through()
            self.main_frame.config(highlightbackground='#404040', highlightthickness=1)

    def revert_to_click_through(self):
        """Automatically revert to click-through mode"""
        if not self._click_through:
            self.make_click_through()
            self.main_frame.config(highlightbackground='#404040', highlightthickness=1)

    def setup_ui(self):
        """Ultra-compact horizontal bar layout with background panel"""
        if COMPACT_MODE:
            font_size = 9
            spacing = 6
        else:
            font_size = 11
            spacing = 10

        # Background panel with border for better visibility
        self.main_frame = tk.Frame(self.root,
                                   bg='#1a1a1a',  # Darker background
                                   highlightbackground='#404040',  # Border color
                                   highlightthickness=1,
                                   padx=10,
                                   pady=6)
        self.main_frame.pack()

        # Single horizontal row
        row = tk.Frame(self.main_frame, bg='#1a1a1a')
        row.pack()

        # CPU
        self.lbl_cpu = self._create_compact_label(row, "CPU", self.COLORS['cpu'], font_size)
        self._add_spacer(row, spacing)

        # GPU
        self.lbl_gpu = self._create_compact_label(row, "GPU", self.COLORS['gpu'], font_size)
        self._add_spacer(row, spacing)

        # TEMP
        self.lbl_temp = self._create_compact_label(row, "TEMP", self.COLORS['temp'], font_size)
        self._add_spacer(row, spacing)

        # RAM
        self.lbl_ram = self._create_compact_label(row, "RAM", self.COLORS['ram'], font_size)

        # Bind Ctrl+Shift+Click to toggle click-through mode
        for widget in [self.root, self.main_frame, row]:
            widget.bind("<Control-Shift-Button-1>", self.toggle_click_through)
            widget.bind("<Button-1>", self.start_move)
            widget.bind("<B1-Motion>", self.do_move)
            widget.bind("<Button-3>", self.exit_app)
            widget.bind("<Double-Button-1>", self.toggle_compact)

    def _create_compact_label(self, parent, name, color, font_size):
        """Create ultra-compact metric display: NAME 00%"""
        frame = tk.Frame(parent, bg='#1a1a1a')
        frame.pack(side=tk.LEFT)

        # Label (name)
        lbl_name = tk.Label(frame, text=name,
                           font=('Consolas', font_size-1, 'bold'),
                           bg='#1a1a1a',
                           fg='#999999')  # Lighter gray for better contrast
        lbl_name.pack(side=tk.LEFT, padx=(0, 3))

        # Value with fixed width to prevent cutoff
        lbl_value = tk.Label(frame, text="--",
                            font=('Consolas', font_size, 'bold'),
                            bg='#1a1a1a',
                            fg=color,
                            width=4,  # Fixed width for up to "100%"
                            anchor='w')  # Left align
        lbl_value.pack(side=tk.LEFT)

        # Bind events
        for w in [frame, lbl_name, lbl_value]:
            w.bind("<Control-Shift-Button-1>", self.toggle_click_through)
            w.bind("<Button-1>", self.start_move)
            w.bind("<B1-Motion>", self.do_move)
            w.bind("<Button-3>", self.exit_app)
            w.bind("<Double-Button-1>", self.toggle_compact)

        return lbl_value

    def _add_spacer(self, parent, width):
        """Add horizontal spacer"""
        spacer = tk.Label(parent, text="|",
                         font=('Consolas', 9),
                         bg='#1a1a1a',
                         fg='#404040')  # More visible separator
        spacer.pack(side=tk.LEFT, padx=width)
        spacer.bind("<Control-Shift-Button-1>", self.toggle_click_through)
        spacer.bind("<Button-1>", self.start_move)
        spacer.bind("<B1-Motion>", self.do_move)
        spacer.bind("<Button-3>", self.exit_app)

    def position_window(self):
        """Position in top-right corner of rightmost display"""
        self.root.update_idletasks()
        w = self.main_frame.winfo_reqwidth()
        h = self.main_frame.winfo_reqheight()

        try:
            user32 = ctypes.windll.user32

            # Structure for monitor info
            class RECT(ctypes.Structure):
                _fields_ = [
                    ('left', ctypes.c_long),
                    ('top', ctypes.c_long),
                    ('right', ctypes.c_long),
                    ('bottom', ctypes.c_long)
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', RECT),
                    ('rcWork', RECT),
                    ('dwFlags', wintypes.DWORD)
                ]

            monitors = []

            def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)

                if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
                    monitors.append({
                        'left': info.rcMonitor.left,
                        'top': info.rcMonitor.top,
                        'right': info.rcMonitor.right,
                    })
                return True

            # Enum all monitors
            MONITOR_ENUM_PROC = ctypes.WINFUNCTYPE(
                ctypes.c_int,
                wintypes.HMONITOR,
                wintypes.HDC,
                ctypes.POINTER(RECT),
                wintypes.LPARAM
            )

            user32.EnumDisplayMonitors(None, None, MONITOR_ENUM_PROC(callback), 0)

            logger.info(f"Detected {len(monitors)} monitor(s)")
            for i, mon in enumerate(monitors):
                logger.info(f"Monitor {i}: left={mon['left']}, right={mon['right']}, top={mon['top']}")

            if len(monitors) > 0:
                # Find the monitor with the highest 'right' value (rightmost)
                rightmost_monitor = max(monitors, key=lambda m: m['right'])

                # Position on rightmost monitor
                x = rightmost_monitor['right'] - w - 10
                y = rightmost_monitor['top'] + 50
<<<<<<< HEAD
                
                # Verify coordinates against the actual virtual screen bounds.
                # When no display is connected, Windows or Remote Desktop might present
                # phantom monitors resulting in off-screen placement.
                SM_XVIRTUALSCREEN = user32.GetSystemMetrics(76)
                SM_YVIRTUALSCREEN = user32.GetSystemMetrics(77)
                SM_CXVIRTUALSCREEN = user32.GetSystemMetrics(78)
                SM_CYVIRTUALSCREEN = user32.GetSystemMetrics(79)
                
                # Fallback to absolute boundaries if placed completely out of bounds
                if not (SM_XVIRTUALSCREEN <= x <= SM_XVIRTUALSCREEN + SM_CXVIRTUALSCREEN - w):
                    x = max(SM_XVIRTUALSCREEN, min(x, SM_XVIRTUALSCREEN + SM_CXVIRTUALSCREEN - w - 10))
                if not (SM_YVIRTUALSCREEN <= y <= SM_YVIRTUALSCREEN + SM_CYVIRTUALSCREEN - h):
                    y = max(SM_YVIRTUALSCREEN, min(y, SM_YVIRTUALSCREEN + SM_CYVIRTUALSCREEN - h - 10))
                
=======

>>>>>>> 939b8911f10d9a77adad84bdba396caed2cb59cb
                self.root.geometry(f'{w}x{h}+{x}+{y}')
                logger.info(f"Positioned on rightmost display at ({x}, {y})")
                return

        except Exception as e:
            logger.error(f"Monitor detection failed: {e}")

        # Fallback
        screen_width = self.root.winfo_screenwidth()
        x = screen_width - w - 10
        y = 50
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        logger.info(f"Fallback positioning at ({x}, {y})")

    def update_stats(self):
        """Optimized update cycle"""
        # Pull new data from queue
        try:
            while True:
                data = data_queue.get_nowait()
                if data.data_type == DataType.GPU_STATS:
                    self.current_gpu_data = data.value
                elif data.data_type == DataType.MEMORY:
                    self.current_ram = data.value
                elif data.data_type == DataType.CPU:
                    self.current_cpu = data.value
        except queue.Empty:
            pass

        # Get CPU usage (use interval=None for instant read from cache)
        cpu_usage = round(self.current_cpu)
        if cpu_usage == 0.0:
            cpu_usage = psutil.cpu_percent(interval=0.1)  # First call needs interval

        gpu_load, gpu_temp = self.current_gpu_data
        ram_usage = self.current_ram

        # Update only if changed (reduce flicker)
        if cpu_usage != self._last_values['cpu']:
            color = self._get_color(cpu_usage, self.COLORS['cpu'])
            self.lbl_cpu.config(text=f"{cpu_usage:.0f}%", fg=color)
            self._last_values['cpu'] = cpu_usage

        if gpu_load != self._last_values['gpu']:
            color = self._get_color(gpu_load, self.COLORS['gpu'])
            self.lbl_gpu.config(text=f"{gpu_load:.0f}%", fg=color)
            self._last_values['gpu'] = gpu_load

        if gpu_temp != self._last_values['temp']:
            color = self._get_temp_color(gpu_temp)
            self.lbl_temp.config(text=f"{gpu_temp}°", fg=color)
            self._last_values['temp'] = gpu_temp

        if ram_usage != self._last_values['ram']:
            color = self._get_color(ram_usage, self.COLORS['ram'])
            self.lbl_ram.config(text=f"{ram_usage:.0f}%", fg=color)
            self._last_values['ram'] = ram_usage

        # Keep topmost
        self._topmost_counter += 1
        if self._topmost_counter >= 30:
            self.root.attributes('-topmost', True)
            self._topmost_counter = 0

        self.root.after(REFRESH_RATE, self.update_stats)

    def _get_color(self, value, base_color):
        """Dynamic color based on load"""
        if value < 50:
            return base_color
        elif value < 80:
            return self.COLORS['temp']  # Yellow warning
        else:
            return '#FF5F5F'  # Red alert

    def _get_temp_color(self, temp):
        """Temperature-specific coloring"""
        if temp < 60:
            return self.COLORS['temp']
        elif temp < 75:
            return '#FFA05F'  # Orange
        else:
            return '#FF5F5F'  # Red

    def toggle_compact(self, event):
        """Toggle between compact and normal mode"""
        global COMPACT_MODE
        COMPACT_MODE = not COMPACT_MODE
        self.root.destroy()
        new_overlay = OverlayGUI()
        new_overlay.run()

    def start_move(self, event):
        if not self._click_through:
            self.root.x = event.x
            self.root.y = event.y

    def do_move(self, event):
        if not self._click_through:
            x = event.x_root - self.root.x
            y = event.y_root - self.root.y
            self.root.geometry(f"+{x}+{y}")

    def exit_app(self, event):
        if not self._click_through:
            self.root.quit()

    def run(self):
        """Start the overlay"""
        self.root.mainloop()

# ===== MAIN ENTRY POINT =====
if __name__ == '__main__':
    try:
        overlay = OverlayGUI()
        overlay.run()
    except Exception as e:
        logger.exception("Fatal error in overlay")
        raise
