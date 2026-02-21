#pragma once
#include <Arduino.h>
#include <Arduino_HS300x.h>

/*
 ===========================================================
    MODULE PhiHumidity - VERSION RAW (ACQUISITION PURE)
    Température & Humidité Relative (HS3003)
 ===========================================================
*/

class PhiHumidity {
public:
    PhiHumidity();

    // Initialisation
    bool begin();

    // Mise à jour (Lecture brute à ~1 Hz)
    void update();

    // Metrics brutes pour le Monitor et le flux binaire
    float temperature() const { return _temperature; } // °C
    float humidity() const    { return _humidity; }    // % RH

private:
    float _temperature;
    float _humidity;
};