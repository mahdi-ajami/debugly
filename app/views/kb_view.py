import json
import logging
from datetime import datetime
from pathlib import Path

import flet as ft

from app.theme import (
    surface_container,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BORDER, LIGHT_BORDER,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BG_PRIMARY, LIGHT_BG_PRIMARY,
    border_all, padding_symmetric, padding_only,
    DANGER, SUCCESS,
)

logger = logging.getLogger(__name__)

KB_PACKAGE_MAP = {
    "error_solutions": {"label": "Python Errors", "icon": ft.Icons.ERROR_OUTLINE, "file": "error_solutions.json"},
    "curated_python": {"label": "Python Advanced", "icon": ft.Icons.CODE, "file": "curated_python.json"},
    "curated_javascript": {"label": "JS/TS", "icon": ft.Icons.JAVASCRIPT, "file": "curated_javascript.json"},
    "curated_docker": {"label": "Docker", "icon": ft.Icons.ENGINEERING, "file": "curated_docker.json"},
    "curated_git": {"label": "Git", "icon": ft.Icons.SOURCE, "file": "curated_git.json"},
    "curated_web_python": {"label": "Web Python", "icon": ft.Icons.WEB, "file": "curated_web_python.json"},
    "security_guidelines": {"label": "Security", "icon": ft.Icons.SHIELD, "file": "security_guidelines.json"},
}


def _build_manager(providers=None):
    from core.kb_manager import KbManager
    return KbManager(providers=providers)


