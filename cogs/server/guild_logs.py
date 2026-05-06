import discord
from discord.ext import commands
from ._shared import LogBase, get_audit
from .._v2 import c_text, c_section, c_container, c_thumbnail


class GuildLogs(LogBase):
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        entry = await get_audit(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        ch_type = "Ses" if isinstance(channel, discord.VoiceChannel) else "Metin" if isinstance(channel, discord.TextChannel) else "Kategori"
        lines = [f"**📁 {ch_type} Kanalı Oluşturuldu**\n", f"📌 **Kanal:** {channel.mention} `{channel.name}`"]
        if entry:
            lines.append(f"👮 **Oluşturan:** {entry.user.mention}")
        await self.log(channel.guild, c_container(c_text("\n".join(lines)), color=0x57F287))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        entry = await get_audit(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        ch_type = "Ses" if isinstance(channel, discord.VoiceChannel) else "Metin" if isinstance(channel, discord.TextChannel) else "Kategori"
        lines = [f"**🗑️ {ch_type} Kanalı Silindi**\n", f"📌 **Kanal Adı:** `{channel.name}`"]
        if entry:
            lines.append(f"👮 **Silen:** {entry.user.mention}")
        await self.log(channel.guild, c_container(c_text("\n".join(lines)), color=0xED4245))

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        entry = await get_audit(role.guild, discord.AuditLogAction.role_create, role.id)
        lines = [f"**🟢 Rol Oluşturuldu**\n", f"🏷️ **Rol:** {role.mention} `{role.name}`"]
        if entry:
            lines.append(f"👮 **Oluşturan:** {entry.user.mention}")
        await self.log(role.guild, c_container(c_text("\n".join(lines)), color=0x57F287))

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        entry = await get_audit(role.guild, discord.AuditLogAction.role_delete, role.id)
        lines = [f"**🔴 Rol Silindi**\n", f"🏷️ **Rol Adı:** `{role.name}`"]
        if entry:
            lines.append(f"👮 **Silen:** {entry.user.mention}")
        await self.log(role.guild, c_container(c_text("\n".join(lines)), color=0xED4245))

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
        lines = ["**⚙️ Sunucu Güncellendi**\n"] + changes
        if entry:
            lines.append(f"\n👮 **Güncelleyen:** {entry.user.mention}")
        await self.log(after, c_container(c_text("\n".join(lines)), color=0x5865F2))

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        uses    = f"{invite.max_uses} kullanım" if invite.max_uses else "Sınırsız"
        expires = f"<t:{int(invite.expires_at.timestamp())}:R>" if invite.expires_at else "Süresiz"
        inviter = f"{invite.inviter.mention} `{invite.inviter}`" if invite.inviter else "Bilinmiyor"
        await self.log(invite.guild, c_container(
            c_text(
                f"**🔗 Davet Linki Oluşturuldu**\n\n"
                f"👤 **Oluşturan:** {inviter}\n"
                f"🔗 **Link:** {invite.url}\n"
                f"📌 **Kanal:** {invite.channel.mention if invite.channel else 'Bilinmiyor'}\n"
                f"🔢 **Kullanım:** {uses} · ⏰ **Süre:** {expires}"
            ),
            color=0x9B59B6,
        ))

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        if not invite.guild:
            return
        entry = await get_audit(invite.guild, discord.AuditLogAction.invite_delete)
        lines = [f"**🗑️ Davet Linki Silindi**\n", f"🔗 **Link:** {invite.url}"]
        if entry:
            lines.append(f"👮 **Silen:** {entry.user.mention} `{entry.user}`")
        await self.log(invite.guild, c_container(c_text("\n".join(lines)), color=0xED4245))

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild: discord.Guild, before: list, after: list):
        added   = [em for em in after  if em not in before]
        removed = [em for em in before if em not in after]
        for em in added:
            entry = await get_audit(guild, discord.AuditLogAction.emoji_create, em.id)
            lines = [f"**😀 Emoji Eklendi**\n", f"😀 **Emoji:** {em} `:{em.name}:`"]
            if entry:
                lines.append(f"👮 **Ekleyen:** {entry.user.mention}")
            card_items = [c_text("\n".join(lines))]
            if em.url:
                from .._v2 import c_section, c_thumbnail as _th
                card_items = [c_section(c_text("\n".join(lines)), accessory=_th(str(em.url)))]
            await self.log(guild, c_container(*card_items, color=0x57F287))
        for em in removed:
            entry = await get_audit(guild, discord.AuditLogAction.emoji_delete, em.id)
            lines = [f"**🗑️ Emoji Silindi**\n", f"📛 **Emoji Adı:** `:{em.name}:`"]
            if entry:
                lines.append(f"👮 **Silen:** {entry.user.mention}")
            await self.log(guild, c_container(c_text("\n".join(lines)), color=0xED4245))

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild: discord.Guild, before: list, after: list):
        added   = [s for s in after  if s not in before]
        removed = [s for s in before if s not in after]
        for s in added:
            await self.log(guild, c_container(
                c_text(f"**🎫 Sticker Eklendi**\n\n🎫 **Sticker:** `{s.name}`"),
                color=0x57F287,
            ))
        for s in removed:
            await self.log(guild, c_container(
                c_text(f"**🗑️ Sticker Silindi**\n\n📛 **Sticker:** `{s.name}`"),
                color=0xED4245,
            ))


async def setup(bot):
    await bot.add_cog(GuildLogs(bot))
