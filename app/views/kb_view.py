import flet as ft

from app.theme import (
    surface_container,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    border_all, padding_symmetric,
)


def _show_add_dialog(page, is_dark):
    error_field = ft.TextField(label="Error text", multiline=True, min_lines=2, max_lines=4)
    solution_field = ft.TextField(label="Solution text", multiline=True, min_lines=3, max_lines=6)

    def _save(e):
        from knowledge_base.seed import get_seed_documents
        from db.chroma import ChromaClient
        client = ChromaClient()
        client.add_documents(
            [f"Error: {error_field.value}\nSolution: {solution_field.value}"],
            [{"source": "knowledge_base", "error": error_field.value}],
        )
        page.dialog.open = False
        page.snack_bar = ft.SnackBar(
            ft.Text("Entry added to knowledge base", size=13),
            open=True, duration=2000,
        )
        page.update()

    page.dialog = ft.AlertDialog(
        title=ft.Text("Add KB Entry"),
        content=ft.Column([
            error_field, solution_field,
        ], width=400, spacing=8),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
            ft.ElevatedButton("Save", on_click=_save),
        ],
    )
    page.dialog.open = True
    page.update()


def kb_view(is_dark: bool = False, page=None):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    seed_errors = [
        "ModuleNotFoundError", "ImportError", "KeyError", "IndexError",
        "TypeError", "FileNotFoundError", "ValueError", "AttributeError",
        "ConnectionRefusedError", "SyntaxError", "PermissionError", "RecursionError",
    ]

    kb_cards = ft.Row([
        surface_container(
            ft.Column([
                ft.Icon(ft.Icons.DESCRIPTION, size=18, color=accent),
                ft.Container(height=4),
                ft.Text(name, size=12, color=text_p, weight=ft.FontWeight.W_500),
                ft.Text("Python", size=10, color=text_m),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=140, height=80, padding=10, is_dark=is_dark,
        ) for name in seed_errors
    ], wrap=True, spacing=8, run_spacing=8)

    search_field = ft.TextField(
        hint_text="Search knowledge base...",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=8,
        text_size=13,
        height=40,
        expand=1,
        border=border_all(1, border),
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
    )

    add_btn = ft.ElevatedButton(
        "Add Entry",
        icon=ft.Icons.ADD,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=accent,
            shape=ft.RoundedRectangleBorder(radius=6),
        ),
    )
    add_btn.on_click = lambda _: _show_add_dialog(page, is_dark)

    return ft.Container(
        content=ft.Column([
            ft.Text("Knowledge Base", size=22, weight=ft.FontWeight.BOLD, color=text_p),
            ft.Container(height=4),
            ft.Text("12 seed documents · ChromaDB vector store", size=13, color=text_s),
            ft.Container(height=12),
            search_field,
            ft.Container(height=12),
            ft.Row([
                ft.Text("Categories", size=15, weight=ft.FontWeight.W_600, color=text_p),
                ft.Container(expand=1),
                add_btn,
            ]),
            ft.Container(height=8),
            kb_cards,
        ]),
        padding=padding_symmetric(horizontal=24, vertical=16),
        expand=1,
    )
