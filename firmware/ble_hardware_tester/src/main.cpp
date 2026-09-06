/*
 * ============================================================================
 *  MINIMAL UART & LED DIAGNOSTIC FIRMWARE FOR STM32 BLUE PILL
 * ============================================================================
 *  Hardware Wiring:
 *    BLE TXD  ──→  STM32 PA10 (USART1 RX)
 *    BLE RXD  ──→  STM32 PA9  (USART1 TX)
 *    PB5      ──→  220Ω ──→ GREEN1 LED ──→ GND
 *    PB9      ──→  220Ω ──→ GREEN2 LED ──→ GND
 *    PB6      ──→  220Ω ──→ BLUE LED   ──→ GND
 *    PB7      ──→  220Ω ──→ RED_L LED  ──→ GND
 *    PB8      ──→  220Ω ──→ RED_R LED  ──→ GND
 *
 *  DIAGNOSTIC BEHAVIOR:
 *  - On boot: PB6 blinks once (300ms ON, 200ms OFF), then stays ON.
 *  - Sends "BOOT_OK\r\n" over Serial1 at 9600 baud.
 *  - Every byte received on Serial1 immediately toggles its LED and sends an ACK:
 *      '1' ──→ Toggles PB5 (Green 1)   ──→ replies "RX:1"
 *      '2' ──→ Toggles PB9 (Green 2)   ──→ replies "RX:2"
 *      '3' ──→ Toggles PB6 (Blue)      ──→ replies "RX:3"
 *      '4' ──→ Toggles PB7 (Red Left)  ──→ replies "RX:4"
 *      '5' ──→ Toggles PB8 (Red Right) ──→ replies "RX:5"
 *      'A' ──→ Turns ALL LEDs ON       ──→ replies "RX:A"
 *      'O' ──→ Turns ALL LEDs OFF      ──→ replies "RX:O"
 *      Any other byte ──→ replies "RX:<byte>"
 * ============================================================================
 */

#include <Arduino.h>

// LED Pin definitions
#define PIN_GREEN1 PB5
#define PIN_GREEN2 PB9
#define PIN_BLUE   PB6
#define PIN_RED_L  PB7
#define PIN_RED_R  PB8

// Current LED states
bool state_g1 = false;
bool state_g2 = false;
bool state_blue = true; // Starts ON after boot blink
bool state_rl = false;
bool state_rr = false;

void updateAllLeds() {
    digitalWrite(PIN_GREEN1, state_g1   ? HIGH : LOW);
    digitalWrite(PIN_GREEN2, state_g2   ? HIGH : LOW);
    digitalWrite(PIN_BLUE,   state_blue ? HIGH : LOW);
    digitalWrite(PIN_RED_L,  state_rl   ? HIGH : LOW);
    digitalWrite(PIN_RED_R,  state_rr   ? HIGH : LOW);
}

void processByte(char c) {
    // Ignore CR, LF, Space
    if (c == '\r' || c == '\n' || c == ' ') {
        return;
    }

    char cmd = toupper(c);

    switch (cmd) {
        case '1':
            state_g1 = !state_g1;
            digitalWrite(PIN_GREEN1, state_g1 ? HIGH : LOW);
            Serial1.println("RX:1");
            break;

        case '2':
            state_g2 = !state_g2;
            digitalWrite(PIN_GREEN2, state_g2 ? HIGH : LOW);
            Serial1.println("RX:2");
            break;

        case '3':
            state_blue = !state_blue;
            digitalWrite(PIN_BLUE, state_blue ? HIGH : LOW);
            Serial1.println("RX:3");
            break;

        case '4':
            state_rl = !state_rl;
            digitalWrite(PIN_RED_L, state_rl ? HIGH : LOW);
            Serial1.println("RX:4");
            break;

        case '5':
            state_rr = !state_rr;
            digitalWrite(PIN_RED_R, state_rr ? HIGH : LOW);
            Serial1.println("RX:5");
            break;

        case 'A':
            state_g1 = state_g2 = state_blue = state_rl = state_rr = true;
            updateAllLeds();
            Serial1.println("RX:A");
            break;

        case 'O':
            state_g1 = state_g2 = state_blue = state_rl = state_rr = false;
            updateAllLeds();
            Serial1.println("RX:O");
            break;

        case 'S':
            state_g1 = state_g2 = state_rl = state_rr = false;
            state_blue = true;
            updateAllLeds();
            Serial1.println("RX:S");
            break;

        default:
            Serial1.print("RX:");
            Serial1.println(cmd);
            break;
    }
}

void setup() {
    // 1. Configure all 5 LED pins as push-pull outputs
    pinMode(PIN_GREEN1, OUTPUT);
    pinMode(PIN_GREEN2, OUTPUT);
    pinMode(PIN_BLUE,   OUTPUT);
    pinMode(PIN_RED_L,  OUTPUT);
    pinMode(PIN_RED_R,  OUTPUT);

    // Initial state: all OFF
    state_g1 = state_g2 = state_blue = state_rl = state_rr = false;
    updateAllLeds();

    // 2. Boot indication: Blink PB6 Blue once, then leave it ON
    digitalWrite(PIN_BLUE, HIGH);
    delay(300);
    digitalWrite(PIN_BLUE, LOW);
    delay(200);
    state_blue = true;
    digitalWrite(PIN_BLUE, HIGH);

    // 3. Explicitly attach USART1 pins to PA10 (RX) and PA9 (TX)
    // In the STM32duino Blue Pill variant, Serial1 pins default to NC (not connected)
    // unless setRx() and setTx() are called before begin().
#if defined(ARDUINO_ARCH_STM32)
    Serial1.setRx(PA10);
    Serial1.setTx(PA9);
#endif

    // 4. Start Hardware USART1 at 9600 baud
    Serial1.begin(9600);

    // 5. Announce readiness over BLE
    Serial1.println("BOOT_OK");
}

void loop() {
    // Read directly from hardware USART1 (PA10)
    while (Serial1.available() > 0) {
        char c = (char)Serial1.read();
        processByte(c);
    }
}
