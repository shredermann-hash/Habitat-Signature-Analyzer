#include "PhiIMU_raw.h"

/*
 ===========================================================
    PhiIMU RAW Implementation - ACQUISITION PURE
    Stockage des 3 axes (X, Y, Z) @ 90 Hz
 ===========================================================
*/

PhiIMU::PhiIMU()
: _index(0),
  _bufferReady(false),
  _nextSampleTime(0),
  _lastX(0), _lastY(0), _lastZ(0)
{}

bool PhiIMU::begin() {
    if (!IMU.begin()) {
        Serial.println("✗ PhiIMU: BMI270 init failed");
        return false;
    }
    
    _nextSampleTime = micros() + IMU_SAMPLE_PERIOD_US;
    
    Serial.println("✓ PhiIMU RAW (12 samples X,Y,Z @ 90 Hz)");
    return true;
}

void PhiIMU::update() {
    uint32_t now = micros();
    
    // Timing précis @ 90 Hz
    if ((int32_t)(now - _nextSampleTime) < 0)
        return;
    
    _nextSampleTime += IMU_SAMPLE_PERIOD_US;
    
    if (!IMU.accelerationAvailable())
        return;
    
    // Lecture brute de l'accélération
    IMU.readAcceleration(_lastX, _lastY, _lastZ);
    
    // Stockage des 3 axes en int16_t (g * 1000)
    // On n'improvise pas : pas de magnitude, juste les registres.
    _buffer[_index++] = (int16_t)(_lastX * 1000.0f);
    _buffer[_index++] = (int16_t)(_lastY * 1000.0f);
    _buffer[_index++] = (int16_t)(_lastZ * 1000.0f);
    
    // Buffer plein ?
    if (_index >= IMU_BUFFER_SIZE) {
        _index = 0;
        _bufferReady = true;
    }
}