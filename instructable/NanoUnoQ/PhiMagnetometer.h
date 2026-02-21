#pragma once
#include <Arduino.h>
#include <Arduino_BMI270_BMM150.h>

/*
 ===========================================================
    MODULE PhiMagnetometer - VERSION RAW (ACQUISITION PURE)
    Détection du champ magnétique terrestre (BMM150)
 ===========================================================
*/

class PhiMagnetometer {
public:
    PhiMagnetometer();

    // Initialisation (IMU.begin() doit déjà être appelé)
    bool begin();

    // Mise à jour des lectures (Appel à ~50 Hz)
    void update();

    // Metrics pour le Monitor et le flux binaire
    float magnitude() const { return _magnitude; }

    // Composantes du vecteur pour l'IA ou l'affichage
    void getComponents(float &x, float &y, float &z) const {
        x = _x; y = _y; z = _z;
    }

private:
    float _x, _y, _z;           // Composantes en µT
    float _magnitude;           // Magnitude totale ||B|| brute
};