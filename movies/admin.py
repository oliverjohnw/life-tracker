from django.contrib import admin

from .models import Movie, WatchlistItem


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ["title", "year", "date", "platform", "rating", "rewatches"]
    list_filter = ["platform", "genre", "year"]
    search_fields = ["title", "notes"]
    date_hierarchy = "date"
    autocomplete_fields = ["watched_with"]


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ["title", "recommended_by", "watched"]
    list_filter = ["watched"]
    list_editable = ["watched"]
    search_fields = ["title"]
