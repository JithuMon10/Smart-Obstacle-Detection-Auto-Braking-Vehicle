# 🚗 Smart Obstacle Detection & Automatic Braking 4WD Robotic Vehicle

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-STM32%20%7C%20ARM%20Cortex--M3-002B49.svg?logo=stmicroelectronics)](https://www.st.com/en/microcontrollers-microprocessors/stm32f103c8.html)
[![Framework](https://img.shields.io/badge/Framework-Arduino%20%2F%20STM32duino%20%2F%20PlatformIO-00979D.svg?logo=arduino)](https://github.com/stm32duino/Arduino_Core_STM32)
[![Fritzing](https://img.shields.io/badge/Schematic-Fritzing%20Verified-blueviolet.svg)](hardware/Bluetooth_4WD_Robot.fzz)

An intelligent, safety-critical 4-wheel drive (4WD) robotic vehicle powered by the **STM32F103C8T6 (Blue Pill) ARM Cortex-M3** microcontroller. The system combines **real-time ultrasonic collision detection and automatic emergency braking** with **Bluetooth wireless remote control (WASD)** and an **automotive-grade visual lighting system** (front status lights, turn signals, and a 4-LED rear brake light bar).

---

## 📋 Table of Contents
1. [Key Features](#-key-features)
2. [System Architecture](#-system-architecture)
3. [Dual-Power Architecture (Safety-Critical)](#-dual-power-architecture-safety-critical)
4. [Hardware Bill of Materials (BOM)](#-hardware-bill-of-materials-bom)
5. [Pinout & Wiring Matrix](#-pinout--wiring-matrix)
6. [Firmware Architecture](#-firmware-architecture)
7. [Getting Started & Flashing Guide](#-getting-started--flashing-guide)
8. [Bluetooth Remote Control (WASD Protocol)](#-bluetooth-remote-control-wasd-protocol)
9. [Crucial Physical Assembly Rules](#-crucial-physical-assembly-rules)
10. [Repository Structure](#-repository-structure)
11. [License](#-license)

---

## ✨ Key Features

* **🛡️ Autonomous Emergency Braking (AEB):** Real-time acoustic distance pinging via HC-SR04 ultrasonic sensor. If an obstacle enters the critical zone ($\le 25\text{ cm}$), the vehicle automatically applies reverse counter-torque and electronic braking, preventing forward collisions regardless of user input.
* **⚠️ Proactive Speed Degradation:** Dynamically slows down the vehicle when entering the warning buffer zone ($25\text{ cm} - 45\text{ cm}$) to maintain safe stopping distances.
* **📱 Wireless Bluetooth Teleoperation:** Low-latency teleoperation via the HC-05 Bluetooth module using standard WASD keys or mobile RC car apps, with real-time distance and status telemetry streamed back to the controller.
* **🚨 Integrated Automotive Lighting System:**
  * **Front Headlights / Indicators:** Green LEDs (`PB5` and `PB9`) for power, cruising animations, and obstacle warning strobes.
  * **Bluetooth Status:** Blue LED (`PB6`) pulses during standby and goes solid upon pairing.
  * **Rear Brake Light Bar:** 4 Red LEDs arranged symmetrically at the rear (2 on `PB7` + 2 on `PB8`), each with its own current-limiting resistor, operating simultaneously during braking and alternating during turns.
* **⚡ 100% Brownout-Immune Dual-Power Design:** Completely isolates high-current motor inductive kickback from sensitive microcontroller logic.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph PowerSystem ["⚡ Dual-Power Supply Architecture"]
        BATT["4× AA Battery Pack (6.0V)"] -->|Motor Power Only| SW["SPST Power Switch"]
        SW -->|Switched 6V| L298N_VS["L298N VS Terminal (+12V)"]
        USB["5V USB Power Bank"] -->|Logic Supply| STM32["STM32 Blue Pill (USB Port)"]
        STM32 -->|5V Rail| HCSR04_VCC["HC-SR04 VCC (5V)"]
        STM32 -->|5V Rail| L298N_VSS["L298N Logic VSS (+5V)"]
        STM32 -->|3.3V LDO Rail| HC05_VCC["HC-05 VCC (3.3V)"]
        BATT_GND["Battery Negative (-)"] === COMMON_GND["Common Ground Bus"]
        STM_GND["STM32 GND"] === COMMON_GND
        L298_GND["L298N GND"] === COMMON_GND
    end

    subgraph Controller ["🧠 Brain: STM32F103C8T6 ARM Cortex-M3"]
        STM32
    end

    subgraph Inputs ["📡 Sensors & Communication"]
        HCSR04["HC-SR04 Ultrasonic Sensor"] -->|Echo 5V Pulse| DIVIDER["2.2kΩ / 4.7kΩ Voltage Divider"]
        DIVIDER -->|Safe 3.41V Echo| STM32
        STM32 -->|Trig Pulse (PB0)| HCSR04
        HC05["HC-05 Bluetooth Module"] <-->|UART1 (PA9/PA10)| STM32
    end

    subgraph Outputs ["🚗 Actuation & Indicators"]
        STM32 -->|PWM & Direction (PA0-PA3, PA6, PA7)| L298N["L298N Dual H-Bridge Driver"]
        L298N -->|OUT1 / OUT2| MOTORS_L["Left Motors (FL + RL Parallel)"]
        L298N -->|OUT3 / OUT4| MOTORS_R["Right Motors (FR + RR Parallel)"]
        STM32 -->|PB5, PB9| LED_FRONT["Front Indicators (Green 1 & 2)"]
        STM32 -->|PB6| LED_BT["Bluetooth Status (Blue LED)"]
        STM32 -->|PB7, PB8| LED_BRAKE["Rear Brake Lights (4× Red LEDs)"]
    end
```

---

## ⚡ Dual-Power Architecture (Safety-Critical)

DC motors draw large burst currents (stalling can exceed 2 Amperes), causing severe voltage dips and inductive back-EMF spikes. Powering microcontrollers from the same battery pack often causes random resets, watchdog freezes, and sensor jitter.

This design implements a **strict dual-rail architecture**:

1. **Power Source 1 (Motors Only):** 4× AA Alkaline Batteries ($6.0\text{V}$) connected exclusively to the L298N motor driver `+12V (VS)` screw terminal through a dedicated SPST toggle switch.
2. **Power Source 2 (Electronics & Logic):** A 5V USB Power Bank connected to the STM32 Blue Pill's Micro-USB port. The Blue Pill distributes clean 5V to the HC-SR04 and L298N logic rail (`VSS/+5V`), and 3.3V to the HC-05 Bluetooth module.
3. **Common Ground:** The negative terminal of the 4×AA battery pack is tied to the STM32 ground at the L298N `GND` terminal to establish an identical reference potential without ground loops.

---

## 📦 Hardware Bill of Materials (BOM)

| Component | Specification / Details | Qty |
|---|---|:---:|
| **Microcontroller Board** | STM32F103C8T6 (Blue Pill) / GD32F103C8T6 (ARM Cortex-M3, 72MHz) | 1 |
| **Programmer** | ST-Link V2 USB Debugger / Flasher (SWD interface) | 1 |
| **Motor Driver** | L298N Dual H-Bridge Module (Red Board with heatsink) | 1 |
| **Robot Chassis Kit** | 4WD Smart Car Chassis Kit (includes 4× TT DC gear motors & wheels) | 1 |
| **Ultrasonic Sensor** | HC-SR04 Ultrasonic Distance Sensor | 1 |
| **Bluetooth Module** | HC-05 Wireless Serial Transceiver Module (6-pin breakout) | 1 |
| **Brake LEDs** | 3mm or 5mm High-Brightness Red LEDs | 4 |
| **Indicator LEDs** | 5mm Green LEDs (Front) + 1× 5mm Blue LED (Bluetooth) | 3 |
| **Resistors (LEDs)** | $220\,\Omega$ Metal Film Resistors, 1/4W (Current limiting) | 7 |
| **Resistor ($R_{\text{TOP}}$)** | $2.2\text{ k}\Omega$ Resistor, 1/4W (Echo Protection Divider) | 1 |
| **Resistor ($R_{\text{BOT}}$)** | $4.7\text{ k}\Omega$ Resistor, 1/4W (Echo Protection Divider) | 1 |
| **Power Switch** | SPST 2-Pin Rocker or Slide Switch | 1 |
| **Motor Battery Pack** | 4-Cell AA Battery Holder with 4× AA 1.5V Alkaline Batteries ($6.0\text{V}$) | 1 |
| **Electronics Power** | Standard 5V USB Power Bank + Micro-USB Cable | 1 |
| **Prototyping** | 400-Point Solderless Breadboard + M2M, M2F, F2F Jumper Wires | 1 |

---

## 📌 Pinout & Wiring Matrix

### STM32 Blue Pill Board Connection Table

| STM32 Pin | Direction | Connected Peripheral | Destination Pin | Description |
|---|---|---|---|---|
| **PA0** | OUTPUT | L298N Motor Driver | `IN1` | Left Motors Forward |
| **PA1** | OUTPUT | L298N Motor Driver | `IN2` | Left Motors Reverse |
| **PA2** | OUTPUT | L298N Motor Driver | `IN3` | Right Motors Forward |
| **PA3** | OUTPUT | L298N Motor Driver | `IN4` | Right Motors Reverse |
| **PA6** | PWM OUT | L298N Motor Driver | `ENA` | Left Motors Speed (Timer 3, Ch 1) |
| **PA7** | PWM OUT | L298N Motor Driver | `ENB` | Right Motors Speed (Timer 3, Ch 2) |
| **PA9** | UART TX | HC-05 Bluetooth | `RXD` | Transmit Data to HC-05 |
| **PA10** | UART RX | HC-05 Bluetooth | `TXD` | Receive Data from HC-05 |
| **PB0** | OUTPUT | HC-SR04 Ultrasonic | `TRIG` | 10µs Ultrasonic Trigger Pulse |
| **PB1** | INPUT | HC-SR04 Ultrasonic | Divider Midpoint | Echo Signal ($5\text{V} \rightarrow 3.41\text{V}$ safe) |
| **PB5** | OUTPUT | Front Green LED 1 | Via $220\,\Omega$ | Headlight / Power status |
| **PB9** | OUTPUT | Front Green LED 2 | Via $220\,\Omega$ | Cruising / Independent animation |
| **PB6** | OUTPUT | Blue LED | Via $220\,\Omega$ | Bluetooth connection indicator |
| **PB7** | OUTPUT | Rear Left Brake LEDs | Via $2\times 220\,\Omega$ | Red LED 1 (Outer) & Red LED 3 (Inner) |
| **PB8** | OUTPUT | Rear Right Brake LEDs | Via $2\times 220\,\Omega$ | Red LED 2 (Outer) & Red LED 4 (Inner) |
| **PB12** | OUTPUT | HC-05 Bluetooth | `EN` / `KEY` | AT Command Mode Control (Optional) |
| **5V** | POWER | HC-SR04 & L298N | `VCC` & `+5V (VSS)` | 5V USB Bus Distribution |
| **3.3V** | POWER | HC-05 Bluetooth | `VCC` | 3.3V Regulated Output |
| **G** | GROUND | Ground Rail | Common GND | Unified Ground Net |

---

## 💻 Firmware Architecture

The firmware is built with a non-blocking architecture using `millis()` scheduling to guarantee that high-speed sensor pings and Bluetooth command decoding never stall or miss a frame:

```
firmware/Smart_Obstacle_4WD_Robot/
├── Smart_Obstacle_4WD_Robot.ino  # Main supervisor loop, safety overrides & telemetry
├── config.h                      # Pin declarations, safety thresholds, and timing constants
├── motors.h / motors.cpp         # L298N H-Bridge control, soft-start, and active braking
├── sensor.h / sensor.cpp         # Ultrasonic sensor driver with exponential smoothing filter
├── lighting.h / lighting.cpp     # Multi-channel LED manager & automotive turn/brake animations
└── bluetooth.h / bluetooth.cpp   # Non-blocking UART parser and bidirectional telemetry
```

### Safety State Machine
1. **NORMAL_DRIVING:** Vehicle navigates according to user WASD input.
2. **WARNING_ZONE ($25\text{ cm} < \text{Distance} \le 45\text{ cm}$):** Speed is automatically capped to `SLOW_SPEED` (PWM 130), and front LEDs alternate rapidly.
3. **CRITICAL_STOP ($\text{Distance} \le 25\text{ cm}$):** If moving forward, an active reverse counter-torque pulse is fired immediately to overcome momentum, motor power is completely cut, forward motion is software-locked, and all 4 rear brake lights latch ON. Reverse and turning maneuvers remain enabled so the user can steer away.

---

## 🚀 Getting Started & Flashing Guide

### Method A: Arduino IDE (Recommended for Beginners)

1. **Install STM32 Board Package:**
   * Open Arduino IDE $\rightarrow$ **File** $\rightarrow$ **Preferences**.
   * Add this URL to **Additional Boards Manager URLs**:
     ```
     https://github.com/stm32duino/BoardManagerFiles/raw/main/package_stmicroelectronics_index.json
     ```
   * Go to **Tools** $\rightarrow$ **Board** $\rightarrow$ **Boards Manager**, search for `STM32` and install **STM32 MCU based boards**.

2. **Select Board Configuration:**
   * **Board:** `Generic STM32F1 series`
   * **Board part number:** `BluePill F103C8` (or `Generic F103C8Tx`)
   * **U(S)ART support:** `Enabled (generic 'Serial')`
   * **Upload method:** `STLink`

3. **Wire the ST-Link V2 to Blue Pill:**
   | ST-Link V2 Pin | Blue Pill Pin |
   |---|---|
   | **SWDIO** | `DIO` |
   | **SWCLK** | `CLK` |
   | **GND** | `GND` |
   | **3.3V** | `3.3V` |

4. **Upload:** Open `firmware/Smart_Obstacle_4WD_Robot/Smart_Obstacle_4WD_Robot.ino` and click **Upload** (`Ctrl+U`).

---

### Method B: VS Code + PlatformIO

1. Open this repository folder in VS Code with the **PlatformIO IDE** extension installed.
2. Connect your ST-Link V2 programmer to the Blue Pill.
3. Click the PlatformIO **Upload** button in the status bar (or run `pio run --target upload`).

---

## 🎮 Bluetooth Remote Control (WASD Protocol)

Pair your computer or Android smartphone with the **HC-05** module:
* **Default Name:** `HC-05`
* **Default Pairing PIN:** `1234` or `0000`
* **Baud Rate:** `9600` (8-N-1)

Use any Serial Bluetooth Terminal app or custom application to send single-byte commands:

| Key | Direction / Action | Motor States | Rear Brake Lights |
|:---:|---|---|:---:|
| **`W` / `F`** | Forward | Left & Right Forward | OFF |
| **`S` / `B`** | Reverse | Left & Right Reverse | Blinking |
| **`A` / `L`** | Spin Turn Left | Left Reverse, Right Forward | Left Bank Blinking |
| **`D` / `R`** | Spin Turn Right | Left Forward, Right Reverse | Right Bank Blinking |
| **`X` / ` `** | Stop / Coast | All Motors Disengaged | Solid ON |
| **`0` – `9`** | Speed Scale ($90 - 255$ PWM) | Sets variable driving speed | — |
| **`q`** | Turbo Boost (Full 255 PWM) | Maximum motor torque | — |

The vehicle continuously reports telemetry back over Bluetooth every 500ms:
```text
DIST:32cm | STAT:FORWARD
DIST:21cm | STAT:EMERGENCY_BRAKE_ACTIVATED
DIST:19cm | STAT:FORWARD_BLOCKED_BY_OBSTACLE
```

---

## ⚠️ Crucial Physical Assembly Rules

> [!IMPORTANT]
> **1. REMOVE ALL THREE JUMPERS ON THE L298N DRIVER:**
> * **5V Regulator Jumper:** Must be removed. The Blue Pill supplies external 5V to the `+5V (VSS)` terminal. Leaving this jumper on will cause the onboard regulator to fight the USB supply!
> * **ENA & ENB Jumpers:** Must be removed so `PA6` and `PA7` can provide dynamic PWM speed control.

> [!CAUTION]
> **2. DO NOT SKIP THE ECHO VOLTAGE DIVIDER:**
> The HC-SR04 emits a 5.0V echo pulse. Direct connection to `PB1` can degrade or permanently damage the STM32's input stage. Always use the $2.2\text{ k}\Omega$ and $4.7\text{ k}\Omega$ divider to safely step down the voltage to $3.41\text{V}$.

> [!WARNING]
> **3. LED POLARITY:**
> Every LED has a longer leg (Anode, $+$) and a shorter leg with a flat edge (Cathode, $-$). The Anode connects to the $220\,\Omega$ resistor from the GPIO pin. The Cathode connects directly to the common ground rail.

---

## 📁 Repository Structure

```
Smart-Obstacle-Detection-Auto-Braking-Vehicle/
├── .gitignore
├── LICENSE
├── README.md
├── platformio.ini
├── hardware/
│   ├── Bluetooth_4WD_Robot.fzz  # Complete verified Fritzing schematic & breadboard view
│   └── wiring_pinout.md         # Full physical wire connection checklist
└── firmware/
    └── Smart_Obstacle_4WD_Robot/
        ├── Smart_Obstacle_4WD_Robot.ino  # Main sketch & control loop
        ├── config.h                      # Hardware pins and thresholds
        ├── motors.h / motors.cpp         # L298N 4WD motion controller
        ├── sensor.h / sensor.cpp         # Ultrasonic distance & smoothing filter
        ├── lighting.h / lighting.cpp     # Visual lighting & brake animations
        └── bluetooth.h / bluetooth.cpp   # Bluetooth serial command handler
```

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
