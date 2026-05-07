# Active Context

## Mevcut Durum
v1.2 tamamlandı. Trendyol Süper Lig komut takımı eklendi.

## Son Yapılanlar (v1.2)
- `cogs/sports/superlig.py` oluşturuldu:
  - `/lig sıralama` — puan tablosu (zon renkleri, form, averaj)
  - `/lig takvim` — önümüzdeki maçlar hafta gruplu, Discord timestamps
  - `/lig sonuçlar` — son sonuçlar, kazanan kalın
  - `/lig canlı` — anlık skorlar (60s cache)
  - api-football.com entegrasyonu, 5dk TTL cache, API key eksikse bilgilendirici hata kartı
- `.env.example` güncellendi: `FOOTBALL_API_KEY` eklendi
- memory-bank güncellendi

## Son Yapılanlar (v1.1 — önceki)
- `cogs/music.py` tamamen yeniden yazıldı:
  - Playlist desteği (YouTube playlist URL, max 100 şarkı)
  - Lazy stream URL resolution: track URL'leri çalınmadan hemen önce çözümlenir
  - Yeni `/müzik şimdi-çalıyor` komutu
  - Döngü modunda stream URL yeniden çözümlenir (süresi dolmuş URL sorunu çözüldü)
  - `/müzik ara` → SearchView buton callback düzeltildi
- `cogs/utility.py` güncellendi:
  - `/ping` — WebSocket gecikmesi
  - `/avatar` — kullanıcı avatarı (PNG/JPG/WEBP linkleri)
  - `/bot-bilgi` — uptime, sunucu sayısı, üye sayısı, gecikme
  - `/komuttazele` — administrator yetkisiyle manuel slash command sync
- `README.md` oluşturuldu (Windows + Ubuntu kurulum kılavuzu)
- GitHub: https://github.com/batuhanbecel/horoz-bot

## Komutların Tam Listesi
### /moderatör (grup)
temizle, at, yasakla, sustur, sustu-kaldır, ihlaller, ihlal-temizle

### /müzik (grup)
çal (tekil + playlist), ara, atla, duraklat, devam, dur, ses, sıra, sıra-temizle, döngü, şimdi-çalıyor

### Eğlence
/yazıtura, /zar, /anket, /etkinlik

### Özel Komutlar
/komutyarat, /komutlistele, /komutsil, /komut (autocomplete)

### Araçlar
/yardım, /ping, /kullanici-bilgi, /sunucu-bilgi, /avatar, /bot-bilgi, /komuttazele

## Sonraki Olası Geliştirmeler
- Moderasyon log kanalı (kick/ban/mute olaylarını bir kanala gönder)
- Custom commands için embed desteği
- `/moderatör yasakla` ID ile ban (sunucuda olmayan kullanıcı)
- Müzik: `/müzik sıra` için pagination (10'dan fazla şarkı için butonlu sayfalama)
