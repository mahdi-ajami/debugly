import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    border_all, padding_symmetric, is_rtl_text,
)


def chat_bubble(
    text: str,
    is_user: bool = False,
    is_markdown: bool = False,
    is_dark: bool = False,
    timestamp: str = "",
    attachments: list | None = None,
):
    if is_user:
        bg = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
        border = None
        max_w = None
        icon = ft.Icons.PERSON_OUTLINE
        icon_color = DARK_ACCENT if is_dark else LIGHT_ACCENT
    else:
        bg = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE
        border = border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER)
        max_w = 600
        icon = ft.Icons.SMART_TOY_OUTLINED
        icon_color = DARK_ACCENT if is_dark else LIGHT_ACCENT

    ts = ""
    if timestamp:
        try:
            ts = timestamp[:19].replace("T", " ")
        except Exception:
            ts = ""

    rtl = is_rtl_text(text)
    text_align = ft.TextAlign.RIGHT if rtl else ft.TextAlign.LEFT

    if is_markdown:
        content = ft.Markdown(
            value=text,
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            code_theme="monokai-sublime" if is_dark else "github",
            selectable=True,
            on_tap_link=lambda e: e.page.launch_url(e.data),
        )
    else:
        content = ft.Text(
            text, selectable=True, size=14,
            color=DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY,
            text_align=text_align,
        )

    children = [content]

    if attachments:
        children.append(
            ft.Container(
                content=ft.Column([*attachments], spacing=4),
                padding=padding_only(top=6),
            )
        )

    return ft.Row([
        ft.Container(
            content=ft.Icon(icon, size=18, color=icon_color),
            tooltip="You" if is_user else "Assistant",
        ) if not is_user else ft.Container(),
        ft.Column([
            ft.Container(
                content=ft.Column(children, spacing=2),
                padding=padding_symmetric(horizontal=14, vertical=10),
                bgcolor=bg,
                border_radius=ft.BorderRadius(
                    top_left=16 if not is_user else 4,
                    top_right=16 if is_user else 4,
                    bottom_left=16,
                    bottom_right=16,
                ),
                border=border,
                width=max_w,
            ),
            ft.Text(ts, size=9, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED,
                    visible=bool(ts)),
        ], spacing=2),
        ft.Container(
            content=ft.Icon(icon, size=18, color=icon_color),
            tooltip="You" if is_user else "Assistant",
        ) if is_user else ft.Container(),
    ], spacing=4, alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.END)
