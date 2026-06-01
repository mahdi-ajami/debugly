import flet as ft


def solution_card(title: str, details: list[dict]) -> ft.Container:
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
        border=ft.border.all(1, ft.Colors.GREY_300),
        border_radius=12,
        width=280,
        visible=bool(details),
    )
