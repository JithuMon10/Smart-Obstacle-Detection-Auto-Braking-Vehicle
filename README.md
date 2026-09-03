# 🚗 Smart Obstacle Detection & Auto-Braking Vehicle

An intelligent, autonomous, and Bluetooth-teleoperated 4WD robotic vehicle powered by the **STM32F103C8T6 (ARM Cortex-M3 Blue Pill)** microcontroller. The system features real-time ultrasonic distance sensing, an automatic emergency braking (AEB) safety override, a full automotive status and brake lighting system, and bi-directional Bluetooth teleoperation.

---

## 🌟 Key Features

* **Autonomous Collision Avoidance & AEB:** Front-facing HC-SR04 ultrasonic sensor continuously scans the forward trajectory. If an obstacle breaches the critical threshold ($\le 25\text{ cm}$), the vehicle triggers an immediate emergency stop with active counter-torque braking to counteract chassis inertia.
* **4WD Dual H-Bridge Motor Propulsion:** L298N driver controlling four high-torque DC gear motors in two parallel groups (Left: FL + RL, Right: FR + RR) with full PWM speed variation and tank-steering capability.
* **Automotive Dual-Zone Lighting System:**
  * **Front Status Indicators:** Green LED 1 (`PB5`) for power/headlight status, Green LED 2 (`PB9`) for cruising/animation, and Blue LED (`PB6`) for Bluetooth pairing status.
  * **Rear Dual-Bank Brake Light Bar:** 4× high-intensity Red LEDs (Rear Left pair on `PB7`, Rear Right pair on `PB8`), each with its own dedicated $220\,\Omega$ resistor, illuminating simultaneously during active braking or deceleration.
* **Isolated Dual-Power Architecture:** Electrically separated motor power ($6.0\text{V}$ from $4\times\text{AA}$ batteries) and sensitive digital logic ($5.0\text{V}$ from USB power bank) connected via a single unified common ground to eliminate inductive voltage spikes and brownouts.
* **Protected Level Shifting:** Hardware resistor voltage divider ($2.2\text{ k}\Omega + 4.7\text{ k}\Omega$) safely steps down the HC-SR04 $5.0\text{V}$ echo signal to a microcontroller-safe $3.41\text{V}$ at `PB1`.
* **Wireless Teleoperation:** HC-05 Bluetooth module operating over hardware USART (`PA9`/`PA10`) for responsive keyboard control (WASD) from smartphone or PC terminal.

---

## 🏗️ System Architecture

```
                                  ┌────────────────────────┐
                                  │   5V USB Power Bank    │
                                  └───────────┬────────────┘
                                              │ Micro-USB
                                              ▼
┌───────────────────────┐            ┌─────────────────┐            ┌────────────────────────┐
│ 4× AA Battery (6.0V)  │            │ STM32 Blue Pill │            │     HC-05 Bluetooth    │
└──────────┬────────────┘            │ (ARM Cortex-M3) │◄──UART1───►│       (3.3V Rail)      │
           │ SPST Switch             └────────┬────────┘            └────────────────────────┘
           ▼                                  │
┌───────────────────────┐                     ├──────PWM / GPIO────► 4× Status / Brake LEDs
│   L298N Motor Driver  │◄────IN1-IN4,ENA,ENB─┤
│   (+12V Motor Power)  │                     │
└──────────┬────────────┘                     └──────TRIG / ECHO───► HC-SR04 Ultrasonic
           │ OUT1-OUT4 (PWM)                                         (with 2.2k/4.7k divider)
     ┌─────┴───────────────┐
     ▼                     ▼
┌──────────────┐     ┌──────────────┐
│ Left Motors  │     │ Right Motors │
│  (FL + RL)   │     │  (FR + RR)   │
└──────────────┘     └──────────────┘
```

---

## ⚡ Dual-Power Architecture

To prevent motor current surges from resetting the STM32 microcontroller, power is divided into two distinct, isolated sources:

```
[Power Source 1: Motors Only]
  4× AA Battery Pack (6.0V)
    └──> SPST Power Switch
           └──> L298N "+12V" Screw Terminal (VS) ──> 4× DC Motors

[Power Source 2: Digital Electronics]
  5V USB Power Bank
    └──> STM32 Blue Pill Micro-USB Port
           ├──> 5V Header Pin (c17) ──> HC-SR04 VCC (5V Sensor Supply)
           ├──> 5V Header Pin (c17) ──> L298N "+5V" Screw Terminal (VSS Logic Supply)
           └──> 3.3V Regulated Output (c19) ──> HC-05 Bluetooth VCC (3.3V Supply)

[Unified Ground Reference]
  Battery 1(-) ═══ L298N GND ═══ Blue Pill GND ═══ Sensors & LEDs GND
```

