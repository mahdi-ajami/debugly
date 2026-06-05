import asyncio
import logging

import flet as ft

from app.theme import (
    surface_container,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_PRIMARY, LIGHT_BG_PRIMARY,
    DARK_BG_SIDEBAR, LIGHT_BG_SIDEBAR,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DANGER, SUCCESS, TOKEN_LOW, TOKEN_MED, TOKEN_HIGH,
    border_all, padding_symmetric, padding_only, is_rtl_text,
)
from app.components.chat_bubble import chat_bubble
from app.components.drag_drop_zone import drag_drop_zone
from app.components.diff_view import parse_diffs_from_text, diff_view
from app.components.step_view import typing_indicator, step_view, image_preview_card

logger = logging.getLogger(__name__)

_FILE_ICONS = {
    "py": ft.Icons.CODE, "js": ft.Icons.JAVASCRIPT, "ts": ft.Icons.DATA_OBJECT,
    "java": ft.Icons.CODE, "cpp": ft.Icons.CODE, "c": ft.Icons.CODE,
    "txt": ft.Icons.DESCRIPTION, "md": ft.Icons.DESCRIPTION,
    "pdf": ft.Icons.PICTURE_AS_PDF, "json": ft.Icons.DATA_ARRAY,
    "yaml": ft.Icons.SETTINGS, "yml": ft.Icons.SETTINGS,
    "png": ft.Icons.IMAGE, "jpg": ft.Icons.IMAGE, "jpeg": ft.Icons.IMAGE,
    "webp": ft.Icons.IMAGE, "bmp": ft.Icons.IMAGE,
    "log": ft.Icons.ARTICLE, "csv": ft.Icons.TABLE_CHART,
    "html": ft.Icons.CODE, "css": ft.Icons.CODE,
    "jsx": ft.Icons.CODE, "tsx": ft.Icons.CODE,
}

_MCP_COMMANDS = {
    "/write": "Write content to a file",
    "/edit": "Edit/replace content in a file",
    "/delete": "Delete a file",
    "/cmd": "Execute a shell command",
    "/search": "Search the web for information",
    "/kb": "Search the knowledge base",
    "/step": "Manage debug steps",
    "/help": "Show available commands",
}


def _get_file_icon(ext: str):
    return _FILE_ICONS.get(ext, ft.Icons.ATTACH_FILE)


def _get_ext(filename: str) -> str:
    return filename.split(".")[-1].lower() if "." in filename else ""


def _file_attachment_chip(fname: str, is_dark: bool):
    ext = _get_ext(fname)
    icon = _get_file_icon(ext)
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=16, color=accent),
            ft.Text(fname, size=11, color=accent, weight=ft.FontWeight.W_500),
            ft.Container(
                content=ft.Text(ext.upper() or "?", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                padding=padding_symmetric(horizontal=5, vertical=1),
                border_radius=3,
                bgcolor=accent,
            ),
        ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=padding_symmetric(horizontal=10, vertical=6),
        border_radius=6,
        bgcolor=accent_subtle,
    )


_IMAGE_EXTS = {"png", "jpg", "jpeg", "bmp", "webp"}


