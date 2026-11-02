from django.contrib import admin

from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "status", "format", "date_finished", "rating"]
    list_filter = ["status", "format", "category", "genre"]
    search_fields = ["title", "author", "series"]
    autocomplete_fields = ["recommended_by"]

    fieldsets = [
        ("The book", {"fields": ["title", "author", "series", "category", "genre", "format", "pages", "cover_image"]}),
        ("Reading", {"fields": ["status", "date_started", "date_finished", "re_read", "recommended_by"]}),
        ("Verdict", {"fields": ["rating", "notes", "quotes"]}),
    ]
