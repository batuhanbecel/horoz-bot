import discord
from discord.ext import commands
import asyncio
from datetime import timezone
from ._shared import LogBase, embed, get_audit, WELCOME_CHANNEL_ID, LEAVE_EMOJI_ID


class MemberLogs(LogBase):
    async def _welcome_channel(self, guild: discord.Guild):
        if not WELCOME_CHANNEL_ID:
            return None
        ch = guild.get_channel(WELCOME_CHANNEL_ID)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(WELCOME_CHANNEL_ID)
            except Exception:
                return None
        return ch

    def _leave_emoji(self, guild: discord.Guild) -> str:
        if LEAVE_EMOJI_ID:
            emoji = discord.utils.get(guild.emojis, id=LEAVE_EMOJI_ID)
            if emoji:
                return str(emoji)
        return "👋"

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        e = embed("📥 Üye Katıldı", color=discord.Color.green())
        e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
        e.add_field(name="ID", value=str(member.id), inline=True)
        created = member.created_at.replace(tzinfo=timezone.utc)
        e.add_field(name="Hesap Oluşturulma", value=f"<t:{int(created.timestamp())}:R>", inline=True)
        e.set_thumbnail(url=member.display_avatar.url)
        await self.log(member.guild, embed=e)

        ch = await self._welcome_channel(member.guild)
        if ch:
            await ch.send(f"{member.mention} çiftliğe katıldı 🐤")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await asyncio.sleep(0.75)

        ban_entry = await get_audit(member.guild, discord.AuditLogAction.ban, member.id)
        if ban_entry and (discord.utils.utcnow() - ban_entry.created_at).total_seconds() < 5:
            return

        kick_entry = await get_audit(member.guild, discord.AuditLogAction.kick, member.id)
        if kick_entry and (discord.utils.utcnow() - kick_entry.created_at).total_seconds() < 5:
            e = embed("👢 Üye Atıldı", color=discord.Color.orange())
            e.add_field(name="Kullanıcı",    value=f"{member.mention} `{member}`",                    inline=False)
            e.add_field(name="Atan Yetkili", value=f"{kick_entry.user.mention} `{kick_entry.user}`",  inline=True)
            e.add_field(name="Sebep",        value=kick_entry.reason or "Belirtilmedi",                inline=True)
        else:
            e = embed("📤 Üye Ayrıldı", color=discord.Color.light_grey())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            roles = [r.mention for r in member.roles if r.name != "@everyone"]
            if roles:
                e.add_field(name="Rolleri", value=", ".join(roles[:10]), inline=False)
        e.add_field(name="ID", value=str(member.id), inline=True)
        e.set_thumbnail(url=member.display_avatar.url)
        await self.log(member.guild, embed=e)

        ch = await self._welcome_channel(member.guild)
        if ch:
            await ch.send(f"{member.mention} çiftliği terk etti {self._leave_emoji(member.guild)}")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await get_audit(guild, discord.AuditLogAction.ban, user.id)
        e = embed("🔨 Üye Yasaklandı", color=discord.Color.red())
        e.add_field(name="Kullanıcı", value=f"{user.mention} `{user}`", inline=False)
        if entry:
            e.add_field(name="Yakan Yetkili", value=f"{entry.user.mention} `{entry.user}`", inline=True)
            e.add_field(name="Sebep",         value=entry.reason or "Belirtilmedi",           inline=True)
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

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        before_to = before.timed_out_until
        after_to = after.timed_out_until
        if before_to != after_to:
            if after_to is not None:
                entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
                e = embed("🔇 Üye Susturuldu (Timeout)", color=discord.Color.dark_red())
                e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`",         inline=False)
                e.add_field(name="Bitiş",     value=f"<t:{int(after_to.timestamp())}:R>", inline=True)
                if entry:
                    e.add_field(name="Yetkili", value=entry.user.mention,                 inline=True)
                    e.add_field(name="Sebep",   value=entry.reason or "Belirtilmedi",      inline=True)
            else:
                entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
                e = embed("🔈 Timeout Kaldırıldı", color=discord.Color.green())
                e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
                if entry:
                    e.add_field(name="Yetkili", value=entry.user.mention, inline=True)
            e.add_field(name="ID", value=str(after.id), inline=True)
            await self.log(guild, embed=e)
            return

        added   = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added or removed:
            entry = await get_audit(guild, discord.AuditLogAction.member_role_update, after.id)
            mod = entry.user.mention if entry else "Bilinmiyor"
            if added:
                e = embed("🟢 Rol Eklendi", color=discord.Color.blue())
                e.add_field(name="Kullanıcı",     value=f"{after.mention} `{after}`",          inline=False)
                e.add_field(name="Eklenen Rol(ler)", value=" ".join(r.mention for r in added), inline=True)
                e.add_field(name="Yetkili",       value=mod,                                   inline=True)
                await self.log(guild, embed=e)
            if removed:
                e = embed("🔴 Rol Kaldırıldı", color=discord.Color.orange())
                e.add_field(name="Kullanıcı",        value=f"{after.mention} `{after}`",             inline=False)
                e.add_field(name="Kaldırılan Rol(ler)", value=" ".join(r.mention for r in removed), inline=True)
                e.add_field(name="Yetkili",          value=mod,                                      inline=True)
                await self.log(guild, embed=e)
            return

        if before.nick != after.nick:
            entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
            e = embed("✏️ Takma Ad Değişti", color=discord.Color.blurple())
            e.add_field(name="Kullanıcı", value=f"{after.mention} `{after}`", inline=False)
            e.add_field(name="Eskisi",    value=before.nick or "Yok",          inline=True)
            e.add_field(name="Yenisi",    value=after.nick or "Yok",           inline=True)
            if entry:
                e.add_field(name="Yetkili", value=entry.user.mention, inline=True)
            await self.log(guild, embed=e)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberLogs(bot))
