"""
cogs/_v2.py — Native discord.py Components V2 helpers.
discord.py >= 2.7.1 ile native `discord.ui.Container`, `TextDisplay`, `Section`,
`Thumbnail`, `Separator`, `MediaGallery`, `LayoutView` kullanır.
"""
from __future__ import annotations
from typing import Any

import discord
from discord import ui
from discord.http import Route

_V2  = 1 << 15   # IS_COMPONENTS_V2
_EPH = 1 << 6    # EPHEMERAL


# ── Color palette ─────────────────────────────────────────────────────────────
class COLORS:
    """Tutarlı renk paleti — komut türüne göre ayrılmış."""
    PRIMARY = 0x5865F2
    SUCCESS = 0x57F287
    DANGER  = 0xED4245
    WARNING = 0xFEE75C
    INFO    = 0x3498DB
    MOD     = 0xE67E22
    MUSIC   = 0x9B59B6
    EVENT   = 0xE91E63
    GAME    = 0xF1C40F
    NEUTRAL = 0x2B2D31


# ── Native component builders ─────────────────────────────────────────────────

def c_text(content: str) -> discord.ui.TextDisplay:
    return ui.TextDisplay(content)


def c_thumbnail(url: str | None) -> discord.ui.Thumbnail | None:
    if not url:
        return None
    return ui.Thumbnail(url)


def c_separator(spacing: int = 2) -> discord.ui.Separator:
    """Separator — spacing 2=large, 1=small."""
    sp = discord.SeparatorSpacing.large if spacing >= 2 else discord.SeparatorSpacing.small
    return ui.Separator(spacing=sp)


def c_section(
    *children: discord.ui.TextDisplay,
    accessory: discord.ui.Thumbnail | None = None,
) -> discord.ui.Section | discord.ui.TextDisplay:
    """Section component — accessory zorunludur.
    Verilmediğinde tek TextDisplay veya birleştirilmiş TextDisplay döner.
    """
    if accessory is None:
        if len(children) == 1:
            return children[0]
        merged = "\n".join(c.content for c in children if isinstance(c, ui.TextDisplay))
        return ui.TextDisplay(merged)
    return ui.Section(*children, accessory=accessory)


def c_container(*children: discord.ui.Item, color: int | None = None) -> discord.ui.Container:
    return ui.Container(*children, accent_color=color)


def c_media(*urls: str) -> discord.ui.MediaGallery:
    items = [discord.MediaGalleryItem(media=u) for u in urls]
    return ui.MediaGallery(*items)


# ── Inline formatters ─────────────────────────────────────────────────────────

def c_badge(label: str, color_emoji: str = "🔵") -> str:
    return f"`{color_emoji} {label}`"


def c_status_indicator(status: str, text: str = "") -> str:
    emoji = {"ok": "🟢", "success": "🟢", "warn": "🟡", "warning": "🟡",
             "err": "🔴", "error": "🔴", "critical": "🔴", "info": "🔵"}.get(status.lower(), "⚪")
    return f"{emoji} {text}" if text else emoji


def c_code_block(code: str, lang: str = "") -> str:
    return f"```{lang}\n{code}\n```"


def c_timestamp(ts: int) -> str:
    return f"<t:{int(ts)}:F>"


def c_field(label: str, value: str | int) -> str:
    return f"**{label}:** {value}"


def c_progress(current, total, length: int = 14) -> str:
    if not total or total <= 0:
        return "─" * length
    pct = max(0.0, min(1.0, float(current) / float(total)))
    filled = int(pct * length)
    return "━" * filled + "─" * (length - filled)


def c_kv_block(pairs: list[tuple[str, str | int]]) -> str:
    return "\n".join(c_field(l, v) for l, v in pairs)


# ── Composite cards (native V2) ───────────────────────────────────────────────

def c_rich_card(
    title: str,
    *,
    subtitle: str = "",
    body: str = "",
    thumbnail: str | None = None,
    badges: list[str] | None = None,
    footer: str | None = None,
    color: int | None = None,
) -> discord.ui.Container:
    """All-in-one rich card: title + subtitle + badges + body + thumbnail + footer."""
    header_lines = [f"## {title}"]
    if subtitle:
        header_lines.append(f"### {subtitle}")
    header_text = "\n".join(header_lines)

    header = (
        c_section(c_text(header_text), accessory=c_thumbnail(thumbnail))
        if thumbnail else c_text(header_text)
    )
    items: list[discord.ui.Item] = [header]

    if badges:
        items.append(c_separator())
        items.append(c_text(" ".join(badges)))

    if body:
        items.append(c_separator())
        items.append(c_text(body))

    if footer:
        items.append(c_separator())
        items.append(c_text(f"-# {footer}"))

    return c_container(*items, color=color)


