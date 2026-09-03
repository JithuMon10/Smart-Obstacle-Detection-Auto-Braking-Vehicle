# 📌 Comprehensive Hardware Wiring & Pinout Guide

This document defines the complete physical wiring mapping for the **Smart Obstacle Detection & Automatic Braking 4WD Robotic Vehicle**.

---

## ⚡ 1. Dual-Power Architecture

To prevent motor electrical noise (inductive kickback and brownouts) from resetting the STM32 microcontroller and sensors, the robot uses a strictly isolated **Dual-Power Architecture**:

```
Power Source 1 (Motors Only - High Current):
  4×AA Alkaline Batteries (6.0V) ──→ SPST Power Switch ──→ L298N "+12V" (VS) Terminal

Power Source 2 (Electronics & Logic - Clean 5V):
  5V USB Power Bank ──→ STM32 Blue Pill USB Port
                             ├── 5V Pin ──→ HC-SR04 VCC (Sensor 5V)
                             ├── 5V Pin ──→ L298N "+5V" (VSS Logic Supply)
                             └── 3.3V Pin (Onboard LDO) ──→ HC-05 VCC (3.3V)

Unified Ground Net:
  Battery (-) ──┬── L298N "GND" Terminal
                └── STM32 "G" (GND) Pin ──→ Shared by HC-05, HC-SR04, LEDs & Voltage Divider
```

> [!CAUTION]
> **No battery voltage (6V) ever connects to the STM32 board.** All electronic logic is powered strictly by the clean 5V USB rail.

---

## 🔌 2. Complete Pinout Table (STM32 Blue Pill)

| STM32 Pin | Type | Connected Component | Physical Terminal | Notes / Function |
|---|---|---|---|---|
| **PA0** | GPIO OUT | L298N Motor Driver | `IN1` | Left Motors Forward Direction |
| **PA1** | GPIO OUT | L298N Motor Driver | `IN2` | Left Motors Reverse Direction |
| **PA2** | GPIO OUT | L298N Motor Driver | `IN3` | Right Motors Forward Direction |
| **PA3** | GPIO OUT | L298N Motor Driver | `IN4` | Right Motors Reverse Direction |
| **PA6** | PWM OUT | L298N Motor Driver | `ENA` | Left Motors Speed Control (TIM3_CH1) |
| **PA7** | PWM OUT | L298N Motor Driver | `ENB` | Right Motors Speed Control (TIM3_CH2) |
| **PA9** | UART TX | HC-05 Bluetooth Module | `RXD` | Transmit Data to Bluetooth (crossed) |
| **PA10** | UART RX | HC-05 Bluetooth Module | `TXD` | Receive Data from Bluetooth (crossed) |
| **PB0** | GPIO OUT | HC-SR04 Ultrasonic | `TRIG` | 10µs Trigger Pulse (3.3V compatible) |
| **PB1** | GPIO IN | HC-SR04 Ultrasonic | Midpoint Node | 5V Echo via 2.2kΩ / 4.7kΩ Voltage Divider (3.41V) |
| **PB5** | GPIO OUT | Front Green LED 1 | 220Ω Resistor | Power / Headlight Status Indicator |
| **PB9** | GPIO OUT | Front Green LED 2 | 220Ω Resistor | Cruising / Independent Lighting Animation |
| **PB6** | GPIO OUT | Blue LED | 220Ω Resistor | Bluetooth Connection / Heartbeat Indicator |
| **PB7** | GPIO OUT | Rear Left Brake LEDs | 2× 220Ω Resistors | Controls Red LED 1 & Red LED 3 in parallel |
| **PB8** | GPIO OUT | Rear Right Brake LEDs | 2× 220Ω Resistors | Controls Red LED 2 & Red LED 4 in parallel |
| **PB12**| GPIO OUT | HC-05 Bluetooth Module | `EN` / `KEY` | AT Command Mode Control (Optional) |
| **5V**  | Power OUT| HC-SR04 & L298N | `VCC` & `+5V` | Distributes 5V USB power to logic peripherals |
| **3.3V**| Power OUT| HC-05 Bluetooth | `VCC` | Regulated 3.3V supply from Blue Pill LDO |
| **GND** | Ground   | All Subsystems | Common GND | Unified single reference ground |

---

## 🛡️ 3. Ultrasonic Echo Protection Divider

The HC-SR04 output echo pulse is **5.0V**, which exceeds the rated tolerance of regular 3.3V analog/digital inputs. A two-resistor voltage divider is required:

```
HC-SR04 ECHO Pin (5V)
        │
     [2.2 kΩ] (Top Resistor)
        │
        ├───→ Connected to STM32 Blue Pill Pin PB1 (3.41V Safe)
        │
     [4.7 kΩ] (Bottom Resistor)
        │
       GND
```

$$\text{Voltage at PB1} = 5.0\text{V} \times \frac{4700\,\Omega}{2200\,\Omega + 4700\,\Omega} = 3.41\text{V}$$

---

## 🚗 4. L298N Motor Driver Setup

### Jumper Configuration
Your red L298N module has three jumper caps installed from factory. **Remove all three**:
1. **5V Regulator Jumper (near +5V screw terminal):** **REMOVE.** External 5V logic power is supplied from the Blue Pill 5V pin.
2. **ENA Jumper:** **REMOVE.** Speed is controlled via PWM from STM32 pin `PA6`.
3. **ENB Jumper:** **REMOVE.** Speed is controlled via PWM from STM32 pin `PA7`.

### Motor Terminal Connections
* **OUT1 & OUT2 (Left Screw Terminals):** Connected in parallel to **Front Left Motor** and **Rear Left Motor**.
* **OUT3 & OUT4 (Right Screw Terminals):** Connected in parallel to **Front Right Motor** and **Rear Right Motor**.

---

## 💡 5. Visual Lighting Array

All LEDs have their own dedicated $220\,\Omega$ current-limiting resistors:

* **Front Left / Power:** `PB5` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Green LED 1 Anode $\rightarrow$ Cathode to GND
* **Front Right / Auxiliary:** `PB9` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Green LED 2 Anode $\rightarrow$ Cathode to GND
* **Bluetooth Status:** `PB6` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Blue LED Anode $\rightarrow$ Cathode to GND
* **Rear Left Brake Light (Dual Red):**
  * `PB7` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Red LED 1 (Outer Left) $\rightarrow$ Cathode to GND
  * `PB7` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Red LED 3 (Inner Left) $\rightarrow$ Cathode to GND
* **Rear Right Brake Light (Dual Red):**
  * `PB8` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Red LED 2 (Outer Right) $\rightarrow$ Cathode to GND
  * `PB8` $\rightarrow$ $220\,\Omega$ $\rightarrow$ Red LED 4 (Inner Right) $\rightarrow$ Cathode to GND
