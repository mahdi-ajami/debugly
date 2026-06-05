import asyncio
import logging
import time

import flet as ft

from app.theme import (
    surface_container,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_ACCENT_SECONDARY, LIGHT_ACCENT_SECONDARY,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_PRIMARY, LIGHT_BG_PRIMARY,
    DARK_BG_SIDEBAR, LIGHT_BG_SIDEBAR,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DANGER, SUCCESS, WARNING, INFO,
    TOKEN_LOW, TOKEN_MED, TOKEN_HIGH,
    border_all, padding_symmetric, padding_only, is_rtl_text,
)
from app.components.chat_bubble import chat_bubble
from app.components.drag_drop_zone import drag_drop_zone
from app.components.diff_view import parse_diffs_from_text, diff_view
from app.components.step_view import typing_indicator, step_view, image_preview_card, STEP_STYLE
from app.components.session_form import session_config_form, DEFAULT_SESSION_CFG
from app.components.code_analysis_view import code_analysis_view
from core.session import StepEvent
from core.rag_pipeline import RAGPipeline

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
    "/search_kb": "Search knowledge base (alias for /kb)",
    "/step": "Manage debug steps",
    "/help": "Show available commands",
}

_IMAGE_EXTS = {"png", "jpg", "jpeg", "bmp", "webp"}


def _get_ext(filename: str) -> str:
    return filename.split(".")[-1].lower() if "." in filename else ""


