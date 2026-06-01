import flet as ft

from app.theme import (
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    DARK_ACCENT, LIGHT_ACCENT,
    DANGER, SUCCESS, WARNING,
    STATUS_BAR_HEIGHT, border_all, padding_symmetric,
)

STATUS_MODES = {"idle": SUCCESS, "processing": WARNING, "ready": SUCCESS, "error": DANGER}

class StatusBar:
    def __init__(self, agent=None, is_dark: bool = False):
        self.agent = agent
        self.is_dark = is_dark
        self._status_mode = "idle"
        self._arm_label = "Balanced"
        self._dot = ft.Container(width=6, height=6, border_radius=3, bgcolor=SUCCESS)
        self._mode_text = ft.Text("Ready", size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY)
        self._model_text = ft.Text("qwen3-coder:30b", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._arm_badge = ft.Container(
            content=ft.Text(self._arm_label, size=9, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
            padding=padding_symmetric(horizontal=6, vertical=1),
            border_radius=4,
            bgcolor=DARK_ACCENT if is_dark else LIGHT_ACCENT,
        )
        self._container = self._build()

    def _cp(self):
        return type("_", (), {
            "sec": DARK_TEXT_SECONDARY if self.is_dark else LIGHT_TEXT_SECONDARY,
            "muted": DARK_TEXT_MUTED if self.is_dark else LIGHT_TEXT_MUTED,
            "accent": DARK_ACCENT if self.is_dark else LIGHT_ACCENT,
            "border": DARK_BORDER if self.is_dark else LIGHT_BORDER,
            "bg_surface": DARK_BG_SURFACE if self.is_dark else LIGHT_BG_SURFACE,
        })()

    def _build(self):
        c = self._cp()
        return ft.Container(
            content=ft.Row([
                ft.Row([self._dot, self._mode_text], spacing=6),
                ft.Container(width=1, height=14, bgcolor=c.border),
                self._model_text,
                ft.Container(width=1, height=14, bgcolor=c.border),
                self._arm_badge,
                ft.Container(expand=1),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=13, color=SUCCESS),
                    ft.Text("KB Ready", size=11, color=c.sec),
                ], spacing=4),
                ft.Container(width=1, height=14, bgcolor=c.border),
                ft.Text("v1.0.0", size=11, color=c.muted),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            height=STATUS_BAR_HEIGHT,
            padding=padding_symmetric(horizontal=16),
            bgcolor=c.bg_surface,
            border=border_all(0.5, c.border),
        )

    def set_mode(self, mode: str, arm: str | None = None):
        self._status_mode = mode
        dot_color = STATUS_MODES.get(mode, SUCCESS)
        label = mode.capitalize()
        self._dot.bgcolor = dot_color
        self._mode_text.value = label
        if arm:
            self._arm_label = arm
            self._arm_badge.content = ft.Text(arm, size=9, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE)
        try:
            _ = self._container.page
            self._dot.update()
            self._mode_text.update()
            self._arm_badge.update()
            self._container.update()
        except RuntimeError:
            pass

    def build(self):
        return self._container

    def rebuild(self, is_dark):
        self.is_dark = is_dark
        self._container = self._build()
        return self._container