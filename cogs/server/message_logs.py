import discord
from discord.ext import commands
from ._shared import LogBase
from .._v2 import c_text, c_container


class MessageLogs(LogBase):
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        lines = [
            f"**🗑️ Mesaj Silindi**\n",
            f"👤 **Kullanıcı:** {message.author.mention} `{message.author}`",
            f"📌 **Kanal:** {message.channel.mention}",
        ]
        if message.content:
            content = message.content[:1000] + ("..." if len(message.content) > 1000 else "")
            lines.append(f"💬 **İçerik:** {content}")
        if message.attachments:
            lines.append(f"📎 **Ekler:** {', '.join(a.filename for a in message.attachments)}")
        await self.log(message.guild, c_container(c_text("\n".join(lines))))

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or not after.guild:
            return
        if before.content == after.content:
            return
        old = before.content[:500] + ("..." if len(before.content) > 500 else "") if before.content else "*(boş)*"
        new = after.content[:500]  + ("..." if len(after.content) > 500 else "")  if after.content  else "*(boş)*"
        await self.log(after.guild, c_container(
            c_text(
                f"**✏️ Mesaj Düzenlendi**\n\n"
                f"👤 **Kullanıcı:** {after.author.mention} `{after.author}`\n"
                f"📌 **Kanal:** {after.channel.mention} · [Mesaja Git]({after.jump_url})\n\n"
                f"**Önceki:** {old}\n"
                f"**Sonraki:** {new}"
            ),
        ))


async def setup(bot):
    await bot.add_cog(MessageLogs(bot))
