import plotly.offline

from .categories import BY_SLUG, CATEGORIES

PLOTLY_JS_URL = f"https://cdn.plot.ly/plotly-{plotly.offline.get_plotlyjs_version()}.min.js"


def site(request):
    from quicklog.registry import SPEC_LIST  # imported lazily: it pulls in every tracker's models

    match = getattr(request, "resolver_match", None)
    current = BY_SLUG.get(match.app_name) if match else None
    return {
        "categories": CATEGORIES,
        "current_category": current,
        "plotly_js_url": PLOTLY_JS_URL,
        "log_types": SPEC_LIST,
    }
