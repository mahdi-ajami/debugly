import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    border_all, padding_symmetric,
)


def history_view(is_dark: bool = False, sessions: list | None = None):
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    border = DARK_BORDER if is_dark else LIGHT_BORDER
    bg_surface = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE

    search_bar = ft.TextField(
        hint_text="Search history...",
        prefix_icon=ft.Icons.SEARCH,
        expand=1,
        border_radius=8,
        text_size=13,
        height=40,
        border=border_all(1, border),
        bgcolor=bg_surface,
    )

    if sessions:
        session_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)
        for s in sessions:
            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.DESCRIPTION, size=16, color=accent),
                        ft.Text(s.get("preview", "") or "(empty)", size=12, color=text_p,
                                weight=ft.FontWeight.W_500, expand=1),
                    ], spacing=6),
                    ft.Text(f"{s.get('created_at', '')[:19].replace('T', ' ')}",
                            size=10, color=text_m),
                ], spacing=2),
                padding=12,
                bgcolor=bg_surface,
                border_radius=8,
                border=border_all(0.5, border),
            )
            session_list.controls.append(card)
        content = session_list
    else:
        content = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.HISTORY, size=48, color=text_m),
                ft.Container(height=8),
                ft.Text("No history yet", size=16, weight=ft.FontWeight.W_500, color=text_m),
                ft.Text("Your debug sessions will appear here", size=12, color=text_m),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            expand=1,
        )

    return ft.Container(
        content=ft.Column([
            ft.Text("History", size=22, weight=ft.FontWeight.BOLD, color=text_p),
            ft.Container(height=4),
            ft.Text("Your recent debug sessions", size=13, color=text_s),
            ft.Container(height=12),
            search_bar,
            ft.Container(height=8),
            content,
        ]),
        padding=padding_symmetric(horizontal=24, vertical=16),
        expand=1,
    )
