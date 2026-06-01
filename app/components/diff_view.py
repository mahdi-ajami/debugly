import re
import flet as ft

from app.theme import (
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    DARK_ACCENT, LIGHT_ACCENT,
    SUCCESS, DANGER,
    border_all, padding_symmetric, padding_only,
)

DIFF_ADD_BG_DARK = "rgba(34,197,94,0.12)"
DIFF_ADD_BG_LIGHT = "rgba(34,197,94,0.08)"
DIFF_DEL_BG_DARK = "rgba(239,68,68,0.12)"
DIFF_DEL_BG_LIGHT = "rgba(239,68,68,0.08)"


def parse_diffs_from_text(text: str) -> list[dict]:
    diffs = []
    pattern = re.compile(r'```(\w+)?(?::([^\n]+))?\n(.*?)```', re.DOTALL)
    for m in pattern.finditer(text):
        lang = m.group(1) or ""
        file_path = m.group(2) or ""
        code = m.group(3)
        has_add = "+" in code[:50]
        has_del = "-" in code[:50]
        if file_path and (has_add or has_del):
            lines = code.split("\n")
            parsed = []
            for line in lines:
                if line.startswith("+++") or line.startswith("---"):
                    parsed.append({"type": "header", "content": line})
                elif line.startswith("@@"):
                    parsed.append({"type": "header", "content": line})
                elif line.startswith("+"):
                    parsed.append({"type": "add", "content": line[1:]})
                elif line.startswith("-"):
                    parsed.append({"type": "del", "content": line[1:]})
                else:
                    parsed.append({"type": "ctx", "content": line})
            add_count = sum(1 for l in parsed if l["type"] == "add")
            del_count = sum(1 for l in parsed if l["type"] == "del")
            diffs.append({
                "file_path": file_path,
                "lang": lang,
                "lines": parsed,
                "add_count": add_count,
                "del_count": del_count,
            })
        elif file_path and not has_add and not has_del:
            diffs.append({
                "file_path": file_path,
                "lang": lang,
                "lines": [{"type": "ctx", "content": code}],
                "add_count": 0,
                "del_count": 0,
            })
    return diffs


def _diff_line_widget(dl: dict, is_dark: bool):
    dt = dl["type"]
    content = dl["content"]
    muted = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    sec = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    add_bg = DIFF_ADD_BG_DARK if is_dark else DIFF_ADD_BG_LIGHT
    del_bg = DIFF_DEL_BG_DARK if is_dark else DIFF_DEL_BG_LIGHT

    if dt == "add":
        return ft.Container(
            content=ft.Row([
                ft.Text("+", size=11, color=SUCCESS, width=14),
                ft.Text(content, size=11, color=SUCCESS, selectable=True),
            ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=add_bg,
            padding=padding_only(left=2, top=1, right=2, bottom=1),
        )
    elif dt == "del":
        return ft.Container(
            content=ft.Row([
                ft.Text("-", size=11, color=DANGER, width=14),
                ft.Text(content, size=11, color=DANGER, selectable=True),
            ], spacing=0, vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor=del_bg,
            padding=padding_only(left=2, top=1, right=2, bottom=1),
        )
    else:
        return ft.Container(
            content=ft.Row([
                ft.Text(" ", size=11, color=muted, width=14),
                ft.Text(content, size=11, color=muted if dt == "header" else sec, selectable=True),
            ], spacing=0),
            padding=padding_only(left=2, top=1, right=2, bottom=1),
        )


def diff_view(file_path: str, diff_lines: list[dict], add_count: int, del_count: int, is_dark: bool = False) -> ft.Container:
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    border = DARK_BORDER if is_dark else LIGHT_BORDER
    muted = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED

    add_badge = ft.Container(
        content=ft.Text(f"+{add_count}", size=9, weight=ft.FontWeight.W_600, color=SUCCESS),
        padding=padding_symmetric(horizontal=4, vertical=1),
        border_radius=3,
    ) if add_count > 0 else ft.Container()

    del_badge = ft.Container(
        content=ft.Text(f"-{del_count}", size=9, weight=ft.FontWeight.W_600, color=DANGER),
        padding=padding_symmetric(horizontal=4, vertical=1),
        border_radius=3,
    ) if del_count > 0 else ft.Container()

    body_rows = [_diff_line_widget(dl, is_dark) for dl in diff_lines]
    expanded = ft.Ref[ft.Column]()

    def toggle_expand(e):
        expanded.current.visible = not expanded.current.visible
        expanded.current.update()

    return ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.DESCRIPTION, size=14, color=accent),
                    ft.Text(file_path, size=11, weight=ft.FontWeight.W_600, color=accent, expand=1),
                    add_badge,
                    del_badge,
                    ft.Icon(ft.Icons.EXPAND_MORE, size=14, color=muted),
                ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=padding_symmetric(horizontal=8, vertical=5),
                border_radius=ft.BorderRadius(top_left=6, top_right=6, bottom_left=0, bottom_right=0),
                on_click=toggle_expand,
            ),
            ft.Column(body_rows, spacing=0, ref=expanded, visible=True),
        ], spacing=0),
        border=border_all(0.5, border),
        border_radius=6,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )
