"""
cogs/fun/misc.py — Eğlence, bilgi, araç ve Türkiye-spesifik komutlar
Hardcoded veritabanları + ücretsiz API'ler (wttr.in, exchangerate-api, truncgil, orhanaydogdu).
Tüm çıktılar Türkçe ve native Discord V2 component formatındadır.
"""
from __future__ import annotations

import logging
import random
import string
import urllib.parse
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import (
    COLORS,
    c_container,
    c_error,
    c_media,
    c_rich_card,
    c_section,
    c_separator,
    c_text,
    c_thumbnail,
    respond,
)

log = logging.getLogger("horoz_bot.eglence")

# ── Inline veritabanları ─────────────────────────────────────────────────────

_FIKRALAR = [
    "Temel Dursun'a demiş ki: 'Senin burnun niye kırmızı?' Dursun: 'Çünkü kırmızı severim.' Temel: 'O zaman niye mor değil?' Dursun: 'Çünkü mor sevmem.'",
    "Temel bir gün hastaneye gitmiş. Doktor: 'Kanser misin?' Temel: 'Hayır, ben Temel\'im.'",
    "Nasreddin Hoca'ya sormuşlar: 'Hoca, bu tavuğu kaça aldın?' Hoca: 'Beş akçeye.' 'Satarken kaça sattın?' 'Üç akçeye.' 'Niye zarar ettin?' 'Alırken aldım sandım, satarken fark ettim ki tavuk horozmuş.'",
    "Temel'e sormuşlar: 'Dünya kaç günde döner?' Temel: 'Hangi gün dönerse dönsün, ben döner yemem.'",
    "Nasreddin Hoca eve gelmiş, karısı ağlıyor. 'Niye ağlıyorsun?' 'Komşunun tavuğu ölmüş.' 'Peki bizim tavuğumuz ölse ağlar mısın?' 'Ağlarım.' 'Niye?' 'Çünkü bizim komşumuz olur.'",
    "Temel Amerika'ya gitmiş, İngilizce konuşuyor. Adam: 'Where are you from?' Temel: 'From home.'",
    "Bir fakir köye doktor gelmiş, 'Burada veba var mı?' diye sormuş. Köylü: 'Yok, ama zenginlerde var.'",
    "Temel uçakta hostese: 'Bu koltuk niye bu kadar dar?' Hostes: 'Kurtarma yeleği koltuğun altında.' Temel: 'Anladım, o zaman ben kurtulamam.'",
]

_ATASOZLERI = [
    ("Ağaç yaş iken eğilir.", "Küçük yaşta verilen eğitim önemlidir."),
    ("Acele işe şeytan karışır.", "Acele edilen işte hata yapma ihtimali yüksektir."),
    ("Ak akçe kara gün içindir.", "Kazanç, zor günler için biriktirilmelidir."),
    ("Arpa ektim, darı çıktı.", "Yapılan iyilik karşılıksız kalmadı."),
    ("At binenin, kılıç kuşananın.", "Güç, güçlü olanın elindedir."),
    ("Başkasına dilenci etme, kendi elin kapı etme.", "Başkalarına muhtaç olmamaya çalış."),
    ("Bir elin nesi var, iki elin sesi var.", "İş birliği güçlendirir."),
    ("Bilmeyen öğrenir, öğrenmeyen öğretmez.", "Öğrenmeye açık olmak gerekir."),
    ("Boş çuval dik durmaz.", "Boş olan değerli değildir."),
    ("Çıkmayan candan umut kesilmez.", "Umut her zaman var olmalıdır."),
    ("Damlaya damlaya göl olur.", "Küçük birikimler büyük sonuçlar doğurur."),
    ("Davulun sesi uzaktan hoş gelir.", "Her şey uzaktan iyi görünür."),
    ("Değirmenin suyu nereden geliyor?", "Her işin bir nedeni vardır."),
    ("Dost kara günde belli olur.", "Gerçek dost zor anlarda belli olur."),
    ("Eğri otur, doğru söyle.", "Doğruyu söylemek için dürüst ol."),
    ("El elden üstündür.", "Herkesin bir üstün yanı vardır."),
    ("Eşek ölür, semeri kalır; insan ölür, eseri kalır.", "İnsan eserleriyle anılır."),
]