def _file_attachment_chip(fname: str, is_dark: bool):
    ext = _get_ext(fname)
    icon = _FILE_ICONS.get(ext, ft.Icons.ATTACH_FILE)
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    return ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=14, color=accent),
            ft.Text(fname, size=10, color=accent, weight=ft.FontWeight.W_500),
            ft.Container(
                content=ft.Text(ext.upper() or "?", size=7, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                padding=padding_symmetric(horizontal=4, vertical=1),
                border_radius=3, bgcolor=accent,
            ),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=padding_symmetric(horizontal=8, vertical=4),
        border_radius=6, bgcolor=accent_subtle,
    )


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
        self._sidebar_files = []
        self._diff_cards = []
        self._changes_tab_index = 0
        self._has_welcome = False
        self._input_focused = False
        self._session_cfg = dict(DEFAULT_SESSION_CFG)

        # Eager processing caches
        self._eager_vlm_results: dict[str, str] = {}
        self._eager_vlm_parsed: dict[str, dict] = {}
        self._eager_file_contents: dict[str, str] = {}

        self.text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
        self.text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
        self.text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
        self.accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
        self.accent_sub = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
        self.accent2 = DARK_ACCENT_SECONDARY if is_dark else LIGHT_ACCENT_SECONDARY
        self.bg_surface = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE
        self.border = DARK_BORDER if is_dark else LIGHT_BORDER

        # Chat log
        self.chat_log = ft.ListView(expand=1, spacing=8, padding=10, auto_scroll=True)

        # Steps sidebar
        self._steps_section = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=1)
        self._steps_header = self._section_header("Steps", ft.Icons.PSYCHOLOGY)
        self._sidebar_container = ft.Container(
            content=ft.Column([
                self._steps_header,
                ft.Divider(height=1, color=self.border),
                ft.Container(content=self._steps_section, expand=1, padding=padding_symmetric(horizontal=6)),
            ], spacing=0),
            width=200, bgcolor=DARK_BG_SIDEBAR if is_dark else LIGHT_BG_SIDEBAR,
            border=border_all(0.5, self.border),
        )

        # Sources/Changes panel
        self._changes_panel = ft.Column(spacing=4, expand=True, scroll=ft.ScrollMode.AUTO)
        self._changes_tab_0 = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CODE, size=12, color=self.accent),
                ft.Text("Changes", size=10, weight=ft.FontWeight.W_600, color=self.text_p),
            ], spacing=4),
            padding=padding_symmetric(horizontal=8, vertical=5),
            on_click=lambda _: self._switch_changes_tab(0),
        )
        self._changes_tab_1 = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ARTICLE, size=12, color=self.accent),
                ft.Text("Sources", size=10, weight=ft.FontWeight.W_600, color=self.text_p),
            ], spacing=4),
            padding=padding_symmetric(horizontal=8, vertical=5),
            on_click=lambda _: self._switch_changes_tab(1),
        )
        self._changes_header = ft.Container(
            content=ft.Row([self._changes_tab_0, self._changes_tab_1, ft.Container(expand=1)], spacing=0),
            border=border_all(0.5, self.border),
            border_radius=6, bgcolor=self.bg_surface,
        )
        self.sources_panel = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6)

        # Token counter
        self._token_label = ft.Text("0 tok", size=9, color=self.text_m)
        self._token_bar = ft.Container(content=self._token_label, padding=padding_symmetric(horizontal=4))

        # Input field
        self.error_input = ft.TextField(
            hint_text="Type a message or /command...",
            expand=1, multiline=True, min_lines=1, max_lines=4,
            text_size=13, border_radius=8,
            border=border_all(1, self.border),
            bgcolor=self.bg_surface,
            on_change=self._on_input_change,
            on_focus=lambda _: setattr(self, '_input_focused', True),
            on_blur=lambda _: setattr(self, '_input_focused', False),
        )

        # Buttons
        self.attach_btn = ft.IconButton(
            icon=ft.Icons.ATTACH_FILE, icon_size=18, tooltip="Attach files",
            style=ft.ButtonStyle(color=self.text_s), on_click=self._on_attach,
        )
        self.send_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED, icon_size=20, tooltip="Send (Ctrl+Enter)",
            style=ft.ButtonStyle(color=self.accent), on_click=self._on_send,
        )
        self.stop_btn = ft.IconButton(
            icon=ft.Icons.STOP_CIRCLE_OUTLINED, icon_size=20,
            style=ft.ButtonStyle(color=DANGER), on_click=self._on_stop, visible=False,
        )

        # Session name (editable)
        self._session_name_field = ft.TextField(
            value="",
            hint_text="Session name",
            text_size=16,
            border=ft.InputBorder.NONE, bgcolor="transparent",
            color=self.text_p,
            text_style=ft.TextStyle(weight=ft.FontWeight.BOLD),
            on_submit=self._on_session_name_change,
            on_blur=self._on_session_name_change,
            dense=True,
        )

        # File picker & drop zone
        self._file_picker = ft.FilePicker()
        self._drop_instance = drag_drop_zone(is_dark=is_dark)
        self.drop_zone = self._drop_instance["zone"]

        self._attach_chips = ft.Row(spacing=4, wrap=True)
        self._attachment_bar = ft.Container(
            content=ft.Column([
                ft.Divider(height=1, color=self.border),
                ft.Row([
                    self._attach_chips,
                    ft.Container(expand=1),
                    ft.TextButton("Clear", on_click=self._on_clear_attachments, style=ft.ButtonStyle(color=self.text_m)),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]),
            visible=False, padding=padding_only(top=4, bottom=2),
        )

        # Keyboard handler
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

    def _section_header(self, title: str, icon):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=14, color=self.accent),
                ft.Text(title, size=11, weight=ft.FontWeight.W_600, color=self.text_p, expand=1),
            ], spacing=4),
            padding=padding_symmetric(horizontal=8, vertical=6),
        )

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

    # ---- Eager processing ----
    def _on_drop_files_changed(self, paths):
        self._attach_chips.controls.clear()
        for p in paths:
            fname = p.split("\\")[-1]
            self._attach_chips.controls.append(_file_attachment_chip(fname, self.is_dark))
            ext = _get_ext(fname)
            if ext in _IMAGE_EXTS:
                card = image_preview_card(p, self.is_dark, "pending")
                self._attach_chips.controls.append(card)
                asyncio.create_task(self._eager_process_image(p, card))
            else:
                asyncio.create_task(self._eager_read_file(p))
        self._attachment_bar.visible = bool(paths)
        self._attachment_bar.update()

    async def _eager_process_image(self, path: str, card: ft.Container):
        try:
            from PIL import Image
            from core.vlm_handler import VLMHandler, parse_vlm_output
            img = Image.open(path)
            vlm = VLMHandler(providers=self.agent.providers)
            def _update_card(s, icon, color):
                card.content = ft.Row([
                    ft.Icon(icon, size=12, color=color),
                    ft.Text(s, size=9, color=DARK_TEXT_SECONDARY if self.is_dark else LIGHT_TEXT_SECONDARY),
                ], spacing=4)
                try: card.update()
                except RuntimeError: pass
            _update_card("Extracting...", ft.Icons.HOURGLASS_TOP, WARNING)
            await asyncio.sleep(0.3)
            text = await asyncio.to_thread(vlm.extract_text, img)
            self._eager_vlm_results[path] = text
            self._eager_vlm_parsed[path] = parse_vlm_output(text)
            parsed = self._eager_vlm_parsed[path]
            label = parsed.get("type", "Unknown")
            if parsed.get("summary"):
                label += f" - {parsed['summary'][:60]}"
            _update_card(f"VLM: {label}", ft.Icons.CHECK_CIRCLE, SUCCESS)
        except Exception as exc:
            logger.warning("Eager VLM failed: %s", exc)
            self._eager_vlm_results[path] = ""
            self._eager_vlm_parsed[path] = {}

    async def _eager_read_file(self, path: str):
        try:
            content = await asyncio.to_thread(lambda: open(path, encoding="utf-8", errors="replace").read())
            self._eager_file_contents[path] = content
        except Exception:
            self._eager_file_contents[path] = ""

    # ---- Session name ----
    def _on_session_name_change(self, e):
        name = self._session_name_field.value.strip()
        if name and self._session:
            self._session.session_name = name
            self._session.save()

    # ---- Input ----
    def _on_input_change(self, e):
        text = e.control.value or ""
        rtl = is_rtl_text(text)
        self.error_input.text_align = ft.TextAlign.RIGHT if rtl else ft.TextAlign.LEFT
        tokens = self._estimate_tokens(text)
        pct = tokens / 4000
        color = TOKEN_LOW if pct < 0.7 else (TOKEN_MED if pct < 0.9 else TOKEN_HIGH)
        self._token_label.value = f"~{tokens} tok"
        self._token_label.color = color
        self._token_label.update()

    def _on_stop(self, e):
        self._stop_requested = True

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text) * 0.35) + 1

    # ---- Steps sidebar ----
    def _rebuild_steps_sidebar(self):
        """Rebuild the steps sidebar with animated step cards showing active state."""
        self._steps_section.controls.clear()
        all_types = ["warmup", "image", "think", "retrieve", "tool", "code", "generate", "error", "wait", "done"]
        completed_types = {e.type for e in self._current_events}
        # Determine the "active" step: the last step that's not the final generate yet
        active_step = None
        for e in self._current_events:
            if e.type in all_types:
                active_step = e.type if not e.metadata.get("partial", False) else e.type
        # Mark all completed steps as done, the most recent unique type as active
        seen = set()
        for e in self._current_events:
            if e.type not in seen and e.type in all_types:
                seen.add(e.type)
                is_active = (e.type == active_step and not all(
                    x.type == "generate" and not x.metadata.get("partial", True)
                    for x in self._current_events
                )) if active_step else False
                sv = step_view(e.type, e.content, e.metadata, self.is_dark,
                               active=False, completed=True)
                self._steps_section.controls.append(sv)

        if not self._current_events:
            # Show pending state for common steps
            for st in ["warmup", "think", "retrieve", "tool", "generate"]:
                s = STEP_STYLE.get(st, {})
                sv = step_view(st, "Waiting...", None, self.is_dark, active=False, completed=False)
                self._steps_section.controls.append(sv)
        try:
            self._steps_section.update()
        except RuntimeError:
            pass

    # ---- Changes / Sources ----
    def _switch_changes_tab(self, index: int):
        self._changes_tab_index = index
        self._changes_tab_0.bgcolor = self.accent_sub if index == 0 else "transparent"
        self._changes_tab_1.bgcolor = self.accent_sub if index == 1 else "transparent"
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
                            ft.Icon(ft.Icons.CODE_OFF, size=20, color=self.text_m),
                            ft.Text("No file changes", size=10, color=self.text_m),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                        padding=20,
                    )
                )
        else:
            if self.sources_panel.controls:
                self._changes_panel.controls.append(self.sources_panel)
            else:
                self._changes_panel.controls.append(
                    ft.Container(ft.Text("No sources", size=10, color=self.text_m), padding=20)
                )
        try:
            self._changes_panel.update()
        except RuntimeError:
            pass

    def _add_sidebar_file(self, file_path: str):
        if file_path in self._sidebar_files:
            return
        self._sidebar_files.append(file_path)

    # ---- Chat bubbles ----
    def _add_bubble(self, text, is_user=False, is_markdown=False, timestamp="", attachments=None, steps=None):
        b = chat_bubble(text, is_user=is_user, is_markdown=is_markdown, is_dark=self.is_dark, timestamp=timestamp, attachments=attachments, steps=steps)
        if self._has_welcome:
            self.chat_log.controls.clear()
            self._has_welcome = False
        self.chat_log.controls.append(ft.Container(content=b, margin=ft.Margin(left=0, top=0, right=0, bottom=4)))
        try:
            self.chat_log.update()
        except RuntimeError:
            pass

    def _show_sources(self, docs, web_results=None):
        self.sources_panel.controls.clear()
        self.sources_panel.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ARTICLE_OUTLINED, size=12, color=self.accent),
                        ft.Text("Sources", size=11, weight=ft.FontWeight.BOLD, color=self.text_p),
                    ], spacing=4),
                ], spacing=2),
                padding=padding_only(bottom=4),
            )
        )
        if web_results:
            for r in web_results[:3]:
                self.sources_panel.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(r.get("source", "")[:60], size=9, weight=ft.FontWeight.W_500, color=self.accent),
                            ft.Text(r.get("content", "")[:60] + "...", size=8, color=self.text_s),
                        ], spacing=1),
                        padding=8, border_radius=4, bgcolor=self.accent_sub,
                    )
                )
        if docs:
            for d in docs:
                score = d.get("score", 0)
                badge_color = ft.Colors.GREEN_400 if score >= 0.7 else (ft.Colors.AMBER_400 if score >= 0.4 else ft.Colors.GREY_400)
                badge_txt = "High" if score >= 0.7 else ("Med" if score >= 0.4 else "Low")
                card = surface_container(
                    ft.Column([
                        ft.Row([
                            ft.Text(d.get("source", "kb"), size=9, weight=ft.FontWeight.W_500, color=self.accent, expand=1),
                            ft.Container(
                                content=ft.Text(badge_txt, size=7, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                padding=padding_only(left=4, top=1, right=4, bottom=1), border_radius=3, bgcolor=badge_color,
                            ),
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text(d.get("content", "")[:60] + "...", size=8, color=self.text_s),
                    ], spacing=2),
                    width=180, padding=6, is_dark=self.is_dark,
                )
                self.sources_panel.controls.append(card)
        try:
            self.sources_panel.update()
        except RuntimeError:
            pass
        self._refresh_changes_panel()

    # ---- Core message processing ----
    async def _process_message_task(self, text: str, images: list[str], files: list[str]):
        self._processing = True
        self._stop_requested = False
        self._current_events = []
        self._update_status("processing")
        self._sidebar_files.clear()
        self._diff_cards.clear()

        # VLM switching: if user has images mid-conversation, process with VLM first
        vlm_context = ""
        vlm_parsed_all = {}
        if images:
            from PIL import Image
            from core.vlm_handler import VLMHandler, parse_vlm_output
            vlm = VLMHandler(providers=self.agent.providers)
            for img_path in images:
                try:
                    img = Image.open(img_path)
                    extracted = self._eager_vlm_results.get(img_path)
                    if not extracted:
                        extracted = await asyncio.to_thread(vlm.extract_text, img)
                    if extracted:
                        vlm_context += f"\n[Image: {img_path.split(chr(92))[-1]}]\nExtracted text: {extracted}\n"
                    parsed = self._eager_vlm_parsed.get(img_path)
                    if not parsed and extracted:
                        parsed = parse_vlm_output(extracted)
                    if parsed:
                        vlm_parsed_all[img_path] = parsed
                except Exception as exc:
                    vlm_context += f"\n[Image: {img_path.split(chr(92))[-1]}]\nFailed to extract: {exc}\n"

        # Build full query with VLM context
        full_query = text
        if vlm_context:
            attachments_steps = [step_view("image", f"VLM extracted ({len(vlm_context)} chars)", is_dark=self.is_dark, completed=True)]
        else:
            attachments_steps = []

        # Attachment chips for user bubble
        attach_chips = []
        for img in images:
            attach_chips.append(_file_attachment_chip(img.split("\\")[-1], self.is_dark))
        for f in files:
            attach_chips.append(_file_attachment_chip(f.split("\\")[-1], self.is_dark))

        self._add_bubble(full_query or "Analyze attachments", is_user=True, attachments=attach_chips or None)
        self.page.update()

        if self._session:
            content = full_query or ""
            if images:
                content += "\n[Images: " + ", ".join(i.split("\\")[-1] for i in images) + "]"
            if files:
                content += "\n[Files: " + ", ".join(f.split("\\")[-1] for f in files) + "]"
            self._session.add_message(role="user", content=content)

        history_list = [{"role": m.role, "content": m.content} for m in (self._session.messages if self._session else [])]

        # Build assistant container
        steps_col = ft.Column(spacing=4)
        typing_ind = typing_indicator(self.is_dark)
        md = ft.Markdown(
            value="", extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
            code_theme="monokai-sublime" if self.is_dark else "github",
            selectable=True,
        )
        bubble_container = ft.Container(
            content=ft.Column([md], spacing=4),
            padding=padding_symmetric(horizontal=14, vertical=10),
            bgcolor=self.bg_surface,
            border_radius=ft.BorderRadius(top_left=4, top_right=16, bottom_left=16, bottom_right=16),
            border=border_all(0.5, self.border),
            visible=False,
        )
        assistant_col = ft.Column([steps_col, typing_ind, bubble_container], spacing=6)
        row_wrapper = ft.Container(content=assistant_col, margin=ft.Margin(left=26, top=0, right=0, bottom=0))

        if self._has_welcome:
            self.chat_log.controls.clear()
            self._has_welcome = False
        self.chat_log.controls.append(row_wrapper)
        self.page.update()

        # Warmup step
        ws = step_view("warmup", "Initializing agents...", is_dark=self.is_dark, active=True)
        steps_col.controls.append(ws)
        steps_col.update()
        self._current_events.append(StepEvent("warmup", "Initializing agents..."))
        self._rebuild_steps_sidebar()

        # Add VLM step if applicable
        if vlm_context:
            vs = step_view("image", f"VLM extracted ({len(vlm_context)} chars)", is_dark=self.is_dark, completed=True)
            steps_col.controls.append(vs)
            steps_col.update()
            self._current_events.append(StepEvent("image", f"VLM extracted ({len(vlm_context)} chars)"))
            self._rebuild_steps_sidebar()

        # Build context dict
        ctx = {"images": images, "files": files, "file_contents": self._eager_file_contents,
               "vlm_text": vlm_context}

        # Run agent pipeline with timeout
        SOLVE_TIMEOUT = 300
        try:
            event_stream, state = await asyncio.wait_for(
                asyncio.to_thread(
                    self.agent.solve, full_query or "Analyze attachments", True, history_list, ctx
                ),
                timeout=SOLVE_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self._add_bubble("**Pipeline timed out** — the agents took too long to respond. Try a simpler query or check Ollama.", is_user=False, is_markdown=True)
            self._processing = False
            self.send_btn.visible = True
            self.stop_btn.visible = False
            self._update_status("ready")
            self._cleanup_resources()
            try:
                self.send_btn.update()
                self.stop_btn.update()
            except RuntimeError:
                pass
            return
        self._current_arm = state.arm_selected
        self.last_state = state

        full_text = ""
        seen_types = set()
        _last_partial_time = time.time()

        for event in event_stream:
            if self._stop_requested:
                break
            self._current_events.append(event)
            if event.type in ("think", "retrieve", "tool", "warmup", "wait"):
                sv = step_view(event.type, event.content, event.metadata, is_dark=self.is_dark, completed=True)
                if event.type not in seen_types:
                    seen_types.add(event.type)
                    steps_col.controls.append(sv)
                    steps_col.update()
                    self._rebuild_steps_sidebar()
            elif event.type == "code":
                sv = step_view("code", event.content, event.metadata, is_dark=self.is_dark, completed=True)
                steps_col.controls.append(sv)
                steps_col.update()
            elif event.type == "error":
                sv = step_view("error", event.content, event.metadata, is_dark=self.is_dark, completed=True)
                steps_col.controls.append(sv)
                steps_col.update()
                bubble_container.visible = True
                md.value = event.content
                md.update()
                bubble_container.update()
            elif event.type == "generate":
                if "generate" not in seen_types:
                    seen_types.add("generate")
                    gv = step_view("generate", "Generating solution...", event.metadata, is_dark=self.is_dark, active=True)
                    steps_col.controls.append(gv)
                    steps_col.update()
                    self._rebuild_steps_sidebar()
                if typing_ind in assistant_col.controls:
                    assistant_col.controls.remove(typing_ind)
                    assistant_col.update()
                bubble_container.visible = True
                bubble_container.update()
                if event.metadata.get("partial"):
                    full_text += event.content
                    md.value = full_text
                    md.update()
                    _last_partial_time = time.time()
                else:
                    # Heartbeat: if no partial content for >30s, show a keep-alive
                    elapsed = time.time() - _last_partial_time
                    if elapsed > 30 and steps_col.controls:
                        heartbeat_msg = f"Still generating... ({int(elapsed)}s)"
                        gv = step_view("generate", heartbeat_msg, event.metadata, is_dark=self.is_dark, active=True)
                        steps_col.controls[-1] = gv
                        steps_col.update()
                        self._rebuild_steps_sidebar()

        if full_text:
            md.value = full_text
            md.update()
        if typing_ind in assistant_col.controls:
            assistant_col.controls.remove(typing_ind)
            assistant_col.update()

        # Mark generate as done
        if full_text:
            gs = step_view("done", "Solution generated", is_dark=self.is_dark, completed=True)
            steps_col.controls.append(gs)
            steps_col.update()
            self._rebuild_steps_sidebar()

        # Show code analysis if available
        agent_results = getattr(state, 'agent_results', {})
        code_agent_data = agent_results.get("code_agent", {}).get("output", {}).get("data", {})
        bug_reports = code_agent_data.get("bug_reports", [])
        if bug_reports:
            ca_view = code_analysis_view(bug_reports, is_dark=self.is_dark)
            row_wrapper.content.controls.append(ca_view)
            try:
                row_wrapper.update()
            except RuntimeError:
                pass

        # Show VLM analysis details
        if vlm_parsed_all:
            from app.components.step_view import image_analysis_card
            combined = {"images": images, "analyses": vlm_parsed_all}
            ia_card = image_analysis_card(combined, is_dark=self.is_dark)
            row_wrapper.content.controls.append(ia_card)
            try:
                row_wrapper.update()
            except RuntimeError:
                pass

        self._show_sources(state.retrieved_docs, web_results=state.web_results)

        parsed = parse_diffs_from_text(full_text)
        for d in parsed:
            card = diff_view(d["file_path"], d["lines"], d["add_count"], d["del_count"], is_dark=self.is_dark)
            self._diff_cards.append(card)
            self._add_sidebar_file(d["file_path"])
        self._refresh_changes_panel()

        # Save with steps
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

    def _cleanup_resources(self):
        import gc
        try:
            if hasattr(self, 'agent') and self.agent:
                self.agent.cleanup()
        except Exception:
            pass
        try:
            from core.database import close as close_db
            close_db()
        except Exception:
            pass
        try:
            from core.cache import close_cache
            import asyncio
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(close_cache())
            except RuntimeError:
                pass
        except Exception:
            pass
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
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
        self._eager_vlm_results.clear()
        self._eager_vlm_parsed.clear()
        self._eager_file_contents.clear()
        self._process_message(text, images, code_files)

    def _handle_mcp_command(self, cmd: str, files: list[str]):
        parts = cmd.split(maxsplit=2)
        command = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if command == "/help":
            help_text = "\n".join(f"  {k}  - {v}" for k, v in _MCP_COMMANDS.items())
            self._add_bubble(f"**MCP Commands:**\n{help_text}", is_user=False, is_markdown=True)
        elif command == "/write":
            self._add_bubble(f"**Usage:** /write filename.py", is_user=False, is_markdown=True)
        elif command == "/search":
            query = args or "Search attached files"
            self._process_message(query, [], files)
        elif command in ("/kb", "/search_kb"):
            if args:
                asyncio.create_task(self._handle_kb_search(args))
            else:
                self._add_bubble("**Usage:** /kb your search query", is_user=False, is_markdown=True)
        else:
            self._add_bubble(f"Unknown: {command}. Type /help.", is_user=False, is_markdown=True)

    async def _handle_kb_search(self, query: str):
        self._add_bubble(f"**🔍 KB Search:** _{query}_", is_user=False, is_markdown=True)
        self.page.update()

        docs = []
        rag = None
        try:
            rag = RAGPipeline(providers=self.agent.providers)
            if rag.ok:
                _, docs = await asyncio.to_thread(rag.retrieve_context, query, 10)
        except Exception as exc:
            logger.warning("KB search (ChromaDB) failed: %s", exc)

        # Fallback to SQLite if ChromaDB failed or empty
        if not docs:
            try:
                from core.database import kb_search
                sql_results = await asyncio.to_thread(kb_search, query, 10)
                for r in sql_results:
                    docs.append({
                        "content": r.get("solution_text", ""),
                        "source": r.get("source", "kb_sqlite"),
                        "score": 0.5,
                    })
            except Exception as exc:
                logger.warning("KB search (SQLite fallback) also failed: %s", exc)

        if rag:
            try:
                rag.close()
            except Exception:
                pass

        if not docs:
            self._add_bubble("**No results found** in the knowledge base. Try a different query or seed the KB:\n```\npython scripts/seed_kb.py\n```", is_user=False, is_markdown=True)
            return

        results_col = ft.Column(spacing=6)
        for i, doc in enumerate(docs):
            score = doc.get("score", 0)
            score_pct = int(score * 100)
            color = ft.Colors.GREEN_400 if score >= 0.7 else (ft.Colors.AMBER_400 if score >= 0.4 else ft.Colors.GREY_400)
            badge = "High" if score >= 0.7 else ("Med" if score >= 0.4 else "Low")

            content_short = doc.get("content", "")[:200] + ("..." if len(doc.get("content", "")) > 200 else "")
            source = doc.get("source", "kb")

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"#{i+1}  {source}", size=10, weight=ft.FontWeight.W_600, color=self.accent, expand=1),
                        ft.Container(
                            content=ft.Text(f"{badge} {score_pct}%", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                            padding=padding_only(left=4, top=2, right=4, bottom=2),
                            border_radius=4, bgcolor=color,
                        ),
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Container(height=2),
                    ft.Text(content_short, size=10, color=self.text_s),
                    ft.Row([
                        ft.TextButton(
                            "Show solution",
                            style=ft.ButtonStyle(color=self.accent, text_style=ft.TextStyle(size=10)),
                            on_click=lambda _, d=doc: self._show_kb_solution(d),
                        ),
                        ft.TextButton(
                            "Apply fix",
                            style=ft.ButtonStyle(color=ft.Colors.GREEN_400, text_style=ft.TextStyle(size=10)),
                            on_click=lambda _, d=doc: self._apply_kb_fix(d),
                        ),
                    ], spacing=4),
                ], spacing=2),
                padding=10,
                border_radius=6,
                bgcolor=self.accent_sub,
                border=border_all(0.5, self.border),
            )
            results_col.controls.append(card)

        result_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.LIBRARY_BOOKS, size=14, color=self.accent),
                    ft.Text(f"Knowledge Base ({len(docs)} results)", size=11, weight=ft.FontWeight.W_600, color=self.text_p),
                    ft.Container(expand=1),
                    ft.Text(f"Query: {query[:40]}{'...' if len(query) > 40 else ''}", size=9, color=self.text_m),
                ], spacing=4),
                ft.Divider(height=1, color=self.border),
                results_col,
            ], spacing=6),
            padding=10,
            border_radius=8,
            bgcolor=self.bg_surface,
            border=border_all(0.5, self.border),
            margin=ft.Margin(left=26, top=4, right=0, bottom=4),
        )
        self.chat_log.controls.append(result_container)
        try:
            self.chat_log.update()
        except RuntimeError:
            pass

    def _show_kb_solution(self, doc: dict):
        content_full = doc.get("content", "No content")
        source = doc.get("source", "kb")
        score = doc.get("score", 0)
        md_text = f"**Solution from KB** ({source}, relevance: {int(score * 100)}%)\n\n---\n\n{content_full}"
        self._add_bubble(md_text, is_user=False, is_markdown=True)

    def _apply_kb_fix(self, doc: dict):
        content_full = doc.get("content", "")
        self._add_bubble(f"**Applying KB fix...**\n\n```\n{content_full[:500]}\n```\n\nReview the fix above. If it looks correct, use `/write <file>` to apply.", is_user=False, is_markdown=True)

    def load_session(self, session):
        self._cleanup_resources()
        self._session = session
        self.chat_log.controls.clear()
        self.sources_panel.controls.clear()
        self._steps_section.controls.clear()
        self._sidebar_files.clear()
        self._diff_cards.clear()
        self._has_welcome = False
        self._current_events = []

        # Set session name
        self._session_name_field.value = session.session_name or "Debug Session"
        try:
            self._session_name_field.update()
        except RuntimeError:
            pass

        source = session.context.get("source_file", "") or ""
        if source:
            self._add_bubble(f"Opened file", is_user=True, attachments=[_file_attachment_chip(source.split("\\")[-1], self.is_dark)])
        for msg in session.messages:
            is_user = msg.role == "user"
            steps = []
            if hasattr(msg, "steps") and msg.steps:
                for s in msg.steps:
                    sv = step_view(s.type, s.content, s.metadata, self.is_dark, completed=True)
                    steps.append(sv)
            self._add_bubble(msg.content, is_user=is_user, is_markdown=not is_user, timestamp=msg.timestamp, steps=steps or None)
        self.page.update()

    def _update_status(self, mode="idle", arm=None):
        if self._status_bar:
            self._status_bar.set_mode(mode, arm)

    def _on_clear_attachments(self, e):
        self._drop_instance["clear"]()
        self._eager_vlm_results.clear()
        self._eager_vlm_parsed.clear()
        self._eager_file_contents.clear()

    # ---- Overlay session config ----
    def show_session_config(self, on_config_done):
        """Show the session configuration dialog (used on new session)."""
        overlay = ft.Container(
            content=session_config_form(
                self.is_dark,
                on_submit=lambda cfg: self._on_config_submit(cfg, on_config_done, overlay),
                on_cancel=lambda: self._close_overlay(overlay),
            ),
            alignment=ft.alignment.center,
            expand=1,
        )
        self.page.overlay.append(overlay)
        self.page.update()
        return overlay

    def _on_config_submit(self, cfg, on_config_done, overlay):
        self._session_cfg = cfg
        self._close_overlay(overlay)
        on_config_done(cfg)

    def _close_overlay(self, overlay):
        if overlay in self.page.overlay:
            self.page.overlay.remove(overlay)
            self.page.update()

    # ---- Build ----
    def build(self):
        # Session header
        session_id_str = f"  #{self._session.id[:6]}" if self._session else ""
        session_header = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.BUG_REPORT, size=18, color=self.accent),
                self._session_name_field,
                ft.Text(session_id_str, size=10, color=self.text_m, visible=bool(self._session)),
                ft.Container(expand=1),
                ft.IconButton(
                    icon=ft.Icons.EDIT, icon_size=14, tooltip="Rename session",
                    style=ft.ButtonStyle(color=self.text_m),
                    on_click=lambda _: self._session_name_field.focus(),
                ),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=padding_symmetric(horizontal=8, vertical=6),
            border=border_all(0.5, self.border),
            border_radius=8,
            bgcolor=self.bg_surface,
        )

        # Input row
        input_row = ft.Container(
            content=ft.Column([
                self._attachment_bar,
                ft.Container(
                    content=ft.Row([
                        self.error_input, self._token_bar, self.attach_btn, self.send_btn, self.stop_btn,
                    ], vertical_alignment=ft.CrossAxisAlignment.END, spacing=4),
                    padding=padding_symmetric(horizontal=6, vertical=4),
                    border_radius=8,
                    bgcolor=self.bg_surface,
                    border=border_all(1, self.border),
                ),
            ]),
            padding=padding_only(top=4, bottom=2),
        )

        # Chat area
        chat_area = ft.Column([
            session_header,
            ft.Container(height=4),
            ft.Container(content=self.chat_log, expand=1, padding=padding_symmetric(horizontal=4)),
        ], expand=2, spacing=0)

        # Welcome message
        if not self.chat_log.controls and not self._has_welcome:
            self._has_welcome = True
            welcome_content = ft.Column([
                ft.Icon(ft.Icons.CHAT_OUTLINED, size=32, color=self.text_m),
                ft.Container(height=4),
                ft.Text("Ready to Debug", size=15, weight=ft.FontWeight.W_600, color=self.text_p),
                ft.Text("Drop a screenshot, attach a file, or type a message", size=10, color=self.text_s),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.IMAGE, size=12, color=self.accent),
                            ft.Text("Image", size=9, color=self.accent),
                        ], spacing=4),
                        padding=padding_symmetric(horizontal=8, vertical=4),
                        border_radius=4, bgcolor=self.accent_sub,
                    ),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CODE, size=12, color=self.accent2),
                            ft.Text("Code", size=9, color=self.accent2),
                        ], spacing=4),
                        padding=padding_symmetric(horizontal=8, vertical=4),
                        border_radius=4, bgcolor=self.accent_sub,
                    ),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SEARCH, size=12, color=INFO),
                            ft.Text("Search", size=9, color=INFO),
                        ], spacing=4),
                        padding=padding_symmetric(horizontal=8, vertical=4),
                        border_radius=4, bgcolor=self.accent_sub,
                    ),
                ], spacing=6),
                ft.Container(height=8),
                ft.Text("Ctrl+Enter to send  •  /help for commands", size=9, color=self.text_m),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2)
            self.chat_log.controls.append(ft.Container(content=welcome_content, expand=1))

        # Content layout
        content_row = ft.Row([
            self._sidebar_container if self._sidebar_visible else ft.Container(width=3),
            ft.VerticalDivider(width=1, color=self.border) if self._sidebar_visible else ft.Container(width=0),
            chat_area,
            ft.VerticalDivider(width=1, color=self.border) if self._changes_visible else ft.Container(width=0),
            ft.Column([
                self._changes_header,
                ft.Divider(height=1, color=self.border),
                self._changes_panel,
            ], expand=1, spacing=2) if self._changes_visible else ft.Container(width=3),
        ], expand=1, spacing=0, vertical_alignment=ft.CrossAxisAlignment.START)

        return ft.Container(
            content=ft.Column([
                content_row,
                input_row,
            ], spacing=0),
            padding=padding_symmetric(horizontal=12, vertical=6),
            expand=1,
        )
