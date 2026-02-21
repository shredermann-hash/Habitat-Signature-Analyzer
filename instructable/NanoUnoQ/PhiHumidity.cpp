#include "PhiHumidity.h"

/*
 ===========================================================
    PhiHumidity Implementation - MODE RAW
    Suppression des calculs (Heat Index, Dew Point, LPF)
 ===========================================================
*/

PhiHumidity::PhiHumidity()
: _temperature(0),
  _humidity(0)
{}

bool PhiHumidity::begin() {
    // HS300x.begin() doit être appelé dans le setup principal
    Serial.println("✓ PhiHumidity RAW initialized (HS3003)");
    return true;
}

void PhiHumidity::update() {
    // Lecture directe des capteurs HS3003
    float t = HS300x.readTemperature();
    float h = HS300x.readHumidity();
    
    // On ne stocke que si les valeurs sont valides (pas de NaN)
    if (!isnan(t) && !isnan(h)) {
        _temperature = t;
        _humidity = h;
    }
}