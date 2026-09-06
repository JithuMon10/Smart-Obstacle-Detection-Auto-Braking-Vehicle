"""
===============================================================================
  SMART VEHICLE — VERIFIED BLE LED TESTER & TELEMETRY CLIENT
===============================================================================
  Target Device:       A0:85:E0:1C:3E:10
  Write UUID (TX):     0000FFE2-0000-1000-8000-00805F9B34FB
  Notify UUID (RX):    0000FFE1-0000-1000-8000-00805F9B34FB

  UART SETTINGS ON STM32:
    Hardware: USART1 (Serial1) on Blue Pill
    Baud:     9600
    Pins:     PA10 = RX, PA9 = TX

  COMMAND PROTOCOL:
    '1' ──► PB5 only                  (Expected ACK: "ACK:1")
    '2' ──► PB9 only                  (Expected ACK: "ACK:2")
    '3' ──► PB6 only                  (Expected ACK: "ACK:3")
    '4' ──► PB7 only                  (Expected ACK: "ACK:4")
    '5' ──► PB8 only                  (Expected ACK: "ACK:5")
    'A' ──► All 5 LEDs ON             (Expected ACK: "ACK:A")
    'O' ──► All 5 LEDs OFF            (Expected ACK: "ACK:O")
    'S' ──► PB6 Blue ON (Standby)     (Expected ACK: "ACK:S")
    'F' ──► PB5 + PB9 ON (Forward)    (Expected ACK: "ACK:F")
    'B' ──► PB7 + PB8 ON (Backward)   (Expected ACK: "ACK:B")
    'L' ──► PB5 + PB7 ON (Left Turn)  (Expected ACK: "ACK:L")
    'R' ──► PB9 + PB8 ON (Right Turn) (Expected ACK: "ACK:R")
===============================================================================
"""

import sys
import os
import asyncio
from datetime import datetime
from bleak import BleakClient

# Windows non-blocking single-keypress detection
if sys.platform == "win32":
    import msvcrt
else:
    import select

# --- CONFIGURATION ---
BLE_ADDRESS = "A0:85:E0:1C:3E:10"
UUID_WRITE  = "0000ffe2-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY = "0000ffe1-0000-1000-8000-00805f9b34fb"

# Global ACK tracking
ack_event = asyncio.Event()
latest_ack = ""

# Automated Test Sequence
TEST_STAGES = [
    # (cmd, display_name, target_hardware, duration_sec)
    ("1", "INDIVIDUAL LED 1",       "Front Left GREEN1  (PB5 only)", 1.5),
    ("2", "INDIVIDUAL LED 2",       "Front Right GREEN2 (PB9 only)", 1.5),
    ("3", "INDIVIDUAL LED 3",       "Center BLUE        (PB6 only)", 1.5),
    ("4", "INDIVIDUAL LED 4",       "Rear Left RED_L    (PB7 only)", 1.5),
    ("5", "INDIVIDUAL LED 5",       "Rear Right RED_R   (PB8 only)", 1.5),
    ("A", "ALL 5 LEDS ON",          "Every LED ON [PB5, PB9, PB6, PB7, PB8]", 2.0),
    ("O", "ALL 5 LEDS OFF",         "All LEDs Dark", 1.0),
    ("F", "FORWARD HEADLIGHTS",     "Front Greens [PB5, PB9] ON", 1.5),
    ("B", "BACKWARD TAILLIGHTS",    "Rear Reds    [PB7, PB8] ON", 1.5),
    ("L", "LEFT SIDE INDICATORS",   "Left Green+Red [PB5, PB7] ON", 1.5),
    ("R", "RIGHT SIDE INDICATORS",  "Right Green+Red [PB9, PB8] ON", 1.5),
    ("S", "STANDBY / STOP",         "Center Blue  (PB6) ON", 1.0),
]

# Manual key bindings
KEY_COMMANDS = {
    '1': ('1', "GREEN1 (PB5 only)"),
    '2': ('2', "GREEN2 (PB9 only)"),
    '3': ('3', "BLUE (PB6 only)"),
    '4': ('4', "RED_L (PB7 only)"),
    '5': ('5', "RED_R (PB8 only)"),
    'a': ('A', "ALL 5 LEDs ON"),
    'o': ('O', "ALL LEDs OFF"),
    's': ('S', "STANDBY / STOP (PB6 Blue)"),
    ' ': ('S', "STANDBY / STOP (PB6 Blue)"),
    'f': ('F', "FORWARD (PB5 + PB9)"),
    'w': ('F', "FORWARD (PB5 + PB9)"),
    'b': ('B', "BACKWARD (PB7 + PB8)"),
    'l': ('L', "LEFT TURN (PB5 + PB7)"),
    'r': ('R', "RIGHT TURN (PB9 + PB8)"),
    'd': ('R', "RIGHT TURN (PB9 + PB8)"),
}


def on_notification(sender, data: bytearray):
    """Callback when STM32 transmits characters back to BLE module"""
    global latest_ack
    try:
        text = data.decode("utf-8", errors="replace").strip()
        if text:
            latest_ack = text
            ack_event.set()
    except Exception:
        pass


def check_key():
    """Non-blocking keyboard reader"""
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


