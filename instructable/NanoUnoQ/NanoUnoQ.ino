// CORRECTIONS MAJEURES APPLIQUÉES :
// 1. IMU réduit à 3 floats (au lieu de 18 redondants)
// 2. Timestamp ajouté (uint32_t timestamp_us)
// 3. Struct optimisée : 174 → 118 bytes

#include <Arduino_APDS9960.h>
#include <Wire.h>
#include "PhiAudio_raw.h"
#include "PhiIMU_raw.h"
#include "PhiMagnetometer.h"
#include "PhiBarometer.h"
#include "PhiHumidity.h"
#include "PhiProximity.h"
#include "arm_math.h"

PhiAudio audio;
PhiIMU imu;
PhiMagnetometer mag;
PhiBarometer baro;
PhiHumidity humidity;
PhiProximity proximity;

// ---------------- FFT audio avec OVERLAP 50% ----------------
#define AUDIO_FFT_SIZE      128
#define AUDIO_OVERLAP_STEP   64

arm_rfft_fast_instance_f32 audio_fft;
float32_t audio_fft_input[AUDIO_FFT_SIZE];
float32_t audio_fft_output[AUDIO_FFT_SIZE];
float32_t audio_magnitudes[AUDIO_FFT_SIZE / 2];
float32_t hann_window[AUDIO_FFT_SIZE];

static int16_t audio_buffer_circ[AUDIO_FFT_SIZE];
static size_t  audio_buf_index = 0;
static bool    audio_buffer_filled = false;

// ---------- STRUCT CORRIGÉE ----------
struct __attribute__((packed)) SensorFeatures {
    uint8_t  header[2];          // 0xAA 0xBB
    uint16_t packet_id;          // Compteur paquets
    uint32_t timestamp_us;       // ← NOUVEAU : micros() pour sync temporelle

    // Audio features
    float    audio_bands[16];    // 64 bytes
    float    audio_rms;          // 4 bytes
    float    audio_zcr;          // 4 bytes

    // IMU corrigé : seulement dernier échantillon
    float    imu_data[3];        // ← CORRIGÉ : 3 au lieu de 18 (12 bytes)

    // Environnement
    float    env_data[6];        // 24 bytes
    uint8_t  prox;
    uint8_t  _padding;
};
// Taille totale : 2 + 2 + 4 + 72 + 12 + 24 + 2 = 118 bytes (économie 56 bytes)

SensorFeatures feat;

unsigned long lastStatsTime = 0;
uint16_t packetCount = 0;

// Bandes mel-scale
const int mel_bins[17] = {
    0, 1, 2, 3, 4, 5, 7, 9, 12, 15, 19, 24, 30, 37, 45, 54, 64
};

// ---------------- Helpers audio (inchangés) ----------------

void add_audio_samples(const int16_t* new_samples, size_t count) {
    for (size_t i = 0; i < count; i++) {
        audio_buffer_circ[audio_buf_index] = new_samples[i];
        audio_buf_index = (audio_buf_index + 1) % AUDIO_FFT_SIZE;
    }
    if (!audio_buffer_filled && audio_buf_index == 0) {
        audio_buffer_filled = true;
    }
}

void prepare_fft_input_from_circ() {
    int read_idx = audio_buf_index;
    for (int i = 0; i < AUDIO_FFT_SIZE; i++) {
        audio_fft_input[i] = (audio_buffer_circ[read_idx] / 32768.0f) * hann_window[i];
        read_idx = (read_idx + 1) % AUDIO_FFT_SIZE;
    }
}

void extract_audio_features(float bands[16], float* rms, float* zcr) {
    audio_magnitudes[0] = fabsf(audio_fft_output[0]);
    for (int i = 1; i < AUDIO_FFT_SIZE / 2; i++) {
        float re = audio_fft_output[i * 2];
        float im = audio_fft_output[i * 2 + 1];
        audio_magnitudes[i] = sqrtf(re * re + im * im);
    }

    for (int b = 0; b < 16; b++) {
        float sum = 0;
        int count = mel_bins[b + 1] - mel_bins[b];
        for (int i = mel_bins[b]; i < mel_bins[b + 1]; i++) {
            sum += audio_magnitudes[i];
        }
        bands[b] = sum / count;
    }

    float sum_sq;
    arm_power_f32(audio_fft_input, AUDIO_FFT_SIZE, &sum_sq);
    *rms = sqrtf(sum_sq / AUDIO_FFT_SIZE);

    int z = 0;
    for (int i = 1; i < AUDIO_FFT_SIZE; i++) {
        if ((audio_fft_input[i - 1] >= 0 && audio_fft_input[i] < 0) ||
            (audio_fft_input[i - 1] < 0 && audio_fft_input[i] >= 0)) {
            z++;
        }
    }
    *zcr = z / (float)AUDIO_FFT_SIZE;
}

