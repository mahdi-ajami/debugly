import flet as ft

from app.theme import (
    surface_container,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    padding_symmetric, border_all,
)


def home_view(on_navigate, is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    kb_count = "0"
    try:
        from core.database import get_conn
        r = get_conn().execute("SELECT COUNT(1) FROM kb_entries").fetchone()
        if r:
            kb_count = str(r[0])
    except Exception:
        pass

    stat_card = lambda icon, label, value: surface_container(
        ft.Column([
            ft.Icon(icon, size=24, color=accent),
            ft.Container(height=4),
            ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=text_p),
            ft.Text(label, size=11, color=text_m),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
        width=160, height=110, padding=16, is_dark=is_dark,
    )

    stats = ft.Row([
        stat_card(ft.Icons.BUG_REPORT, "Errors Solved", "0"),
        stat_card(ft.Icons.LIBRARY_BOOKS, "KB Entries", kb_count),
        stat_card(ft.Icons.SPEED, "Accuracy", "—"),
        stat_card(ft.Icons.PSYCHOLOGY, "Active Model", "Qwen 3"),
    ], spacing=12, alignment=ft.MainAxisAlignment.CENTER)

    quick_actions = ft.Row([
        ft.ElevatedButton(
            "New Debug Session",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=accent,
                padding=padding_symmetric(horizontal=24, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda _: on_navigate(1),
        ),
        ft.OutlinedButton(
            "Knowledge Base",
            icon=ft.Icons.LIBRARY_BOOKS_OUTLINED,
            style=ft.ButtonStyle(
                padding=padding_symmetric(horizontal=20, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=8),
                side=border_all(1, border),
            ),
            on_click=lambda _: on_navigate(4),
        ),
        ft.OutlinedButton(
            "History",
            icon=ft.Icons.HISTORY,
            style=ft.ButtonStyle(
                padding=padding_symmetric(horizontal=20, vertical=12),
                shape=ft.RoundedRectangleBorder(radius=8),
                side=border_all(1, border),
            ),
            on_click=lambda _: on_navigate(2),
        ),
    ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)

    return ft.Container(
        content=ft.Column([
            ft.Text("Welcome to Debugly", size=28, weight=ft.FontWeight.BOLD, color=text_p),
            ft.Container(height=4),
            ft.Text("Your intelligent error debugger with self-learning AI", size=13, color=text_s),
            ft.Container(height=24),
            stats,
            ft.Container(height=28),
            ft.Text("Quick Actions", size=16, weight=ft.FontWeight.W_600, color=text_p),
            ft.Container(height=10),
            quick_actions,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=padding_symmetric(horizontal=32, vertical=24),
        expand=1,
    )