def kb_view(is_dark: bool = False, page=None, providers=None):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_sub = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    border = DARK_BORDER if is_dark else LIGHT_BORDER
    bg_surface = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE
    bg_primary = DARK_BG_PRIMARY if is_dark else LIGHT_BG_PRIMARY

    kb = None
    stats = {}
    entries = []
    search_results = []
    current_collection = "all"
    entry_list_content = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)

    search_field = ft.TextField(
        hint_text="Search knowledge base...",
        prefix_icon=ft.Icons.SEARCH,
        border_radius=8,
        text_size=13,
        height=40,
        expand=1,
        border=border_all(1, border),
        bgcolor=bg_surface,
    )
    search_results_text = ft.Text("", size=11, color=text_m)
    search_container = ft.Column(spacing=4)

    def _refresh_stats():
        nonlocal stats
        try:
            mgr = _build_manager(providers)
            stats = mgr.get_collection_stats()
            mgr.close()
        except Exception as exc:
            logger.warning("Failed to get KB stats: %s", exc)
            stats = {}

    def _load_entries():
        nonlocal entries
        try:
            mgr = _build_manager(providers)
            entries = mgr.get_entries(current_collection) if current_collection != "all" else []
            mgr.close()
        except Exception as exc:
            logger.warning("Failed to load entries: %s", exc)
            entries = []

    def _build_stats_row():
        _refresh_stats()
        cards = []
        sqlite_count = stats.get("sqlite", {}).get("count", 0)
        total = sqlite_count

        def _stat_card(label, value, icon, color=None):
            return surface_container(
                ft.Column([
                    ft.Row([
                        ft.Icon(icon, size=16, color=color or accent),
                        ft.Text(str(value), size=22, weight=ft.FontWeight.BOLD, color=text_p, expand=1),
                    ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(label, size=10, color=text_m),
                ], spacing=2),
                width=140, height=70, padding=padding_symmetric(horizontal=12, vertical=8), is_dark=is_dark,
            )

        cards.append(_stat_card("Total Entries", total, ft.Icons.LIBRARY_BOOKS))
        collection_names = list(stats.keys())
        for col_name in collection_names:
            if col_name == "sqlite":
                continue
            col_info = stats[col_name]
            color_map = {"error_solutions": DANGER, "security_guidelines": SUCCESS, "code_patterns": ft.Colors.BLUE_400, "best_practices": ft.Colors.AMBER_400}
            c = color_map.get(col_name, accent)
            cards.append(_stat_card(col_info.get("description", col_name), col_info.get("count", 0), ft.Icons.FOLDER_SPECIAL, color=c))

        return ft.Row(cards, wrap=True, spacing=8, run_spacing=8)

    def _build_package_card(pkg_key, pkg_info):
        pkg_stats = stats.get(pkg_info.get("collection", ""), {})
        count = pkg_stats.get("count", 0) if pkg_stats else 0
        description = pkg_stats.get("description", "") if pkg_stats else ""
        return surface_container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(pkg_info["icon"], size=18, color=accent),
                    ft.Container(expand=1),
                    ft.Text(f"{len(_get_pkg_entries(pkg_key))}", size=14, weight=ft.FontWeight.BOLD, color=text_p),
                ], spacing=4),
                ft.Text(pkg_info["label"], size=12, weight=ft.FontWeight.W_500, color=text_p),
                ft.Text(f"{count} indexed · {description[:40]}", size=10, color=text_m),
            ], spacing=2),
            width=180, height=80, padding=padding_symmetric(horizontal=12, vertical=8), is_dark=is_dark,
        )

    def _get_pkg_entries(pkg_key):
        pkg_info = KB_PACKAGE_MAP.get(pkg_key, {})
        file_path = Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "data" / pkg_info.get("file", "")
        if not file_path.exists():
            return []
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _build_packages_section():
        pkgs_row = ft.Row(wrap=True, spacing=8, run_spacing=8)
        for pkg_key, pkg_info in KB_PACKAGE_MAP.items():
            pkgs_row.controls.append(_build_package_card(pkg_key, pkg_info))
        return pkgs_row

    def _build_entry_list():
        nonlocal entry_list_content
        _load_entries()
        items = []
        for e in entries[:50]:
            title = e.get("error_text", "Untitled")[:80]
            solution = e.get("solution_text", "")
            source = e.get("source", "")
            created = e.get("created_at", "")[:10]
            items.append(
                surface_container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(title, size=12, weight=ft.FontWeight.W_600, color=text_p, expand=1),
                            ft.Text(created, size=9, color=text_m),
                            ft.Text(f"[{source[:20]}]", size=9, color=text_m),
                        ], spacing=4),
                        ft.Text(solution[:120] + ("..." if len(solution) > 120 else ""), size=10, color=text_s),
                        ft.Row([
                            ft.TextButton("Edit", style=ft.ButtonStyle(color=accent, text_style=ft.TextStyle(size=10)),
                                          on_click=lambda _, eid=e["id"], et=title, st=solution: _edit_entry(eid, et, st)),
                            ft.TextButton("Delete", style=ft.ButtonStyle(color=DANGER, text_style=ft.TextStyle(size=10)),
                                          on_click=lambda _, eid=e["id"]: _delete_entry(eid)),
                        ], spacing=4),
                    ], spacing=4),
                    padding=padding_symmetric(horizontal=10, vertical=8), is_dark=is_dark,
                )
            )
        entry_list_content.controls = items
        entry_list_content.update()

    def _edit_entry(eid, current_error, current_solution):
        if not page:
            return
        error_f = ft.TextField(label="Error text", value=current_error, multiline=True, min_lines=2, max_lines=4)
        solution_f = ft.TextField(label="Solution text", value=current_solution, multiline=True, min_lines=3, max_lines=6)

        def _save(e):
            try:
                mgr = _build_manager(providers)
                mgr.update_entry(eid, error_f.value, solution_f.value)
                mgr.close()
                page.dialog.open = False
                _build_entry_list()
                page.update()
            except Exception as exc:
                logger.warning("Update entry failed: %s", exc)

        page.dialog = ft.AlertDialog(
            title=ft.Text("Edit KB Entry"),
            content=ft.Column([error_f, solution_f], width=400, spacing=8),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Save", on_click=_save),
            ],
        )
        page.dialog.open = True
        page.update()

    def _delete_entry(eid):
        if not page:
            return
        def _confirm(e):
            try:
                mgr = _build_manager(providers)
                mgr.delete_entry(eid)
                mgr.close()
                page.dialog.open = False
                _build_entry_list()
                page.update()
            except Exception as exc:
                logger.warning("Delete entry failed: %s", exc)

        page.dialog = ft.AlertDialog(
            title=ft.Text("Delete Entry"),
            content=ft.Text("Are you sure you want to delete this entry?"),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Delete", style=ft.ButtonStyle(bgcolor=DANGER, color=ft.Colors.WHITE), on_click=_confirm),
            ],
        )
        page.dialog.open = True
        page.update()

    def _show_add_dialog(e):
        if not page:
            return
        title_f = ft.TextField(label="Title / Error", hint_text="e.g. KeyError in dict access")
        tags_f = ft.TextField(label="Tags", hint_text="comma separated: python, dict")
        steps_f = ft.TextField(label="Solution steps", hint_text="one per line", multiline=True, min_lines=3, max_lines=6)
        code_f = ft.TextField(label="Code example (optional)", multiline=True, min_lines=2, max_lines=5)
        severity_dd = ft.Dropdown(
            label="Severity",
            value="medium",
            options=[ft.dropdown.Option("low"), ft.dropdown.Option("medium"), ft.dropdown.Option("high"), ft.dropdown.Option("critical")],
        )
        lang_f = ft.TextField(label="Languages", hint_text="comma separated: python, javascript")

        def _save(e):
            entry = {
                "title": title_f.value,
                "tags": [t.strip() for t in tags_f.value.split(",") if t.strip()],
                "languages": [l.strip() for l in lang_f.value.split(",") if l.strip()],
                "severity": severity_dd.value or "medium",
                "error_patterns": [title_f.value],
                "solution_steps": [s.strip() for s in steps_f.value.split("\n") if s.strip()],
                "code_example": code_f.value,
                "related_topics": [],
                "source": "user_added",
            }
            try:
                mgr = _build_manager(providers)
                mgr.add_entry(entry)
                mgr.close()
                page.dialog.open = False
                _build_entry_list()
                page.snack_bar = ft.SnackBar(ft.Text("Entry added", size=13), open=True, duration=2000)
                page.update()
            except Exception as exc:
                logger.warning("Add entry failed: %s", exc)

        page.dialog = ft.AlertDialog(
            title=ft.Text("Add KB Entry"),
            content=ft.Column([title_f, tags_f, lang_f, severity_dd, steps_f, code_f], width=400, spacing=8, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Save", on_click=_save),
            ],
        )
        page.dialog.open = True
        page.update()

    def _show_import_dialog(e):
        if not page:
            return
        path_f = ft.TextField(label="File path", hint_text="absolute path to .json or .txt file")
        col_dd = ft.Dropdown(
            label="Target collection",
            value="error_solutions",
            options=[ft.dropdown.Option(k, v.get("label", k)) for k, v in KB_PACKAGE_MAP.items()],
        )

        def _import(e):
            path = path_f.value.strip()
            if not path:
                return
            try:
                mgr = _build_manager(providers)
                if path.endswith(".json"):
                    count = mgr.import_json(path, col_dd.value or "error_solutions")
                else:
                    count = mgr.import_text(path, col_dd.value or "error_solutions")
                mgr.close()
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"Imported {count} entries", size=13), open=True, duration=2000)
                _build_entry_list()
                page.update()
            except Exception as exc:
                logger.warning("Import failed: %s", exc)

        page.dialog = ft.AlertDialog(
            title=ft.Text("Import KB Entries"),
            content=ft.Column([path_f, col_dd], width=400, spacing=8),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Import", on_click=_import),
            ],
        )
        page.dialog.open = True
        page.update()

    def _show_export_dialog(e):
        if not page:
            return
        col_dd = ft.Dropdown(
            label="Collection",
            value="error_solutions",
            options=[ft.dropdown.Option(k, v.get("label", k)) for k, v in KB_PACKAGE_MAP.items()],
        )

        def _export(e):
            col = col_dd.value or "error_solutions"
            try:
                mgr = _build_manager(providers)
                data = mgr.export_collection(col)
                mgr.close()
                export_path = Path.cwd() / f"kb_export_{col}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                export_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                page.dialog.open = False
                page.snack_bar = ft.SnackBar(ft.Text(f"Exported to {export_path.name}", size=13), open=True, duration=2000)
                page.update()
            except Exception as exc:
                logger.warning("Export failed: %s", exc)

        page.dialog = ft.AlertDialog(
            title=ft.Text("Export KB Collection"),
            content=ft.Column([col_dd], width=400, spacing=8),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(page.dialog, 'open', False) or page.update()),
                ft.ElevatedButton("Export", on_click=_export),
            ],
        )
        page.dialog.open = True
        page.update()

    def _do_search(e):
        query = search_field.value.strip()
        if not query:
            return
        nonlocal search_results
        try:
            mgr = _build_manager(providers)
            search_results = mgr.search_all_collections(query, k=3)
            mgr.close()
        except Exception as exc:
            logger.warning("KB search failed: %s", exc)
            search_results = []

        search_container.controls.clear()
        if not search_results:
            search_results_text.value = "No results found"
            search_container.controls.append(search_results_text)
        else:
            search_results_text.value = f"{len(search_results)} results"
            search_container.controls.append(search_results_text)
            for r in search_results:
                score = r.get("score", 0)
                score_pct = int(score * 100)
                color = ft.Colors.GREEN_400 if score >= 0.7 else (ft.Colors.AMBER_400 if score >= 0.4 else ft.Colors.GREY_400)
                col_name = r.get("collection", "kb")
                title = r.get("title", r.get("content", "")[:60])
                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(title, size=11, weight=ft.FontWeight.W_600, color=text_p, expand=1),
                            ft.Container(
                                content=ft.Text(f"{score_pct}%", size=8, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                                padding=padding_only(left=4, top=2, right=4, bottom=2), border_radius=4, bgcolor=color,
                            ),
                        ], spacing=4),
                        ft.Text(f"Collection: {col_name} · Score: {score:.3f}", size=9, color=text_m),
                    ], spacing=2),
                    padding=padding_symmetric(horizontal=10, vertical=6),
                    border_radius=4, bgcolor=accent_sub,
                    border=border_all(0.5, border),
                )
                search_container.controls.append(card)
        search_container.update()
        page.update()

    search_field.on_submit = _do_search

    header = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.LIBRARY_BOOKS, size=22, color=accent),
                ft.Text("Knowledge Base", size=20, weight=ft.FontWeight.BOLD, color=text_p, expand=1),
                ft.TextButton("Import", icon=ft.Icons.FILE_UPLOAD, style=ft.ButtonStyle(color=accent, text_style=ft.TextStyle(size=11)), on_click=_show_import_dialog),
                ft.TextButton("Export", icon=ft.Icons.FILE_DOWNLOAD, style=ft.ButtonStyle(color=accent, text_style=ft.TextStyle(size=11)), on_click=_show_export_dialog),
                ft.FilledButton("Add Entry", icon=ft.Icons.ADD, style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=accent, shape=ft.RoundedRectangleBorder(radius=6)),
                                on_click=_show_add_dialog),
            ], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=4),
            ft.Text("Manage, search, import, and export your knowledge base", size=11, color=text_s),
        ], spacing=2),
        padding=padding_symmetric(horizontal=0, vertical=4),
    )

    stats_section = ft.Container(
        content=_build_stats_row(),
        padding=padding_symmetric(vertical=8),
    )

    packages_section = ft.Container(
        content=ft.Column([
            ft.Text("Knowledge Packages", size=14, weight=ft.FontWeight.W_600, color=text_p),
            ft.Text("Curated collections of debugging solutions", size=10, color=text_s),
            ft.Container(height=6),
            _build_packages_section(),
        ], spacing=2),
        padding=padding_symmetric(vertical=8),
    )

    search_section = ft.Container(
        content=ft.Column([
            ft.Text("Search", size=14, weight=ft.FontWeight.W_600, color=text_p),
            ft.Row([search_field], spacing=4),
            search_container,
        ], spacing=4),
        padding=padding_symmetric(vertical=8),
    )

    entries_section = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Entries", size=14, weight=ft.FontWeight.W_600, color=text_p, expand=1),
                ft.Text("recent 50", size=10, color=text_m),
            ], spacing=4),
            ft.Container(height=4),
            entry_list_content,
        ], spacing=2),
        padding=padding_symmetric(vertical=8),
    )

    stats_section.content = _build_stats_row()

    return ft.Container(
        content=ft.Column([
            header,
            ft.Divider(height=1, color=border),
            stats_section,
            packages_section,
            search_section,
            ft.Divider(height=1, color=border),
            entries_section,
        ], spacing=0, scroll=ft.ScrollMode.AUTO),
        padding=padding_symmetric(horizontal=24, vertical=16),
        expand=1,
    )
