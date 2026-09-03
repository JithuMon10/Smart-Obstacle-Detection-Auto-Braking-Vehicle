#include "sensor.h"

static float currentDistance = 100.0f;
static unsigned long lastPingTime = 0;
const unsigned long PING_INTERVAL_MS = 40; // 25 Hz update rate

void sensorInit() {
    pinMode(PIN_TRIG, OUTPUT);
    pinMode(PIN_ECHO, INPUT);
    digitalWrite(PIN_TRIG, LOW);
}

static float measureRawDistance() {
    // 10 microsecond trigger pulse
    digitalWrite(PIN_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG, LOW);

    // 20ms timeout = ~340 cm max distance
    unsigned long duration = pulseIn(PIN_ECHO, HIGH, 20000);

    if (duration == 0) {
        return MAX_DISTANCE_CM; // Out of range or no echo
    }

    // Speed of sound = 343 m/s = 0.0343 cm/us -> distance = (duration * 0.0343) / 2
    float distance = (float)duration * 0.01715f;

    if (distance > MAX_DISTANCE_CM || distance < 2.0f) {
        return MAX_DISTANCE_CM;
    }

    return distance;
}

void sensorUpdate() {
    unsigned long now = millis();
    if (now - lastPingTime >= PING_INTERVAL_MS) {
        lastPingTime = now;
        float raw = measureRawDistance();

        // Exponential smoothing filter (alpha = 0.65 for fast response + noise rejection)
        if (raw < MAX_DISTANCE_CM) {
            currentDistance = (0.65f * raw) + (0.35f * currentDistance);
        } else {
            currentDistance = (0.2f * raw) + (0.8f * currentDistance);
        }
    }
}

float getDistanceCm() {
    return currentDistance;
}

bool isObstacleCritical() {
    return (currentDistance > 0.0f && currentDistance <= EMERGENCY_STOP_CM);
}

bool isObstacleWarning() {
    return (currentDistance > EMERGENCY_STOP_CM && currentDistance <= WARNING_DISTANCE_CM);
}
