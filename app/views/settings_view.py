import flet as ft

from app.theme import (
    surface_container, border_all, padding_symmetric, padding_only,
    DARK_ACCENT, LIGHT_ACCENT,
    DARK_ACCENT_SUBTLE, LIGHT_ACCENT_SUBTLE,
    DARK_TEXT_PRIMARY, LIGHT_TEXT_PRIMARY,
    DARK_TEXT_SECONDARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_MUTED, LIGHT_TEXT_MUTED,
    DARK_BG_SURFACE, LIGHT_BG_SURFACE,
    DARK_BORDER, LIGHT_BORDER,
)
from core.providers import ProviderManager, ProviderConfig
from core.database import approved_sites_list, approved_site_add, approved_site_delete, approved_site_toggle, seed_approved_sites
from core.config import OLLAMA_BASE_URL


def _collapsible_section(
    title: str,
    icon,
    config: ProviderConfig | None,
    on_change,
    is_dark: bool = False,
    page: ft.Page | None = None,
):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    _expanded = [True]

    def _mark_dirty():
        if on_change:
            on_change()

    def _update(field, value):
        if config:
            setattr(config, field, value)
        _mark_dirty()

    if config is None:
        return ft.Container()

    model_field = ft.Dropdown(
        value=config.model if config.model else None,
        hint_text="Select or type model...",
        expand=1,
        text_size=12,
        editable=True,
        enable_filter=True,
        options=[],
        on_select=lambda e: _update("model", e.control.value),
        on_blur=lambda e: _update("model", e.control.value.strip() or config.model),
    )
    loading_text = ft.Text("Loading...", size=10, color=text_s, visible=False)

    def _auto_load_models():
        base = config.base_url or OLLAMA_BASE_URL
        ptype = config.provider_type
        try:
            models = ProviderManager.fetch_available_models(ptype, base)
            if models:
                model_field.options = [ft.dropdown.Option(m, m) for m in models]
                model_field.value = config.model if config.model in models else models[0]
        except Exception:
            pass

    async def _load_models(e):
        base = base_url_field.value.strip() or OLLAMA_BASE_URL
        ptype = provider_type_dd.value
        loading_text.visible = True
        loading_text.update()
        try:
            models = ProviderManager.fetch_available_models(ptype, base)
            if models:
                model_field.options = [ft.dropdown.Option(m, m) for m in models]
                model_field.value = config.model if config.model in models else models[0]
            else:
                model_field.options = []
                model_field.value = ""
        except Exception:
            model_field.options = []
            model_field.value = ""
        loading_text.visible = False
        model_field.update()
        loading_text.update()

    load_models_btn = ft.IconButton(
        icon=ft.Icons.REFRESH, icon_size=14, tooltip="Load models",
        on_click=_load_models,
    )

    enabled_switch = ft.Switch(
        value=config.enabled,
        active_color=accent,
        on_change=lambda e: (_update("enabled", e.control.value)),
    )

    base_url_field = ft.TextField(
        value=config.base_url,
        hint_text="http://localhost:11434",
        expand=1,
        text_size=12,
        border_radius=6,
        border=border_all(1, border),
        bgcolor="transparent",
        on_change=lambda e: (_update("base_url", e.control.value)),
    )
    api_key_field = ft.TextField(
        value=config.api_key,
        hint_text="API key",
        expand=1,
        text_size=12,
        border_radius=6,
        border=border_all(1, border),
        password=True,
        can_reveal_password=True,
        on_change=lambda e: (_update("api_key", e.control.value)),
    )

    provider_type_dd = ft.Dropdown(
        value=config.provider_type,
        options=[
            ft.dropdown.Option("ollama", "Ollama"),
            ft.dropdown.Option("openai", "OpenAI Compatible"),
        ],
        width=160,
        text_size=12,
        on_select=lambda e: (_update("provider_type", e.control.value)),
    )

    fields = ft.Column([
        ft.Row([
            ft.Text("Enable", size=12, color=text_s, width=70),
            enabled_switch,
            ft.Text("Type", size=12, color=text_s, width=30),
            provider_type_dd,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            ft.Text("Base URL", size=12, color=text_s, width=70),
            base_url_field,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            ft.Text("Model", size=12, color=text_s, width=70),
            ft.Row([model_field, load_models_btn, loading_text], spacing=4, expand=1),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Row([
            ft.Text("API Key", size=12, color=text_s, width=70),
            api_key_field,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
    ], spacing=4)

    content_col = ft.Column([fields], spacing=4, visible=True)

    def _toggle_expand(e):
        _expanded[0] = not _expanded[0]
        content_col.visible = _expanded[0]
        content_col.update()

    header = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Icon(icon, size=16, color=accent),
                width=26, height=26, border_radius=6, bgcolor=accent_subtle,
            ),
            ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=text_p, expand=1),
            ft.Icon(ft.Icons.EXPAND_LESS, size=18, color=text_s),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        on_click=_toggle_expand,
    )

    section = ft.Container(
        content=ft.Column([header, ft.Divider(height=0, color=border), content_col], spacing=6),
        padding=12, border_radius=8,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border=border_all(0.5, border),
    )

    return section, _auto_load_models


def _approved_sites_section(is_dark: bool, page: ft.Page | None = None):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    text_m = DARK_TEXT_MUTED if is_dark else LIGHT_TEXT_MUTED
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    sites_list = ft.Column(spacing=4)

    def _refresh():
        sites = approved_sites_list()
        sites_list.controls.clear()
        if not sites:
            sites_list.controls.append(ft.Text("No approved sites configured.", size=11, color=text_m, italic=True))
        for s in sites:
            row = ft.Container(
                content=ft.Row([
                    ft.Switch(
                        value=bool(s.get("enabled", 1)),
                        active_color=accent,
                        on_change=lambda e, sid=s["id"]: (approved_site_toggle(sid, e.control.value), _refresh()),
                    ),
                    ft.Column([
                        ft.Text(s.get("label", "") or s.get("url", ""), size=11, weight=ft.FontWeight.W_500, color=text_p, expand=1),
                        ft.Text(s.get("url", ""), size=9, color=text_m),
                    ], spacing=1, expand=1),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE, icon_size=14,
                        icon_color=ft.Colors.RED_400,
                        on_click=lambda _, sid=s["id"]: (approved_site_delete(sid), _refresh()),
                    ),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=padding_only(left=6, top=2, right=2, bottom=2),
                border_radius=4,
                bgcolor=accent_subtle,
            )
            sites_list.controls.append(row)
        try:
            sites_list.update()
        except RuntimeError:
            pass

    add_url_field = ft.TextField(
        hint_text="https://example.com/docs",
        expand=1, text_size=12, border_radius=6,
        border=border_all(1, border),
    )
    add_label_field = ft.TextField(
        hint_text="Label", width=120, text_size=12, border_radius=6,
        border=border_all(1, border),
    )

    def _add_site(e):
        url = add_url_field.value.strip()
        label = add_label_field.value.strip()
        if url:
            approved_site_add(url, label)
            add_url_field.value = ""
            add_label_field.value = ""
            add_url_field.update()
            add_label_field.update()
            _refresh()

    seed_approved_sites()

    section = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.LANGUAGE, size=16, color=accent),
                    width=26, height=26, border_radius=6, bgcolor=accent_subtle,
                ),
                ft.Text("Approved Web Sources", size=14, weight=ft.FontWeight.W_600, color=text_p, expand=1),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=0, color=border),
            ft.Text("Approved sites are searched when the knowledge base has no results. Only traffic to these domains is allowed.", size=10, color=text_s),
            ft.Container(height=4),
            sites_list,
            ft.Container(height=4),
            ft.Row([add_url_field, add_label_field, ft.ElevatedButton("Add", icon=ft.Icons.ADD, style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=accent, shape=ft.RoundedRectangleBorder(radius=6)), on_click=_add_site)], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=6),
        padding=12, border_radius=8,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border=border_all(0.5, border),
    )

    _refresh()
    return section


