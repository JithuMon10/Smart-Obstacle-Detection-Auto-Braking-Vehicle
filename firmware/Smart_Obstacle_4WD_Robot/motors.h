#ifndef MOTORS_H
#define MOTORS_H

#include <Arduino.h>
#include "config.h"

enum VehicleMotionState {
    MOTION_STOPPED,
    MOTION_FORWARD,
    MOTION_BACKWARD,
    MOTION_TURN_LEFT,
    MOTION_TURN_RIGHT,
    MOTION_EMERGENCY_BRAKE
};

void motorsInit();
void motorsForward(uint8_t speed = DEFAULT_SPEED);
void motorsBackward(uint8_t speed = DEFAULT_SPEED);
void motorsTurnLeft(uint8_t speed = TURN_SPEED);
void motorsTurnRight(uint8_t speed = TURN_SPEED);
void motorsCoast();
void motorsBrake();

VehicleMotionState getMotionState();

#endif // MOTORS_H
