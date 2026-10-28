/*
 * ============================================================================
 *  T18 — HARDWARE DIAGNOSTIC FIRMWARE FOR STM32 BLUE PILL
 * ============================================================================
 *  Vehicle: TT 1800R — Bluetooth 4WD Robot Car
 *  Based on proven-working dj.ino UART implementation (05-Sep):
 *  - Dual Serial1 + Serial at 9600 baud (no setRx/setTx overrides)
 *  - PA10/PA9 USART1 for BLE module communication
 *
 *  HARDWARE WIRING:
 *    BLE TXD  →  STM32 PA10 (USART1 RX)
 *    BLE RXD  →  STM32 PA9  (USART1 TX)
 *
 *  LEDs:
 *    PB9  →  220Ω → GREEN1 (Left)   → GND
 *    PB5  →  220Ω → GREEN2 (Right)  → GND
 *    PB6  →  220Ω → BLUE   (Center) → GND
 *    PB7  →  220Ω → RED_L  (Left)   → GND
 *    PB8  →  220Ω → RED_R  (Right)  → GND
 *
 *  Motors (L298N):
 *    PA0 → IN1   PA1 → IN2   (Left motors)
 *    PA2 → IN3   PA3 → IN4   (Right motors)
 *    PA6 → ENA   PA7 → ENB   (PWM speed)
 *
 *  Ultrasonic (HC-SR04):
 *    PB0 → TRIG
 *    PB1 → ECHO  (via 2.2k+4.7k voltage divider)
 *
 *  COMMAND PROTOCOL:
 *    LED:    1-5=toggle, A=all on, O=all off, S=standby, F/B/L/R=patterns
 *    MOTOR:  W=forward, X=reverse, <=left, >=right, !=stop, P0-P9=speed
 *    SENSOR: D=read distance
 *    STATUS: ?=full report
 * ============================================================================
 */

#include <Arduino.h>

// ── LED Pins ──
#define GREEN1 PB9  // Green Left  (Front-Left)
#define GREEN2 PB5  // Green Right (Front-Right)
#define BLUE   PB6  // Blue Center (Standby)
#define RED_L  PB7  // Red Left    (Rear-Left)
#define RED_R  PB8  // Red Right   (Rear-Right)

// ── Motor Pins (L298N) ──
#define MOTOR_IN1 PA0
#define MOTOR_IN2 PA1
#define MOTOR_IN3 PA2
#define MOTOR_IN4 PA3
#define MOTOR_ENA PA6
#define MOTOR_ENB PA7

// ── Ultrasonic Pins (HC-SR04) ──
#define US_TRIG PB0
#define US_ECHO PB1

// ── LED States ──
bool state_g1  = false;
bool state_g2  = false;
bool state_b   = true;   // Blue starts ON (standby indicator)
bool state_rl  = false;
bool state_rr  = false;

// ── Motor State ──
uint8_t motor_speed = 191;  // Default 75% of 255
char    motor_dir   = '!';  // Current direction (! = stopped)

// ══════════════════════════════════════════════════════════════════
//  UTILITY FUNCTIONS
// ══════════════════════════════════════════════════════════════════

void sendAck(const char* msg) {
  Serial1.println(msg);
  Serial.println(msg);
}

void sendAckF(const char* prefix, int value) {
  char buf[32];
  snprintf(buf, sizeof(buf), "%s%d", prefix, value);
  sendAck(buf);
}

// ── LED Control ──

void applyLeds() {
  digitalWrite(GREEN1, state_g1 ? HIGH : LOW);
  digitalWrite(GREEN2, state_g2 ? HIGH : LOW);
  digitalWrite(BLUE,   state_b  ? HIGH : LOW);
  digitalWrite(RED_L,  state_rl ? HIGH : LOW);
  digitalWrite(RED_R,  state_rr ? HIGH : LOW);
}

// ── Motor Control ──

