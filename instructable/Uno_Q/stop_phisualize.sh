#!/bin/bash

echo "🛑 Arrêt Phisualize V2"
echo ""

sudo pkill -f ml_predict_habitat
sudo pkill -f ml_predict_spectrum
sudo pkill -f ml_process_influx
sudo pkill -f capture_daemon

sleep 2
rm -f /dev/shm/phisualize_buffer

REMAINING=$(ps aux | grep -E "capture_daemon|ml_process|ml_predict" | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "⚠️  Process restants, force kill..."
    sudo pkill -9 -f capture_daemon
    sudo pkill -9 -f ml_process
    sudo pkill -9 -f ml_predict
    echo "✅ Force kill effectué"
else
    echo "✅ Tous les process arrêtés"
fi

echo ""
echo "✅ Phisualize V2 arrêté"
