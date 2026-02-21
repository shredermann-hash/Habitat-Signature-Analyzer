#pragma once
#include <Arduino.h>
#include <Arduino_LPS22HB.h>

/*
 ===========================================================
    MODULE PhiBarometer - VERSION RAW (ACQUISITION PURE)
    Lecture directe de la pression atmosphérique LPS22HB.
    Correction ×10 pour conversion kPa -> hPa intégrée.
 ===========================================================
*/

class PhiBarometer {
public:
    PhiBarometer();

    // Initialisation
    bool begin();

    // Mise à jour (Lecture brute sans filtrage)
    void update();

    // Metric brute pour le Monitor et le flux binaire
    float pressure() const { return _pressure; }

private:
    float _pressure; // Pression en hPa
};