# Project Brief — Horoz Bot

## Proje Özeti
Horoz Bot, Discord sunucuları için geliştirilmiş çok amaçlı bir Türkçe Discord botudur.
Tüm komutlar Discord'un native slash command (/) sistemiyle çalışır.

## Temel Gereksinimler
- Sadece slash commands (prefix yok)
- Tüm komut isimleri ve yanıtlar Türkçe
- Windows'ta geliştirme, Ubuntu'da production host
- GitHub: https://github.com/batuhanbecel/horoz-bot

## Kapsam

### Moderasyon (`/moderatör` grubu)
- `/moderatör temizle` — mesaj sil
- `/moderatör at` — kick
- `/moderatör yasakla` — ban
- `/moderatör sustur` — timeout (süre: 10m, 2h, 1d vb.)
- `/moderatör sustu-kaldır` — timeout kaldır
- `/moderatör ihlaller` — infraction geçmişi
- `/moderatör ihlal-temizle` — infraction temizle

### Müzik (`/müzik` grubu)
- `/müzik çal` — YouTube'dan çal
- `/müzik ara` — 5 sonuç göster, seç
- `/müzik atla`, `/müzik duraklat`, `/müzik devam`
- `/müzik dur`, `/müzik ses`, `/müzik sıra`, `/müzik sıra-temizle`, `/müzik döngü`

### Eğlence
- `/yazıtura` — yazı tura
- `/zar` — özelleştirilebilir zar (1-10 adet, 2-100 yüz)
- `/anket` — interaktif butonlu anket (max 5 seçenek)
- `/etkinlik` — etkinlik duyurusu + katılım butonu

### Özel Komutlar
- `/komutyarat` — özel komut oluştur (Sunucuyu Yönet yetkisi gerekir)
- `/komutlistele` — tüm özel komutlar
- `/komutsil` — özel komut sil
- `/komut` — özel komutu çalıştır (autocomplete destekli)

### Araçlar
- `/yardım`, `/kullanici-bilgi`, `/sunucu-bilgi`

## Kapsam Dışı
- Levels / XP sistemi
- Economy sistemi (coins, shop, items)
- Web dashboard
- Prefix komutlar
- Spotify / SoundCloud entegrasyonu
