"""
cogs/_v2.py — Components V2 raw-API helpers.
discord.py >= 2.4.0 ile native V2 desteği gerektirmeden çalışır.
"""
from __future__ import annotations
from typing import Any

import discord
from discord.http import Route

_V2  = 1 << 15   # IS_COMPONENTS_V2
_EPH = 1 << 6    # EPHEMERAL

# ── Component type IDs ────────────────────────────────────────────────────────
CONTAINER = 17
SECTION   = 9
TEXT      = 10
THUMBNAIL = 11
MEDIA     = 12
SEPARATOR = 14


# ── Builders ──────────────────────────────────────────────────────────────────

def c_text(content: str) -> dict:
    return {"type": TEXT, "content": content}


def c_thumbnail(url: str) -> dict:
    return {"type": THUMBNAIL, "media": {"url": url}}


def c_separator(spacing: int = 2) -> dict:
    return {"type": SEPARATOR, "divider": True, "spacing": spacing}


def c_section(*texts: dict, accessory: dict | None = None) -> dict:
    d: dict[str, Any] = {"type": SECTION, "components": list(texts)}
    if accessory:
        d["accessory"] = accessory
    return d


def c_container(*items: dict, color: int | None = None) -> dict:
    d: dict[str, Any] = {"type": CONTAINER, "components": list(items)}
    if color is not None:
        d["accent_color"] = color
    return d


def c_media(*urls: str) -> dict:
    return {"type": MEDIA, "items": [{"media": {"url": u}} for u in urls]}


# ── Internals ─────────────────────────────────────────────────────────────────

def _build(components: tuple[dict, ...], view: discord.ui.View | None) -> list[dict]:
    result = list(components)
    if view:
        result.extend(view.to_components())
    return result


def _flags(ephemeral: bool) -> int:
    return _V2 | (_EPH if ephemeral else 0)


def _mark_responded(resp: discord.InteractionResponse, type_id: int = 4) -> None:
    # discord.py < 2.5 uses _responded: bool, newer versions use _response_type: int
    try:
        resp._responded = True  # type: ignore[attr-defined]
    except AttributeError:
        try:
            resp._response_type = type_id  # type: ignore[attr-defined]
        except AttributeError:
            pass


# ── Color palette ─────────────────────────────────────────────────────────────

class COLORS:
    """Tutarlı renk paleti — komut türüne göre ayrılmış."""
    PRIMARY = 0x5865F2  # Discord blurple — info/default
    SUCCESS = 0x57F287  # green — onay, başarı
    DANGER  = 0xED4245  # red — hata, ban
    WARNING = 0xFEE75C  # yellow — uyarı, mute
    INFO    = 0x3498DB  # mavi — bilgi kartları
    MOD     = 0xE67E22  # turuncu — moderasyon (kick)
    MUSIC   = 0x9B59B6  # mor — müzik
    EVENT   = 0xE91E63  # pembe — etkinlik
    GAME    = 0xF1C40F  # altın — oyunlar
    NEUTRAL = 0x2B2D31  # discord card bg


# ── Convenience card builders ─────────────────────────────────────────────────

def c_card(
    title: str,
    body: str = "",
    thumbnail: str | None = None,
    color: int = COLORS.PRIMARY,
) -> dict:
    """8top-style card: ## title + optional thumbnail (right) + separator + body."""
    header = (
        c_section(c_text(title), accessory=c_thumbnail(thumbnail))
        if thumbnail else c_text(title)
    )
    items: list[dict] = [header]
    if body:
        items.append(c_separator())
        items.append(c_text(body))
    return c_container(*items, color=color)


def c_error(msg: str, thumbnail: str | None = None) -> dict:
    return c_card("## ❌ Hata", body=msg, thumbnail=thumbnail, color=COLORS.DANGER)


def c_success(msg: str, thumbnail: str | None = None) -> dict:
    return c_card("## ✅ Başarılı", body=msg, thumbnail=thumbnail, color=COLORS.SUCCESS)