// -------- FONCTION CORRIGÉE --------
void fill_imu_and_env_data(SensorFeatures& f) {
    // IMU : seulement le dernier échantillon (corrigé !)
    f.imu_data[0] = imu.lastX();
    f.imu_data[1] = imu.lastY();
    f.imu_data[2] = imu.lastZ();

    // Magnétomètre
    float mx, my, mz;
    mag.getComponents(mx, my, mz);
    f.env_data[0] = mx;
    f.env_data[1] = my;
    f.env_data[2] = mz;

    // Baromètre
    float p = baro.pressure();
    if (p > 100.0 && p < 1200.0) {
        f.env_data[3] = p;
    }
    
    // Température & Humidité
    f.env_data[4] = humidity.temperature();
    f.env_data[5] = humidity.humidity();

    // Proximité
    f.prox = (uint8_t)proximity.proximity();
}

// ---------------- SETUP / LOOP ----------------

void setup() {
    Serial.begin(115200);
    Serial1.begin(921600);
    Wire.begin();

    if (!APDS.begin()) {
        Serial.println("✗ APDS9960 init failed");
    } else {
        Serial.println("✓ APDS9960 OK");
    }

    BARO.begin();
    HS300x.begin();
    delay(2000);

    audio.begin();
    imu.begin();
    mag.begin();
    baro.begin();
    humidity.begin();
    proximity.begin();

    feat.header[0] = 0xAA;
    feat.header[1] = 0xBB;

    arm_rfft_fast_init_f32(&audio_fft, AUDIO_FFT_SIZE);

    for (int i = 0; i < AUDIO_FFT_SIZE; i++) {
        hann_window[i] = 0.5f * (1.0f - arm_cos_f32(2.0f * PI * i / AUDIO_FFT_SIZE));
    }

    Serial.println("================================");
    Serial.println("   HSA - NANO SENSE   ");
    Serial.print("   sizeof(SensorFeatures) = ");
    Serial.println(sizeof(feat));
    Serial.println("================================\n");
}

void loop() {
    audio.update();
    imu.update();
    mag.update();
    baro.update();
    humidity.update();
    proximity.update();

    if (audio.hasNewSamples()) {
        const int16_t* samples = audio.getSamples();

        add_audio_samples(samples, 96);

        if (!audio_buffer_filled) {
            audio.consumeSamples();
            return;
        }

        // FFT 1
        prepare_fft_input_from_circ();
        arm_rfft_fast_f32(&audio_fft, audio_fft_input, audio_fft_output, 0);
        float bands1[16], rms1, zcr1;
        extract_audio_features(bands1, &rms1, &zcr1);

        // OVERLAP
        audio_buf_index = (audio_buf_index + AUDIO_FFT_SIZE - AUDIO_OVERLAP_STEP) % AUDIO_FFT_SIZE;

        // FFT 2
        prepare_fft_input_from_circ();
        arm_rfft_fast_f32(&audio_fft, audio_fft_input, audio_fft_output, 0);
        float bands2[16], rms2, zcr2;
        extract_audio_features(bands2, &rms2, &zcr2);

        // MOYENNER
        for (int i = 0; i < 16; i++) {
            feat.audio_bands[i] = (bands1[i] + bands2[i]) * 0.5f;
        }
        feat.audio_rms = (rms1 + rms2) * 0.5f;
        feat.audio_zcr = (zcr1 + zcr2) * 0.5f;

        fill_imu_and_env_data(feat);

        // ══════ AJOUT TIMESTAMP ══════
        feat.timestamp_us = micros();
        feat.packet_id = packetCount++;

        // ══════ ENVOI ══════
        Serial1.write((uint8_t*)&feat, sizeof(feat));

        audio_buf_index = (audio_buf_index + AUDIO_OVERLAP_STEP) % AUDIO_FFT_SIZE;
        audio.consumeSamples();
    }

    if (millis() - lastStatsTime > 2000) {
        lastStatsTime = millis();
        Serial.println("\n--- NANO DIAGNOSTIC ---");
        Serial.print("📦 Paquets envoyés: "); Serial.println(packetCount);
        Serial.print("📏 Taille paquet: "); Serial.print(sizeof(feat)); Serial.println(" bytes");
        Serial.print("🎯 IMU X/Y/Z: ");
        Serial.print(imu.lastX(), 3); Serial.print(" / ");
        Serial.print(imu.lastY(), 3); Serial.print(" / ");
        Serial.println(imu.lastZ(), 3);
        Serial.print("🌡️ Temp: "); Serial.print(humidity.temperature(), 1); Serial.println("°C");
        Serial.print("💧 Hum: "); Serial.print(humidity.humidity(), 0); Serial.println("%");
        Serial.print("☁️ Baro: "); Serial.print(feat.env_data[3], 1); Serial.println(" hPa");
        Serial.print("🧲 Mag: "); Serial.print(mag.magnitude(), 1); Serial.println(" µT");
        Serial.print("📊 Audio RMS: "); Serial.println(feat.audio_rms, 4);
        Serial.print("📍 Prox: "); Serial.println(feat.prox);
        Serial.println("------------------------");
    }
}