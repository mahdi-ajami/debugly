import flet as ft

from app.theme import DARK_BORDER, LIGHT_BORDER, border_all

LANG_NAMES = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "jsx": "JSX", "tsx": "TSX", "html": "HTML", "css": "CSS",
    "json": "JSON", "yaml": "YAML", "yml": "YAML", "bash": "Bash",
    "sh": "Shell", "sql": "SQL", "rust": "Rust", "go": "Go",
    "java": "Java", "kotlin": "Kotlin", "swift": "Swift",
    "c": "C", "cpp": "C++", "csharp": "C#", "ruby": "Ruby",
    "php": "PHP", "r": "R", "dart": "Dart", "toml": "TOML",
    "ini": "INI", "dockerfile": "Dockerfile", "makefile": "Makefile",
    "text": "Text", "plain": "Text",
}


def code_block(code: str, language: str = "python", is_dark: bool = False, page=None):
    def _copy(e):
        if page is None:
            return
        page.set_clipboard(code)
        page.show_snack_bar(
            ft.SnackBar(ft.Text("Copied to clipboard", size=13), open=True, duration=1500)
        )

    lang_label = LANG_NAMES.get(language, language.capitalize())

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.TERMINAL, size=12, color="#9CA3AF"),
                        ft.Text(lang_label, size=11, color="#9CA3AF", weight=ft.FontWeight.W_500),
                    ], spacing=4),
                    padding=ft.Padding(left=4, top=0, right=0, bottom=0),
                ),
                ft.Container(
                    content=ft.Icon(ft.Icons.CONTENT_COPY, size=14, color="#9CA3AF"),
                    padding=4,
                    border_radius=6,
                    on_click=_copy,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Markdown(
                    f"```{language}\n{code}\n```",
                    extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                    code_theme="monokai-sublime" if is_dark else "github",
                    selectable=True,
                ),
                padding=ft.Padding(left=0, top=4, right=0, bottom=0),
            ),
        ], spacing=4),
        padding=10,
        border_radius=8,
        bgcolor="rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.04)",
        border=border_all(0.5, DARK_BORDER if is_dark else LIGHT_BORDER),
    )
