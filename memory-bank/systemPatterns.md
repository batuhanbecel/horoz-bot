# System Patterns

## Mimari
- **Cog tabanlı modüler yapı**: Her özellik grubu ayrı bir cog dosyası
- `main.py` tüm cog'ları yükler ve slash komutlarını sync eder
- `database/db.py` tüm DB işlemlerini merkezi yönetir (helper functions)

## Slash Command Grupları
discord.py'nin `app_commands.Group` kullanılır:
```python
mod = app_commands.Group(name="moderatör", description="...")
@mod.command(name="temizle", ...)
```
Böylece `/moderatör temizle`, `/müzik çal` gibi alt komutlar oluşur.

## Veritabanı Erişim Paterni
```python
async with await get_db() as db:
    await db.execute(...)
    await db.commit()
```
Her fonksiyon kendi context manager açar. Connection pooling yok (SQLite WAL mode yeterli).

## Müzik Mimarisi
- Her guild için ayrı `GuildPlayer` dataclass (queue, current, volume, loop)
- `play_next()` callback zinciri ile sıra yönetimi
- yt-dlp blocking call'lar `loop.run_in_executor(None, ...)` ile async yapılır
- FFmpeg `-reconnect` seçeneği ile stream kesilme toleransı

## Hata Yönetimi
- Her cog `cog_app_command_error` override eder
- `MissingPermissions` özel mesajla yakalanır
- Kullanıcıya her zaman ephemeral embed ile hata gösterilir

## Autocomplete
`/komut` ve `/komutsil` komutlarında DB'den dinamik autocomplete:
```python
@komut.autocomplete("isim")
async def komut_autocomplete(self, interaction, current):
    names = await db.get_command_names(interaction.guild_id)
    return [Choice(name=n, value=n) for n in names if current in n][:25]
```

## Güvenlik
- `.env` gitignore'da, token asla commit edilmez
- Moderasyon komutlarında `top_role` karşılaştırması (role hiyerarşisi)
- Custom command ismi sanitize edilir (lowercase, boşluk kaldırılır)
