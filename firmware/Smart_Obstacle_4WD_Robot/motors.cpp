#include "motors.h"

static VehicleMotionState currentState = MOTION_STOPPED;

void motorsInit() {
    pinMode(PIN_IN1, OUTPUT);
    pinMode(PIN_IN2, OUTPUT);
    pinMode(PIN_IN3, OUTPUT);
    pinMode(PIN_IN4, OUTPUT);
    pinMode(PIN_ENA, OUTPUT);
    pinMode(PIN_ENB, OUTPUT);

    motorsCoast();
}

void motorsForward(uint8_t speed) {
    // Left Motors Forward
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
    analogWrite(PIN_ENA, speed);

    // Right Motors Forward
    digitalWrite(PIN_IN3, HIGH);
    digitalWrite(PIN_IN4, LOW);
    analogWrite(PIN_ENB, speed);

    currentState = MOTION_FORWARD;
}

void motorsBackward(uint8_t speed) {
    // Left Motors Reverse
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, HIGH);
    analogWrite(PIN_ENA, speed);

    // Right Motors Reverse
    digitalWrite(PIN_IN3, LOW);
    digitalWrite(PIN_IN4, HIGH);
    analogWrite(PIN_ENB, speed);

    currentState = MOTION_BACKWARD;
}

void motorsTurnLeft(uint8_t speed) {
    // Left Motors Reverse / Pivot
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, HIGH);
    analogWrite(PIN_ENA, speed);

    // Right Motors Forward
    digitalWrite(PIN_IN3, HIGH);
    digitalWrite(PIN_IN4, LOW);
    analogWrite(PIN_ENB, speed);

    currentState = MOTION_TURN_LEFT;
}

void motorsTurnRight(uint8_t speed) {
    // Left Motors Forward
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, LOW);
    analogWrite(PIN_ENA, speed);

    // Right Motors Reverse / Pivot
    digitalWrite(PIN_IN3, LOW);
    digitalWrite(PIN_IN4, HIGH);
    analogWrite(PIN_ENB, speed);

    currentState = MOTION_TURN_RIGHT;
}

void motorsCoast() {
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
    digitalWrite(PIN_IN3, LOW);
    digitalWrite(PIN_IN4, LOW);
    analogWrite(PIN_ENA, 0);
    analogWrite(PIN_ENB, 0);

    currentState = MOTION_STOPPED;
}

void motorsBrake() {
    // If we were moving forward, briefly apply reverse torque to halt mechanical inertia
    if (currentState == MOTION_FORWARD) {
        digitalWrite(PIN_IN1, LOW);
        digitalWrite(PIN_IN2, HIGH);
        digitalWrite(PIN_IN3, LOW);
        digitalWrite(PIN_IN4, HIGH);
        analogWrite(PIN_ENA, 220);
        analogWrite(PIN_ENB, 220);
        delay(70); // Brief active counter-pulse
    }

    // Full electronic brake: both inputs HIGH shorts motor terminals through L298N
    digitalWrite(PIN_IN1, HIGH);
    digitalWrite(PIN_IN2, HIGH);
    digitalWrite(PIN_IN3, HIGH);
    digitalWrite(PIN_IN4, HIGH);
    analogWrite(PIN_ENA, 255);
    analogWrite(PIN_ENB, 255);
    delay(50);

    // Transition to idle coast
    digitalWrite(PIN_IN1, LOW);
    digitalWrite(PIN_IN2, LOW);
    digitalWrite(PIN_IN3, LOW);
    digitalWrite(PIN_IN4, LOW);
    analogWrite(PIN_ENA, 0);
    analogWrite(PIN_ENB, 0);

    currentState = MOTION_EMERGENCY_BRAKE;
}

VehicleMotionState getMotionState() {
    return currentState;
}
