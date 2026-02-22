# HSA — Habitat Signature Analyzer
### A Multi-Sensor Edge AI System Running Entirely on Arduino Hardware

---

## Introduction

A room has a behavioral fingerprint. This project classifies environmental behavioral states in real time using 7 physical sensors, a distributed 3-MCU pipeline, and a RandomForest model running entirely on Arduino hardware. No cloud. No dedicated AI accelerator. No external dependencies.

The system detects four habitat classes — **calme** (quiet), **presence** (person nearby but still), **activite** (active movement), **ambiance** (music playing) — at 10 Hz with 99.1% accuracy. It has run continuously for 4+ days without interruption.

---

## Architecture

Three MCUs work together in a distributed pipeline:

**Arduino Nano 33 BLE Sense** acquires data from 7 integrated sensors, runs double-windowed FFT processing on the PDM microphone signal, packs all features into a 118-byte struct, and transmits at 921600 baud over UART.

**STM32** (embedded on the UNO Q) acts as a transparent UART bridge between the Nano and the Linux SoC. It also drives the 13×8 LED matrix, displaying a real-time audio spectrum.

**Arduino UNO Q** (Qualcomm QRB2210, 4GB RAM, 32GB eMMC) runs the full intelligence layer over SSH: three Python processes communicating via shared memory, InfluxDB for time-series storage, and Grafana for real-time visualization.

```
Nano 33 BLE Sense  →[UART 921600]→  STM32  →[/dev/ttyHS1]
  → hsa_capture.py   (UART reader, shared memory ring buffer)
  → hsa_process.py   (packet decoder, InfluxDB writer)
  → hsa_predict.py   (RandomForest inference, habitat classification)
  → Grafana          (localhost:3000, 5s refresh)
```

End-to-end latency: 4–5 seconds.

---

## The 118-Byte Packet

Every sensor reading is packed into a single 118-byte struct transmitted at ~10 Hz:

```
header[2]        0xAA 0xBB  — frame sync
packet_id        uint16     — loss detection
timestamp_us     uint32     — micros()
audio_bands[16]  float×16   — 64B mel-scale FFT
audio_rms        float      — RMS amplitude
audio_zcr        float      — zero-crossing rate
imu_data[3]      float×3    — 12B accelerometer X/Y/Z
env_data[6]      float×6    — 24B mag + pressure + temp + RH
prox             uint8      — IR proximity 0–255
_padding         uint8      — alignment
TOTAL                         118B @ 10 Hz = 9.2 kB/s
```

The double FFT with 50% overlap (two 128-point Hann-windowed frames averaged) produces stable mel-scale energy estimates that are robust to transient noise — critical for distinguishing **ambiance** from **activite**.

---

## Signal Processing on the Nano

The PDM microphone runs at 16 kHz. Every audio callback delivers 96 samples. Two overlapping 128-point FFT frames are computed using the ARM CMSIS-DSP library (`arm_rfft_fast_f32`), averaged, and mapped to 16 mel-scale bands covering 0–8 kHz.

The magnetometer (BMM150) proved to be the most discriminative feature for presence detection — human proximity causes 10–12 µT² variance versus ~2 µT² in an empty room, due to electromagnetic field perturbations from nearby electronics. This was an unexpected discovery that emerged from feature importance analysis after training.

The barometer (LPS22HB) detects window openings through pressure impulses (~0.1–0.3 hPa). The proximity sensor (APDS9960) resolves the ambiguity between **calme** and **presence** that no other sensor could reliably separate.

---

## Python Pipeline on the UNO Q

Three independent Python processes run with `setsid`, surviving terminal closure:

**hsa_capture.py** reads `/dev/ttyHS1`, synchronizes on the `0xAA 0xBB` header, validates each 118-byte packet, and writes to a shared memory ring buffer (`/dev/shm/hsa_buffer`). It never touches InfluxDB. Process isolation is what enables multi-day stability.

**hsa_process.py** reads the shared memory ring buffer, unpacks all sensor fields, and writes raw data to InfluxDB (`sensors` measurement) in batches of 10 points to minimize I/O overhead.

**hsa_predict.py** queries the last 10 sensor points from InfluxDB every 500ms, computes 14 engineered features, runs RandomForest inference, applies a rolling average over 5 consecutive predictions to smooth label transitions, and writes the classified habitat state and per-class probabilities to InfluxDB (`habitat` measurement). It also sends a 15-byte spectrum command to the STM32 to update the LED matrix pattern.

```bash
./hsa_start.sh    # launch all three processes
./hsa_stop.sh     # clean stop + shared memory cleanup
./hsa_status.sh   # health check
./hsa_watchdog.sh # auto-restart on crash
```

---

## Machine Learning

- **Algorithm:** RandomForest (sklearn, 200 estimators, `class_weight='balanced'`)
- **Training data:** 966 windows, 18 sessions, 4 classes
- **Cross-validation:** GroupKFold by session — windows from the same recording session are temporally correlated and must never appear in both train and test sets. Random splitting causes data leakage and inflated accuracy.
- **Accuracy:** 97.2% on held-out sessions
- **Features:** 14 engineered features computed over a 10-point sliding window (audio RMS mean/variance/delta, ZCR mean/variance, IMU magnitude mean/variance, magnetometer magnitude mean/variance, pressure mean/gradient, audio-IMU correlation, proximity mean/max)
- **Smoothing:** rolling average over 5 consecutive predictions

Training and inference run entirely on the UNO Q — no external compute required.

```bash
python3 hsa_collect.py   # collect labeled sessions per class
python3 hsa_train.py     # train and save model
```

---

## Grafana Dashboard

Grafana runs locally on the UNO Q at `http://[UNO-Q-IP]:3000`. Two dashboards feed from the same InfluxDB instance:

**Sensors dashboard** — raw time series for all 7 sensors: audio RMS, 16 mel bands, IMU X/Y/Z, magnetometer X/Y/Z, pressure, temperature, humidity, proximity bar gauge.

**Habitat dashboard** — State Timeline (colour-coded behavioral history), Confidence LED gauge (green ≥80%, yellow 60–79%, red <60%), per-class probability bars, event log excluding calme.

InfluxDB stores all data on the eMMC (`/dev/mmcblk0p68`). History survives reboots. After 4 days of continuous operation, the complete behavioral history of the room is immediately visible on dashboard load.

**Important:** InfluxDB's default retention policy is infinite (`0s`). At 10 Hz, the database grows continuously and will eventually fill the eMMC. Set a 30-day retention policy immediately after installation:

```bash
influx -execute 'ALTER RETENTION POLICY "autogen" ON "hsa" DURATION 30d SHARD DURATION 1d DEFAULT'
# Verify: duration should show 720h0m0s
influx -execute 'SHOW RETENTION POLICIES ON hsa'
```

---

## Key Lessons

- Process isolation between capture, processing, and inference enabled 4+ days of continuous uptime
- Session-based cross-validation (GroupKFold) is mandatory for time-series ML — random splits cause leakage
- The magnetometer is a better presence detector than the IMU in a domestic environment
- Install Grafana from the `.deb` package on the UNO Q — the apt repository breaks App Lab on every boot
- `sizeof(SensorFeatures)` must print **118** on the Nano before proceeding — anything else means misaligned structs and corrupted data
