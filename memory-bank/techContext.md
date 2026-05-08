# Tech Context

## Stack
- **Python 3.11+**
- **discord.py 2.4+** — `app_commands` ile native slash commands
- **yt-dlp** — YouTube ses akışı
- **FFmpeg** — ses encode/decode (sistem kurulumu gerekir)
- **aiosqlite** — async SQLite veritabanı
- **PyNaCl** — Discord voice şifreleme
- **python-dotenv** — .env yönetimi
- **spotipy** — Spotify metadata → YouTube bridge
- **aiohttp** — HTTP istemcisi (API, Giphy)
- **Pillow** — resim işleme

## Proje Yapısı
```
horoz_bot/
├── main.py                  # Bot entry point, auto cog loader
├── .env                     # Gizli (gitignore'da)
├── .env.example             # Şablon
├── requirements.txt
├── .gitignore
├── bot.log                  # Runtime log
├── cogs/
│   ├── _v2.py               # Components V2 raw-API renderer
│   ├── moderation/
│   │   ├── channel.py       # /kanal temizle, yavaşmod, kilitle
│   │   ├── member.py        # /üye uyar, at, yasakla, sustur, sus-kaldır
│   │   ├── infraction.py    # /ihlal listele, sil
│   │   └── _shared.py       # parse_duration, hierarchy_ok
│   ├── music/
│   │   ├── player.py        # /müzik çal, ara, atla, duraklat, devam, dur, ses, sıra...
│   │   ├── spotify.py       # Spotify metadata → YouTube bridge
│   │   ├── views.py         # PlayerView, SearchView
│   │   ├── lyrics.py        # lyrics.ovh entegrasyonu
│   │   └── _shared.py       # Track, GuildPlayer, yt-dlp opts
│   ├── fun/
│   │   ├── games.py         # /yazıtura, /zar, /8top, /tkm, /adamasmaca, /kaccm
│   │   ├── social.py        # /anket, /etkinlik
│   │   ├── arena.py         # /arena PvP dövüş
│   │   ├── isim_sehir.py    # /isimşehir
│   │   ├── vampir_koylu.py  # /vampirköylü
│   │   ├── rus_ruleti.py    # /rusruleti
│   │   ├── _render.py, _shared.py
│   │   └── ...
│   ├── utility/
│   │   ├── info.py          # /ping, /avatar, /bot, /profil, /sunucu
│   │   ├── admin.py         # /yardım, /tazele, /restart
│   │   ├── messaging.py     # /yaz, /embed, /duyuru, /hatırlat
│   │   └── _shared.py       # Modal builders, renk map
│   ├── server/
│   │   ├── custom_commands.py   # /komut-yarat, /komut-liste, /komut-sil, /komut
│   │   ├── emoji.py, sticker.py
│   │   ├── guild_logs.py, member_logs.py, message_logs.py, voice_logs.py
│   │   └── _shared.py       # LogBase, get_audit, LOG_CHANNEL_ID
│   └── sports/
│       └── superlig.py      # /lig sıralama, takvim, sonuçlar, canlı
├── database/
│   ├── db.py                # SQLite init + CRUD helpers
│   └── bot.db               # Auto-created (gitignore'da)
└── memory-bank/             # AGENTS.md dokümantasyonu
```

## Environment Variables
| Değişken | Açıklama |
|---|---|
| `DISCORD_TOKEN` | Bot token (Discord Developer Portal) |
| `GUILD_ID` | Ana sunucu ID (opsiyonel) |
| `SPOTIFY_CLIENT_ID` | Spotify API client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify API client secret |
| `FOOTBALL_API_KEY` | api-football.com API key |
| `GIPHY_API_KEY` | Giphy API key (opsiyonel, GIF komutları) |
| `LOG_CHANNEL_ID` | Log mesajlarının gönderileceği kanal ID |
| `WELCOME_CHANNEL_ID` | Hoş geldin/ayrılma mesaj kanalı ID (opsiyonel) |
| `LEAVE_EMOJI_ID` | Ayrılma mesajında kullanılacak custom emoji ID (opsiyonel) |

## Geliştirme Ortamı
- OS: Windows 11
- Shell: PowerShell
- FFmpeg: PATH'e eklenmiş olmalı

## Production (Ubuntu)
```bash
sudo apt install ffmpeg python3.11 python3-pip -y
pip install -r requirements.txt
python main.py
# veya systemd service ile
```

## Discord Bot Ayarları (Developer Portal)
Gerekli Intents:
- Server Members Intent ✅
- Message Content Intent ✅
- Presence Intent (isteğe bağlı)

Gerekli Permissions:
- `manage_messages`, `kick_members`, `ban_members`, `moderate_members`
- `manage_channels`, `manage_roles`, `manage_events`, `manage_guild`
- `connect`, `speak` (voice)
- `manage_emojis_and_stickers`, `read_message_history`

## Veritabanı Şeması
```sql
infractions (id, guild_id, user_id, mod_id, reason, type, created_at)
custom_commands (id, guild_id, name, response, created_by, created_at)
mutes (guild_id, user_id, unmute_at)
guild_settings (guild_id, key, value)
```
