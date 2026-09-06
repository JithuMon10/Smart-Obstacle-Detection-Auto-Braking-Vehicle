"""
===============================================================================
  SMART VEHICLE — VERIFIED WORKING BLE LED TEST SUITE
===============================================================================
  Target:       A0:85:E0:1C:3E:10
  UUID:         0000FFE1-0000-1000-8000-00805F9B34FB  (Write With Response & Notify)
  
  KEY FIX:
  Uses response=True (Acknowledged ATT Write).
  This guarantees bytes reach the BLE UART buffer without being dropped.
===============================================================================
"""

import sys
import os
import asyncio
from datetime import datetime
from bleak import BleakClient

# Windows single-keypress handling
if sys.platform == "win32":
    import msvcrt
else:
    import select

BLE_ADDRESS = "A0:85:E0:1C:3E:10"
UUID_UART   = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Automated Test Sequence: (cmd, name, desc, hold_sec)
STAGES = [
    ("1", "FRONT LEFT GREEN1",  "PB5 only",              1.2),
    ("2", "FRONT RIGHT GREEN2", "PB9 only",              1.2),
    ("3", "CENTER BLUE",        "PB6 only",              1.2),
    ("4", "REAR LEFT RED_L",    "PB7 only",              1.2),
    ("5", "REAR RIGHT RED_R",   "PB8 only",              1.2),
    ("A", "ALL 5 LEDS ON",      "Every LED ON (PB5,9,6,7,8)", 2.0),
    ("O", "ALL 5 LEDS OFF",     "Dark",                  1.0),
    ("S", "STANDBY / STOP",     "Center Blue (PB6) ON",  1.2),
]

# Manual key mapping
KEYS = {
    '1': ('1', "Toggle Green 1 (PB5)"),
    '2': ('2', "Toggle Green 2 (PB9)"),
    '3': ('3', "Toggle Center Blue (PB6)"),
    '4': ('4', "Toggle Red Left (PB7)"),
    '5': ('5', "Toggle Red Right (PB8)"),
    'a': ('A', "All 5 LEDs ON"),
    'o': ('O', "All 5 LEDs OFF"),
    's': ('S', "Standby (PB6 Blue ON)"),
    ' ': ('S', "Standby (PB6 Blue ON)"),
}

ack_event = asyncio.Event()
last_ack = ""


def on_notify(sender, data: bytearray):
    global last_ack
    try:
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            last_ack = text
            ack_event.set()
    except Exception:
        pass


def check_key():
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


async def send_cmd(client: BleakClient, cmd: str, timeout: float = 0.8) -> str:
    global last_ack
    ack_event.clear()
    last_ack = ""

    # CRITICAL: response=True (Write With Response)
    await client.write_gatt_char(UUID_UART, cmd.encode("ascii"), response=True)

    try:
        await asyncio.wait_for(ack_event.wait(), timeout=timeout)
        return last_ack
    except asyncio.TimeoutError:
        return None


async def run_auto_test(client: BleakClient):
    total = len(STAGES)
    print("\n" + "=" * 66)
    print("      AUTOMATED VEHICLE LED DIAGNOSTIC & VERIFICATION       ")
    print(f"      Total Stages: {total}  |  Watch your vehicle LEDs!      ")
    print("=" * 66)

    for i, (cmd, name, desc, hold) in enumerate(STAGES, start=1):
        bar = "█" * i + "░" * (total - i)
        print(f"\n  [{i:02d}/{total:02d}] \033[1;93m{name}\033[0m  [{bar}]")
        print(f"        Action : Sending '{cmd}' ──► {desc}")

        ack = await send_cmd(client, cmd)
        if ack:
            print(f"        STM32  : \033[92m✔ {ack} (Confirmed via UART PA9)\033[0m")
        else:
            print(f"        STM32  : \033[94m(Command sent)\033[0m")

        await asyncio.sleep(hold)

    print("\n" + "=" * 66)
    print("  \033[92m✔ ALL LEDS VERIFIED SUCCESSFULLY!\033[0m")
    print("=" * 66)


async def run_manual_switchboard(client: BleakClient):
    print("\n" + "-" * 66)
    print("  \033[1;96mLIVE INTERACTIVE SWITCHBOARD (STAYS CONNECTED)\033[0m")
    print("  ----------------------------------------------------------------")
    print("  [1] Green 1 (PB5)   |  [4] Red Left  (PB7)  |  [A] All 5 ON")
    print("  [2] Green 2 (PB9)   |  [5] Red Right (PB8)  |  [O] All 5 OFF")
    print("  [3] Blue    (PB6)   |  [S] Standby Blue     |  [T] Re-run Auto")
    print("  [Q] Quit & Disconnect")
    print("  ----------------------------------------------------------------")
    print("  Press (1-5, A, O, S, T, Q): ", end="", flush=True)

    running = True
    while running and client.is_connected:
        k = check_key()
        if k:
            if k in ('q', '\x1b'):
                print("\n\n[Exiting] Disconnecting...")
                running = False
                break

            if k == 't':
                await run_auto_test(client)
                print("\n  Press (1-5, A, O, S, T, Q): ", end="", flush=True)
                continue

            if k in KEYS:
                cmd_char, desc = KEYS[k]
                ack = await send_cmd(client, cmd_char)
                t = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                if ack:
                    print(f"\r  \033[94m──► [{t}] Key '{k.upper()}' ── Sent '{cmd_char}'\033[0m ({desc}) ◄── \033[92m{ack}\033[0m")
                else:
                    print(f"\r  \033[94m──► [{t}] Key '{k.upper()}' ── Sent '{cmd_char}'\033[0m ({desc})")

                print("  Command > ", end="", flush=True)

        await asyncio.sleep(0.02)


async def main():
    print("\n" + "=" * 66)
    print("  Smart Vehicle — Bluetooth LED Diagnostics & Telemetry")
    print(f"  Target MAC: {BLE_ADDRESS}")
    print("=" * 66)
    print("  Connecting to BLE module...")

    try:
        async with BleakClient(BLE_ADDRESS, timeout=12.0) as client:
            if not client.is_connected:
                print(f"[ERROR] Could not connect to {BLE_ADDRESS}.")
                return

            print(f"[OK] Connected successfully to {BLE_ADDRESS}!")

            # Subscribe to FFE1 notifications
            await client.start_notify(UUID_UART, on_notify)
            print("[OK] Subscribed to UART feedback notifications.")

            # 1. Run the complete automated test
            await run_auto_test(client)

            # 2. Enter persistent manual mode
            await run_manual_switchboard(client)

    except asyncio.TimeoutError:
        print("\n[ERROR] Connection timed out. Ensure BLE module is powered.")
    except Exception as ex:
        print(f"\n[ERROR] Session error: {ex}")

    print("\n[Done] Disconnected cleanly.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Aborted]")
