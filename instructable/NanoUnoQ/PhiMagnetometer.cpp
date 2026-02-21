#include "PhiMagnetometer.h"

/*
 ===========================================================
    PhiMagnetometer Implementation - MODE RAW
    Suppression des filtres et des calculs de dérive.
 ===========================================================
*/

PhiMagnetometer::PhiMagnetometer()
: _x(0), _y(0), _z(0),
  _magnitude(0)
{}

bool PhiMagnetometer::begin() {
    // Le BMM150 est initialisé automatiquement avec le BMI270
    Serial.println("✓ PhiMagnetometer RAW initialized (BMM150)");
    return true;
}

void PhiMagnetometer::update() {
    if (!IMU.magneticFieldAvailable())
        return;

    // Lecture brute des composantes
    IMU.readMagneticField(_x, _y, _z);

    // Magnitude totale brute : sqrt(x² + y² + z²)
    // On garde ce calcul pour ton Serial Monitor
    _magnitude = sqrtf(_x*_x + _y*_y + _z*_z);
}