---

## 📌 Pinout & Hardware Mapping

### STM32F103C8T6 (Blue Pill) Connections

| STM32 Pin | Direction | Connected Device | Device Terminal | Function / Description |
|---|---|---|---|---|
| **PA0** | OUTPUT | L298N Motor Driver | `IN1` | Left Motors Forward Direction |
| **PA1** | OUTPUT | L298N Motor Driver | `IN2` | Left Motors Reverse Direction |
| **PA2** | OUTPUT | L298N Motor Driver | `IN3` | Right Motors Forward Direction |
| **PA3** | OUTPUT | L298N Motor Driver | `IN4` | Right Motors Reverse Direction |
| **PA6** | PWM OUT | L298N Motor Driver | `ENA` | Left Motors Speed (TIM3_CH1) |
| **PA7** | PWM OUT | L298N Motor Driver | `ENB` | Right Motors Speed (TIM3_CH2) |
| **PA9** | UART TX | HC-05 Bluetooth | `RXD` | MCU Transmit $\rightarrow$ Bluetooth Receive |
| **PA10** | UART RX | HC-05 Bluetooth | `TXD` | MCU Receive $\leftarrow$ Bluetooth Transmit |
| **PB0** | OUTPUT | HC-SR04 Ultrasonic | `TRIG` | $10\,\mu\text{s}$ Ultrasonic Trigger Pulse |
| **PB1** | INPUT | HC-SR04 Ultrasonic | Divider Midpoint | Safe Echo Pulse ($5\text{V} \rightarrow 3.41\text{V}$) |
| **PB5** | OUTPUT | Front Green LED 1 | Via $220\,\Omega$ | Headlight / Power status indicator |
| **PB9** | OUTPUT | Front Green LED 2 | Via $220\,\Omega$ | Independent cruising / animation indicator |
| **PB6** | OUTPUT | Status Blue LED | Via $220\,\Omega$ | Bluetooth pairing / link status indicator |
| **PB7** | OUTPUT | Rear Left Brake LEDs | Via $2\times 220\,\Omega$ | Red LED 1 (Outer) & Red LED 3 (Inner) in parallel |
| **PB8** | OUTPUT | Rear Right Brake LEDs | Via $2\times 220\,\Omega$ | Red LED 2 (Outer) & Red LED 4 (Inner) in parallel |
| **PB12** | OUTPUT | HC-05 Bluetooth | `EN` / `KEY` | AT Command Mode Control (Optional) |
| **5V** | POWER OUT | HC-SR04 & L298N | `VCC` & `+5V (VSS)` | 5V USB Bus Distribution |
| **3.3V** | POWER OUT | HC-05 Bluetooth | `VCC` | 3.3V Onboard Regulated Output |
| **G (GND)**| GROUND | Common Ground Rail| `GND` | Unified ground reference for all components |

---

## 🛡️ Echo Protection Voltage Divider

The HC-SR04 ultrasonic sensor operates at $5.0\text{V}$ and outputs a $5.0\text{V}$ logic pulse on its `ECHO` pin. To protect the STM32's `PB1` input pin, a two-resistor voltage divider is placed between `ECHO` and ground:

```
HC-SR04 ECHO (5.0V) ───[ 2.2kΩ R_TOP ]───┬───[ 4.7kΩ R_BOT ]─── GND
                                         │
                                   Midpoint Node
                                         │ (3.41V max)
                                         ▼
                                  STM32 Pin PB1
```

$$\text{V}_{\text{PB1}} = 5.0\text{V} \times \frac{4.7\text{ k}\Omega}{2.2\text{ k}\Omega + 4.7\text{ k}\Omega} = 5.0\text{V} \times \frac{4700}{6900} \approx 3.41\text{V} \quad (\le 3.6\text{V Safe Limit})$$

---

## 🚨 Critical Physical Assembly Rules

> [!IMPORTANT]
> **1. REMOVE ALL THREE JUMPER CAPS ON THE RED L298N MODULE:**
> * **5V Regulator Jumper:** Must be **REMOVED**. External $5.0\text{V}$ logic is supplied from the USB power bank via Blue Pill `5V` to the `+5V` screw terminal. Leaving the jumper installed will cause the onboard regulator to fight the USB supply!
> * **ENA & ENB Jumpers:** Must be **REMOVED** so `PA6` and `PA7` can provide PWM motor speed regulation.

