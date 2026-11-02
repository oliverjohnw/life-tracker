from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "Life Dashboard"
admin.site.site_title = "Life Dashboard admin"
admin.site.index_title = "Log & manage"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("concerts/", include("concerts.urls")),
    path("movies/", include("movies.urls")),
    path("sports/", include("sports.urls")),
    path("golf/", include("golf.urls")),
    path("books/", include("books.urls")),
    path("log/", include("quicklog.urls")),
    # Uploaded images. The login middleware already guards every path, so these stay private.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    path("", include("dashboard.urls")),
]
