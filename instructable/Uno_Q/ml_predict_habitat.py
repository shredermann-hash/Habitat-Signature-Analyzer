#!/usr/bin/env python3
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
"""
Habitat Signature V2 - Prediction Temps Reel
V2 : 14 features (ajout proximity_mean, proximity_max)
"""
from influxdb import InfluxDBClient
import numpy as np
import pandas as pd
import joblib
import time
import json
import serial

# ══════ UART MATRICE ══════
try:
    uart = serial.Serial('/dev/ttyHS1', 921600, timeout=0.01)
    print("UART matrice OK")
except Exception as e:
    uart = None
    print(f"UART non disponible: {e}")

# ══════ CHARGEMENT PIPELINE ══════
print("Chargement pipeline...")
pipeline = joblib.load('/home/arduino/ml_models/habitat_signature_pipeline.pkl')
config   = json.load(open('/home/arduino/ml_models/habitat_signature_config.json'))
FEATURES = config['features']
CLASSES  = config['classes']

print(f"Classes  : {CLASSES}")
print(f"Features : {len(FEATURES)}")
print(f"Accuracy : {config['accuracy']*100:.1f}%\n")

# ══════ INFLUXDB ══════
client = InfluxDBClient(host='localhost', port=8086, database='phisualize')

WINDOW_SIZE = 10

def safe_float(val):
    try:
        f = float(val)
        return 0.0 if not np.isfinite(f) else f
    except:
        return 0.0

def safe_corr(a, b):
    if len(a) < 2: return 0.0
    if np.std(a) < 1e-6 or np.std(b) < 1e-6: return 0.0
    c = np.corrcoef(a, b)[0,1]
    return 0.0 if np.isnan(c) else float(c)

def get_latest_window():
    query = """
    SELECT audio_rms, audio_zcr,
           imu_x, imu_y, imu_z,
           mag_x, mag_y, mag_z,
           pressure, proximity
    FROM sensors
    ORDER BY time DESC
    LIMIT 10
    """
    result = client.query(query)
    points = list(result.get_points())

    if len(points) < WINDOW_SIZE:
        return None

    df = pd.DataFrame(points).iloc[::-1].reset_index(drop=True)

    audio_rms = df['audio_rms'].values.astype(float)
    audio_zcr = df['audio_zcr'].values.astype(float)
    imu_x     = df['imu_x'].values.astype(float)
    imu_y     = df['imu_y'].values.astype(float)
    imu_z     = df['imu_z'].values.astype(float)
    imu_norm  = np.sqrt(imu_x**2 + imu_y**2 + imu_z**2)
    mag_x     = df['mag_x'].values.astype(float)
    mag_y     = df['mag_y'].values.astype(float)
    mag_z     = df['mag_z'].values.astype(float)
    mag_norm  = np.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
    pressure  = df['pressure'].values.astype(float)
    proximity = df['proximity'].values.astype(float)

    features = [
        safe_float(np.mean(audio_rms)),
        safe_float(np.var(audio_rms)),
        safe_float(audio_rms[-1] - audio_rms[0]),
        safe_float(np.mean(audio_zcr)),
        safe_float(np.var(audio_zcr)),
        safe_float(np.mean(imu_norm)),
        safe_float(np.var(imu_norm)),
        safe_float(np.mean(mag_norm)),
        safe_float(np.var(mag_norm)),
        safe_float(np.mean(pressure)),
        safe_float(pressure[-1] - pressure[0]),
        safe_corr(audio_rms, imu_norm),
        safe_float(np.mean(proximity)),
        safe_float(np.max(proximity)),
    ]

    return features

# ══════ PATTERNS MATRICE ══════
SEUILS = {
    'calme'    : 0.85,
    'presence' : 0.65,
    'activite' : 0.65,
    'ambiance' : 0.75,
}

HABITAT_PATTERNS = {
    'calme'    : [8, 8, 8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    'presence' : [8, 8, 8, 8, 8, 8, 0, 0, 0, 0, 0, 0, 0],
    'activite' : [8, 8, 8, 8, 8, 8, 8, 8, 8, 0, 0, 0, 0],
    'ambiance' : [8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8],
}

def send_habitat_pattern(label):
    if uart is None:
        return
    try:
        bands    = HABITAT_PATTERNS.get(label, [0]*13)
        header   = 0xDD
        data     = bytes([header] + bands)
        checksum = 0
        for byte in data:
            checksum ^= byte
        uart.write(data + bytes([checksum]))
        uart.flush()
    except Exception as e:
        print(f"UART erreur: {e}")

EMOJIS = {
    'calme'    : '😴',
    'presence' : '🧍',
    'activite' : '🏃',
    'ambiance' : '🎵'
}

PROBA_BUFFER_SIZE = 5
proba_buffer = []

print("=" * 45)
print("  HABITAT SIGNATURE V2 - PREDICTION LIVE")
print("=" * 45)
print("Ctrl+C pour arreter\n")

def write_habitat(label, confidence, mean_proba):
    try:
        point = [{
            "measurement": "habitat",
            "fields": {
                "label":      label,
                "confidence": float(confidence),
            }
        }]
        for i, c in enumerate(CLASSES):
            point[0]["fields"][f"proba_{c}"] = float(mean_proba[i])
        client.write_points(point)
    except Exception:
        pass

pred_count  = 0
last_label  = None
error_count = 0

try:
    while True:
        try:
            features = get_latest_window()

            if features is None:
                time.sleep(0.5)
                continue

            proba = pipeline.predict_proba([features])[0]

            proba_buffer.append(proba)
            if len(proba_buffer) > PROBA_BUFFER_SIZE:
                proba_buffer.pop(0)

            mean_proba = np.mean(proba_buffer, axis=0)
            label_idx  = np.argmax(mean_proba)
            label      = CLASSES[label_idx]
            confidence = mean_proba[label_idx] * 100

            pred_count += 1

            if label != last_label:
                print(f"\n{'='*45}")
                print(f"  {EMOJIS.get(label,'?')} HABITAT : {label.upper()}")
                print(f"  Confiance : {confidence:.1f}%")
                print(f"  Probas    : ", end='')
                for i, c in enumerate(CLASSES):
                    print(f"{c}={mean_proba[i]*100:.0f}%", end=' ')
                print(f"\n{'='*45}")
                last_label = label
                send_habitat_pattern(label)
                write_habitat(label, confidence/100, mean_proba)

            if pred_count % 2 == 0:
                write_habitat(label, confidence, mean_proba)

            elif pred_count % 10 == 0:
                print(f"[{pred_count:4d}] {EMOJIS.get(label,'?')} {label:10s} "
                      f"| {confidence:.1f}% "
                      f"| buffer={len(proba_buffer)}")

            error_count = 0
            time.sleep(0.5)

        except KeyboardInterrupt:
            raise

        except Exception as e:
            error_count += 1
            print(f"Erreur ({error_count}): {e}")
            if error_count >= 10:
                print("Trop d'erreurs, arret")
                break
            time.sleep(1)

except KeyboardInterrupt:
    print(f"\n\nArret - {pred_count} predictions effectuees")
    print(f"Derniere prediction : {last_label}")
    if uart:
        send_habitat_pattern('calme')
        uart.close()
