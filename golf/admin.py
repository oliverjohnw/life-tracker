from django.contrib import admin

from .models import Round


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ["date", "game", "course", "holes", "score", "par", "to_par_display", "rating"]
    list_filter = ["game", "holes", "course"]
    search_fields = ["course__name", "notes"]
    date_hierarchy = "date"
    autocomplete_fields = ["course", "played_with"]
    list_select_related = ["course"]

    fieldsets = [
        ("The round", {"fields": ["game", "date", "course", "layout", "holes", "score", "par"]}),
        ("Golf handicap extras (optional)", {"fields": ["course_rating", "slope", "transport"],
                                             "classes": ["collapse"]}),
        ("Conditions & company", {"fields": ["weather", "played_with", "rating", "notes"]}),
    ]

    @admin.display(description="To par")
    def to_par_display(self, obj):
        return "—" if obj.to_par is None else ("E" if obj.to_par == 0 else f"{obj.to_par:+d}")