async def send_command_and_wait_ack(client: BleakClient, cmd: str, timeout: float = 1.0) -> str:
    """
    Sends command character to FFE2 and waits for ACK from FFE1.
    Returns the received ACK string or None if timed out.
    """
    global latest_ack
    ack_event.clear()
    latest_ack = ""

    # Send command byte to FFE2 (No-Response Write)
    await client.write_gatt_char(UUID_WRITE, cmd.encode("ascii"), response=False)

    # Wait for STM32 response via notification
    try:
        await asyncio.wait_for(ack_event.wait(), timeout=timeout)
        return latest_ack
    except asyncio.TimeoutError:
        return None


async def run_automated_sequence(client: BleakClient):
    """Runs through each stage and prints physical progress and ACK status"""
    total = len(TEST_STAGES)
    print("\n" + "=" * 68)
    print("        STARTING AUTOMATED LED VERIFICATION SEQUENCE        ")
    print(f"        Total Stages: {total}  |  Watch your vehicle LEDs!    ")
    print("=" * 68)

    for i, (cmd, name, desc, hold_time) in enumerate(TEST_STAGES, start=1):
        print(f"\n  [{i:02d}/{total:02d}] \033[1;93m{name}\033[0m")
        print(f"        Action : \033[96mSending '{cmd}'\033[0m ──► {desc}")

        # Send command and wait for ACK
        ack = await send_command_and_wait_ack(client, cmd, timeout=0.8)

        if ack:
            print(f"        STM32  : \033[92m✔ {ack} (Confirmed by STM32 Serial1)\033[0m")
        else:
            print(f"        STM32  : \033[93m(Sent '{cmd}' — waiting for observation)\033[0m")

        # Keep LED on for observation
        await asyncio.sleep(hold_time)

    print("\n" + "=" * 68)
    print("  \033[92m✔ AUTOMATED TEST SEQUENCE FINISHED!\033[0m")
    print("=" * 68)


async def run_interactive_mode(client: BleakClient):
    """Interactive manual mode that stays connected indefinitely until user quits"""
    print("\n" + "-" * 68)
    print("  \033[1;96mINTERACTIVE MANUAL LED SWITCHBOARD (SESSION ACTIVE)\033[0m")
    print("  ------------------------------------------------------------------")
    print("  [1] Green 1 (PB5)   |  [4] Red Left  (PB7)  |  [F] Forward (PB5+PB9)")
    print("  [2] Green 2 (PB9)   |  [5] Red Right (PB8)  |  [B] Backward(PB7+PB8)")
    print("  [3] Blue    (PB6)   |  [A] All 5 ON         |  [L] Left Turn(PB5+PB7)")
    print("  [S] Stop/Standby    |  [O] All 5 OFF        |  [R] Right Turn(PB9+PB8)")
    print("  [T] Re-run Auto Sequence                    |  [Q] Quit & Disconnect")
    print("  ------------------------------------------------------------------")
    print("  Press any key above to control LEDs: ", end="", flush=True)

    running = True
    while running and client.is_connected:
        k = check_key()
        if k:
            if k in ('q', '\x1b'):
                print("\n\n[Exiting] Sending Standby 'S' and disconnecting cleanly...")
                try:
                    await client.write_gatt_char(UUID_WRITE, b"S", response=False)
                except Exception:
                    pass
                running = False
                break

            if k == 't':
                await run_automated_sequence(client)
                print("\n  Press any key to control LEDs (1-5, A, O, S, F, B, L, R, Q): ", end="", flush=True)
                continue

            if k in KEY_COMMANDS:
                cmd_char, desc = KEY_COMMANDS[k]
                ack = await send_command_and_wait_ack(client, cmd_char, timeout=0.6)
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                if ack:
                    print(f"\r  \033[94m──► [{timestamp}] Sent '{cmd_char}'\033[0m ({desc})  ◄── \033[92m{ack}\033[0m")
                else:
                    print(f"\r  \033[94m──► [{timestamp}] Sent '{cmd_char}'\033[0m ({desc})")

                print("  Command > ", end="", flush=True)

        await asyncio.sleep(0.02)


async def main():
    print("\n" + "=" * 68)
    print("  STM32 BLE LED Diagnostic Tester")
    print(f"  Target BLE MAC: {BLE_ADDRESS}")
    print(f"  Write UUID:     {UUID_WRITE}")
    print(f"  Notify UUID:    {UUID_NOTIFY}")
    print("=" * 68)
    print("  Connecting to vehicle...")

    try:
        async with BleakClient(BLE_ADDRESS, timeout=12.0) as client:
            if not client.is_connected:
                print(f"[ERROR] Could not connect to {BLE_ADDRESS}.")
                return

            print(f"[OK] Connected successfully to {BLE_ADDRESS}!")

            # Subscribe to FFE1 for STM32 ACK telemetry
            try:
                await client.start_notify(UUID_NOTIFY, on_notification)
                print("[OK] Subscribed to FFE1 notifications (Telemetry & ACK active).")
            except Exception as ex:
                print(f"[NOTE] Notification subscription on FFE1 failed ({ex}). Proceeding in TX mode.")

            # 1. Run the complete automated test routine
            await run_automated_sequence(client)

            # 2. Enter interactive manual mode and DO NOT disconnect until Q is pressed
            await run_interactive_mode(client)

    except asyncio.TimeoutError:
        print("\n[ERROR] Connection timed out. Make sure the STM32 and BLE module are powered.")
    except Exception as ex:
        print(f"\n[ERROR] Session error: {ex}")

    print("\n[Done] BLE link closed cleanly.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Aborted by user]")
