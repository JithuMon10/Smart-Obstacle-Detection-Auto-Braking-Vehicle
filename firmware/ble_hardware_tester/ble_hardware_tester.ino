/*
 * ============================================================================
 *  SMART VEHICLE — STAGE 1: HARDWARE COMMUNICATION & LED TESTER
 * ============================================================================
 *  Board:      STM32F103C8T6 "Blue Pill"
 *  Framework:  Arduino (STM32duino)
 *
 *  PURPOSE:
 *  Verifies end-to-end wireless telemetry: Windows PC (Bleak) ──→ BLE module
 *  ──→ USART1 (PA10/PA9) ──→ STM32 Blue Pill ──→ Physical LED Indicators.
 *
 *  SAFETY GUARANTEE:
 *  - No motor outputs are energized (IN1–IN4 / ENA / ENB remain untouched).
 *  - Existing hardware wiring is 100% preserved.
 *
 *  PIN ASSIGNMENTS:
 *  ┌────────────┬─────────────┬──────────────────────────────────────────────┐
 *  │ Pin        │ Component   │ Role / Function                              │
 *  ├────────────┼─────────────┼──────────────────────────────────────────────┤
 *  │ PA10       │ USART1 RX   │ Receives data from BLE TXD (3.3V logic)      │
 *  │ PA9        │ USART1 TX   │ Transmits data to BLE RXD (3.3V logic)       │
 *  │ PB5        │ GREEN1      │ Front Left Green LED (via 220Ω to GND)       │
 *  │ PB9        │ GREEN2      │ Front Right Green LED (via 220Ω to GND)      │
 *  │ PB7        │ RED_L       │ Rear Left Red LED (via 220Ω to GND)          │
 *  │ PB8        │ RED_R       │ Rear Right Red LED (via 220Ω to GND)         │
 *  │ PB6        │ BLUE        │ Center / Status Blue LED (via 220Ω to GND)   │
 *  └────────────┴─────────────┴──────────────────────────────────────────────┘
 *
 *  COMMAND PROTOCOL (9600 baud, 8-N-1):
 *  ┌─────────┬──────────────┬────────────────────────────────────────────────┐
 *  │ Command │ Meaning      │ LED Response                                   │
 *  ├─────────┼──────────────┼────────────────────────────────────────────────┤
 *  │ 'F'     │ FORWARD      │ Front Greens (PB5, PB9) ON; Reds & Blue OFF    │
 *  │ 'B'     │ BACKWARD     │ Rear Reds (PB7, PB8) ON; Greens & Blue OFF     │
 *  │ 'L'     │ LEFT TURN    │ Left side (PB5 Green + PB7 Red) ON; Others OFF │
 *  │ 'R'     │ RIGHT TURN   │ Right side (PB9 Green + PB8 Red) ON; Others OFF│
 *  │ 'S'     │ STOP / IDLE  │ All Greens & Reds OFF; Center Blue (PB6) ON    │
 *  └─────────┴──────────────┴────────────────────────────────────────────────┘
 * ============================================================================
 */

#include <Arduino.h>

// --- PIN DEFINITIONS ---
#define PIN_GREEN1   PB5   // Front Left Green LED
#define PIN_GREEN2   PB9   // Front Right Green LED
#define PIN_RED_L    PB7   // Rear Left Red LED
#define PIN_RED_R    PB8   // Rear Right Red LED
#define PIN_BLUE     PB6   // Status / Standby Blue LED

// --- SERIAL CONFIGURATION ---
// In STM32duino, Serial1 maps to hardware USART1 (PA9=TX, PA10=RX).
// Serial maps to USB CDC (if USB enabled) or USART1.
#if defined(HAVE_HWSERIAL1) || defined(Serial1)
  #define BLE_SERIAL Serial1
#else
  #define BLE_SERIAL Serial
#endif

// Current active state
char currentCommand = 'S';

// Function prototypes
void setLeds(bool g1, bool g2, bool rl, bool rr, bool blue);
void processCommand(char cmd);
void echoFeedback(const char* code, const char* desc);
void startupLedSweep();
void printBanner();

void setup() {
    // 1. Initialize LED GPIOs as push-pull outputs
    pinMode(PIN_GREEN1, OUTPUT);
    pinMode(PIN_GREEN2, OUTPUT);
    pinMode(PIN_RED_L,  OUTPUT);
    pinMode(PIN_RED_R,  OUTPUT);
    pinMode(PIN_BLUE,   OUTPUT);

    // Turn all LEDs off immediately
    setLeds(false, false, false, false, false);

    // 2. Initialize Bluetooth UART at 9600 baud
    BLE_SERIAL.begin(9600);

    // Also initialize USB Serial if available for dual-monitoring
    #if defined(BLE_SERIAL) && defined(Serial) && (BLE_SERIAL != Serial)
    Serial.begin(9600);
    #endif

    // 3. Run a quick power-on visual sweep to verify every LED and resistor
    startupLedSweep();

    // 4. Default to STOP state (Blue LED ON)
    processCommand('S');

    // 5. Announce readiness over both serial channels
    printBanner();
}