# ── Inline formatters ─────────────────────────────────────────────────────────

def c_field(label: str, value: str | int) -> str:
    """Format an inline label-value pair: '**Label:** value'"""
    return f"**{label}:** {value}"


def c_progress(current, total, length: int = 18) -> str:
    """Build a unicode progress bar (current/total, 0..length filled chars)."""
    if not total or total <= 0:
        return "▱" * length
    pct = max(0.0, min(1.0, float(current) / float(total)))
    filled = int(pct * length)
    return "▰" * filled + "▱" * (length - filled)


def c_kv_block(pairs: list[tuple[str, str | int]]) -> str:
    """Multi-line label-value block."""
    return "\n".join(c_field(l, v) for l, v in pairs)


# ── Composite cards ───────────────────────────────────────────────────────────

def c_action_card(
    title: str,
    target_avatar: str,
    fields: list[tuple[str, str | int]],
    *,
    footer: str | None = None,
    color: int = COLORS.MOD,
) -> dict:
    """Eylem kartı: başlık + hedef üye avatarı + label/değer çiftleri."""
    items: list[dict] = [
        c_section(c_text(f"## {title}"), accessory=c_thumbnail(target_avatar)),
        c_separator(),
        c_text(c_kv_block(fields)),
    ]
    if footer:
        items.append(c_separator())
        items.append(c_text(f"-# {footer}"))
    return c_container(*items, color=color)


def c_info_card(
    title: str,
    *,
    thumbnail: str | None = None,
    groups: list[list[tuple[str, str | int]] | str],
    media: str | None = None,
    footer: str | None = None,
    color: int = COLORS.INFO,
) -> dict:
    """Bilgi kartı: başlık + thumbnail + ayraçlarla bölünmüş çoklu gruplar."""
    items: list[dict] = [
        c_section(c_text(f"## {title}"), accessory=c_thumbnail(thumbnail))
        if thumbnail else c_text(f"## {title}"),
    ]
    for group in groups:
        items.append(c_separator())
        if isinstance(group, str):
            items.append(c_text(group))
        else:
            items.append(c_text(c_kv_block(group)))
    if media:
        items.append(c_separator())
        items.append(c_media(media))
    if footer:
        items.append(c_separator())
        items.append(c_text(f"-# {footer}"))
    return c_container(*items, color=color)


def c_list_card(
    title: str,
    rows: list[str],
    *,
    thumbnail: str | None = None,
    footer: str | None = None,
    empty: str = "Henüz öğe yok.",
    color: int = COLORS.PRIMARY,
) -> dict:
    """Liste kartı: başlık + thumbnail + satır listesi."""
    header = (
        c_section(c_text(f"## {title}"), accessory=c_thumbnail(thumbnail))
        if thumbnail else c_text(f"## {title}")
    )
    items: list[dict] = [header, c_separator(), c_text("\n".join(rows) if rows else empty)]
    if footer:
        items.append(c_separator())
        items.append(c_text(f"-# {footer}"))
    return c_container(*items, color=color)


async def error_response(interaction: discord.Interaction, msg: str) -> None:
    """Hata mesajı gönderir — interaction daha önce yanıtlanmış olsa da çalışır."""
    thumb = str(interaction.client.user.display_avatar.url)  # type: ignore[union-attr]
    card = c_error(msg, thumbnail=thumb)
    if interaction.response.is_done():
        await followup(interaction, card, ephemeral=True)
    else:
        await respond(interaction, card, ephemeral=True)


# ── Interaction response helpers ──────────────────────────────────────────────

async def respond(
    interaction: discord.Interaction,
    *components: dict,
    view: discord.ui.View | None = None,
    ephemeral: bool = False,
) -> discord.InteractionMessage | None:
    """Type-4: yeni mesaj yanıtı. View varsa mesajı döner (view kaydı için)."""
    route = Route(
        "POST",
        "/interactions/{interaction_id}/{interaction_token}/callback",
        interaction_id=interaction.id,
        interaction_token=interaction.token,
    )
    await interaction._state.http.request(
        route,
        json={"type": 4, "data": {"flags": _flags(ephemeral), "components": _build(components, view)}},
    )
    _mark_responded(interaction.response, 4)
    if view:
        msg = await interaction.original_response()
        interaction._state.store_view(view, msg.id)
        return msg
    return None


async def edit_original(
    interaction: discord.Interaction,
    *components: dict,
    view: discord.ui.View | None = None,
) -> None:
    """Orijinal interaction yanıtını düzenle."""
    route = Route(
        "PATCH",
        "/webhooks/{webhook_id}/{webhook_token}/messages/@original",
        webhook_id=interaction.application_id,
        webhook_token=interaction.token,
    )
    await interaction._state.http.request(
        route,
        json={"flags": _V2, "components": _build(components, view)},
    )


async def update(
    interaction: discord.Interaction,
    *components: dict,
    view: discord.ui.View | None = None,
) -> None:
    """Type-7: bu interaction'ı tetikleyen mesajı güncelle."""
    route = Route(
        "POST",
        "/interactions/{interaction_id}/{interaction_token}/callback",
        interaction_id=interaction.id,
        interaction_token=interaction.token,
    )
    await interaction._state.http.request(
        route,
        json={"type": 7, "data": {"flags": _V2, "components": _build(components, view)}},
    )
    _mark_responded(interaction.response, 7)


async def followup(
    interaction: discord.Interaction,
    *components: dict,
    view: discord.ui.View | None = None,
    ephemeral: bool = False,
) -> int:
    """Followup V2 mesajı gönderir. Mesaj ID'sini döner."""
    route = Route(
        "POST",
        "/webhooks/{webhook_id}/{webhook_token}",
        webhook_id=interaction.application_id,
        webhook_token=interaction.token,
    )
    data = await interaction._state.http.request(
        route,
        json={"flags": _flags(ephemeral), "components": _build(components, view)},
        params={"wait": 1},
    )
    msg_id = int(data["id"])
    if view:
        interaction._state.store_view(view, msg_id)
    return msg_id


async def edit_followup(
    interaction: discord.Interaction,
    message_id: int,
    *components: dict,
    view: discord.ui.View | None = None,
) -> None:
    """Followup mesajını ID ile düzenle."""
    route = Route(
        "PATCH",
        "/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}",
        webhook_id=interaction.application_id,
        webhook_token=interaction.token,
        message_id=message_id,
    )
    await interaction._state.http.request(
        route,
        json={"flags": _V2, "components": _build(components, view)},
    )


async def channel_send(
    channel: discord.abc.Messageable,
    *components: dict,
    view: discord.ui.View | None = None,
    content: str | None = None,
) -> discord.Message:
    """Metin kanalına V2 mesaj gönderir (interaction dışı). Message döner."""
    state = channel._state  # type: ignore[attr-defined]
    route = Route("POST", "/channels/{channel_id}/messages", channel_id=channel.id)  # type: ignore[attr-defined]
    payload: dict = {"flags": _V2, "components": _build(components, view)}
    if content:
        payload["content"] = content
    data = await state.http.request(route, json=payload)
    msg = discord.Message(state=state, channel=channel, data=data)  # type: ignore[arg-type]
    if view:
        state.store_view(view, msg.id)
    return msg


async def msg_edit(
    msg: discord.Message,
    *components: dict,
    view: discord.ui.View | None = None,
) -> None:
    """Herhangi bir mesajı V2 componentleriyle düzenle."""
    route = Route(
        "PATCH",
        "/channels/{channel_id}/messages/{message_id}",
        channel_id=msg.channel.id,
        message_id=msg.id,
    )
    await msg._state.http.request(
        route,
        json={"flags": _V2, "components": _build(components, view)},
    )
    if view:
        msg._state.store_view(view, msg.id)
