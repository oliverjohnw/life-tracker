from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .registry import SPECS


def _wants_fragment(request):
    return request.headers.get("x-requested-with") == "fetch"


def index(request):
    """The standalone 'Log something' page — handy as a phone bookmark."""
    return render(request, "quicklog/page.html", {"kind": "", "form": None, "hide_drawer": True})


@require_http_methods(["GET", "POST"])
def log(request, kind):
    spec = SPECS.get(kind)
    if spec is None:
        raise Http404("Unknown thing to log")

    if request.method == "POST":
        form = spec.make(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            result = {
                "ok": True, "message": form.message, "kind": kind,
                "tracker": spec.cat.label, "view_url": spec.view_url,
            }
            if _wants_fragment(request):
                return JsonResponse(result)
            return render(request, "quicklog/page.html",
                          {"kind": kind, "form": None, "success": result, "hide_drawer": True})
        status = 400
    else:
        form, status = spec.make(), 200

    context = {"form": form, "kind": kind, "spec": spec, "hide_drawer": True}
    template = "quicklog/_form.html" if _wants_fragment(request) else "quicklog/page.html"
    return render(request, template, context, status=status)
