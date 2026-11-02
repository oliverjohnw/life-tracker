from django.contrib import admin

from .models import SportingEvent


@admin.register(SportingEvent)
class SportingEventAdmin(admin.ModelAdmin):
    list_display = ["date", "league", "matchup", "my_team", "result", "location", "rating"]
    list_filter = ["league", "game_type", "location__state"]
    search_fields = ["home_team", "away_team", "location__name", "notes"]
    date_hierarchy = "date"
    autocomplete_fields = ["location", "attendees"]
    list_select_related = ["location"]
