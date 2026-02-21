#!/usr/bin/env python3
import time, struct, numpy as np
from multiprocessing import shared_memory
from influxdb import InfluxDBClient

FRAME_SIZE = 118
RING_SIZE = 100

influx = InfluxDBClient(host='localhost', port=8086, database='phisualize')
shm = shared_memory.SharedMemory(name='phisualize_buffer')
shared_array = np.ndarray((4 + RING_SIZE * FRAME_SIZE,), dtype=np.uint8, buffer=shm.buf)
write_idx_ptr = shared_array[:4].view(np.uint32)
frames_buffer = shared_array[4:].reshape(RING_SIZE, FRAME_SIZE)

read_idx = 0
batch_points = []

print("ML Process - 16 BANDES MEL")

try:
    while True:
        if read_idx < write_idx_ptr[0]:
            packet = frames_buffer[read_idx % RING_SIZE].tobytes()
            
            if len(packet) == FRAME_SIZE and packet[0:2] == b'\xAA\xBB':
                packet_id, timestamp_us = struct.unpack('<HI', packet[2:8])
                floats = struct.unpack('<27fBB', packet[8:])
                
                bands = floats[0:16]
                
                point = {
                    "measurement": "sensors",
                    "tags": {"device": "nano"},
                    "fields": {
                        "audio_band_0": float(bands[0]),
                        "audio_band_1": float(bands[1]),
                        "audio_band_2": float(bands[2]),
                        "audio_band_3": float(bands[3]),
                        "audio_band_4": float(bands[4]),
                        "audio_band_5": float(bands[5]),
                        "audio_band_6": float(bands[6]),
                        "audio_band_7": float(bands[7]),
                        "audio_band_8": float(bands[8]),
                        "audio_band_9": float(bands[9]),
                        "audio_band_10": float(bands[10]),
                        "audio_band_11": float(bands[11]),
                        "audio_band_12": float(bands[12]),
                        "audio_band_13": float(bands[13]),
                        "audio_band_14": float(bands[14]),
                        "audio_band_15": float(bands[15]),
                        "audio_rms": float(floats[16]),
                        "audio_zcr": float(floats[17]),
                        "imu_x": float(floats[18]),
                        "imu_y": float(floats[19]),
                        "imu_z": float(floats[20]),
                        "mag_x": float(floats[21]),
                        "mag_y": float(floats[22]),
                        "mag_z": float(floats[23]),
                        "pressure": float(floats[24]),
                        "temperature": float(floats[25]),
                        "humidity": float(floats[26]),
                        "proximity": int(floats[27])
                    }
                }
                
                batch_points.append(point)
                
                if len(batch_points) >= 10:
                    influx.write_points(batch_points)
                    batch_points = []
            
            read_idx += 1
        else:
            time.sleep(0.01)
except KeyboardInterrupt:
    if batch_points:
        influx.write_points(batch_points)
finally:
    shm.close()
