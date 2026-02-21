#!/bin/bash
# Afficher status système

echo "📊 PHISUALIZE STATUS"
echo "===================="
echo ""

# Process
echo "🐍 PROCESS:"
ps aux | grep -E "capture_daemon|ml_process|ml_predict" | grep -v grep | awk '{print "  ", $11, "(PID", $2")"}'

# Shared memory
echo ""
echo "💾 SHARED MEMORY:"
if [ -f /dev/shm/phisualize_buffer ]; then
    SIZE=$(stat -c%s /dev/shm/phisualize_buffer)
    echo "   ✅ Buffer actif ($SIZE bytes)"
else
    echo "   ❌ Buffer absent"
fi

# InfluxDB
echo ""
echo "📊 INFLUXDB:"
COUNT=$(influx -database phisualize -execute 'SELECT COUNT(*) FROM sensors' 2>/dev/null | tail -1 | awk '{print $2}')
if [ -n "$COUNT" ]; then
    echo "   Total points: $COUNT"
    LAST=$(influx -database phisualize -execute 'SELECT time FROM sensors ORDER BY time DESC LIMIT 1' -precision rfc3339 2>/dev/null | tail -1)
    echo "   Dernier point: $LAST"
else
    echo "   ❌ Pas de données"
fi

echo ""
