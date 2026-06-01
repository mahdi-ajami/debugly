import flet as ft

from core.agent import DebugAgent
from app.components.chat_bubble import chat_bubble
from app.components.feedback_bar import FeedbackBar
from app.components.solution_card import solution_card
from core.config import UI_TITLE, UI_THEME_COLOR


class MainView:
    def __init__(self):
        self.agent = DebugAgent()
        self.last_state = None
        self._current_arm = None

    def build(self, page: ft.Page):
        page.title = UI_TITLE
        page.window.width = 1100
        page.window.height = 750
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(color_scheme_seed=UI_THEME_COLOR)
        page.padding = 20

        chat_log = ft.ListView(expand=1, spacing=10, padding=10, auto_scroll=True)

        error_input = ft.TextField(
            hint_text="Or type an error message manually...",
            expand=1,
            multiline=True,
            min_lines=1,
            max_lines=3,
        )

        feedback_bar = FeedbackBar(
            on_thumbs_up=lambda: self._handle_feedback(1),
            on_thumbs_down=lambda: self._handle_feedback(0),
        )

        side_panel = ft.Column([], scroll=ft.ScrollMode.AUTO, width=300)

        def on_upload(e: ft.FilePickerResultEvent):
            if not e.files:
                return
            path = e.files[0].path
            chat_log.controls.append(
                ft.Row([chat_bubble(f"📸 Screenshot uploaded: {e.files[0].name}", is_user=True)],
                       alignment=ft.MainAxisAlignment.END)
            )
            page.update()
            chat_log.controls.append(
                ft.Row([chat_bubble("⏳ Extracting error text...")],
                       alignment=ft.MainAxisAlignment.START)
            )
            page.update()

            try:
                error_text = self.agent.extract_error(path)
                chat_log.controls.append(
                    ft.Row([chat_bubble(f"**Extracted Error:**\n{error_text}", is_user=True)],
                           alignment=ft.MainAxisAlignment.END)
                )
                page.update()
                _run_inference(error_text)
            except Exception as ex:
                chat_log.controls.append(
                    ft.Row([chat_bubble(f"❌ Extraction failed: {ex}")],
                           alignment=ft.MainAxisAlignment.START)
                )
                page.update()

        file_picker = ft.FilePicker(on_result=on_upload)
        page.overlay.append(file_picker)

        def on_send(e):
            text = error_input.value.strip()
            if not text:
                return
            error_input.value = ""
            chat_log.controls.append(
                ft.Row([chat_bubble(text, is_user=True)],
                       alignment=ft.MainAxisAlignment.END)
            )
            page.update()
            _run_inference(text)

        def _run_inference(error_text: str):
            stream_gen, state = self.agent.solve(error_text, stream=True)
            self._current_arm = state.arm_selected
            self.last_state = state

            solution_bubble = ft.Container(
                content=ft.Column([ft.Text("💡 Thinking...")]),
                padding=12,
                bgcolor=ft.Colors.GREY_100,
                border_radius=20,
                width=500,
            )
            chat_log.controls.append(ft.Row([solution_bubble], alignment=ft.MainAxisAlignment.START))
            page.update()

            full_text = ""
            placeholder = solution_bubble.content.controls[0]
            for chunk in stream_gen:
                full_text += chunk
                placeholder.value = full_text
                page.update()

            placeholder.value = full_text
            feedback_bar.visible = True
            side_panel.controls.clear()
            side_panel.controls.append(
                solution_card("Retrieved Sources", state.retrieved_docs)
            )
            page.update()

        def _handle_feedback(rating: int):
            if self._current_arm is not None:
                self.agent.handle_feedback(self._current_arm, rating)
            feedback_bar.visible = False
            page.snack_bar = ft.SnackBar(ft.Text("Thanks for your feedback!"), open=True)
            page.update()

        upload_btn = ft.ElevatedButton(
            "📤 Upload Screenshot",
            icon=ft.Icons.UPLOAD_FILE,
            on_click=lambda _: file_picker.pick_files(
                allow_multiple=False,
                allowed_extensions=["png", "jpg", "jpeg", "bmp"],
            ),
        )

        send_btn = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_size=28,
            tooltip="Send",
            on_click=on_send,
        )

        page.add(
            ft.Row([
                ft.Column([
                    ft.Text(UI_TITLE, size=28, weight=ft.FontWeight.BOLD),
                    ft.Text("Upload an error screenshot or type an error message", size=13,
                            color=ft.Colors.GREY_600),
                    ft.Divider(height=12),
                    ft.Row([upload_btn], alignment=ft.MainAxisAlignment.START),
                    ft.Divider(height=8),
                    ft.Row([error_input, send_btn], vertical_alignment=ft.CrossAxisAlignment.END),
                    ft.Divider(height=8),
                    chat_log,
                    feedback_bar,
                ], expand=1),
                ft.VerticalDivider(width=1),
                side_panel,
            ], expand=1, vertical_alignment=ft.CrossAxisAlignment.START)
        )