_TRIVIA = [
    {"soru": "Türkiye'nin en yüksek dağı hangisidir?", "secenekler": ["Ağrı Dağı", "Uludağ", "Erciyes", "Kaçkar Dağı"], "dogru": 0},
    {"soru": "İstanbul'un fethi hangi yılda gerçekleşmiştir?", "secenekler": ["1451", "1453", "1455", "1460"], "dogru": 1},
    {"soru": "Türk bayrağındaki ay ve yıldızın rengi nedir?", "secenekler": ["Sarı", "Beyaz", "Kırmızı", "Siyah"], "dogru": 1},
    {"soru": "Türkiye'nin başkenti hangi şehirdir?", "secenekler": ["İstanbul", "İzmir", "Ankara", "Bursa"], "dogru": 2},
    {"soru": "Nutuk hangi yılda söylenmiştir?", "secenekler": ["1920", "1923", "1927", "1934"], "dogru": 2},
    {"soru": "Dünya'nın en büyük okyanusu hangisidir?", "secenekler": ["Atlantik", "Hint", "Pasifik", "Arktik"], "dogru": 2},
    {"soru": "Python programlama dili hangi yılda yayımlanmıştır?", "secenekler": ["1989", "1991", "1995", "2000"], "dogru": 1},
    {"soru": "Türkiye'nin en uzun nehri hangisidir?", "secenekler": ["Fırat", "Dicle", "Kızılırmak", "Sakarya"], "dogru": 2},
    {"soru": "Işık hızı yaklaşık kaç km/s'dir?", "secenekler": ["150.000", "300.000", "500.000", "1.000.000"], "dogru": 1},
    {"soru": "Dünya'nın uydusu hangisidir?", "secenekler": ["Mars", "Venüs", "Ay", "Jüpiter"], "dogru": 2},
    {"soru": "Bir yılda kaç gün vardır?", "secenekler": ["364", "365", "366", "360"], "dogru": 1},
    {"soru": "İnsan vücudundaki en büyük organ hangisidir?", "secenekler": ["Karaciğer", "Deri", "Akciğer", "Beyin"], "dogru": 1},
    {"soru": "H2O hangi maddenin kimyasal formülüdür?", "secenekler": ["Su", "Tuz", "Kum", "Demir"], "dogru": 0},
    {"soru": "Dünya'nın en yüksek dağı hangisidir?", "secenekler": ["K2", "Everest", "Kilimanjaro", "Mont Blanc"], "dogru": 1},
]

_BABASAKALARI = [
    "Çocuk: 'Baba, neden elektrik süpürgesi ses çıkarır?' Baba: 'Çünkü içinde kedi varmış da çıkamamış!'",
    "Çocuk: 'Baba, neden gökyüzü mavidir?' Baba: 'Çünkü yukarıda birileri maviyi seviyor!'",
    "Çocuk: 'Baba, su neden ıslak?' Baba: 'Islak değil, sadece sen öyle hissediyorsun!'",
    "Çocuk: 'Baba, neden ayak parmaklarım beş tane?' Baba: 'Altıncıyı bulamadığın için!'",
    "Çocuk: 'Baba, neden tavuklar uçamaz?' Baba: 'Çünkü uçak bileti pahalı!'",
    "Çocuk: 'Baba, neden uyuyoruz?' Baba: 'Çünkü uyanıkken de uyuyor gibiyiz!'",
    "Çocuk: 'Baba, neden çikolata tatlıdır?' Baba: 'Çünkü acı olsa yemezsin!'",
    "Çocuk: 'Baba, neden saçlarım beyazlanıyor?' Baba: 'Çünkü akıllı oluyorsun!'",
    "Çocuk: 'Baba, neden televizyon konuşmuyor?' Baba: 'Seninle konuşmaktan utanıyor!'",
    "Çocuk: 'Baba, neden buz gibi?' Baba: 'Çünkü buz onun soyadı!'",
    "Çocuk: 'Baba, neden arılar bal yapar?' Baba: 'Para kazanmak için!'",
    "Çocuk: 'Baba, neden gözlük takıyorsun?' Baba: 'Seni daha net görmek için!'",
]


