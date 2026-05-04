import discord
from ._shared import LogBase, embed


class VoiceLogs(LogBase):
    @discord.ext.commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        guild = member.guild

        if before.channel is None and after.channel is not None:
            e = embed("🔊 Ses Kanalına Katıldı", color=discord.Color.green())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Kanal",     value=after.channel.mention,           inline=True)

        elif before.channel is not None and after.channel is None:
            e = embed("🔇 Ses Kanalından Ayrıldı", color=discord.Color.red())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Kanal",     value=before.channel.mention,          inline=True)

        elif before.channel != after.channel:
            e = embed("🔀 Ses Kanalı Değiştirdi", color=discord.Color.yellow())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`", inline=False)
            e.add_field(name="Önceki",    value=before.channel.mention,          inline=True)
            e.add_field(name="Yeni",      value=after.channel.mention,           inline=True)

        elif before.self_mute != after.self_mute:
            action = "Kendini Susturdu 🔇" if after.self_mute else "Sesini Açtı 🔊"
            e = embed(f"🎙️ {action}", color=discord.Color.light_grey())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`",              inline=False)
            e.add_field(name="Kanal",     value=(after.channel or before.channel).mention,   inline=True)

        elif before.mute != after.mute:
            action = "Sunucu Tarafından Susturuldu" if after.mute else "Susturma Kaldırıldı"
            e = embed(f"🎙️ {action}", color=discord.Color.orange())
            e.add_field(name="Kullanıcı", value=f"{member.mention} `{member}`",              inline=False)
            e.add_field(name="Kanal",     value=(after.channel or before.channel).mention,   inline=True)

        else:
            return

        e.add_field(name="ID", value=str(member.id), inline=True)
        await self.log(guild, embed=e)


async def setup(bot):
    await bot.add_cog(VoiceLogs(bot))
