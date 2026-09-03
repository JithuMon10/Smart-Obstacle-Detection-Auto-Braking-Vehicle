#ifndef LIGHTING_H
#define LIGHTING_H

#include <Arduino.h>
#include "config.h"
#include "motors.h"

void lightingInit();
void lightingUpdate(VehicleMotionState state, bool warning, bool critical, bool btConnected);
void lightingSetBrakes(bool active);
void lightingSetFront(bool g1, bool g2);
void lightingSetBluetooth(bool connected);

#endif // LIGHTING_H
