import flet as ft


def skeleton_text(lines: int = 3, is_dark: bool = False):
    bg = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.06)"
    items = []
    for i in range(lines):
        w = 180 if i % 2 == 0 else 240
        c = ft.Container(
            width=w,
            height=12,
            bgcolor=bg,
            border_radius=6,
            animate=ft.Animation(800, ft.AnimationCurve.EASE_IN_OUT),
        )
        items.append(c)
    return ft.Column(items, spacing=10)


def skeleton_card(is_dark: bool = False):
    bg = "rgba(255,255,255,0.06)" if is_dark else "rgba(0,0,0,0.04)"
    return ft.Container(
        content=ft.Column([
            ft.Container(width=120, height=14, bgcolor=bg, border_radius=7),
            ft.Container(width=260, height=10, bgcolor=bg, border_radius=5),
            ft.Container(width=200, height=10, bgcolor=bg, border_radius=5),
        ], spacing=8),
        padding=16,
        border_radius=12,
        bgcolor=bg,
    )
