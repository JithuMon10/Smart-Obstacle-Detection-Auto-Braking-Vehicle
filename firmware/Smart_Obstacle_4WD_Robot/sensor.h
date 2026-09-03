#ifndef SENSOR_H
#define SENSOR_H

#include <Arduino.h>
#include "config.h"

void sensorInit();
void sensorUpdate();
float getDistanceCm();
bool isObstacleCritical();
bool isObstacleWarning();

#endif // SENSOR_H
