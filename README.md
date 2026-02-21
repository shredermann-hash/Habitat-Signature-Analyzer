# Habitat-Signature-Analyzer
Multi-Sensor Edge AI System Running Entirely on Arduino Hardware


Classifies environmental behavioral states in real time using 7 physical sensors, a distributed 3-MCU pipeline, and a RandomForest model trained on-device.

## Overview

The system detects four habitat classes — **calme**, **presence**, **activite**, **ambiance** — at 10 Hz with 97.2% accuracy, using no cloud infrastructure and no dedicated AI accelerator.

The core insight is that each behavioral state produces a distinct multi-sensor signature: audio spectrum + vibration + magnetic field perturbations + proximity + environmental baselines, fused into a 118-byte packet and classified in under 100 ms on the UNO Q SoC.

## Hardware

| Arduino Nano 33 BLE Sense | Sensor acquisition + FFT + packet assembly |
| Arduino UNO Q (Qualcomm QRB2210) | Linux SoC — ML inference + InfluxDB + Grafana |
| STM32 (on UNO Q) | UART passthrough bridge |

The Nano 33 BLE Sense integrates all 7 sensors used:

- PDM microphone (MP34DT06JTR) — 16 kHz, mel-scale FFT
- IMU (BMI270) — 90 Hz, 3-axis accelerometer
- Magnetometer (BMM150) — 50 Hz, electromagnetic field
- IR proximity (APDS9960) — 10 Hz, calme/presence discrimination
- Temperature + Humidity (HS3003) — 0.5 Hz
- Barometer (LPS22HB) — 0.5 Hz, detects pressure events (e.g. window opening)

## Packet Structure

The Nano sends a 118-byte packed struct at 10 Hz over UART at 921600 baud:

```
header[2]        0xAA 0xBB — frame sync
packet_id        uint16    — loss detection
timestamp_us     uint32    — micros()
audio_bands[16]  float×16  — 64 B, mel-scale B0–B15
audio_rms        float     — 4 B
audio_zcr        float     — 4 B
imu_data[3]      float×3   — 12 B, aX aY aZ last sample
env_data[6]      float×6   — 24 B, Bx By Bz + pressure + temp + RH
prox             uint8     — 1 B
_padding         uint8     — 1 B
TOTAL                        118 B  @ 10 Hz = 9.2 kB/s
```

## Pipeline

```
Nano 33 BLE Sense
  → UART 921600 baud → STM32 passthrough → /dev/ttyHS1
    → capture.py (shared memory, lock-free ring buffer)
      → ml_pipeline.py (RandomForest, 118 features, rolling vote N=5)
        → InfluxDB (hsa_realtime bucket, 10 Hz)
          → Grafana (localhost:3000, 1s poll)
```

End-to-end latency: 4–5 seconds.

## ML Model

- Algorithm: RandomForest (sklearn, 200 estimators)
- Training: 655 samples, 12 sessions, GroupKFold cross-validation (anti-leakage)
- Accuracy: 97.2% on held-out sessions
- Features: 118 raw values from the struct (audio bands, RMS, ZCR, IMU, mag, env, proximity)
- Smoothing: majority vote over 5 consecutive predictions

## Repository Structure

```
NanoUnoQ/          Arduino sketch (Nano 33 BLE Sense firmware)
    NanoUnoQ.ino
    PhiAudio_raw.cpp/h
    PhiIMU_raw.cpp/h
    PhiMagnetometer.cpp/h
    PhiBarometer.cpp/h
    PhiHumidity.cpp/h
    PhiProximity.cpp/h

Uno_Q/             Python scripts and shell launchers (UNO Q Linux)
    capture_daemon.py      UART capture → shared memory
    ml_process_influx.py   Shared memory → InfluxDB
    ml_collect_habitat.py  Training data collection
    ml_train_habitat.py    Model training
    ml_predict_habitat.py  Real-time inference + LED matrix
    start_phisualize.sh    Launch all processes
    stop_phisualize.sh     Clean stop + shared memory cleanup
    status.sh              System health check
    watchdog.sh            Auto-restart on process failure

Schemas/           Technical diagrams
```

## Branches

| Branch | Content |
|--------|---------|
| `instructable`   | Original script names matching the Instructables tutorial |
| `main`           | Renamed HSA scripts (hsa_capture.py, hsa_process.py, etc.) |

## Requirements

Runs on the UNO Q over SSH. Python 3.13, aarch64 Debian Trixie.

```bash
sudo apt update && sudo apt install python3-pip python3-numpy
pip3 install influxdb-client scikit-learn pandas joblib --break-system-packages
```

InfluxDB and Grafana are installed as systemd services. See the Instructables tutorial for the full setup procedure including the Grafana .deb installation workaround specific to the UNO Q.

## Publication

- Instructables
- Arduino Project Hub
  

## License

GPL-3.0