> [!CAUTION]
> **2. DO NOT CONNECT RAW BATTERY VOLTAGE TO STM32:**
> The $4\times\text{AA}$ battery pack ($6.0\text{V}$) must connect **ONLY** through the SPST switch to the L298N `+12V (VS)` terminal. It must **NEVER** touch `5V`, `3.3V`, `VDD`, `VDDA`, or `VBAT` on the Blue Pill.

> [!WARNING]
> **3. LED POLARITY & RESISTORS:**
> Every single LED must have its own dedicated $220\,\Omega$ current-limiting resistor on the anode (long leg). All cathodes (short leg) connect directly to the common ground rail.

---

## 🎮 Bluetooth Control Protocol (WASD)

When paired with a computer or mobile Bluetooth serial terminal (`9600` baud, 8-N-1):

| Command Byte | Action | Motor States | Rear Brake Lights | Front Status LEDs |
|:---:|---|---|:---:|:---:|
| **`W` / `w`** | Forward | Left & Right Forward | OFF | Solid ON |
| **`S` / `s`** | Reverse | Left & Right Reverse | Blinking | Normal |
| **`A` / `a`** | Spin Turn Left | Left Reverse, Right Forward | Left Bank Blinking | Normal |
| **`D` / `d`** | Spin Turn Right | Left Forward, Right Reverse | Right Bank Blinking | Normal |
| **`X` / `x`** | Stop / Coast | All Motors Stopped (PWM 0) | Solid ON | Normal |
| **`0` – `9`** | Speed Presets | Scaled PWM output ($90 - 255$) | — | — |
| **`q`** | Turbo Boost | Maximum PWM ($255$) | — | Fast Pulse |

---

## 📦 Hardware Bill of Materials (BOM)

| # | Component | Quantity | Notes |
|---|---|:---:|---|
| 1 | STM32F103C8T6 (Blue Pill) ARM Cortex-M3 Board | 1 | 72 MHz, 64KB Flash, 20KB SRAM |
| 2 | ST-Link V2 USB Programmer | 1 | Firmware flashing via SWD (`SWDIO`, `SWCLK`) |
| 3 | L298N Dual H-Bridge Motor Driver Module | 1 | High-power dual motor driver |
| 4 | 4WD Robot Chassis Kit with 4× TT Geared Motors | 1 | Includes 4 wheels and mounting plate |
| 5 | HC-SR04 Ultrasonic Distance Sensor | 1 | 2 cm – 400 cm range |
| 6 | HC-05 Bluetooth Serial Module | 1 | SPP wireless UART communication |
| 7 | SPST Rocker / Toggle Switch | 1 | Main motor battery power isolation |
| 8 | 4-Cell AA Battery Holder + 4× AA Alkaline Batteries | 1 | 6.0V dedicated motor power pack |
| 9 | 5V USB Power Bank + Micro-USB Cable | 1 | Regulated clean logic power |
| 10 | 5mm Red LEDs (Brake Light Array) | 4 | Rear brake indicators |
| 11 | 5mm Green LEDs | 2 | Headlight & cruising status indicators |
| 12 | 5mm Blue LED | 1 | Bluetooth pairing indicator |
| 13 | $220\,\Omega$ Resistors (1/4W) | 8 | LED current-limiting ($6\times$ in circuit + spares) |
| 14 | $2.2\text{ k}\Omega$ Resistor (1/4W) | 1 | Echo voltage divider top ($R_{\text{TOP}}$) |
| 15 | $4.7\text{ k}\Omega$ Resistor (1/4W) | 1 | Echo voltage divider bottom ($R_{\text{BOT}}$) |
| 16 | 400-Point Solderless Breadboard & Jumper Wires | 1 | Circuit prototyping & interconnections |

---

## 🛠️ Software Development Roadmap

The upcoming firmware is organized into modular drivers:
1. **Core Supervisor (`main.cpp`):** Cooperative non-blocking scheduler running at $50\text{ Hz}$.
2. **Motor Driver (`motors.cpp`):** Hardware PWM acceleration curves, forward/reverse H-bridge polarity control, and active emergency brake torque injection.
3. **Safety Observer (`sensor.cpp`):** Moving-average filtered distance acquisition with obstacle tripwire interrupts.
4. **Lighting Manager (`lighting.cpp`):** Dynamic automotive brake light strobes and hazard turn animations.
5. **Telemetry / Bluetooth Handler (`bluetooth.cpp`):** Packet parser for single-byte WASD commands with live distance telemetry return.

---

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
