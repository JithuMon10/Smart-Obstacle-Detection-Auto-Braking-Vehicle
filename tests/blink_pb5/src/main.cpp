/*
 * ============================================================
 *  HARDWARE BRING-UP TEST — Green LED Blink on PB5
 * ============================================================
 *
 *  Board:    STM32F103C8T6 "Blue Pill" (or GD32F103C8T6)
 *  Purpose:  Verify that the toolchain, ST-Link, and one GPIO
 *            pin work before wiring anything else.
 *
 *  Wiring required:
 *    PB5 ──→ 220Ω resistor ──→ Green LED (long leg / anode)
 *    Green LED (short leg / cathode) ──→ GND
 *
 *  Expected behavior:
 *    Green LED turns ON for 500 ms, OFF for 500 ms (1 Hz blink)
 *    Onboard PC13 LED also blinks in sync (inverted — active LOW)
 *
 *  This file does NOT initialize motors, Bluetooth, HC-SR04,
 *  or any other peripheral. It is a standalone bring-up test.
 * ============================================================
 */

#define GREEN_LED_PIN   PB5    // External green LED via 220Ω
#define ONBOARD_LED_PIN PC13   // Blue Pill onboard LED (active LOW)

void setup() {
    // Configure PB5 as a push-pull digital output
    pinMode(GREEN_LED_PIN, OUTPUT);

    // Also blink the onboard LED so we get visual feedback
    // even if external wiring is wrong
    pinMode(ONBOARD_LED_PIN, OUTPUT);

    // Start with both LEDs OFF
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(ONBOARD_LED_PIN, HIGH);  // HIGH = OFF on PC13 (active LOW)
}

void loop() {
    // ── ON phase (500 ms) ──
    digitalWrite(GREEN_LED_PIN, HIGH);     // External green LED ON
    digitalWrite(ONBOARD_LED_PIN, LOW);    // Onboard LED ON (active LOW)
    delay(500);

    // ── OFF phase (500 ms) ──
    digitalWrite(GREEN_LED_PIN, LOW);      // External green LED OFF
    digitalWrite(ONBOARD_LED_PIN, HIGH);   // Onboard LED OFF (active LOW)
    delay(500);
}
