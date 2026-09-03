#include "lighting.h"

static unsigned long lastAnimTime = 0;
static bool blinkToggle = false;
static bool animStep = false;

void lightingInit() {
    pinMode(PIN_LED_GREEN1, OUTPUT);
    pinMode(PIN_LED_GREEN2, OUTPUT);
    pinMode(PIN_LED_BLUE, OUTPUT);
    pinMode(PIN_LED_BRAKE_L, OUTPUT);
    pinMode(PIN_LED_BRAKE_R, OUTPUT);

    // Initial test sequence (all on briefly, then off)
    digitalWrite(PIN_LED_GREEN1, HIGH);
    digitalWrite(PIN_LED_GREEN2, HIGH);
    digitalWrite(PIN_LED_BLUE, HIGH);
    digitalWrite(PIN_LED_BRAKE_L, HIGH);
    digitalWrite(PIN_LED_BRAKE_R, HIGH);
    delay(250);
    digitalWrite(PIN_LED_GREEN1, LOW);
    digitalWrite(PIN_LED_GREEN2, LOW);
    digitalWrite(PIN_LED_BLUE, LOW);
    digitalWrite(PIN_LED_BRAKE_L, LOW);
    digitalWrite(PIN_LED_BRAKE_R, LOW);
}

void lightingSetBrakes(bool active) {
    digitalWrite(PIN_LED_BRAKE_L, active ? HIGH : LOW);
    digitalWrite(PIN_LED_BRAKE_R, active ? HIGH : LOW);
}

void lightingSetFront(bool g1, bool g2) {
    digitalWrite(PIN_LED_GREEN1, g1 ? HIGH : LOW);
    digitalWrite(PIN_LED_GREEN2, g2 ? HIGH : LOW);
}

void lightingSetBluetooth(bool connected) {
    digitalWrite(PIN_LED_BLUE, connected ? HIGH : LOW);
}

void lightingUpdate(VehicleMotionState state, bool warning, bool critical, bool btConnected) {
    unsigned long now = millis();

    // 150ms animation tick
    if (now - lastAnimTime >= 150) {
        lastAnimTime = now;
        blinkToggle = !blinkToggle;
        animStep = !animStep;
    }

    // --- 1. Blue Bluetooth Indicator ---
    if (btConnected) {
        digitalWrite(PIN_LED_BLUE, HIGH); // Solid ON when paired & active
    } else {
        digitalWrite(PIN_LED_BLUE, blinkToggle ? HIGH : LOW); // Heartbeat pulse while waiting
    }

    // --- 2. Front Green Indicators (PB5 & PB9) ---
    if (critical) {
        // Fast emergency strobe
        digitalWrite(PIN_LED_GREEN1, blinkToggle ? HIGH : LOW);
        digitalWrite(PIN_LED_GREEN2, blinkToggle ? HIGH : LOW);
    } else if (warning) {
        // Alternating warning flash
        digitalWrite(PIN_LED_GREEN1, animStep ? HIGH : LOW);
        digitalWrite(PIN_LED_GREEN2, animStep ? LOW : HIGH);
    } else if (state == MOTION_FORWARD) {
        // Cruising headlights ON
        digitalWrite(PIN_LED_GREEN1, HIGH);
        digitalWrite(PIN_LED_GREEN2, HIGH);
    } else if (state == MOTION_STOPPED) {
        // Gentle breathing / standby
        digitalWrite(PIN_LED_GREEN1, HIGH);
        digitalWrite(PIN_LED_GREEN2, LOW);
    } else {
        // Turning / other motion
        digitalWrite(PIN_LED_GREEN1, HIGH);
        digitalWrite(PIN_LED_GREEN2, HIGH);
    }

    // --- 3. Rear Brake Lights (PB7 = Left Pair, PB8 = Right Pair) ---
    if (critical || state == MOTION_EMERGENCY_BRAKE) {
        // Emergency Stop: Solid ON on all 4 rear brake lights
        digitalWrite(PIN_LED_BRAKE_L, HIGH);
        digitalWrite(PIN_LED_BRAKE_R, HIGH);
    } else if (state == MOTION_STOPPED) {
        // Vehicle at rest: Solid brake lights
        digitalWrite(PIN_LED_BRAKE_L, HIGH);
        digitalWrite(PIN_LED_BRAKE_R, HIGH);
    } else if (state == MOTION_BACKWARD) {
        // Reverse indicator: Both rear banks blink
        digitalWrite(PIN_LED_BRAKE_L, blinkToggle ? HIGH : LOW);
        digitalWrite(PIN_LED_BRAKE_R, blinkToggle ? HIGH : LOW);
    } else if (state == MOTION_TURN_LEFT) {
        // Left turn: Left brake bank blinks, Right is OFF
        digitalWrite(PIN_LED_BRAKE_L, blinkToggle ? HIGH : LOW);
        digitalWrite(PIN_LED_BRAKE_R, LOW);
    } else if (state == MOTION_TURN_RIGHT) {
        // Right turn: Right brake bank blinks, Left is OFF
        digitalWrite(PIN_LED_BRAKE_L, LOW);
        digitalWrite(PIN_LED_BRAKE_R, blinkToggle ? HIGH : LOW);
    } else {
        // Driving Forward: Brake lights OFF
        digitalWrite(PIN_LED_BRAKE_L, LOW);
        digitalWrite(PIN_LED_BRAKE_R, LOW);
    }
}
