"""
╔══════════════════════════════════════════════════════════════════╗
║   T18 — Hardware Diagnostic System                             ║
║   Vehicle: TT 1800R — Bluetooth 4WD Robot Car                  ║
║                                                                ║
║   BLE Address : A0:85:E0:1C:3E:10                              ║
║   Write UUID  : FFE2 (response=True)                           ║
║   Notify UUID : FFE1                                           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import asyncio
import threading
import queue
import time
from datetime import datetime

import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont

try:
    from bleak import BleakClient, BleakScanner
    BLEAK_OK = True
except ImportError:
    BLEAK_OK = False

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION — DO NOT CHANGE BLE SETTINGS
# ══════════════════════════════════════════════════════════════════

BLE_ADDRESS  = "A0:85:E0:1C:3E:10"
UUID_WRITE   = "0000ffe2-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY  = "0000ffe1-0000-1000-8000-00805f9b34fb"

# ══════════════════════════════════════════════════════════════════
#  COLOR PALETTE
# ══════════════════════════════════════════════════════════════════

C = {
    "bg_dark":      "#0d1117",
    "bg_panel":     "#161b22",
    "bg_card":      "#1c2333",
    "bg_input":     "#21262d",
    "border":       "#30363d",
    "border_light": "#3d444d",
    "text":         "#e6edf3",
    "text_dim":     "#8b949e",
    "text_muted":   "#484f58",
    "accent":       "#58a6ff",
    "accent_hover": "#79c0ff",
    "green":        "#3fb950",
    "green_dim":    "#1a4721",
    "red":          "#f85149",
    "red_dim":      "#5c1a1a",
    "orange":       "#d29922",
    "blue_led":     "#4da6ff",
    "blue_dim":     "#1a3a5c",
    "yellow":       "#e3b341",
    "purple":       "#bc8cff",
    "green_led":    "#00ff66",
    "red_led":      "#ff3333",
    "motor_arrow":  "#ff9f43",
    "chassis":      "#2d333b",
    "chassis_edge": "#444c56",
    "wheel":        "#1a1e24",
}


# ══════════════════════════════════════════════════════════════════
#  BLE COMMUNICATION THREAD
# ══════════════════════════════════════════════════════════════════

class BLEWorker:
    """Runs BLE operations in a background thread with its own event loop."""

    def __init__(self, gui_queue: queue.Queue):
        self.gui_queue = gui_queue
        self.cmd_queue = queue.Queue()
        self.client = None
        self.loop = None
        self.thread = None
        self.connected = False
        self.running = False
        self.auto_reconnect = True
        self._user_requested_disconnect = False
        self._last_traffic_time = 0.0
        self._reconnect_at = 0.0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

    def send_command(self, cmd: str):
        self.cmd_queue.put(("CMD", cmd))

    def request_connect(self):
        self._user_requested_disconnect = False
        self._reconnect_at = 0.0
        self.cmd_queue.put(("CONNECT", None))

    def request_disconnect(self):
        self._user_requested_disconnect = True
        self._reconnect_at = 0.0
        self.cmd_queue.put(("DISCONNECT", None))

    def set_auto_reconnect(self, enabled: bool):
        self.auto_reconnect = enabled
        if not enabled:
            self._reconnect_at = 0.0

    def _post(self, msg_type: str, data=None):
        self.gui_queue.put((msg_type, data))

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._worker())

    def _on_disconnected(self, client):
        """Bleak client disconnected callback (invoked from Bleak thread)."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._handle_link_loss)

    def _handle_link_loss(self):
        if not self.connected:
            return
        self.connected = False
        self.client = None
        self._post("STATUS", "disconnected")
        self._post("LOG_WARN", "BLE connection dropped / timed out")
        if self.auto_reconnect and not self._user_requested_disconnect:
            self._reconnect_at = time.time() + 2.0
            self._post("LOG_INFO", "Auto-reconnect scheduled in 2s...")

    async def _worker(self):
        while self.running:
            # Process incoming command if available
            try:
                action, payload = self.cmd_queue.get_nowait()
                if action == "CONNECT":
                    await self._connect()
                elif action == "DISCONNECT":
                    await self._disconnect()
                elif action == "CMD":
                    await self._send(payload)
            except queue.Empty:
                pass

            now = time.time()

            # ── Heartbeat Keep-Alive ──
            # If connected, ensure traffic occurs at least every 2.5 seconds to prevent
            # Windows GATT or BLE module idle timeout (10-20s sleep).
            if self.connected and self.client and self.client.is_connected:
                if now - self._last_traffic_time >= 2.5:
                    await self._send("?", is_heartbeat=True)

            # ── Auto-Reconnect ──
            elif (not self.connected and self.auto_reconnect
                  and not self._user_requested_disconnect
                  and self._reconnect_at > 0 and now >= self._reconnect_at):
                self._reconnect_at = 0.0
                self._post("LOG_INFO", "Attempting automatic reconnection...")
                await self._connect()

            await asyncio.sleep(0.05)

    async def _on_notify(self, sender, data: bytearray):
        self._last_traffic_time = time.time()
        try:
            text = data.decode("utf-8", errors="replace").strip()
            if text:
                self._post("RX", text)
        except Exception:
            pass

    async def _connect(self):
        if self.connected:
            return
        self._post("STATUS", "connecting")
        self._post("LOG_INFO", f"Connecting to {BLE_ADDRESS}...")
        try:
            self.client = BleakClient(
                BLE_ADDRESS,
                disconnected_callback=self._on_disconnected,
                timeout=12.0
            )
            await self.client.connect()
            if self.client.is_connected:
                self.connected = True
                self._last_traffic_time = time.time()
                self._post("STATUS", "connected")
                self._post("LOG_OK", f"Connected to TT 1800R ({BLE_ADDRESS})")
                # Subscribe to notifications
                try:
                    await self.client.start_notify(UUID_NOTIFY, self._on_notify)
                    self._post("LOG_OK", "Telemetry stream active (FFE1)")
                    # Immediate sync query & establish traffic
                    await self._send("?", is_heartbeat=True)
                except Exception as e:
                    self._post("LOG_WARN", f"Notify subscribe failed: {e}")
            else:
                self.connected = False
                self.client = None
                self._post("STATUS", "disconnected")
                self._post("LOG_ERR", "Connection failed — no link established")
                if self.auto_reconnect and not self._user_requested_disconnect:
                    self._reconnect_at = time.time() + 3.0
        except Exception as e:
            self.connected = False
            self.client = None
            self._post("STATUS", "disconnected")
            self._post("LOG_ERR", f"Connection failed: {e}")
            if self.auto_reconnect and not self._user_requested_disconnect:
                self._reconnect_at = time.time() + 3.0

    async def _disconnect(self):
        if self.client and self.client.is_connected:
            try:
                await self.client.write_gatt_char(UUID_WRITE, b"S", response=True)
            except Exception:
                pass
            try:
                await self.client.disconnect()
            except Exception:
                pass
        self.connected = False
        self.client = None
        self._post("STATUS", "disconnected")
        self._post("LOG_INFO", "Disconnected from TT 1800R")

    async def _send(self, cmd: str, is_heartbeat: bool = False):
        if not self.connected or not self.client or not self.client.is_connected:
            if not is_heartbeat:
                self._post("LOG_ERR", f"Cannot send '{cmd}' — not connected")
            return
        try:
            self._last_traffic_time = time.time()
            await self.client.write_gatt_char(
                UUID_WRITE,
                cmd.encode("ascii"),
                response=True
            )
            if not is_heartbeat:
                self._post("TX", cmd)
            else:
                self._post("HEARTBEAT_ACK", None)
        except Exception as e:
            if not is_heartbeat:
                self._post("LOG_ERR", f"Write failed: {e}")
            # Check if connection dropped
            if self.client and not self.client.is_connected:
                self._handle_link_loss()


