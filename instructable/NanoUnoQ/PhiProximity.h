#pragma once
#include <Arduino.h>
#include <Arduino_APDS9960.h>

/*
 ===========================================================
    MODULE PhiProximity - VERSION RAW (ACQUISITION PURE)
    Détection de proximité IR brute (APDS9960)
 ===========================================================
*/

class PhiProximity {
public:
    PhiProximity();

    // Initialisation
    bool begin();

    // Mise à jour (Lecture brute 0-255)
    void update();

    // Valeur brute pour le Monitor et le flux binaire
    int proximity() const { return _proximity; }           

private:
    int _proximity; // Valeur brute 0 (loin) à 255 (très proche)
};