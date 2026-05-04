# Tech Context

## Stack
- **Python 3.11+**
- **discord.py 2.4+** — `app_commands` ile native slash commands
- **yt-dlp** — YouTube ses akışı
- **FFmpeg** — ses encode/decode (sistem kurulumu gerekir)
- **aiosqlite** — async SQLite veritabanı
- **PyNaCl** — Discord voice şifreleme
- **python-dotenv** — .env yönetimi

## Proje Yapısı
```
horoz_bot/
├── main.py                  # Bot entry point, cog loader
├── .env                     # Gizli (gitignore'da)
├── .env.example             # Şablon
├── requirements.txt
├── .gitignore
├── cogs/
│   ├── moderation.py        # /moderatör grubu
│   ├── music.py             # /müzik grubu + voice
│   ├── fun.py               # /yazıtura /zar /anket /etkinlik
│   ├── utility.py           # /yardım /kullanici-bilgi /sunucu-bilgi
│   └── custom_commands.py   # /komutyarat /komut vs.
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
- `connect`, `speak` (voice)
- `manage_guild` (custom commands için)

## Veritabanı Şeması
```sql
infractions (id, guild_id, user_id, mod_id, reason, type, created_at)
custom_commands (id, guild_id, name, response, created_by, created_at)
mutes (guild_id, user_id, unmute_at)  -- gelecekte kullanım için
```
