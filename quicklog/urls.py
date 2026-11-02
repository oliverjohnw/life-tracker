from django.urls import path

from . import views

app_name = "quicklog"

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:kind>/", views.log, name="form"),
]
