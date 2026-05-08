# Progress

## Çalışan Özellikler (v1.2+)

### ✅ Temel Altyapı
- Bot başlatma, cog yükleme, slash command sync
- SQLite async veritabanı (WAL mode)
- .env ile güvenli token yönetimi
- Logging (konsol + bot.log)
- Components V2 raw-API renderer (`cogs/_v2.py`)

### ✅ Moderasyon
- `/kanal temizle`, `/kanal yavaşmod`, `/kanal kilitle`, `/kanal kilit-aç`
- `/üye uyar`, `/üye at`, `/üye yasakla`, `/üye sustur`, `/üye sus-kaldır`
- `/ihlal listele`, `/ihlal sil`
- Role hiyerarşi kontrolü, infraction DB kaydı, audit-log bazlı loglar

### ✅ Müzik
- `/müzik çal`: tekil şarkı, YouTube playlist, Spotify track/album/playlist → YouTube bridge
- `/müzik ara`: 5 sonuç listele, SearchView buton seçimi
- `/müzik atla`, `duraklat`, `devam`, `dur`, `ses`, `sıra`, `sıra-sil`, `karıştır`, `döngü`, `şimdi`
- Lazy stream URL resolution, loop'ta URL yenileme
- PlayerView butonları: yeniden-çal, duraklat/devam, atla, dur, döngü, ses+/-, karıştır, sözler, sıra

### ✅ Eğlence / Oyunlar
- `/yazıtura`, `/zar`, `/8top`, `/kaccm`
- `/tkm` — PvP veya bot, ilk 2 galibiyet
- `/adamasmaca` — modal harf/kelime tahmini
- `/arena` — PvP dövüş (Kılıç/Büyü/Kalkan, 150 HP, max 20 tur)
- `/isimşehir`, `/vampirköylü`, `/rusruleti`

### ✅ Sosyal
- `/anket` — butonlu, canlı barlı
- `/etkinlik` — scheduled event + duyuru kanalı

### ✅ Özel Komutlar
- `/komut-yarat`, `/komut-liste`, `/komut-sil`, `/komut` (autocomplete)

### ✅ Yayın & Mesajlaşma
- `/yaz` — kanala bot mesajı (modal)
- `/embed` — V2 embed (renk seçimli, modal)
- `/duyuru` — duyuru + ping (modal)
- `/hatırlat` — DM hatırlatma (1-1440 dk, async task)

### ✅ Yönetim
- `/tazele` — slash sync (administrator)
- `/restart` — bot yeniden başlatma

### ✅ Araçlar
- `/yardım`, `/ping`, `/profil`, `/sunucu`, `/avatar`, `/bot`

### ✅ Spor — Trendyol Süper Lig (`/lig`)
- `sıralama`, `takvim`, `sonuçlar`, `canlı`
- api-football.com, 5dk cache (canlı 60s)

### ✅ Sunucu Araçları
- `/emoji-ekle` — başka sunucudan özel emoji çalar (`<:isim:ID>`)
- `/oto-emoji` — yabancı emojileri otomatik ekleme (aç/kapa, `guild_settings` tabanlı)
- Sağ tık context menu: **Emojileri Ekle**, **Sticker'ı Ekle**

### ✅ Loglar
- Sunucu logları: kanal/rol oluşturma-silme, sunucu güncelleme, davet, emoji/sticker
- Üye logları: katılma/ayrılma, ban/unban, timeout, rol değişimi, nick değişimi
- Mesaj logları: silme, düzenleme
- Ses logları: kanala katılma/ayrılma, değiştirme, mute/deafen
- Log kanalı env tabanlı (`LOG_CHANNEL_ID`)

### ✅ Dokümantasyon
- README.md: Windows + Ubuntu kurulum kılavuzu
- memory-bank: AGENTS.md uyumlu dokümantasyon

## Yapılmadı / Planlı Değil
- Levels / XP sistemi
- Economy sistemi
- Web dashboard

## Bilinen Kısıtlar
- Playlist desteği sadece YouTube (yt-dlp genel URL desteği var ama test edilmedi)
- Sıra görünümü 10 şarkı ile sınırlı (pagination yok)
- Spotify entegrasyonu sadece metadata → YouTube bridge (direkt çalma yok)
