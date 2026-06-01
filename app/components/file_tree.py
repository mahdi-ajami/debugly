import os

import flet as ft

from app.theme import (
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    border_all, padding_symmetric,
)

EXCLUDED_DIRS = {".venv", "__pycache__", ".git", "chroma_data", ".gitignore"}
EXCLUDED_EXTS = {".pyc", ".pyo"}
MAX_DEPTH = 4

FILE_ICONS = {
    ".py": ft.Icons.CODE,
    ".js": ft.Icons.JAVASCRIPT,
    ".ts": ft.Icons.DATA_OBJECT,
    ".jsx": ft.Icons.JAVASCRIPT,
    ".tsx": ft.Icons.DATA_OBJECT,
    ".html": ft.Icons.HTML,
    ".css": ft.Icons.CSS,
    ".json": ft.Icons.DATA_ARRAY,
    ".yaml": ft.Icons.SETTINGS,
    ".yml": ft.Icons.SETTINGS,
    ".md": ft.Icons.ARTICLE,
    ".txt": ft.Icons.TEXT_SNIPPET,
    ".jpg": ft.Icons.IMAGE,
    ".jpeg": ft.Icons.IMAGE,
    ".png": ft.Icons.IMAGE,
    ".gif": ft.Icons.GIF,
    ".svg": ft.Icons.IMAGE,
    ".toml": ft.Icons.SETTINGS,
    ".env": ft.Icons.LOCK,
    ".sql": ft.Icons.STORAGE,
    ".sh": ft.Icons.TERMINAL,
    ".bat": ft.Icons.TERMINAL,
    ".ps1": ft.Icons.TERMINAL,
    ".exe": ft.Icons.TERMINAL,
    ".dll": ft.Icons.TERMINAL,
    ".pdf": ft.Icons.PICTURE_AS_PDF,
}

EXT_COLORS = {
    ".py": "#3572A5", ".js": "#F7DF1E", ".ts": "#3178C6",
    ".html": "#E34F26", ".css": "#563D7C", ".json": "#5B5B5B",
    ".md": "#083FA1", ".yaml": "#6B6B6B", ".yml": "#6B6B6B",
    ".toml": "#6B6B6B", ".sql": "#E38C00", ".sh": "#4EAA25",
    ".bat": "#C1F12E", ".ps1": "#012456", ".env": "#DBA400",
    ".txt": "#6B6B6B", ".jpg": "#6B6B6B", ".png": "#6B6B6B",
    ".svg": "#FFB13B", ".gif": "#6B6B6B", ".jpeg": "#6B6B6B",
}

LANG_MAP = {
    ".py": "Python", ".js": "JS", ".ts": "TS", ".html": "HTML",
    ".css": "CSS", ".json": "JSON", ".md": "MD", ".yaml": "YAML",
    ".yml": "YAML", ".toml": "TOML", ".sql": "SQL", ".sh": "Shell",
    ".bat": "Batch", ".ps1": "PowerShell", ".env": "Env",
    ".txt": "Text", ".svg": "SVG",
}


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 ** 2:
        return f"{size/1024:.1f}KB"
    return f"{size/1024**2:.1f}MB"


def _get_ext(name: str) -> str:
    _, ext = os.path.splitext(name)
    return ext.lower()


def _count_files(root: str) -> dict:
    total_files = 0
    total_dirs = 0
    ext_counts = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        total_dirs += 1
        for f in filenames:
            ext = _get_ext(f)
            if ext in EXCLUDED_EXTS:
                continue
            total_files += 1
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
    return {"files": total_files, "dirs": total_dirs, "exts": ext_counts}


