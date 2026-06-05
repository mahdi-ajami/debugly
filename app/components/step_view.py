import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_ACCENT_SECONDARY, LIGHT_ACCENT_SECONDARY,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DANGER, SUCCESS, WARNING, INFO,
    border_all, padding_symmetric,
)

STEP_STYLE = {
    "think":    {"icon": ft.Icons.PSYCHOLOGY,      "label": "Thinking",    "color": "#A78BFA"},
    "retrieve": {"icon": ft.Icons.SEARCH,           "label": "Retrieving",  "color": "#60A5FA"},
    "tool":     {"icon": ft.Icons.BUILD,            "label": "Tool Call",   "color": "#F59E0B"},
    "generate": {"icon": ft.Icons.AUTO_FIX_HIGH,    "label": "Generating",  "color": "#34D399"},
    "error":    {"icon": ft.Icons.ERROR_OUTLINE,     "label": "Error",      "color": "#EF4444"},
    "image":    {"icon": ft.Icons.IMAGE,             "label": "Vision",     "color": "#EC4899"},
    "wait":     {"icon": ft.Icons.HOURGLASS_EMPTY,   "label": "Waiting",    "color": "#F59E0B"},
    "warmup":   {"icon": ft.Icons.LOCAL_FIRE_DEPARTMENT, "label": "Starting","color": "#F97316"},
    "done":     {"icon": ft.Icons.CHECK_CIRCLE,      "label": "Complete",   "color": "#22C55E"},
    "code":     {"icon": ft.Icons.CODE,              "label": "Code",       "color": "#38BDF8"},
}

STEP_ORDER = ["warmup", "image", "think", "retrieve", "tool", "code", "generate", "error", "done", "wait"]


def step_view(step_type: str, content: str, metadata: dict | None = None, is_dark: bool = False, active: bool = False, completed: bool = False):
    style = STEP_STYLE.get(step_type, {"icon": ft.Icons.CIRCLE, "label": step_type, "color": DARK_ACCENT if is_dark else LIGHT_ACCENT})
    icon = style["icon"]
    label = style["label"]
    color = style["color"]
    is_partial = (metadata or {}).get("partial", False)

    display = content[:120] + "..." if len(content) > 120 and not is_partial else content

    if completed:
        state_icon = ft.Icons.CHECK_CIRCLE_OUTLINED
        state_color = SUCCESS
        status_text = "Done"
    elif active:
        state_icon = ft.Icons.RADIO_BUTTON_CHECKED
        state_color = color
        status_text = "In progress..."
    else:
        state_icon = ft.Icons.RADIO_BUTTON_UNCHECKED
        state_color = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
        status_text = ""

    header = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icon, size=14, color=color),
                animate_opacity=300 if active else 0,
            ),
            ft.Text(label, size=10, weight=ft.FontWeight.W_600, color=color),
            ft.Container(
                content=ft.ProgressRing(width=10, height=10, stroke_width=1.5, color=color),
                visible=active,
            ),
            ft.Container(expand=1),
            ft.Container(
                content=ft.Row([
                    ft.Text(status_text, size=9, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED, visible=bool(status_text)),
                    ft.Icon(state_icon, size=12, color=state_color),
                ], spacing=4),
            ),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        padding=padding_symmetric(horizontal=8, vertical=4),
        border_radius=ft.BorderRadius(top_left=4, top_right=4, bottom_left=0, bottom_right=0),
    )

    body = ft.Container(
        content=ft.Column([
            ft.Text(display, size=11, color=DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY),
        ], spacing=2),
        padding=padding_symmetric(horizontal=8, vertical=4),
        border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=4, bottom_right=4),
        visible=bool(content) and (active or completed),
    )

    border_color = color + "60" if active else (SUCCESS + "60" if completed else color + "30")
    return ft.Container(
        content=ft.Column([header, body], spacing=0),
        border=border_all(0.5, border_color),
        border_radius=5,
        bgcolor=color + "08" if active else DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        margin=ft.Margin(left=0, top=3, right=0, bottom=0),
        animate_opacity=300,
        animate_margin=300,
    )


def typing_indicator(is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    dots = ft.Row([
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent, animate_opacity=500),
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent, animate_opacity=500),
        ft.Container(width=6, height=6, border_radius=3, bgcolor=accent, animate_opacity=500),
    ], spacing=4)
    return ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.SMART_TOY_OUTLINED, size=14, color=accent),
            dots,
            ft.Text("Generating...", size=10, color=DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED),
        ], spacing=6),
        padding=padding_symmetric(horizontal=14, vertical=8),
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border_radius=16,
        border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
        margin=ft.Margin(left=26, top=2, right=0, bottom=2),
    )


