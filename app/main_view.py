import flet as ft
from pathlib import Path

from core.agent import DebugAgent
from core.config import UI_TITLE
from core.providers import ProviderManager
from core.project_manager import ProjectManager
from core.session import Session
from app.theme import (
    make_theme,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_PRIMARY, LIGHT_BG_PRIMARY,
    DARK_BG_SIDEBAR, LIGHT_BG_SIDEBAR,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
    NAV_WIDTH, TOP_BAR_HEIGHT,
    border_all, padding_symmetric,
)
from app.components.detailed_footer import DetailedFooter
from app.components.toolbar import Toolbar
from app.components.file_tree import FileTree
from app.components.session_list import SessionList
from app.views.home_view import home_view
from app.views.debug_view import DebugView
from app.views.history_view import history_view
from app.views.settings_view import settings_view
from app.views.kb_view import kb_view
from core.kb_manager import KbManager

SIDEBAR_WIDTH = 260


class MainView:
    def __init__(self, is_dark_default=False):
        providers = ProviderManager.load()
        self.agent = DebugAgent(providers=providers)
        self.project_mgr = ProjectManager()
        try:
            mgr = KbManager(providers=providers)
            mgr.ensure_seeded()
            mgr.close()
        except Exception as exc:
            logger.debug("KbManager seeding skipped: %s", exc)
        self.project = self.project_mgr.get_or_create_default()
        self._current_session: Session | None = None
        self.page = None
        self._is_dark = is_dark_default
        self._nav_index = 0
        self.content_area = ft.Container(expand=1)
        self.nav_rail = None
        self.debug_view = None
        self._toolbar = None
        self._footer = None
        self._side_panel = None
        self._file_tree = None
        self._session_list: SessionList | None = None
        self._project_header = None
        self._menubar_container = None
        self._side_panel_content = None
        self._root = None

    def _cp(self):
        d = self._is_dark
        return type("_", (), {
            "accent": DARK_ACCENT if d else LIGHT_ACCENT,
            "accent_subtle": DARK_ACCENT_SUBTLE if d else LIGHT_ACCENT_SUBTLE,
            "text_p": DARK_TEXT_PRIMARY if d else LIGHT_TEXT_PRIMARY,
            "text_s": DARK_TEXT_SECONDARY if d else LIGHT_TEXT_SECONDARY,
            "text_m": DARK_TEXT_MUTED if d else LIGHT_TEXT_MUTED,
            "bg": DARK_BG_PRIMARY if d else LIGHT_BG_PRIMARY,
            "bg_surface": DARK_BG_SURFACE if d else LIGHT_BG_SURFACE,
            "bg_sidebar": DARK_BG_SIDEBAR if d else LIGHT_BG_SIDEBAR,
            "border": DARK_BORDER if d else LIGHT_BORDER,
        })()

    def build(self, page: ft.Page):
        self.page = page
        page.title = UI_TITLE
        page.window.width = 1280
        page.window.height = 820
        page.window.min_width = 960
        page.window.min_height = 600
        page.padding = 0
        page.spacing = 0
        page.theme = make_theme(self._is_dark)
        page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        page.bgcolor = self._cp().bg
        page.update()
        c = self._cp()
        self._footer = DetailedFooter(agent=self.agent, page=page, is_dark=self._is_dark)
        self._footer.set_os_info(self.agent.get_os_info())
        self.debug_view = DebugView(page, self.agent, is_dark=self._is_dark, on_new_session=self._on_new_session, status_bar=self._footer)
        self._build_side_panel()
        self.nav_rail = self._build_nav_rail()
        self._build_toolbar()
        self._build_menubar()

        self._root = ft.Column([
            self._menubar_container,
            ft.Divider(height=1, color=c.border),
            self._toolbar.build(),
            ft.Divider(height=1, color=c.border),
            ft.Row([
                self.nav_rail,
                ft.VerticalDivider(width=1, color=c.border),
                self._side_panel,
                ft.VerticalDivider(width=1, color=c.border),
                self.content_area,
            ], expand=1, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
            ft.Divider(height=1, color=c.border),
            self._footer.build(),
        ], spacing=0, expand=1)

        page.add(self._root)
        self._footer.start()
        self._navigate(0)

    def _update_theme_colors(self):
        c = self._cp()
        self.page.theme = make_theme(self._is_dark)
        self.page.theme_mode = ft.ThemeMode.DARK if self._is_dark else ft.ThemeMode.LIGHT
        self.page.bgcolor = c.bg
        self._menubar_container.bgcolor = c.bg_sidebar
        self._menubar_container.update()
        old_toolbar = self._toolbar._container
        new_toolbar = self._toolbar.rebuild(self._is_dark)
        for i, ctrl in enumerate(self._root.controls):
            if ctrl is old_toolbar:
                self._root.controls[i] = new_toolbar
                break
        old_footer = self._footer._container
        new_footer = self._footer.rebuild(self._is_dark)
        for i, ctrl in enumerate(self._root.controls):
            if ctrl is old_footer:
                self._root.controls[i] = new_footer
                break
        self._root.update()
        self._side_panel.bgcolor = c.bg_sidebar
        self._side_panel.border = border_all(0.5, c.border)
        self._side_panel.update()
        self.content_area.content = None
        self._navigate(self._nav_index)
        self.page.update()

    def _refresh_session_list(self):
        if not self.project:
            return
        sessions = self.project.list_sessions()
        active_id = self.project.active_session_id
        if self._session_list:
            self._session_list.update_data(sessions, active_id)

    def _build_side_panel(self):
        c = self._cp()
        root = self.project.root_path if self.project else "."

        sessions = self.project.list_sessions() if self.project else []
        active_id = self.project.active_session_id if self.project else None
        self._session_list = SessionList(
            sessions=sessions,
            active_id=active_id,
            on_select=self._on_session_selected,
            on_new=self._on_new_session,
            is_dark=self._is_dark,
        )

        self._file_tree = FileTree(
            root_path=root,
            on_file_select=self._on_file_selected,
            is_dark=self._is_dark,
        )

        proj_name = self.project.name if self.project else "No project"
        self._project_header = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER, size=16, color=c.accent),
                ft.Text(proj_name, size=13, weight=ft.FontWeight.W_600, color=c.text_p, expand=1),
                ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16, color=c.text_m),
            ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=padding_symmetric(horizontal=10, vertical=8),
            border_radius=6,
        )
        self._project_header.on_click = lambda _: self._show_project_switcher()

        divider = ft.Divider(height=1, color=c.border)
        ft_header_text = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN, size=14, color=c.text_m),
                ft.Text("Files", size=11, weight=ft.FontWeight.W_600, color=c.text_m, expand=1),
            ], spacing=4),
            padding=padding_symmetric(horizontal=10, vertical=4),
        )

        side_content = ft.Column([
            self._project_header,
            divider,
            self._session_list.build(),
            divider,
            ft_header_text,
            self._file_tree.build(),
        ], spacing=0, expand=1)

        if self._side_panel is not None:
            self._side_panel.content = side_content
            self._side_panel.bgcolor = c.bg_sidebar
            self._side_panel.border = border_all(0.5, c.border)
        else:
            self._side_panel = ft.Container(
                content=side_content,
                width=SIDEBAR_WIDTH,
                bgcolor=c.bg_sidebar,
                border=border_all(0.5, c.border),
                padding=padding_symmetric(vertical=4),
            )

    def _on_session_selected(self, session_id: str):
        if not self.project:
            return
        session_path = self.project.sessions_dir / f"{session_id}.json"
        if session_path.exists():
            session = Session.load(file_path=session_path)
        else:
            session = Session.load(session_id=session_id)
        if not session:
            return
        self._current_session = session
        self.project.active_session_id = session_id
        self.project.save()
        if self._nav_index != 1:
            self._nav_index = 1
            self.nav_rail.selected_index = 1
            self._navigate(1)
        self.debug_view.load_session(session)
        self._refresh_session_list()
        if self.page:
            self.page.update()

    def _on_new_session(self, preconfig: dict | None = None):
        if not self.project:
            return
        if preconfig:
            # Called after config form submits
            self._do_create_session(preconfig)
            return
        # Show config dialog first
        overlay = self.debug_view.show_session_config(
            on_config_done=lambda cfg: self._on_new_session(cfg)
        )

    def _do_create_session(self, cfg: dict):
        session = Session.create(
            project=self.project, source_file="",
            session_name=cfg.get("name", ""),
            skills=cfg.get("skills", ["debugging"]),
            role=cfg.get("role", "developer"),
            prompt_style=cfg.get("prompt_style", "detailed"),
        )
        self._current_session = session
        self.project.active_session_id = session.id
        self.project.save()
        if self._nav_index != 1:
            self._nav_index = 1
            self.nav_rail.selected_index = 1
            self._navigate(1)
        self.debug_view.load_session(session)
        self._refresh_session_list()
        if self.page:
            self.page.update()

    def _on_file_selected(self, path):
        if not self.project:
            return
        session = Session.create(project=self.project, source_file=path)
        self._current_session = session
        self.project.active_session_id = session.id
        self.project.save()
        if self._nav_index != 1:
            self._nav_index = 1
            self.nav_rail.selected_index = 1
            self._navigate(1)
        self.debug_view.load_session(session)
        self._refresh_session_list()
        if self.page:
            self.page.update()

    def _show_project_switcher(self):
        if not self.page:
            return
        projects = self.project_mgr.list_projects()
        current = self.project.name if self.project else ""

        options = [ft.dropdown.Option(p["name"]) for p in projects]
        dd = ft.Dropdown(
            options=options,
            value=current if current in [p["name"] for p in projects] else None,
            label="Switch project",
            width=300,
        )

        def _on_switch(e):
            name = dd.value
            if name and name != current:
                self._switch_project(name)
            self.page.dialog.open = False
            self.page.update()

        name_field = ft.TextField(label="New project name", hint_text="e.g. my-web-app")
        path_field = ft.TextField(label="Project folder path", hint_text="e.g. C:\\Projects\\my-app", expand=1)

        def _on_create(e):
            n = name_field.value.strip()
            p = path_field.value.strip()
            if n:
                import os
                if not p or not os.path.isdir(p):
                    p = str(Path(self.project.root_path if self.project else ".").resolve())
                new_proj = self.project_mgr.create_project(n, root_path=p)
                self._switch_to_project(new_proj)
            self.page.dialog.open = False
            self.page.update()

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Projects"),
            content=ft.Column([
                dd,
                ft.Row([
                    ft.ElevatedButton("Switch", on_click=_on_switch),
                ], alignment=ft.MainAxisAlignment.END),
                ft.Divider(height=1),
                ft.Text("Create new project", size=13, weight=ft.FontWeight.W_600),
                name_field,
                path_field,
                ft.Row([
                    ft.ElevatedButton("Create", on_click=_on_create),
                ], alignment=ft.MainAxisAlignment.END),
            ], width=450, spacing=8),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()),
            ],
        )
        self.page.dialog.open = True
        self.page.update()

    def _switch_project(self, name: str):
        p = ProjectManager._load_project(name)
        if p:
            self._switch_to_project(p)

    def _switch_to_project(self, project):
        self.project = project
        self.project_mgr.set_current(project)
        self._current_session = None
        self.debug_view = DebugView(self.page, self.agent, is_dark=self._is_dark, on_new_session=self._on_new_session, status_bar=self._footer)
        self._build_side_panel()
        self._toolbar.set_project_name(project.name)
        self._navigate(self._nav_index)
        if self.page:
            self.page.update()

    def _build_toolbar(self):
        self._toolbar = Toolbar(
            page=self.page,
            is_dark=self._is_dark,
            on_toggle_theme=self._toggle_theme,
            on_project_click=lambda _: self._show_project_switcher(),
        )
        if self.project:
            self._toolbar.set_project_name(self.project.name)

    def _toggle_sidebar(self, e=None):
        if self._side_panel:
            self._side_panel.visible = not self._side_panel.visible
            self._side_panel.update()
            self.page.update()

    def _toggle_theme_menu(self, e=None):
        self._is_dark = not self._is_dark
        self.debug_view.is_dark = self._is_dark
        self._footer.is_dark = self._is_dark
        self._update_theme_colors()
        self._toolbar.set_theme(self._is_dark)

    def _build_menubar(self):
        c = self._cp()
        bg_style = ft.ButtonStyle(bgcolor={"": c.bg_surface})
        menubar = ft.MenuBar(
            controls=[
                ft.SubmenuButton(
                    content=ft.Text("  File  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("New Project...", size=12), leading=ft.Icon(ft.Icons.FOLDER, size=16), on_click=lambda _: self._show_project_switcher(), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Open Folder...", size=12), leading=ft.Icon(ft.Icons.FOLDER_OPEN, size=16), on_click=self._pick_project_folder, style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Close Project", size=12), leading=ft.Icon(ft.Icons.CLOSE, size=16), style=bg_style, on_click=lambda _: self._switch_to_project(self.project_mgr.get_or_create_default())),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Recent Projects", size=12), leading=ft.Icon(ft.Icons.HISTORY, size=16), style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Exit", size=12), leading=ft.Icon(ft.Icons.EXIT_TO_APP, size=16), on_click=lambda _: self.page.window.close() if self.page else None, style=bg_style),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text("  Edit  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("Undo", size=12), leading=ft.Icon(ft.Icons.UNDO, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Redo", size=12), leading=ft.Icon(ft.Icons.REDO, size=16), style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Cut", size=12), leading=ft.Icon(ft.Icons.CONTENT_CUT, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Copy", size=12), leading=ft.Icon(ft.Icons.CONTENT_COPY, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Paste", size=12), leading=ft.Icon(ft.Icons.CONTENT_PASTE, size=16), style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Select All", size=12), leading=ft.Icon(ft.Icons.SELECT_ALL, size=16), style=bg_style),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text("  View  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("Toggle Sidebar", size=12), leading=ft.Icon(ft.Icons.VIEW_SIDEBAR, size=16), on_click=self._toggle_sidebar, style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Toggle Footer", size=12), leading=ft.Icon(ft.Icons.VIEW_COLUMN, size=16), on_click=self._toggle_footer, style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Toggle Dark Mode", size=12), leading=ft.Icon(ft.Icons.DARK_MODE, size=16), on_click=self._toggle_theme_menu, style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Zoom In", size=12), leading=ft.Icon(ft.Icons.ZOOM_IN, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Zoom Out", size=12), leading=ft.Icon(ft.Icons.ZOOM_OUT, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Reset Zoom", size=12), leading=ft.Icon(ft.Icons.ASPECT_RATIO, size=16), style=bg_style),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text("  Debug  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("New Session", size=12), leading=ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=16), on_click=lambda _: self._on_new_session(), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Stop Generation", size=12), leading=ft.Icon(ft.Icons.STOP_CIRCLE, size=16), on_click=lambda _: self.debug_view._on_stop(None) if self.debug_view else None, style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Clear Chat", size=12), leading=ft.Icon(ft.Icons.DELETE_SWEEP, size=16), on_click=lambda _: self._on_new_session(), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Screenshot Mode", size=12), leading=ft.Icon(ft.Icons.CAMERA_ALT, size=16), style=bg_style),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text("  Tools  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("AI Providers...", size=12), leading=ft.Icon(ft.Icons.TUNE, size=16), on_click=lambda _: self._navigate(3), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Knowledge Base", size=12), leading=ft.Icon(ft.Icons.LIBRARY_BOOKS, size=16), on_click=lambda _: self._navigate(4), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Bandit Statistics", size=12), leading=ft.Icon(ft.Icons.BAR_CHART, size=16), style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Import", size=12), leading=ft.Icon(ft.Icons.FILE_UPLOAD, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Export", size=12), leading=ft.Icon(ft.Icons.FILE_DOWNLOAD, size=16), style=bg_style),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text("  Window  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("Minimize", size=12), leading=ft.Icon(ft.Icons.HORIZONTAL_RULE, size=16), on_click=lambda _: self.page.window.minimize() if self.page else None, style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Maximize", size=12), leading=ft.Icon(ft.Icons.CROP_SQUARE, size=16), on_click=lambda _: self.page.window.maximize() if self.page else None, style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Close", size=12), leading=ft.Icon(ft.Icons.CLOSE, size=16), on_click=lambda _: self.page.window.close() if self.page else None, style=bg_style),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text("  Help  ", size=12, color=c.text_m),
                    controls=[
                        ft.MenuItemButton(content=ft.Text("About Debugly", size=12), leading=ft.Icon(ft.Icons.INFO_OUTLINE, size=16), style=bg_style),
                        ft.Divider(height=1),
                        ft.MenuItemButton(content=ft.Text("Check for Updates", size=12), leading=ft.Icon(ft.Icons.SYSTEM_UPDATE, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Documentation", size=12), leading=ft.Icon(ft.Icons.MENU_BOOK, size=16), style=bg_style),
                        ft.MenuItemButton(content=ft.Text("Report Issue", size=12), leading=ft.Icon(ft.Icons.BUG_REPORT_OUTLINED, size=16), style=bg_style),
                    ],
                ),
            ],
        )
        self._menubar_container = ft.Container(
            content=menubar,
            bgcolor=c.bg_sidebar,
            padding=ft.Padding(left=4, top=0, right=0, bottom=0),
        )

    def _toggle_footer(self, e=None):
        if self._footer:
            vis = not self._footer._container.visible
            self._footer._container.visible = vis
            self._footer._container.update()
            self.page.update()

    async def _pick_project_folder(self, e):
        fp = ft.FilePicker()
        result = await fp.get_directory_path()
        if result and self.project_mgr:
            name = Path(result).name
            p = self.project_mgr.create_project(name, root_path=result)
            self._switch_to_project(p)

    def _build_nav_rail(self):
        c = self._cp()
        destinations = [
            ("Explorer", ft.Icons.FOLDER_OUTLINED, ft.Icons.FOLDER),
            ("Debug", ft.Icons.BUG_REPORT_OUTLINED, ft.Icons.BUG_REPORT),
            ("History", ft.Icons.HISTORY_OUTLINED, ft.Icons.HISTORY),
            ("Settings", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS),
            ("Knowledge", ft.Icons.LIBRARY_BOOKS_OUTLINED, ft.Icons.LIBRARY_BOOKS),
        ]

        return ft.NavigationRail(
            selected_index=self._nav_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=72,
            min_extended_width=NAV_WIDTH,
            group_alignment=-0.8,
            bgcolor=c.bg_sidebar,
            indicator_color=c.accent_subtle,
            indicator_shape=ft.RoundedRectangleBorder(radius=8),
            leading=ft.Container(height=8),
            trailing=ft.Container(height=8),
            destinations=[
                ft.NavigationRailDestination(
                    icon=icon,
                    selected_icon=sel_icon,
                    label=label,
                ) for label, icon, sel_icon in destinations
            ],
            on_change=self._on_nav_change,
            selected_label_text_style=ft.TextStyle(
                size=11,
                weight=ft.FontWeight.W_600,
                color=c.accent,
            ),
            unselected_label_text_style=ft.TextStyle(
                size=11,
                weight=ft.FontWeight.W_400,
                color=c.text_m,
            ),
        )

    def _on_nav_change(self, e):
        self._nav_index = e.control.selected_index
        self._navigate(self._nav_index)
        self.page.update()

    def _update_side_panel(self):
        c = self._cp()
        self._side_panel.bgcolor = c.bg_sidebar
        self._side_panel.border = border_all(0.5, c.border)
        self._side_panel.update()

    def _toggle_theme(self, e):
        self._is_dark = e.control.value
        self.debug_view.is_dark = self._is_dark
        self._footer.is_dark = self._is_dark
        self._update_theme_colors()

    def _on_providers_changed(self):
        self.agent.reload_providers()
        self.debug_view = DebugView(self.page, self.agent, is_dark=self._is_dark, on_new_session=self._on_new_session, status_bar=self._footer)
        if self._nav_index == 1:
            self._navigate(1)

    def _navigate(self, index: int):
        self._nav_index = index
        self._update_side_panel()
        views = [self._home, self._debug, self._history, self._settings, self._kb]
        if 0 <= index < len(views):
            content = views[index]()
            self.content_area.content = content
            self.content_area.update()

    def _home(self):
        return home_view(
            on_navigate=lambda i: self._navigate(i),
            is_dark=self._is_dark,
        )

    def _debug(self):
        return self.debug_view.build()

    def _history(self):
        sessions = []
        if self.project:
            sessions = self.project.list_sessions()
        return history_view(
            is_dark=self._is_dark,
            sessions=sessions,
        )

    def _settings(self):
        try:
            stats = self.agent.bandit_stats()
        except Exception:
            stats = {}
        return settings_view(
            page=self.page,
            on_toggle_theme=self._toggle_theme,
            on_providers_change=self._on_providers_changed,
            is_dark=self._is_dark,
            bandit_stats=stats,
        )

    def _kb(self):
        return kb_view(is_dark=self._is_dark, page=self.page, providers=self.agent.providers)
