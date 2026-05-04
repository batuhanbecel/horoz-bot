# 🐓 Horoz Bot

Türkçe, slash command tabanlı çok amaçlı Discord botu.  
Moderasyon · Müzik (YouTube + Playlist) · Eğlence · Özel Komutlar

---

## Özellikler

| Kategori | Komutlar |
|---|---|
| 🛡️ Moderasyon | `/moderatör temizle` `at` `yasakla` `sustur` `sustu-kaldır` `ihlaller` `ihlal-temizle` |
| 🎵 Müzik | `/müzik çal` `ara` `atla` `duraklat` `devam` `dur` `ses` `sıra` `sıra-temizle` `döngü` `şimdi-çalıyor` |
| 🎉 Eğlence | `/yazıtura` `/zar` `/anket` `/etkinlik` |
| ⚙️ Özel Komutlar | `/komutyarat` `/komutlistele` `/komutsil` `/komut` |
| ℹ️ Araçlar | `/yardım` `/ping` `/kullanici-bilgi` `/sunucu-bilgi` `/avatar` `/bot-bilgi` |
| 🔧 Yönetim | `/komuttazele` |

---

## Kurulum

### Gereksinimler

- Python 3.11+
- FFmpeg (sistem genelinde PATH'e ekli)
- Discord Bot Token ([Developer Portal](https://discord.com/developers/applications))

---

### 1. FFmpeg Kurulumu

**Windows:**
```powershell
winget install Gyan.FFmpeg
```
Kurulumdan sonra yeni bir terminal aç (PATH güncellenmesi için).

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg -y
```

---

### 2. Python Bağımlılıkları

```bash
pip install -r requirements.txt
```

Gerekli paketler:
- `discord.py[voice]` — Discord API + ses desteği
- `yt-dlp` — YouTube ses akışı
- `aiosqlite` — Async SQLite veritabanı
- `PyNaCl` — Discord ses şifreleme
- `python-dotenv` — .env yönetimi

---

### 3. Discord Developer Portal Ayarları

1. [discord.com/developers/applications](https://discord.com/developers/applications) adresine git
2. Uygulamanı seç → **Bot** sekmesi
3. **Privileged Gateway Intents** bölümünden şunları aktif et:
   - ✅ **Server Members Intent**
   - ✅ **Message Content Intent**
4. Token'ı kopyala

---

### 4. .env Dosyası

Proje klasöründe `.env` dosyası oluştur:

```env
DISCORD_TOKEN=buraya_bot_tokenini_yaz
GUILD_ID=buraya_sunucu_idni_yaz
```

> **Not:** `GUILD_ID` isteğe bağlıdır. Sunucu ID'si için Discord'da **Geliştirici Modu**'nu aç (Ayarlar → Gelişmiş), ardından sunucu ikonuna sağ tıkla → ID Kopyala.

---

### 5. Botu Sunucuya Ekle

Developer Portal → OAuth2 → URL Generator:

**Scopes:** `bot`, `applications.commands`

**Bot Permissions:**
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members (Timeout)
- Connect & Speak (ses kanalları için)
- Send Messages, Embed Links, Read Message History

Oluşturulan URL'yi tarayıcıda aç ve botu sunucuna ekle.

---

### 6. Botu Başlat

```bash
python main.py
```

İlk başlatmada slash komutları Discord'a senkronize edilir. Komutların görünmesi **birkaç dakika** alabilir.

---

## Ubuntu'da Servis Olarak Çalıştırma

Botu sunucu yeniden başlayınca otomatik başlatmak için systemd servisi oluştur:

```bash
sudo nano /etc/systemd/system/horoz-bot.service
```

```ini
[Unit]
Description=Horoz Discord Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/horoz_bot
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable horoz-bot
sudo systemctl start horoz-bot

# Durumu kontrol et
sudo systemctl status horoz-bot

# Logları izle
sudo journalctl -u horoz-bot -f
```

---

## Komutlar Güncellenmiyorsa

Slash komutları Discord tarafında cache'lenir. Güncelleme için:

```
/komuttazele
```

Bu komut `Administrator` yetkisi gerektirir ve tüm komutları Discord ile yeniden senkronize eder.

---

## Müzik — Playlist Desteği

`/müzik çal` komutuna YouTube playlist linki verilebilir:

```
/müzik çal sorgu:https://www.youtube.com/playlist?list=PLxxx...
```

- Maksimum 100 şarkı yüklenir
- Şarkı URL'leri çalınmadan hemen önce çözümlenir (lazy loading)
- Playlist yüklenirken bot yanıt beklemez, kuyruğa ekleme mesajı gösterilir

---

## Özel Komutlar

Sunucu yöneticileri `/komutyarat` ile özel komutlar oluşturabilir:

```
/komutyarat isim:merhaba yanıt:Merhaba dünya!
/komut isim:merhaba          → "Merhaba dünya!" gönderilir
/komutlistele                → Tüm özel komutlar
/komutsil isim:merhaba       → Komutu sil
```

Özel komutlar sunucuya özeldir, başka sunucularda görünmez.

---

## Katkıda Bulunma

Pull request'ler kabul edilir. Büyük değişiklikler için önce bir issue açın.

---

## Lisans

MIT
