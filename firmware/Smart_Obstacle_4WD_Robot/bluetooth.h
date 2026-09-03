#ifndef BLUETOOTH_H
#define BLUETOOTH_H

#include <Arduino.h>
#include "config.h"

struct VehicleCommand {
    char action;       // 'F', 'B', 'L', 'R', 'S'
    uint8_t speed;     // PWM 0-255
    bool newCommand;
};

void bluetoothInit();
bool bluetoothReadCommand(VehicleCommand &cmd);
bool isBluetoothConnected();
void bluetoothSendTelemetry(float distanceCm, const char* status);

#endif // BLUETOOTH_H
