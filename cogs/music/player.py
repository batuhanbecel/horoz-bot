import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import random
from collections import deque
from ._shared import (
    YTDL_FLAT_OPTIONS, YTDL_STREAM_OPTIONS, FFMPEG_OPTIONS, MAX_PLAYLIST,
    Track, GuildPlayer, duration_fmt, is_url, is_playlist_url, yt_thumbnail,
    detect_platform, now_playing_card,
)
from .spotify import is_spotify_url, is_spotify_collection, fetch_spotify_tracks, format_query
from .views import PlayerView, SearchView
from .._v2 import (
    COLORS, c_text, c_section, c_thumbnail, c_separator, c_container,
    c_card, c_action_card, c_list_card,
    channel_send as v2_channel_send, followup as v2_followup, respond,
    msg_edit as v2_msg_edit,
)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: dict[int, GuildPlayer] = {}

    def get_player(self, guild_id: int) -> GuildPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = GuildPlayer()
        return self.players[guild_id]

    async def ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        # interaction.user Member olmalı (guild_only komut)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None or not member.voice or not member.voice.channel:
            await respond(interaction,
                c_card("## ❌ Ses Kanalı Gerekli", body="Bir ses kanalında olmanız gerekiyor."),
                ephemeral=True,
            )
            return None

        target_channel = member.voice.channel
        # Bot'un ses kanalına bağlanma yetkisi var mı?
        perms = target_channel.permissions_for(interaction.guild.me)
        if not (perms.connect and perms.speak):
            await respond(interaction,
                c_card(
                    "## ❌ Botun Ses Yetkisi Yok",
                    body=f"Botun {target_channel.mention} kanalına bağlanma + konuşma yetkisi gerekiyor.",
                ),
                ephemeral=True,
            )
            return None

        vc: discord.VoiceClient = interaction.guild.voice_client  # type: ignore[assignment]
        try:
            if vc is None:
                vc = await target_channel.connect()
            elif vc.channel != target_channel:
                await vc.move_to(target_channel)
        except discord.ClientException as ex:
            await respond(interaction,
                c_card("## ❌ Ses Bağlantısı Hatası", body=f"```{ex}```"),
                ephemeral=True,
            )
            return None
        except (discord.Forbidden, discord.HTTPException) as ex:
            await respond(interaction,
                c_card("## ❌ Bağlantı Başarısız", body=f"```{ex}```"),
                ephemeral=True,
            )
            return None
        return vc

    async def resolve_stream_url(self, track: Track) -> bool:
        if track.stream_url:
            return True
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_STREAM_OPTIONS) as ydl:
                info = ydl.extract_info(track.webpage_url, download=False)
                return info.get("url"), info.get("duration", 0), info.get("title", track.title)

        try:
            stream_url, duration, title = await loop.run_in_executor(None, _fetch)
            track.stream_url = stream_url
            track.duration = duration
            track.title = title
            return bool(stream_url)
        except Exception:
            return False

    async def fetch_single(self, query: str, requester: discord.Member) -> Track | None:
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_STREAM_OPTIONS) as ydl:
                search = f"ytsearch:{query}" if not is_url(query) else query
                info = ydl.extract_info(search, download=False)
                if not info:
                    return None
                if "entries" in info:
                    entries = info.get("entries") or []
                    if not entries:
                        return None
                    info = entries[0]
                return info

        try:
            info = await loop.run_in_executor(None, _fetch)
            if not info:
                return None
            return Track(
                title=info.get("title") or "Bilinmiyor",
                webpage_url=info.get("webpage_url") or query,
                requester=requester,
                duration=info.get("duration") or 0,
                stream_url=info.get("url"),
            )
        except Exception as e:
            print(f"[fetch_single] Hata: {e}")
            return None

    async def fetch_playlist(self, url: str, requester: discord.Member) -> list[Track]:
        loop = asyncio.get_running_loop()

        def _fetch():
            with yt_dlp.YoutubeDL(YTDL_FLAT_OPTIONS) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await loop.run_in_executor(None, _fetch)
        except Exception as e:
            print(f"[fetch_playlist] Hata: {e}")
            return []

        if not info:
            return []
        entries = (info.get("entries") or [])[:MAX_PLAYLIST]
        tracks = []
        for e in entries:
            if not e:
                continue
            vid_id = e.get("id", "")
            webpage = (
                e.get("webpage_url")
                or e.get("url")
                or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
            )
            if not webpage:
                continue
            tracks.append(Track(
                title=e.get("title", "Bilinmiyor"),
                webpage_url=webpage,
                requester=requester,
                duration=e.get("duration", 0),
                stream_url=None,
            ))
        return tracks

    # ── Playback engine ────────────────────────────────────────────────────────

    def play_next(self, guild_id: int, vc: discord.VoiceClient):
        asyncio.run_coroutine_threadsafe(self._play_next(guild_id, vc), self.bot.loop)

    async def _play_next(self, guild_id: int, vc: discord.VoiceClient):
        if not vc.is_connected():
            return
        player = self.get_player(guild_id)

        if player.loop and player.current and not player.force_next:
            track = player.current
            track.stream_url = None
        elif player.queue:
            player.force_next = False
            if player.current:
                player.history.append(player.current)
            track = player.queue.popleft()
            player.current = track
        else:
            player.current = None
            await self._clear_player_message(player)
            await vc.disconnect()
            return

        ok = await self.resolve_stream_url(track)
        if not ok:
            await self._play_next(guild_id, vc)
            return

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTIONS),
            volume=player.volume,
        )
        vc.play(source, after=lambda e: self.play_next(guild_id, vc))
        player.paused = False
        await self._send_player_message(guild_id, track, player)

    async def _send_player_message(self, guild_id: int, track: Track, player: GuildPlayer):
        await self._clear_player_message(player)
        if not player.text_channel_id:
            return
        channel = self.bot.get_channel(player.text_channel_id)
        if not channel:
            return
        try:
            player.player_message = await v2_channel_send(
                channel,
                now_playing_card(track, player),
                view=PlayerView(self, guild_id),
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def _clear_player_message(self, player: GuildPlayer):
        if player.player_message:
            try:
                await player.player_message.delete()
            except (discord.NotFound, discord.HTTPException):
                pass
            player.player_message = None

    async def _refresh_player_message(self, guild_id: int) -> bool:
        """Mevcut player mesajını now_playing_card ile günceller. Aktif kart yoksa False."""
        p = self.get_player(guild_id)
        if not p.current or not p.player_message:
            return False
        try:
            await v2_msg_edit(p.player_message, now_playing_card(p.current, p), view=PlayerView(self, guild_id))
            return True
        except (discord.HTTPException, discord.NotFound):
            return False

    # ── Track card builder ─────────────────────────────────────────────────────

    def _track_card(self, title: str, track: Track, *, status: str = "", color: int = COLORS.MUSIC, queue_pos: int | None = None) -> dict:
        """Tek şarkı için tutarlı kart düzeni: section + thumbnail + meta."""
        thumb = yt_thumbnail(track.webpage_url) or str(track.requester.display_avatar.url)
        meta_lines = [
            f"⏱️ **Süre:** `{duration_fmt(track.duration)}`",
            f"👤 **İsteyen:** {track.requester.mention}",
        ]
        if queue_pos is not None:
            meta_lines.append(f"📋 **Sırada:** `#{queue_pos}`")
        if status:
            meta_lines.append(status)

        return c_container(
            c_section(
                c_text(f"## {title}\n### [{track.title}]({track.webpage_url})"),
                accessory=c_thumbnail(thumb),
            ),
            c_separator(),
            c_text("\n".join(meta_lines)),
            color=color,
        )

    # ── Commands ───────────────────────────────────────────────────────────────

    music = app_commands.Group(
        name="müzik",
        description="Müzik komutları",
        guild_only=True,
    )

    @music.command(name="çal", description="Şarkı adı, YouTube/Spotify URL'si veya playlist çalar.")
    @app_commands.describe(sorgu="Şarkı adı, YouTube/Spotify linki veya playlist")
    async def cal(self, interaction: discord.Interaction, sorgu: str):
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        await interaction.response.defer()
        player = self.get_player(interaction.guild_id)
        player.text_channel_id = interaction.channel_id
        is_playing_now = vc.is_playing() or vc.is_paused()

        # ── Spotify URL: track / album / playlist ────────────────────────
        if is_url(sorgu) and is_spotify_url(sorgu):
            queries = await fetch_spotify_tracks(sorgu)
            if not queries:
                from .spotify import is_available
                msg = ("Spotify entegrasyonu yapılandırılmamış. `SPOTIFY_CLIENT_ID` ve "
                       "`SPOTIFY_CLIENT_SECRET` env değişkenleri eksik.") if not is_available() \
                      else "Spotify track/album/playlist alınamadı veya boş."
                return await v2_followup(interaction,
                    c_card("## ❌ Spotify Hatası", body=msg),
                )

            collection = is_spotify_collection(sorgu)

            if not collection:
                # Tek şarkı — YouTube'da ara, Spotify metadata bağla
                artist, title = queries[0]
                yt_query = format_query(artist, title)
                track = await self.fetch_single(yt_query, interaction.user)
                if not track:
                    return await v2_followup(interaction,
                        c_card("## ❌ Şarkı Bulunamadı", body=f"`{title}` Spotify'da bulundu ama YouTube'da arama başarısız."),
                    )
                track.platform = "spotify"
                track.source_url = sorgu
                track.title = f"{artist} - {title}" if artist else title

                if is_playing_now:
                    player.queue.append(track)
                    await v2_followup(interaction, self._track_card(
                        "📋 Sıraya Eklendi (🟢 Spotify)",
                        track,
                        queue_pos=len(player.queue),
                    ))
                else:
                    player.queue.appendleft(track)
                    await self._play_next(interaction.guild_id, vc)
                    await v2_followup(interaction, self._track_card(
                        "✅ Çalmaya Başlıyor (🟢 Spotify)",
                        track,
                    ))
                return

            # Album / Playlist — paralel YouTube araması yap
            queries = queries[:MAX_PLAYLIST]
            tracks: list[Track] = []
            for artist, title in queries:
                yt_query = format_query(artist, title)
                t = await self.fetch_single(yt_query, interaction.user)
                if t:
                    t.platform = "spotify"
                    t.source_url = sorgu
                    t.title = f"{artist} - {title}" if artist else title
                    tracks.append(t)

            if not tracks:
                return await v2_followup(interaction,
                    c_card("## ❌ Playlist Boş", body="Spotify'dan şarkılar alındı ama YouTube'da hiçbiri bulunamadı."),
                )

            for t in tracks:
                player.queue.append(t)

            total_dur = sum(t.duration for t in tracks)
            title_str = "✅ Spotify Yüklendi" if not is_playing_now else "📋 Spotify Sıraya Eklendi"

            await v2_followup(interaction, c_action_card(
                title_str,
                target_avatar=str(interaction.user.display_avatar.url),
                fields=[
                    ("🎧 Kaynak", "🟢 Spotify"),
                    ("🎵 Şarkı Sayısı", f"`{len(tracks)}` / `{len(queries)}` (YT'de bulunan)"),
                    ("⏱️ Toplam Süre", f"`{duration_fmt(total_dur)}`"),
                    ("👤 İsteyen", interaction.user.mention),
                ],
            ))

            if not is_playing_now:
                await self._play_next(interaction.guild_id, vc)
            return

        # ── YouTube playlist ────────────────────────────────────────────
        if is_url(sorgu) and is_playlist_url(sorgu):
            tracks = await self.fetch_playlist(sorgu, interaction.user)
            if not tracks:
                return await v2_followup(interaction,
                    c_card("## ❌ Playlist Bulunamadı", body="Playlist boş veya erişilemez."),
                )
            for t in tracks:
                t.platform = detect_platform(t.webpage_url)
                player.queue.append(t)

            total_dur = sum(t.duration for t in tracks)
            title = "✅ Playlist Yüklendi" if not is_playing_now else "📋 Playlist Sıraya Eklendi"

            await v2_followup(interaction, c_action_card(
                title,
                target_avatar=str(interaction.user.display_avatar.url),
                fields=[
                    ("🎵 Şarkı Sayısı", f"`{len(tracks)}`"),
                    ("⏱️ Toplam Süre", f"`{duration_fmt(total_dur)}`"),
                    ("👤 İsteyen", interaction.user.mention),
                ],
            ))

            if not is_playing_now:
                await self._play_next(interaction.guild_id, vc)
            return

        # ── Tek YouTube/diğer şarkı veya arama metni ────────────────────
        track = await self.fetch_single(sorgu, interaction.user)
        if not track:
            return await v2_followup(interaction,
                c_card("## ❌ Şarkı Bulunamadı", body=f"`{sorgu}` için sonuç yok."),
            )
        track.platform = detect_platform(track.webpage_url)

        if is_playing_now:
            player.queue.append(track)
            await v2_followup(interaction, self._track_card(
                "📋 Sıraya Eklendi",
                track,
                queue_pos=len(player.queue),
            ))
        else:
            player.queue.appendleft(track)
            await self._play_next(interaction.guild_id, vc)
            await v2_followup(interaction, self._track_card(
                "✅ Çalmaya Başlıyor",
                track,
            ))

    @music.command(name="ara", description="YouTube'da şarkı arar ve 5 sonuç listeler.")
    @app_commands.describe(sorgu="Aranacak şarkı")
    async def ara(self, interaction: discord.Interaction, sorgu: str):
        await interaction.response.defer(ephemeral=True)
        loop = asyncio.get_running_loop()

        def _search():
            opts = dict(YTDL_FLAT_OPTIONS)
            opts["noplaylist"] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(f"ytsearch5:{sorgu}", download=False)

        try:
            info = await loop.run_in_executor(None, _search)
        except Exception as e:
            return await v2_followup(interaction,
                c_card("## ❌ Arama Hatası", body=f"```{e}```"),
                ephemeral=True,
            )

        entries = [e for e in (info or {}).get("entries", []) if e][:5]

        if not entries:
            return await v2_followup(interaction,
                c_card("## ❌ Sonuç Bulunamadı", body=f"`{sorgu}` için sonuç yok."),
                ephemeral=True,
            )

        rows = []
        for i, e in enumerate(entries, 1):
            url = e.get("url") or f"https://www.youtube.com/watch?v={e.get('id', '')}"
            title = e.get("title", "Bilinmiyor")
            dur = duration_fmt(e.get("duration", 0))
            rows.append(f"`#{i}` **[{title}]({url})**\n┗ ⏱️ `{dur}`")

        await v2_followup(interaction, c_list_card(
            f"🔍 \"{sorgu}\" — Arama Sonuçları",
            rows=rows,
            footer="Aşağıdan butona tıklayarak sıraya ekle",
        ),
            view=SearchView(entries, interaction.user, self),
            ephemeral=True,
        )

    @music.command(name="atla", description="Mevcut şarkıyı atlar.")
    async def atla(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc or not (vc.is_playing() or vc.is_paused()):
            return await respond(interaction,
                c_card("## ❌ Hata", body="Şu anda çalan bir şey yok."),
                ephemeral=True,
            )
        p = self.get_player(interaction.guild_id)
        skipped = p.current
        p.force_next = True
        vc.stop()

        if skipped:
            await respond(interaction, self._track_card(
                "⏭️ Şarkı Atlandı",
                skipped,
            ))
        else:
            await respond(interaction,
                c_card("## ⏭️ Atlandı", body="Şarkı atlandı."),
            )

    @music.command(name="duraklat", description="Çalmayı duraklatır.")
    async def duraklat(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client  # type: ignore[assignment]
        if not vc or not vc.is_playing():
            return await respond(interaction,
                c_card("## ❌ Hata", body="Şu anda çalan bir şey yok."),
                ephemeral=True,
            )
        vc.pause()
        p = self.get_player(interaction.guild_id)
        p.paused = True
        await self._refresh_player_message(interaction.guild_id)
        await respond(interaction,
            c_card("## ⏸️ Duraklatıldı", body="Müzik duraklatıldı."),
            ephemeral=True,
        )

    @music.command(name="devam", description="Duraklatılmış müziği devam ettirir.")
    async def devam(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client  # type: ignore[assignment]
        if not vc or not vc.is_paused():
            return await respond(interaction,
                c_card("## ❌ Hata", body="Duraklatılmış bir şey yok."),
                ephemeral=True,
            )
        vc.resume()
        p = self.get_player(interaction.guild_id)
        p.paused = False
        await self._refresh_player_message(interaction.guild_id)
        await respond(interaction,
            c_card("## ▶️ Devam Ediyor", body="Müzik devam ediyor."),
            ephemeral=True,
        )

    @music.command(name="dur", description="Müziği durdurur ve kanaldan ayrılır.")
    async def dur(self, interaction: discord.Interaction):
        vc: discord.VoiceClient = interaction.guild.voice_client
        if not vc:
            return await respond(interaction,
                c_card("## ❌ Hata", body="Bot bir ses kanalında değil."),
                ephemeral=True,
            )
        p = self.get_player(interaction.guild_id)
        cleared = len(p.queue)
        p.queue.clear()
        p.current = None
        p.loop = False
        await self._clear_player_message(p)
        await vc.disconnect()
        await respond(interaction, c_action_card(
            "⏹️ Müzik Durduruldu",
            fields=[
                ("🚪 Durum", "Kanaldan ayrıldım"),
                ("🧹 Temizlenen Sıra", f"`{cleared}` şarkı"),
                ("👮 İsteyen", interaction.user.mention),
            ],
        ))

    @music.command(name="ses", description="Ses seviyesini ayarlar (0-200).")
    @app_commands.describe(seviye="Ses seviyesi (0-200)")
    async def ses(self, interaction: discord.Interaction, seviye: app_commands.Range[int, 0, 200]):
        vc: discord.VoiceClient = interaction.guild.voice_client  # type: ignore[assignment]
        p = self.get_player(interaction.guild_id)
        p.volume = seviye / 100
        if vc and vc.source:
            vc.source.volume = p.volume

        await self._refresh_player_message(interaction.guild_id)

        emoji = "🔇" if seviye == 0 else "🔈" if seviye < 50 else "🔉" if seviye < 120 else "🔊"
        await respond(interaction,
            c_card(f"## {emoji} Ses Ayarlandı", body=f"Seviye **`{seviye}%`**"),
            ephemeral=True,
        )

    @music.command(name="sıra", description="Mevcut müzik sırasını gösterir.")
    async def sira(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if not p.current and not p.queue:
            return await respond(interaction,
                c_card("## 📋 Sıra Boş", body="Sıra boş — `/müzik çal` ile şarkı ekleyin."),
                ephemeral=True,
            )

        sections: list[dict] = [c_text(f"## 📋 Müzik Sırası")]

        if p.current:
            sections.append(c_separator())
            sections.append(c_text(
                f"▶️ **Şu An Çalıyor**\n"
                f"┗ [{p.current.title}]({p.current.webpage_url}) · `{duration_fmt(p.current.duration)}` · {p.current.requester.mention}"
            ))

        if p.queue:
            queue_lines = []
            for i, t in enumerate(list(p.queue)[:10], 1):
                queue_lines.append(f"`#{i:02d}` [{t.title[:60]}]({t.webpage_url})\n┗ ⏱️ `{duration_fmt(t.duration)}` · {t.requester.mention}")
            sections.append(c_separator())
            sections.append(c_text("\n".join(queue_lines)))

            if len(p.queue) > 10:
                sections.append(c_separator())
                sections.append(c_text(f"-# ve `{len(p.queue) - 10}` şarkı daha sıraya ekli..."))

        total = (p.current.duration if p.current else 0) + sum(t.duration for t in p.queue)
        sections.append(c_separator())
        sections.append(c_text(f"-# 🎵 Toplam: `{1 + len(p.queue) if p.current else len(p.queue)}` şarkı · ⏱️ `{duration_fmt(total)}`"))

        await respond(interaction, c_container(*sections))

    @music.command(name="sıra-sil", description="Müzik sırasını temizler.")
    async def sira_sil(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        count = len(p.queue)
        p.queue.clear()
        await self._refresh_player_message(interaction.guild_id)
        await respond(interaction,
            c_card("## 🗑️ Sıra Temizlendi", body=f"`{count}` şarkı kaldırıldı."),
            ephemeral=True,
        )

    @music.command(name="karıştır", description="Müzik sırasını rastgele karıştırır.")
    async def karistir(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if len(p.queue) < 2:
            return await respond(interaction,
                c_card("## ❌ Hata", body="Karıştırmak için en az **2 şarkı** gerekli."),
                ephemeral=True,
            )
        q = list(p.queue)
        random.shuffle(q)
        p.queue = deque(q)
        await self._refresh_player_message(interaction.guild_id)
        await respond(interaction,
            c_card("## 🔀 Sıra Karıştırıldı", body=f"`{len(q)}` şarkı rastgele sıralandı."),
            ephemeral=True,
        )

    @music.command(name="döngü", description="Döngü modunu açar/kapatır.")
    async def dongu(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        p.loop = not p.loop
        await self._refresh_player_message(interaction.guild_id)
        durum = "Açık 🔂" if p.loop else "Kapalı"
        await respond(interaction,
            c_card(f"## 🔁 Döngü {durum}"),
            ephemeral=True,
        )

    @music.command(name="şimdi", description="Şu an çalan şarkıyı gösterir.")
    async def simdi(self, interaction: discord.Interaction):
        p = self.get_player(interaction.guild_id)
        if not p.current:
            return await respond(interaction,
                c_card("## 🎵 Şu An Çalmıyor", body="Şu an çalan bir şey yok."),
                ephemeral=True,
            )
        await respond(interaction,
            now_playing_card(p.current, p),
            view=PlayerView(self, interaction.guild_id),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
