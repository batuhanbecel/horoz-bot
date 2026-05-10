import discord
from discord.ext import commands
from ._shared import LogBase
from .._v2 import c_text, c_section, c_container, c_thumbnail


class VoiceLogs(LogBase):
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        guild = member.guild

        if before.channel is None and after.channel is not None:
            text = f"**🔊 Ses Kanalına Katıldı**\n\n👤 **Kullanıcı:** {member.mention} `{member}`\n📌 **Kanal:** {after.channel.mention}"
        elif before.channel is not None and after.channel is None:
            text = f"**🔇 Ses Kanalından Ayrıldı**\n\n👤 **Kullanıcı:** {member.mention} `{member}`\n📌 **Kanal:** {before.channel.mention}"
        elif before.channel != after.channel:
            text = f"**🔀 Ses Kanalı Değiştirdi**\n\n👤 **Kullanıcı:** {member.mention} `{member}`\n📌 **Önceki:** {before.channel.mention}\n📌 **Yeni:** {after.channel.mention}"
        elif before.self_mute != after.self_mute:
            action = "Kendini Susturdu 🔇" if after.self_mute else "Sesini Açtı 🔊"
            text = f"**🎙️ {action}**\n\n👤 **Kullanıcı:** {member.mention} `{member}`\n📌 **Kanal:** {(after.channel or before.channel).mention}"
        elif before.mute != after.mute:
            action = "Sunucu Tarafından Susturuldu" if after.mute else "Susturma Kaldırıldı"
            text = f"**🎙️ {action}**\n\n👤 **Kullanıcı:** {member.mention} `{member}`\n📌 **Kanal:** {(after.channel or before.channel).mention}"
        else:
            return

        await self.log(guild, c_container(
            c_section(c_text(text), accessory=c_thumbnail(str(member.display_avatar.url))),
        ))


async def setup(bot):
    await bot.add_cog(VoiceLogs(bot))