def image_preview_card(path: str, is_dark: bool = False, status: str = "pending"):
    fname = path.split("\\")[-1]
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    accent_sub = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE

    if status == "done":
        status_text = "VLM done"
        status_icon = ft.Icons.CHECK_CIRCLE
        status_color = SUCCESS
    elif status == "processing":
        status_text = "Extracting..."
        status_icon = ft.Icons.HOURGLASS_TOP
        status_color = WARNING
    else:
        status_text = "Queued..."
        status_icon = ft.Icons.HOURGLASS_EMPTY
        status_color = text_m

    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Image(src=path, width=64, height=48, fit=ft.BoxFit.COVER, border_radius=6),
            ),
            ft.Column([
                ft.Text(fname, size=11, weight=ft.FontWeight.W_500, color=text_p),
                ft.Row([
                    ft.Icon(status_icon, size=12, color=status_color),
                    ft.Text(status_text, size=9, color=status_color),
                ], spacing=4),
            ], spacing=2, expand=1, alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=8),
        padding=padding_symmetric(horizontal=10, vertical=6),
        border_radius=8,
        bgcolor=accent_sub,
        border=border_all(1, accent + "30"),
    )


def image_analysis_card(data: dict, is_dark: bool = False):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    accent_sub = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    images_list = data.get("images", []) if isinstance(data, dict) else data
    analyses = data.get("analyses", {}) if isinstance(data, dict) else {}

    if not images_list and not analyses:
        return ft.Container()

    analysis_cards = []
    for img_path in images_list:
        fname = img_path.split("\\")[-1]
        vlm = analyses.get(img_path, {})
        summary = (vlm.get("summary") or "").strip()
        extracted = (vlm.get("extracted") or "").strip()
        err_type = vlm.get("type", "Unknown")
        language = vlm.get("language", "Unknown")
        severity = vlm.get("severity", "Medium")
        context_type = vlm.get("context", "Other")

        sev_color = {"Critical": "#EF4444", "High": "#F59E0B", "Medium": "#60A5FA", "Low": "#9CA3AF"}.get(severity, "#9CA3AF")
        type_color = DANGER if err_type not in ("Unknown",) else accent

        badges = ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=9, color=ft.Colors.WHITE),
                    ft.Text(err_type, size=7, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ], spacing=2),
                padding=padding_symmetric(horizontal=5, vertical=2), border_radius=3, bgcolor=type_color,
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CODE, size=9, color=ft.Colors.WHITE),
                    ft.Text(language, size=7, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ], spacing=2),
                padding=padding_symmetric(horizontal=5, vertical=2), border_radius=3, bgcolor=accent,
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SPEED, size=9, color=ft.Colors.WHITE),
                    ft.Text(severity, size=7, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ], spacing=2),
                padding=padding_symmetric(horizontal=5, vertical=2), border_radius=3, bgcolor=sev_color,
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.DEVICES, size=9, color=ft.Colors.WHITE),
                    ft.Text(context_type, size=7, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ], spacing=2),
                padding=padding_symmetric(horizontal=5, vertical=2), border_radius=3,
                bgcolor=DARK_ACCENT_SECONDARY if is_dark else LIGHT_ACCENT_SECONDARY,
            ),
        ], spacing=3, wrap=True)

        extracted_preview = ft.Container(
            content=ft.Text(extracted[:200] + ("..." if len(extracted) > 200 else ""),
                            size=9, color=text_s, font_family="monospace"),
            padding=padding_symmetric(horizontal=6, vertical=4),
            border_radius=4, bgcolor=accent_sub,
            visible=bool(extracted),
        )

        card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Image(src=img_path, width=64, height=48, fit=ft.BoxFit.COVER, border_radius=6),
                    ft.Column([
                        ft.Text(fname, size=10, weight=ft.FontWeight.W_500, color=text_p),
                        badges,
                    ], spacing=2, expand=1),
                ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START),
                extracted_preview,
                ft.Container(
                    content=ft.Text(summary or "No summary", size=9, color=text_s),
                    visible=bool(summary),
                ),
            ], spacing=4),
            padding=8,
            border_radius=6,
            bgcolor=accent_sub,
            border=border_all(0.5, border),
        )
        analysis_cards.append(card)

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.IMAGE_SEARCH, size=14, color=accent),
                ft.Text("Screenshot Analysis", size=11, weight=ft.FontWeight.W_600, color=text_p, expand=1),
                ft.Text(f"{len(images_list)} image{'s' if len(images_list) != 1 else ''}", size=9, color=text_m),
            ], spacing=4),
            ft.Column(analysis_cards, spacing=6),
        ], spacing=4),
        padding=10,
        border_radius=8,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border=border_all(0.5, border),
        margin=ft.Margin(left=26, top=4, right=0, bottom=4),
    )

