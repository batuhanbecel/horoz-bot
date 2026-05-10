import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import paramiko
import a2s
from ._v2 import (
    COLORS, c_card, c_info_card, c_text, c_separator, c_container,
    respond, followup as v2_followup, error_response,
)


class PZServer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.host = "46.235.8.120"
        self.port = 22667
        self.user = "root"
        self.password = "XM2KZ51f6aj7tNl"
        self.remote_dir = "/opt/pz-server"
        self.jar_name = "ProjectZomboid64"
        self.game_port = 16261

    def _exec_sync(self, cmd: str) -> tuple[int, str, str]:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                timeout=15,
                look_for_keys=False,
                allow_agent=False,
            )
            stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
            stdin.close()
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="replace").strip()
            err = stderr.read().decode("utf-8", errors="replace").strip()
            return exit_code, out, err
        finally:
            client.close()

    async def _run_remote(self, cmd: str) -> tuple[int, str, str]:
        return await asyncio.to_thread(self._exec_sync, cmd)

    async def _query_a2s(self) -> dict | None:
        try:
            info = await asyncio.to_thread(
                a2s.info, (self.host, self.game_port), timeout=5
            )
            players = await asyncio.to_thread(
                a2s.players, (self.host, self.game_port), timeout=5
            )
            return {
                "name": info.server_name,
                "map": info.map_name,
                "players": info.player_count,
                "max_players": info.max_players,
                "password": info.password_protected,
                "player_list": [p.name for p in players[:20]] if players else [],
            }
        except Exception:
            return None

    def _is_running(self, stdout: str) -> bool:
        return "ProjectZomboid" in stdout

    async def _ensure_binary(self) -> tuple[bool, str]:
        rc, out, err = await self._run_remote(
            f"test -f {self.remote_dir}/ProjectZomboid64 && echo 'OK' || echo 'MISSING'"
        )
        return out == "OK", out

    @app_commands.command(name="pz-start", description="Project Zomboid sunucusunu başlatır (Admin gerekir).")
    @app_commands.checks.has_permissions(administrator=True)
    async def pz_start(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        ok, msg = await self._ensure_binary()
        if not ok:
            await v2_followup(interaction, c_container(
                c_text("## 🔴 Sunucu Kurulu Değil"),
                c_separator(),
                c_text(f"`{self.jar_name}` bulunamadı.\n"
                       f"Sunucu dosyaları henüz yüklenmemiş. Önce PZ server kurulumunu tamamlayın."),
            ), ephemeral=False)
            return

        rc, out, err = await self._run_remote(f"bash {self.remote_dir}/start_server.sh status")
        if "ONLINE" in out:
            await v2_followup(interaction, c_container(
                c_text("## 🟡 Sunucu Zaten Çalışıyor"),
                c_separator(),
                c_text("Project Zomboid sunucusu şu an aktif."),
            ), ephemeral=False)
            return

        rc, out, err = await self._run_remote(f"bash {self.remote_dir}/start_server.sh start")
        if rc == 0:
            await v2_followup(interaction, c_container(
                c_text("## 🟢 Sunucu Başlatıldı"),
                c_separator(),
                c_text("Project Zomboid sunucusu arka planda başlatılıyor.\n"
                       "Birkaç dakika içinde erişilebilir olacaktır."),
            ), ephemeral=False)
        else:
            await v2_followup(interaction, c_container(
                c_text("## 🔴 Başlatma Başarısız"),
                c_separator(),
                c_text(f"```\n{err or out}\n```"),
            ), ephemeral=False)

    @app_commands.command(name="pz-stop", description="Project Zomboid sunucusunu durdurur (Admin gerekir).")
    @app_commands.checks.has_permissions(administrator=True)
    async def pz_stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        rc, out, err = await self._run_remote(f"bash {self.remote_dir}/start_server.sh stop")
        if "Sunucu çalışmıyor" in out or rc != 0:
            await v2_followup(interaction, c_container(
                c_text("## 🟡 Sunucu Zaten Kapalı"),
                c_separator(),
                c_text("Project Zomboid sunucusu şu an çalışmıyor."),
            ), ephemeral=False)
        else:
            await v2_followup(interaction, c_container(
                c_text("## 🔴 Sunucu Durduruldu"),
                c_separator(),
                c_text("Project Zomboid sunucusu güvenli bir şekilde kapatıldı."),
            ), ephemeral=False)

    @app_commands.command(name="pz-restart", description="Project Zomboid sunucusunu yeniden başlatır (Admin gerekir).")
    @app_commands.checks.has_permissions(administrator=True)
    async def pz_restart(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        ok, msg = await self._ensure_binary()
        if not ok:
            await v2_followup(interaction, c_container(
                c_text("## 🔴 Sunucu Kurulu Değil"),
                c_separator(),
                c_text(f"`{self.jar_name}` bulunamadı.\n"
                       f"Sunucu dosyaları henüz yüklenmemiş. Önce PZ server kurulumunu tamamlayın."),
            ), ephemeral=False)
            return

        rc, out, err = await self._run_remote(f"bash {self.remote_dir}/start_server.sh restart")
        await v2_followup(interaction, c_container(
            c_text("## 🔄 Sunucu Yeniden Başlatılıyor"),
            c_separator(),
            c_text("Project Zomboid sunucusu kapatılıp tekrar başlatılıyor.\n"
                   "Birkaç dakika içinde erişilebilir olacaktır."),
        ), ephemeral=False)

    @app_commands.command(name="pz-status", description="Project Zomboid sunucusunun durumunu gösterir.")
    async def pz_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        rc, out, err = await self._run_remote(f"bash {self.remote_dir}/start_server.sh status")
        ok = "ONLINE" in out
        status = "🟢 Çalışıyor" if ok else "🔴 Kapalı"

        body_lines = [
            f"**Host:** `{self.host}:{self.game_port}`",
            f"**Dizin:** `{self.remote_dir}`",
            f"**Status:** `{out}`" if out else "",
        ]

        if ok:
            a2s_data = await self._query_a2s()
            if a2s_data:
                body_lines.append(f"**Sunucu Adı:** `{a2s_data['name']}`")
                body_lines.append(f"**Harita:** `{a2s_data['map']}`")
                body_lines.append(f"**Oyuncular:** `{a2s_data['players']}/{a2s_data['max_players']}`")
                if a2s_data["player_list"]:
                    names = ", ".join(a2s_data["player_list"])
                    body_lines.append(f"**Online:** `{names}`")
                body_lines.append(f"**Şifre:** `{'Evet' if a2s_data['password'] else 'Hayır'}`")
            else:
                body_lines.append("*Steam query yanıt vermiyor — sunucu başlatma aşamasında olabilir.*")

        body = "\n".join(line for line in body_lines if line)
        await v2_followup(interaction, c_container(
            c_text(f"## {status}"),
            c_separator(),
            c_text(body),
        ), ephemeral=False)

    @app_commands.command(name="pz-info", description="Discord entegrasyonu hakkında bilgi verir.")
    async def pz_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        info_text = (
            "**Discord Token** ne işe yarar?\n\n"
            "Project Zomboid sunucusu, bir Discord bot token'ı kullanarak **oyun içi sohbeti**, "
            "**oyuncu giriş/çıkış loglarını** ve **sunucu olaylarını** doğrudan bir Discord kanalına gönderebilir.\n\n"
            "Ayarlamak için `servertest.ini` dosyasındaki şu alanları doldurun:\n"
            "```ini\n"
            "DiscordEnable=true\n"
            "DiscordToken=YOUR_BOT_TOKEN\n"
            "DiscordChatChannel=sohbet\n"
            "DiscordLogChannel=loglar\n"
            "```\n\n"
            "Not: Bu token, Discord Developer Portal'dan oluşturduğunuz bir **bot token'ı** olmalıdır. "
            "Bot, sunucuya davet edilmeli ve ilgili kanallara yazma yetkisi verilmelidir."
        )
        await v2_followup(interaction, c_container(
            c_text("## ℹ️ Discord Entegrasyonu"),
            c_separator(),
            c_text(info_text),
        ), ephemeral=False)

    @app_commands.command(name="pz-logs", description="Project Zomboid sunucusunun son loglarını gösterir.")
    @app_commands.describe(satir="Gösterilecek son satır sayısı (varsayılan: 20)")
    async def pz_logs(self, interaction: discord.Interaction, satir: int = 20):
        await interaction.response.defer(ephemeral=False)
        rc, out, err = await self._run_remote(
            f"bash {self.remote_dir}/start_server.sh logs {satir}"
        )
        text = out if out else err
        if not text:
            text = "Log dosyası bulunamadı."
        if len(text) > 1900:
            text = text[-1900:]
        await v2_followup(interaction, c_container(
            c_text(f"## 📋 Son {satir} Satır Log"),
            c_separator(),
            c_text(f"```\n{text}\n```"),
        ), ephemeral=False)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        msg = "Bu komutu kullanmak için **Yönetici** yetkisi gereklidir." \
            if isinstance(error, app_commands.MissingPermissions) else str(error)
        await error_response(interaction, msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(PZServer(bot))
