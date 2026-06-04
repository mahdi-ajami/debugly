import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    border_all, padding_symmetric, padding_only, is_rtl_text,
)


def _user_bubble(text: str, is_dark: bool, attachments: list | None = None):
    rtl = is_rtl_text(text)
    children = []
    if attachments:
        row = ft.Row(attachments, spacing=6, wrap=True)
        children.append(row)
    children.append(
        ft.Text(text, selectable=True, size=14, color=DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY,
                text_align=ft.TextAlign.RIGHT if rtl else ft.TextAlign.LEFT)
    )
    return ft.Container(
        content=ft.Column(children, spacing=4),
        padding=padding_symmetric(horizontal=14, vertical=10),
        bgcolor=DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE,
        border_radius=ft.BorderRadius(top_left=16, top_right=4, bottom_left=16, bottom_right=16),
    )


def _assistant_bubble(text: str, is_dark: bool, steps: list | None = None):
    children = []
    if steps:
        for s in steps:
            children.append(s)
    children.append(
        ft.Markdown(
            value=text,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            code_theme="monokai-sublime" if is_dark else "github",
            selectable=True,
            on_tap_link=lambda e: e.page.launch_url(e.data),
        )
    )
    return ft.Container(
        content=ft.Column(children, spacing=4),
        padding=padding_symmetric(horizontal=14, vertical=10),
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border_radius=ft.BorderRadius(top_left=4, top_right=16, bottom_left=16, bottom_right=16),
        border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
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
    ts = ""
    if timestamp:
        try:
            ts = timestamp[:19].replace("T", " ")
        except Exception:
            ts = ""

    icon = ft.Icons.PERSON_OUTLINE if is_user else ft.Icons.SMART_TOY_OUTLINED
    icon_color = DARK_ACCENT if is_dark else LIGHT_ACCENT
    icon_tip = "You" if is_user else "Assistant"

    bubble = _user_bubble(text, is_dark, attachments) if is_user else _assistant_bubble(text, is_dark, steps)

    left_icon = ft.Container(
        content=ft.Icon(icon, size=20, color=icon_color),
        tooltip=icon_tip,
    ) if not is_user else ft.Container(width=0)

    right_icon = ft.Container(
        content=ft.Icon(icon, size=20, color=icon_color),
        tooltip=icon_tip,
    ) if is_user else ft.Container(width=0)

    return ft.Row([
        left_icon,
        ft.Column([
            bubble,
            ft.Text(ts, size=9, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED, visible=bool(ts)),
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END if is_user else ft.CrossAxisAlignment.START),
        right_icon,
    ], spacing=6, alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END)