void motorStop() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, LOW);
  analogWrite(MOTOR_ENA, 0);
  analogWrite(MOTOR_ENB, 0);
  motor_dir = '!';
}

void motorForward() {
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, HIGH);
  digitalWrite(MOTOR_IN4, LOW);
  analogWrite(MOTOR_ENA, motor_speed);
  analogWrite(MOTOR_ENB, motor_speed);
  motor_dir = 'W';
}

void motorReverse() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, HIGH);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, HIGH);
  analogWrite(MOTOR_ENA, motor_speed);
  analogWrite(MOTOR_ENB, motor_speed);
  motor_dir = 'X';
}

void motorLeft() {
  // Right side forward, left side stopped
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, HIGH);
  digitalWrite(MOTOR_IN4, LOW);
  analogWrite(MOTOR_ENA, 0);
  analogWrite(MOTOR_ENB, motor_speed);
  motor_dir = '<';
}

void motorRight() {
  // Left side forward, right side stopped
  digitalWrite(MOTOR_IN1, HIGH);
  digitalWrite(MOTOR_IN2, LOW);
  digitalWrite(MOTOR_IN3, LOW);
  digitalWrite(MOTOR_IN4, LOW);
  analogWrite(MOTOR_ENA, motor_speed);
  analogWrite(MOTOR_ENB, 0);
  motor_dir = '>';
}

// ── Ultrasonic Distance ──