# ── Cog ────────────────────────────────────────────────────────────────────────

class Eglence(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    eglence = app_commands.Group(name="eglence", description="Eğlence, bilgi ve araç komutları")

    # ── 1. Fıkra ───────────────────────────────────────────────────────────────
    @eglence.command(name="fikra", description="Rastgele klasik bir Türk fıkrası")
    async def fikra(self, interaction: discord.Interaction):
        text = random.choice(_FIKRALAR)
        await respond(interaction, c_container(
            c_text(f"## 😂 Fıkra\n\n{text}"),
            color=COLORS.SUCCESS,
        ))

    # ── 2. Atasözü ───────────────────────────────────────────────────────────
    @eglence.command(name="atasozu", description="Rastgele bir atasözü ve anlamı")
    async def atasozu(self, interaction: discord.Interaction):
        soz, anlam = random.choice(_ATASOZLERI)
        await respond(interaction, c_rich_card(
            title="📜 Atasözü",
            body=f"**{soz}**\n\n*{anlam}*",
            color=COLORS.INFO,
        ))

    # ── 3. Trivia ────────────────────────────────────────────────────────────
    @eglence.command(name="trivia", description="Rastgele bir bilgi yarışması sorusu")
    async def trivia(self, interaction: discord.Interaction):
        soru = random.choice(_TRIVIA)
        secenekler = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(soru["secenekler"]))
        body = f"{soru['soru']}\n\n{secenekler}\n\n-# Doğru cevap: ||{soru['secenekler'][soru['dogru']]}||"
        await respond(interaction, c_rich_card(
            title="❓ Trivia",
            body=body,
            color=COLORS.WARNING,
        ))

    # ── 4. Baba Şakası ────────────────────────────────────────────────────────
    @eglence.command(name="babasakasi", description="Klasik bir baba şakası")
    async def babasakasi(self, interaction: discord.Interaction):
        text = random.choice(_BABASAKALARI)
        await respond(interaction, c_container(
            c_text(f"## 🧔 Baba Şakası\n\n{text}"),
            color=COLORS.NEUTRAL,
        ))

    # ── 5. QR Kod ────────────────────────────────────────────────────────────
    @eglence.command(name="qr", description="Metin veya link için QR kod oluştur")
    @app_commands.describe(metin="QR kodda kodlanacak metin veya URL")
    async def qr(self, interaction: discord.Interaction, metin: str):
        encoded = urllib.parse.quote(metin, safe="")
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded}"
        truncated = metin[:100] + ("..." if len(metin) > 100 else "")
        await respond(interaction, c_container(
            c_section(
                c_text(f"## 📱 QR Kod\n\n`{truncated}`"),
                accessory=c_thumbnail(url),
            ),
            c_separator(),
            c_media(url),
            color=COLORS.PRIMARY,
        ))

    # ── 6. Şifre Üretici ─────────────────────────────────────────────────────
    @eglence.command(name="sifre", description="Güçlü rastgele şifre üret")
    @app_commands.describe(uzunluk="Şifre uzunluğu (varsayılan: 16, max: 64)")
    async def sifre(self, interaction: discord.Interaction, uzunluk: int = 16):
        length = max(4, min(64, uzunluk))
        chars = string.ascii_letters + string.digits + "!@#$%^&*-_+=?"
        password = "".join(random.SystemRandom().choice(chars) for _ in range(length))
        await respond(interaction, c_container(
            c_text(f"## 🔐 Şifre\n\n`{password}`"),
            color=COLORS.SUCCESS,
        ), ephemeral=True)

    # ── 7. Hava Durumu ────────────────────────────────────────────────────────
    @eglence.command(name="hava", description="Hava durumu (wttr.in)")
    @app_commands.describe(sehir="Şehir adı (örn: Istanbul, Ankara, Izmir)")
    async def hava(self, interaction: discord.Interaction, sehir: str):
        city = urllib.parse.quote(sehir)
        url = f"https://wttr.in/{city}?format=3"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Hava durumu alınamadı."), ephemeral=True)
                text = await r.text()
        await respond(interaction, c_rich_card(
            title=f"🌤️ Hava Durumu — {sehir.title()}",
            body=f"`{text.strip()}`",
            color=COLORS.INFO,
        ))

    # ── 8. Döviz ──────────────────────────────────────────────────────────────
    @eglence.command(name="doviz", description="Güncel döviz kurları (USD, EUR, GBP)")
    async def doviz(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get("https://api.exchangerate-api.com/v4/latest/USD") as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Döviz verisi alınamadı."), ephemeral=True)
                data = await r.json()
        try:
            usd_try = float(data["rates"]["TRY"])
            eur_try = usd_try / float(data["rates"]["EUR"])
            gbp_try = usd_try / float(data["rates"]["GBP"])
            body = (
                f"**1 USD** = {usd_try:.3f} ₺\n"
                f"**1 EUR** = {eur_try:.3f} ₺\n"
                f"**1 GBP** = {gbp_try:.3f} ₺"
            )
        except Exception:
            return await respond(interaction, c_error("Veri formatı bozuk."), ephemeral=True)
        await respond(interaction, c_rich_card(
            title="💱 Döviz Kurları",
            body=body,
            footer="Kaynak: exchangerate-api.com",
            color=COLORS.PRIMARY,
        ))

    # ── 9. Altın ──────────────────────────────────────────────────────────────
    @eglence.command(name="altin", description="Güncel altın fiyatları (Truncgil)")
    async def altin(self, interaction: discord.Interaction):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get("https://finans.truncgil.com/v3/today.json") as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Altın verisi alınamadı."), ephemeral=True)
                data = await r.json()
        lines: list[str] = []
        keys = ["Gram_Altin", "Ceyrek_Altin", "Yarim_Altin", "Tam_Altin", "Ons_Altin", "USD", "EUR"]
        for key in keys:
            if key not in data or not isinstance(data[key], dict):
                continue
            satis = data[key].get("satis", data[key].get("Selling", "?"))
            alis = data[key].get("alis", data[key].get("Buying", "?"))
            name = key.replace("_", " ")
            lines.append(f"**{name}:** Alış {alis} / Satış {satis}")
        if not lines:
            return await respond(interaction, c_error("Veri formatı bozuk."), ephemeral=True)
        await respond(interaction, c_rich_card(
            title="🏅 Altın & Döviz",
            body="\n".join(lines),
            footer="Kaynak: finans.truncgil.com",
            color=COLORS.WARNING,
        ))

    # ── 10. Deprem ────────────────────────────────────────────────────────────
    @eglence.command(name="deprem", description="Son Kandilli depremleri")
    @app_commands.describe(limit="Kaç deprem gösterilsin? (1-10, varsayılan: 5)")
    async def deprem(self, interaction: discord.Interaction, limit: int = 5):
        count = max(1, min(10, limit))
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"https://api.orhanaydogdu.com.tr/deprem/kandilli/live?limit={count}") as r:
                if r.status != 200:
                    return await respond(interaction, c_error("Deprem verisi alınamadı."), ephemeral=True)
                data = await r.json()
        rows: list[str] = []
        for item in data.get("result", []):
            if not isinstance(item, dict) or not item.get("mag"):
                continue
            loc = item.get("title", "Bilinmiyor")
            mag = item.get("mag", "?")
            depth = item.get("depth", "?")
            date = item.get("date", "?")
            time = item.get("time", "?")
            rows.append(f"**{loc}** — `M{mag}` — Derinlik: {depth}km — {date} {time}")
        body = "\n".join(rows) if rows else "Veri bulunamadı."
        await respond(interaction, c_rich_card(
            title="🌍 Son Depremler",
            body=body,
            footer="Kaynak: Kandilli Rasathanesi (orhanaydogdu.com.tr)",
            color=COLORS.DANGER,
        ))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("Eglence komutu hatası: %s", error)
        await respond(interaction, c_error(f"❌ Hata: {error}"), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Eglence(bot))
