import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    padding_symmetric,
)


class SessionList:
    def __init__(self, sessions: list | None = None,
                 active_id: str | None = None,
                 on_select=None, on_new=None,
                 is_dark: bool = False):
        self.sessions = sessions or []
        self.active_id = active_id
        self.on_select = on_select
        self.on_new = on_new
        self.is_dark = is_dark
        self._container = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self._build()

    def _cp(self):
        d = self.is_dark
        return type("_", (), {
            "accent": DARK_ACCENT if d else LIGHT_ACCENT,
            "accent_subtle": DARK_ACCENT_SUBTLE if d else LIGHT_ACCENT_SUBTLE,
            "text_p": DARK_TEXT_PRIMARY if d else LIGHT_TEXT_PRIMARY,
            "text_s": DARK_TEXT_SECONDARY if d else LIGHT_TEXT_SECONDARY,
            "text_m": DARK_TEXT_MUTED if d else LIGHT_TEXT_MUTED,
            "bg_surface": DARK_BG_SURFACE if d else LIGHT_BG_SURFACE,
            "border": DARK_BORDER if d else LIGHT_BORDER,
        })()

    def _build(self):
        self._container.controls.clear()
        c = self._cp()

        header = ft.Container(
            content=ft.Row([
                ft.Text("Conversations", size=11, weight=ft.FontWeight.W_600, color=c.text_m),
                ft.Container(expand=1),
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    icon_size=18,
                    icon_color=c.accent,
                    tooltip="New conversation",
                    on_click=lambda _: self.on_new() if self.on_new else None,
                ),
            ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=padding_symmetric(horizontal=8, vertical=4),
        )
        self._container.controls.append(header)

        if not self.sessions:
            empty = ft.Container(
                content=ft.Text("No conversations yet", size=11, color=c.text_m, italic=True),
                padding=padding_symmetric(horizontal=12, vertical=6),
            )
            self._container.controls.append(empty)
        else:
            for s in self.sessions:
                sid = s.get("id", "")
                preview = s.get("preview", "") or "Empty session"
                preview = preview if len(preview) < 50 else preview[:47] + "..."
                is_active = sid == self.active_id
                row = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.CHAT_OUTLINED, size=14,
                                            color=c.accent if is_active else c.text_m),
                            width=20,
                        ),
                        ft.Text(preview, size=11,
                                color=c.text_p if is_active else c.text_s,
                                weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.W_400,
                                expand=1),
                    ], spacing=4),
                    padding=padding_symmetric(horizontal=10, vertical=6),
                    border_radius=6,
                    bgcolor=c.accent_subtle if is_active else None,
                    on_click=lambda _, sid=sid: self.on_select(sid) if self.on_select else None,
                )
                self._container.controls.append(row)

    def update_data(self, sessions: list, active_id: str | None = None):
        self.sessions = sessions
        self.active_id = active_id
        self._build()
        self._container.update()

    def build(self):
        return self._container