def _bandit_stats_section(bandit_stats: dict, is_dark: bool, page: ft.Page | None = None):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    accent_subtle = DARK_ACCENT_SUBTLE if is_dark else LIGHT_ACCENT_SUBTLE
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    arms = bandit_stats.get("arms", [])
    arm_rows = []
    for a in arms:
        arm_rows.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(a["label"][0], size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        width=22, height=22, border_radius=11, bgcolor=accent, alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Text(a["label"], size=11, color=text_p, expand=1),
                    ft.Text(f"n={a['count']}", size=10, color=text_s),
                    ft.Text(f"v={a['value']:.3f}", size=10, color=accent),
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=padding_only(left=4, top=2, right=4, bottom=2),
                border_radius=4, bgcolor=accent_subtle,
            )
        )

    section = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.TUNE, size=16, color=accent),
                    width=26, height=26, border_radius=6, bgcolor=accent_subtle,
                ),
                ft.Text("RL Bandit Stats", size=14, weight=ft.FontWeight.W_600, color=text_p, expand=1),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=0, color=border),
            ft.Row([
                ft.Text(f"Epsilon: {bandit_stats.get('epsilon', 0):.4f}", size=10, color=text_s),
                ft.Text("(exploration rate)", size=9, color=text_s),
            ]),
            ft.Column(arm_rows, spacing=4),
        ], spacing=6),
        padding=12, border_radius=8,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border=border_all(0.5, border),
    )
    return section


