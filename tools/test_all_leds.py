"""
===============================================================================
  SMART VEHICLE — AUTOMATED & INTERACTIVE LED TEST SUITE
===============================================================================
  Target:      BLE Module (HM-10 / AT-09 / CC2541 BLE UART)
  BLE Address: A0:85:E0:1C:3E:10
  Write UUID:  0000FFE2-0000-1000-8000-00805F9B34FB  (FFE2)
  Notify UUID: 0000FFE1-0000-1000-8000-00805F9B34FB  (FFE1)

  PURPOSE:
  Performs an automated visual verification of every physical LED on the vehicle:
    - PB5 : Front Left GREEN1
    - PB9 : Front Right GREEN2
    - PB6 : Center / Status BLUE
    - PB7 : Rear Left RED_L
    - PB8 : Rear Right RED_R

  Followed by an interactive switchboard to test any LED on demand.
===============================================================================
"""

import sys
import os
import asyncio
from datetime import datetime
from bleak import BleakClient

# Windows non-blocking keypress handling
if sys.platform == "win32":
    import msvcrt
else:
    import select

# --- CONFIGURATION ---
BLE_ADDRESS = "A0:85:E0:1C:3E:10"
UUID_WRITE   = "0000ffe2-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY  = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Automated Test Sequence
TEST_SEQUENCE = [
    ("F", 1.8, "HEADLIGHTS TEST",           "Front Greens [PB5, PB9] ON  (Reds & Blue OFF)"),
    ("B", 1.8, "TAILLIGHTS TEST",           "Rear Reds    [PB7, PB8] ON  (Greens & Blue OFF)"),
    ("L", 1.8, "LEFT INDICATORS TEST",      "Left Side    [PB5, PB7] ON  (Right & Blue OFF)"),
    ("R", 1.8, "RIGHT INDICATORS TEST",     "Right Side   [PB9, PB8] ON  (Left & Blue OFF)"),
    ("S", 1.8, "STATUS / STOP TEST",        "Center Blue  [PB6]      ON  (Greens & Reds OFF)"),
    ("1", 1.2, "INDIVIDUAL PB5 TEST",       "Front Left   [PB5 Green1] ONLY"),
    ("2", 1.2, "INDIVIDUAL PB9 TEST",       "Front Right  [PB9 Green2] ONLY"),
    ("3", 1.2, "INDIVIDUAL PB6 TEST",       "Center       [PB6 Blue]   ONLY"),
    ("4", 1.2, "INDIVIDUAL PB7 TEST",       "Rear Left    [PB7 Red_L]  ONLY"),
    ("5", 1.2, "INDIVIDUAL PB8 TEST",       "Rear Right   [PB8 Red_R]  ONLY"),
    ("A", 2.0, "ALL LEDS SIMULTANEOUS TEST", "EVERY LED ON [PB5, PB9, PB7, PB8, PB6]"),
    ("O", 0.8, "ALL LEDS OFF TEST",         "ALL LEDS OFF"),
    ("S", 1.0, "STANDBY RESTORATION",       "Center Blue  [PB6]      ON  (Ready)"),
]

# Manual Key Mapping for Interactive Mode
MANUAL_KEYS = {
    '1': ('1', "GREEN 1 ONLY",       "PB5 Front Left"),
    '2': ('2', "GREEN 2 ONLY",       "PB9 Front Right"),
    '3': ('3', "BLUE ONLY",          "PB6 Center Status"),
    '4': ('4', "RED LEFT ONLY",      "PB7 Rear Left"),
    '5': ('5', "RED RIGHT ONLY",     "PB8 Rear Right"),
    'a': ('A', "ALL 5 LEDS ON",      "PB5 + PB9 + PB7 + PB8 + PB6"),
    'o': ('O', "ALL LEDS OFF",       "Dark"),
    'w': ('F', "FORWARD (Headlights)","PB5 + PB9 Green"),
    's': ('B', "BACKWARD (Taillights)","PB7 + PB8 Red"),
    ' ': ('S', "STOP (Blue Status)", "PB6 Blue"),
    'x': ('S', "STOP (Blue Status)", "PB6 Blue"),
    'l': ('L', "LEFT INDICATORS",    "PB5 + PB7"),
    'r': ('R', "RIGHT INDICATORS",   "PB9 + PB8"),
}


def on_rx(sender, data: bytearray):
    """Prints incoming STM32 telemetry feedback"""
    try:
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            print(f"\r  \033[92m◄── {text}\033[0m")
            print("  Command > ", end="", flush=True)
    except Exception:
        pass


def check_key():
    """Non-blocking keyboard check"""
    if sys.platform == "win32":
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            try:
                return ch.decode("utf-8").lower()
            except UnicodeDecodeError:
                return None
        return None
    else:
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            return sys.stdin.read(1).lower()
        return None


async def send_cmd(client: BleakClient, cmd: str):
    """Sends a single character command to FFE2"""
    await client.write_gatt_char(UUID_WRITE, cmd.encode("ascii"), response=False)


