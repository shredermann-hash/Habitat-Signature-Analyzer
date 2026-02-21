#include "PhiBarometer.h"

/*
 ===========================================================
    PhiBarometer Implementation - MODE RAW
    Suppression des filtres et de la calibration.
 ===========================================================
*/

PhiBarometer::PhiBarometer()
: _pressure(0)
{}

bool PhiBarometer::begin() {
    // Note: BARO.begin() est géré dans le setup principal.
    Serial.println("✓ PhiBarometer RAW initialized (LPS22HB)");
    return true;
}

void PhiBarometer::update() {
    // Lecture directe du registre
    // La librairie retourne des kPa, on multiplie par 10 pour avoir des hPa.
    float p = BARO.readPressure() * 10.0f;

    if (p > 0) { 
        _pressure = p;
    }
}