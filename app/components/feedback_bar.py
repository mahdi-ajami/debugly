import flet as ft


class FeedbackBar(ft.Row):
    def __init__(self, on_thumbs_up, on_thumbs_down):
        super().__init__()
        self.visible = False
        self.alignment = ft.MainAxisAlignment.CENTER
        self.spacing = 8
        self.controls = [
            ft.IconButton(
                icon=ft.Icons.THUMB_UP_OUTLINED,
                icon_size=20,
                tooltip="Good solution",
                on_click=lambda _: on_thumbs_up(),
            ),
            ft.Text("Was this helpful?", size=12, color=ft.Colors.GREY_500),
            ft.IconButton(
                icon=ft.Icons.THUMB_DOWN_OUTLINED,
                icon_size=20,
                tooltip="Needs improvement",
                on_click=lambda _: on_thumbs_down(),
            ),
        ]
