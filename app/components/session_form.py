import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DANGER, SUCCESS,
    border_all, padding_symmetric,
)

SKILL_OPTIONS = [
    {"key": "debugging", "label": "Debugging", "icon": ft.Icons.BUG_REPORT, "desc": "Find and fix code errors"},
    {"key": "code_review", "label": "Code Review", "icon": ft.Icons.RATE_REVIEW, "desc": "Review code quality"},
    {"key": "architecture", "label": "Architecture", "icon": ft.Icons.ACCOUNT_TREE, "desc": "Design system architecture"},
    {"key": "security", "label": "Security", "icon": ft.Icons.SECURITY, "desc": "Security audit and analysis"},
    {"key": "performance", "label": "Performance", "icon": ft.Icons.SPEED, "desc": "Optimize performance"},
    {"key": "testing", "label": "Testing", "icon": ft.Icons.SCIENCE, "desc": "Write and fix tests"},
]

ROLE_OPTIONS = [
    {"key": "developer", "label": "Developer", "desc": "Focus on implementation"},
    {"key": "architect", "label": "Architect", "desc": "Focus on system design"},
    {"key": "reviewer", "label": "Code Reviewer", "desc": "Focus on code quality"},
    {"key": "devops", "label": "DevOps", "desc": "Focus on deployment/CI-CD"},
    {"key": "fullstack", "label": "Full Stack", "desc": "Both frontend and backend"},
]

PROMPT_STYLES = [
    {"key": "concise", "label": "Concise", "desc": "Short direct answers"},
    {"key": "detailed", "label": "Detailed", "desc": "Step-by-step with code"},
    {"key": "educational", "label": "Educational", "desc": "Explain concepts thoroughly"},
    {"key": "creative", "label": "Creative", "desc": "Creative problem solving"},
]

DEFAULT_SESSION_CFG = {
    "name": "",
    "skills": ["debugging"],
    "role": "developer",
    "prompt_style": "detailed",
}


def session_config_form(is_dark: bool, on_submit, on_cancel):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    bg_surface = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE
    border = DARK_BORDER if is_dark else LIGHT_BORDER
    accent_sub = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE

    name_field = ft.TextField(
        label="Session Name",
        hint_text="e.g. Fix login bug",
        value="",
        expand=1,
        text_size=14,
        border_radius=8,
        border=border_all(1, border),
        bgcolor=bg_surface,
    )

    skill_toggles = []
    skills_col = ft.Column(spacing=4)
    for sk in SKILL_OPTIONS:
        active = sk["key"] == "debugging"
        chip = ft.Container(
            content=ft.Row([
                ft.Icon(sk["icon"], size=16, color=accent if active else text_m),
                ft.Text(sk["label"], size=12, weight=ft.FontWeight.W_500,
                        color=text_p if active else text_m),
            ], spacing=4),
            padding=padding_symmetric(horizontal=10, vertical=6),
            border_radius=6,
            bgcolor=accent_sub if active else bg_surface,
            border=border_all(1, accent + "40" if active else border),
            ink=True,
        )
        skill_toggles.append({"key": sk["key"], "active": active, "chip": chip})
        chip.on_click = lambda _, k=sk["key"]: _toggle_skill(k)
        skills_col.controls.append(chip)

    def _toggle_skill(key):
        for st in skill_toggles:
            if st["key"] == key:
                st["active"] = not st["active"]
                a = st["active"]
                st["chip"].bgcolor = accent_sub if a else bg_surface
                st["chip"].border = border_all(1, accent + "40" if a else border)
                st["chip"].content.controls[0].color = accent if a else text_m
                st["chip"].content.controls[1].color = text_p if a else text_m
                st["chip"].update()

    role_dd = ft.Dropdown(
        label="Role",
        value="developer",
        options=[ft.dropdown.Option(r["key"], r["label"]) for r in ROLE_OPTIONS],
        expand=1,
        text_size=13,
        border_radius=8,
        border=border_all(1, border),
        bgcolor=bg_surface,
    )

    prompt_dd = ft.Dropdown(
        label="Response Style",
        value="detailed",
        options=[ft.dropdown.Option(p["key"], p["label"]) for p in PROMPT_STYLES],
        expand=1,
        text_size=13,
        border_radius=8,
        border=border_all(1, border),
        bgcolor=bg_surface,
    )

    error_text = ft.Text("", size=11, color=DANGER, visible=False)

    def _submit(e):
        name = name_field.value.strip()
        if not name:
            error_text.value = "Please enter a session name"
            error_text.visible = True
            error_text.update()
            return
        active_skills = [st["key"] for st in skill_toggles if st["active"]]
        cfg = {
            "name": name,
            "skills": active_skills,
            "role": role_dd.value or "developer",
            "prompt_style": prompt_dd.value or "detailed",
        }
        on_submit(cfg)

    submit_btn = ft.FilledButton(
        "Start Session",
        icon=ft.Icons.PLAY_ARROW,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=accent,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=padding_symmetric(horizontal=20, vertical=12),
        ),
        on_click=_submit,
    )

    cancel_btn = ft.TextButton("Cancel", on_click=lambda _: on_cancel())

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.TUNE, size=20, color=accent),
                ft.Text("New Session Config", size=16, weight=ft.FontWeight.BOLD, color=text_p),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text("Configure how this session should behave", size=11, color=text_s),
            ft.Divider(height=1, color=border),
            name_field,
            error_text,
            ft.Text("Skills", size=12, weight=ft.FontWeight.W_600, color=text_p),
            ft.Text("Select the capabilities for this session", size=10, color=text_s),
            skills_col,
            ft.Row([role_dd, prompt_dd], spacing=10),
            ft.Divider(height=1, color=border),
            ft.Row([cancel_btn, submit_btn], alignment=ft.MainAxisAlignment.END, spacing=8),
        ], spacing=8, scroll=ft.ScrollMode.AUTO),
        padding=padding_symmetric(horizontal=20, vertical=16),
        border_radius=12,
        bgcolor=bg_surface,
        border=border_all(1, border),
        width=460,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=20, color="rgba(0,0,0,0.3)", offset=ft.Offset(0, 4)),
    )
