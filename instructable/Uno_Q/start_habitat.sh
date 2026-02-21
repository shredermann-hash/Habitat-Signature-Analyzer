#!/bin/bash
trap '' SIGHUP

echo "🏠 PHISUALIZE HABITAT MODE"
echo ""

# Nettoyage
echo "🧹 Nettoyage..."
sudo pkill -f capture_daemon 2>/dev/null || true
sudo pkill -f ml_process 2>/dev/null || true
sudo pkill -f ml_predict 2>/dev/null || true
rm -f /dev/shm/phisualize_buffer
sleep 2

cd /home/arduino/phisualizematrix

echo "📦 capture_daemon..."
setsid python3 capture_daemon.py > /tmp/capture.log 2>&1 &
CAPTURE_PID=$!
sleep 3

echo "🧠 ml_process..."
setsid python3 ml_process_influx.py > /tmp/ml_process.log 2>&1 &
ML_PID=$!
sleep 3

echo "🏠 habitat signature..."
setsid python3 ml_predict_habitat.py > /tmp/habitat.log 2>&1 &
HABITAT_PID=$!
sleep 2

echo ""
echo "✅ MODE HABITAT DÉMARRÉ"
echo ""
echo "Process:"
echo "  capture: $CAPTURE_PID"
echo "  ml_process: $ML_PID"
echo "  habitat: $HABITAT_PID"
echo ""
echo "Matrice affiche patterns habitat:"
echo "  calme    → ███░░░░░░░░░░"
echo "  presence → ██████░░░░░░░"
echo "  activite → █████████░░░░"
echo "  ambiance → █████████████"
echo ""
echo "Logs: tail -f /tmp/habitat.log"
echo "Stop: ./stop_spectrum.sh"
echo ""
