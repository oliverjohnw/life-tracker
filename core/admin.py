from django.contrib import admin

from .models import Location, Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["name", "relationship"]
    search_fields = ["name", "relationship"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "state", "setting"]
    list_filter = ["setting", "state"]
    search_fields = ["name", "city", "state"]
