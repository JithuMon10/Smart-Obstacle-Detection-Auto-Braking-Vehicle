#include "bluetooth.h"

static unsigned long lastPacketTime = 0;
static uint8_t configuredSpeed = DEFAULT_SPEED;
const unsigned long BT_TIMEOUT_MS = 3000;

void bluetoothInit() {
    pinMode(PIN_BT_KEY, OUTPUT);
    digitalWrite(PIN_BT_KEY, LOW); // Normal transparent data mode

    BT_SERIAL.begin(BT_BAUD);

    // Also begin primary USB Serial for debugging if connected to PC
    #if defined(USBCON)
    Serial.begin(115200);
    #endif
}

bool isBluetoothConnected() {
    return (lastPacketTime > 0 && (millis() - lastPacketTime < BT_TIMEOUT_MS));
}

bool bluetoothReadCommand(VehicleCommand &cmd) {
    if (!BT_SERIAL.available()) {
        return false;
    }

    char c = BT_SERIAL.read();

    // Ignore newline / carriage return
    if (c == '\r' || c == '\n') {
        return false;
    }

    lastPacketTime = millis();
    cmd.newCommand = true;

    // Speed setting via numeric keys '0' through '9'
    if (c >= '0' && c <= '9') {
        configuredSpeed = map(c - '0', 0, 9, MIN_SPEED, 255);
        cmd.action = ' '; // Speed change only, no motion change
        cmd.speed = configuredSpeed;
        return true;
    }

    if (c == 'q' || c == 'Q') {
        configuredSpeed = 255;
        cmd.action = ' ';
        cmd.speed = configuredSpeed;
        return true;
    }

    // Motion commands (Supports WASD and Standard Bluetooth RC Car App keys)
    switch (c) {
        case 'F':
        case 'f':
        case 'W':
        case 'w':
            cmd.action = 'F';
            break;

        case 'B':
        case 'b':
        case 'S':
        case 's':
            cmd.action = 'B';
            break;

        case 'L':
        case 'l':
        case 'A':
        case 'a':
            cmd.action = 'L';
            break;

        case 'R':
        case 'r':
        case 'D':
        case 'd':
            cmd.action = 'R';
            break;

        case 'X':
        case 'x':
        case ' ':
        case '0':
            cmd.action = 'S';
            break;

        default:
            cmd.action = 'S';
            break;
    }

    cmd.speed = configuredSpeed;
    return true;
}

void bluetoothSendTelemetry(float distanceCm, const char* status) {
    BT_SERIAL.print(F("DIST:"));
    BT_SERIAL.print((int)distanceCm);
    BT_SERIAL.print(F("cm | STAT:"));
    BT_SERIAL.println(status);
}