def c_card(
    title: str,
    body: str = "",
    thumbnail: str | None = None,
    color: int | None = None,
) -> discord.ui.Container:
    header = (
        c_section(c_text(title), accessory=c_thumbnail(thumbnail))
        if thumbnail else c_text(title)
    )
    items: list[discord.ui.Item] = [header]
    if body:
        items.append(c_separator())
        items.append(c_text(body))
    return c_container(*items, color=color)


def c_error(msg: str, thumbnail: str | None = None) -> discord.ui.Container:
    return c_card("## ❌ Hata", body=msg, thumbnail=thumbnail)


def c_success(msg: str, thumbnail: str | None = None) -> discord.ui.Container:
    return c_card("## ✅ Başarılı", body=msg, thumbnail=thumbnail)


def c_action_card(
    title: str,
    target_avatar: str | None = None,
    fields: list[tuple[str, str | int]] | None = None,
    *,
    footer: str | None = None,
    color: int | None = None,
) -> discord.ui.Container:
    header = (
        c_section(c_text(f"## {title}"), accessory=c_thumbnail(target_avatar))
        if target_avatar else c_text(f"## {title}")
    )
    items: list[discord.ui.Item] = [header]
    if fields:
        items.append(c_separator())
        items.append(c_text(c_kv_block(fields)))
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
    color: int | None = None,
) -> discord.ui.Container:
    items: list[discord.ui.Item] = [
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
    color: int | None = None,
) -> discord.ui.Container:
    header = (
        c_section(c_text(f"## {title}"), accessory=c_thumbnail(thumbnail))
        if thumbnail else c_text(f"## {title}")
    )
    items: list[discord.ui.Item] = [header, c_separator(), c_text("\n".join(rows) if rows else empty)]
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


# ── Internals ─────────────────────────────────────────────────────────────────

def _serialize(items: tuple[Any, ...]) -> list[dict]:
    """Native discord.ui Items → raw component dict list."""
    result: list[dict] = []
    for item in items:
        if isinstance(item, discord.ui.Container):
            result.append(item.to_component_dict())
        elif isinstance(item, discord.ui.LayoutView):
            result.extend(item.to_components())
        elif hasattr(item, "to_component_dict"):
            result.append(item.to_component_dict())
        elif isinstance(item, dict):
            result.append(item)
        else:
            result.append(item)
    return result


def _flags(ephemeral: bool) -> int:
    return _V2 | (_EPH if ephemeral else 0)


def _mark_responded(resp: discord.InteractionResponse, type_id: int = 4) -> None:
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
    *items: discord.ui.Item,
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
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    await interaction._state.http.request(
        route,
        json={"type": 4, "data": {"flags": _flags(ephemeral), "components": components}},
    )
    _mark_responded(interaction.response, 4)
    if view:
        msg = await interaction.original_response()
        interaction._state.store_view(view, msg.id)
        return msg
    return None


async def edit_original(
    interaction: discord.Interaction,
    *items: discord.ui.Item,
    view: discord.ui.View | None = None,
) -> None:
    """Orijinal interaction yanıtını düzenle."""
    route = Route(
        "PATCH",
        "/webhooks/{webhook_id}/{webhook_token}/messages/@original",
        webhook_id=interaction.application_id,
        webhook_token=interaction.token,
    )
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    await interaction._state.http.request(
        route,
        json={"flags": _V2, "components": components},
    )


async def update(
    interaction: discord.Interaction,
    *items: discord.ui.Item,
    view: discord.ui.View | None = None,
) -> None:
    """Type-7: bu interaction'ı tetikleyen mesajı güncelle."""
    route = Route(
        "POST",
        "/interactions/{interaction_id}/{interaction_token}/callback",
        interaction_id=interaction.id,
        interaction_token=interaction.token,
    )
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    await interaction._state.http.request(
        route,
        json={"type": 7, "data": {"flags": _V2, "components": components}},
    )
    _mark_responded(interaction.response, 7)
    if view and getattr(interaction, "message", None):
        interaction._state.store_view(view, interaction.message.id)


async def followup(
    interaction: discord.Interaction,
    *items: discord.ui.Item,
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
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    data = await interaction._state.http.request(
        route,
        json={"flags": _flags(ephemeral), "components": components},
        params={"wait": 1},
    )
    msg_id = int(data["id"])
    if view:
        interaction._state.store_view(view, msg_id)
    return msg_id


async def edit_followup(
    interaction: discord.Interaction,
    message_id: int,
    *items: discord.ui.Item,
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
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    await interaction._state.http.request(
        route,
        json={"flags": _V2, "components": components},
    )


async def channel_send(
    channel: discord.abc.Messageable,
    *items: discord.ui.Item,
    view: discord.ui.View | None = None,
    content: str | None = None,
) -> discord.Message:
    """Metin kanalına V2 mesaj gönderir (interaction dışı). Message döner."""
    state = channel._state  # type: ignore[attr-defined]
    route = Route("POST", "/channels/{channel_id}/messages", channel_id=channel.id)  # type: ignore[attr-defined]
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    payload: dict = {"flags": _V2, "components": components}
    if content:
        payload["content"] = content
    data = await state.http.request(route, json=payload)
    msg = discord.Message(state=state, channel=channel, data=data)  # type: ignore[arg-type]
    if view:
        state.store_view(view, msg.id)
    return msg


async def msg_edit(
    msg: discord.Message,
    *items: discord.ui.Item,
    view: discord.ui.View | None = None,
) -> None:
    """Herhangi bir mesajı V2 componentleriyle düzenle."""
    route = Route(
        "PATCH",
        "/channels/{channel_id}/messages/{message_id}",
        channel_id=msg.channel.id,
        message_id=msg.id,
    )
    components = _serialize(items)
    if view:
        components.extend(view.to_components())
    await msg._state.http.request(
        route,
        json={"flags": _V2, "components": components},
    )
    if view:
        msg._state.store_view(view, msg.id)


# ── File upload helpers ─────────────────────────────────────────────────────────

async def respond_with_files(
    interaction: discord.Interaction,
    *items: discord.ui.Item,
    files: list[discord.File],
    view: discord.ui.View | None = None,
    ephemeral: bool = False,
) -> discord.InteractionMessage | None:
    """Type-4: yeni mesaj yanıtı + dosya eki."""
    import json as _json
    try:
        from aiohttp import FormData
    except ImportError:
        raise ImportError("respond_with_files requires aiohttp")

    route = Route(
        "POST",
        "/interactions/{interaction_id}/{interaction_token}/callback",
        interaction_id=interaction.id,
        interaction_token=interaction.token,
    )

    components = _serialize(items)
    if view:
        components.extend(view.to_components())

    payload = {
        "type": 4,
        "data": {
            "flags": _flags(ephemeral),
            "components": components,
            "attachments": [{"id": str(i), "filename": f.filename} for i, f in enumerate(files)],
        },
    }

    form = FormData()
    form.add_field("payload_json", _json.dumps(payload), content_type="application/json")
    for i, f in enumerate(files):
        form.add_field(f"files[{i}]", f.fp, filename=f.filename)

    await interaction._state.http.request(route, multipart=form)
    _mark_responded(interaction.response, 4)
    if view:
        msg = await interaction.original_response()
        interaction._state.store_view(view, msg.id)
        return msg
    return None


async def msg_edit_with_files(
    msg: discord.Message,
    *items: discord.ui.Item,
    files: list[discord.File],
    view: discord.ui.View | None = None,
) -> None:
    """Mesajı V2 componentleri + yeni dosya ekleriyle düzenle."""
    import json as _json
    try:
        from aiohttp import FormData
    except ImportError:
        raise ImportError("msg_edit_with_files requires aiohttp")

    route = Route(
        "PATCH",
        "/channels/{channel_id}/messages/{message_id}",
        channel_id=msg.channel.id,
        message_id=msg.id,
    )

    components = _serialize(items)
    if view:
        components.extend(view.to_components())

    payload = {
        "flags": _V2,
        "components": components,
        "attachments": [{"id": str(i), "filename": f.filename} for i, f in enumerate(files)],
    }

    form = FormData()
    form.add_field("payload_json", _json.dumps(payload), content_type="application/json")
    for i, f in enumerate(files):
        form.add_field(f"files[{i}]", f.fp, filename=f.filename)

    await msg._state.http.request(route, multipart=form)
    if view:
        msg._state.store_view(view, msg.id)


async def channel_send_with_files(
    channel: discord.abc.Messageable,
    *items: discord.ui.Item,
    files: list[discord.File],
    view: discord.ui.View | None = None,
    content: str | None = None,
) -> discord.Message:
    """Metin kanalına V2 mesaj + dosya eki gönderir."""
    import json as _json
    try:
        from aiohttp import FormData
    except ImportError:
        raise ImportError("channel_send_with_files requires aiohttp")

    state = channel._state  # type: ignore[attr-defined]
    route = Route("POST", "/channels/{channel_id}/messages", channel_id=channel.id)  # type: ignore[attr-defined]

    components = _serialize(items)
    if view:
        components.extend(view.to_components())

    payload: dict = {
        "flags": _V2,
        "components": components,
        "attachments": [{"id": str(i), "filename": f.filename} for i, f in enumerate(files)],
    }
    if content:
        payload["content"] = content

    form = FormData()
    form.add_field("payload_json", _json.dumps(payload), content_type="application/json")
    for i, f in enumerate(files):
        form.add_field(f"files[{i}]", f.fp, filename=f.filename)

    data = await state.http.request(route, multipart=form)
    msg = discord.Message(state=state, channel=channel, data=data)  # type: ignore[arg-type]
    if view:
        state.store_view(view, msg.id)
    return msg
