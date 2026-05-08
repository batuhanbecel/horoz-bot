# System Patterns

## Mimari
- **Cog tabanlı modüler yapı**: Her özellik grubu kendi alt-klasöründe (`moderation/`, `music/`, `fun/`, `utility/`, `server/`, `sports/`)
- `main.py` otomatik cog keşfi yapar (`discover_cogs()`): `cogs/` altındaki tüm `*.py` dosyalarını bulur (`_*` ve `views.py` hariç)
- `database/db.py` tüm DB işlemlerini merkezi yönetir (helper functions)
- **Components V2**: Tüm UI `cogs/_v2.py` üzerinden native discord.py 2.7.1 V2 sınıfları ile render edilir: `discord.ui.Container`, `TextDisplay`, `Section`, `Thumbnail`, `Separator`, `MediaGallery`, `LayoutView`. Native `to_component_dict()` / `to_components()` serialize edilir; raw dict builder kullanılmaz. Standart discord.py embed kullanılmaz.
- **Accent color policy**: `c_card`, `c_rich_card`, `c_action_card`, `c_info_card`, `c_list_card` default `color=None` (temiz container, accent bar yok). Sadece `c_error` (DANGER) ve `c_success` (SUCCESS) sabit renk taşır — hata/başarı durumlarında sol kenarlık belirgin.

## Slash Command Grupları
discord.py'nin `app_commands.Group` kullanılır:
```python
kanal = app_commands.Group(name="kanal", description="Kanal yönetim komutları", guild_only=True)
@kanal.command(name="temizle", ...)
```
Böylece `/kanal temizle`, `/üye at`, `/müzik çal` gibi alt komutlar oluşur.

## Veritabanı Erişim Paterni
```python
async with await get_db() as db:
    await db.execute(...)
    await db.commit()
```
Her fonksiyon kendi context manager açar. Connection pooling yok (SQLite WAL mode yeterli).

## Müzik Mimarisi
- Her guild için ayrı `GuildPlayer` dataclass (queue, current, volume, loop, paused, force_next, text_channel_id, player_message, history)
- `play_next()` callback zinciri ile sıra yönetimi
- yt-dlp blocking call'lar `loop.run_in_executor(None, ...)` ile async yapılır
- FFmpeg `-reconnect` seçeneği ile stream kesilme toleransı
- **Lazy stream URL resolution**: Track'ler sıraya eklenirken sadece metadata çözülür; stream URL çalmadan hemen önce resolve edilir (süresi dolmuş URL sorununu çözer)
- Spotify bridge: `spotipy` ile metadata alınır, arama sorgusu `yt-dlp` ile YouTube'da çalınır

## Hata Yönetimi
- Her cog `cog_app_command_error` override eder
- `MissingPermissions` özel mesajla yakalanır
- Kullanıcıya her zaman ephemeral V2 card ile hata gösterilir (`error_response()` helper)

## Autocomplete
`/komut` ve `/komut-sil` komutlarında DB'den dinamik autocomplete:
```python
@komut.autocomplete("isim")
async def komut_autocomplete(self, interaction, current):
    names = await db.get_command_names(interaction.guild_id)
    return [Choice(name=n, value=n) for n in names if current.lower() in n.lower()][:25]
```

## Log Mimarisi
- `server/_shared.py`'te `LogBase` base class: `LOG_CHANNEL_ID` env değişkenine göre log kanalını bulur
- Audit log tabanlı: `get_audit()` helper ile Discord audit loglarından moderatör/aktör bilgisi çekilir (0.75s gecikme ile race condition önlenir)
- Tüm loglar V2 container card olarak gönderilir

## Güvenlik
- `.env` gitignore'da, token asla commit edilmez
- Moderasyon komutlarında `top_role` karşılaştırması (role hiyerarşisi) + sunucu sahibi muafiyeti
- Custom command ismi sanitize edilir (lowercase, boşluk → `-`, max 32 karakter)
- Context menu komutları (`Emojileri Ekle`) guild-only ve yetki kontrollüdür
