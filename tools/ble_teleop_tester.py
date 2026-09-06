"""
===============================================================================
  SMART VEHICLE — WINDOWS BLE TELEMETRY & HARDWARE TESTER
===============================================================================
  Target:      BLE Module (HM-10 / AT-09 / CC2541 BLE UART)
  BLE Address: A0:85:E0:1C:3E:10
  Write UUID:  0000FFE2-0000-1000-8000-00805F9B34FB  (Verified TX to STM32)
  Notify UUID: 0000FFE1-0000-1000-8000-00805F9B34FB  (RX from STM32)

  CONTROLS:
    [W] ──→ Forward   (Sends 'F' ── Front Greens ON)
    [S] ──→ Backward  (Sends 'B' ── Rear Reds ON)
    [A] ──→ Turn Left (Sends 'L' ── Left Indicators ON)
    [D] ──→ Turn Right(Sends 'R' ── Right Indicators ON)
    [SPACE] ──→ Stop  (Sends 'S' ── Standby Blue ON)
    [Q] / [ESC] ──→ Quit tester cleanly
===============================================================================
"""

import sys
import os
import asyncio
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Windows real-time keypress handling
if sys.platform == "win32":
    import msvcrt
else:
    import select
    import termios
    import tty

# --- CONFIGURATION ---
BLE_ADDRESS = "A0:85:E0:1C:3E:10"
UUID_SERVICE = "0000ffe0-0000-1000-8000-00805f9b34fb"
UUID_WRITE   = "0000ffe2-0000-1000-8000-00805f9b34fb"  # FFE2 verified
UUID_NOTIFY  = "0000ffe1-0000-1000-8000-00805f9b34fb"  # FFE1 feedback

# Key to Command mapping
KEY_MAP = {
    'w': ('F', "FORWARD",   "Front Greens [PB5, PB9] ON"),
    's': ('B', "BACKWARD",  "Rear Reds    [PB7, PB8] ON"),
    'a': ('L', "LEFT TURN", "Left Side    [PB5, PB7] ON"),
    'd': ('R', "RIGHT TURN","Right Side   [PB9, PB8] ON"),
    ' ': ('S', "STOP",      "Standby Blue [PB6]      ON"),
    'x': ('S', "STOP",      "Standby Blue [PB6]      ON"),
}

# Buffer for received STM32 serial messages
received_messages = []


def on_rx_data(sender, data: bytearray):
    """Callback when STM32 replies over BLE notification"""
    try:
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            received_messages.append(f"[{timestamp}] {text}")
            if len(received_messages) > 6:
                received_messages.pop(0)
            print(f"\r  \033[92m◄── {text}\033[0m")
            print("  Command > ", end="", flush=True)
    except Exception:
        pass


def print_ui(status="CONNECTED", active_cmd="S", detail="Standby Blue [PB6] ON"):
    """Prints a clean interactive terminal dashboard"""
    print("\n" + "=" * 62)
    print("      SMART VEHICLE — HARDWARE COMMUNICATION TESTER       ")
    print("=" * 62)
    print(f"  Target BLE Address : \033[96m{BLE_ADDRESS}\033[0m")
    print(f"  Connection Status  : \033[92m● {status}\033[0m")
    print(f"  Write Characteristic: FFE2 (No-Response UART)")
    print("-" * 62)
    print("                 [FRONT OF VEHICLE]")
    print("       PB5 (Green Left)  ───  PB9 (Green Right)")
    print("                      \\     /")
    print("                     PB6 (Blue)")
    print("                      /     \\")
    print("       PB7 (Red Left)    ───  PB8 (Red Right)")
    print("                  [REAR OF VEHICLE]")
    print("-" * 62)
    print("  CONTROLS: [W] Forward | [S] Back | [A] Left | [D] Right")
    print("            [SPACE] Stop | [Q] Quit")
    print("-" * 62)
    print(f"  CURRENT STATE : \033[1;93m[{active_cmd}] {detail}\033[0m")
    print("-" * 62)
    print("  STM32 Telemetry Feed:")
    if received_messages:
        for msg in received_messages[-3:]:
            print(f"    \033[90m{msg}\033[0m")
    else:
        print("    \033[90m(Awaiting UART telemetry from PA9...)\033[0m")
    print("=" * 62)
    print("  Press W/A/S/D/Space to send: ", end="", flush=True)


def check_key():
    """Non-blocking keyboard check on Windows and POSIX"""
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


async def run_telemetry_loop(client: BleakClient):
    """Main interactive control loop"""
    current_cmd = "S"
    current_desc = "STOP"
    current_detail = "Standby Blue [PB6] ON"

    print_ui("READY", current_cmd, current_detail)

    # Initial STOP command to synchronize STM32
    try:
        await client.write_gatt_char(UUID_WRITE, b"S", response=False)
    except Exception as e:
        print(f"\n[Warning] Initial write failed: {e}")

    running = True
    while running and client.is_connected:
        key = check_key()
        if key:
            if key in ('q', '\x1b'):  # Q or Escape to quit
                print("\n\n[Exiting] Sending STOP and disconnecting...")
                try:
                    await client.write_gatt_char(UUID_WRITE, b"S", response=False)
                except Exception:
                    pass
                running = False
                break

            if key in KEY_MAP:
                cmd_char, desc, detail = KEY_MAP[key]
                current_cmd = cmd_char
                current_desc = desc
                current_detail = detail

                try:
                    # Send single command byte to FFE2
                    await client.write_gatt_char(
                        UUID_WRITE,
                        cmd_char.encode("ascii"),
                        response=False
                    )
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"\r  \033[94m──► [{timestamp}] Sent '{cmd_char}' ({desc})\033[0m -> {detail}")
                    print("  Press W/A/S/D/Space: ", end="", flush=True)
                except Exception as e:
                    print(f"\n[Error] Write failed: {e}")

        await asyncio.sleep(0.02)  # 50 Hz non-blocking poll


async def main():
    print("\n" + "=" * 62)
    print("  Connecting to STM32 BLE Vehicle...")
    print(f"  Target Address: {BLE_ADDRESS}")
    print("=" * 62)

    try:
        async with BleakClient(BLE_ADDRESS, timeout=12.0) as client:
            if not client.is_connected:
                print(f"[ERROR] Failed to establish BLE link with {BLE_ADDRESS}.")
                return

            print(f"[OK] Connected successfully to {BLE_ADDRESS}!")

            # Attempt to subscribe to FFE1 notifications for STM32 echoes
            try:
                await client.start_notify(UUID_NOTIFY, on_rx_data)
                print("[OK] Subscribed to UART feedback stream (FFE1).")
            except Exception as e:
                print(f"[NOTE] Notification on FFE1 not active ({e}). Telemetry TX only.")

            await run_telemetry_loop(client)

    except asyncio.TimeoutError:
        print(f"\n[ERROR] Connection timed out. Ensure the BLE module is powered.")
    except Exception as ex:
        print(f"\n[ERROR] BLE session terminated: {ex}")

    print("\n[Done] Disconnected cleanly.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Aborted by user]")
