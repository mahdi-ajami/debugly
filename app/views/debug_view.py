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
from app.components.feedback_bar import FeedbackBar
from app.components.step_view import typing_indicator, step_view


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
        self.feedback_bar = FeedbackBar(
            on_thumbs_up=lambda: self._handle_feedback(1),
            on_thumbs_down=lambda: self._handle_feedback(0),
        )

        self._token_label = ft.Text("0 tok", size=10, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED)
        self._token_bar = ft.Container(
            content=self._token_label,
            padding=padding_symmetric(horizontal=6),
        )

        self.error_input = ft.TextField(
            hint_text="Or type an error message manually...",
            expand=1,
            multiline=True,
            min_lines=1,
            max_lines=5,
            text_size=14,
            border_radius=8,
            border=border_all(1, DARK_BORDER if is_dark else LIGHT_BORDER),
            bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
            on_change=self._on_input_change,
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
            tooltip="Send (Enter)",
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

        self._drop_instance = drag_drop_zone(is_dark=is_dark)
        self.drop_zone = self._drop_instance["zone"]

        self._attach_chips = ft.Row(spacing=4, wrap=True)
        self._analyze_btn = ft.ElevatedButton(
            "Analyze Files",
            icon=ft.Icons.SEARCH,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=self.accent,
                shape=ft.RoundedRectangleBorder(radius=6),
                padding=padding_symmetric(horizontal=12, vertical=5),
            ),
            on_click=self._on_analyze_files,
        )
        self._clear_attach_btn = ft.TextButton("Clear", on_click=self._on_clear_attachments)
        self._attachment_bar = ft.Container(
            content=ft.Column([
                ft.Divider(height=1, color=DARK_BORDER if is_dark else LIGHT_BORDER),
                ft.Row([
                    self._attach_chips,
                    ft.Container(expand=1),
                    self._analyze_btn,
                    self._clear_attach_btn,
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ]),
            visible=False,
            padding=padding_only(top=4, bottom=2),
        )

        self._drop_instance["set_on_change"](self._on_drop_files_changed)
        self._drop_instance["set_on_tap"](self._on_drop_zone_tap)
        try:
            self._switch_changes_tab(0)
        except RuntimeError:
            pass

    async def _on_drop_zone_tap(self):
        fp = ft.FilePicker()
        result = await fp.pick_files(
            allow_multiple=True,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "webp", "txt", "py", "js", "ts", "pdf", "md", "json", "yaml", "yml", "log", "csv"],
        )
        if result:
            self._drop_instance["add_paths"]([f.path for f in result])

    def _on_input_change(self, e):
        text = e.control.value or ""
        rtl = is_rtl_text(text)
        self.error_input.text_align = ft.TextAlign.RIGHT if rtl else ft.TextAlign.LEFT
        chars = len(text)
        tokens = self._estimate_tokens(text)
        max_tokens = 4000
        pct = tokens / max_tokens
        if pct < 0.7:
            color = TOKEN_LOW
        elif pct < 0.9:
            color = TOKEN_MED
        else:
            color = TOKEN_HIGH
        self._token_label.value = f"~{tokens} tok   {chars} chr"
        self._token_label.color = color
        self._token_label.update()

    async def _on_attach(self, e):
        fp = ft.FilePicker()
        result = await fp.pick_files(
            allow_multiple=True,
            allowed_extensions=["png", "jpg", "jpeg", "bmp", "webp", "txt", "py", "js", "ts", "pdf", "md", "json", "yaml", "yml", "log", "csv"],
        )
        if result:
            self._drop_instance["add_paths"]([f.path for f in result])

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
        r0 = 6 if index == 0 else 0
        r1 = 6 if index == 1 else 0
        self._changes_tab_0.border_radius = ft.BorderRadius(top_left=r0, top_right=0, bottom_left=r0, bottom_right=0)
        self._changes_tab_1.border_radius = ft.BorderRadius(top_left=0, top_right=r1, bottom_left=0, bottom_right=r1)
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
                    ft.Container(
                        content=ft.Text("No sources loaded", size=11, color=DARK_TEXT_MUTED if self.is_dark else LIGHT_TEXT_MUTED),
                        padding=20,
                    )
                )
        try:
            self._changes_panel.update()
        except RuntimeError:
            pass

    def _add_sidebar_step(self, step_type: str, content: str):
        icon_map = {"think": ft.Icons.PSYCHOLOGY, "retrieve": ft.Icons.SEARCH, "tool": ft.Icons.BUILD}
        icon = icon_map.get(step_type, ft.Icons.CIRCLE)
        label = step_type.capitalize()
        self._sidebar_step_list.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=12, color=DARK_ACCENT if self.is_dark else LIGHT_ACCENT),
                    ft.Text(label, size=10, color=DARK_TEXT_SECONDARY if self.is_dark else LIGHT_TEXT_SECONDARY),
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

    def _add_bubble(self, text, is_user=False, is_markdown=False, timestamp="", attachments=None):
        b = chat_bubble(text, is_user=is_user, is_markdown=is_markdown, is_dark=self.is_dark, timestamp=timestamp, attachments=attachments)
        if self._has_welcome:
            self.chat_log.controls.clear()
            self._has_welcome = False
        self.chat_log.controls.append(b)
        try:
            self.chat_log.update()
        except RuntimeError:
            pass

    def _show_sources(self, docs: list[dict], web_results: list[dict] | None = None):
        self.sources_panel.controls.clear()
        accent_subtle = DARK_ACCENT_SUBTLE if self.is_dark else LIGHT_ACCENT_SUBTLE
        self.sources_panel.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ARTICLE_OUTLINED, size=14, color=self.accent),
                        ft.Text("Sources", size=12, weight=ft.FontWeight.BOLD, color=self.text_p),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text("Knowledge base & web references used for this answer.", size=9, color=self.text_s),
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
                            ft.Text(r.get("site_label", ""), size=8, color=self.text_s, italic=True),
                        ], spacing=1),
                        padding=10, border_radius=4,
                        bgcolor=accent_subtle,
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
                if score >= 0.7:
                    badge_txt = "High"
                    badge_color = ft.Colors.GREEN_400
                elif score >= 0.4:
                    badge_txt = "Med"
                    badge_color = ft.Colors.AMBER_400
                else:
                    badge_txt = "Low"
                    badge_color = ft.Colors.GREY_400
                card = surface_container(
                    ft.Column([
                        ft.Row([
                            ft.Text(d.get("source", "kb"), size=10, weight=ft.FontWeight.W_500, color=self.accent, expand=1),
                            ft.Container(
                                content=ft.Text(badge_txt, size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                padding=padding_only(left=5, top=2, right=5, bottom=2),
                                border_radius=4,
                                bgcolor=badge_color,
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

    def _handle_screenshot(self, path: str):
        if self._processing:
            return
        self._processing = True
        self._update_status("processing")
        fname = path.split("\\")[-1]
        self._add_bubble(f"Screenshot: {fname}", is_user=True)
        self._add_bubble("Extracting error text from image...")
        self.page.update()

        try:
            error_text = self.agent.extract_error(path)
            self._add_bubble(f"**Extracted Error:**\n{error_text}", is_user=True, is_markdown=True)
            self.page.update()
            if self._session:
                self._session.add_message(role="user", content=f"Screenshot: {fname}\n\nExtracted Error: {error_text}")
            self._run_inference(error_text, history=self._session.messages if self._session else [])
        except Exception as ex:
            self._add_bubble(f"Extraction failed: {ex}")
        finally:
            self._processing = False
            self.page.update()

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
            self._add_bubble(f"File: `{source}`", is_user=True)

        for msg in session.messages:
            is_user = msg.role == "user"
            self._add_bubble(msg.content, is_user=is_user, is_markdown=not is_user, timestamp=msg.timestamp)
        self.page.update()

    def _on_send(self, e):
        if self._processing:
            return
        text = self.error_input.value.strip()
        drop_files = list(self._drop_instance["selected_paths"])
        if not text and not drop_files:
            return

        if drop_files:
            self._drop_instance["clear"]()
            for p in drop_files:
                self._handle_screenshot(p)
            return

        self._processing = True
        self.send_btn.visible = False
        self.stop_btn.visible = True
        self.send_btn.update()
        self.stop_btn.update()

        self.error_input.value = ""
        self.error_input.update()
        self._token_label.value = "0 tok"
        self._token_label.update()
        self._add_bubble(text, is_user=True)
        self.page.update()
        if self._session:
            self._session.add_message(role="user", content=text)
        self._run_inference(text, history=self._session.messages if self._session else [])

    def _update_status(self, mode="idle", arm=None):
        if self._status_bar:
            self._status_bar.set_mode(mode, arm)

    def _run_inference(self, error_text: str, history: list | None = None):
        self._stop_requested = False
        self._update_status("processing")

        self._sidebar_step_list.controls.clear()
        self._sidebar_file_list.controls.clear()
        self._sidebar_files.clear()
        self._diff_cards.clear()
        try:
            if self._session:
                self.agent._current_session_id = self._session.id
            history_list = [{"role": m.role, "content": m.content} for m in (history or [])]
            event_stream, state = self.agent.solve(error_text, stream=True, history=history_list)
            self._current_arm = state.arm_selected
            self.last_state = state

            steps_col = ft.Column(spacing=0)
            placeholder = ft.Text("", selectable=True, size=14, color=self.text_p)
            bubble = ft.Container(
                content=placeholder,
                padding=padding_symmetric(horizontal=14, vertical=10),
                bgcolor=DARK_BG_SURFACE if self.is_dark else LIGHT_BG_SURFACE,
                border_radius=ft.BorderRadius(top_left=16, top_right=16, bottom_left=16, bottom_right=16),
                border=border_all(0.5, DARK_BORDER if self.is_dark else LIGHT_BORDER),
                width=540,
            )

            typing_ind = typing_indicator(self.is_dark)
            assistant_row = ft.Column([
                steps_col,
                typing_ind,
                ft.Row([bubble], alignment=ft.MainAxisAlignment.START),
            ], spacing=4)
            self.chat_log.controls.append(assistant_row)
            self.page.update()

            full_text = ""
            for event in event_stream:
                if self._stop_requested:
                    break
                if event.type in ("think", "retrieve", "tool"):
                    sv = step_view(event.type, event.content, event.metadata, is_dark=self.is_dark)
                    steps_col.controls.append(sv)
                    steps_col.update()
                    self._add_sidebar_step(event.type, event.content)
                elif event.type == "error":
                    placeholder.value = event.content
                    placeholder.color = ft.Colors.RED_400 if self.is_dark else ft.Colors.RED_700
                    placeholder.update()
                elif event.type == "generate":
                    if typing_ind in assistant_row.controls:
                        assistant_row.controls.remove(typing_ind)
                    if event.metadata.get("partial"):
                        full_text += event.content
                        placeholder.value = full_text
                        placeholder.update()

            if full_text:
                placeholder.value = full_text
                placeholder.update()
            self.feedback_bar.visible = True
            self.feedback_bar.update()
            self._show_sources(state.retrieved_docs, web_results=state.web_results)

            parsed = parse_diffs_from_text(full_text)
            for d in parsed:
                card = diff_view(d["file_path"], d["lines"], d["add_count"], d["del_count"], is_dark=self.is_dark)
                self._diff_cards.append(card)
                self._add_sidebar_file(d["file_path"])
            self._refresh_changes_panel()

            if self._session and full_text:
                self._session.add_message(role="assistant", content=full_text, steps=[])
                self._session.save()
            arm_name = ["Conservative", "Balanced", "Creative"][self._current_arm] if self._current_arm is not None else None
            self._update_status("ready", arm_name)
        except Exception as ex:
            self._add_bubble(f"Error generating solution: {ex}")
            self._update_status("error")
        finally:
            self._processing = False
            self.send_btn.visible = True
            self.stop_btn.visible = False
            self.send_btn.update()
            self.stop_btn.update()

    def _handle_feedback(self, rating: int):
        if self._current_arm is not None:
            self.agent.handle_feedback(self._current_arm, rating)
        self.feedback_bar.visible = False
        self.feedback_bar.update()
        try:
            self.page.show_dialog(
                ft.SnackBar(
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=18),
                        ft.Text("Thanks for your feedback!", size=13),
                    ]),
                    open=True,
                    duration=2000,
                    bgcolor=DARK_BG_SURFACE if self.is_dark else LIGHT_BG_SURFACE,
                )
            )
        except Exception:
            pass

    def _on_drop_files_changed(self, paths):
        self._attach_chips.controls.clear()
        for p in paths:
            fname = p.split("\\")[-1]
            ext = fname.split(".")[-1].lower() if "." in fname else ""
            icon_map = {
                "py": ft.Icons.CODE, "js": ft.Icons.JAVASCRIPT, "ts": ft.Icons.DATA_OBJECT,
                "txt": ft.Icons.DESCRIPTION, "pdf": ft.Icons.PICTURE_AS_PDF,
                "png": ft.Icons.IMAGE, "jpg": ft.Icons.IMAGE, "jpeg": ft.Icons.IMAGE,
                "webp": ft.Icons.IMAGE, "bmp": ft.Icons.IMAGE,
            }
            icon = icon_map.get(ext, ft.Icons.ATTACH_FILE)
            self._attach_chips.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(icon, size=14, color=self.accent),
                        ft.Text(fname, size=10, color=self.accent),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=padding_only(left=6, top=3, right=6, bottom=3),
                    border_radius=4,
                    bgcolor=DARK_ACCENT_SUBTLE if self.is_dark else LIGHT_ACCENT_SUBTLE,
                )
            )
        self._attachment_bar.visible = bool(paths)
        self._attachment_bar.update()

    def _on_analyze_files(self, e):
        paths = list(self._drop_instance["selected_paths"])
        self._drop_instance["clear"]()
        for p in paths:
            self._handle_screenshot(p)

    def _on_clear_attachments(self, e):
        self._drop_instance["clear"]()

    def build(self):
        input_row = ft.Container(
            content=ft.Column([
                self._attachment_bar,
                ft.Row(
                    [self.error_input, self._token_bar, self.attach_btn, self.send_btn, self.stop_btn],
                    vertical_alignment=ft.CrossAxisAlignment.END,
                    spacing=4,
                ),
            ]),
            padding=padding_only(top=6, bottom=2),
        )

        session_id = self._session.id[:8] if self._session else ""
        header_row = ft.Row([
            ft.Column([
                ft.Text("Debug Session", size=18, weight=ft.FontWeight.BOLD, color=self.text_p),
                ft.Text(f"Session: {session_id}" if session_id else "Start a new debug session",
                        size=10, color=self.text_s),
            ]),
            ft.Container(expand=1),
            ft.ElevatedButton(
                "New Chat",
                icon=ft.Icons.ADD,
                style=ft.ButtonStyle(
                    color=ft.Colors.WHITE,
                    bgcolor=self.accent,
                    padding=padding_symmetric(horizontal=12, vertical=5),
                    shape=ft.RoundedRectangleBorder(radius=6),
                ),
                on_click=lambda _: self.on_new_session() if self.on_new_session else None,
            ),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        self.feedback_bar.visible = False
        chat_area = ft.Column([self.chat_log, self.feedback_bar], expand=2, spacing=2)
        if not self.chat_log.controls and not self._has_welcome:
            self._has_welcome = True
            self.chat_log.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CHAT_OUTLINED, size=36, color=self.text_s),
                        ft.Container(height=6),
                        ft.Text("Ready to Debug", size=16, weight=ft.FontWeight.W_600, color=self.text_p),
                        ft.Text("Drop a screenshot or type an error message below", size=11, color=self.text_s),
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
