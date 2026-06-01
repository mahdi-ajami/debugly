import flet as ft

from app.theme import (
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    ALIGN_CENTER,
    border_all,
)


def drag_drop_zone(is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE

    selected_paths = []
    on_change_callback = None
    on_tap_callback = None

    def _set_on_change(cb):
        nonlocal on_change_callback
        on_change_callback = cb

    def _set_on_tap(cb):
        nonlocal on_tap_callback
        on_tap_callback = cb

    drop_hint = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Icon(ft.Icons.UPLOAD_FILE, size=28, color=text_m),
                alignment=ALIGN_CENTER,
            ),
            ft.Text("Drop screenshots or files here", size=12, color=text_s, weight=ft.FontWeight.W_500),
            ft.Text("or click to browse  ·  PNG, JPG, PDF, TXT, PY, ...", size=10, color=text_m),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
        alignment=ALIGN_CENTER,
        expand=1,
    )

    def _add_paths(paths):
        for p in paths:
            if p not in selected_paths:
                selected_paths.append(p)
        if on_change_callback:
            on_change_callback(list(selected_paths))

    def _clear():
        selected_paths.clear()
        if on_change_callback:
            on_change_callback([])

    async def _on_tap(e):
        if on_tap_callback:
            await on_tap_callback()

    zone = ft.GestureDetector(
        content=ft.Container(
            content=drop_hint,
            height=80,
            border_radius=8,
            bgcolor=accent_subtle,
            border=border_all(1.5, accent),
            padding=8,
        ),
        on_tap=_on_tap,
    )

    instance = {
        "zone": zone,
        "selected_paths": selected_paths,
        "add_paths": _add_paths,
        "clear": _clear,
        "set_on_change": _set_on_change,
        "set_on_tap": _set_on_tap,
    }
    return instance
