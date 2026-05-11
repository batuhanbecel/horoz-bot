"""
cogs/fun/lol.py — League of Legends rehber botu
Riot Data Dragon (ücretsiz, API key gerektirmez) ile şampiyon/ eşya verisi.
38 popüler şampiyon için detaylı rehber + rol bazlı varsayılan build.
Tüm çıktılar Türkçe.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from .._v2 import (
    c_container,
    c_separator,
    c_text,
    c_thumbnail,
    c_section,
    respond,
)

log = logging.getLogger("horoz_bot.lol")

# ── Sabitler ──────────────────────────────────────────────────────────────────
DD_VERSION = "15.9.1"
DD_BASE = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}"
DD_LANG = "tr_TR"

# ── Orman bilinen şampiyonlar ─────────────────────────────────────────────────
_JUNGLE_CHAMPS: set[str] = {
    "Lee Sin", "Graves", "Viego", "Lillia", "Elise", "Kha'Zix", "Rengar",
    "Shaco", "Evelynn", "Nocturne", "Kayn", "Vi", "Warwick", "Xin Zhao",
    "Udyr", "Jarvan IV", "Hecarim", "Amumu", "Sejuani", "Zac", "Rammus",
    "Maokai", "Nunu & Willump", "Ivern", "Taliyah", "Gragas", "Rek'Sai",
    "Skarner", "Bel'Veth", "Briar", "Naafiri", "Diana", "Pantheon", "Ekko",
    "Fiddlesticks", "Nidalee", "Kindred", "Wukong",
}

# ── Rol bazlı varsayılan buildler ─────────────────────────────────────────────
_ROLE_DEFAULTS: dict[str, dict[str, Any]] = {
    "ADC": {
        "tier": "B", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6672", "Kraken Slayer"), ("3031", "Infinity Edge"), ("3085", "Runaan's Hurricane")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Presence of Mind", "Legend: Bloodline", "Cut Down"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Ornn", "Sion", "Malphite"], "weak_vs": ["Zed", "LeBlanc", "Kha'Zix"],
        "matchups": {"Genel": "Pozisyonunu koru, geri kitle, ön cizginin arkasında kal"},
        "combos": ["AA → Q → W (temel kombinasyon)"],
        "tips": ["2 eşya gücüne kadar güvenli cs yap", "Takım dövüşünde ön çizginin arkasında dur", "En yakın hedefe odaklan, uzaklaşma"],
        "pro_build": "Standart ADC: Kraken Slayer → Infinity Edge → Runaan's Hurricane.",
        "playstyle": {"early": "2 eşyaya kadar cs yap, all-in'den kaçın", "mid": "Objelerde toplan, pozisyonunu koru", "late": "Yüksek DPS taşıyıcısı, her maliyetle hayatta kal"},
    },
    "Mid-Mage": {
        "tier": "B", "role": "Mid", "role_tr": "Orta (Büyücü)",
        "core_items": [("6655", "Luden's Tempest"), ("3089", "Rabadon's Deathcap"), ("3135", "Void Staff")],
        "situational": [("3157", "Zhonya's Hourglass"), ("3165", "Morellonomicon"), ("3115", "Nashor's Tooth")],
        "runes_primary": ("Sorcery", ["Arcane Comet", "Manaflow Band", "Transcendence", "Scorch"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Barrier",
        "strong_vs": ["Ornn", "Sion", "Malphite"], "weak_vs": ["Zed", "Talon", "Fizz"],
        "matchups": {"Genel": "Uzaktan poke yap, dalgayı kontrol et, all-in'den kaçın"},
        "combos": ["Q → W (poke kombinasyonu)"],
        "tips": ["Q ile cs yap, W ile poke at", "Takım dövüşünde güvenli pozisyonda dur", "Suikastçılara karşı Zhonya's kullan"],
        "pro_build": "Standart AP: Luden's Tempest → Rabadon's Deathcap → Void Staff.",
        "playstyle": {"early": "Güvenli cs yap, rakip hata yapınca poke at", "mid": "Objelerde toplan, menzilinle dövüşü kontrol et", "late": "Yüksek patlama hasarı, ön çizginin arkasında kal"},
    },
    "Mid-Assassin": {
        "tier": "B", "role": "Mid", "role_tr": "Orta (Suikastçı)",
        "core_items": [("6691", "Duskblade of Draktharr"), ("3071", "Black Cleaver"), ("6333", "Death's Dance")],
        "situational": [("3026", "Guardian Angel"), ("3139", "Mercurial Scimitar"), ("3156", "Maw of Malmortius")],
        "runes_primary": ("Domination", ["Electrocute", "Sudden Impact", "Eyeball Collection", "Relentless Hunter"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Teleport",
        "strong_vs": ["Lux", "Ziggs", "Xerath"], "weak_vs": ["Malzahar", "Lissandra", "Galio"],
        "matchups": {"Genel": "6. seviyeden sonra all-in yap, roam ile kar yakala, erken kar yap"},
        "combos": ["Q → E → W → R (patlama kombinasyonu)"],
        "tips": ["6. seviyede kill fırsatı ara", "Yan koridorlara roam yap, kar yakala", "Erken avantajını objelere dönüştür"],
        "pro_build": "Standart suikastçı: Duskblade → Black Cleaver → Death's Dance.",
        "playstyle": {"early": "6'ya kadar cs yap, kill fırsatı bekle", "mid": "Bot/Top'a roam yap, karla kartlan", "late": "İzole hedefleri sile, doğrudan dövüşten kaçın"},
    },
    "Top-Fighter": {
        "tier": "B", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6632", "Goredrinker"), ("3074", "Ravenous Hydra"), ("3026", "Guardian Angel")],
        "situational": [("3071", "Black Cleaver"), ("6333", "Death's Dance"), ("3153", "Blade of the Ruined King")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Ornn", "Sion", "Malphite"], "weak_vs": ["Vayne", "Quinn", "Teemo"],
        "matchups": {"Genel": "Rakip ana yeteneği soğuktayken takas yap"},
        "combos": ["Q → W → AA (temel takas)"],
        "tips": ["Rakip ana yeteneği soğuktayken takas yap", "Öndeyken bölücü it", "TP ile takım dövüşüne katıl"],
        "pro_build": "Standart dövüşçü: Goredrinker → Ravenous Hydra → Guardian Angel.",
        "playstyle": {"early": "Agresif takas yap, rünlerle sürdür", "mid": "Bölücü it tehdidi, TP ile dövüşlere katıl", "late": "Önden arkaya dövüşçü, taşıyıcılara dal"},
    },
    "Top-Tank": {
        "tier": "B", "role": "Top", "role_tr": "Üst (Tank)",
        "core_items": [("3068", "Sunfire Aegis"), ("3075", "Thornmail"), ("4401", "Force of Nature")],
        "situational": [("3193", "Gargoyle Stoneplate"), ("3143", "Randuin's Omen"), ("3065", "Warmog's Armor")],
        "runes_primary": ("Resolve", ["Grasp of the Undying", "Shield Bash", "Bone Plating", "Overgrowth"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Zırh / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Zed", "Talon", "Rengar"], "weak_vs": ["Vayne", "Fiora", "Gwen"],
        "matchups": {"Genel": "Grasp ile sürünür, direnç yığ"},
        "combos": ["Q → AA → W (Grasp takas)"],
        "tips": ["Düşman kadroya göre direnç yığ", "Dövüşlerde taşıyıcıları koru", "Ult ile engage yap"],
        "pro_build": "Standart tank: Sunfire Aegis → Thornmail → Force of Nature.",
        "playstyle": {"early": "Güvenli cs yap, Grasp ile sürünür", "mid": "Takım için ön çizgi ol, objeleri kontrol et", "late": "Ölümsüz ön çizgi, taşıyıcıları koru"},
    },
    "Jungle": {
        "tier": "B", "role": "Jungle", "role_tr": "Orman",
        "core_items": [("6630", "Eclipse"), ("3071", "Black Cleaver"), ("3026", "Guardian Angel")],
        "situational": [("3156", "Maw of Malmortius"), ("3139", "Mercurial Scimitar"), ("3074", "Ravenous Hydra")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Coup de Grace"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Smite", "spells_alt": "Ghost + Smite",
        "strong_vs": ["Lux", "Jinx", "Ashe"], "weak_vs": ["Udyr", "Trundle", "Bel'Veth"],
        "matchups": {"Genel": "Koridor itildiğinde gank yap, objeleri güvence altına al"},
        "combos": ["Q → AA → E (temizlik ve gank)"],
        "tips": ["Eşleşmeye göre full clear veya 3-kampta gank yap", "Scuttle'ları güven altına al", "Koridorlar itildiğinde karşı-gank bekle"],
        "pro_build": "Standart orman: Eclipse → Black Cleaver → Guardian Angel.",
        "playstyle": {"early": "Eşleşmeye göre full clear veya erken gank", "mid": "Objeleri güvence altına al, itiklen koridorlara gank", "late": "Arka hatta dal veya taşıyıcıları koru"},
    },
    "Support-Enchanter": {
        "tier": "B", "role": "Support", "role_tr": "Destek (Büyüleyici)",
        "core_items": [("2065", "Shurelya's Battlesong"), ("3119", "Ardent Censer"), ("3504", "Chemtech Putrifier")],
        "situational": [("3222", "Mikael's Blessing"), ("3109", "Knight's Vow"), ("3158", "Ionian Boots")],
        "runes_primary": ("Sorcery", ["Summon Aery", "Manaflow Band", "Transcendence", "Scorch"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "E > W > Q", "first_levels": "Q → W → E → E → E → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Leona", "Nautilus", "Blitzcrank"], "weak_vs": ["Thresh", "Bard", "Pyke"],
        "matchups": {"Genel": "ADC'nin arkasından poke at, kilitli engage'leri kalkanla"},
        "combos": ["E → Q (kalkanla poke)"],
        "tips": ["Takastan önce ADC'ye kalkan at", "Ult ile dövüşleri tersine çevir", "Nehir ve objeleri wardla"],
        "pro_build": "Standet büyüleyici: Shurelya's Battlesong → Ardent Censer.",
        "playstyle": {"early": "Poke ve kalkan at, nehri wardla", "mid": "ADC'yi takip et, kalkanla dövüşleri kazandır", "late": "Taşıyıcıyı güçlendir, kalkan için hayatta kal"},
    },
    "Support-Tank": {
        "tier": "B", "role": "Support", "role_tr": "Destek (Tank)",
        "core_items": [("3190", "Locket of the Iron Solari"), ("3109", "Knight's Vow"), ("3050", "Zeke's Convergence")],
        "situational": [("3222", "Mikael's Blessing"), ("3065", "Warmog's Armor"), ("3111", "Mercury's Treads")],
        "runes_primary": ("Resolve", ["Aftershock", "Font of Life", "Bone Plating", "Unflinching"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Zırh / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Jhin", "Senna", "Ashe"], "weak_vs": ["Morgana", "Bard", "Senna"],
        "matchups": {"Genel": "Düşman pozisyon hatası yapınca engage at"},
        "combos": ["Q → E → R (engage kombinasyonu)"],
        "tips": ["Düşman pozisyon hatası yapınca engage at", "CC ile taşıyıcıları koru", "Objeler için derin ward at"],
        "pro_build": "Standart tank destek: Locket → Knight's Vow → Zeke's.",
        "playstyle": {"early": "Engage açıları ara, ADC'yi koru", "mid": "Pick için roam yap, görüşü kontrol et", "late": "Ön çizgi ve engage, kritik hedefleri CC'le"},
    },
}

# ── Detaylı rehberler (38 popüler şampiyon, Türkçe) ───────────────────────────
_META_BUILDS: dict[str, dict[str, Any]] = {
    "jinx": {
        "tier": "S", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("3085", "Kraken Slayer"), ("3031", "Infinity Edge"), ("6672", "Runaan's Hurricane")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3072", "Bloodthirster")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Presence of Mind", "Legend: Bloodline", "Cut Down"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Jhin", "Kai'Sa", "Miss Fortune"], "weak_vs": ["Draven", "Samira", "Tristana"],
        "matchups": {"Jhin": "4. atışını bekle, şarjör değişiminde all-in yap", "Draven": "Erken takastan kaçın, 3 eşyaya kadar sürün", "Vayne": "Dalgayı erken it, skalasını geciktir"},
        "combos": ["AA → Q → W (poke)", "Q-roket → AA → W (uzun menzil tuzak)"],
        "tips": ["Takım dövüşünde AoE için Q roketlere geç", "Kaçış yolunu kesmek için E koru", "Ult ile haritada düşük HP hedefleri bitir"],
        "pro_build": "Yüksek elo: Kraken → IE → Hurricane. Tanklara karşı Lord Dom 3. olabilir.",
        "playstyle": {"early": "Güvenli cs yap, kule altında roketlerle it/poke", "mid": "Objelerde toplan, menzilin dövüşleri domine eder", "late": "Ön çizginin arkasında kal, roketler tüm takımı parçalar"},
    },
    "kaisa": {
        "tier": "S", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("3006", "Berserker's Greaves"), ("6671", "Kraken Slayer"), ("3091", "Wit's End"), ("6672", "Runaan's Hurricane")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Presence of Mind", "Legend: Bloodline", "Cut Down"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Jinx", "Aphelios", "Senna"], "weak_vs": ["Draven", "Samira", "Tristana"],
        "matchups": {"Jinx": "İzole olduğunda pasif + R ile all-in yap", "Senna": "Q poke'sundan kaçın, W kullandıktan sonra gir", "Draven": "6'dan önce takas yapma, erken hasarına saygı duy"},
        "combos": ["AA → Q → AA (patlama)", "R → Flash → Q + AA (all-in bitirici)"],
        "tips": ["Q evrimi için 100 AD topla, dalga temizleme ve patlama için", "W evrimi büyük poke menzili verir — 2. düşün", "Ult kalkan + yer değiştirme verir — agresif veya savunma kullan"],
        "pro_build": "AP Kai'Sa (Wit's End → Nashor's → Rabadon's) mümkün ama artık daha az yaygın.",
        "playstyle": {"early": "3 eşyaya kadar cs yap, ağır takastan kaçın", "mid": "İzole hedeflerde R all-in ara", "late": "Yüksek mobilite + DPS, kitle ve suikast yap"},
    },
    "vayne": {
        "tier": "A", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6672", "Kraken Slayer"), ("3153", "Blade of the Ruined King"), ("3085", "Runaan's Hurricane")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Triumph", "Legend: Alacrity", "Cut Down"]),
        "runes_secondary": ("Resolve", ["Conditioning", "Overgrowth"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "W > Q > E", "first_levels": "Q → W → E → W → W → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Ornn", "Sion", "Cho'Gath"], "weak_vs": ["Caitlyn", "Draven", "Lucian"],
        "matchups": {"Caitlyn": "Tuzaklardan kaçın, menzil takası yapma — outscale et", "Leona": "Zenith'den Q takla atarak kaç, engage'dan sonra condemn", "Draven": "Erken asla dövüşme, 2 eşya gücünde onu yenersin"},
        "combos": ["AA → Q → AA (reset)", "E → Flash (duvar stun açısı)"],
        "tips": ["Maksimum DPS için Q ile AA animasyonunu iptal et", "Condemn flash açıları kazanamayacağın düelloları kazandırır", "W gerçek hasar tankları eritir — dövüşlerde ön çizgiye odaklan"],
        "pro_build": "Bork rush + Kraken standart. Shieldbow tankı buildler artık nadir.",
        "playstyle": {"early": "Erken zayıf, gerekirse kule altında cs yap", "mid": "2 eşya gücü, çarpışmalara başla", "late": "En yüksek DPS ADC, kitle ve herkesi 3 vuruşta öldür"},
    },
    "jhin": {
        "tier": "B", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6671", "Kraken Slayer"), ("3094", "Rapid Firecannon"), ("3031", "Infinity Edge")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3158", "Youmuu's Ghostblade")],
        "runes_primary": ("Precision", ["Fleet Footwork", "Presence of Mind", "Legend: Bloodline", "Coup de Grace"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Jinx", "Aphelios", "Senna"], "weak_vs": ["Draven", "Lucian", "Kai'Sa"],
        "matchups": {"Kai'Sa": "4. atışla poke at, all-in yaptırma", "Leona": "Engage geldiğinde kendi üstüne tuzak koy", "Thresh": "4. atışı fener kalkanı için sakla"},
        "combos": ["4. atış → Q (infaz)", "W kök → R (uzun menzil kökten Perde Ateşi)"],
        "tips": ["4. atışı son vuruş ve poke için aynı anda zamanla", "E tuzakları dar geçit ve çalılarda görüş sağlar", "Ult dövüş başında veya düşük HP hedefleri bitirmek için en iyi"],
        "pro_build": "Rapid Firecannon 2. olarak 4. atış menzili artırmak pro standart.",
        "playstyle": {"early": "4. atışla poke yap, takas için cephane koru", "mid": "Menzil avantajıyla kule kuşat", "late": "Perde Ateşi dövüş alanını kontrol eder"},
    },
    "caitlyn": {
        "tier": "A", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6672", "Kraken Slayer"), ("3094", "Rapid Firecannon"), ("3031", "Infinity Edge")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Fleet Footwork", "Presence of Mind", "Legend: Bloodline", "Coup de Grace"]),
        "runes_secondary": ("Sorcery", ["Absolute Focus", "Gathering Storm"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Vayne", "Kai'Sa", "Nilah"], "weak_vs": ["Draven", "Samira", "Tristana"],
        "matchups": {"Vayne": "Menzil avantajını kullan, asla yakınlaşma", "Tristana": "Erken kadraç kontrolü yap, 6'dan önce kill ara", "Draven": "Kule altında it, asla düz takasa girme"},
        "combos": ["W → AA → Q → AA (tuzak baş kadraç)", "E → W → AA → Q → AA (kombin)"],
        "tips": ["W tuzakları kadraç kontrolü için kilit — her zaman yerleştir", "E + W kombini neredeyse garanti headshot verir", "En uzun menzilli ADC — her zaman mesafe koru"],
        "pro_build": "Kraken → Rapid Firecannon → IE standart. Stormrazor erken snowball için.",
        "playstyle": {"early": "Menzil avantajıyla kadraç it ve poke yap", "mid": "Kule kuşat ikonu ol, uzun menzille baskı yap", "late": "Headshot patlaması ile hedef erit, mesafeni koru"},
    },
    "tristana": {
        "tier": "B", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6672", "Kraken Slayer"), ("3031", "Infinity Edge"), ("3085", "Runaan's Hurricane")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Triumph", "Legend: Bloodline", "Cut Down"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → E → W → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Jinx", "Aphelios", "Jhin"], "weak_vs": ["Draven", "Caitlyn", "Varus"],
        "matchups": {"Caitlyn": "2 seviyede all-in, tuzak kadraçlarına dalma", "Jinx": "Erken all-in yap, skalasını geciktir", "Varus": "Q'dan kaçın, 6'da R ile all-in"},
        "combos": ["E → AA → Q → AA (bomb kombinasyonu)", "W → E → AA → Q → R (tam all-in)"],
        "tips": ["E bomb kadraçlarda patlama hasarı verir — itme ile kullan", "W engage veya kaçış için — dikkatli kullan", "R düşmanı iterek peele veya save için kullanılabilir"],
        "pro_build": "Kraken → IE → Hurricane standart. Tank karşı Bork 3.",
        "playstyle": {"early": "2 seviyede güçlü all-in, E bomb itme", "mid": "R ile engage veya kaçış, objelerde güçlü", "late": "En uzun menzilli ADC, kitle ve kule yık"},
    },
    "draven": {
        "tier": "A", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6671", "Kraken Slayer"), ("3031", "Infinity Edge"), ("6694", "The Collector")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Triumph", "Legend: Bloodline", "Coup de Grace"]),
        "runes_secondary": ("Domination", ["Taste of Blood", "Treasure Hunter"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Vayne", "Jinx", "Kai'Sa"], "weak_vs": ["Caitlyn", "Varus", "Miss Fortune"],
        "matchups": {"Vayne": "Erken her takası kazan, skalasına fırsat verme", "Caitlyn": "2 seviyede all-in, tuzak alanına girme", "Jinx": "Erken domine et, baskı yapmadan bırakma"},
        "combos": ["Q → AA → W → AA (baltaları yakala, yenile)", "E → AA → Q → AA → R (engage)"],
        "tips": ["Baltaları yakalamak hareket yönünü kontrol eder — bilinçli hareket et", "W atacını yenile, her kill sonra baltaları tut", "E ile engage ve kaçış engelle — çift yönlü"],
        "pro_build": "Kraken → Collector erken snowball standart. IE 2. veya 3.",
        "playstyle": {"early": "En güçlü erken ADC, her takası kazan", "mid": "Kar yığını ile domine, roam takip et", "late": "Baltalar devasa hasar verir, pozisyonunu koru"},
    },
    "yone": {
        "tier": "S", "role": "Mid", "role_tr": "Orta",
        "core_items": [("3031", "Infinity Edge"), ("6672", "Kraken Slayer"), ("3074", "Ravenous Hydra")],
        "situational": [("3026", "Guardian Angel"), ("3139", "Mercurial Scimitar"), ("3161", "Spear of Shojin")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Triumph", "Legend: Alacrity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Saldırı Hızı / Uygun / Sihir Direnci",
        "skill_priority": "Q > E > W", "first_levels": "Q → E → W → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Syndra", "Lux", "Xerath"], "weak_vs": ["Akali", "Fizz", "Zed"],
        "matchups": {"Zed": "Ult atınca W kullan, E2 ile shurikenlerden kaçın", "Syndra": "Scatter'dan kaçın, 6'dan sonra R + E ile all-in", "Akali": "6 öncesi cezalandır, 6 sonrası W'sinin bitmesini bekle"},
        "combos": ["Q3 → E → R → Q (yükseltme zinciri)", "E → AA → Q → AA → E2 (kısa takas)"],
        "tips": ["Q3 → R birden fazla hedefi yükseltmeyi garanti eder", "E geri dönüş hasarı alır — patlama takasları için kullan", "W kalkan AD ile ölçeklenir, dövüş ortasında hayatta kalmak için kullan"],
        "pro_build": "IE rush + Kraken yüksek elo standart. Hydra 3. dalga temizleme + sürünür.",
        "playstyle": {"early": "Q ile cs yap, rakip yetenek kullanınca kısa E takasları", "mid": "Q3 + R ile bot'a roam, Hydra ile bölücü it", "late": "E ile kanat değiştir, Q3 + R ile arka hatta CC zinciri"},
    },
    "yasuo": {
        "tier": "S", "role": "Mid", "role_tr": "Orta",
        "core_items": [("6672", "Kraken Slayer"), ("3031", "Infinity Edge"), ("3074", "Ravenous Hydra")],
        "situational": [("3026", "Guardian Angel"), ("3139", "Mercurial Scimitar"), ("3161", "Spear of Shojin")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Triumph", "Legend: Alacrity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Saldırı Hızı / Uygun / Sihir Direnci",
        "skill_priority": "Q > E > W", "first_levels": "Q → E → W → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Syndra", "Lux", "Veigar"], "weak_vs": ["Akali", "Fizz", "Malzahar"],
        "matchups": {"Zed": "Rüzgar Duvarı ile shurikenlerini engelle, ult atınca ult at", "Akali": "6 öncesi E ile zorla, 6 sonrası W süresini bekle", "Malzahar": "QSS al, ult'ü en büyük tehdit"},
        "combos": ["Q3 → R (yükseltme ult)", "Minyonlardan E → Q → E → AA (dash takas)"],
        "tips": ["Rüzgar Duvarı tüm yönlerden mermileri engeller", "E dash ile minionlardan pozisyon değiştir", "Pasif kalkan hareketle yenilenir — son vuruşlar arasında yürü"],
        "pro_build": "Kraken sonrası IE rush standart. Hydra 3. dalga temizleme.",
        "playstyle": {"early": "Q ile cs yap, E ile yetenek kaçır", "mid": "Q3 sonrası all-in, yükseltme kurulumuyla roam", "late": "Takım dövüşü kanat değiştirme, Rüzgar Duvarı takım için"},
    },
    "zed": {
        "tier": "A", "role": "Mid", "role_tr": "Orta",
        "core_items": [("6691", "Duskblade of Draktharr"), ("3071", "Black Cleaver"), ("6333", "Death's Dance")],
        "situational": [("3026", "Guardian Angel"), ("3142", "Edge of Night"), ("3156", "Maw of Malmortius")],
        "runes_primary": ("Domination", ["Electrocute", "Sudden Impact", "Eyeball Collection", "Ultimate Hunter"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Teleport",
        "strong_vs": ["Lux", "Ziggs", "Xerath"], "weak_vs": ["Malzahar", "Lissandra", "Kayle"],
        "matchups": {"Ahri": "Charm'ı dodge'la, ult atınca W ile arkasına geç", "Malzahar": "QSS rush, ult'ü en büyük tehdit", "Syndra": "6 öncesi poke yap, 6 sonrası W + R ile one-shot"},
        "combos": ["W → E → Q (poke/kısa takas)", "R → W → E → Q → AA (tam all-in)"],
        "tips": ["W gölge pozisyonu one-shot kombini için kritik", "R sonrası W gölgesi ile 3 gölgeye çık — hasar patlaması", "Gölge ile karıştır, rakip hangisinin gerçek olduğunu bilemesin"],
        "pro_build": "Duskblade → Cleaver standart. GA 3. dövüş güvenliği.",
        "playstyle": {"early": "6'ya kadar poke yap, kill fırsatı bekle", "mid": "Roam yap, izole hedefleri one-shot", "late": "Karışık gölge komboları, squishy hedefleri sil"},
    },
    "ahri": {
        "tier": "A", "role": "Mid", "role_tr": "Orta",
        "core_items": [("6655", "Luden's Tempest"), ("3100", "Lich Bane"), ("3089", "Rabadon's Deathcap")],
        "situational": [("3157", "Zhonya's Hourglass"), ("3135", "Void Staff"), ("3165", "Morellonomicon")],
        "runes_primary": ("Domination", ["Electrocute", "Cheap Shot", "Eyeball Collection", "Ultimate Hunter"]),
        "runes_secondary": ("Sorcery", ["Manaflow Band", "Transcendence"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Lux", "Ziggs", "Xerath"], "weak_vs": ["Yasuo", "Zed", "LeBlanc"],
        "matchups": {"Yasuo": "Minyon dalgasından Q at, Rüzgar Duvarı kapalıyken charm", "Zed": "Ult atınca charm, ult ile arkasına geç", "Lux": "Işık Bağlaması'dan kaçın, Q kaçırdıktan sonra all-in"},
        "combos": ["E → W → Q (Electrocute patlat)", "R → E → W → Q → R (kovma kombosu)"],
        "tips": ["CC'li hedeflerde charm garanti vuruş", "Q dönüşü gerçek hasar — her iki geçiş için pozisyonlan", "Ult şarjları kill'de sıfırlanır — dövüşte saldır"],
        "pro_build": "Luden's → Lich Bane standart. Everfrost rework sonrası ölü.",
        "playstyle": {"early": "Q ile cs yap, charm ile takas", "mid": "R ile roam, izole düşmanları pick'le", "late": "Takım dövüşü suikastçısı, R şarjlarıyla yer değiştir"},
    },
    "syndra": {
        "tier": "A", "role": "Mid", "role_tr": "Orta",
        "core_items": [("3089", "Rabadon's Deathcap"), ("3115", "Nashor's Tooth"), ("6655", "Luden's Tempest")],
        "situational": [("3165", "Morellonomicon"), ("3157", "Zhonya's Hourglass"), ("3135", "Void Staff")],
        "runes_primary": ("Sorcery", ["Arcane Comet", "Manaflow Band", "Transcendence", "Scorch"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Barrier",
        "strong_vs": ["Veigar", "Lux", "Ziggs"], "weak_vs": ["Zed", "Yasuo", "Fizz"],
        "matchups": {"Zed": "Barrier + stopwatch rush, kule altında ult", "Yasuo": "Rüzgar Duvarı arkasından Q, dash yapınca E", "Fizz": "6 öncesi zorla, E engage'ini koru"},
        "combos": ["Q → E (scatter stun)", "Q → W → E → R (tam patlama)"],
        "tips": ["Q sonrası Scatter Açısı (E) stun garantiler", "Ult hasarı pasif kürelerle ölçeklenir", "W minion ve orman kampları kaldırır — ekstra poke"],
        "pro_build": "Luden's → Rabadon's standart. Suikastçıya karşı Crown.",
        "playstyle": {"early": "Q ile poke, Scatter ile koridor kontrolü", "mid": "E stun ile pick, R patlamasıyla obje kontrolü", "late": "Squishy'leri one-shot, Scatter ile peele"},
    },
    "malphite": {
        "tier": "A", "role": "Top", "role_tr": "Üst (Tank)",
        "core_items": [("3068", "Sunfire Aegis"), ("3075", "Thornmail"), ("4401", "Force of Nature")],
        "situational": [("3193", "Gargoyle Stoneplate"), ("3143", "Randuin's Omen"), ("3157", "Zhonya's Hourglass")],
        "runes_primary": ("Resolve", ["Grasp of the Undying", "Shield Bash", "Bone Plating", "Overgrowth"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Zırh / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Yasuo", "Yone", "Zed"], "weak_vs": ["Vayne", "Fiora", "Gwen"],
        "matchups": {"Yasuo": "Rüzgar Duvarı işe yaramaz, Q ile sürekli poke", "Vayne": "6'da R engage ile burstla, uzun dövüşten kaçın", "Fiora": "W ult'ını kullan, Q ile güvenli takas"},
        "combos": ["R → Q → E → W (tam engage)", "Q → AA → E (Grasp takas)"],
        "tips": ["R en güçlü engage yeteneklerinden — rakip grubu hedefle", "AP veya tank build seç — kadroya göre karar ver", "E saldırı hızını düşürür — AA bağımlılara karşı güçlü"],
        "pro_build": "Tank: Sunfire → Thornmail → FoN. AP: Luden's → Shadowflame.",
        "playstyle": {"early": "Q ile güvenli poke, Grasp ile sürünür", "mid": "R engage ile dövüş başlat, objeleri kontrol et", "late": "R ile 5 kişiyi havaya uçur, takımını taşı"},
    },
    "darius": {
        "tier": "A", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6632", "Goredrinker"), ("3074", "Ravenous Hydra"), ("3071", "Black Cleaver")],
        "situational": [("6333", "Death's Dance"), ("3026", "Guardian Angel"), ("3153", "Blade of the Ruined King")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Ghost", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Ornn", "Sion", "Nasus"], "weak_vs": ["Vayne", "Quinn", "Gnar"],
        "matchups": {"Vayne": "6'da Ghost + E ile yakala, menzil bırakma", "Garen": "W'sını bekle, Q dış çemberiyle sürünür", "Renekton": "6 öncesi saygılı oyna, sonrası tüm düelloları kazan"},
        "combos": ["E → AA → W → AA → Q (çek + tam kombinasyon)", "AA → W → AA → R (5 pasif ult)"],
        "tips": ["Q dış çemberi sürünür ve hasar verir — her zaman dış çember vurma", "5 pasif ult gerçek hasar — dövüşte pasif biriktir", "Ghost ile kaçan hedefleri kovala"],
        "pro_build": "Goredrinker → Hydra → Cleaver standart. DD 4. sürünür.",
        "playstyle": {"early": "Q dış çember ile sürünür, agresif takas", "mid": "Bölücü it tehdidi, 1v1 kralı", "late": "5 pasif R gerçek hasarla temizle"},
    },
    "garen": {
        "tier": "A", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6631", "Eclipse"), ("3071", "Black Cleaver"), ("6333", "Death's Dance")],
        "situational": [("3026", "Guardian Angel"), ("3074", "Ravenous Hydra"), ("4401", "Force of Nature")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → E → W → Q → Q → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Teleport",
        "strong_vs": ["Syndra", "Lux", "Malzahar"], "weak_vs": ["Vayne", "Quinn", "Teemo"],
        "matchups": {"Darius": "Q dış çemberini W ile engelle, kısa takas yap", "Teemo": "6'da Q + E + R ile one-shot, kör olmadan yaklaş", "Vayne": "Q hızlı yaklaş, R'den kaçınma"},
        "combos": ["Q → AA → E → R (hızlı burst)", "Q → E (dönerek süpürme)"],
        "tips": ["Q sessizlik verir — büyü bağımlılara karşı güçlü", "W pasif süresi büyük sürünür sağlar — kısa takaslar için ideal", "R düşük HP hedefe gerçek hasar — kesici yetenek"],
        "pro_build": "Eclipse → Cleaver → DD standart. Hydra bölücü it için.",
        "playstyle": {"early": "Q kısa takaslar, W ile sürünür", "mid": "Q hız + E süpürme ile bölücü it", "late": "Villain R gerçek hasar, squishy'leri kes"},
    },
    "aatrox": {
        "tier": "S", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6631", "Eclipse"), ("3071", "Black Cleaver"), ("6333", "Death's Dance")],
        "situational": [("3026", "Guardian Angel"), ("3074", "Ravenous Hydra"), ("3161", "Spear of Shojin")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Revitalize"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Ornn", "Sion", "Cho'Gath"], "weak_vs": ["Fiora", "Camille", "Gwen"],
        "matchups": {"Fiora": "W'sini E ile kışkırt, bittikten sonra Q2/3 at", "Camille": "E süresini cezalandır, o E'siz zayıf", "Gwen": "6'dan önce all-in, W Q tatlı noktanı engeller"},
        "combos": ["Q1 → E → Q2 → Q3 (tam kombinasyon)", "W → Q1 → E → Q2 (çekip tatlı nokta)"],
        "tips": ["Q tatlı nokta (uç) sürünür ve bonus hasar verir", "Ult tüm sürünürmeyi artırır — pasifle birleştir", "E duvarlardan kaçış veya beklenmeyen gank açıları için"],
        "pro_build": "Eclipse → Cleaver → DD standart. Hydra 3. dalga temizleme.",
        "playstyle": {"early": "Q tatlı noktalarıyla takas, pasifle sürünür", "mid": "Cleaver ile bölücü it, TP ile dövüşlere katıl", "late": "Ön çizgi dövüşçüsü, tüm dövüşte sürünür"},
    },
    "fiora": {
        "tier": "S", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6632", "Goredrinker"), ("3074", "Ravenous Hydra"), ("3153", "Blade of the Ruined King")],
        "situational": [("3026", "Guardian Angel"), ("3139", "Mercurial Scimitar"), ("3071", "Black Cleaver")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Bloodline", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Demolish", "Second Wind"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → E → W → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Ornn", "Sion", "Malphite"], "weak_vs": ["Akali", "Jax", "Gwen"],
        "matchups": {"Jax": "Stun'ını W ile engelle, E'si kapalıyken vitallere Q", "Gwen": "W'sinden önce all-in, gerçek hasarın onu yener", "Malphite": "Ult'ını W ile engelle, sürünmek için vitallere Q"},
        "combos": ["Q → AA → E → AA (vital patlama)", "R → Vital'lere Q → W (CC engelle)"],
        "tips": ["Vitallere vuruş sürünür + hareket hızı verir — etrafında kitle", "W tüm sert CC'yi engeller — ult'ları zamanla", "R vitalleri devasa AoE sürünür alanı verir — içinde dövüş"],
        "pro_build": "Goredrinker → Hydra standart. Bork 3. tank eritme.",
        "playstyle": {"early": "Q vitalleri ile takas, pasifle sürünür", "mid": "Bölücü it tehdidi, 1v1 düellocu", "late": "En yüksek DPS üst şampiyonu, R ile arka hatta dal"},
    },
    "viego": {
        "tier": "S", "role": "Jungle", "role_tr": "Orman",
        "core_items": [("6672", "Kraken Slayer"), ("3153", "Blade of the Ruined King"), ("3074", "Ravenous Hydra")],
        "situational": [("3026", "Guardian Angel"), ("3139", "Mercurial Scimitar"), ("3161", "Spear of Shojin")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Alacrity", "Coup de Grace"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Smite", "spells_alt": "Ghost + Smite",
        "strong_vs": ["Elise", "Lee Sin", "Graves"], "weak_vs": ["Udyr", "Kindred", "Trundle"],
        "matchups": {"Lee Sin": "Q'dan kaçın, kombo kaçırdıktan sonra dövüş", "Elise": "Cocoon vurunca W, sonrası all-in", "Graves": "Şarj değişimine E ile gir, pasifle reset"},
        "combos": ["W → Q → AA (poke)", "R → W → Q → AA → reset (tam patlama)"],
        "tips": ["Hayalet Possession cooldown'ları sıfırlar — dövüşte kill zincirle", "E sisi görünmezlik verir — gank açıları için kullan", "Q2 sürünür — orman ve düelloda sürünmek için"],
        "pro_build": "Kraken → Bork → Hydra standart. GA 4. dövüş resetleri.",
        "playstyle": {"early": "6'ya kadar cs yap, E görünmezliği ile gank", "mid": "İşgal ve çarpışma, possession dövüşleri tersine çevirir", "late": "Pasif resetlerle dövüş, taşıyıcıları possess et"},
    },
    "lee sin": {
        "tier": "S", "role": "Jungle", "role_tr": "Orman",
        "core_items": [("6630", "Eclipse"), ("3071", "Black Cleaver"), ("3161", "Spear of Shojin")],
        "situational": [("3026", "Guardian Angel"), ("3074", "Ravenous Hydra"), ("6333", "Death's Dance")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Smite", "spells_alt": "Ignite + Smite",
        "strong_vs": ["Graves", "Kindred", "Lillia"], "weak_vs": ["Udyr", "Trundle", "Bel'Veth"],
        "matchups": {"Graves": "Duvarlardan Q at, takımına tekmele", "Udyr": "Bear duruşunu kitle, kapalıyken dövüş", "Kindred": "Ult'sinde ult at — düşmanları dışarı tekmele"},
        "combos": ["Q → Q → W → E → R (insec)", "Flash → R → Q (flash kick kurulumu)"],
        "tips": ["Insec (W arkaya → R) imza hamlesi — pratik yap", "Q orman kamplarında mobilite ve görüş için", "W müttefik kalkanı — dövüşlerde taşıyıcıları kurtar"],
        "pro_build": "Eclipse → Cleaver çekirdek. Goredrinker dövüş sürünür için.",
        "playstyle": {"early": "Agresif ganklar, koridorları kar kartlan", "mid": "R tekirmeleriyle obje kontrolü, görüş oyunu", "late": "R ile peele veya taşıyıcıyı takımına tekmele"},
    },
    "graves": {
        "tier": "A", "role": "Jungle", "role_tr": "Orman",
        "core_items": [("6672", "Kraken Slayer"), ("3074", "Ravenous Hydra"), ("3031", "Infinity Edge")],
        "situational": [("3026", "Guardian Angel"), ("3139", "Mercurial Scimitar"), ("3071", "Black Cleaver")],
        "runes_primary": ("Precision", ["Fleet Footwork", "Triumph", "Legend: Alacrity", "Coup de Grace"]),
        "runes_secondary": ("Domination", ["Sudden Impact", "Treasure Hunter"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → E → W → Q → Q → R",
        "spells": "Flash + Smite", "spells_alt": "Ghost + Smite",
        "strong_vs": ["Elise", "Nidalee", "Kindred"], "weak_vs": ["Lee Sin", "Kha'Zix", "Udyr"],
        "matchups": {"Lee Sin": "E'sini engage için koru, Q menziliyle kitle", "Kha'Zix": "Birlikte ol — izolasyonu dövüşlerde işe yaramaz", "Udyr": "Uzaktan poke et, arayı kapatmasın"},
        "combos": ["Q → AA → E (oto reset)", "W → R → Q (sis + patlama)"],
        "tips": ["E zırh yığar — dövüşlerden önce yığınları koru", "Q dar alanlarda duvarlardan seker — patlama hasarı", "Duman Perdesi (W) görüş reddeder — objelerde kullan"],
        "pro_build": "Kraken → Hydra → IE standart. Collector erken snowball.",
        "playstyle": {"early": "Hızlı temizle, E zırh yığınlarıyla işgal", "mid": "Obje kontrolü, sis perdesi ile pick", "late": "Yüksek DPS önden arkaya, E yığınlarını koru"},
    },
    "lillia": {
        "tier": "A", "role": "Jungle", "role_tr": "Orman",
        "core_items": [("3152", "Liandry's Anguish"), ("3115", "Nashor's Tooth"), ("3089", "Rabadon's Deathcap")],
        "situational": [("3157", "Zhonya's Hourglass"), ("3135", "Void Staff"), ("3165", "Morellonomicon")],
        "runes_primary": ("Sorcery", ["Phase Rush", "Nimbus Cloak", "Celerity", "Waterwalking"]),
        "runes_secondary": ("Domination", ["Cheap Shot", "Treasure Hunter"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Smite", "spells_alt": "Ghost + Smite",
        "strong_vs": ["Amumu", "Sejuani", "Zac"], "weak_vs": ["Lee Sin", "Graves", "Kha'Zix"],
        "matchups": {"Lee Sin": "Engage'ini kitle, commit edince ult at", "Graves": "Outscale et, dövüşün daha iyi", "Kha'Zix": "Dövüşler için toplan, 1v1 kazanır"},
        "combos": ["Q → W (merkez vuruş)", "E → R (harita genelinde uyku)"],
        "tips": ["Pasif hareket hızı çarpışmalarda yakalanmaz yapar", "W merkezi gerçek hasar verir — dikkatle pozisyonlan", "R pasif yığınlı tüm düşmanları uyutur — önce E at"],
        "pro_build": "Liandry's → Nashor's standart. Zhonya's ağır AD'ye karşı.",
        "playstyle": {"early": "Hızlı temizle, gankları hızla kitle", "mid": "Obje kontrolü, E+R uyku pick'leri", "late": "AoE uyku dövüş, tankları erit"},
    },
    "thresh": {
        "tier": "S", "role": "Support", "role_tr": "Destek (Tank)",
        "core_items": [("3190", "Locket of the Iron Solari"), ("3109", "Knight's Vow"), ("3050", "Zeke's Convergence")],
        "situational": [("3222", "Mikael's Blessing"), ("3065", "Warmog's Armor"), ("3111", "Mercury's Treads")],
        "runes_primary": ("Resolve", ["Aftershock", "Font of Life", "Bone Plating", "Unflinching"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Zırh / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Leona", "Nautilus", "Blitzcrank"], "weak_vs": ["Morgana", "Bard", "Senna"],
        "matchups": {"Leona": "Zenith'ini E ile it, hook sonra at", "Morgana": "Siyah Kalkan kışkırt, kapalıyken hook at", "Senna": "Q rüzgarını it, ignite ile all-in"},
        "combos": ["Q → E → R (ölüm cezası)", "W → Q → Fener kurtarma (peele)"],
        "tips": ["Fener her şeyden kurtarır — kullanımını iletiş", "Süpürme dash'leri iptal eder — engage'leri zamanla", "Ölüm Cezası (Q) flash açıları düşmanı şaşırtır"],
        "pro_build": "Locket → Knight's Vow standart. Ağır CC'ye Mikael's.",
        "playstyle": {"early": "Koridor çalısında hook açıları, süpürme engage iptal", "mid": "Hook ile roam, harita genelinde fener kurtarma", "late": "Q ile pick, kutu dövüş alanını kontrol eder"},
    },
    "lulu": {
        "tier": "A", "role": "Support", "role_tr": "Destek (Büyüleyici)",
        "core_items": [("2065", "Shurelya's Battlesong"), ("3119", "Ardent Censer"), ("3504", "Chemtech Putrifier")],
        "situational": [("3222", "Mikael's Blessing"), ("3109", "Knight's Vow"), ("3158", "Ionian Boots")],
        "runes_primary": ("Sorcery", ["Summon Aery", "Manaflow Band", "Transcendence", "Scorch"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "E > W > Q", "first_levels": "Q → W → E → E → E → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Leona", "Nautilus", "Blitzcrank"], "weak_vs": ["Thresh", "Bard", "Nami"],
        "matchups": {"Leona": "W engage'ini iptal et, E ADC'ye kalkan, geri kitle", "Thresh": "Hook atınca W, E ADC'ye kalkan", "Nami": "E ile sürünür, Q baloncuktan kaçın"},
        "combos": ["E → Q (Pix ile poke)", "W müttefik → R (steroid + yükseltme zinciri)"],
        "tips": ["Pix hedefte kalır — çift menzil için Q ondan geçir", "W düşmanda zararsız sincaba çevirir", "R devasa AoE yavaşlatma + HP verir — dövüşleri tersine çevir"],
        "pro_build": "Shurelya's → Ardent standart. Redemption takım sürünür gerekirse.",
        "playstyle": {"early": "Q ile poke, E kalkan takasları", "mid": "ADC'yi takip et, W engage, R dövüşleri kazandır", "late": "Taşıyıcı güçlendirici, suikastçıları polymorph"},
    },
    "blitzcrank": {
        "tier": "B", "role": "Support", "role_tr": "Destek (Tank)",
        "core_items": [("2065", "Shurelya's Battlesong"), ("3050", "Zeke's Convergence"), ("3109", "Knight's Vow")],
        "situational": [("3222", "Mikael's Blessing"), ("3065", "Warmog's Armor"), ("3111", "Mercury's Treads")],
        "runes_primary": ("Resolve", ["Aftershock", "Font of Life", "Bone Plating", "Unflinching"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Zırh / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Senna", "Jhin", "Aphelios"], "weak_vs": ["Morgana", "Thresh", "Leona"],
        "matchups": {"Morgana": "Siyah Kalkan kışkırt, süresi dolunca hook at", "Thresh": "O seni hooklamadan önce onu hookla", "Leona": "E'sini it, commit ettikten sonra hook at"},
        "combos": ["Q → E → R (one-shot kombosu)", "W → Q → Flash (flash hook sürprizi)"],
        "tips": ["Sis veya çalılardan hook — sürpriz için", "E hook sonrası yükseltir — zincir CC garanti", "R sessizlik verir — düşman yeteneklerini durdur"],
        "pro_build": "Shurelya's takım mobilitesi. Knight's Vow taşıyıcıya bağla.",
        "playstyle": {"early": "Koridor çalısında hook açıları, hareketsiz ADC'leri cezalandır", "mid": "Q ile pick, R sessizlik obje kontrolü", "late": "Squishy'leri one-shot, hook dövüşleri kazandır"},
    },
    "leona": {
        "tier": "A", "role": "Support", "role_tr": "Destek (Tank)",
        "core_items": [("3190", "Locket of the Iron Solari"), ("3109", "Knight's Vow"), ("3050", "Zeke's Convergence")],
        "situational": [("3222", "Mikael's Blessing"), ("3065", "Warmog's Armor"), ("3143", "Randuin's Omen")],
        "runes_primary": ("Resolve", ["Aftershock", "Font of Life", "Bone Plating", "Unflinching"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Zırh / Zırh",
        "skill_priority": "W > E > Q", "first_levels": "Q → W → E → W → W → R",
        "spells": "Flash + Ignite", "spells_alt": "Flash + Exhaust",
        "strong_vs": ["Senna", "Yuumi", "Soraka"], "weak_vs": ["Morgana", "Thresh", "Janna"],
        "matchups": {"Morgana": "Kalkan süresini bekle, kapalıyken E → Q", "Thresh": "E önce at, hook'dan önce engage", "Janna": "W hız engelleyemez, R engage ile sıkıştır"},
        "combos": ["E → AA → Q → R (tam engage zinciri)", "R → E → Q (uzun menzil engage)"],
        "tips": ["R uzun menzilliAoE kök — uzaktan dövüş başlat", "W + pasif büyük sürünür — kısa takaslarda güçlü", "E → Q combo neredeyse kesin CC zinciri"],
        "pro_build": "Locket → Knight's Vow standart. Warmog's sürünür için.",
        "playstyle": {"early": "2 seviyede güçlü all-in, E → Q ile lock down", "mid": "R ile roam ve pick, obje kontrolü", "late": "AoE CC ile dövüş başlat, taşıyıcıları koru"},
    },
    "lux": {
        "tier": "B", "role": "Mid", "role_tr": "Orta (Büyücü)",
        "core_items": [("6655", "Luden's Tempest"), ("3089", "Rabadon's Deathcap"), ("3135", "Void Staff")],
        "situational": [("3157", "Zhonya's Hourglass"), ("3165", "Morellonomicon"), ("4633", "Mejai's Soulstealer")],
        "runes_primary": ("Sorcery", ["Arcane Comet", "Manaflow Band", "Transcendence", "Scorch"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "E > Q > W", "first_levels": "Q → E → W → E → E → R",
        "spells": "Flash + Barrier", "spells_alt": "Flash + Teleport",
        "strong_vs": ["Veigar", "Annie", "Malzahar"], "weak_vs": ["Zed", "Fizz", "Akali"],
        "matchups": {"Zed": "Q ile güvenli poke, E kök atınca kaçma, Zhonya rush", "Ahri": "Menzil avantajı kullan, charm'den kaçın", "Fizz": "6 öncesi zorla, E dalışından kaçın"},
        "combos": ["Q → E → R (patlama kombosu)", "E → Q → R (alan kontrolü)"],
        "tips": ["E görüş sağlar — çalılarda ve objelerde kullan", "Q kök iki hedefe çarpabilir — doğru açı ile ikili kill", "R menzili devasa — harita genelinde ult ile assist/kill"],
        "pro_build": "Luden's → Rabadon's standart. Mejai kar yığını ile.",
        "playstyle": {"early": "E ile güvenli poke, Q ile kök takasları", "mid": "R ile harita boyunca kill/assist, obje kontrolü", "late": "Uzun menzil patlama hasarı, ön çizginin arkasında"},
    },
    "morgana": {
        "tier": "B", "role": "Support", "role_tr": "Destek (Büyüleyici)",
        "core_items": [("4005", "Moonstone Renewer"), ("3119", "Ardent Censer"), ("3504", "Chemtech Putrifier")],
        "situational": [("3222", "Mikael's Blessing"), ("3157", "Zhonya's Hourglass"), ("3165", "Morellonomicon")],
        "runes_primary": ("Sorcery", ["Summon Aery", "Manaflow Band", "Transcendence", "Scorch"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "W > Q > E", "first_levels": "Q → W → E → W → W → R",
        "spells": "Flash + Exhaust", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Blitzcrank", "Thresh", "Leona"], "weak_vs": ["Braum", "Sivir", "Nami"],
        "matchups": {"Blitzcrank": "E kalkan hook'u engeller, Q ile cezalandır", "Thresh": "E ile ADC'yi koru, Q ile karşı engage", "Nami": "Q'dan kaçın, W ile sürünür savaşı"},
        "combos": ["Q → W (kök + hasar alanı)", "R → Q → W (Zhonya ile tam dövüş)"],
        "tips": ["E Siyah Kalkan tüm CC'yi engeller — taşıyıcıya zamanla", "Q 3 saniye kök — en uzun CC'lerden", "R + Zhonya güvenli AoE stun kombosu"],
        "pro_build": "Moonstone → Ardent standart. Zhonya R kombosu için.",
        "playstyle": {"early": "Q ile poke ve engage, E ile ADC koru", "mid": "R ile dövüş başlat, Zhonya ile güvenli", "late": "Siyah Kalkan taşıyıcıyı korur, R AoE stun"},
    },
    "ekko": {
        "tier": "A", "role": "Mid", "role_tr": "Orta (Suikastçı)",
        "core_items": [("6691", "Duskblade of Draktharr"), ("3115", "Nashor's Tooth"), ("3089", "Rabadon's Deathcap")],
        "situational": [("3157", "Zhonya's Hourglass"), ("3135", "Void Staff"), ("3165", "Morellonomicon")],
        "runes_primary": ("Domination", ["Electrocute", "Sudden Impact", "Eyeball Collection", "Relentless Hunter"]),
        "runes_secondary": ("Sorcery", ["Absolute Focus", "Gathering Storm"]),
        "shards": "Uygun / Uygun / Sihir Direnci",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Lux", "Ziggs", "Veigar"], "weak_vs": ["Malzahar", "Galio", "Annie"],
        "matchups": {"Zed": "Ult'ten R ile kaçın, stun alanı ile karşı engage", "Ahri": "Charm'dan kaçın, Q dönüş hasarı ile outplay", "Syndra": "6'da W alanı + R ile one-shot"},
        "combos": ["Q → E → AA (proc Elektrocute)", "W alanı → R (stun + dönüş patlama)"],
        "tips": ["R 4 saniye geriye dön + sürünür — agresif oyna, R ile güvenli çık", "W stun alanı dövüş başlatmak için mükemmel", "Q dönüşü yavaşlatır — kitleme ve poke için"],
        "pro_build": "Duskblade → Nashor's standart. AP veya hybrid build.",
        "playstyle": {"early": "Q ile poke, E ile kısa takaslar", "mid": "Roam yap, W stun alanı ile pick", "late": "R ile agresif dala, düşük HP'ye dönüş patlaması"},
    },
    "renekton": {
        "tier": "A", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6631", "Eclipse"), ("3071", "Black Cleaver"), ("6333", "Death's Dance")],
        "situational": [("3026", "Guardian Angel"), ("3074", "Ravenous Hydra"), ("3161", "Spear of Shojin")],
        "runes_primary": ("Precision", ["Press the Attack", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Uygun / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Garen", "Darius", "Nasus"], "weak_vs": ["Quinn", "Vayne", "Gwen"],
        "matchups": {"Darius": "50 fury W ile outtrade, Q dış çemberinden kaçın", "Garen": "Kısa takaslar yap, W sessizlik ile dövüşü kontrol et", "Jax": "E'sini bekle, W stun sonra at"},
        "combos": ["E → AA → W → Q → E (tam all-in)", "AA → W → Q (kısa fury takas)"],
        "tips": ["50+ fury W iki kez ısırır — devasa patlama hasarı", "E iki kullanım — biri engage biri kaçış", "R sürünür + boyut artışı — dövüşlerde korkutucu"],
        "pro_build": "Eclipse → Cleaver → DD standart. Hydra bölücü it.",
        "playstyle": {"early": "Fury ile agresif domine, W ile kill baskısı", "mid": "Bölücü it, 1v1 güçlü", "late": "R ile dövüş başlat, fury W ile burst"},
    },
    "sett": {
        "tier": "A", "role": "Top", "role_tr": "Üst (Dövüşçü)",
        "core_items": [("6632", "Goredrinker"), ("3074", "Ravenous Hydra"), ("3071", "Black Cleaver")],
        "situational": [("6333", "Death's Dance"), ("3026", "Guardian Angel"), ("3153", "Blade of the Ruined King")],
        "runes_primary": ("Precision", ["Conqueror", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Second Wind", "Overgrowth"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Teleport", "spells_alt": "Flash + Ignite",
        "strong_vs": ["Darius", "Garen", "Nasus"], "weak_vs": ["Vayne", "Quinn", "Gnar"],
        "matchups": {"Darius": "Q dış çemberinden kaçın, W hayatta kalmak için kullan", "Garen": "W sessizliğinden sonra Q ile takas", "Vayne": "E ile yakala, R ile taşıyı takımına taşı"},
        "combos": ["E → AA → Q → W (çek + patlama)", "R → E → Q → W (dövüş başlatma)"],
        "tips": ["W geri dönüş hasarı aldığın hasara göre ölçeklenir — dövüşte beklet", "R düşmanı arkana atar — kule/team'e doğru taşı", "E iki tarafında hedef varsa her ikisini de çeker"],
        "pro_build": "Goredrinker → Hydra → Cleaver standart. DD sürünür için.",
        "playstyle": {"early": "Q ile agresif takas, W ile sürünür", "mid": "Bölücü it, R ile engage", "late": "W patlaması devasa, R ile taşıyıcıyı taşı"},
    },
    "warwick": {
        "tier": "B", "role": "Jungle", "role_tr": "Orman",
        "core_items": [("3153", "Blade of the Ruined King"), ("3748", "Eclipse"), ("3075", "Thornmail")],
        "situational": [("3026", "Guardian Angel"), ("3065", "Warmog's Armor"), ("6333", "Death's Dance")],
        "runes_primary": ("Precision", ["Lethal Tempo", "Triumph", "Legend: Tenacity", "Last Stand"]),
        "runes_secondary": ("Resolve", ["Revitalize", "Overgrowth"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Smite", "spells_alt": "Ghost + Smite",
        "strong_vs": ["Lee Sin", "Kindred", "Graves"], "weak_vs": ["Udyr", "Trundle", "Volibear"],
        "matchups": {"Lee Sin": "6'da R ile lock down, Q ile sürünür", "Graves": "E korkut ile baskı yap, dövüşte sürünür", "Udyr": "Kite etmeye çalışır, R ile sabitle"},
        "combos": ["R → Q → AA → E (korkut kombosu)", "Q → AA → E → AA (temel gank)"],
        "tips": ["Pasif düşük HP hedefleri gösterir — gank yolları belirle", "Q takip eder — flash ile kaçanı izle", "E korkut hasarı azaltır + AoE korkut verir — dövüşlerde güçlü"],
        "pro_build": "Bork → Eclipse standart. Tank: Sunfire → Thornmail.",
        "playstyle": {"early": "Düşük HP koridorları gankla, Q ile sürünür", "mid": "R ile lock down, obje kontrolü", "late": "R ile taşıyıcıyı sabitle, E ile AoE korkut"},
    },
    "miss fortune": {
        "tier": "B", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6671", "Kraken Slayer"), ("3094", "Rapid Firecannon"), ("3031", "Infinity Edge")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("6333", "Death's Dance")],
        "runes_primary": ("Precision", ["Press the Attack", "Presence of Mind", "Legend: Bloodline", "Coup de Grace"]),
        "runes_secondary": ("Inspiration", ["Magical Footwear", "Biscuit Delivery"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > W > E", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Jinx", "Aphelios", "Senna"], "weak_vs": ["Draven", "Lucian", "Tristana"],
        "matchups": {"Jinx": "Q sekmeli vuruş ile poke at, all-in'de W aç", "Draven": "6'da R ile burst, kısa dövüşlerden kaçın", "Caitlyn": "Q sekmeli kadraç hasarı, W ile hareket hızı kullan"},
        "combos": ["Q sekmeli → AA → W (poke patlama)", "E → R (yavaşlatma + mermi yağmuru)"],
        "tips": ["Q sekmeli vuruş devasa hasar verir — düşük HP minionları hedefle", "W hareket hızı büyük — pozisyon için kullan", "R kanalize edilir — CC koruma veya güvenli pozisyon şart"],
        "pro_build": "Kraken → Rapid Firecannon standart. Lethality build de mümkün.",
        "playstyle": {"early": "Q sekmeli ile poke, W ile hareket", "mid": "R ile dövüş domine et, obje kontrolü", "late": "R mermi yağmuru devasa, koruma ile kanalize"},
    },
    "ezreal": {
        "tier": "B", "role": "ADC", "role_tr": "Nişancı",
        "core_items": [("6632", "Trinity Force"), ("3074", "Ravenous Hydra"), ("3031", "Infinity Edge")],
        "situational": [("3036", "Lord Dominik's Regards"), ("3139", "Mercurial Scimitar"), ("3026", "Guardian Angel")],
        "runes_primary": ("Precision", ["Conqueror", "Presence of Mind", "Legend: Bloodline", "Cut Down"]),
        "runes_secondary": ("Inspiration", ["Biscuit Delivery", "Cosmic Insight"]),
        "shards": "Saldırı Hızı / Uygun / Zırh",
        "skill_priority": "Q > E > W", "first_levels": "Q → W → E → Q → Q → R",
        "spells": "Flash + Heal", "spells_alt": "Flash + Cleanse",
        "strong_vs": ["Ornn", "Sion", "Malphite"], "weak_vs": ["Draven", "Caitlyn", "Miss Fortune"],
        "matchups": {"Caitlyn": "Q ile güvenli cs, kadraç itme fırsatı verme", "Draven": "Uzaktan Q poke, asla yakın takasa girme", "Vayne": "Q ile menzil avantajı, W patlaması ile outpoke"},
        "combos": ["Q → W → AA (Q + W patlama)", "E → Q → AA (arka dash + isabet)"],
        "tips": ["Q her şey — isabet şart, kaçırma", "E ile dash yap, agresif veya savunma", "W takım yeteneklerini hızlandırır — müttefik combolarında güçlü"],
        "pro_build": "Trinity → Hydra standart. Lethality: Duskblade → Collector.",
        "playstyle": {"early": "Q ile güvenli cs ve poke", "mid": "Q patlaması ile itme, E ile güvenli pozisyon", "late": "Uzun menzil poke, E ile kaçış, R ile harita etkisi"},
    },
}

# ── Data Dragon önbellek ───────────────────────────────────────────────────────
class _DDCache:
    def __init__(self):
        self.champions: dict[str, Any] | None = None
        self._last: float = 0
        self._ttl: int = 3600

    async def _get_json(self, url: str) -> Any:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
                async with s.get(url) as r:
                    if r.status == 200:
                        return await r.json()
        except Exception as exc:
            log.warning("Data Dragon hatası %s: %s", url, exc)
        return None

    async def get_champions(self) -> dict[str, Any]:
        import time as _time
        if self.champions is not None and _time.time() - self._last < self._ttl:
            return self.champions
        data = await self._get_json(f"{DD_BASE}/data/{DD_LANG}/champion.json")
        if data and "data" in data:
            self.champions = data["data"]
            self._last = _time.time()
        return self.champions or {}

_dd_cache = _DDCache()

# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────
def _normalize_name(name: str) -> str:
    return name.lower().strip().replace("'", "").replace(" ", "").replace("-", "").replace(".", "").replace("&", "")

def _get_role_from_tags(tags: list[str], champ_name: str) -> str:
    if champ_name in _JUNGLE_CHAMPS:
        return "Jungle"
    primary = tags[0] if tags else "Fighter"
    secondary = tags[1] if len(tags) > 1 else ""
    if primary == "Marksman":
        return "ADC"
    elif primary == "Mage":
        if secondary == "Assassin": return "Mid-Assassin"
        elif secondary == "Support": return "Support-Enchanter"
        return "Mid-Mage"
    elif primary == "Assassin":
        return "Mid-Assassin"
    elif primary == "Fighter":
        if secondary == "Tank": return "Top-Tank"
        return "Top-Fighter"
    elif primary == "Tank":
        if secondary == "Support": return "Support-Tank"
        return "Top-Tank"
    elif primary == "Support":
        if secondary == "Mage": return "Support-Enchanter"
        return "Support-Tank"
    return "Top-Fighter"

def _role_display(role_key: str) -> str:
    _MAP = {"ADC": "Nişancı", "Mid-Mage": "Orta (Büyücü)", "Mid-Assassin": "Orta (Suikastçı)",
            "Top-Fighter": "Üst (Dövüşçü)", "Top-Tank": "Üst (Tank)", "Jungle": "Orman",
            "Support-Enchanter": "Destek (Büyüleyici)", "Support-Tank": "Destek (Tank)"}
    return _MAP.get(role_key, role_key)

async def _resolve_champion(name: str) -> tuple[str, dict[str, Any] | None, str | None]:
    """Champion name → (display_name, meta_or_None, dd_id_or_None)"""
    n = _normalize_name(name)
    # 1) Detaylı rehberde var mı?
    for key, build in _META_BUILDS.items():
        if _normalize_name(key) == n:
            dd_id = await _get_dd_id(key)
            return key.split()[0].capitalize() if " " not in key else key, build, dd_id
    # 2) Data Dragon'dan bul
    champs = await _dd_cache.get_champions()
    for dd_id, info in champs.items():
        dd_name = info.get("name", "")
        dd_norm = _normalize_name(dd_name)
        if dd_norm == n or n in dd_norm or dd_norm in n:
            # Detaylı rehberde isim eşleşmesi var mı?
            for key, build in _META_BUILDS.items():
                if _normalize_name(key) == dd_norm:
                    return dd_name, build, dd_id
            # Rol bazlı varsayılan
            tags = info.get("tags", [])
            role = _get_role_from_tags(tags, dd_name)
            meta = _ROLE_DEFAULTS.get(role)
            if meta:
                meta = meta.copy()
                meta["role_tr"] = _role_display(role)
                # Tier tweak
                s = {"Aatrox", "Yone", "Yasuo", "Jinx", "Kai'Sa", "Viego", "Lee Sin", "Thresh", "Fiora", "Graves"}
                a = {"Vayne", "Syndra", "Ahri", "Lillia", "Gwen", "Jax", "Lulu"}
                if dd_name in s: meta["tier"] = "S"
                elif dd_name in a: meta["tier"] = "A"
            return dd_name, meta, dd_id
    return name.strip(), None, None

async def _get_dd_id(internal_name: str) -> str | None:
    champs = await _dd_cache.get_champions()
    n = _normalize_name(internal_name)
    for dd_id, info in champs.items():
        if _normalize_name(info.get("name", "")) == n:
            return dd_id
    return None

def _item_link(item_id: str, name: str) -> str:
    return f"* [{name}](https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/item/{item_id}.png)"

# ── Rehber oluşturucu ─────────────────────────────────────────────────────────
def _build_guide(champ: str, meta: dict[str, Any]) -> str:
    L: list[str] = []
    L.append("---")
    L.append("0. Meta")
    L.append("")
    L.append(f"* Patch: {DD_VERSION}")
    L.append(f"* Seviye: {meta['tier']}")
    L.append(f"* Rol: {meta.get('role_tr', meta.get('role', '?'))}")
    L.append("---")

    L.append("1. Build")
    L.append("   Çekirdek Eşyalar:")
    L.append("")
    for iid, nm in meta["core_items"]:
        L.append(_item_link(iid, nm))
    L.append("")
    L.append("   Durumsal Eşyalar:")
    L.append("")
    for iid, nm in meta["situational"]:
        L.append(_item_link(iid, nm))
    L.append("---")

    L.append("2. Rünler")
    pt, pr = meta["runes_primary"]
    L.append(f"   Primer: {pt}")
    L.append("")
    for r in pr: L.append(f"* {r}")
    L.append("")
    st, sr = meta["runes_secondary"]
    L.append(f"   Sekonder: {st}")
    L.append("")
    for r in sr: L.append(f"* {r}")
    L.append("")
    L.append("   Kırıntılar:")
    L.append("")
    L.append(f"* {meta['shards']}")
    L.append("---")

    L.append("3. Yetenek Sırası")
    L.append(f"   Öncelik: {meta['skill_priority']}")
    L.append("")
    L.append("   İlk Seviyeler:")
    L.append(f"   {meta['first_levels']}")
    L.append("---")

    L.append("4. Büyü Seçimleri")
    L.append("")
    L.append(f"* {meta['spells']}")
    L.append(f"  Alternatif: {meta['spells_alt']}")
    L.append("---")

    L.append("5. Counterlar")
    L.append("   Güçlüsün:")
    L.append("")
    for c in meta["strong_vs"]: L.append(f"* {c}")
    L.append("")
    L.append("   Zayıfsın:")
    L.append("")
    for c in meta["weak_vs"]: L.append(f"* {c}")
    L.append("---")

    L.append("6. Eşleşmeler")
    L.append("")
    for opp, tip in meta["matchups"].items():
        L.append(f"* vs {opp}: {tip}")
    L.append("---")

    L.append("7. Kombolar")
    L.append("")
    for combo in meta["combos"]: L.append(f"* {combo}")
    L.append("---")

    L.append("8. İpuçları")
    L.append("")
    for tip in meta["tips"]: L.append(f"* {tip}")
    L.append("---")

    L.append("9. Pro Build")
    L.append("")
    L.append(f"* {meta['pro_build']}")
    L.append("---")

    L.append("10. Oyun Tarzı")
    L.append("    Erken:")
    L.append("")
    L.append(f"* {meta['playstyle']['early']}")
    L.append("")
    L.append("    Orta:")
    L.append("")
    L.append(f"* {meta['playstyle']['mid']}")
    L.append("")
    L.append("    Geç:")
    L.append("")
    L.append(f"* {meta['playstyle']['late']}")
    L.append("---")
    return "\n".join(L)

def _build_spells(champ: str, meta: dict[str, Any]) -> str:
    return (f"**{champ}** Büyü Seçimleri\n\n"
            f"✅ Birincil: {meta['spells']}\n"
            f"🔄 Alternatif: {meta['spells_alt']}")

def _build_tips(champ: str, meta: dict[str, Any]) -> str:
    tips = "\n".join(f"• {t}" for t in meta["tips"])
    combos = "\n".join(f"• {c}" for c in meta["combos"])
    play = (f"**Erken:** {meta['playstyle']['early']}\n"
            f"**Orta:** {meta['playstyle']['mid']}\n"
            f"**Geç:** {meta['playstyle']['late']}")
    return f"**{champ}** İpuçları\n\n{tips}\n\n**Kombolar:**\n{combos}\n\n**Oyun Tarzı:**\n{play}"

def _build_counters(champ: str, meta: dict[str, Any]) -> str:
    strong = ", ".join(meta["strong_vs"])
    weak = ", ".join(meta["weak_vs"])
    return (f"**{champ}** Counterlar\n\n"
            f"✅ Güçlüsün: {strong}\n"
            f"❌ Zayıfsın: {weak}")

def _build_matchup(champ1: str, meta1: dict[str, Any], champ2: str, meta2: dict[str, Any] | None) -> str:
    # İlk şampiyonun matchups'ında ikinci var mı?
    for opp, tip in meta1["matchups"].items():
        if _normalize_name(opp) == _normalize_name(champ2) or _normalize_name(champ2) in _normalize_name(opp):
            return f"**{champ1} vs {champ2}**\n\n{tip}"
    # İkinci şampiyonun matchups'ında birinci var mı?
    if meta2:
        for opp, tip in meta2["matchups"].items():
            if _normalize_name(opp) == _normalize_name(champ1) or _normalize_name(champ1) in _normalize_name(opp):
                return f"**{champ1} vs {champ2}**\n\n{tip} (— {champ2} perspektifinden)"
    # Genel eşleşme ipucu
    r1 = meta1.get("role_tr", meta1.get("role", "?"))
    r2 = meta2.get("role_tr", meta2.get("role", "?")) if meta2 else "?"
    return (f"**{champ1} vs {champ2}**\n\n"
            f"Detaylı eşleşme verisi yok. {champ1} ({r1}) vs {champ2} ({r2}) — "
            f"rol avantajına ve erken/geç güç dönemlerine dikkat et.")

def _build_response(content: str, thumb_url: str | None, title: str) -> dict:
    header = c_section(
        c_text(f"## 🎮 {title}"),
        accessory=c_thumbnail(thumb_url) if thumb_url else None,
    )
    items: list = [header, c_separator()]
    for part in content.split("\n---\n"):
        p = part.strip()
        if p:
            items.append(c_text(p))
            items.append(c_separator())
    return c_container(*items)

def _build_simple_response(content: str, thumb_url: str | None, title: str) -> dict:
    header = c_section(
        c_text(f"## 🎮 {title}"),
        accessory=c_thumbnail(thumb_url) if thumb_url else None,
    )
    return c_container(header, c_separator(), c_text(content))


# ── Cog ───────────────────────────────────────────────────────────────────────
class LoL(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    lol = app_commands.Group(name="lol", description="League of Legends rehber komutları")

    @lol.command(name="rehber", description="Şampiyon için tam rehber: build, rün, counter, kombinasyon")
    @app_commands.describe(champion="Şampiyon adı (örn: Jinx, Yone, Malphite)")
    async def rehber(self, interaction: discord.Interaction, champion: str):
        display, meta, dd_id = await _resolve_champion(champion)
        if not meta:
            return await respond(interaction, c_container(c_text("Şampiyon bulunamadı.")), ephemeral=True)
        thumb = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{dd_id}.png" if dd_id else None
        guide = _build_guide(display, meta)
        await respond(interaction, _build_response(guide, thumb, f"{display} — Meta Rehber"))

    @lol.command(name="buyu", description="Şampiyon için en iyi büyü seçimleri (Summoner Spells)")
    @app_commands.describe(champion="Şampiyon adı (örn: Draven, Caitlyn)")
    async def buyu(self, interaction: discord.Interaction, champion: str):
        display, meta, dd_id = await _resolve_champion(champion)
        if not meta:
            return await respond(interaction, c_container(c_text("Şampiyon bulunamadı.")), ephemeral=True)
        thumb = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{dd_id}.png" if dd_id else None
        content = _build_spells(display, meta)
        await respond(interaction, _build_simple_response(content, thumb, f"{display} — Büyü Seçimleri"))

    @lol.command(name="ipuclari", description="Şampiyon için kısa ama değerli ipuçları ve kombolar")
    @app_commands.describe(champion="Şampiyon adı (örn: Draven, Yasuo)")
    async def ipuclari(self, interaction: discord.Interaction, champion: str):
        display, meta, dd_id = await _resolve_champion(champion)
        if not meta:
            return await respond(interaction, c_container(c_text("Şampiyon bulunamadı.")), ephemeral=True)
        thumb = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{dd_id}.png" if dd_id else None
        content = _build_tips(display, meta)
        await respond(interaction, _build_simple_response(content, thumb, f"{display} — İpuçları"))

    @lol.command(name="counter", description="Şampiyonun kime güçlü / kime zayıf olduğunu gösterir")
    @app_commands.describe(champion="Şampiyon adı (örn: Draven, Malphite)")
    async def counter(self, interaction: discord.Interaction, champion: str):
        display, meta, dd_id = await _resolve_champion(champion)
        if not meta:
            return await respond(interaction, c_container(c_text("Şampiyon bulunamadı.")), ephemeral=True)
        thumb = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{dd_id}.png" if dd_id else None
        content = _build_counters(display, meta)
        await respond(interaction, _build_simple_response(content, thumb, f"{display} — Counterlar"))

    @lol.command(name="eslesme", description="İki şampiyon arası lane eşleşmesi ve kısa analiz")
    @app_commands.describe(champion="Şampiyon adı", rakip="Rakip şampiyon adı")
    async def eslesme(self, interaction: discord.Interaction, champion: str, rakip: str):
        display1, meta1, dd_id1 = await _resolve_champion(champion)
        if not meta1:
            return await respond(interaction, c_container(c_text("Şampiyon bulunamadı.")), ephemeral=True)
        display2, meta2, _ = await _resolve_champion(rakip)
        if not meta2:
            return await respond(interaction, c_container(c_text("Rakip şampiyon bulunamadı.")), ephemeral=True)
        thumb = f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{dd_id1}.png" if dd_id1 else None
        content = _build_matchup(display1, meta1, display2, meta2)
        await respond(interaction, _build_simple_response(content, thumb, f"{display1} vs {display2}"))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        log.error("LoL komutu hatası: %s", error)
        await respond(interaction, c_container(c_text(f"❌ Hata: {error}")), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LoL(bot))
