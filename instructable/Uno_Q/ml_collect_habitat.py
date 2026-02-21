#!/usr/bin/env python3
"""
Habitat Signature V2 - Collecte PRODUCTION GRADE
V2 : ajout proximity_mean, proximity_max (14 features)
"""
from influxdb import InfluxDBClient
import numpy as np
import pandas as pd
import time
import os

client = InfluxDBClient(host='localhost', port=8086, database='phisualize')

WINDOW_SIZE = 10

def safe_corr(a, b):
    if len(a) < 2:
        return 0.0
    if np.std(a) < 1e-6 or np.std(b) < 1e-6:
        return 0.0
    c = np.corrcoef(a, b)[0, 1]
    return 0.0 if np.isnan(c) else float(c)

def safe_float(val):
    try:
        f = float(val)
        return 0.0 if not np.isfinite(f) else f
    except:
        return 0.0

def compute_features(window):
    audio_rms = window['audio_rms'].values.astype(float)
    audio_zcr = window['audio_zcr'].values.astype(float)
    imu_x = window['imu_x'].values.astype(float)
    imu_y = window['imu_y'].values.astype(float)
    imu_z = window['imu_z'].values.astype(float)
    imu_norm = np.sqrt(imu_x**2 + imu_y**2 + imu_z**2)
    mag_x = window['mag_x'].values.astype(float)
    mag_y = window['mag_y'].values.astype(float)
    mag_z = window['mag_z'].values.astype(float)
    mag_norm = np.sqrt(mag_x**2 + mag_y**2 + mag_z**2)
    pressure = window['pressure'].values.astype(float)
    proximity = window['proximity'].values.astype(float)

    return {
        'audio_rms_mean':  safe_float(np.mean(audio_rms)),
        'audio_rms_var':   safe_float(np.var(audio_rms)),
        'audio_rms_delta': safe_float(audio_rms[-1] - audio_rms[0]) if len(audio_rms) > 1 else 0.0,
        'audio_zcr_mean':  safe_float(np.mean(audio_zcr)),
        'audio_zcr_var':   safe_float(np.var(audio_zcr)),
        'imu_norm_mean':   safe_float(np.mean(imu_norm)),
        'imu_norm_var':    safe_float(np.var(imu_norm)),
        'mag_norm_mean':   safe_float(np.mean(mag_norm)),
        'mag_norm_var':    safe_float(np.var(mag_norm)),
        'pressure_mean':   safe_float(np.mean(pressure)),
        'pressure_grad':   safe_float(pressure[-1] - pressure[0]) if len(pressure) > 1 else 0.0,
        'corr_audio_imu':  safe_corr(audio_rms, imu_norm),
        'proximity_mean':  safe_float(np.mean(proximity)),
        'proximity_max':   safe_float(np.max(proximity)),
    }

def collect_with_precise_timing(duration_seconds):
    print(f"\nPrepare le contexte...")
    input("Appuie sur ENTER pour demarrer ->")

    start_time = pd.Timestamp.now("UTC")
    print(f"\nENREGISTREMENT EN COURS ({duration_seconds}s)...")

    time.sleep(duration_seconds)

    end_time = pd.Timestamp.now("UTC")
    print(f"Enregistrement termine !\n")

    start_ns = int(start_time.timestamp() * 1e9)
    end_ns = int(end_time.timestamp() * 1e9)

    query = f"""
    SELECT audio_rms, audio_zcr,
           imu_x, imu_y, imu_z,
           mag_x, mag_y, mag_z,
           pressure, proximity
    FROM sensors
    WHERE time >= {start_ns} AND time <= {end_ns}
    ORDER BY time ASC
    """

    print(f"Recuperation donnees InfluxDB...")
    result = client.query(query)
    points = list(result.get_points())

    if len(points) < WINDOW_SIZE * 2:
        print(f"Pas assez de donnees ({len(points)} points)")
        print(f"Periode: {start_time} -> {end_time}")
        return None

    print(f"{len(points)} points recuperes\n")

    df = pd.DataFrame(points)

    features_list = []
    for i in range(0, len(df) - WINDOW_SIZE + 1):
        window = df.iloc[i:i + WINDOW_SIZE]
        features = compute_features(window)
        features_list.append(features)

    result_df = pd.DataFrame(features_list)
    result_df = result_df.fillna(0)

    return result_df

def main():
    print("===================================")
    print("  HABITAT SIGNATURE V2 - COLLECTE")
    print("===================================\n")

    print("Classes disponibles:")
    print("  calme     : Piece vide, silence total")
    print("  activite  : Mouvement humain actif")
    print("  ambiance  : Musique ou film, son fort")
    print("  presence  : Main au-dessus du Nano, bruit ambiant\n")

    label = input("Label: ").strip().lower()

    if label not in ['calme', 'presence', 'activite', 'ambiance']:
        print("Label invalide")
        return

    duration = int(input("Duree (secondes, defaut 60): ") or "60")

    df = collect_with_precise_timing(duration)

    if df is None or len(df) == 0:
        print("Echec collecte")
        return

    df['label'] = label

    os.makedirs("/home/arduino/ml_data", exist_ok=True)

    timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"/home/arduino/ml_data/habitat_{label}_{timestamp}.csv"

    df.to_csv(filename, index=False)

    print(f"\nCollecte terminee !")
    print(f"   {len(df)} fenetres (stride 1)")
    print(f"   {filename}\n")

    print("Apercu features (mean):")
    print(df.drop('label', axis=1).mean().to_string())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCollecte interrompue")
    except Exception as e:
        print(f"\nErreur: {e}")
        import traceback
        traceback.print_exc()
