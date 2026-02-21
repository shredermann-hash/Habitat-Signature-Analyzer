#pragma once
#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>

/*
 ===========================================================
    PhiIMU - VERSION RAW (ACQUISITION PURE)
    Collecte 12 samples (X,Y,Z) @ 90 Hz
    Pas de calcul de magnitude, envoi des 3 axes bruts
 ===========================================================
*/

// 12 échantillons * 3 axes = 36 valeurs
#define IMU_BUFFER_SIZE 36
#define IMU_SAMPLE_RATE_HZ 90.0f
#define IMU_SAMPLE_PERIOD_US (1000000 / IMU_SAMPLE_RATE_HZ)

class PhiIMU {
public:
    PhiIMU();
    
    bool begin();
    void update();
    
    // Accès aux samples bruts (X,Y,Z alternés)
    bool hasNewSamples() const { return _bufferReady; }
    const int16_t* getSamples() const { return _buffer; }
    size_t getSampleCount() const { return IMU_BUFFER_SIZE; }
    void consumeSamples() { _bufferReady = false; }
    
    // Pour ton monitor : accès aux dernières valeurs lues
    float lastX() const { return _lastX; }
    float lastY() const { return _lastY; }
    float lastZ() const { return _lastZ; }

private:
    int16_t _buffer[IMU_BUFFER_SIZE]; 
    size_t _index;
    bool _bufferReady;
    
    uint32_t _nextSampleTime;
    
    float _lastX, _lastY, _lastZ;
};