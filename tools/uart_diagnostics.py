"""
===============================================================================
  MINIMAL UART DIAGNOSTIC CONSOLE FOR STM32 BLUE PILL
===============================================================================
  Target:       A0:85:E0:1C:3E:10
  Write UUID:   0000FFE2-0000-1000-8000-00805F9B34FB  (Single raw byte TX)
  Notify UUID:  0000FFE1-0000-1000-8000-00805F9B34FB  (ACK & Telemetry RX)

  PURPOSE:
  Tests low-level STM32 UART (PA10 RX / PA9 TX) communication in real time.
  Pressing '1' through '5' directly toggles the corresponding LED on the vehicle
  and prints the immediate ACK returned by the STM32.
===============================================================================
"""

import sys
import asyncio
from datetime import datetime
from bleak import BleakClient

# Windows single-keypress detection
if sys.platform == "win32":
    import msvcrt
else:
    import select

BLE_ADDRESS = "A0:85:E0:1C:3E:10"
UUID_WRITE  = "0000ffe2-0000-1000-8000-00805f9b34fb"
UUID_NOTIFY = "0000ffe1-0000-1000-8000-00805f9b34fb"

KEY_MAP = {
    '1': ('1', "Toggle PB5 (Green 1)"),
    '2': ('2', "Toggle PB9 (Green 2)"),
    '3': ('3', "Toggle PB6 (Blue)"),
    '4': ('4', "Toggle PB7 (Red Left)"),
    '5': ('5', "Toggle PB8 (Red Right)"),
    'a': ('A', "All 5 LEDs ON"),
    'o': ('O', "All 5 LEDs OFF"),
    's': ('S', "Standby (PB6 Blue ON)"),
}


def on_notify(sender, data: bytearray):
    """Prints incoming raw notification from STM32"""
    raw_hex = " ".join(f"{b:02X}" for b in data)
    text = data.decode("utf-8", errors="replace").strip()
    t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n  \033[1;92m◄── [{t}] STM32 RESPONSE: '{text}'  (Hex: {raw_hex})\033[0m")
    print("  Press (1-5, A, O, S, Q): ", end="", flush=True)


def get_key():
    """Non-blocking key read"""
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


async def main():
    print("\n" + "=" * 66)
    print("      STM32 BLUE PILL — LOW-LEVEL UART DIAGNOSTIC TOOL       ")
    print("=" * 66)
    print(f"  Target Device : {BLE_ADDRESS}")
    print(f"  Write Char    : FFE2 (Direct single-byte write)")
    print(f"  Notify Char   : FFE1 (Incoming serial stream)")
    print("=" * 66)
    print("  Connecting to BLE module...")

    try:
        async with BleakClient(BLE_ADDRESS, timeout=12.0) as client:
            if not client.is_connected:
                print(f"[ERROR] Could not connect to {BLE_ADDRESS}.")
                return

            print(f"[OK] Connected successfully to {BLE_ADDRESS}!")

            # Subscribe to FFE1 notifications
            try:
                await client.start_notify(UUID_NOTIFY, on_notify)
                print("[OK] Subscribed to FFE1 notifications.")
            except Exception as ex:
                print(f"[NOTE] FFE1 notification failed: {ex}")

            print("\n" + "-" * 66)
            print("  READY! Tap any key below to test STM32 UART:")
            print("    [1] Toggle Green 1 (PB5)   |  [4] Toggle Red Left  (PB7)")
            print("    [2] Toggle Green 2 (PB9)   |  [5] Toggle Red Right (PB8)")
            print("    [3] Toggle Blue    (PB6)   |  [A] All 5 LEDs ON")
            print("    [S] Standby (Blue ON)      |  [O] All 5 LEDs OFF")
            print("    [Q] Quit")
            print("-" * 66)
            print("  Press (1-5, A, O, S, Q): ", end="", flush=True)

            running = True
            while running and client.is_connected:
                k = get_key()
                if k:
                    if k in ('q', '\x1b'):
                        print("\n\n[Exiting] Disconnecting...")
                        running = False
                        break

                    if k in KEY_MAP:
                        cmd_byte, desc = KEY_MAP[k]
                        payload = cmd_byte.encode("ascii")  # Exact 1-byte raw payload
                        t = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        hex_val = f"0x{payload[0]:02X}"

                        # Transmit directly with response=True (Acknowledged ATT Write)
                        await client.write_gatt_char(UUID_WRITE, payload, response=True)
                        print(f"\n  \033[94m──► [{t}] Sent raw byte: '{cmd_byte}' ({hex_val}) ── {desc}\033[0m")
                        print("  Press (1-5, A, O, S, Q): ", end="", flush=True)

                await asyncio.sleep(0.02)

    except asyncio.TimeoutError:
        print("\n[ERROR] Connection timed out. Make sure the BLE module is powered on.")
    except Exception as e:
        print(f"\n[ERROR] Session error: {e}")

    print("\n[Done] Disconnected cleanly.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Aborted by user]")