class FileTree:
    def __init__(self, root_path: str, on_file_select=None, is_dark: bool = False):
        self.root = os.path.abspath(root_path)
        self.on_file_select = on_file_select
        self.is_dark = is_dark
        self._expanded = set()
        self._filter = ""

        self.c_accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
        self.c_text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
        self.c_text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
        self.c_text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
        self.c_bg_surface = DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE
        self.c_accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
        self.c_border = DARK_BORDER if is_dark else LIGHT_BORDER

        self.container = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0)
        self._rebuild()

    def _stats_header(self):
        stats = _count_files(self.root)
        lang_parts = []
        for ext, count in sorted(stats["exts"].items(), key=lambda x: -x[1])[:5]:
            name = LANG_MAP.get(ext, ext.lstrip(".").upper())
            lang_parts.append(f"{name} ({count})")
        exts_str = " \u00b7 ".join(lang_parts) if lang_parts else ""
        return ft.Container(
            content=ft.Text(
                f"{stats['files']} files \u00b7 {stats['dirs']} dirs"
                + (f" \u00b7 {exts_str}" if exts_str else ""),
                size=10, color=self.c_text_m,
            ),
            padding=padding_symmetric(horizontal=10, vertical=2),
        )

    def _search_field(self):
        def _on_search(e):
            self._filter = (e.control.value or "").strip().lower()
            self._rebuild()
            self.container.update()

        return ft.TextField(
            hint_text="Search files...",
            prefix_icon=ft.Icons.SEARCH,
            text_size=11,
            height=32,
            border_radius=6,
            border=border_all(0.5, self.c_border),
            bgcolor=self.c_bg_surface,
            content_padding=ft.Padding(left=8, right=8, top=4, bottom=4),
            on_change=_on_search,
        )

    def _rebuild(self):
        self.container.controls.clear()

        header = ft.Column([
            self._search_field(),
            self._stats_header(),
        ], spacing=2)
        self.container.controls.append(header)

        if self._filter:
            self._walk_filtered(self.root, self.container, 0)
        else:
            self._walk(self.root, self.container, 0)

    def _walk_filtered(self, dir_path, parent_col, depth):
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            return

        for name in entries:
            fp = os.path.join(dir_path, name)
            if os.path.isdir(fp):
                if name in EXCLUDED_DIRS:
                    continue
                self._add_dir(name, fp, parent_col, depth)
            elif os.path.isfile(fp):
                _, ext = os.path.splitext(name)
                if ext in EXCLUDED_EXTS:
                    continue
                if self._filter in name.lower():
                    self._add_file(name, fp, parent_col, depth)

    def _walk(self, dir_path, parent_col, depth):
        if depth > MAX_DEPTH:
            parent_col.controls.append(self._leaf("...", depth))
            return
        try:
            entries = sorted(os.listdir(dir_path))
        except PermissionError:
            parent_col.controls.append(self._leaf("(access denied)", depth, is_error=True))
            return

        dirs = []
        files = []
        for name in entries:
            fp = os.path.join(dir_path, name)
            if os.path.isdir(fp):
                dirs.append(name)
            elif os.path.isfile(fp):
                files.append(name)

        for name in dirs:
            if name in EXCLUDED_DIRS:
                continue
            self._add_dir(name, os.path.join(dir_path, name), parent_col, depth)

        for name in files:
            _, ext = os.path.splitext(name)
            if ext in EXCLUDED_EXTS:
                continue
            self._add_file(name, os.path.join(dir_path, name), parent_col, depth)

    def _add_dir(self, name, full_path, parent_col, depth):
        is_expanded = full_path in self._expanded
        icon = ft.Icons.EXPAND_MORE if is_expanded else ft.Icons.CHEVRON_RIGHT
        # Count visible children
        child_count = 0
        try:
            child_count = len([e for e in os.listdir(full_path)
                               if e not in EXCLUDED_DIRS and not e.startswith(".")])
        except PermissionError:
            pass
        count_label = f" ({child_count})" if child_count > 0 else ""

        row = ft.Row([
            ft.Icon(icon, size=14, color=self.c_text_m),
            ft.Icon(ft.Icons.FOLDER if not is_expanded else ft.Icons.FOLDER_OPEN,
                    size=15, color=self.c_accent),
            ft.Text(name + count_label, size=12, color=self.c_text_p, expand=1),
        ], spacing=4)

        btn = ft.Container(
            content=row,
            padding=padding_symmetric(horizontal=8),
            on_click=lambda _, p=full_path: self._toggle_dir(p),
        )

        child_col = ft.Column(spacing=0, visible=is_expanded)
        parent_col.controls.append(btn)
        parent_col.controls.append(child_col)

        if is_expanded:
            if self._filter:
                self._walk_filtered(full_path, child_col, depth + 1)
            else:
                self._walk(full_path, child_col, depth + 1)

        setattr(child_col, "__path", full_path)
        setattr(btn, "__child_col", child_col)

    def _add_file(self, name, full_path, parent_col, depth):
        display = name if len(name) < 36 else name[:33] + "..."
        ext = _get_ext(name)
        icon = FILE_ICONS.get(ext, ft.Icons.DESCRIPTION)
        ext_color = EXT_COLORS.get(ext, self.c_text_m)
        try:
            size_str = _format_size(os.path.getsize(full_path))
        except OSError:
            size_str = ""

        row = ft.Row([
            ft.Container(width=18),
            ft.Container(
                content=ft.Icon(icon, size=13, color=ext_color),
            ),
            ft.Text(display, size=12, color=self.c_text_s, expand=1),
            ft.Text(size_str, size=9, color=self.c_text_m, visible=bool(size_str)),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        btn = ft.Container(
            content=row,
            padding=padding_symmetric(horizontal=8),
        )
        btn.on_click = lambda _, p=full_path: self._on_file(p)
        parent_col.controls.append(btn)

    def _toggle_dir(self, path):
        if path in self._expanded:
            self._expanded.discard(path)
        else:
            self._expanded.add(path)
        self._rebuild()

    def _on_file(self, path):
        if self.on_file_select:
            self.on_file_select(path)

    def _leaf(self, text, depth, is_error=False):
        color = self.c_text_m
        if is_error:
            color = self.c_accent
        return ft.Container(
            content=ft.Row([
                ft.Container(width=22),
                ft.Text(text, size=11, color=color, italic=True),
            ], spacing=4),
            padding=padding_symmetric(horizontal=8),
        )

    def build(self):
        return self.container
