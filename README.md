# 🐓 Horoz Bot

Türkçe, slash command tabanlı çok amaçlı Discord botu.  
Moderasyon · Müzik · Eğlence / Oyunlar · Sunucu Yönetimi · Özel Komutlar

---

## Özellikler

| Kategori | Komutlar |
|---|---|
| 🛡️ Moderasyon — Üye | `/üye uyar` `at` `yasakla` `sustur` `sus-kaldır` |
| 🛡️ Moderasyon — Kanal | `/kanal temizle` `yavaşmod` `kilitle` `kilit-aç` |
| ⚠️ İhlal | `/ihlal listele` `sil` |
| 🎵 Müzik | `/müzik çal` `ara` `atla` `duraklat` `devam` `dur` `ses` `sıra` `sıra-sil` `karıştır` `döngü` `şimdi` |
| 🎮 Oyunlar | `/yazıtura` `/zar` `/8top` `/kaccm` `/tkm` `/adamasmaca` `/arena` `/isimşehir` `/vampirkoylu` `/rusruleti` |
| 📊 Sosyal | `/anket` `/etkinlik` |
| 📢 Mesajlaşma | `/yaz` `/embed` `/duyuru` `/hatırlat` |
| ℹ️ Araçlar | `/ping` `/profil` `/sunucu` `/avatar` `/bot` `/yardım` |
| 😀 Emoji & Sticker | `/emoji-ekle` `/oto-emoji` · Sağ tık → Emojileri Ekle / Sticker'ı Ekle |
| ⚙️ Özel Komutlar | `/komut-yarat` `/komut-liste` `/komut-sil` `/komut` |
| 🔧 Yönetim | `/tazele` `/restart` |

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
```

---

### 5. Botu Sunucuya Ekle

Developer Portal → OAuth2 → URL Generator:

**Scopes:** `bot`, `applications.commands`

**Bot Permissions:**
- Manage Messages
- Kick Members
- Ban Members
- Moderate Members (Timeout)
- Manage Channels
- Manage Emojis and Stickers
- Connect & Speak (ses kanalları için)
- Send Messages, Embed Links, Read Message History, Attach Files

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
User=root
WorkingDirectory=/root/horoz_bot
ExecStart=/root/horoz_bot/venv/bin/python main.py
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
/tazele
```

Bu komut `Administrator` yetkisi gerektirir ve tüm komutları Discord ile yeniden senkronize eder.  
Ayrıca `/restart` komutu botu yeniden başlatarak senkronizasyonu otomatik yapar.

---

## Oyunlar

| Oyun | Açıklama |
|---|---|
| `/vampirkoylu` | 4–12 kişilik çok oyunculu rol yapma oyunu. Vampirler gece öldürür, köylüler gündüz oylar. |
| `/rusruleti` | 2–6 kişilik Rus Ruleti. 6 oda, 1 mermi — biri mutlaka kaybeder. |
| `/arena` | 2 kişilik tur bazlı dövüş. Kılıç / Büyü / Kalkan sistemi. |
| `/isimşehir` | 2–8 kişilik İsim Şehir. 5 tur, 5 kategori. Eşsiz cevap 10 puan. |
| `/tkm` | Taş Kağıt Makas. İnsan veya bota karşı, ilk 2 galibiyeti alan kazanır. |
| `/adamasmaca` | Tek oyunculu Adam Asmaca. 6 yanlış hak, Türkçe kelime havuzu. |

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

Sunucu yöneticileri `/komut-yarat` ile sunucuya özel komutlar oluşturabilir:

```
/komut-yarat isim:merhaba yanıt:Merhaba dünya!
/komut isim:merhaba          → "Merhaba dünya!" gönderilir
/komut-liste                 → Tüm özel komutlar
/komut-sil isim:merhaba      → Komutu sil
```

Özel komutlar sunucuya özeldir, başka sunucularda görünmez.

---

## Katkıda Bulunma

Pull request'ler kabul edilir. Büyük değişiklikler için önce bir issue açın.

---

## Lisans

MIT