class DebugView:
    def __init__(self, page, agent, is_dark=False, on_new_session=None, status_bar=None):
        self.page = page
        self.agent = agent
        self.is_dark = is_dark
        self.on_new_session = on_new_session
        self._status_bar = status_bar
        self.last_state = None
        self._current_arm = None
        self._processing = False
        self._session = None
        self._current_events = []
        self._stop_requested = False
        self._sidebar_visible = True
        self._changes_visible = True
        self._sidebar_steps = []
        self._sidebar_files = []
        self._diff_cards = []
        self._changes_tab_index = 0
        self._has_welcome = False
        self._input_focused = False

        # Eager processing caches
        self._eager_vlm_results: dict[str, str] = {}
        self._eager_file_contents: dict[str, str] = {}
        # Track preview card refs so we can update them dynamically
        self._preview_cards: dict[str, ft.Container] = {}

        self.text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
        self.text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
        self.accent = DARK_ACCENT if is_dark else LIGHT_ACCENT

        self.chat_log = ft.ListView(expand=1, spacing=8, padding=10, auto_scroll=True)
        self.sources_panel = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)

        self._sidebar_step_list = ft.Column(spacing=2)
        self._sidebar_file_list = ft.Column(spacing=2)
        self._sidebar_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.LIST_ALT, size=14, color=DARK_ACCENT if is_dark else LIGHT_ACCENT),
                        ft.Text("Steps", size=11, weight=ft.FontWeight.W_600, color=DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY),
                    ], spacing=4),
                    padding=padding_symmetric(horizontal=8, vertical=6),
                ),
                ft.Divider(height=1, color=DARK_BORDER if is_dark else LIGHT_BORDER),
                ft.Container(content=ft.Column([self._sidebar_step_list], scroll=ft.ScrollMode.AUTO, expand=1), expand=1, padding=padding_symmetric(horizontal=4)),
                ft.Divider(height=1, color=DARK_BORDER if is_dark else LIGHT_BORDER),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DESCRIPTION, size=14, color=DARK_ACCENT if is_dark else LIGHT_ACCENT),
                        ft.Text("Files", size=11, weight=ft.FontWeight.W_600, color=DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY),
                    ], spacing=4),
                    padding=padding_symmetric(horizontal=8, vertical=6),
                ),
                ft.Container(content=self._sidebar_file_list, padding=padding_symmetric(horizontal=4)),
            ], spacing=0),
            width=180,
            bgcolor=DARK_BG_SIDEBAR if is_dark else LIGHT_BG_SIDEBAR,
            border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
        )

        self._changes_panel = ft.Column(spacing=4, expand=True, scroll=ft.ScrollMode.AUTO)
        self._changes_tab_0 = ft.Container(
            content=ft.Text("Changes", size=11, weight=ft.FontWeight.W_600),
            padding=padding_symmetric(horizontal=10, vertical=5),
            on_click=lambda _: self._switch_changes_tab(0),
        )
        self._changes_tab_1 = ft.Container(
            content=ft.Text("Sources", size=11, weight=ft.FontWeight.W_600),
            padding=padding_symmetric(horizontal=10, vertical=5),
            on_click=lambda _: self._switch_changes_tab(1),
        )
        self._changes_header = ft.Container(
            content=ft.Row([self._changes_tab_0, self._changes_tab_1, ft.Container(expand=1)], spacing=0),
            border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
            border_radius=6,
            bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        )

        self._token_label = ft.Text("0 tok", size=10, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._token_bar = ft.Container(content=self._token_label, padding=padding_symmetric(horizontal=6))

        self.error_input = ft.TextField(
            hint_text="Type error or /command...",
            expand=1,
            multiline=True,
            min_lines=1,
            max_lines=4,
            text_size=14,
            border_radius=8,
            border=border_all(1, DARK_BORDER if is_dark else LIGHT_BORDER),
            bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
            on_change=self._on_input_change,
            on_focus=lambda _: setattr(self, '_input_focused', True),
            on_blur=lambda _: setattr(self, '_input_focused', False),
        )

        self.attach_btn = ft.IconButton(
            icon=ft.Icons.ATTACH_FILE,
            icon_size=20,
            tooltip="Attach files",
            style=ft.ButtonStyle(color=self.text_s),
            on_click=self._on_attach,
        )

        self.send_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_size=22,
            tooltip="Send (Ctrl+Enter)",
            style=ft.ButtonStyle(color=self.accent),
            on_click=self._on_send,
        )

        self.stop_btn = ft.IconButton(
            icon=ft.Icons.STOP_CIRCLE_OUTLINED,
            icon_size=22,
            tooltip="Stop generation",
            style=ft.ButtonStyle(color=DANGER),
            on_click=self._on_stop,
            visible=False,
        )

        # Singleton FilePicker
        self._file_picker = ft.FilePicker()

        self._drop_instance = drag_drop_zone(is_dark=is_dark)
        self.drop_zone = self._drop_instance["zone"]

        self._attach_chips = ft.Row(spacing=6, wrap=True)
        self._attachment_bar = ft.Container(
            content=ft.Column([
                ft.Divider(height=1, color=DARK_BORDER if is_dark else LIGHT_BORDER),
                ft.Row([
                    self._attach_chips,
                    ft.Container(expand=1),
                    ft.TextButton("Clear", on_click=self._on_clear_attachments),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]),
            visible=False,
            padding=padding_only(top=4, bottom=2),
        )

        def _page_key_handler(e: ft.KeyboardEvent):
            if e.ctrl and e.key == "Enter" and self._input_focused:
                self._on_send(None)
        page.on_keyboard_event = _page_key_handler

        self._drop_instance["set_on_change"](self._on_drop_files_changed)
        self._drop_instance["set_on_tap"](self._on_drop_zone_tap)
        try:
            self._switch_changes_tab(0)
        except RuntimeError:
            pass

    # ---- File picker ----
    async def _on_drop_zone_tap(self):
        result = await self._file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "webp", "txt", "py", "js", "ts", "pdf", "md", "json", "yaml", "yml", "log", "csv"],
        )
        if result:
            self._drop_instance["add_paths"]([f.path for f in result])

    async def _on_attach(self, e):
        result = await self._file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "webp", "txt", "py", "js", "ts", "pdf", "md", "json", "yaml", "yml", "log", "csv"],
        )
        if result:
            self._drop_instance["add_paths"]([f.path for f in result])

    # ---- Eager processing on drop ----
    def _on_drop_files_changed(self, paths):
        self._attach_chips.controls.clear()
        self._preview_cards.clear()
        for p in paths:
            fname = p.split("\\")[-1]
            chip = _file_attachment_chip(fname, self.is_dark)
            self._attach_chips.controls.append(chip)
            ext = _get_ext(fname)
            if ext in _IMAGE_EXTS:
                card = image_preview_card(p, self.is_dark)
                self._attach_chips.controls.append(card)
                self._preview_cards[p] = card
                # Fire-and-forget eager VLM
                asyncio.create_task(self._eager_process_image(p, card))
            else:
                # Fire-and-forget eager file read
                asyncio.create_task(self._eager_read_file(p))
        self._attachment_bar.visible = bool(paths)
        self._attachment_bar.update()

    async def _eager_process_image(self, path: str, card: ft.Container):
        try:
            from PIL import Image
            from core.vlm_handler import VLMHandler
            img = Image.open(path)
            vlm = VLMHandler(providers=self.agent.providers)
            text = await asyncio.to_thread(vlm.extract_text, img)
            self._eager_vlm_results[path] = text
            # Update card inline with a status message
            def _update():
                card.content = ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=SUCCESS),
                    ft.Text(f"VLM done ({len(text)} chars)", size=10, color=DARK_TEXT_SECONDARY if self.is_dark else LIGHT_TEXT_SECONDARY),
                ], spacing=4)
                card.update()
            try:
                _update()
            except RuntimeError:
                pass
        except Exception as exc:
            logger.warning("Eager VLM failed for %s: %s", path, exc)
            self._eager_vlm_results[path] = ""

    async def _eager_read_file(self, path: str):
        try:
            content = await asyncio.to_thread(lambda: open(path, encoding="utf-8", errors="replace").read())
            self._eager_file_contents[path] = content
        except Exception as exc:
            logger.warning("Eager file read failed for %s: %s", path, exc)
            self._eager_file_contents[path] = ""

    # ---- Misc UI helpers ----
    def _on_input_change(self, e):
        text = e.control.value or ""
        rtl = is_rtl_text(text)
        self.error_input.text_align = ft.TextAlign.RIGHT if rtl else ft.TextAlign.LEFT
        chars = len(text)
        tokens = self._estimate_tokens(text)
        pct = tokens / 4000
        if pct < 0.7:
            color = TOKEN_LOW
        elif pct < 0.9:
            color = TOKEN_MED
        else:
            color = TOKEN_HIGH
        self._token_label.value = f"~{tokens} tok   {chars} chr"
        self._token_label.color = color
        self._token_label.update()

    def _on_stop(self, e):
        self._stop_requested = True

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text) * 0.35) + 1

    def _switch_changes_tab(self, index: int):
        self._changes_tab_index = index
        accent_sub = DARK_ACCENT_SUBTLE if self.is_dark else LIGHT_ACCENT_SUBTLE
        trans = "transparent"
        self._changes_tab_0.bgcolor = accent_sub if index == 0 else trans
        self._changes_tab_1.bgcolor = accent_sub if index == 1 else trans
        self._changes_tab_0.border_radius = ft.BorderRadius(top_left=6 if index == 0 else 0, top_right=0, bottom_left=6 if index == 0 else 0, bottom_right=0)
        self._changes_tab_1.border_radius = ft.BorderRadius(top_left=0, top_right=6 if index == 1 else 0, bottom_left=0, bottom_right=6 if index == 1 else 0)
        self._changes_header.update()
        self._refresh_changes_panel()

    def _refresh_changes_panel(self):
        self._changes_panel.controls.clear()
        if self._changes_tab_index == 0:
            if self._diff_cards:
                for card in self._diff_cards:
                    self._changes_panel.controls.append(card)
            else:
                self._changes_panel.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.CODE_OFF, size=24, color=DARK_TEXT_MUTED if self.is_dark else LIGHT_TEXT_MUTED),
                            ft.Text("No file changes yet", size=11, color=DARK_TEXT_MUTED if self.is_dark else LIGHT_TEXT_MUTED),
                            ft.Text("Agent suggestions with file annotations will appear here", size=9, color=DARK_TEXT_MUTED if self.is_dark else LIGHT_TEXT_MUTED),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                        padding=20,
                    )
                )
        else:
            if self.sources_panel.controls:
                self._changes_panel.controls.append(self.sources_panel)
            else:
                self._changes_panel.controls.append(
                    ft.Container(content=ft.Text("No sources loaded", size=11, color=DARK_TEXT_MUTED if self.is_dark else LIGHT_TEXT_MUTED), padding=20)
                )
        try:
            self._changes_panel.update()
        except RuntimeError:
            pass

    def _add_sidebar_step(self, step_type: str, content: str):
        icon_map = {"think": ft.Icons.PSYCHOLOGY, "retrieve": ft.Icons.SEARCH, "tool": ft.Icons.BUILD, "generate": ft.Icons.AUTO_FIX_HIGH}
        icon = icon_map.get(step_type, ft.Icons.CIRCLE)
        self._sidebar_step_list.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=12, color=DARK_ACCENT if self.is_dark else LIGHT_ACCENT),
                    ft.Text(content[:60], size=10, color=DARK_TEXT_SECONDARY if self.is_dark else LIGHT_TEXT_SECONDARY, expand=1),
                ], spacing=4),
                padding=padding_symmetric(horizontal=4, vertical=2),
                border_radius=4,
            )
        )
        try:
            self._sidebar_step_list.update()
        except RuntimeError:
            pass

    def _add_sidebar_file(self, file_path: str):
        if file_path in self._sidebar_files:
            return
        self._sidebar_files.append(file_path)
        self._sidebar_file_list.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=12, color=DARK_ACCENT if self.is_dark else LIGHT_ACCENT),
                    ft.Text(file_path.split("\\")[-1], size=10, color=DARK_TEXT_SECONDARY if self.is_dark else LIGHT_TEXT_SECONDARY, expand=1),
                ], spacing=4),
                padding=padding_symmetric(horizontal=4, vertical=2),
                border_radius=4,
            )
        )
        try:
            self._sidebar_file_list.update()
        except RuntimeError:
            pass

    def _add_bubble(self, text, is_user=False, is_markdown=False, timestamp="", attachments=None, steps=None):
        b = chat_bubble(text, is_user=is_user, is_markdown=is_markdown, is_dark=self.is_dark, timestamp=timestamp, attachments=attachments, steps=steps)
        if self._has_welcome:
            self.chat_log.controls.clear()
            self._has_welcome = False
        self.chat_log.controls.append(ft.Container(content=b, margin=ft.Margin(left=0, top=0, right=0, bottom=0)))
        try:
            self.chat_log.update()
        except RuntimeError:
            pass

    def _show_sources(self, docs, web_results=None):
        self.sources_panel.controls.clear()
        accent_subtle = DARK_ACCENT_SUBTLE if self.is_dark else LIGHT_ACCENT_SUBTLE
        self.sources_panel.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ARTICLE_OUTLINED, size=14, color=self.accent),
                        ft.Text("Sources", size=12, weight=ft.FontWeight.BOLD, color=self.text_p),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text("Knowledge base & web references", size=9, color=self.text_s),
                ], spacing=2),
                padding=padding_only(bottom=4),
            )
        )
        if web_results:
            self.sources_panel.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.LANGUAGE, size=12, color=ft.Colors.BLUE_400),
                        ft.Text(f"Web ({len(web_results)})", size=10, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_400),
                    ], spacing=4),
                    padding=padding_only(left=2, top=4, bottom=2),
                )
            )
            for r in web_results[:3]:
                self.sources_panel.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(r.get("source", "")[:60], size=9, weight=ft.FontWeight.W_500, color=self.accent),
                            ft.Text(r.get("content", "")[:60] + "...", size=8, color=self.text_s),
                        ], spacing=1),
                        padding=10, border_radius=4, bgcolor=accent_subtle,
                    )
                )
        if docs:
            self.sources_panel.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DATASET, size=12, color=self.accent),
                        ft.Text(f"KB ({len(docs)})", size=10, weight=ft.FontWeight.W_600, color=self.accent),
                    ], spacing=4),
                    padding=padding_only(left=2, top=4, bottom=2),
                )
            )
            for d in docs:
                score = d.get("score", 0)
                badge_color = ft.Colors.GREEN_400 if score >= 0.7 else (ft.Colors.AMBER_400 if score >= 0.4 else ft.Colors.GREY_400)
                badge_txt = "High" if score >= 0.7 else ("Med" if score >= 0.4 else "Low")
                card = surface_container(
                    ft.Column([
                        ft.Row([
                            ft.Text(d.get("source", "kb"), size=10, weight=ft.FontWeight.W_500, color=self.accent, expand=1),
                            ft.Container(
                                content=ft.Text(badge_txt, size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                padding=padding_only(left=5, top=2, right=5, bottom=2), border_radius=4, bgcolor=badge_color,
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(d.get("content", "")[:80] + "...", size=9, color=self.text_s),
                    ], spacing=2),
                    width=240, padding=8, is_dark=self.is_dark,
                )
                self.sources_panel.controls.append(card)
        try:
            self.sources_panel.update()
        except RuntimeError:
            pass
        self._refresh_changes_panel()

    # ---- Core async message processing ----
    async def _process_message_task(self, text: str, images: list[str], files: list[str]):
        self._processing = True
        self._stop_requested = False
        self._current_events = []
        self._update_status("processing")
        self._sidebar_step_list.controls.clear()
        self._sidebar_file_list.controls.clear()
        self._sidebar_files.clear()
        self._diff_cards.clear()

        # Build attachment chips for user bubble
        attachments = []
        for img in images:
            fname = img.split("\\")[-1]
            attachments.append(_file_attachment_chip(fname, self.is_dark))
        for f in files:
            fname = f.split("\\")[-1]
            attachments.append(_file_attachment_chip(fname, self.is_dark))

        parts = [text] if text else []
        self._add_bubble(parts[0] if parts else "Debug request", is_user=True, attachments=attachments)
        self.page.update()

        if self._session:
            content = text or ""
            if images:
                content += "\n[Images: " + ", ".join(i.split("\\")[-1] for i in images) + "]"
            if files:
                content += "\n[Files: " + ", ".join(f.split("\\")[-1] for f in files) + "]"
            self._session.add_message(role="user", content=content)

        history_list = [{"role": m.role, "content": m.content} for m in (self._session.messages if self._session else [])]

        # Build assistant container (hidden until first content)
        steps_col = ft.Column(spacing=4)
        typing_ind = typing_indicator(self.is_dark)
        md = ft.Markdown(
            value="",
            extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            code_theme="monokai-sublime" if self.is_dark else "github",
            selectable=True,
        )
        bubble_container = ft.Container(
            content=ft.Column([md], spacing=4),
            padding=padding_symmetric(horizontal=14, vertical=10),
            bgcolor=DARK_BG_SURFACE if self.is_dark else LIGHT_BG_SURFACE,
            border_radius=ft.BorderRadius(top_left=4, top_right=16, bottom_left=16, bottom_right=16),
            border=border_all(0.5, DARK_BORDER if self.is_dark else LIGHT_BORDER),
            visible=False,  # hidden until markdown content arrives
        )
        assistant_content = ft.Column([steps_col, typing_ind, bubble_container], spacing=6)
        row_wrapper = ft.Container(content=assistant_content, margin=ft.Margin(left=26, top=0, right=0, bottom=0))

        if self._has_welcome:
            self.chat_log.controls.clear()
            self._has_welcome = False
        self.chat_log.controls.append(row_wrapper)
        self.page.update()

        # Warmup step
        steps_col.controls.append(step_view("warmup", "Initializing agents...", is_dark=self.is_dark))
        steps_col.update()
        self._add_sidebar_step("think", "Warming up agents...")

        # Decide query: use eager VLM results if available
        query = text
        eager_vlm = self._eager_vlm_results.get(images[0]) if images else None
        if not query and images and eager_vlm:
            query = eager_vlm
        elif not query and images and not eager_vlm:
            # Fallback: process inline (shouldn't happen if eager works)
            try:
                from PIL import Image as PILImage
                from core.vlm_handler import VLMHandler
                img = PILImage.open(images[0])
                vlm = VLMHandler(providers=self.agent.providers)
                query = vlm.extract_text(img)
            except Exception:
                query = "Analyze the attached screenshot"

        # Show VLM step when images present
        if images:
            vlm_text = self._eager_vlm_results.get(images[0], query)
            steps_col.controls.append(step_view("image", f"VLM extracted ({len(vlm_text)} chars)", is_dark=self.is_dark))
            steps_col.update()

        # Build context dict for agent
        ctx = {"images": images, "files": files, "file_contents": self._eager_file_contents}
        if images:
            ctx["vlm_text"] = self._eager_vlm_results.get(images[0], "")

        # Start the agent pipeline
        event_stream, state = await asyncio.to_thread(
            self.agent.solve, query, True, history_list, ctx
        )
        self._current_arm = state.arm_selected
        self.last_state = state

        full_text = ""
        for event in event_stream:
            if self._stop_requested:
                break
            self._current_events.append(event)
            if event.type in ("think", "retrieve", "tool", "warmup", "wait"):
                sv = step_view(event.type, event.content, event.metadata, is_dark=self.is_dark)
                steps_col.controls.append(sv)
                steps_col.update()
                self._add_sidebar_step(event.type, event.content)
            elif event.type == "error":
                sv = step_view("error", event.content, event.metadata, is_dark=self.is_dark)
                steps_col.controls.append(sv)
                steps_col.update()
                bubble_container.visible = True
                md.value = event.content
                md.update()
                bubble_container.update()
            elif event.type == "generate":
                if typing_ind in assistant_content.controls:
                    assistant_content.controls.remove(typing_ind)
                    assistant_content.update()
                bubble_container.visible = True
                bubble_container.update()
                if event.metadata.get("partial"):
                    full_text += event.content
                    md.value = full_text
                    md.update()

        if full_text:
            md.value = full_text
            md.update()
        if typing_ind in assistant_content.controls:
            assistant_content.controls.remove(typing_ind)
            assistant_content.update()
        self._show_sources(state.retrieved_docs, web_results=state.web_results)

        parsed = parse_diffs_from_text(full_text)
        for d in parsed:
            card = diff_view(d["file_path"], d["lines"], d["add_count"], d["del_count"], is_dark=self.is_dark)
            self._diff_cards.append(card)
            self._add_sidebar_file(d["file_path"])
        self._refresh_changes_panel()

        # Save assistant message WITH steps
        if self._session and full_text:
            self._session.add_message(role="assistant", content=full_text, steps=self._current_events)
            self._session.save()
        arm_name = ["Conservative", "Balanced", "Creative"][self._current_arm] if self._current_arm is not None else None
        self._update_status("ready", arm_name)

        self._processing = False
        self.send_btn.visible = True
        self.stop_btn.visible = False
        try:
            self.send_btn.update()
            self.stop_btn.update()
        except RuntimeError:
            pass

    def _process_message(self, text: str, images: list[str], files: list[str]):
        asyncio.create_task(self._process_message_task(text, images, files))

    # ---- Send / MCP ----
    def _on_send(self, e):
        if self._processing:
            return
        text = self.error_input.value.strip()
        drop_files = list(self._drop_instance["selected_paths"])

        if not text and not drop_files:
            return

        if text.startswith("/"):
            self._handle_mcp_command(text, drop_files)
            return

        images = [p for p in drop_files if _get_ext(p) in _IMAGE_EXTS]
        code_files = [p for p in drop_files if _get_ext(p) not in _IMAGE_EXTS]

        self.error_input.value = ""
        self.error_input.update()
        self._token_label.value = "0 tok"
        self._token_label.update()
        self._drop_instance["clear"]()

        # Clear eager caches after sending (they've been consumed)
        self._eager_vlm_results.clear()
        self._eager_file_contents.clear()

        self._process_message(text, images, code_files)

    def _handle_mcp_command(self, cmd: str, files: list[str]):
        parts = cmd.split(maxsplit=2)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        extra = parts[2] if len(parts) > 2 else ""

        if command == "/help":
            help_text = "\n".join(f"  {k}  - {v}" for k, v in _MCP_COMMANDS.items())
            self._add_bubble(f"**MCP Commands:**\n{help_text}", is_user=False, is_markdown=True)
            return

        if command == "/write":
            if not args:
                self._add_bubble("**Usage:** /write filename.py\n```\ncode here\n```", is_user=False, is_markdown=True)
                return
            self._add_bubble(f"**Writing to:** `{args}`", is_user=False, is_markdown=True)
            return

        if command == "/search":
            if not args and not files:
                self._add_bubble("**Usage:** /search query or attach files", is_user=False, is_markdown=True)
                return
            query = args or "Search attached files"
            self._process_message(query, [], files)
            return

        if command == "/kb":
            query = args or "List knowledge base"
            self._process_message(f"Search knowledge base for: {query}", [], [])
            return

        self._add_bubble(f"Unknown command: {command}. Type /help for commands.", is_user=False, is_markdown=True)

    def load_session(self, session):
        self._session = session
        self.chat_log.controls.clear()
        self.sources_panel.controls.clear()
        self._sidebar_step_list.controls.clear()
        self._sidebar_file_list.controls.clear()
        self._sidebar_files.clear()
        self._diff_cards.clear()
        self._has_welcome = False
        source = session.context.get("source_file", "") or ""
        if source:
            fname = source.split("\\")[-1]
            self._add_bubble(f"Opened file", is_user=True, attachments=[_file_attachment_chip(fname, self.is_dark)])
        for msg in session.messages:
            is_user = msg.role == "user"
            steps = msg.steps if hasattr(msg, "steps") else []
            self._add_bubble(msg.content, is_user=is_user, is_markdown=not is_user, timestamp=msg.timestamp, steps=steps)
        self.page.update()

    def _update_status(self, mode="idle", arm=None):
        if self._status_bar:
            self._status_bar.set_mode(mode, arm)

    def _on_drop_files_changed_clear(self):
        self._eager_vlm_results.clear()
        self._eager_file_contents.clear()

    def _on_clear_attachments(self, e):
        self._drop_instance["clear"]()
        self._eager_vlm_results.clear()
        self._eager_file_contents.clear()

    def build(self):
        input_row = ft.Container(
            content=ft.Column([
                self._attachment_bar,
                ft.Row(
                    [self.error_input, self._token_bar, self.attach_btn, self.send_btn, self.stop_btn],
                    vertical_alignment=ft.CrossAxisAlignment.END, spacing=4,
                ),
            ]),
            padding=padding_only(top=6, bottom=2),
        )

        session_id = self._session.id[:8] if self._session else ""
        header_row = ft.Row([
            ft.Column([
                ft.Text("Debug Session", size=18, weight=ft.FontWeight.BOLD, color=self.text_p),
                ft.Text(f"Session: {session_id}" if session_id else "Start a new debug session", size=10, color=self.text_s),
            ]),
            ft.Container(expand=1),
            ft.ElevatedButton(
                "New Chat", icon=ft.Icons.ADD,
                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=self.accent, padding=padding_symmetric(horizontal=12, vertical=5), shape=ft.RoundedRectangleBorder(radius=6)),
                on_click=lambda _: self.on_new_session() if self.on_new_session else None,
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        chat_area = ft.Column([self.chat_log], expand=2, spacing=2)
        if not self.chat_log.controls and not self._has_welcome:
            self._has_welcome = True
            self.chat_log.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CHAT_OUTLINED, size=36, color=self.text_s),
                        ft.Container(height=6),
                        ft.Text("Ready to Debug", size=16, weight=ft.FontWeight.W_600, color=self.text_p),
                        ft.Text("Drop a screenshot or type an error message below", size=11, color=self.text_s),
                        ft.Text("Type /help for commands  •  Ctrl+Enter to send", size=10, color=self.text_s),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    expand=1,
                )
            )

        sidebar_help = ft.Container(width=3)
        changes_help = ft.Container(width=3)

        content_row = ft.Row([
            self._sidebar_container if self._sidebar_visible else sidebar_help,
            ft.VerticalDivider(width=1, color=DARK_BORDER if self.is_dark else LIGHT_BORDER) if self._sidebar_visible else ft.Container(width=0),
            chat_area,
            ft.VerticalDivider(width=1, color=DARK_BORDER if self.is_dark else LIGHT_BORDER) if self._changes_visible else ft.Container(width=0),
            ft.Column([self._changes_header, ft.Divider(height=1, color=DARK_BORDER if self.is_dark else LIGHT_BORDER), self._changes_panel], expand=1, spacing=2) if self._changes_visible else changes_help,
        ], expand=1, spacing=4, vertical_alignment=ft.CrossAxisAlignment.START)

        return ft.Container(
            content=ft.Column([
                header_row,
                ft.Container(height=4),
                self.drop_zone,
                ft.Divider(height=4, color="transparent"),
                content_row,
                input_row,
            ], spacing=2),
            padding=padding_symmetric(horizontal=20, vertical=10),
            expand=1,
        )
