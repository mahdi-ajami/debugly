import flet as ft

LIGHT_BG_PRIMARY = "#F8F9FC"
LIGHT_BG_SURFACE = "#FFFFFF"
LIGHT_BG_SIDEBAR = "#F0F1F5"

LIGHT_ACCENT = "#7C3AED"
LIGHT_ACCENT_SUBTLE = "#EDE9FE"
LIGHT_ACCENT_SECONDARY = "#2563EB"

LIGHT_TEXT_PRIMARY = "#0F172A"
LIGHT_TEXT_SECONDARY = "#475569"
LIGHT_TEXT_MUTED = "#94A3B8"

LIGHT_BORDER = "#E2E8F0"

DARK_BG_PRIMARY = "#0B0D14"
DARK_BG_SURFACE = "#13151D"
DARK_BG_SIDEBAR = "#0F1118"

DARK_ACCENT = "#A78BFA"
DARK_ACCENT_SUBTLE = "rgba(124,58,237,0.15)"
DARK_ACCENT_SECONDARY = "#60A5FA"

DARK_TEXT_PRIMARY = "#F1F5F9"
DARK_TEXT_SECONDARY = "#94A3B8"
DARK_TEXT_MUTED = "#64748B"

DARK_BORDER = "#1E293B"

NAV_WIDTH = 200
STATUS_BAR_HEIGHT = 32
TOP_BAR_HEIGHT = 52
FOOTER_HEIGHT = 64

ALIGN_CENTER = ft.Alignment(0, 0)
ALIGN_TOP_LEFT = ft.Alignment(-1, -1)
ALIGN_BOTTOM_RIGHT = ft.Alignment(1, 1)

BOX_FIT_CONTAIN = ft.controls.box.BoxFit.CONTAIN

DANGER = "#EF4444"
SUCCESS = "#22C55E"
WARNING = "#F59E0B"
INFO = "#3B82F6"

TOKEN_LOW = "#22C55E"
TOKEN_MED = "#F59E0B"
TOKEN_HIGH = "#EF4444"


def padding_symmetric(horizontal: float = 0, vertical: float = 0) -> ft.Padding:
    return ft.Padding(left=horizontal, top=vertical, right=horizontal, bottom=vertical)


def padding_only(left=0, top=0, right=0, bottom=0) -> ft.Padding:
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def border_all(width: float = 1, color: str = "transparent") -> ft.Border:
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


def make_theme(is_dark: bool) -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=LIGHT_ACCENT,
        use_material3=True,
    )


def surface_container(content, width=None, height=None, border_radius=10, padding=16, is_dark=False):
    return ft.Container(
        content=content,
        width=width,
        height=height,
        padding=padding,
        border_radius=border_radius,
        bgcolor=DARK_BG_SURFACE if is_dark else LIGHT_BG_SURFACE,
        border=border_all(1, DARK_BORDER if is_dark else LIGHT_BORDER),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=4,
            color="rgba(0,0,0,0.05)" if not is_dark else "rgba(0,0,0,0.2)",
            offset=ft.Offset(0, 1),
        ),
    )


def is_rtl_text(text: str) -> bool:
    rtl_ranges = [
        (0x0590, 0x05FF), (0x0600, 0x06FF), (0x0700, 0x074F),
        (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB1D, 0xFB4F),
        (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
    ]
    for ch in text:
        cp = ord(ch)
        for lo, hi in rtl_ranges:
            if lo <= cp <= hi:
                return True
    return False
