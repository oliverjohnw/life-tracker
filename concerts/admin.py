from django.contrib import admin
from django.utils.html import format_html

from .models import Event, Performance


class PerformanceInline(admin.TabularInline):
    model = Performance
    extra = 1
    fields = [
        "order",
        "artist",
        "role",
        "genre",
        "tour_name",
        "rating",
        "set_length",
        "setlist_fm_url",
        "setlist_highlights",
    ]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["poster_thumb", "date", "display_name", "event_type", "location", "attendee_list"]
    list_display_links = ["date", "display_name"]
    list_filter = ["event_type", "location__state"]
    search_fields = ["name", "performances__artist", "location__name"]
    date_hierarchy = "date"
    autocomplete_fields = ["location", "attendees"]
    readonly_fields = ["poster_preview"]
    inlines = [PerformanceInline]
    list_select_related = ["location"]

    fieldsets = [
        ("The night", {"fields": ["date", "name", "event_type", "location", "attendees"]}),
        ("Tickets & spend", {"fields": ["seats", "price", "merch_spent"]}),
        ("How it felt (0–10)", {"fields": ["sound_quality", "view_quality", "crowd_rating"]}),
        ("Poster", {"fields": ["poster_taken", "poster_image", "poster_preview"]}),
        ("Notes", {"fields": ["notes", "venue_notes"]}),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("performances", "attendees")

    @admin.display(description="")
    def poster_thumb(self, obj):
        if obj.poster_image:
            return format_html(
                '<img src="{}" style="height:40px;width:30px;object-fit:cover;border-radius:4px">',
                obj.poster_image.url,
            )
        return ""

    @admin.display(description="Poster preview")
    def poster_preview(self, obj):
        if obj.poster_image:
            return format_html(
                '<img src="{}" style="max-height:260px;border-radius:8px">', obj.poster_image.url
            )
        return "No poster uploaded yet."

    @admin.display(description="Event")
    def display_name(self, obj):
        return obj.title

    @admin.display(description="Attended With")
    def attendee_list(self, obj):
        return ", ".join(p.name for p in obj.attendees.all())


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ["artist", "event", "role", "genre", "rating"]
    list_filter = ["role", "genre"]
    search_fields = ["artist", "tour_name"]
    list_select_related = ["event"]
