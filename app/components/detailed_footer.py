import threading
import time

import flet as ft

from app.theme import (
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DANGER, SUCCESS, WARNING, INFO,
    FOOTER_HEIGHT, border_all, padding_symmetric,
)

STATUS_MODES = {"idle": SUCCESS, "processing": WARNING, "ready": SUCCESS, "error": DANGER}


class DetailedFooter:
    def __init__(self, agent=None, page=None, is_dark: bool = False, on_notification=None):
        self.agent = agent
        self.page = page
        self.is_dark = is_dark
        self._status_mode = "idle"
        self._has_notification = False
        self._on_notification = on_notification
        self._last_db_check = 0
        self._chroma_count = 0

        self._dot = ft.Container(width=8, height=8, border_radius=4, bgcolor=SUCCESS)
        self._mode_text = ft.Text("Ready", size=11, color=SUCCESS, weight=ft.FontWeight.W_600)

        self._llm_text = ft.Text("--", size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY)
        self._vlm_text = ft.Text("--", size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY)
        self._embed_text = ft.Text("--", size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY)

        self._token_text = ft.Text("0", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._speed_text = ft.Text("--", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)

        self._provider_text = ft.Text("Ollama", size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY)

        self._arm_badge = ft.Container(
            content=ft.Text("Balanced", size=9, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
            padding=padding_symmetric(horizontal=6, vertical=2),
            border_radius=4,
            bgcolor=DARK_ACCENT if is_dark else LIGHT_ACCENT,
        )

        self._chroma_text = ft.Text("--", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._session_text = ft.Text("--", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._ram_text = ft.Text("--", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._sessions_count = ft.Text("--", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._os_text = ft.Text("--", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._version_text = ft.Text("v1.0.0", size=11, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._notif_icon = ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED, size=14, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)

        self._running = False
        self._timer = None
        self._container = self._build()

    def _cp(self):
        d = self.is_dark
        return type("_", (), {
            "sec": DARK_TEXT_SECONDARY if d else LIGHT_TEXT_SECONDARY,
            "muted": DARK_TEXT_MUTED if d else LIGHT_TEXT_MUTED,
            "accent": DARK_ACCENT if d else LIGHT_ACCENT,
            "accent_subtle": DARK_ACCENT_SUBTLE if d else LIGHT_ACCENT_SUBTLE,
            "border": DARK_BORDER if d else LIGHT_BORDER,
            "bg_surface": DARK_BG_SURFACE if d else LIGHT_BG_SURFACE,
        })()

    def _build(self):
        c = self._cp()

        sep = lambda: ft.Container(width=1, height=18, bgcolor=c.border)

        row1 = ft.Row([
            ft.Row([self._dot, self._mode_text], spacing=6),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.MEMORY, size=13, color=c.sec),
                self._llm_text,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.IMAGE, size=13, color=c.sec),
                self._vlm_text,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.SHORT_TEXT, size=13, color=c.sec),
                self._embed_text,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.BOLT, size=13, color=c.sec),
                ft.Text("T:", size=11, color=c.muted),
                self._token_text,
                ft.Text("@", size=11, color=c.muted),
                self._speed_text,
            ], spacing=2),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.CLOUD, size=13, color=c.sec),
                self._provider_text,
            ], spacing=3),
            sep(),
            self._arm_badge,
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        row2 = ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.STORAGE, size=13, color=c.sec),
                self._chroma_text,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.CHAT, size=13, color=c.sec),
                self._session_text,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.MEMORY, size=13, color=c.sec),
                self._ram_text,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.FOLDER_OUTLINED, size=13, color=c.sec),
                self._sessions_count,
            ], spacing=3),
            sep(),
            ft.Row([
                ft.Icon(ft.Icons.COMPUTER, size=13, color=c.sec),
                self._os_text,
            ], spacing=3),
            ft.Container(expand=1),
            self._version_text,
            sep(),
            self._notif_icon,
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        return ft.Container(
            content=ft.Column([
                row1,
                ft.Container(height=2),
                row2,
            ], spacing=0),
            height=FOOTER_HEIGHT,
            padding=padding_symmetric(horizontal=16, vertical=6),
            bgcolor=c.bg_surface,
            border=border_all(0.5, c.border),
        )

    def start(self):
        self._running = True
        self._tick(None)
        self._schedule_tick()

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_tick(self):
        if not self._running:
            return
        self._timer = threading.Timer(5.0, self._do_tick)
        self._timer.daemon = True
        self._timer.start()

    def _do_tick(self):
        if not self._running:
            return
        try:
            if self.page and self._container.page:
                self._tick(None)
                self._container.update()
        except RuntimeError:
            self._running = False
            return
        self._schedule_tick()

    def _tick(self, e):
        self._update_status()
        self._update_models()
        self._update_tokens()
        self._update_provider()
        self._update_arm()
        self._update_db()
        self._update_session()
        self._update_ram()
        now = time.time()
        if now - self._last_db_check > 30:
            self._last_db_check = now
            self._update_chroma_count()
            self._update_session_count()
        try:
            self._container.update()
        except RuntimeError:
            pass

    def _update_status(self):
        if self.agent:
            connected = self.agent.ping_ollama()
            if connected:
                self._dot.bgcolor = SUCCESS
                self._mode_text.value = "Connected"
                self._mode_text.color = SUCCESS
            else:
                self._dot.bgcolor = DANGER
                self._mode_text.value = "Disconnected"
                self._mode_text.color = DANGER

    def _update_models(self):
        if self.agent:
            models = self.agent.get_active_model_names()
            self._llm_text.value = models["llm"].split(":")[0] if ":" in models["llm"] else models["llm"]
            self._vlm_text.value = models["vlm"].split(":")[0] if ":" in models["vlm"] else models["vlm"]
            self._embed_text.value = models["embedding"].split(":")[0] if ":" in models["embedding"] else models["embedding"]

    def _update_tokens(self):
        if self.agent:
            stats = self.agent.get_token_stats()
            total = stats["sent"] + stats["received"]
            self._token_text.value = f"{total:,}" if total > 0 else "0"
            speed = stats["speed"]
            self._speed_text.value = f"{speed:.1f} t/s" if speed > 0 else "--"

    def _update_provider(self):
        if self.agent:
            info = self.agent.get_provider_info()
            self._provider_text.value = info["type"].capitalize()

    def _update_arm(self):
        if self.agent:
            stats = self.agent.bandit_stats()
            arms = stats.get("arms", [])
            best = max(arms, key=lambda a: a["value"]) if arms else None
            if best:
                pct = f"{best['value'] * 100:.0f}%"
                self._arm_badge.content = ft.Text(
                    f"{best['label']} ({pct})",
                    size=9, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE,
                )

    def _update_db(self):
        if self.agent and hasattr(self.agent.rag, 'db'):
            try:
                count = self.agent.rag.db.count()
                self._chroma_count = count
                self._chroma_text.value = f"Chroma: {count}"
            except Exception:
                self._chroma_text.value = "Chroma: ?"

    def _update_session(self):
        if self.agent:
            sid = self.agent._current_session_id
            self._session_text.value = f"Session: {sid[:8]}" if sid else "Session: --"

    def _update_ram(self):
        if self.agent:
            mb = self.agent.get_memory_usage()
            self._ram_text.value = f"RAM: {mb} MB"

    def _update_chroma_count(self):
        if self.agent and hasattr(self.agent.rag, 'db'):
            try:
                count = self.agent.rag.db.count()
                self._chroma_count = count
                self._chroma_text.value = f"Chroma: {count}"
            except Exception:
                pass

    def _update_session_count(self):
        pass

    def set_session_count(self, count: int):
        self._sessions_count.value = f"Sessions: {count}"
        try:
            self._sessions_count.update()
        except RuntimeError:
            pass

    def set_os_info(self, info: str):
        self._os_text.value = info
        try:
            self._os_text.update()
        except RuntimeError:
            pass

    def set_mode(self, mode: str, arm: str | None = None):
        self._status_mode = mode
        dot_color = STATUS_MODES.get(mode, SUCCESS)
        label = mode.capitalize()
        self._dot.bgcolor = dot_color
        self._mode_text.value = label
        self._mode_text.color = dot_color
        if arm:
            self._arm_badge.content = ft.Text(arm, size=9, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE)
        try:
            self._dot.update()
            self._mode_text.update()
            if arm:
                self._arm_badge.update()
            self._container.update()
        except RuntimeError:
            pass

    def set_notification(self, has: bool):
        self._has_notification = has
        if has:
            self._notif_icon.name = ft.Icons.NOTIFICATIONS_ACTIVE
            self._notif_icon.color = WARNING
        else:
            self._notif_icon.name = ft.Icons.NOTIFICATIONS_OUTLINED
            self._notif_icon.color = self._cp().muted
        try:
            self._notif_icon.update()
        except RuntimeError:
            pass

    def build(self):
        return self._container

    def rebuild(self, is_dark):
        self.is_dark = is_dark
        old_container = self._container
        self._container = self._build()
        return self._container
