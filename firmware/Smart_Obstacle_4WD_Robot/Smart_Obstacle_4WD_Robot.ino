/**
 * ============================================================================
 * Smart Obstacle Detection & Automatic Braking 4WD Robotic Vehicle
 * ============================================================================
 * Target MCU : STM32F103C8T6 (Blue Pill) / GD32F103C8T6
 * Framework  : Arduino / STM32duino / PlatformIO
 * Flasher    : ST-Link V2 (SWD)
 *
 * Hardware Peripherals:
 *  - 4WD Motors via L298N Dual H-Bridge (IN1-IN4: PA0-PA3, ENA/ENB: PA6/PA7)
 *  - HC-SR04 Ultrasonic Distance Sensor (TRIG: PB0, ECHO: PB1 via 2.2k/4.7k divider)
 *  - HC-05 Bluetooth Module (USART1: PA9 TX, PA10 RX)
 *  - Visual Lighting:
 *      * Front Indicator 1 (Green 1): PB5
 *      * Front Indicator 2 (Green 2): PB9
 *      * Bluetooth Indicator (Blue): PB6
 *      * Rear Left Brake LEDs (Red 1 & 3): PB7
 *      * Rear Right Brake LEDs (Red 2 & 4): PB8
 * ============================================================================
 */

#include "config.h"
#include "motors.h"
#include "sensor.h"
#include "lighting.h"
#include "bluetooth.h"

static unsigned long lastTelemetryTime = 0;
static char activeRequestedDirection = 'S';

void setup() {
    // 1. Initialize all subsystems
    lightingInit();
    motorsInit();
    sensorInit();
    bluetoothInit();

    // 2. Ready indication: flash front lights twice
    lightingSetFront(true, true);
    delay(150);
    lightingSetFront(false, false);
    delay(150);
    lightingSetFront(true, true);

    #if defined(USBCON)
    Serial.println(F("=== STM32 4WD SMART BRAKING VEHICLE INITIALIZED ==="));
    #endif
}

void loop() {
    // 1. Update ultrasonic distance sensor (non-blocking)
    sensorUpdate();
    float currentDistance = getDistanceCm();
    bool critical = isObstacleCritical();
    bool warning  = isObstacleWarning();

    // 2. Critical Safety Override: Automatic Emergency Braking
    // If the vehicle is driving forward and detects an obstacle within 25cm
    if (getMotionState() == MOTION_FORWARD && critical) {
        motorsBrake();
        activeRequestedDirection = 'S';
        bluetoothSendTelemetry(currentDistance, "EMERGENCY_BRAKE_ACTIVATED");
    }

    // 3. Process Bluetooth Remote Control Commands
    VehicleCommand cmd;
    if (bluetoothReadCommand(cmd)) {
        if (cmd.action != ' ') {
            activeRequestedDirection = cmd.action;
        }

        switch (cmd.action) {
            case 'F': // Forward request
                if (critical) {
                    // Obstacle in front: Intercept and refuse forward motion!
                    motorsCoast();
                    activeRequestedDirection = 'S';
                    bluetoothSendTelemetry(currentDistance, "FORWARD_BLOCKED_BY_OBSTACLE");
                } else if (warning) {
                    // Slow approach zone
                    motorsForward(SLOW_SPEED);
                } else {
                    motorsForward(cmd.speed);
                }
                break;

            case 'B': // Backward request: always allowed (away from front obstacle)
                motorsBackward(cmd.speed);
                break;

            case 'L': // Turn Left
                motorsTurnLeft(cmd.speed);
                break;

            case 'R': // Turn Right
                motorsTurnRight(cmd.speed);
                break;

            case 'S': // Stop
                motorsCoast();
                break;

            default:
                break;
        }
    }

    // 4. Proactive safety adjustment if user is holding forward and entering warning zone
    if (activeRequestedDirection == 'F' && getMotionState() == MOTION_FORWARD) {
        if (warning) {
            motorsForward(SLOW_SPEED);
        }
    }

    // 5. Update Lighting & Indicator Subsystem
    lightingUpdate(getMotionState(), warning, critical, isBluetoothConnected());

    // 6. Periodic Telemetry broadcast (every 500ms)
    unsigned long now = millis();
    if (now - lastTelemetryTime >= 500) {
        lastTelemetryTime = now;
        const char* stateStr = "STOPPED";
        switch (getMotionState()) {
            case MOTION_FORWARD:         stateStr = "FORWARD"; break;
            case MOTION_BACKWARD:        stateStr = "REVERSING"; break;
            case MOTION_TURN_LEFT:       stateStr = "TURNING_LEFT"; break;
            case MOTION_TURN_RIGHT:      stateStr = "TURNING_RIGHT"; break;
            case MOTION_EMERGENCY_BRAKE: stateStr = "AUTO_BRAKED"; break;
            default:                     stateStr = "IDLE"; break;
        }
        bluetoothSendTelemetry(currentDistance, stateStr);
    }
}
