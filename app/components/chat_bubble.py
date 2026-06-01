import flet as ft


def chat_bubble(text: str, is_user: bool = False) -> ft.Container:
    align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
    bg = ft.Colors.BLUE_100 if is_user else ft.Colors.GREY_100
    border_radius = ft.border_only(
        top_left=20 if not is_user else 5,
        top_right=20 if is_user else 5,
        bottom_left=20,
        bottom_right=20,
    )
    return ft.Container(
        content=ft.Column([
            ft.Text(text, selectable=True, size=14),
        ]),
        padding=12,
        bgcolor=bg,
        border_radius=border_radius,
        width=500,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )
