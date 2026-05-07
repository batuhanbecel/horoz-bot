# Progress

## Çalışan Özellikler (v1.1)

### ✅ Temel Altyapı
- Bot başlatma, cog yükleme, slash command sync
- SQLite async veritabanı (WAL mode)
- .env ile güvenli token yönetimi
- Logging (konsol + bot.log)

### ✅ Moderasyon (`/moderatör`)
- temizle, at, yasakla, sustur, sustu-kaldır
- ihlaller, ihlal-temizle
- Role hiyerarşi kontrolü, infraction DB kaydı

### ✅ Müzik (`/müzik`) — v1.1 güncellendi
- çal: tekil şarkı (URL veya arama) + YouTube playlist desteği
- ara: 5 sonuç listele, buton ile seç
- atla, duraklat, devam, dur
- ses (0-200%), sıra (ilk 10 + footer), sıra-temizle, döngü
- şimdi-çalıyor: mevcut şarkı + döngü/ses durumu
- Lazy stream URL resolution (süresi dolmuş URL otomatik yenilenir)
- Playlist: max 100 şarkı, flat extraction + lazy resolve

### ✅ Eğlence
- yazıtura, zar (özelleştirilebilir)
- anket (max 5 seçenek, butonlu, canlı sonuç)
- etkinlik (tarih/saat/konum, katılım butonu)

### ✅ Özel Komutlar
- komutyarat, komutlistele, komutsil, komut
- Autocomplete desteği, guild izolasyonu

### ✅ Araçlar — v1.1 güncellendi
- yardım, kullanici-bilgi, sunucu-bilgi
- ping (WebSocket latency + renk)
- avatar (PNG/JPG/WEBP format linkleri)
- bot-bilgi (uptime, sunucu/üye sayısı, gecikme)
- komuttazele (administrator → manuel slash sync)

### ✅ Dokümantasyon
- README.md: Windows + Ubuntu kurulum kılavuzu
- memory-bank: AGENTS.md uyumlu tam dokümantasyon

### ✅ Spor — Trendyol Süper Lig (`/lig`) — v1.2
- `/lig sıralama` — tam puan tablosu (sıra, puan, G/B/M, averaj, zon rengi, form)
- `/lig takvim` — önümüzdeki 30 gündeki maçlar, hafta gruplu, Discord timestamp
- `/lig sonuçlar` — son 15 tamamlanmış maç, hafta gruplu, kazanan kalın
- `/lig canlı` — devam eden maçlar ve anlık skor (60s cache)
- API: api-football.com (FOOTBALL_API_KEY env), 5dk cache (canlı 60s)

## Yapılmadı / Planlı Değil
- Levels / XP sistemi
- Economy sistemi
- Web dashboard
- Spotify / SoundCloud

## Bilinen Kısıtlar
- Playlist desteği sadece YouTube (yt-dlp genel URL desteği var ama test edilmedi)
- Sıra görünümü 10 şarkı ile sınırlı (pagination yok)
- Moderasyon log kanalı yok
