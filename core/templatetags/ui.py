from datetime import timedelta
from decimal import Decimal

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

ICONS = {
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "film": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18M3 7.5h4M3 12h18M3 16.5h4M17 3v18M17 7.5h4M17 16.5h4"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7"/>',
    "book": '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2zM22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "external": '<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "plus": '<path d="M5 12h14M12 5v14"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M2 14h4M10 8h4M18 16h4"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "chart": '<path d="M12 20V10M18 20V4M6 20v-4"/>',
    "bookmark": '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "image": '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.09-3.09a2 2 0 0 0-2.82 0L6 21"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "close": '<path d="M18 6 6 18M6 6l12 12"/>',
    "star":'<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>',
}


@register.simple_tag
def icon(name, size=20, cls=""):
    paths = ICONS.get(name, "")
    return format_html(
        '<svg class="icon {}" width="{}" height="{}" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">{}</svg>',
        cls,
        size,
        size,
        mark_safe(paths),
    )


@register.filter
def initials(value, count=2):
    words = [w for w in str(value or "").replace("&", " ").split() if w[:1].isalnum()]
    return "".join(w[0] for w in words[: int(count)]).upper() or "?"


@register.filter
def hue(value):
    """Stable 0-359 hue derived from a string, for placeholder art."""
    return sum(ord(c) * (i + 1) for i, c in enumerate(str(value or ""))) % 360


@register.filter
def score(value):
    """8 -> '8.0', 7.25 -> '7.25', None -> '—'."""
    if value in (None, ""):
        return "—"
    text = format(Decimal(str(value)).normalize(), "f")
    return text if "." in text else f"{text}.0"


@register.filter
def rating_tier(value):
    if value in (None, ""):
        return "none"
    v = float(value)
    if v >= 9:
        return "elite"
    if v >= 8:
        return "high"
    if v >= 6.5:
        return "mid"
    return "low"


@register.filter
def money(value):
    if value in (None, ""):
        return "—"
    value = Decimal(value)
    return f"${value:,.0f}" if value == value.to_integral() else f"${value:,.2f}"


@register.filter
def duration(value):
    if not isinstance(value, timedelta):
        return ""
    minutes = int(value.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    return f"{hours}h" if hours else f"{minutes}m"


@register.filter
def meter(value):
    """0-10 score -> percentage width for a meter bar."""
    try:
        return max(0, min(100, float(value) * 10))
    except (TypeError, ValueError):
        return 0


@register.filter
def signed(value):
    """+3 / -2 / E (even) for golf scores relative to par."""
    if value is None:
        return "—"
    if value == 0:
        return "E"
    return f"{value:+d}"


@register.filter
def first_word(value):
    parts = str(value or "").split()
    return parts[0] if parts else ""


@register.simple_tag
def asset(path):
    """{% static %} plus, in DEBUG, a ?v=<mtime> so edited CSS/JS is never served stale.

    In production WhiteNoise's manifest storage already hashes file names.
    """
    import os

    from django.conf import settings
    from django.contrib.staticfiles import finders
    from django.templatetags.static import static

    url = static(path)
    if settings.DEBUG:
        found = finders.find(path)
        if found:
            url += f"?v={int(os.path.getmtime(found))}"
    return url
