from django.conf import settings
from django.contrib.auth.views import redirect_to_login

EXEMPT_PREFIXES = ("/admin/login", "/login", "/static/")


class LoginRequiredMiddleware:
    """Requires an authenticated session for every page except login and static files.

    This dashboard shows personal data and is deployed on the open internet, so the
    whole site is locked down by default rather than annotating each view.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not request.path.startswith(EXEMPT_PREFIXES):
            return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)
        return self.get_response(request)