void loop() {
    // Check for incoming commands over Bluetooth UART (PA10)
    if (BLE_SERIAL.available() > 0) {
        char c = (char)BLE_SERIAL.read();
        processCommand(c);
    }

    // Also check USB Serial if user is connected via USB cable
    #if defined(BLE_SERIAL) && defined(Serial) && (BLE_SERIAL != Serial)
    if (Serial.available() > 0) {
        char c = (char)Serial.read();
        processCommand(c);
    }
    #endif
}

/**
 * Updates all 5 LED outputs simultaneously
 */
void setLeds(bool g1, bool g2, bool rl, bool rr, bool blue) {
    digitalWrite(PIN_GREEN1, g1   ? HIGH : LOW);
    digitalWrite(PIN_GREEN2, g2   ? HIGH : LOW);
    digitalWrite(PIN_RED_L,  rl   ? HIGH : LOW);
    digitalWrite(PIN_RED_R,  rr   ? HIGH : LOW);
    digitalWrite(PIN_BLUE,   blue ? HIGH : LOW);
}

/**
 * Dispatches action and visual response based on received character
 */
void processCommand(char cmd) {
    // Normalize case and ignore whitespace
    char upper = toupper(cmd);
    if (upper == '\r' || upper == '\n' || upper == '\0') {
        return;
    }

    // Map WASD aliases directly to FBLR for flexibility
    if (upper == 'W') upper = 'F';
    else if (upper == 'A') upper = 'L';
    else if (upper == 'D') upper = 'R';
    else if (upper == ' ' || upper == 'X') upper = 'S';

    switch (upper) {
        case 'F':  // FORWARD: Headlights ON
            currentCommand = 'F';
            setLeds(true, true, false, false, false);
            echoFeedback("F", "FORWARD [Front Greens ON]");
            break;

        case 'B':  // BACKWARD: Taillights ON
            currentCommand = 'B';
            setLeds(false, false, true, true, false);
            echoFeedback("B", "BACKWARD [Rear Reds ON]");
            break;

        case 'L':  // LEFT: Left side indicators ON
            currentCommand = 'L';
            setLeds(true, false, true, false, false);
            echoFeedback("L", "LEFT TURN [Left Green+Red ON]");
            break;

        case 'R':  // RIGHT: Right side indicators ON
            currentCommand = 'R';
            setLeds(false, true, false, true, false);
            echoFeedback("R", "RIGHT TURN [Right Green+Red ON]");
            break;

        case 'S':  // STOP: Standby Blue ON, all others OFF
            currentCommand = 'S';
            setLeds(false, false, false, false, true);
            echoFeedback("S", "STOP / IDLE [Center Blue ON]");
            break;

        default:
            // Unknown command - brief blink of Blue LED to signal unrecognized input
            digitalWrite(PIN_BLUE, HIGH);
            delay(40);
            digitalWrite(PIN_BLUE, (currentCommand == 'S') ? HIGH : LOW);
            
            BLE_SERIAL.print("[STM32] Unknown command: '");
            BLE_SERIAL.print(cmd);
            BLE_SERIAL.println("' (Supported: F, B, L, R, S)");
            #if defined(BLE_SERIAL) && defined(Serial) && (BLE_SERIAL != Serial)
            Serial.print("[STM32] Unknown command: '");
            Serial.print(cmd);
            Serial.println("'");
            #endif
            break;
    }
}

/**
 * Echoes formatted response back over Bluetooth and USB
 */
void echoFeedback(const char* code, const char* desc) {
    BLE_SERIAL.print("[STM32] ACK: ");
    BLE_SERIAL.print(code);
    BLE_SERIAL.print(" -> ");
    BLE_SERIAL.println(desc);

    #if defined(BLE_SERIAL) && defined(Serial) && (BLE_SERIAL != Serial)
    Serial.print("[STM32] ACK: ");
    Serial.print(code);
    Serial.print(" -> ");
    Serial.println(desc);
    #endif
}

/**
 * Visual sweep across all 5 LEDs at power-on
 */
void startupLedSweep() {
    const int delayMs = 120;
    const int pins[] = { PIN_GREEN1, PIN_GREEN2, PIN_BLUE, PIN_RED_R, PIN_RED_L };

    // Turn each LED ON sequentially
    for (int i = 0; i < 5; i++) {
        digitalWrite(pins[i], HIGH);
        delay(delayMs);
        digitalWrite(pins[i], LOW);
    }

    // Flash all LEDs together once
    setLeds(true, true, true, true, true);
    delay(200);
    setLeds(false, false, false, false, false);
    delay(100);
}

/**
 * Prints startup diagnostics banner
 */
void printBanner() {
    const char banner[] =
        "\r\n===================================================\r\n"
        "  STM32 BLE HARDWARE TESTER READY\r\n"
        "  Baud: 9600 | PA10 = RX, PA9 = TX\r\n"
        "  LEDs: PB5(G1), PB9(G2), PB7(RL), PB8(RR), PB6(BL)\r\n"
        "  Commands: F (Fwd), B (Back), L (Left), R (Right), S (Stop)\r\n"
        "===================================================\r\n";

    BLE_SERIAL.print(banner);
    #if defined(BLE_SERIAL) && defined(Serial) && (BLE_SERIAL != Serial)
    Serial.print(banner);
    #endif
}
