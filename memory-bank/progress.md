# Progress

## Çalışan Özellikler (v1.0)

### ✅ Temel Altyapı
- Bot başlatma, cog yükleme, slash command sync
- SQLite async veritabanı (WAL mode)
- .env ile güvenli token yönetimi
- Logging (konsol + bot.log)

### ✅ Moderasyon (`/moderatör`)
- temizle, at, yasakla, sustur, sustu-kaldır
- ihlaller, ihlal-temizle
- Role hiyerarşi kontrolü
- Infraction DB kaydı

### ✅ Müzik (`/müzik`)
- çal (URL veya arama), ara (5 sonuç + buton seçimi)
- atla, duraklat, devam, dur
- ses (0-200%), sıra, sıra-temizle, döngü
- Guild başına ayrı player state

### ✅ Eğlence
- yazıtura, zar (özelleştirilebilir)
- anket (max 5 seçenek, butonlu, canlı sonuç)
- etkinlik (tarih/saat/konum, katılım butonu)

### ✅ Özel Komutlar
- komutyarat, komutlistele, komutsil, komut
- Autocomplete desteği
- Guild başına izole

### ✅ Araçlar
- yardım, kullanici-bilgi, sunucu-bilgi

## Yapılmadı / Planlı Değil
- Levels / XP
- Economy
- Web dashboard
- Spotify / SoundCloud

## Bilinen Sorunlar
- SearchView callback'inde `cal.callback()` doğrudan çağrısı test edilmeli
- Playlist desteği yok (yt-dlp `extract_flat` şu an sadece ilk sonucu alıyor)
