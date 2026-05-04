#!/bin/bash
set -e

echo ""
echo "========================================="
echo "   🐓 Horoz Bot — Ubuntu Kurulum Scripti"
echo "========================================="
echo ""

# Sistem güncellemesi
echo "[1/7] Sistem güncelleniyor..."
apt update -qq && apt upgrade -y -qq

# Gerekli paketler
echo "[2/7] FFmpeg, Python3, pip, git kuruluyor..."
apt install -y -qq ffmpeg python3 python3-pip python3-venv git curl

echo "      Python: $(python3 --version)"
echo "      FFmpeg: $(ffmpeg -version 2>&1 | head -n1)"

# Repo klonla
echo "[3/7] Horoz Bot GitHub'dan çekiliyor..."
if [ -d "/opt/horoz_bot" ]; then
    echo "      Klasör zaten var, güncelleniyor..."
    cd /opt/horoz_bot && git pull
else
    git clone https://github.com/batuhanbecel/horoz-bot.git /opt/horoz_bot
fi
cd /opt/horoz_bot

# Virtual environment
echo "[4/7] Python sanal ortamı oluşturuluyor..."
python3 -m venv venv
source venv/bin/activate

# Bağımlılıklar
echo "[5/7] Python paketleri yükleniyor..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# .env dosyası
echo "[6/7] .env dosyası yapılandırılıyor..."
if [ ! -f "/opt/horoz_bot/.env" ]; then
    cp /opt/horoz_bot/.env.example /opt/horoz_bot/.env
    echo ""
    echo "  ⚠️  .env dosyası oluşturuldu. Lütfen düzenle:"
    echo "      nano /opt/horoz_bot/.env"
    echo ""
fi

# Systemd service
echo "[7/7] Systemd servisi kuruluyor..."
cat > /etc/systemd/system/horoz-bot.service << 'EOF'
[Unit]
Description=Horoz Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/horoz_bot
ExecStart=/opt/horoz_bot/venv/bin/python main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable horoz-bot

echo ""
echo "========================================="
echo "   ✅ Kurulum tamamlandı!"
echo "========================================="
echo ""
echo "  Sonraki adım — .env dosyasını düzenle:"
echo "  nano /opt/horoz_bot/.env"
echo ""
echo "  Botu başlat:"
echo "  systemctl start horoz-bot"
echo ""
echo "  Logları izle:"
echo "  journalctl -u horoz-bot -f"
echo ""
