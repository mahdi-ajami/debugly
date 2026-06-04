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

STEP_STYLE = {
    "think":    {"icon": ft.Icons.PSYCHOLOGY,      "label": "Think",    "color": "#A78BFA"},
    "retrieve": {"icon": ft.Icons.SEARCH,           "label": "Retrieve", "color": "#60A5FA"},
    "tool":     {"icon": ft.Icons.BUILD,            "label": "Tool",     "color": "#F59E0B"},
    "generate": {"icon": ft.Icons.AUTO_FIX_HIGH,    "label": "Generate", "color": "#34D399"},
    "error":    {"icon": ft.Icons.ERROR_OUTLINE,    "label": "Error",    "color": "#EF4444"},
    "image":    {"icon": ft.Icons.IMAGE,            "label": "Image",    "color": "#EC4899"},
    "wait":     {"icon": ft.Icons.HOURGLASS_EMPTY,  "label": "Wait",     "color": "#F59E0B"},
    "warmup":   {"icon": ft.Icons.LOCAL_FIRE_DEPARTMENT, "label": "Warmup", "color": "#F97316"},
}


def step_view(step_type: str, content: str, metadata: dict | None = None, is_dark: bool = False):
    style = STEP_STYLE.get(step_type, {"icon": ft.Icons.CIRCLE, "label": step_type, "color": DARK_ACCENT if is_dark else LIGHT_ACCENT})
    icon = style["icon"]
    label = style["label"]
    color = style["color"]
    is_partial = (metadata or {}).get("partial", False)

    display = content[:100] + "..." if len(content) > 100 and not is_partial else content

    header = ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=14, color=color),
            ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=color),
            ft.Container(
                content=ft.ProgressRing(width=10, height=10, stroke_width=1.5, color=color),
                visible=is_partial,
            ),
            ft.Container(expand=1),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, size=12, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=padding_symmetric(horizontal=8, vertical=4),
        border_radius=ft.BorderRadius(top_left=4, top_right=4, bottom_left=0, bottom_right=0),
    )

    body = ft.Container(
        content=ft.Text(display, size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY),
        padding=padding_symmetric(horizontal=8, vertical=4),
        border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=4, bottom_right=4),
    )

    return ft.Container(
        content=ft.Column([header, body], spacing=0),
        border=border_all(0.5, color + "40"),
        border_radius=5,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        margin=ft.Margin(left=0, top=4, right=0, bottom=0),
    )


def typing_indicator(is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    dots = ft.Row([
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent),
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent),
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent),
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
        margin=ft.Margin(left=26, top=2, right=0, bottom=2),
    )


def image_preview_card(path: str, is_dark: bool = False):
    fname = path.split("\\")[-1]
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Image(src=path, width=80, height=60, fit=ft.ImageFit.COVER, border_radius=6),
            ),
            ft.Column([
                ft.Text(fname, size=12, weight=ft.FontWeight.W_500, color=DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY),
                ft.Text("Processing...", size=10, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED),
                ft.ProgressBar(width=120, height=3, color=accent, bgcolor=accent_subtle),
            ], spacing=2, expand=1, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=10),
        padding=padding_symmetric(horizontal=12, vertical=8),
        border_radius=8,
        bgcolor=accent_subtle,
        border=border_all(1, accent + "40"),
        animate_opacity=300,
        opacity=0,
    )
