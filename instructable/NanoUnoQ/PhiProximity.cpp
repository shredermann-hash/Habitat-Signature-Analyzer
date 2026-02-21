#include "PhiProximity.h"

/*
 ===========================================================
    PhiProximity Implementation - MODE RAW
    Suppression des filtres et de la normalisation.
 ===========================================================
*/

PhiProximity::PhiProximity()
: _proximity(0)
{}

bool PhiProximity::begin() {
    // APDS.begin() doit être appelé dans le setup principal
    Serial.println("✓ PhiProximity RAW initialized (APDS9960)");
    return true;
}

void PhiProximity::update() {
    if (!APDS.proximityAvailable())
        return;

    // Lecture directe du registre sans filtrage
    _proximity = APDS.readProximity();
}