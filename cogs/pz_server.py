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

    @app_commands.command(name="pz-info", description="Project Zomboid sunucusu bağlantı bilgilerini gösterir.")
    async def pz_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        a2s_data = await self._query_a2s()
        server_name = a2s_data["name"] if a2s_data else "Tavuk Çiftliği"
        password_status = "Şifreli" if (a2s_data and a2s_data.get("password")) else "Şifresiz"
        body = (
            f"**Sunucu Adı:** `{server_name}`\n"
            f"**IP Adresi:** `{self.host}`\n"
            f"**Port:** `{self.game_port}`\n"
            f"**Versiyon:** `Build 42.17`\n"
            f"**Şifre Durumu:** `{password_status}`\n"
            f"**Admin Şifresi:** `botadmin123`\n\n"
            f"**Nasıl Bağlanılır?**\n"
            f"1. Project Zomboid'yi açın\n"
            f"2. Ana menüden **Join** seçin\n"
            f"3. **IP** alanına: `{self.host}`\n"
            f"4. **Port** alanına: `{self.game_port}`\n"
            f"5. **Account** alanına: kullanıcı adınız\n"
            f"6. **Password** alanına: şifre (varsa)\n"
            f"7. **Save**'e basın, sonra **Connect** ile bağlanın\n\n"
            f"**Admin Olma (oyun içi):**\n"
            f"Sohbete `/setaccesslevel KULLANICI_ADIN admin` yazın veya `admin` şifresiyle direkt giriş yapın."
        )
        await v2_followup(interaction, c_container(
            c_text("## ℹ️ Sunucu Bilgileri"),
            c_separator(),
            c_text(body),
        ), ephemeral=False)

    @app_commands.command(name="pz-baglanti", description="Project Zomboid sunucusuna nasıl bağlanılacağını gösterir.")
    async def pz_baglanti(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        a2s_data = await self._query_a2s()
        server_name = a2s_data["name"] if a2s_data else "Tavuk Çiftliği"
        password_info = "Sunucu şifreli — bağlanmadan önce şifre girmeniz gerekebilir." if (a2s_data and a2s_data.get("password")) else "Sunucu şifresiz — direkt bağlanabilirsiniz."
        body = (
            f"**Sunucu Adı:** `{server_name}`\n"
            f"**IP:** `{self.host}`\n"
            f"**Port:** `{self.game_port}`\n"
            f"**Versiyon:** `Build 42.17`\n\n"
            f"**Nasıl Bağlanılır?**\n"
            f"1. Project Zomboid'yi açın\n"
            f"2. Ana menüden **Join** seçin\n"
            f"3. **IP** alanına: `{self.host}`\n"
            f"4. **Port** alanına: `{self.game_port}`\n"
            f"5. **Account** alanına: sunucuya kaydolmak istediğiniz kullanıcı adı\n"
            f"6. **Password** alanına: şifre (varsa)\n"
            f"7. **Save**'e basın, sonra sunucuya **Connect** ile bağlanın\n\n"
            f"**Admin Girişi (oyun içi):**\n"
            f"Sohbet kutusuna: `/setaccesslevel YOUR_USERNAME admin`\n"
            f"veya `admin` şifresiyle giriş yapın.\n\n"
            f"{password_info}"
        )
        await v2_followup(interaction, c_container(
            c_text("## 🔌 Sunucu Bağlantı Bilgileri"),
            c_separator(),
            c_text(body),
        ), ephemeral=False)

    @app_commands.command(name="pz-mod-ekle", description="Project Zomboid sunucusuna Steam Workshop modu ekler (Admin gerekir).")
    @app_commands.describe(workshop_id="Steam Workshop item ID (sayısal)", mod_id="Mod ID (mod.info içindeki ID)")
    @app_commands.checks.has_permissions(administrator=True)
    async def pz_mod_ekle(self, interaction: discord.Interaction, workshop_id: str, mod_id: str):
        await interaction.response.defer(ephemeral=False)
        ini_path = "/root/Zomboid/Server/servertest.ini"

        # --- Mods= ekle ---
        rc, out, err = await self._run_remote(
            f"python3 -c \""
            f"import re\n"
            f"with open('{ini_path}') as f: c = f.read()\n"
            f"m = re.search(r'^Mods=(.*)$', c, re.M)\n"
            f"if m:\n"
            f"    existing = [x.strip() for x in m.group(1).split(',') if x.strip()]\n"
            f"    if '{mod_id}' not in existing:\n"
            f"        existing.append('{mod_id}')\n"
            f"        c = re.sub(r'^Mods=.*$', 'Mods=' + ','.join(existing), c, flags=re.M)\n"
            f"        with open('{ini_path}', 'w') as f: f.write(c)\n"
            f"        print('ADDED_MOD')\n"
            f"    else:\n"
            f"        print('ALREADY_MOD')\n"
            f"else:\n"
            f"    print('NO_MODS_KEY')\n"
            f"\""
        )
        mod_status = out.strip()

        # --- WorkshopItems= ekle ---
        rc2, out2, err2 = await self._run_remote(
            f"python3 -c \""
            f"import re\n"
            f"with open('{ini_path}') as f: c = f.read()\n"
            f"m = re.search(r'^WorkshopItems=(.*)$', c, re.M)\n"
            f"if m:\n"
            f"    existing = [x.strip() for x in m.group(1).split(';') if x.strip()]\n"
            f"    if '{workshop_id}' not in existing:\n"
            f"        existing.append('{workshop_id}')\n"
            f"        c = re.sub(r'^WorkshopItems=.*$', 'WorkshopItems=' + ';'.join(existing), c, flags=re.M)\n"
            f"        with open('{ini_path}', 'w') as f: f.write(c)\n"
            f"        print('ADDED_WORKSHOP')\n"
            f"    else:\n"
            f"        print('ALREADY_WORKSHOP')\n"
            f"else:\n"
            f"    print('NO_WORKSHOP_KEY')\n"
            f"\""
        )
        ws_status = out2.strip()

        if mod_status == "NO_MODS_KEY" or ws_status == "NO_WORKSHOP_KEY":
            await v2_followup(interaction, c_container(
                c_text("## 🔴 Mod Ekleme Başarısız"),
                c_separator(),
                c_text(f"`servertest.ini` dosyasında `Mods=` veya `WorkshopItems=` anahtarı bulunamadı.\n"
                       f"Manuel olarak eklemeniz gerekebilir."),
            ), ephemeral=False)
            return

        await v2_followup(interaction, c_container(
            c_text("## ✅ Mod Eklendi"),
            c_separator(),
            c_text(
                f"**Workshop ID:** `{workshop_id}`\n"
                f"**Mod ID:** `{mod_id}`\n\n"
                f"`servertest.ini` güncellendi. Değişikliklerin aktif olması için:\n"
                f"`/pz-restart` komutunu kullanarak sunucuyu yeniden başlatın."
            ),
        ), ephemeral=False)

    @app_commands.command(name="pz-mod-sil", description="Project Zomboid sunucusundan mod kaldırır (Admin gerekir).")
    @app_commands.describe(mod_id="Kaldırılacak Mod ID")
    @app_commands.checks.has_permissions(administrator=True)
    async def pz_mod_sil(self, interaction: discord.Interaction, mod_id: str):
        await interaction.response.defer(ephemeral=False)
        ini_path = "/root/Zomboid/Server/servertest.ini"

        # --- Mods= sil ---
        rc, out, err = await self._run_remote(
            f"python3 -c \""
            f"import re\n"
            f"with open('{ini_path}') as f: c = f.read()\n"
            f"m = re.search(r'^Mods=(.*)$', c, re.M)\n"
            f"if m:\n"
            f"    existing = [x.strip() for x in m.group(1).split(',') if x.strip()]\n"
            f"    if '{mod_id}' in existing:\n"
            f"        existing.remove('{mod_id}')\n"
            f"        c = re.sub(r'^Mods=.*$', 'Mods=' + ','.join(existing), c, flags=re.M)\n"
            f"        with open('{ini_path}', 'w') as f: f.write(c)\n"
            f"        print('REMOVED')\n"
            f"    else:\n"
            f"        print('NOT_FOUND')\n"
            f"else:\n"
            f"    print('NO_MODS_KEY')\n"
            f"\""
        )
        mod_status = out.strip()

        # --- WorkshopItems= sil (eşleşen workshop ID'yi bulmak zor olabilir, mod_id ile aynı olmayabilir)
        # Basitçe: kullanıcı sadece mod_id verdi, workshop_id bilmiyor olabilir.
        # Bu yüzden WorkshopItems listesinden sadece boş kalan modları temizleyeceğiz,
        # veya kullanıcıya manuel temizlemesi gerektiğini söyleyeceğiz.

        if mod_status == "NO_MODS_KEY":
            await v2_followup(interaction, c_container(
                c_text("## 🔴 Mod Silme Başarısız"),
                c_separator(),
                c_text("`Mods=` anahtarı `servertest.ini` içinde bulunamadı."),
            ), ephemeral=False)
            return

        if mod_status == "NOT_FOUND":
            await v2_followup(interaction, c_container(
                c_text("## 🟡 Mod Bulunamadı"),
                c_separator(),
                c_text(f"`{mod_id}` zaten `Mods=` listesinde yok."),
            ), ephemeral=False)
            return

        await v2_followup(interaction, c_container(
            c_text("## ✅ Mod Kaldırıldı"),
            c_separator(),
            c_text(
                f"**Mod ID:** `{mod_id}`\n"
                f"`Mods=` listesinden silindi.\n\n"
                f"**WorkshopItems** temizliği için eşleşen Workshop ID'yi "
                f"`servertest.ini` dosyasından manuel olarak kaldırabilirsiniz.\n\n"
                f"Değişikliklerin aktif olması için `/pz-restart` komutunu kullanın."
            ),
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
