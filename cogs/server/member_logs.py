import discord
from discord.ext import commands
import asyncio
from datetime import timezone
from ._shared import LogBase, get_audit, WELCOME_CHANNEL_ID, LEAVE_EMOJI_ID
from .._v2 import c_text, c_section, c_container, c_thumbnail


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
        created = member.created_at.replace(tzinfo=timezone.utc)
        await self.log(member.guild, c_container(
            c_section(
                c_text(
                    f"**📥 Üye Katıldı**\n\n"
                    f"👤 **Kullanıcı:** {member.mention} `{member}`\n"
                    f"🆔 **ID:** `{member.id}`\n"
                    f"📅 **Hesap Oluşturulma:** <t:{int(created.timestamp())}:R>"
                ),
                accessory=c_thumbnail(str(member.display_avatar.url)),
            ),
        ))

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
            text = (
                f"**👢 Üye Atıldı**\n\n"
                f"👤 **Kullanıcı:** {member.mention} `{member}`\n"
                f"👮 **Atan Yetkili:** {kick_entry.user.mention} `{kick_entry.user}`\n"
                f"📝 **Sebep:** {kick_entry.reason or 'Belirtilmedi'}\n"
                f"🆔 **ID:** `{member.id}`"
            )
        else:
            roles = [r.mention for r in member.roles if r.name != "@everyone"]
            text = (
                f"**📤 Üye Ayrıldı**\n\n"
                f"👤 **Kullanıcı:** {member.mention} `{member}`\n"
                + (f"🏷️ **Rolleri:** {', '.join(roles[:10])}\n" if roles else "")
                + f"🆔 **ID:** `{member.id}`"
            )

        await self.log(member.guild, c_container(
            c_section(c_text(text), accessory=c_thumbnail(str(member.display_avatar.url))),
        ))

        ch = await self._welcome_channel(member.guild)
        if ch:
            await ch.send(f"{member.mention} çiftliği terk etti {self._leave_emoji(member.guild)}")

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        entry = await get_audit(guild, discord.AuditLogAction.ban, user.id)
        lines = [
            f"**🔨 Üye Yasaklandı**\n",
            f"👤 **Kullanıcı:** {user.mention} `{user}`",
            f"🆔 **ID:** `{user.id}`",
        ]
        if entry:
            lines.append(f"👮 **Yakan Yetkili:** {entry.user.mention} `{entry.user}`")
            lines.append(f"📝 **Sebep:** {entry.reason or 'Belirtilmedi'}")
        await self.log(guild, c_container(
            c_section(c_text("\n".join(lines)), accessory=c_thumbnail(str(user.display_avatar.url))),
        ))

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        entry = await get_audit(guild, discord.AuditLogAction.unban, user.id)
        lines = [
            f"**✅ Yasak Kaldırıldı**\n",
            f"👤 **Kullanıcı:** {user.mention} `{user}`",
            f"🆔 **ID:** `{user.id}`",
        ]
        if entry:
            lines.append(f"👮 **Kaldıran Yetkili:** {entry.user.mention} `{entry.user}`")
        await self.log(guild, c_container(
            c_section(c_text("\n".join(lines)), accessory=c_thumbnail(str(user.display_avatar.url))),
        ))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        guild = after.guild

        before_to = before.timed_out_until
        after_to = after.timed_out_until
        if before_to != after_to:
            if after_to is not None:
                entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
                lines = [
                    f"**🔇 Üye Susturuldu (Timeout)**\n",
                    f"👤 **Kullanıcı:** {after.mention} `{after}`",
                    f"⏰ **Bitiş:** <t:{int(after_to.timestamp())}:R>",
                    f"🆔 **ID:** `{after.id}`",
                ]
                if entry:
                    lines.append(f"👮 **Yetkili:** {entry.user.mention}")
                    lines.append(f"📝 **Sebep:** {entry.reason or 'Belirtilmedi'}")
            else:
                entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
                lines = [
                    f"**🔈 Timeout Kaldırıldı**\n",
                    f"👤 **Kullanıcı:** {after.mention} `{after}`",
                    f"🆔 **ID:** `{after.id}`",
                ]
                if entry:
                    lines.append(f"👮 **Yetkili:** {entry.user.mention}")
            await self.log(guild, c_container(
                c_section(c_text("\n".join(lines)), accessory=c_thumbnail(str(after.display_avatar.url))),
            ))
            return

        added   = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added or removed:
            entry = await get_audit(guild, discord.AuditLogAction.member_role_update, after.id)
            mod = entry.user.mention if entry else "Bilinmiyor"
            if added:
                await self.log(guild, c_container(
                    c_section(
                        c_text(
                            f"**🟢 Rol Eklendi**\n\n"
                            f"👤 **Kullanıcı:** {after.mention} `{after}`\n"
                            f"🏷️ **Eklenen:** {' '.join(r.mention for r in added)}\n"
                            f"👮 **Yetkili:** {mod}"
                        ),
                        accessory=c_thumbnail(str(after.display_avatar.url)),
                    ),
                ))
            if removed:
                await self.log(guild, c_container(
                    c_section(
                        c_text(
                            f"**🔴 Rol Kaldırıldı**\n\n"
                            f"👤 **Kullanıcı:** {after.mention} `{after}`\n"
                            f"🏷️ **Kaldırılan:** {' '.join(r.mention for r in removed)}\n"
                            f"👮 **Yetkili:** {mod}"
                        ),
                        accessory=c_thumbnail(str(after.display_avatar.url)),
                    ),
                ))
            return

        if before.nick != after.nick:
            entry = await get_audit(guild, discord.AuditLogAction.member_update, after.id)
            lines = [
                f"**✏️ Takma Ad Değişti**\n",
                f"👤 **Kullanıcı:** {after.mention} `{after}`",
                f"📝 **Eskisi:** {before.nick or 'Yok'}",
                f"📝 **Yenisi:** {after.nick or 'Yok'}",
            ]
            if entry:
                lines.append(f"👮 **Yetkili:** {entry.user.mention}")
            await self.log(guild, c_container(
                c_section(c_text("\n".join(lines)), accessory=c_thumbnail(str(after.display_avatar.url))),
            ))


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberLogs(bot))
