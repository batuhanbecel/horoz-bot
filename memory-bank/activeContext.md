# Active Context

## Mevcut Durum
v1.2+ tamamlandı. Trendyol Süper Lig komut takımı, arena oyunları, mesajlaşma araçları ve log sistemi eklendi.

## Son Yapılanlar (v1.2+)
- `cogs/sports/superlig.py` oluşturuldu:
  - `/lig sıralama`, `/lig takvim`, `/lig sonuçlar`, `/lig canlı`
  - api-football.com entegrasyonu, 5dk TTL cache
- `cogs/fun/arena.py` — PvP dövüş (Kılıç/Büyü/Kalkan, 150 HP, max 20 tur)
- `cogs/utility/messaging.py` — `/yaz`, `/embed`, `/duyuru`, `/hatırlat`
- `cogs/server/` log cogs — guild, member, message, voice logları
- `cogs/fun/social.py` — `/anket`, `/etkinlik` (scheduled event + duyuru)
- `cogs/fun/games.py` — `/tkm`, `/adamasmaca`, `/8top`, `/kaccm`
- `cogs/_v2.py` — Components V2 raw-API renderer

## Son Yapılanlar (v1.1 — önceki)
- Müzik tamamen yeniden yazıldı: playlist, lazy stream URL, döngü, Spotify bridge
- `cogs/utility/info.py` — `/ping`, `/avatar`, `/bot`, `/profil`, `/sunucu`
- `cogs/utility/admin.py` — `/yardım`, `/tazele`, `/restart`

## Komutların Tam Listesi

### Moderasyon
- `/kanal temizle`, `/kanal yavaşmod`, `/kanal kilitle`, `/kanal kilit-aç`
- `/üye uyar`, `/üye at`, `/üye yasakla`, `/üye sustur`, `/üye sus-kaldır`
- `/ihlal listele`, `/ihlal sil`

### Müzik
- `/müzik çal`, `/müzik ara`, `/müzik atla`, `/müzik duraklat`, `/müzik devam`, `/müzik dur`
- `/müzik ses`, `/müzik sıra`, `/müzik sıra-sil`, `/müzik karıştır`, `/müzik döngü`, `/müzik şimdi`

### Eğlence
- `/yazıtura`, `/zar`, `/8top`, `/tkm`, `/adamasmaca`, `/kaccm`, `/arena`
- `/isimşehir`, `/vampirköylü`, `/rusruleti`

### Sosyal
- `/anket`, `/etkinlik`

### Yayın & Mesajlaşma
- `/yaz`, `/embed`, `/duyuru`, `/hatırlat`

### Yönetim
- `/tazele`, `/restart`

### Araçlar
- `/yardım`, `/ping`, `/profil`, `/sunucu`, `/avatar`, `/bot`

### Özel Komutlar
- `/komut-yarat`, `/komut-liste`, `/komut-sil`, `/komut`

### Sunucu Araçları
- `/emoji-ekle` — başka sunucudan özel emoji çalar
- `/oto-emoji` — mesajlardaki yabancı emojileri otomatik ekleme (aç/kapa)
- Sağ tık → **Emojileri Ekle** context menu
- Sağ tık → **Sticker'ı Ekle** context menu

### Spor
- `/lig sıralama`, `/lig takvim`, `/lig sonuçlar`, `/lig canlı`

## Sonraki Olası Geliştirmeler
- `/üye yasakla` ID ile ban (sunucuda olmayan kullanıcı)
- Müzik: `/müzik sıra` pagination (10'dan fazla şarkı için butonlu sayfalama)
- Custom commands için embed/V2 component desteği
- `/oto-emoji` whitelist/blacklist (sunucu bazlı filtre)
- Slash command olarak `/sticker-ekle` (şu an sadece sağ tık context menu)
