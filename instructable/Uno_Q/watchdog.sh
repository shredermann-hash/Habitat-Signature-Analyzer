#!/bin/bash
# Watchdog : redémarre si crash

trap '' SIGHUP

LOG="/tmp/watchdog.log"
echo "$(date) - Watchdog démarré" >> $LOG

while true; do
    # Vérifier si capture_daemon tourne
    if ! pgrep -f "python3.*capture_daemon" > /dev/null; then
        echo "$(date) - CRASH détecté, redémarrage..." >> $LOG
        
        cd /home/arduino/phisualizematrix
        ./stop_phisualize.sh >> $LOG 2>&1
        sleep 3
        ./start_phisualize.sh >> $LOG 2>&1
        
        echo "$(date) - Système redémarré" >> $LOG
    fi
    
    sleep 60  # Vérifier toutes les minutes
done
