#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ============================================================================
// PIN DEFINITIONS (STM32F103C8T6 Blue Pill)
// ============================================================================

// --- L298N Motor Driver ---
// Left Motor Group (Front Left + Rear Left in parallel)
#define PIN_IN1        PA0
#define PIN_IN2        PA1
#define PIN_ENA        PA6  // Hardware PWM (Timer 3 Channel 1)

// Right Motor Group (Front Right + Rear Right in parallel)
#define PIN_IN3        PA2
#define PIN_IN4        PA3
#define PIN_ENB        PA7  // Hardware PWM (Timer 3 Channel 2)

// --- HC-SR04 Ultrasonic Distance Sensor ---
#define PIN_TRIG       PB0  // 3.3V Output Trigger Pulse
#define PIN_ECHO       PB1  // 5V Echo via 2.2k/4.7k divider (3.41V max)

// --- HC-05 Bluetooth Module ---
// USART1 uses PA9 (STM32 TX -> HC-05 RX) and PA10 (STM32 RX -> HC-05 TX)
#define PIN_BT_KEY     PB12 // AT-Command / Key pin (Optional)
#define BT_SERIAL      Serial1
#define BT_BAUD        9600

// --- Visual Lighting & Indicator LEDs ---
// Front Indicators
#define PIN_LED_GREEN1 PB5  // Front Green LED 1 (Power / Status)
#define PIN_LED_GREEN2 PB9  // Front Green LED 2 (Cruising / Independent animation)

// Connectivity Indicator
#define PIN_LED_BLUE   PB6  // Blue LED (Bluetooth Connection Status)

// Rear Brake Lights (Dual pair on rear chassis)
#define PIN_LED_BRAKE_L PB7 // Rear Left Brake LEDs (Red 1 & Red 3 in parallel)
#define PIN_LED_BRAKE_R PB8 // Rear Right Brake LEDs (Red 2 & Red 4 in parallel)

// ============================================================================
// VEHICLE TUNING & SAFETY THRESHOLDS
// ============================================================================
#define EMERGENCY_STOP_CM   25   // Trigger auto-braking if obstacle closer than 25 cm
#define WARNING_DISTANCE_CM 45   // Slow down and alert if obstacle within 45 cm
#define MAX_DISTANCE_CM     300  // Maximum reliable range for HC-SR04

#define DEFAULT_SPEED       200  // Normal driving PWM (0 - 255)
#define SLOW_SPEED          130  // Speed during obstacle warning zone
#define TURN_SPEED          175  // Speed during turning maneuvers
#define MIN_SPEED           90   // Minimum PWM needed to overcome motor friction

#define BRAKE_ACTIVE_TIME   400  // Milliseconds to apply active reverse counter-pulse
#define BRAKE_LIGHT_HOLD_MS 800  // Milliseconds to keep brake lights on after stopping

#endif // CONFIG_H
