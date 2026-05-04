import discord
from discord.ext import commands
from ._shared import LogBase, embed


class MessageLogs(LogBase):
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        e = embed("🗑️ Mesaj Silindi", color=discord.Color.red())
        e.add_field(name="Kullanıcı", value=f"{message.author.mention} `{message.author}`", inline=True)
        e.add_field(name="Kanal",     value=message.channel.mention,                         inline=True)
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
        e.add_field(name="Kanal",     value=after.channel.mention,                       inline=True)
        e.add_field(name="Mesaja Git",value=f"[Tıkla]({after.jump_url})",                inline=True)
        old = before.content[:500] + ("..." if len(before.content) > 500 else "") if before.content else "*(boş)*"
        new = after.content[:500] + ("..." if len(after.content) > 500 else "")   if after.content  else "*(boş)*"
        e.add_field(name="Önceki", value=old, inline=False)
        e.add_field(name="Sonraki", value=new, inline=False)
        await self.log(after.guild, embed=e)


async def setup(bot):
    await bot.add_cog(MessageLogs(bot))
