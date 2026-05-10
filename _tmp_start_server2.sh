#!/bin/bash
# Project Zomboid Server Starter Script

SERVER_DIR="/opt/pz-server"
LOG_FILE="$SERVER_DIR/pz_server.log"
PID_FILE="$SERVER_DIR/pz_server.pid"

get_pz_pid() {
    pgrep -f "ProjectZomboid64" | head -1
}

start_server() {
    PID=$(get_pz_pid)
    if [ -n "$PID" ]; then
        echo "Sunucu zaten çalışıyor (PID: $PID)"
        return 1
    fi

    cd "$SERVER_DIR"
    echo "[$(date)] Sunucu başlatılıyor..."
    nohup bash start-server.sh > "$LOG_FILE" 2>&1 &
    NOHUP_PID=$!
    sleep 2
    PID=$(get_pz_pid)
    if [ -n "$PID" ]; then
        echo $PID > "$PID_FILE"
        echo "[$(date)] Sunucu başlatıldı (PID: $PID)"
        return 0
    else
        echo "[$(date)] Sunucu başlatılamadı (nohup PID: $NOHUP_PID)"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_server() {
    PID=$(get_pz_pid)
    if [ -z "$PID" ] && [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
    fi
    if [ -z "$PID" ]; then
        echo "Sunucu çalışmıyor"
        return 1
    fi

    if kill -0 "$PID" 2>/dev/null; then
        echo "[$(date)] Sunucu durduruluyor (PID: $PID)..."
        kill "$PID"
        sleep 5
        if kill -0 "$PID" 2>/dev/null; then
            kill -9 "$PID"
        fi
        rm -f "$PID_FILE"
        echo "[$(date)] Sunucu durduruldu"
        return 0
    else
        echo "Sunucu çalışmıyor (PID dosyası eski)"
        rm -f "$PID_FILE"
        return 1
    fi
}

restart_server() {
    stop_server
    sleep 2
    start_server
}

status_server() {
    PID=$(get_pz_pid)
    if [ -n "$PID" ]; then
        echo "ONLINE (PID: $PID)"
        return 0
    fi
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "ONLINE (PID: $OLD_PID)"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    echo "OFFLINE"
    return 1
}

get_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -n "${1:-20}" "$LOG_FILE"
    else
        echo "Log dosyası bulunamadı"
    fi
}

case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    logs)
        get_logs "$2"
        ;;
    *)
        echo "Kullanım: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
