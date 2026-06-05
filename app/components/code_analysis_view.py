import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DANGER, SUCCESS, WARNING, INFO,
    border_all, padding_symmetric, padding_only,
)


def _issue_badge(severity: str):
    color = DANGER if severity == "error" else (WARNING if severity == "warning" else INFO)
    label = severity.upper()
    return ft.Container(
        content=ft.Text(label, size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        padding=padding_only(left=4, top=1, right=4, bottom=1),
        border_radius=3, bgcolor=color,
    )


def code_analysis_view(bug_reports: list[dict], is_dark: bool = False):
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_sub = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    bg_surface = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    if not bug_reports:
        return ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=SUCCESS),
                ft.Text("No issues detected in files", size=10, color=text_s),
            ], spacing=4),
            padding=8, border_radius=6, bgcolor=accent_sub,
            margin=ft.Margin(left=0, top=2, right=0, bottom=2),
        )

    file_cards = []
    total_issues = sum(len(br["issues"]) for br in bug_reports)
    for br in bug_reports:
        fname = br["file"]
        issues = br["issues"]
        err_count = sum(1 for i in issues if i["severity"] == "error")
        warn_count = sum(1 for i in issues if i["severity"] == "warning")

        issue_rows = []
        for iss in issues:
            code_line = iss.get("code", "").strip()
            line_num = iss.get("line", 0)
            issue_rows.append(
                ft.Container(
                    content=ft.Row([
                        _issue_badge(iss.get("severity", "info")),
                        ft.Text(f"Line {line_num}: ", size=9, weight=ft.FontWeight.W_500, color=text_p),
                        ft.Text(iss["message"], size=9, color=text_s, expand=1),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=padding_symmetric(horizontal=6, vertical=3),
                    border_radius=4,
                    bgcolor=DANGER + "10" if iss.get("severity") == "error" else (WARNING + "10" if iss.get("severity") == "warning" else INFO + "10"),
                    margin=ft.Margin(left=0, top=1, right=0, bottom=1),
                )
            )
            if code_line:
                issue_rows.append(
                    ft.Container(
                        content=ft.Text(code_line[:150], size=9, color=text_s, font_family="monospace"),
                        padding=padding_only(left=20, bottom=2),
                    )
                )

        file_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=12, color=accent),
                    ft.Text(fname, size=10, weight=ft.FontWeight.W_600, color=text_p, expand=1),
                    ft.Container(
                        content=ft.Text(f"⚠ {err_count} err  ⚡ {warn_count} warn", size=8, color=text_s),
                        padding=padding_symmetric(horizontal=4, vertical=1),
                    ),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Column(issue_rows, spacing=1),
            ], spacing=2),
            padding=8, border_radius=6,
            bgcolor=accent_sub,
            margin=ft.Margin(left=0, top=2, right=0, bottom=2),
        )
        file_cards.append(file_card)

    header = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.BUG_REPORT, size=14, color=DANGER if total_issues > 0 else accent),
            ft.Text(f"Code Analysis ({total_issues} issue{'s' if total_issues != 1 else ''})",
                    size=10, weight=ft.FontWeight.W_600, color=text_p),
        ], spacing=4),
        padding=padding_only(bottom=2),
    )

    return ft.Container(
        content=ft.Column([header] + file_cards, spacing=2),
        padding=8, border_radius=8,
        bgcolor=bg_surface,
        border=border_all(0.5, border),
        margin=ft.Margin(left=26, top=4, right=0, bottom=4),
    )
