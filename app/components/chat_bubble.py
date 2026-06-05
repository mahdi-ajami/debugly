import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DANGER, SUCCESS,
    border_all, padding_symmetric, padding_only, is_rtl_text,
)


def _user_bubble(text: str, is_dark: bool, attachments: list | None = None):
    rtl = is_rtl_text(text)
    children = []
    if attachments:
        children.append(ft.Row(attachments, spacing=6, wrap=True))
    children.append(
        ft.Markdown(
            value=text,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            code_theme="monokai-sublime" if is_dark else "github",
            selectable=True,
        )
    )
    return ft.Container(
        content=ft.Column(children, spacing=4),
        padding=padding_symmetric(horizontal=14, vertical=10),
        bgcolor=DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE,
        border_radius=ft.BorderRadius(top_left=16, top_right=4, bottom_left=16, bottom_right=16),
        border=border_all(1, DARK_ACCENT + "30" if is_dark else LIGHT_ACCENT + "30"),
    )


def _assistant_bubble(text: str, is_dark: bool, steps: list | None = None):
    children = []
    if steps:
        steps_col = ft.Column(steps, spacing=2)
        children.append(steps_col)
    if text:
        children.append(
            ft.Markdown(
                value=text,
                extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                code_theme="monokai-sublime" if is_dark else "github",
                selectable=True,
            )
        )
    return ft.Container(
        content=ft.Column(children, spacing=6),
        padding=padding_symmetric(horizontal=14, vertical=10),
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border_radius=ft.BorderRadius(top_left=4, top_right=16, bottom_left=16, bottom_right=16),
        border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
    )


def _avatar(is_user: bool, is_dark: bool):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    if is_user:
        return ft.Container(
            content=ft.Icon(ft.Icons.PERSON, size=16, color=ft.Colors.WHITE),
            width=28, height=28, border_radius=14,
            bgcolor=accent,
        )
    return ft.Container(
        content=ft.Icon(ft.Icons.SMART_TOY, size=16, color=accent),
        width=28, height=28, border_radius=14,
        bgcolor=DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE,
        border=border_all(1, accent + "40"),
    )


def chat_bubble(
    text: str,
    is_user: bool = False,
    is_markdown: bool = False,
    is_dark: bool = False,
    timestamp: str = "",
    attachments: list | None = None,
    steps: list | None = None,
):
    bubble = _user_bubble(text, is_dark, attachments) if is_user else _assistant_bubble(text, is_dark, steps)

    avatar = _avatar(is_user, is_dark)

    ts = ""
    if timestamp:
        try:
            ts = timestamp[:19].replace("T", " ")
        except Exception:
            ts = ""

    if is_user:
        return ft.Row([
            ft.Container(expand=1),
            ft.Column([bubble, ft.Text(ts, size=9, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED, visible=bool(ts))],
                      spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END),
            ft.Container(content=avatar, margin=ft.Margin(left=0, top=6, right=0, bottom=0)),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START)
    else:
        return ft.Row([
            ft.Container(content=avatar, margin=ft.Margin(left=0, top=6, right=0, bottom=0)),
            ft.Column([ft.Container(content=bubble), ft.Text(ts, size=9, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED, visible=bool(ts))],
                      spacing=2),
            ft.Container(expand=1),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START)
