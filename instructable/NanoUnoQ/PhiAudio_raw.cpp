#include "PhiAudio_raw.h"

/*
 ===========================================================
    PhiAudio RAW Implementation
    Pure PDM acquisition - NO processing
 ===========================================================
*/

int16_t PhiAudio::_buffer[AUDIO_BUFFER_SIZE];
volatile bool PhiAudio::_bufferReady = false;

PhiAudio::PhiAudio()
: _lastPeak(0)
{}

void PhiAudio::_onPDMdata() {
    int bytes = PDM.available();
    if (bytes >= AUDIO_BUFFER_SIZE * 2) {
        PDM.read(_buffer, AUDIO_BUFFER_SIZE * 2);
        _bufferReady = true;
    }
}

bool PhiAudio::begin() {
    PDM.setBufferSize(AUDIO_BUFFER_SIZE * 2);
    PDM.onReceive(_onPDMdata);
    
    if (!PDM.begin(1, (int)AUDIO_FS)) {
        Serial.println("✗ PhiAudio: PDM init failed");
        return false;
    }
    
    Serial.println("✓ PhiAudio RAW (96 samples @ 16 kHz)");
    return true;
}

void PhiAudio::update() {
    if (!_bufferReady)
        return;
    
    // Calculate peak for diagnostics
    _lastPeak = 0;
    for (int i = 0; i < AUDIO_BUFFER_SIZE; i++) {
        int16_t abs_val = abs(_buffer[i]);
        if (abs_val > _lastPeak)
            _lastPeak = abs_val;
    }
}
