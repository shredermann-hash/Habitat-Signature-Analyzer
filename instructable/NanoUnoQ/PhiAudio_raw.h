#pragma once
#include <Arduino.h>
#include <PDM.h>

/*
 ===========================================================
    PhiAudio - VERSION RAW (NO FFT)
    Pure PDM acquisition for Phisualize V2
    
    Collecte 96 samples @ 16 kHz (6 ms window)
    Pas de traitement, envoi brut vers UNO Q
 ===========================================================
*/

#define AUDIO_BUFFER_SIZE 96
#define AUDIO_FS 16000.0f

class PhiAudio {
public:
    PhiAudio();
    
    bool begin();
    void update();
    
    // Accès aux samples bruts
    bool hasNewSamples() const { return _bufferReady; }
    const int16_t* getSamples() const { return _buffer; }
    size_t getSampleCount() const { return AUDIO_BUFFER_SIZE; }
    void consumeSamples() { _bufferReady = false; }
    
    // Diagnostics
    int16_t getLastPeak() const { return _lastPeak; }

private:
    static void _onPDMdata();
    
    static int16_t _buffer[AUDIO_BUFFER_SIZE];
    static volatile bool _bufferReady;
    
    int16_t _lastPeak;
};