# ══════════════════════════════════════════════════════════════════
#  VEHICLE CANVAS — Top-Down Visualization
# ══════════════════════════════════════════════════════════════════

class VehicleCanvas(tk.Canvas):
    """Draws a top-down view of the TT 1800R with live LED & motor state."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg_dark"], highlightthickness=0, **kwargs)

        self.led_states = {
            "g1": False, "g2": False, "blue": True,
            "rl": False, "rr": False
        }
        self.motor_state = "!"  # stopped
        self.motor_speed = 191
        self.distance = None
        self._anim_frame = 0

        self.bind("<Configure>", lambda e: self.draw())

    def set_leds(self, g1, g2, blue, rl, rr):
        self.led_states = {"g1": g1, "g2": g2, "blue": blue, "rl": rl, "rr": rr}
        self.draw()

    def set_motor(self, direction, speed):
        self.motor_state = direction
        self.motor_speed = speed
        self.draw()

    def set_distance(self, dist):
        self.distance = dist
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 50 or h < 50:
            return

        cx, cy = w // 2, h // 2
        # Scale to fit
        scale = min(w / 280, h / 380)

        # ── Section Label ──
        self.create_text(cx, 14, text="VEHICLE STATUS", fill=C["text_dim"],
                         font=("Consolas", 9, "bold"), anchor="center")

        # ── Chassis Body ──
        bw = int(100 * scale)   # body width
        bh = int(150 * scale)   # body height
        r = int(12 * scale)     # corner radius
        x1, y1 = cx - bw // 2, cy - bh // 2
        x2, y2 = cx + bw // 2, cy + bh // 2
        self._rounded_rect(x1, y1, x2, y2, r, C["chassis"], C["chassis_edge"])

        # ── FRONT label ──
        self.create_text(cx, y1 - int(18 * scale), text="▲ FRONT", fill=C["text_dim"],
                         font=("Consolas", max(8, int(8 * scale))))

        # ── Wheels (4 rectangles) ──
        ww = int(18 * scale)
        wh = int(40 * scale)
        wo = int(14 * scale)  # offset outside chassis
        # Front-left
        self._wheel(x1 - wo, y1 + int(15 * scale), ww, wh)
        # Front-right
        self._wheel(x2 + wo - ww, y1 + int(15 * scale), ww, wh)
        # Rear-left
        self._wheel(x1 - wo, y2 - int(55 * scale), ww, wh)
        # Rear-right
        self._wheel(x2 + wo - ww, y2 - int(55 * scale), ww, wh)

        # ── LEDs ──
        led_r = max(6, int(10 * scale))
        glow_r = max(10, int(18 * scale))

        # Front-left Green (PB9)
        lx1 = x1 + int(22 * scale)
        ly_front = y1 + int(25 * scale)
        self._led(lx1, ly_front, led_r, glow_r, self.led_states["g1"], C["green_led"], C["green_dim"], "GL")

        # Front-right Green (PB5)
        lx2 = x2 - int(22 * scale)
        self._led(lx2, ly_front, led_r, glow_r, self.led_states["g2"], C["green_led"], C["green_dim"], "GR")

        # Center Blue (PB6)
        self._led(cx, cy - int(10 * scale), led_r, glow_r, self.led_states["blue"], C["blue_led"], C["blue_dim"], "BLU")

        # Rear-left Red (PB7)
        ly_rear = y2 - int(25 * scale)
        self._led(lx1, ly_rear, led_r, glow_r, self.led_states["rl"], C["red_led"], C["red_dim"], "RL")

        # Rear-right Red (PB8)
        self._led(lx2, ly_rear, led_r, glow_r, self.led_states["rr"], C["red_led"], C["red_dim"], "RR")

        # ── Motor Direction Arrow ──
        if self.motor_state != '!':
            self._draw_motor_arrow(cx, cy + int(15 * scale), scale)

        # ── Distance Sensor Bar ──
        if self.distance is not None:
            self._draw_distance(cx, y1 - int(38 * scale), scale)

        # ── Speed Readout ──
        pct = int(self.motor_speed / 255 * 100)
        speed_txt = f"PWM: {self.motor_speed}/255 ({pct}%)"
        self.create_text(cx, y2 + int(25 * scale), text=speed_txt,
                         fill=C["text_dim"], font=("Consolas", max(8, int(8 * scale))))

        # ── Motor status ──
        dir_labels = {'W': '▲ FORWARD', 'X': '▼ REVERSE', '<': '◄ LEFT',
                      '>': '► RIGHT', '!': '■ STOPPED'}
        dir_text = dir_labels.get(self.motor_state, '■ STOPPED')
        dir_color = C["motor_arrow"] if self.motor_state != '!' else C["text_muted"]
        self.create_text(cx, y2 + int(40 * scale), text=dir_text,
                         fill=dir_color, font=("Consolas", max(9, int(9 * scale)), "bold"))

    def _rounded_rect(self, x1, y1, x2, y2, r, fill, outline):
        pts = [
            x1 + r, y1, x2 - r, y1,
            x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2,
            x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r,
            x1, y1 + r, x1, y1,
        ]
        self.create_polygon(pts, smooth=True, fill=fill, outline=outline, width=2)

    def _wheel(self, x, y, w, h):
        self.create_rectangle(x, y, x + w, y + h, fill=C["wheel"],
                              outline=C["border_light"], width=1)
        # Tread lines
        for i in range(1, 5):
            ly = y + i * h // 5
            self.create_line(x + 2, ly, x + w - 2, ly, fill=C["border"], width=1)

    def _led(self, cx, cy, r, glow_r, is_on, color_on, color_off, label):
        if is_on:
            # Glow effect
            for i in range(3):
                gr = glow_r - i * 3
                alpha_hex = ["30", "18", "0c"][i]
                glow_color = color_on[:1] + alpha_hex + color_on[1:]
                self.create_oval(cx - gr, cy - gr, cx + gr, cy + gr,
                                 fill="", outline=color_on, width=1)
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill=color_on, outline="white", width=1)
        else:
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill=color_off, outline=C["border"], width=1)
        self.create_text(cx, cy + r + 10, text=label, fill=C["text_dim"],
                         font=("Consolas", 7))

    def _draw_motor_arrow(self, cx, cy, scale):
        s = int(20 * scale)
        color = C["motor_arrow"]
        if self.motor_state == 'W':  # Forward ▲
            pts = [cx, cy - s, cx - s // 2, cy + s // 3, cx + s // 2, cy + s // 3]
            self.create_polygon(pts, fill=color, outline="")
        elif self.motor_state == 'X':  # Reverse ▼
            pts = [cx, cy + s, cx - s // 2, cy - s // 3, cx + s // 2, cy - s // 3]
            self.create_polygon(pts, fill=color, outline="")
        elif self.motor_state == '<':  # Left ◄
            pts = [cx - s, cy, cx + s // 3, cy - s // 2, cx + s // 3, cy + s // 2]
            self.create_polygon(pts, fill=color, outline="")
        elif self.motor_state == '>':  # Right ►
            pts = [cx + s, cy, cx - s // 3, cy - s // 2, cx - s // 3, cy + s // 2]
            self.create_polygon(pts, fill=color, outline="")

    def _draw_distance(self, cx, y, scale):
        if self.distance is None:
            return
        dist = self.distance
        max_dist = 200
        bar_w = int(80 * scale)
        bar_h = max(6, int(6 * scale))
        x1 = cx - bar_w // 2
        x2 = cx + bar_w // 2

        # Background bar
        self.create_rectangle(x1, y, x2, y + bar_h, fill=C["bg_input"], outline=C["border"])
        # Fill bar
        ratio = min(dist / max_dist, 1.0)
        if dist < 0:
            fill_color = C["red"]
            ratio = 1.0
        elif dist < 20:
            fill_color = C["red"]
        elif dist < 50:
            fill_color = C["orange"]
        else:
            fill_color = C["green"]
        fill_x = x1 + int((x2 - x1) * ratio)
        self.create_rectangle(x1, y, fill_x, y + bar_h, fill=fill_color, outline="")

        # Text
        txt = f"{dist} cm" if dist >= 0 else "ERR"
        self.create_text(cx, y - 8, text=f"📏 {txt}", fill=C["text"],
                         font=("Consolas", max(8, int(9 * scale))))


# ══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════

class T18App(ctk.CTk):
    """T18 Hardware Diagnostic System — Main Window."""

    def __init__(self):
        super().__init__()

        # ── Window Config ──
        self.title("T18 — Hardware Diagnostic System")
        self.geometry("1060x720")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=C["bg_dark"])

        # ── State ──
        self.led_vars = {
            "g1": tk.BooleanVar(value=False),
            "g2": tk.BooleanVar(value=False),
            "blue": tk.BooleanVar(value=True),
            "rl": tk.BooleanVar(value=False),
            "rr": tk.BooleanVar(value=False),
        }
        self.motor_speed_var = tk.IntVar(value=75)
        self.connection_status = "disconnected"
        self.continuous_dist = False
        self._dist_job = None

        # ── BLE Worker ──
        self.gui_queue = queue.Queue()
        self.ble = BLEWorker(self.gui_queue)
        self.ble.start()

        # ── Build UI ──
        self._build_header()
        self._build_body()

        # ── Keyboard Shortcuts ──
        self.bind("<Key>", self._on_key)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Poll GUI queue ──
        self._poll_queue()

    # ══════════════════════════════════════════════════════════════
    #  HEADER BAR
    # ══════════════════════════════════════════════════════════════

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=C["bg_panel"], corner_radius=0, height=72)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        # Left — Logo & title
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=16, pady=8)

        title_lbl = ctk.CTkLabel(left, text="T18", font=("Segoe UI", 28, "bold"),
                                  text_color=C["accent"])
        title_lbl.pack(side="left", padx=(0, 8))

        subtitle = ctk.CTkLabel(left, text="Hardware Diagnostic System",
                                 font=("Segoe UI", 13), text_color=C["text_dim"])
        subtitle.pack(side="left", padx=(0, 20), anchor="s", pady=(0, 4))

        # Center — Connection status
        center = ctk.CTkFrame(header, fg_color="transparent")
        center.pack(side="left", expand=True, fill="x")

        self.status_dot = ctk.CTkLabel(center, text="●", font=("Segoe UI", 16),
                                        text_color=C["red"])
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_label = ctk.CTkLabel(center, text="Disconnected",
                                          font=("Segoe UI", 12, "bold"),
                                          text_color=C["text_dim"])
        self.status_label.pack(side="left")

        self.ble_addr_label = ctk.CTkLabel(center, text=f"BLE: {BLE_ADDRESS}",
                                            font=("Consolas", 10),
                                            text_color=C["text_muted"])
        self.ble_addr_label.pack(side="left", padx=(16, 0))

        self.auto_reconnect_var = tk.BooleanVar(value=True)
        self.auto_reconnect_cb = ctk.CTkCheckBox(
            center, text="Auto-Reconnect", variable=self.auto_reconnect_var,
            font=("Segoe UI", 11), text_color=C["text_dim"],
            fg_color=C["accent"], hover_color=C["accent_hover"],
            command=self._on_auto_reconnect_toggle
        )
        self.auto_reconnect_cb.pack(side="left", padx=(16, 0))

        # Right — Connect button
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=16, pady=8)

        self.connect_btn = ctk.CTkButton(
            right, text="Connect", width=120, height=36,
            font=("Segoe UI", 12, "bold"),
            fg_color=C["green"], hover_color="#2ea043",
            text_color="white", corner_radius=8,
            command=self._toggle_connection
        )
        self.connect_btn.pack(side="right")

    # ══════════════════════════════════════════════════════════════
    #  BODY (3-Column Layout)
    # ══════════════════════════════════════════════════════════════

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color=C["bg_dark"], corner_radius=0)
        body.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # ── Left Panel: Controls ──
        left = ctk.CTkFrame(body, fg_color=C["bg_panel"], corner_radius=12, width=250)
        left.pack(side="left", fill="y", padx=(0, 4))
        left.pack_propagate(False)
        self._build_led_panel(left)
        self._build_motor_panel(left)
        self._build_sensor_panel(left)

        # ── Center Panel: Vehicle View ──
        center = ctk.CTkFrame(body, fg_color=C["bg_panel"], corner_radius=12)
        center.pack(side="left", fill="both", expand=True, padx=4)
        self.vehicle = VehicleCanvas(center, width=320, height=400)
        self.vehicle.pack(fill="both", expand=True, padx=6, pady=6)

        # ── Right Panel: Telemetry ──
        right = ctk.CTkFrame(body, fg_color=C["bg_panel"], corner_radius=12, width=300)
        right.pack(side="right", fill="y", padx=(4, 0))
        right.pack_propagate(False)
        self._build_telemetry_panel(right)

    # ══════════════════════════════════════════════════════════════
    #  LED CONTROL PANEL
    # ══════════════════════════════════════════════════════════════

    def _build_led_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=(12, 4))

        # Section header
        hdr = ctk.CTkLabel(frame, text="💡  LED Control", font=("Segoe UI", 13, "bold"),
                            text_color=C["text"], anchor="w")
        hdr.pack(fill="x", pady=(0, 8))

        sep = ctk.CTkFrame(frame, fg_color=C["border"], height=1)
        sep.pack(fill="x", pady=(0, 8))

        # LED switches
        led_defs = [
            ("g1",   "Green Left  (PB9)",  C["green_led"],  "1"),
            ("g2",   "Green Right (PB5)",  C["green_led"],  "2"),
            ("blue", "Blue        (PB6)",  C["blue_led"],   "3"),
            ("rl",   "Red Left    (PB7)",  C["red_led"],    "4"),
            ("rr",   "Red Right   (PB8)",  C["red_led"],    "5"),
        ]

        self.led_switches = {}
        for key, label, color, cmd in led_defs:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            # Color dot
            dot = ctk.CTkLabel(row, text="●", font=("Segoe UI", 14),
                                text_color=color, width=20)
            dot.pack(side="left", padx=(0, 6))

            lbl = ctk.CTkLabel(row, text=label, font=("Consolas", 10),
                                text_color=C["text_dim"], anchor="w")
            lbl.pack(side="left", expand=True, fill="x")

            switch = ctk.CTkSwitch(
                row, text="", width=40, variable=self.led_vars[key],
                onvalue=True, offvalue=False,
                progress_color=color,
                command=lambda c=cmd: self._send(c)
            )
            switch.pack(side="right")
            self.led_switches[key] = switch

        # Quick action buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            btn_row, text="ALL ON", width=70, height=28,
            font=("Segoe UI", 10, "bold"),
            fg_color=C["green_dim"], hover_color=C["green"],
            text_color=C["green"], corner_radius=6,
            command=lambda: self._send("A")
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_row, text="ALL OFF", width=70, height=28,
            font=("Segoe UI", 10, "bold"),
            fg_color=C["red_dim"], hover_color=C["red"],
            text_color=C["red"], corner_radius=6,
            command=lambda: self._send("O")
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_row, text="SWEEP", width=70, height=28,
            font=("Segoe UI", 10, "bold"),
            fg_color=C["blue_dim"], hover_color=C["accent"],
            text_color=C["accent"], corner_radius=6,
            command=self._led_sweep
        ).pack(side="left")

    # ══════════════════════════════════════════════════════════════
    #  MOTOR CONTROL PANEL
    # ══════════════════════════════════════════════════════════════

    def _build_motor_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=(12, 4))

        hdr = ctk.CTkLabel(frame, text="⚡  Motor Control", font=("Segoe UI", 13, "bold"),
                            text_color=C["text"], anchor="w")
        hdr.pack(fill="x", pady=(0, 8))

        sep = ctk.CTkFrame(frame, fg_color=C["border"], height=1)
        sep.pack(fill="x", pady=(0, 8))

        # D-Pad
        dpad = ctk.CTkFrame(frame, fg_color="transparent")
        dpad.pack(pady=(0, 8))

        btn_style = {
            "width": 52, "height": 36, "corner_radius": 8,
            "font": ("Segoe UI", 13, "bold"),
            "fg_color": C["bg_card"], "hover_color": C["motor_arrow"],
            "text_color": C["text"], "border_width": 1,
            "border_color": C["border"]
        }

        # Row 1: Forward
        r1 = ctk.CTkFrame(dpad, fg_color="transparent")
        r1.pack()
        ctk.CTkButton(r1, text="▲", command=lambda: self._send("W"), **btn_style).pack()

        # Row 2: Left, Stop, Right
        r2 = ctk.CTkFrame(dpad, fg_color="transparent")
        r2.pack(pady=3)
        ctk.CTkButton(r2, text="◄", command=lambda: self._send("<"), **btn_style).pack(side="left", padx=3)

        stop_btn = ctk.CTkButton(
            r2, text="■", width=52, height=36, corner_radius=8,
            font=("Segoe UI", 13, "bold"),
            fg_color=C["red_dim"], hover_color=C["red"],
            text_color=C["red"], border_width=1, border_color=C["red"],
            command=lambda: self._send("!")
        )
        stop_btn.pack(side="left", padx=3)

        ctk.CTkButton(r2, text="►", command=lambda: self._send(">"), **btn_style).pack(side="left", padx=3)

        # Row 3: Reverse
        r3 = ctk.CTkFrame(dpad, fg_color="transparent")
        r3.pack()
        ctk.CTkButton(r3, text="▼", command=lambda: self._send("X"), **btn_style).pack()

        # Speed slider
        spd_frame = ctk.CTkFrame(frame, fg_color="transparent")
        spd_frame.pack(fill="x", pady=(4, 0))

        self.speed_label = ctk.CTkLabel(spd_frame, text="Speed: 75%",
                                         font=("Consolas", 10), text_color=C["text_dim"])
        self.speed_label.pack(anchor="w")

        self.speed_slider = ctk.CTkSlider(
            spd_frame, from_=0, to=100, number_of_steps=10,
            variable=self.motor_speed_var,
            progress_color=C["motor_arrow"],
            button_color=C["motor_arrow"],
            button_hover_color=C["orange"],
            command=self._on_speed_change
        )
        self.speed_slider.pack(fill="x", pady=(2, 0))

        # Shortcut hint
        hint = ctk.CTkLabel(spd_frame, text="Keys: W A S D · Space=Stop",
                             font=("Consolas", 8), text_color=C["text_muted"])
        hint.pack(anchor="w", pady=(4, 0))

    # ══════════════════════════════════════════════════════════════
    #  SENSOR PANEL
    # ══════════════════════════════════════════════════════════════

    def _build_sensor_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=(12, 4))

        hdr = ctk.CTkLabel(frame, text="📏  Ultrasonic Sensor", font=("Segoe UI", 13, "bold"),
                            text_color=C["text"], anchor="w")
        hdr.pack(fill="x", pady=(0, 8))

        sep = ctk.CTkFrame(frame, fg_color=C["border"], height=1)
        sep.pack(fill="x", pady=(0, 8))

        # Distance display
        self.dist_display = ctk.CTkLabel(
            frame, text="— cm", font=("Consolas", 22, "bold"),
            text_color=C["accent"], anchor="center"
        )
        self.dist_display.pack(fill="x", pady=(0, 8))

        # Buttons
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text="READ", width=80, height=28,
            font=("Segoe UI", 10, "bold"),
            fg_color=C["bg_card"], hover_color=C["accent"],
            text_color=C["accent"], corner_radius=6,
            border_width=1, border_color=C["accent"],
            command=lambda: self._send("D")
        ).pack(side="left", padx=(0, 4))

        self.cont_btn = ctk.CTkButton(
            btn_row, text="CONTINUOUS", width=100, height=28,
            font=("Segoe UI", 10, "bold"),
            fg_color=C["bg_card"], hover_color=C["purple"],
            text_color=C["purple"], corner_radius=6,
            border_width=1, border_color=C["purple"],
            command=self._toggle_continuous
        )
        self.cont_btn.pack(side="left")

    # ══════════════════════════════════════════════════════════════
    #  TELEMETRY LOG PANEL
    # ══════════════════════════════════════════════════════════════

    def _build_telemetry_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Header row
        hdr_row = ctk.CTkFrame(frame, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(hdr_row, text="📡  Telemetry Log", font=("Segoe UI", 13, "bold"),
                      text_color=C["text"]).pack(side="left")

        ctk.CTkButton(
            hdr_row, text="Clear", width=50, height=24,
            font=("Segoe UI", 9),
            fg_color=C["bg_card"], hover_color=C["border_light"],
            text_color=C["text_dim"], corner_radius=4,
            command=self._clear_log
        ).pack(side="right")

        sep = ctk.CTkFrame(frame, fg_color=C["border"], height=1)
        sep.pack(fill="x", pady=(0, 4))

        # Scrollable log
        self.log_text = tk.Text(
            frame, bg=C["bg_dark"], fg=C["text_dim"],
            font=("Consolas", 9), wrap="word",
            borderwidth=0, highlightthickness=0,
            insertbackground=C["text"], selectbackground=C["accent"],
            state="disabled", padx=8, pady=4
        )
        self.log_text.pack(fill="both", expand=True)

        # Configure log tags
        self.log_text.tag_configure("tx", foreground=C["accent"])
        self.log_text.tag_configure("rx", foreground=C["green"])
        self.log_text.tag_configure("err", foreground=C["red"])
        self.log_text.tag_configure("warn", foreground=C["orange"])
        self.log_text.tag_configure("info", foreground=C["text_dim"])
        self.log_text.tag_configure("ok", foreground=C["green"])
        self.log_text.tag_configure("ts", foreground=C["text_muted"])

        # Status bar
        self.status_bar = ctk.CTkLabel(
            frame, text="Ready", font=("Consolas", 9), text_color=C["text_muted"],
            anchor="w"
        )
        self.status_bar.pack(fill="x", pady=(4, 0))

    # ══════════════════════════════════════════════════════════════
    #  ACTIONS
    # ══════════════════════════════════════════════════════════════

    def _send(self, cmd: str):
        self.ble.send_command(cmd)

    def _toggle_connection(self):
        if self.connection_status == "connected":
            self.ble.request_disconnect()
        else:
            self.ble.request_connect()

    def _on_speed_change(self, value):
        pct = int(value)
        self.speed_label.configure(text=f"Speed: {pct}%")
        # Map 0-100 to P0-P9
        digit = min(9, int(pct / 100 * 9 + 0.5))
        self._send(f"P{digit}")

    def _toggle_continuous(self):
        self.continuous_dist = not self.continuous_dist
        if self.continuous_dist:
            self.cont_btn.configure(fg_color=C["purple"], text_color="white", text="● POLLING")
            self._poll_distance()
        else:
            self.cont_btn.configure(fg_color=C["bg_card"], text_color=C["purple"], text="CONTINUOUS")
            if self._dist_job:
                self.after_cancel(self._dist_job)
                self._dist_job = None

    def _poll_distance(self):
        if self.continuous_dist:
            self._send("D")
            self._dist_job = self.after(500, self._poll_distance)

    def _led_sweep(self):
        """Send LED commands in sequence with delays for visual sweep test."""
        cmds = ["O", "1", "1", "2", "2", "3", "3", "4", "4", "5", "5", "A", "O", "S"]
        delay = 200  # ms between commands
        for i, cmd in enumerate(cmds):
            self.after(i * delay, lambda c=cmd: self._send(c))

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════
    #  KEYBOARD SHORTCUTS
    # ══════════════════════════════════════════════════════════════

    def _on_key(self, event):
        # Don't intercept if focus is on an entry/text widget
        if isinstance(event.widget, (tk.Entry, tk.Text)):
            return

        k = event.keysym.lower()
        char = event.char

        key_map = {
            'w': 'W', 'up': 'W',
            's': 'X', 'down': 'X',
            'a': '<', 'left': '<',
            'd': '>', 'right': '>',
        }

        if k in key_map:
            self._send(key_map[k])
            return

        if k == 'space':
            self._send("!")
            return

        # Number keys for LEDs
        if char in '12345':
            self._send(char)
            return

    # ══════════════════════════════════════════════════════════════
    #  GUI QUEUE POLLING (BLE → GUI bridge)
    # ══════════════════════════════════════════════════════════════

    def _poll_queue(self):
        try:
            while True:
                msg_type, data = self.gui_queue.get_nowait()

                if msg_type == "STATUS":
                    self._update_connection_status(data)
                elif msg_type == "TX":
                    self._log_tx(data)
                elif msg_type == "RX":
                    self._handle_rx(data)
                elif msg_type == "HEARTBEAT_ACK":
                    if self.connection_status == "connected":
                        self.status_bar.configure(text="● Online — BLE Link Active (Heartbeat OK)")
                elif msg_type == "LOG_OK":
                    self._log(data, "ok", "✓")
                elif msg_type == "LOG_ERR":
                    self._log(data, "err", "✗")
                elif msg_type == "LOG_WARN":
                    self._log(data, "warn", "⚠")
                elif msg_type == "LOG_INFO":
                    self._log(data, "info", "◆")

        except queue.Empty:
            pass
        finally:
            self.after(50, self._poll_queue)

    def _on_auto_reconnect_toggle(self):
        enabled = self.auto_reconnect_var.get()
        self.ble.set_auto_reconnect(enabled)
        msg = "Auto-reconnect enabled" if enabled else "Auto-reconnect disabled"
        self._log(msg, "info", "◆")

    def _update_connection_status(self, status):
        self.connection_status = status

        if status == "connected":
            self.status_dot.configure(text_color=C["green"])
            self.status_label.configure(text="Connected to TT 1800R", text_color=C["green"])
            self.connect_btn.configure(text="Disconnect", fg_color=C["red_dim"],
                                        hover_color=C["red"])
            self.status_bar.configure(text="● Online — BLE link active")
        elif status == "connecting":
            self.status_dot.configure(text_color=C["orange"])
            self.status_label.configure(text="Connecting...", text_color=C["orange"])
            self.connect_btn.configure(text="Connecting...", fg_color=C["bg_card"],
                                        hover_color=C["bg_card"])
            self.status_bar.configure(text="⟳ Establishing BLE connection...")
        else:
            self.status_dot.configure(text_color=C["red"])
            self.status_label.configure(text="Disconnected", text_color=C["text_dim"])
            self.connect_btn.configure(text="Connect", fg_color=C["green"],
                                        hover_color="#2ea043")
            self.status_bar.configure(text="○ Offline")

    def _log_tx(self, cmd):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._log_raw(f"[{ts}]  → Sent '{cmd}'\n", "tx", "ts")
        self.status_bar.configure(text=f"→ {cmd}")

    def _handle_rx(self, text):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Parse periodic status report from heartbeat or '?' query
        if text.startswith("ST:"):
            self._parse_status(text[3:])
            if self.connection_status == "connected":
                self.status_bar.configure(text=f"● Online — Telemetry Synced [{text}]")
            return

        self._log_raw(f"[{ts}]  ← {text}\n", "rx", "ts")
        self.status_bar.configure(text=f"← {text}")

        # Parse LED state from ACKs
        if text.startswith("RX:"):
            cmd = text[3:]
            self._update_led_state_from_ack(cmd)

        # Parse distance
        if text.startswith("DIST:"):
            val = text[5:]
            if val == "ERR":
                self.dist_display.configure(text="ERR", text_color=C["red"])
                self.vehicle.set_distance(-1)
            else:
                try:
                    dist = int(val)
                    color = C["red"] if dist < 20 else C["orange"] if dist < 50 else C["green"]
                    self.dist_display.configure(text=f"{dist} cm", text_color=color)
                    self.vehicle.set_distance(dist)
                except ValueError:
                    pass

        # Parse status report
        if text.startswith("ST:"):
            self._parse_status(text[3:])

    def _update_led_state_from_ack(self, cmd):
        """Update GUI LED states based on confirmed ACK from STM32."""
        if cmd == "1":
            self.led_vars["g1"].set(not self.led_vars["g1"].get())
        elif cmd == "2":
            self.led_vars["g2"].set(not self.led_vars["g2"].get())
        elif cmd == "3":
            self.led_vars["blue"].set(not self.led_vars["blue"].get())
        elif cmd == "4":
            self.led_vars["rl"].set(not self.led_vars["rl"].get())
        elif cmd == "5":
            self.led_vars["rr"].set(not self.led_vars["rr"].get())
        elif cmd == "A":
            for v in self.led_vars.values():
                v.set(True)
        elif cmd == "O":
            for v in self.led_vars.values():
                v.set(False)
        elif cmd == "S":
            self.led_vars["g1"].set(False)
            self.led_vars["g2"].set(False)
            self.led_vars["blue"].set(True)
            self.led_vars["rl"].set(False)
            self.led_vars["rr"].set(False)
        elif cmd == "F":
            self.led_vars["g1"].set(True)
            self.led_vars["g2"].set(True)
            self.led_vars["blue"].set(False)
            self.led_vars["rl"].set(False)
            self.led_vars["rr"].set(False)
        elif cmd == "B":
            self.led_vars["g1"].set(False)
            self.led_vars["g2"].set(False)
            self.led_vars["blue"].set(False)
            self.led_vars["rl"].set(True)
            self.led_vars["rr"].set(True)
        elif cmd == "L":
            self.led_vars["g1"].set(True)
            self.led_vars["g2"].set(False)
            self.led_vars["blue"].set(False)
            self.led_vars["rl"].set(True)
            self.led_vars["rr"].set(False)
        elif cmd == "R":
            self.led_vars["g1"].set(False)
            self.led_vars["g2"].set(True)
            self.led_vars["blue"].set(False)
            self.led_vars["rl"].set(False)
            self.led_vars["rr"].set(True)

        # Update vehicle canvas
        self.vehicle.set_leds(
            self.led_vars["g1"].get(),
            self.led_vars["g2"].get(),
            self.led_vars["blue"].get(),
            self.led_vars["rl"].get(),
            self.led_vars["rr"].get()
        )

        # Motor state from ACK
        if cmd in ("W", "X", "<", ">", "!"):
            self.vehicle.set_motor(cmd, int(self.motor_speed_var.get() / 100 * 255))
        elif cmd == "S":
            self.vehicle.set_motor("!", 0)

    def _parse_status(self, data):
        """Parse ST:GGRBB,Mdir,Pspd format."""
        try:
            parts = data.split(",")
            if len(parts) >= 3:
                leds = parts[0]
                if len(leds) == 5:
                    self.led_vars["g1"].set(leds[0] == '1')
                    self.led_vars["g2"].set(leds[1] == '1')
                    self.led_vars["blue"].set(leds[2] == '1')
                    self.led_vars["rl"].set(leds[3] == '1')
                    self.led_vars["rr"].set(leds[4] == '1')
                motor_dir = parts[1]
                motor_spd = int(parts[2])
                self.vehicle.set_leds(
                    self.led_vars["g1"].get(),
                    self.led_vars["g2"].get(),
                    self.led_vars["blue"].get(),
                    self.led_vars["rl"].get(),
                    self.led_vars["rr"].get()
                )
                self.vehicle.set_motor(motor_dir, motor_spd)
        except Exception:
            pass

    def _log(self, text, tag, prefix):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._log_raw(f"[{ts}]  {prefix} {text}\n", tag, "ts")

    def _log_raw(self, text, content_tag, ts_tag):
        self.log_text.configure(state="normal")
        # Insert timestamp portion with ts tag, rest with content tag
        bracket_end = text.find("]") + 1
        if bracket_end > 0:
            self.log_text.insert("end", text[:bracket_end], ts_tag)
            self.log_text.insert("end", text[bracket_end:], content_tag)
        else:
            self.log_text.insert("end", text, content_tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ══════════════════════════════════════════════════════════════
    #  CLEANUP
    # ══════════════════════════════════════════════════════════════

    def _on_close(self):
        self.continuous_dist = False
        if self._dist_job:
            self.after_cancel(self._dist_job)
        self.ble.request_disconnect()
        time.sleep(0.3)  # Brief pause for disconnect command
        self.ble.stop()
        self.destroy()


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not BLEAK_OK:
        print("[ERROR] 'bleak' is not installed. Run: pip install bleak")
        sys.exit(1)

    app = T18App()
    app.mainloop()