def settings_view(page: ft.Page, on_toggle_theme, on_providers_change, is_dark: bool = False, bandit_stats: dict | None = None):
    accent = DARK_ACCENT if is_dark else LIGHT_ACCENT
    text_p = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
    text_s = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
    border = DARK_BORDER if is_dark else LIGHT_BORDER

    providers = ProviderManager.load()
    _dirty = [False]

    theme_switch = ft.Switch(
        value=is_dark,
        active_color=accent,
        on_change=on_toggle_theme,
    )

    save_btn = ft.ElevatedButton(
        "Save Changes",
        icon=ft.Icons.SAVE,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE, bgcolor=accent,
            shape=ft.RoundedRectangleBorder(radius=6),
        ),
        on_click=lambda _: _do_save(),
        disabled=True,
    )

    def _mark_dirty():
        _dirty[0] = True
        save_btn.disabled = False
        save_btn.update()

    def _do_save():
        try:
            providers.save()
            _dirty[0] = False
            save_btn.disabled = True
            save_btn.update()
            if on_providers_change:
                on_providers_change()
            page.show_snack_bar(
                ft.SnackBar(
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=18),
                        ft.Text("Settings saved", size=13),
                    ]),
                    open=True, duration=1500,
                )
            )
        except Exception as ex:
            page.show_snack_bar(
                ft.SnackBar(
                    ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_400, size=18),
                        ft.Text(f"Save failed: {ex}", size=13),
                    ]),
                    open=True, duration=3000,
                )
            )

    sec1, auto1 = _collapsible_section("LLM Provider", ft.Icons.PSYCHOLOGY, providers.llm, _mark_dirty, is_dark, page)
    sec2, auto2 = _collapsible_section("VLM / Vision", ft.Icons.IMAGE_SEARCH, providers.vlm, _mark_dirty, is_dark, page)
    sec3, auto3 = _collapsible_section("Chat Provider", ft.Icons.CHAT, providers.chat, _mark_dirty, is_dark, page)
    sec4, auto4 = _collapsible_section("Code Provider", ft.Icons.CODE, providers.code, _mark_dirty, is_dark, page)
    sec5, auto5 = _collapsible_section("Embedding", ft.Icons.LAYERS, providers.embedding, _mark_dirty, is_dark, page)

    import threading
    threading.Timer(0.5, auto1).start()
    threading.Timer(0.6, auto2).start()
    threading.Timer(0.7, auto3).start()
    threading.Timer(0.8, auto4).start()
    threading.Timer(0.9, auto5).start()

    approved = _approved_sites_section(is_dark, page)

    bandit = _bandit_stats_section(bandit_stats or {}, is_dark, page)

    content = ft.Column([
        ft.Text("Settings", size=22, weight=ft.FontWeight.BOLD, color=text_p),
        ft.Container(height=2),
        ft.Text("Configure models, providers, and behavior", size=12, color=text_s),
        ft.Container(height=12),

        ft.Text("General", size=14, weight=ft.FontWeight.W_600, color=text_p),
        ft.Container(height=6),
        surface_container(
            ft.Row([
                ft.Text("Dark Mode", size=13, color=text_p, expand=1),
                theme_switch,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=12, is_dark=is_dark,
        ),
        ft.Container(height=4),
        surface_container(
            ft.Row([
                ft.Text("Version", size=13, color=text_p, expand=1),
                ft.Text("1.0.0", size=12, color=text_s),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=12, is_dark=is_dark,
        ),

        ft.Container(height=12),
        ft.Text("AI Providers", size=14, weight=ft.FontWeight.W_600, color=text_p),
        ft.Container(height=6),
        sec1, ft.Container(height=6),
        sec2, ft.Container(height=6),
        sec3, ft.Container(height=6),
        sec4, ft.Container(height=6),
        sec5,

        ft.Container(height=12),
        approved,
        ft.Container(height=12),
        bandit,
        ft.Container(height=12),
        ft.Row([save_btn], alignment=ft.MainAxisAlignment.END),
        ft.Container(height=24),
    ], scroll=ft.ScrollMode.AUTO)

    return ft.Container(
        content=content,
        padding=padding_symmetric(horizontal=24, vertical=16),
        expand=1,
    )
