import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    TOP_BAR_HEIGHT, border_all, padding_symmetric,
)


class Toolbar:
    def __init__(self, page, is_dark=False, on_toggle_theme=None, on_project_click=None):
        self.page = page
        self.is_dark = is_dark
        self._on_toggle_theme = on_toggle_theme
        self._on_project_click = on_project_click
        self._project_name = "No Project"

        self._theme_icon = ft.Icon(
            ft.Icons.DARK_MODE_OUTLINED if is_dark else ft.Icons.LIGHT_MODE,
            size=16, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED,
        )
        self._theme_switch = ft.Switch(
            value=is_dark,
            active_color=DARK_ACCENT if is_dark else LIGHT_ACCENT,
            track_color={"": DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE},
            on_change=self._on_toggle_theme,
            scale=0.8,
        )
        self._project_btn = self._build_project_btn()
        self._container = self._build()

    def _build_project_btn(self):
        c = self._cp()
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER, size=16, color=c.accent),
                ft.Text(self._project_name, size=13, color=c.text_p, weight=ft.FontWeight.W_500),
                ft.Icon(ft.Icons.UNFOLD_MORE, size=14, color=c.text_m),
            ], spacing=4),
            padding=padding_symmetric(horizontal=10, vertical=4),
            border_radius=6,
            on_click=self._on_project_click,
        )

    def _cp(self):
        d = self.is_dark
        return type("_", (), {
            "accent": DARK_ACCENT if d else LIGHT_ACCENT,
            "accent_subtle": DARK_ACCENT_SUBTLE if d else LIGHT_ACCENT_SUBTLE,
            "text_p": DARK_TEXT_PRIMARY if d else LIGHT_TEXT_PRIMARY,
            "text_m": DARK_TEXT_MUTED if d else LIGHT_TEXT_MUTED,
            "bg_surface": DARK_BG_SURFACE if d else LIGHT_BG_SURFACE,
            "border": DARK_BORDER if d else LIGHT_BORDER,
        })()

    def _build(self):
        c = self._cp()
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.BUG_REPORT, size=22, color=c.accent),
                    width=32, height=32, border_radius=8, bgcolor=c.accent_subtle,
                ),
                ft.Text("Debugly", size=17, weight=ft.FontWeight.W_700, color=c.text_p),
                ft.Container(width=16),
                self._project_btn,
                ft.Container(expand=1),
                ft.Row([
                    self._theme_icon,
                    self._theme_switch,
                ], spacing=4),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=TOP_BAR_HEIGHT,
            padding=padding_symmetric(horizontal=20),
            bgcolor=c.bg_surface,
            border=border_all(0.5, c.border),
        )

    def set_project_name(self, name: str):
        self._project_name = name
        c = self._cp()
        self._project_btn.content = ft.Row([
            ft.Icon(ft.Icons.FOLDER, size=16, color=c.accent),
            ft.Text(name, size=13, color=c.text_p, weight=ft.FontWeight.W_500),
            ft.Icon(ft.Icons.UNFOLD_MORE, size=14, color=c.text_m),
        ], spacing=4)
        try:
            self._project_btn.update()
        except RuntimeError:
            pass

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self._theme_icon.name = ft.Icons.DARK_MODE_OUTLINED if is_dark else ft.Icons.LIGHT_MODE
        self._theme_switch.value = is_dark
        try:
            self._theme_icon.update()
            self._theme_switch.update()
        except RuntimeError:
            pass

    def build(self):
        return self._container

    def rebuild(self, is_dark):
        self.is_dark = is_dark
        self._theme_icon.name = ft.Icons.DARK_MODE_OUTLINED if is_dark else ft.Icons.LIGHT_MODE
        self._container = self._build()
        return self._container
