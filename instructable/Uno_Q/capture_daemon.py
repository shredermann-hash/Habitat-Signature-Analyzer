#!/usr/bin/env python3
"""
Capture daemon - CORRIGÉ pour struct 118 bytes
(ne détruit plus la shared memory)
"""
import serial
import struct
import time
from multiprocessing import shared_memory
import numpy as np

PORT = "/dev/ttyHS1"
BAUD = 921600
FRAME_SIZE = 118
RING_SIZE = 100

# Créer shared memory
shm_size = 4 + (RING_SIZE * FRAME_SIZE)
shm = shared_memory.SharedMemory(create=True, size=shm_size, name='phisualize_buffer')

# Vue numpy
shared_array = np.ndarray((shm_size,), dtype=np.uint8, buffer=shm.buf)
write_idx_ptr = shared_array[:4].view(np.uint32)
frames_buffer = shared_array[4:].reshape(RING_SIZE, FRAME_SIZE)

write_idx_ptr[0] = 0

ser = serial.Serial(PORT, BAUD, timeout=0.01)
ser.reset_input_buffer()

buffer = bytearray()
last_id = None
total_packets = 0
total_lost = 0

print("🚀 Capture Daemon démarré (VERSION CORRIGÉE)")
print(f"📡 {PORT} @ {BAUD}")
print(f"💾 Shared memory: {shm_size} bytes")
print(f"📦 Frame size: {FRAME_SIZE} bytes\n")

try:
    while True:
        chunk = ser.read(2048)
        if chunk:
            buffer.extend(chunk)

        while len(buffer) >= FRAME_SIZE:
            try:
                idx = buffer.index(b'\xAA\xBB')
            except ValueError:
                buffer = buffer[-FRAME_SIZE:]
                break

            if idx + FRAME_SIZE <= len(buffer):
                packet = buffer[idx:idx+FRAME_SIZE]
                buffer = buffer[idx+FRAME_SIZE:]

                try:
                    packet_id, timestamp_us = struct.unpack('<HI', packet[2:8])

                    if last_id is not None:
                        lost = (packet_id - last_id - 1) % 65536
                        if lost > 0:
                            total_lost += lost
                            print(f"⚠️  Perte: {lost} paquets (ID {last_id} → {packet_id})")

                    last_id = packet_id
                    total_packets += 1

                    slot = write_idx_ptr[0] % RING_SIZE
                    frames_buffer[slot] = np.frombuffer(packet, dtype=np.uint8)
                    write_idx_ptr[0] += 1

                except struct.error as e:
                    print(f"⚠️  Erreur parsing: {e}")
            else:
                break

except KeyboardInterrupt:
    print("\n📊 Stats finales:")
    print(f"   Paquets: {total_packets}")
    print(f"   Perdus: {total_lost}")
    if total_packets > 0:
        loss_rate = (total_lost / (total_packets + total_lost)) * 100
        print(f"   Taux perte: {loss_rate:.2f}%")
    print("👋 Arrêt capture daemon")
finally:
    try:
        ser.close()
    except:
        pass

    try:
        shm.close()
    except:
        pass
    # IMPORTANT : pas de shm.unlink() ici.
    # La destruction du segment est gérée par stop_spectrum.sh
