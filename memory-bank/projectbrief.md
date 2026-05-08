# Project Brief — Horoz Bot

## Proje Özeti
Horoz Bot, Discord sunucuları için geliştirilmiş çok amaçlı bir Türkçe Discord botudur.
Tüm komutlar Discord'un native slash command (/) sistemiyle çalışır.
Tüm yanıtlar **Components V2** (raw Discord API container/section/text/thumbnail/media) ile render edilir.

## Temel Gereksinimler
- Sadece slash commands (prefix yok)
- Tüm komut isimleri ve yanıtlar Türkçe
- Windows'ta geliştirme, Ubuntu'da production host
- GitHub: https://github.com/batuhanbecel/horoz-bot

## Kapsam

### Moderasyon
- `/kanal` grubu
  - `temizle` — mesaj sil (1-100)
  - `yavaşmod` — slowmode (0-21600 saniye)
  - `kilitle` — kanalı kilitler
  - `kilit-aç` — kilit kaldırır
- `/üye` grubu
  - `uyar` — uyarı + infraction kaydı
  - `at` — kick
  - `yasakla` — ban (0-7 gün mesaj silme)
  - `sustur` — timeout (10m, 2h, 1d ... max 28 gün)
  - `sus-kaldır` — timeout kaldır
- `/ihlal` grubu
  - `listele` — infraction geçmişi
  - `sil` — infraction temizle

### Müzik (`/müzik` grubu)
- `çal` — YouTube'dan veya Spotify'dan çal
  - Tekil şarkı (arama metni, YouTube URL, Spotify track)
  - YouTube playlist
  - Spotify album / playlist → YouTube bridge
- `ara` — 5 sonuç listele, buton ile seç
- `atla`, `duraklat`, `devam`, `dur`
- `ses` — 0-200%
- `sıra`, `sıra-sil`, `karıştır`
- `döngü`, `şimdi` (şu an çalan)
- PlayerView butonları: ⏮️ yeniden-başlat, ⏯️ duraklat/devam, ⏭️ atla, ⏹️ dur, 🔁 döngü, 🔉/🔊 ses, 🔀 karıştır, 📜 sözler, 📋 sıra

### Eğlence / Oyunlar
- `/yazıtura` — yazı tura (spin animasyon + GIF)
- `/zar` — özelleştirilebilir zar (1-10 adet, 2-100 yüz)
- `/8top` — sihirli 8-top
- `/tkm` — taş kağıt makas (PvP veya bot, ilk 2 galibiyet)
- `/adamasmaca` — harf/kelime modal tahmin
- `/kaccm` — bilimsel pipi ölçümü
- `/arena` — PvP dövüş (Kılıç / Büyü / Kalkan, 150 HP, max 20 tur)
- `/isimşehir`, `/vampirköylü`, `/rusruleti` — party oyunları

### Sosyal
- `/anket` — interaktif butonlu anket (max 5 seçenek, canlı sonuç barları)
- `/etkinlik` — Discord scheduled event oluşturma + duyuru kanalı

### Özel Komutlar
- `/komut-yarat` — özel komut oluştur (Sunucuyu Yönet)
- `/komut-liste` — tüm özel komutlar
- `/komut-sil` — özel komut sil
- `/komut` — özel komutu çalıştır (autocomplete destekli)

### Yayın & Mesajlaşma
- `/yaz` — kanala bot mesajı (modal)
- `/embed` — kanala V2 embed (renk seçimli, modal)
- `/duyuru` — duyuru mesajı + ping (modal)
- `/hatırlat` — DM hatırlatma (1-1440 dakika)

### Yönetim
- `/tazele` — slash komut senkronizasyonu (administrator)
- `/restart` — bot yeniden başlatma (administrator)

### Araçlar
- `/yardım` — tam komut listesi
- `/ping` — WebSocket + roundtrip latency kartı
- `/profil` — kullanıcı profili (roller, boost, join date)
- `/sunucu` — sunucu bilgisi (member cache tabanlı)
- `/avatar` — avatar + format linkleri (PNG/JPG/WEBP)
- `/bot` — uptime, sunucu/üye sayısı, discord.py sürümü

### Spor
- `/lig` grubu — Trendyol Süper Lig
  - `sıralama` — puan tablosu (zon, form, averaj)
  - `takvim` — önümüzdeki maçlar
  - `sonuçlar` — son sonuçlar
  - `canlı` — anlık skorlar (60s cache)

### Sunucu Araçları
- `/emoji-ekle` — başka sunucudan özel emoji çalar (`<:isim:ID>` formatı)
- `/oto-emoji` — mesajlardaki yabancı emojileri otomatik ekleme (aç/kapa)
- Sağ tık → **Emojileri Ekle** context menu — mesajdaki tüm yabancı emojileri toplu ekle
- Sağ tık → **Sticker'ı Ekle** context menu — mesajdaki sticker'ı sunucuya ekle (`server/sticker.py`)

### Loglar
- Sunucu logları: kanal/rol oluşturma-silme, sunucu güncelleme, davet linkleri, emoji/sticker değişimi
- Üye logları: katılma/ayrılma, ban/unban, timeout, rol değişimi, nick değişimi
- Mesaj logları: silme, düzenleme
- Ses logları: kanala katılma/ayrılma, değiştirme, mute/deafen
- Log kanalı: `LOG_CHANNEL_ID` env değişkeni ile ayarlanır

## Kapsam Dışı
- Levels / XP sistemi
- Economy sistemi (coins, shop, items)
- Web dashboard
- Prefix komutlar
- SoundCloud entegrasyonu (Spotify sadece metadata → YouTube bridge)
