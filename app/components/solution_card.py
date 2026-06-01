import flet as ft

from app.theme import border_all, LIGHT_BORDER, DARK_BORDER


def solution_card(title: str, details: list[dict], is_dark: bool = False) -> ft.Container:
    border_color = DARK_BORDER if is_dark else LIGHT_BORDER
    items = []
    for d in details:
        items.append(ft.ListTile(
            leading=ft.Icon(ft.Icons.DESCRIPTION, size=20),
            title=ft.Text(d.get("source", "knowledge_base"), size=12, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(f"Relevance: {d.get('score', 0):.2f}", size=11),
        ))
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=8),
            *items,
        ]),
        padding=15,
        border=border_all(1, border_color),
        border_radius=12,
        width=280,
        visible=bool(details),
    )