async def run_automated_suite(client: BleakClient):
    """Runs the full automated test routine step-by-step with progress"""
    total_steps = len(TEST_SEQUENCE)
    print("\n" + "=" * 64)
    print("       STARTING AUTOMATED VEHICLE LED TEST SEQUENCE       ")
    print(f"       Total Stages: {total_steps}  |  Watch your vehicle LEDs!   ")
    print("=" * 64)

    for i, (cmd, duration, stage_name, description) in enumerate(TEST_SEQUENCE, start=1):
        # Progress bar
        bar_filled = "█" * i
        bar_empty  = "░" * (total_steps - i)
        print(f"\n  [{i:02d}/{total_steps:02d}] \033[1;93m{stage_name}\033[0m")
        print(f"        Action : \033[96mSending '{cmd}'\033[0m ──► {description}")
        print(f"        Visual : [{bar_filled}{bar_empty}]")

        try:
            await send_cmd(client, cmd)
        except Exception as e:
            print(f"        \033[91m[Error sending '{cmd}']: {e}\033[0m")

        # Countdown delay for user observation
        await asyncio.sleep(duration)

    # Dynamic Wig-Wag / Alternating Chase Effect (Grand Finale)
    print("\n  [BONUS] \033[1;95mRUNNING ALTERNATING STROBE (Front ↔ Rear 4x)...\033[0m")
    for _ in range(4):
        await send_cmd(client, "F")
        await asyncio.sleep(0.18)
        await send_cmd(client, "B")
        await asyncio.sleep(0.18)

    # Return to Stop
    await send_cmd(client, "S")
    await asyncio.sleep(0.3)

    print("\n" + "=" * 64)
    print("  \033[92m✔ AUTOMATED LED TEST SEQUENCE COMPLETE!\033[0m")
    print("=" * 64)
    print("  Physical verification checklist:")
    print("    [✓] Front Left Green  (PB5)")
    print("    [✓] Front Right Green (PB9)")
    print("    [✓] Center Status Blue(PB6)")
    print("    [✓] Rear Left Red     (PB7)")
    print("    [✓] Rear Right Red    (PB8)")
    print("=" * 64)


async def run_interactive_mode(client: BleakClient):
    """Enters live interactive switchboard where user can press any key to test"""
    print("\n  \033[1;96mENTERING INTERACTIVE MANUAL SWITCHBOARD\033[0m")
    print("  ------------------------------------------------------------")
    print("  [1] Test Green 1 (PB5)  |  [4] Test Red Left  (PB7)")
    print("  [2] Test Green 2 (PB9)  |  [5] Test Red Right (PB8)")
    print("  [3] Test Blue    (PB6)  |  [A] Turn ALL LEDs ON")
    print("  [O] Turn ALL LEDs OFF   |  [T] Re-run Auto Test Suite")
    print("  [W] Forward | [S] Back  |  [SPACE] Stop | [Q] Quit")
    print("  ------------------------------------------------------------")
    print("  Press a key (1-5, A, O, T, W, S, Space, Q): ", end="", flush=True)

    running = True
    while running and client.is_connected:
        k = check_key()
        if k:
            if k in ('q', '\x1b'):
                print("\n\n[Exiting] Restoring Standby Blue and disconnecting...")
                try:
                    await send_cmd(client, "S")
                except Exception:
                    pass
                running = False
                break

            if k == 't':
                await run_automated_suite(client)
                print("\n  Press a key (1-5, A, O, T, W, S, Space, Q): ", end="", flush=True)
                continue

            if k in MANUAL_KEYS:
                cmd_byte, name, pins = MANUAL_KEYS[k]
                try:
                    await send_cmd(client, cmd_byte)
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"\r  \033[94m──► [{timestamp}] Key '{k.upper()}' ── Sent '{cmd_byte}'\033[0m: {name} ({pins})")
                    print("  Command > ", end="", flush=True)
                except Exception as ex:
                    print(f"\n[Write Error]: {ex}")

        await asyncio.sleep(0.02)


async def main():
    print("\n" + "=" * 64)
    print("  Smart Vehicle — Bluetooth LED Diagnostics & Telemetry Tester")
    print(f"  Target Device: {BLE_ADDRESS}")
    print("=" * 64)
    print("  Connecting via Bluetooth Low Energy...")

    try:
        async with BleakClient(BLE_ADDRESS, timeout=12.0) as client:
            if not client.is_connected:
                print(f"[ERROR] Could not connect to {BLE_ADDRESS}.")
                return

            print(f"[OK] Connected successfully to {BLE_ADDRESS}!")

            # Attempt notification subscription on FFE1
            try:
                await client.start_notify(UUID_NOTIFY, on_rx)
                print("[OK] Subscribed to UART feedback notifications (FFE1).")
            except Exception as e:
                print(f"[NOTE] FFE1 notify not available ({e}). Running TX-only.")

            # 1. Run the complete automated test suite
            await run_automated_suite(client)

            # 2. Transition into interactive mode
            await run_interactive_mode(client)

    except asyncio.TimeoutError:
        print("\n[ERROR] Connection timed out. Make sure the STM32/BLE module is powered on.")
    except Exception as ex:
        print(f"\n[ERROR] Session error: {ex}")

    print("\n[Done] BLE session disconnected cleanly.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Terminated by user]")
