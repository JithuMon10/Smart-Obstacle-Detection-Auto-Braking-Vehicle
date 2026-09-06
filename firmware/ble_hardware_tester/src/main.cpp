/*
 * ============================================================================
 *  PROVEN WORKING UART & LED DIAGNOSTIC FIRMWARE FOR STM32 BLUE PILL
 * ============================================================================
 *  Based directly on the known-working dj.ino implementation from 05-Sep:
 *  - Dual initialization of Serial1 AND Serial at 9600 baud.
 *  - Default STM32duino pin bindings (no setRx/setTx overrides).
 *  - Dual-port reception and dual-port ACK so that regardless of Arduino IDE
 *    menu settings (Generic Serial vs CDC), PA10/PA9 communication works.
 *
 *  HARDWARE WIRING:
 *    BLE TXD  ──→  STM32 PA10 (USART1 RX)
 *    BLE RXD  ──→  STM32 PA9  (USART1 TX)
 *    PB5      ──→  220Ω ──→ GREEN1 LED ──→ GND
 *    PB9      ──→  220Ω ──→ GREEN2 LED ──→ GND
 *    PB6      ──→  220Ω ──→ BLUE LED   ──→ GND
 *    PB7      ──→  220Ω ──→ RED_L LED  ──→ GND
 *    PB8      ──→  220Ω ──→ RED_R LED  ──→ GND
 * ============================================================================
 */

#include <Arduino.h>

#define GREEN1 PB5
#define GREEN2 PB9
#define BLUE   PB6
#define RED_L  PB7
#define RED_R  PB8

// Current states
bool state_g1  = false;
bool state_g2  = false;
bool state_b   = true;  // Blue starts ON
bool state_rl  = false;
bool state_rr  = false;

void sendAck(const char* msg) {
  Serial1.println(msg);
  Serial.println(msg);
}

void applyLeds() {
  digitalWrite(GREEN1, state_g1 ? HIGH : LOW);
  digitalWrite(GREEN2, state_g2 ? HIGH : LOW);
  digitalWrite(BLUE,   state_b  ? HIGH : LOW);
  digitalWrite(RED_L,  state_rl ? HIGH : LOW);
  digitalWrite(RED_R,  state_rr ? HIGH : LOW);
}

void handleCommand(char c) {
  if (c == '\r' || c == '\n' || c == ' ') return;

  char cmd = toupper(c);

  switch (cmd) {
    case '1': // PB5 (Green 1)
      state_g1 = !state_g1;
      digitalWrite(GREEN1, state_g1 ? HIGH : LOW);
      sendAck("RX:1");
      break;

    case '2': // PB9 (Green 2)
      state_g2 = !state_g2;
      digitalWrite(GREEN2, state_g2 ? HIGH : LOW);
      sendAck("RX:2");
      break;

    case '3': // PB6 (Blue)
      state_b = !state_b;
      digitalWrite(BLUE, state_b ? HIGH : LOW);
      sendAck("RX:3");
      break;

    case '4': // PB7 (Red Left)
      state_rl = !state_rl;
      digitalWrite(RED_L, state_rl ? HIGH : LOW);
      sendAck("RX:4");
      break;

    case '5': // PB8 (Red Right)
      state_rr = !state_rr;
      digitalWrite(RED_R, state_rr ? HIGH : LOW);
      sendAck("RX:5");
      break;

    case 'A': // All LEDs ON
      state_g1 = state_g2 = state_b = state_rl = state_rr = true;
      applyLeds();
      sendAck("RX:A");
      break;

    case 'O': // All LEDs OFF
      state_g1 = state_g2 = state_b = state_rl = state_rr = false;
      applyLeds();
      sendAck("RX:O");
      break;

    case 'S': // Standby (PB6 Blue ON)
      state_g1 = state_g2 = state_rl = state_rr = false;
      state_b = true;
      applyLeds();
      sendAck("RX:S");
      break;

    default:
      Serial1.print("RX:");
      Serial1.println(cmd);
      Serial.print("RX:");
      Serial.println(cmd);
      break;
  }
}

void setup() {
  // Configure LED pins
  pinMode(GREEN1, OUTPUT);
  pinMode(GREEN2, OUTPUT);
  pinMode(BLUE,   OUTPUT);
  pinMode(RED_L,  OUTPUT);
  pinMode(RED_R,  OUTPUT);

  // Initial state: Blue ON, others OFF
  state_g1 = state_g2 = state_rl = state_rr = false;
  state_b = true;
  applyLeds();

  // EXACT known-working initialization from dj.ino
  Serial1.begin(9600);
  Serial.begin(9600);

  sendAck("BOOT_OK");
}

void loop() {
  // Check Serial1 first (PA10/PA9 USART1)
  if (Serial1.available()) {
    char c = Serial1.read();
    handleCommand(c);
  }
  // Also check Serial (if core mapped generic Serial to PA10/PA9)
  else if (Serial.available()) {
    char c = Serial.read();
    handleCommand(c);
  }
}
