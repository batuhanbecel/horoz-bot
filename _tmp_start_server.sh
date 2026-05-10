#!/bin/bash
# Project Zomboid Server Starter Script

SERVER_DIR="/opt/pz-server"
LOG_FILE="$SERVER_DIR/pz_server.log"
PID_FILE="$SERVER_DIR/pz_server.pid"

start_server() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "Sunucu zaten çalışıyor (PID: $PID)"
            return 1
        fi
    fi
    
    cd "$SERVER_DIR"
    echo "[$(date)] Sunucu başlatılıyor..."
    nohup bash start-server.sh > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "[$(date)] Sunucu başlatıldı (PID: $(cat $PID_FILE))"
    return 0
}

stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Sunucu çalışmıyor"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
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
    if [ ! -f "$PID_FILE" ]; then
        echo "OFFLINE"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "ONLINE (PID: $PID)"
        return 0
    else
        echo "OFFLINE (PID dosyası eski)"
        rm -f "$PID_FILE"
        return 1
    fi
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
