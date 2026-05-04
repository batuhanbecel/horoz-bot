import discord
from discord.ext import commands
import os
from datetime import timezone

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1326534476213256192"))


def embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e


async def get_audit(guild: discord.Guild, action: discord.AuditLogAction, target_id: int = None, limit: int = 1):
    """En son audit log kaydını getirir."""
    try:
        async for entry in guild.audit_logs(action=action, limit=limit):
            if target_id is None or entry.target.id == target_id:
                return entry
    except (discord.Forbidden, discord.HTTPException):
        pass
    return None


class LogEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def log(self, guild: discord.Guild, **kwargs) -> None:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(LOG_CHANNEL_ID)
            except Exception:
                return
        try:
            await ch.send(**kwargs)
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ── Üye Katılma / Ayrılma ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        e = embed("📥 Üye Katıldı", color=discord.Color.green())
        e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
        e.add_field(name="ID", value=str(member.id), inline=True)
        created = member.created_at.replace(tzinfo=timezone.utc)
        e.add_field(name="Hesap Oluşturulma", value=f"<t:{int(created.timestamp())}:R>", inline=True)
        e.set_thumbnail(url=member.display_avatar.url)
        await self.log(member.guild, embed=e)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Kick mi yoksa gönüllü ayrılma mı?
        entry = await get_audit(member.guild, discord.AuditLogAction.kick, member.id)
        if entry and (discord.utils.utcnow() - entry.created_at).total_seconds() < 5:
            e = embed("👢 Üye Atıldı", color=discord.Color.orange())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Atan Yetkili", value=f"{entry.user.mention} `{entry.user}`", inline=True)
            e.add_field(name="Sebep", value=entry.reason or "Belirtilmedi", inline=True)
        else:
            e = embed("📤 Üye Ayrıldı", color=discord.Color.light_grey())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            roles = [r.mention for r in member.roles if r.name != "@everyone"]
            if roles:
                e.add_field(name="Rolleri", value=", ".join(roles[:10]), inline=False)
        e.add_field(name="ID", value=str(member.id), inline=True)
        e.set_thumbnail(url=member.display_avatar.url)
        await self.log(member.guild, embed=e)

    # ── Ban / Unban ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await get_audit(guild, discord.AuditLogAction.ban, user.id)
        e = embed("🔨 Üye Yasaklandı", color=discord.Color.red())
        e.add_field(name="Kullanıcı", value=f"{user.mention} `{user}`", inline=False)
        if entry:
            e.add_field(name="Yakan Yetkili", value=f"{entry.user.mention} `{entry.user}`", inline=True)
            e.add_field(name="Sebep", value=entry.reason or "Belirtilmedi", inline=True)
        e.add_field(name="ID", value=str(user.id), inline=True)
        e.set_thumbnail(url=user.display_avatar.url)
        await self.log(guild, embed=e)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        entry = await get_audit(guild, discord.AuditLogAction.unban, user.id)
        e = embed("✅ Yasak Kaldırıldı", color=discord.Color.green())
        e.add_field(name="Kullanıcı", value=f"{user.mention} `{user}`", inline=False)
        if entry:
            e.add_field(name="Kaldıran Yetkili", value=f"{entry.user.mention} `{entry.user}`", inline=True)
        e.add_field(name="ID", value=str(user.id), inline=True)
        await self.log(guild, embed=e)

    # ── Üye Güncelleme (rol, takma ad, timeout) ───────────────────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        # Timeout değişimi
        before_to = before.timed_out_until
        after_to = after.timed_out_until
        if before_to != after_to:
            if after_to is not None:
                entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
                e = embed("🔇 Üye Susturuldu (Timeout)", color=discord.Color.dark_red())
                e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
                e.add_field(name="Bitiş", value=f"<t:{int(after_to.timestamp())}:R>", inline=True)
                if entry:
                    e.add_field(name="Yetkili", value=f"{entry.user.mention}", inline=True)
                    e.add_field(name="Sebep", value=entry.reason or "Belirtilmedi", inline=True)
            else:
                entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
                e = embed("🔈 Timeout Kaldırıldı", color=discord.Color.green())
                e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
                if entry:
                    e.add_field(name="Yetkili", value=f"{entry.user.mention}", inline=True)
            e.add_field(name="ID", value=str(after.id), inline=True)
            await self.log(guild, embed=e)
            return

        # Rol değişimi
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added or removed:
            entry = await get_audit(guild, discord.AuditLogAction.member_role_update, after.id)
            mod = entry.user.mention if entry else "Bilinmiyor"
            if added:
                e = embed("🟢 Rol Eklendi", color=discord.Color.blue())
                e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
                e.add_field(name="Eklenen Rol(ler)", value=" ".join(r.mention for r in added), inline=True)
                e.add_field(name="Yetkili", value=mod, inline=True)
                await self.log(guild, embed=e)
            if removed:
                e = embed("🔴 Rol Kaldırıldı", color=discord.Color.orange())
                e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
                e.add_field(name="Kaldırılan Rol(ler)", value=" ".join(r.mention for r in removed), inline=True)
                e.add_field(name="Yetkili", value=mod, inline=True)
                await self.log(guild, embed=e)
            return

        # Takma ad değişimi
        if before.nick != after.nick:
            entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
            e = embed("✏️ Takma Ad Değişti", color=discord.Color.blurple())
            e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
            e.add_field(name="Eskisi", value=before.nick or "Yok", inline=True)
            e.add_field(name="Yenisi", value=after.nick or "Yok", inline=True)
            if entry:
                e.add_field(name="Yetkili", value=entry.user.mention, inline=True)
            await self.log(guild, embed=e)

    # ── Ses Kanalı ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        guild = member.guild

        if before.channel is None and after.channel is not None:
            # Kanala katıldı
            e = embed("🔊 Ses Kanalına Katıldı", color=discord.Color.green())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Kanal", value=after.channel.mention, inline=True)

        elif before.channel is not None and after.channel is None:
            # Kanaldan ayrıldı
            e = embed("🔇 Ses Kanalından Ayrıldı", color=discord.Color.red())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Kanal", value=before.channel.mention, inline=True)

        elif before.channel != after.channel:
            # Kanal değiştirdi
            e = embed("🔀 Ses Kanalı Değiştirdi", color=discord.Color.yellow())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Önceki", value=before.channel.mention, inline=True)
            e.add_field(name="Yeni", value=after.channel.mention, inline=True)

        elif before.self_mute != after.self_mute:
            action = "Kendini Susturdu 🔇" if after.self_mute else "Sesini Açtı 🔊"
            e = embed(f"🎙️ {action}", color=discord.Color.light_grey())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Kanal", value=(after.channel or before.channel).mention, inline=True)

        elif before.mute != after.mute:
            action = "Sunucu Tarafından Susturuldu" if after.mute else "Susturma Kaldırıldı"
            e = embed(f"🎙️ {action}", color=discord.Color.orange())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Kanal", value=(after.channel or before.channel).mention, inline=True)

        else:
            return

        e.add_field(name="ID", value=str(member.id), inline=True)
        await self.log(guild, embed=e)

    # ── Davet Linki ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        e = embed("🔗 Davet Linki Oluşturuldu", color=discord.Color.purple())
        e.add_field(name="Oluşturan", value=f"{invite.inviter.mention} `{invite.inviter}`" if invite.inviter else "Bilinmiyor", inline=False)
        e.add_field(name="Link", value=invite.url, inline=False)
        e.add_field(name="Kanal", value=invite.channel.mention if invite.channel else "Bilinmiyor", inline=True)
        uses = f"{invite.max_uses} kullanım" if invite.max_uses else "Sınırsız"
        expires = f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "Süresiz"
        e.add_field(name="Kullanım Limiti", value=uses, inline=True)
        e.add_field(name="Süre Sonu", value=expires, inline=True)
        await self.log(invite.guild, embed=e)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if not invite.guild:
            return
        entry = await get_audit(invite.guild, discord.AuditLogAction.invite_delete)
        e = embed("🗑️ Davet Linki Silindi", color=discord.Color.dark_red())
        e.add_field(name="Link", value=invite.url, inline=False)
        if entry:
            e.add_field(name="Silen", value=f"{entry.user.mention} `{entry.user}`", inline=True)
        await self.log(invite.guild, embed=e)

    # ── Emoji ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list, after: list):
        added = [em for em in after if em not in before]
        removed = [em for em in before if em not in after]

        for em in added:
            entry = await get_audit(guild, discord.AuditLogAction.emoji_create, em.id)
            e = embed("😀 Emoji Eklendi", color=discord.Color.green())
            e.add_field(name="Emoji", value=f"{em} `:{em.name}:`", inline=True)
            if entry:
                e.add_field(name="Ekleyen", value=entry.user.mention, inline=True)
            if em.url:
                e.set_thumbnail(url=em.url)
            await self.log(guild, embed=e)

        for em in removed:
            entry = await get_audit(guild, discord.AuditLogAction.emoji_delete, em.id)
            e = embed("🗑️ Emoji Silindi", color=discord.Color.red())
            e.add_field(name="Emoji Adı", value=f"`:{em.name}:`", inline=True)
            if entry:
                e.add_field(name="Silen", value=entry.user.mention, inline=True)
            await self.log(guild, embed=e)

    # ── Mesaj Silme / Düzenleme ───────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        e = embed("🗑️ Mesaj Silindi", color=discord.Color.red())
        e.add_field(name="Kullanıcı", value=f"{message.author.mention} `{message.author}`", inline=True)
        e.add_field(name="Kanal", value=message.channel.mention, inline=True)
        if message.content:
            content = message.content[:1000] + ("..." if len(message.content) > 1000 else "")
            e.add_field(name="İçerik", value=content, inline=False)
        if message.attachments:
            e.add_field(name="Ekler", value="\n".join(a.filename for a in message.attachments), inline=False)
        await self.log(message.guild, embed=e)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or not after.guild:
            return
        if before.content == after.content:
            return
        e = embed("✏️ Mesaj Düzenlendi", color=discord.Color.yellow())
        e.add_field(name="Kullanıcı", value=f"{after.author.mention} `{after.author}`", inline=True)
        e.add_field(name="Kanal", value=after.channel.mention, inline=True)
        e.add_field(name="Mesaja Git", value=f"[Tıkla]({after.jump_url})", inline=True)
        old = before.content[:500] + ("..." if len(before.content) > 500 else "") if before.content else "*(boş)*"
        new = after.content[:500] + ("..." if len(after.content) > 500 else "") if after.content else "*(boş)*"
        e.add_field(name="Önceki", value=old, inline=False)
        e.add_field(name="Sonraki", value=new, inline=False)
        await self.log(after.guild, embed=e)

    # ── Kanal Oluşturma / Silme ───────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        entry = await get_audit(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        ch_type = "Ses" if isinstance(channel, discord.VoiceChannel) else "Metin" if isinstance(channel, discord.TextChannel) else "Kategori"
        e = embed(f"📁 {ch_type} Kanalı Oluşturuldu", color=discord.Color.green())
        e.add_field(name="Kanal", value=f"{channel.mention} `{channel.name}`", inline=True)
        if entry:
            e.add_field(name="Oluşturan", value=entry.user.mention, inline=True)
        await self.log(channel.guild, embed=e)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        entry = await get_audit(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        ch_type = "Ses" if isinstance(channel, discord.VoiceChannel) else "Metin" if isinstance(channel, discord.TextChannel) else "Kategori"
        e = embed(f"🗑️ {ch_type} Kanalı Silindi", color=discord.Color.red())
        e.add_field(name="Kanal Adı", value=f"`{channel.name}`", inline=True)
        if entry:
            e.add_field(name="Silen", value=entry.user.mention, inline=True)
        await self.log(channel.guild, embed=e)

    # ── Rol Oluşturma / Silme ─────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        entry = await get_audit(role.guild, discord.AuditLogAction.role_create, role.id)
        e = embed("🟢 Rol Oluşturuldu", color=discord.Color.green())
        e.add_field(name="Rol", value=f"{role.mention} `{role.name}`", inline=True)
        if entry:
            e.add_field(name="Oluşturan", value=entry.user.mention, inline=True)
        await self.log(role.guild, embed=e)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        entry = await get_audit(role.guild, discord.AuditLogAction.role_delete, role.id)
        e = embed("🔴 Rol Silindi", color=discord.Color.red())
        e.add_field(name="Rol Adı", value=f"`{role.name}`", inline=True)
        if entry:
            e.add_field(name="Silen", value=entry.user.mention, inline=True)
        await self.log(role.guild, embed=e)

    # ── Sunucu Güncelleme ─────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        changes = []
        if before.name != after.name:
            changes.append(f"**Ad:** `{before.name}` → `{after.name}`")
        if before.icon != after.icon:
            changes.append("**İkon değişti**")
        if before.verification_level != after.verification_level:
            changes.append(f"**Doğrulama:** `{before.verification_level}` → `{after.verification_level}`")
        if not changes:
            return
        entry = await get_audit(after, discord.AuditLogAction.guild_update)
        e = embed("⚙️ Sunucu Güncellendi", "\n".join(changes), discord.Color.blurple())
        if entry:
            e.add_field(name="Güncelleyen", value=entry.user.mention, inline=True)
        await self.log(after, embed=e)

    # ── Sticker ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list, after: list):
        added = [s for s in after if s not in before]
        removed = [s for s in before if s not in after]
        for s in added:
            e = embed("🎫 Sticker Eklendi", color=discord.Color.green())
            e.add_field(name="Sticker", value=f"`{s.name}`", inline=True)
            await self.log(guild, embed=e)
        for s in removed:
            e = embed("🗑️ Sticker Silindi", color=discord.Color.red())
            e.add_field(name="Sticker", value=f"`{s.name}`", inline=True)
            await self.log(guild, embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(LogEvents(bot))
