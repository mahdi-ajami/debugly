import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DANGER, SUCCESS, WARNING, INFO,
    border_all, padding_symmetric,
)

STEP_ICONS = {
    "think": ft.Icons.PSYCHOLOGY,
    "retrieve": ft.Icons.SEARCH,
    "tool": ft.Icons.BUILD,
    "generate": ft.Icons.AUTO_FIX_HIGH,
}

STEP_LABELS = {
    "think": "Thinking",
    "retrieve": "Searching KB",
    "tool": "Using tool",
    "generate": "Generating",
}

STEP_COLORS = {
    "think": "#A78BFA",
    "retrieve": "#60A5FA",
    "tool": "#F59E0B",
    "generate": "#34D399",
}


def typing_indicator(is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    dots = ft.Row([
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent,
                     animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT)),
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent,
                     animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT)),
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent,
                     animate=ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT)),
    ], spacing=4)
    return ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=14, color=accent),
            dots,
        ], spacing=6),
        padding=padding_symmetric(horizontal=14, vertical=10),
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border_radius=16,
        border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
        margin=ft.Margin(left=40, top=2, right=0, bottom=2),
    )


def step_view(step_type: str, content: str, metadata: dict | None = None, is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED

    icon = STEP_ICONS.get(step_type, ft.Icons.CIRCLE)
    label = STEP_LABELS.get(step_type, step_type)
    color = STEP_COLORS.get(step_type, accent)

    is_partial = (metadata or {}).get("partial", False)
    is_error = step_type == "error"
    if is_error:
        color = DANGER
        label = "Error"
        icon = ft.Icons.ERROR_OUTLINE

    display = content
    if len(display) > 120 and not is_partial:
        display = display[:117] + "..."

    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icon, size=14, color=color),
                width=24, height=24,
                border_radius=12,
                bgcolor=color + "20",
            ),
            ft.Column([
                ft.Row([
                    ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=color),
                    ft.Container(
                        content=ft.ProgressRing(width=10, height=10, stroke_width=1.5, color=color),
                        visible=is_partial,
                    ),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(display, size=11, color=text_s if not is_partial else text_m),
            ], spacing=1, expand=1),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START),
        padding=padding_symmetric(horizontal=10, vertical=6),
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border_radius=6,
        border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
        margin=ft.Margin(left=24, top=2, right=0, bottom=2),
    )
