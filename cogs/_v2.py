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
) -> discord.Message:
    """Metin kanalına V2 mesaj gönderir (interaction dışı). Message döner."""
    state = channel._state  # type: ignore[attr-defined]
    route = Route("POST", "/channels/{channel_id}/messages", channel_id=channel.id)  # type: ignore[attr-defined]
    data = await state.http.request(
        route,
        json={"flags": _V2, "components": _build(components, view)},
    )
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
