/*
 * ============================================================================
 *  SMART VEHICLE — MINIMAL RELIABLE BLE LED TESTER
 * ============================================================================
 *  Board:      STM32F103C8T6 "Blue Pill"
 *  Framework:  Arduino (STM32duino)
 *
 *  HARDWARE WIRING:
 *  - BLE TXD ──→ STM32 PA10 (USART1 RX)
 *  - BLE RXD ──→ STM32 PA9  (USART1 TX)
 *  - PB5     ──→ 220Ω ──→ GREEN1 LED  ──→ GND
 *  - PB9     ──→ 220Ω ──→ GREEN2 LED  ──→ GND
 *  - PB6     ──→ 220Ω ──→ BLUE LED    ──→ GND
 *  - PB7     ──→ 220Ω ──→ RED_L LED   ──→ GND
 *  - PB8     ──→ 220Ω ──→ RED_R LED   ──→ GND
 *
 *  COMMAND PROTOCOL (Serial1, 9600 baud):
 *    '1' ── PB5 only                 (ACK:1)
 *    '2' ── PB9 only                 (ACK:2)
 *    '3' ── PB6 only                 (ACK:3)
 *    '4' ── PB7 only                 (ACK:4)
 *    '5' ── PB8 only                 (ACK:5)
 *    'A' ── All 5 LEDs ON            (ACK:A)
 *    'O' ── All 5 LEDs OFF           (ACK:O)
 *    'S' ── PB6 Blue ON, others OFF  (ACK:S)
 *    'F' ── PB5 + PB9 ON (Front)     (ACK:F)
 *    'B' ── PB7 + PB8 ON (Rear)      (ACK:B)
 *    'L' ── PB5 + PB7 ON (Left)      (ACK:L)
 *    'R' ── PB9 + PB8 ON (Right)     (ACK:R)
 * ============================================================================
 */

#include <Arduino.h>

// LED Pin definitions
#define PIN_GREEN1 PB5
#define PIN_GREEN2 PB9
#define PIN_BLUE   PB6
#define PIN_RED_L  PB7
#define PIN_RED_R  PB8

// Helper to set all 5 LEDs
void setLeds(bool g1, bool g2, bool b, bool rl, bool rr) {
    digitalWrite(PIN_GREEN1, g1 ? HIGH : LOW);
    digitalWrite(PIN_GREEN2, g2 ? HIGH : LOW);
    digitalWrite(PIN_BLUE,   b  ? HIGH : LOW);
    digitalWrite(PIN_RED_L,  rl ? HIGH : LOW);
    digitalWrite(PIN_RED_R,  rr ? HIGH : LOW);
}

// Power-on startup sweep to visually confirm all 5 LEDs and resistors work
void startupSweep() {
    const int pins[] = { PIN_GREEN1, PIN_GREEN2, PIN_BLUE, PIN_RED_L, PIN_RED_R };
    for (int i = 0; i < 5; i++) {
        digitalWrite(pins[i], HIGH);
        delay(100);
        digitalWrite(pins[i], LOW);
    }
    // Quick flash of all 5
    setLeds(true, true, true, true, true);
    delay(150);
    setLeds(false, false, false, false, false);
    delay(100);
}

// Process single-character command from BLE UART
void processCommand(char c) {
    // Ignore line endings and whitespace
    if (c == '\r' || c == '\n' || c == ' ') {
        return;
    }

    char cmd = toupper(c);

    switch (cmd) {
        case '1': // PB5 only
            setLeds(true, false, false, false, false);
            Serial1.println("ACK:1");
            break;

        case '2': // PB9 only
            setLeds(false, true, false, false, false);
            Serial1.println("ACK:2");
            break;

        case '3': // PB6 only
            setLeds(false, false, true, false, false);
            Serial1.println("ACK:3");
            break;

        case '4': // PB7 only
            setLeds(false, false, false, true, false);
            Serial1.println("ACK:4");
            break;

        case '5': // PB8 only
            setLeds(false, false, false, false, true);
            Serial1.println("ACK:5");
            break;

        case 'A': // All 5 LEDs ON
            setLeds(true, true, true, true, true);
            Serial1.println("ACK:A");
            break;

        case 'O': // All 5 LEDs OFF
            setLeds(false, false, false, false, false);
            Serial1.println("ACK:O");
            break;

        case 'S': // Stop / Standby: PB6 Blue ON
            setLeds(false, false, true, false, false);
            Serial1.println("ACK:S");
            break;

        case 'F': // Forward: PB5 + PB9 ON
            setLeds(true, true, false, false, false);
            Serial1.println("ACK:F");
            break;

        case 'B': // Backward: PB7 + PB8 ON
            setLeds(false, false, false, true, true);
            Serial1.println("ACK:B");
            break;

        case 'L': // Left: PB5 + PB7 ON
            setLeds(true, false, false, true, false);
            Serial1.println("ACK:L");
            break;

        case 'R': // Right: PB9 + PB8 ON
            setLeds(false, true, false, false, true);
            Serial1.println("ACK:R");
            break;

        default:
            Serial1.print("ERR:");
            Serial1.println(cmd);
            break;
    }
}

void setup() {
    // 1. Configure all LED pins as outputs
    pinMode(PIN_GREEN1, OUTPUT);
    pinMode(PIN_GREEN2, OUTPUT);
    pinMode(PIN_BLUE,   OUTPUT);
    pinMode(PIN_RED_L,  OUTPUT);
    pinMode(PIN_RED_R,  OUTPUT);

    // Initial state: all OFF
    setLeds(false, false, false, false, false);

    // 2. Visual self-test sweep
    startupSweep();

    // 3. Explicitly initialize hardware USART1 (PA10=RX, PA9=TX) at 9600 baud
    Serial1.begin(9600);

    // 4. Set initial state to Standby (PB6 Blue ON)
    setLeds(false, false, true, false, false);

    // 5. Send ready signal over BLE
    Serial1.println("OK:READY");
}

void loop() {
    // Receive commands directly from hardware USART1 (BLE module)
    while (Serial1.available()) {
        char c = (char)Serial1.read();
        processCommand(c);
    }
}
