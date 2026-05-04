import discord
from discord.ext import commands
from ._shared import LogBase, embed, get_audit


class GuildLogs(LogBase):
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

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        e = embed("🔗 Davet Linki Oluşturuldu", color=discord.Color.purple())
        e.add_field(name="Oluşturan", value=f"{invite.inviter.mention} `{invite.inviter}`" if invite.inviter else "Bilinmiyor", inline=False)
        e.add_field(name="Link",  value=invite.url,                                                                              inline=False)
        e.add_field(name="Kanal", value=invite.channel.mention if invite.channel else "Bilinmiyor",                             inline=True)
        uses    = f"{invite.max_uses} kullanım" if invite.max_uses else "Sınırsız"
        expires = f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "Süresiz"
        e.add_field(name="Kullanım Limiti", value=uses,    inline=True)
        e.add_field(name="Süre Sonu",       value=expires, inline=True)
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

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list, after: list):
        added   = [em for em in after  if em not in before]
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

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list, after: list):
        added   = [s for s in after  if s not in before]
        removed = [s for s in before if s not in after]
        for s in added:
            e = embed("🎫 Sticker Eklendi", color=discord.Color.green())
            e.add_field(name="Sticker", value=f"`{s.name}`", inline=True)
            await self.log(guild, embed=e)
        for s in removed:
            e = embed("🗑️ Sticker Silindi", color=discord.Color.red())
            e.add_field(name="Sticker", value=f"`{s.name}`", inline=True)
            await self.log(guild, embed=e)


async def setup(bot):
    await bot.add_cog(GuildLogs(bot))
