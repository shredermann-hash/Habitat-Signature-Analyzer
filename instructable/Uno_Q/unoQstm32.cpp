#include <Arduino.h>
#include "Arduino_LED_Matrix.h"

ArduinoLEDMatrix matrix;

// Struct capteurs (inchangée)
struct __attribute__((packed)) SensorFeatures {
    uint8_t  header[2];
    uint16_t packet_id;
    uint32_t timestamp_us;
    float    audio_bands[16];
    float    audio_rms;
    float    audio_zcr;
    float    imu_data[3];
    float    env_data[6];
    uint8_t  prox;
    uint8_t  _padding;
};

void draw_spectrum(uint8_t bands[13]) {
    uint32_t frame[4] = {0, 0, 0, 0};
    
    // 13 colonnes × 8 lignes = 104 pixels
    // Matrice stockée en 4×32 bits
    
    for (int col = 0; col < 13; col++) {
        uint8_t height = bands[col];
        if (height > 8) height = 8;
        
        // Allumer pixels de bas en haut
        for (int row = 0; row < height; row++) {
            // Ligne 0 = haut, ligne 7 = bas
            int pixel_row = 7 - row;
            
            // Calcul position dans frame[4]
            int bit_pos = pixel_row * 13 + col;
            int word_idx = bit_pos / 32;
            int bit_idx = 31 - (bit_pos % 32);
            
            if (word_idx < 4) {
                frame[word_idx] |= (1UL << bit_idx);
            }
        }
    }
    
    matrix.loadFrame(frame);
}

void setup() {
    Serial.begin(921600);   // Nano -> STM32
    Serial1.begin(921600);  // STM32 <-> Linux
    
    matrix.begin();
    
    // Animation démarrage
    uint32_t boot[] = {0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF};
    matrix.loadFrame(boot);
    delay(200);
    uint32_t clear[] = {0, 0, 0, 0};
    matrix.loadFrame(clear);
}

void loop() {
    // Passthrough capteurs Nano -> Linux
    while (Serial.available()) {
        uint8_t b = Serial.read();
        Serial1.write(b);
    }
    
    // Commandes spectrum Linux -> STM32
    static uint8_t spectrum_buffer[16];
    static uint8_t spectrum_index = 0;
    
    while (Serial1.available()) {
        uint8_t b = Serial1.read();
        
        // Détecter header spectrum (0xDD)
        if (b == 0xDD && spectrum_index == 0) {
            spectrum_buffer[0] = b;
            spectrum_index = 1;
        }
        else if (spectrum_index > 0 && spectrum_index < 15) {
            spectrum_buffer[spectrum_index++] = b;
            
            // Paquet complet : 0xDD + 13 bandes + checksum = 15 bytes
            if (spectrum_index == 15) {
                // Vérifier checksum
                uint8_t checksum = 0;
                for (int i = 0; i < 14; i++) {
                    checksum ^= spectrum_buffer[i];
                }
                
                if (checksum == spectrum_buffer[14]) {
                    // Valide ! Dessiner spectrum
                    draw_spectrum(&spectrum_buffer[1]);
                }
                
                spectrum_index = 0;
            }
        }
        else {
            spectrum_index = 0;  // Reset si corruption
        }
    }
}