long readDistanceCm() {
  // Send 10µs trigger pulse
  digitalWrite(US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(US_TRIG, LOW);

  // Read echo pulse duration (timeout 30ms = ~500cm max)
  long duration = pulseIn(US_ECHO, HIGH, 30000);

  if (duration == 0) return -1;  // No echo / out of range
  return duration / 58;          // Convert to cm
}

// ══════════════════════════════════════════════════════════════════
//  COMMAND HANDLER
// ══════════════════════════════════════════════════════════════════

void handleCommand(char c) {
  if (c == '\r' || c == '\n' || c == ' ') return;

  char cmd = c;  // Preserve case for < > ! P
  char upper = toupper(c);

  // ── LED COMMANDS (use uppercase) ──
  switch (upper) {
    case '1':
      state_g1 = !state_g1;
      digitalWrite(GREEN1, state_g1 ? HIGH : LOW);
      sendAck("RX:1");
      return;

    case '2':
      state_g2 = !state_g2;
      digitalWrite(GREEN2, state_g2 ? HIGH : LOW);
      sendAck("RX:2");
      return;

    case '3':
      state_b = !state_b;
      digitalWrite(BLUE, state_b ? HIGH : LOW);
      sendAck("RX:3");
      return;

    case '4':
      state_rl = !state_rl;
      digitalWrite(RED_L, state_rl ? HIGH : LOW);
      sendAck("RX:4");
      return;

    case '5':
      state_rr = !state_rr;
      digitalWrite(RED_R, state_rr ? HIGH : LOW);
      sendAck("RX:5");
      return;

    case 'A':  // All LEDs ON
      state_g1 = state_g2 = state_b = state_rl = state_rr = true;
      applyLeds();
      sendAck("RX:A");
      return;

    case 'O':  // All LEDs OFF
      state_g1 = state_g2 = state_b = state_rl = state_rr = false;
      applyLeds();
      sendAck("RX:O");
      return;

    case 'S':  // Standby — Blue ON, others OFF, motors STOP
      state_g1 = state_g2 = state_rl = state_rr = false;
      state_b = true;
      applyLeds();
      motorStop();
      sendAck("RX:S");
      return;

    case 'F':  // Forward indicator pattern
      state_g1 = state_g2 = true;
      state_b = state_rl = state_rr = false;
      applyLeds();
      sendAck("RX:F");
      return;

    case 'B':  // Backward indicator pattern
      state_g1 = state_g2 = false;
      state_b = false;
      state_rl = state_rr = true;
      applyLeds();
      sendAck("RX:B");
      return;

    case 'L':  // Left indicator pattern
      state_g1 = state_rl = true;
      state_g2 = state_rr = state_b = false;
      applyLeds();
      sendAck("RX:L");
      return;

    case 'R':  // Right indicator pattern
      state_g2 = state_rr = true;
      state_g1 = state_rl = state_b = false;
      applyLeds();
      sendAck("RX:R");
      return;
  }

  // ── MOTOR COMMANDS (use original char for < > !) ──
  switch (cmd) {
    case 'W': case 'w':  // Forward
      motorForward();
      sendAck("RX:W");
      return;

    case 'X': case 'x':  // Reverse
      motorReverse();
      sendAck("RX:X");
      return;

    case '<':  // Turn left
      motorLeft();
      sendAck("RX:<");
      return;

    case '>':  // Turn right
      motorRight();
      sendAck("RX:>");
      return;

    case '!':  // Motor STOP
      motorStop();
      sendAck("RX:!");
      return;
  }

  // ── SPEED COMMAND: P followed by digit 0-9 ──
  if (upper == 'P') {
    // Speed will be set by next byte — store flag
    // For simplicity, wait briefly for next char
    unsigned long t = millis();
    while (!Serial1.available() && !Serial.available()) {
      if (millis() - t > 200) {
        sendAck("RX:P?");  // Timeout, no digit received
        return;
      }
    }
    char digit = Serial1.available() ? Serial1.read() : Serial.read();
    if (digit >= '0' && digit <= '9') {
      // Map 0-9 to 0-255 (0=off, 1=28, ... 9=255)
      motor_speed = (digit == '0') ? 0 : map(digit - '0', 1, 9, 28, 255);
      // Re-apply speed to currently running motors
      if (motor_dir != '!') {
        analogWrite(MOTOR_ENA, motor_speed);
        analogWrite(MOTOR_ENB, motor_speed);
      }
      char ack[8];
      snprintf(ack, sizeof(ack), "RX:P%c", digit);
      sendAck(ack);
    } else {
      sendAck("RX:P?");
    }
    return;
  }

  // ── DISTANCE COMMAND ──
  if (upper == 'D') {
    long dist = readDistanceCm();
    if (dist < 0) {
      sendAck("DIST:ERR");
    } else {
      sendAckF("DIST:", dist);
    }
    return;
  }

  // ── STATUS REPORT ──
  if (cmd == '?') {
    // Format: ST:GGRBB,Mdir,Pspd,Ddist
    char status[48];
    snprintf(status, sizeof(status), "ST:%d%d%d%d%d,%c,%d",
      state_g1, state_g2, state_b, state_rl, state_rr,
      motor_dir, motor_speed);
    sendAck(status);
    return;
  }

  // ── UNKNOWN COMMAND ──
  Serial1.print("RX:");
  Serial1.println(cmd);
  Serial.print("RX:");
  Serial.println(cmd);
}

// ══════════════════════════════════════════════════════════════════
//  SETUP & LOOP
// ══════════════════════════════════════════════════════════════════

void setup() {
  // ── LED Pins ──
  pinMode(GREEN1, OUTPUT);
  pinMode(GREEN2, OUTPUT);
  pinMode(BLUE,   OUTPUT);
  pinMode(RED_L,  OUTPUT);
  pinMode(RED_R,  OUTPUT);

  // ── Motor Pins ──
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_IN3, OUTPUT);
  pinMode(MOTOR_IN4, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(MOTOR_ENB, OUTPUT);

  // ── Ultrasonic Pins ──
  pinMode(US_TRIG, OUTPUT);
  pinMode(US_ECHO, INPUT);

  // ── Initial State ──
  state_g1 = state_g2 = state_rl = state_rr = false;
  state_b = true;
  applyLeds();
  motorStop();

  // ── UART — EXACT proven-working initialization ──
  Serial1.begin(9600);
  Serial.begin(9600);

  sendAck("BOOT_OK");
}

void loop() {
  // Check Serial1 first (PA10/PA9 USART1 — BLE module)
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
