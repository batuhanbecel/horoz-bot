import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from ._shared import fun_embed, SEKIZ_TOP_YANIT


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /yazıtura
    @app_commands.command(name="yazıtura", description="Yazı mı tura mı? Bozuk para atar.")
    async def yazıtura(self, interaction: discord.Interaction):
        await interaction.response.defer()

        sonuç = random.choice(["Yazı", "Tura"])

        spin_embed = discord.Embed(
            title="Para atılıyor...",
            description=f"{interaction.user.mention} parayı havaya fırlattı!\n\n<a:spinning_para:1500895448968331468>",
            color=discord.Color.gold(),
        )
        spin_embed.timestamp = discord.utils.utcnow()
        msg = await interaction.followup.send(embed=spin_embed, wait=True)

        await asyncio.sleep(2)

        if sonuç == "Tura":
            emoji_str = "<:tura:1500895527242563837>"
            title = "Tura!"
            color = discord.Color.gold()
        else:
            emoji_str = "<:yazi:1500895591129944194>"
            title = "Yazı!"
            color = discord.Color.light_grey()

        result_embed = discord.Embed(
            title=title,
            description=f"{interaction.user.mention} parayı attı ve...\n\n{emoji_str}  **{sonuç}** çıktı!",
            color=color,
        )
        result_embed.timestamp = discord.utils.utcnow()
        await msg.edit(embed=result_embed)

    # /zar
    @app_commands.command(name="zar", description="Zar atar.")
    @app_commands.describe(yüz="Zarın kaç yüzlü olduğu (varsayılan 6)", adet="Kaç zar atılsın (1-10)")
    async def zar(
        self,
        interaction: discord.Interaction,
        yüz: app_commands.Range[int, 2, 100] = 6,
        adet: app_commands.Range[int, 1, 10] = 1,
    ):
        sonuçlar = [random.randint(1, yüz) for _ in range(adet)]
        toplam = sum(sonuçlar)
        sonuç_str = " + ".join(f"**{s}**" for s in sonuçlar)
        embed = fun_embed(
            "🎲 Zar Atıldı!",
            f"{adet}d{yüz}: {sonuç_str}\n**Toplam: {toplam}**",
            discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

    # /8top
    @app_commands.command(name="8top", description="Sihirli 8-top'a bir soru sor.")
    @app_commands.describe(soru="Sormak istediğin soru")
    async def sekiz_top(self, interaction: discord.Interaction, soru: str):
        yanıt = random.choice(SEKIZ_TOP_YANIT)
        embed = fun_embed(
            "🎱 Sihirli 8-Top",
            f"**Soru:** {soru}\n\n**Cevap:** {yanıt}",
            discord.Color.dark_blue(),
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
