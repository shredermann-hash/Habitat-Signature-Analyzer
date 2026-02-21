#!/bin/bash
# Protection SIGHUP
trap '' SIGHUP

echo "========================================="
echo "  🎨 PHISUALIZE V2 - HABITAT MODE"
echo "========================================="
echo ""

# Nettoyage complet
echo "🧹 Nettoyage système..."
sudo pkill -f capture_daemon 2>/dev/null || true
sudo pkill -f ml_process 2>/dev/null || true
sudo pkill -f ml_predict 2>/dev/null || true
sudo systemctl stop arduino-router 2>/dev/null || true
rm -f /dev/shm/phisualize_buffer
sleep 2

cd /home/arduino/phisualizematrix

echo "📦 Démarrage capture_daemon..."
setsid python3 capture_daemon.py > /tmp/capture.log 2>&1 &
CAPTURE_PID=$!
sleep 3

echo "🧠 Démarrage ml_process..."
setsid python3 ml_process_influx.py > /tmp/ml_process.log 2>&1 &
ML_PID=$!
sleep 3

echo "🏠 Démarrage habitat signature..."
setsid python3 ml_predict_habitat.py > /tmp/habitat.log 2>&1 &
HABITAT_PID=$!
sleep 2

echo ""
echo "✅ PHISUALIZE V2 DÉMARRÉ"
echo "========================================="
echo ""
echo "Process actifs :"
echo "  capture_daemon : PID $CAPTURE_PID"
echo "  ml_process     : PID $ML_PID"
echo "  habitat        : PID $HABITAT_PID"
echo ""
echo "Mode : 🏠 Habitat Signature ML"
echo ""
echo "Matrice LED :"
echo "  😴 Calme    → ███░░░░░░░░░░ (3 col)"
echo "  🧍 Présence → ██████░░░░░░░ (6 col)"
echo "  🏃 Activité → █████████░░░░ (9 col)"
echo "  🎵 Ambiance → █████████████ (13 col)"
echo ""
echo "Dashboards :"
echo "  http://192.168.1.81:3000"
echo ""
echo "Logs temps réel :"
echo "  tail -f /tmp/habitat.log"
echo ""
echo "Arrêt :"
echo "  ./stop_phisualize.sh"
echo ""
echo "Ces process survivront à la fermeture du terminal"
echo "========================================="
